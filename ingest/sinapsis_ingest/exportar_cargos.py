"""Exporta los cargos públicos a `cargos.json`, aparte del grafo.

Es la única puerta por la que sale el nombre de una persona física, y por eso
es una puerta propia y estrecha en vez de una excepción dentro de la general.
El volcado del grafo sigue sin dejar pasar a NINGUNA persona —como desde
septiembre de 2026—; una excepción metida ahí tendría que convivir con tres
reglas de bloqueo y con el tapado de nombres, y el día que alguien tocara una
de ellas podría abrirla sin querer.

## Qué tiene que cumplir una persona para salir aquí (spec §12)

Todo a la vez, comprobado en SQL sobre la base, no sobre lo que diga el
conector:

1. Esquema `Person`, canónica (no absorbida por una fusión).
2. Clave `boe:persona:…` u `oci:persona:…`, que sólo ponen los conectores
   del BOE y de la Oficina de Conflictos de Intereses (ver `PUERTAS`).
3. Marca `cargo_publico`, que también ponen sólo esos conectores.
4. Ningún identificador personal (DNI/NIE): ninguna de las dos fuentes los
   publica, así que si hay uno, esa ficha no viene de donde dice.
5. Y lo que sale de ella son **sólo** sus actos de cargo (`Occupancy`) y sus
   autorizaciones de actividad privada, con procedencia de SU fuente: ni una
   arista más, venga de donde venga. «Sólo en ese papel».

Lo demás de la persona —si administra una empresa, si cobró una subvención—
no sale por aquí. Cuando haya un vínculo así afirmado por una fuente, o
confirmado por una persona en la cola de revisión, entrará con su propia
regla y su propio test.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import structlog

from sinapsis_ingest.cargos import organo_del_puesto
from sinapsis_ingest.store import Store
from sinapsis_ingest.territorio import clasificar_entidad
from sinapsis_ingest.util import es_identificador_personal, parece_forma_societaria

log = structlog.get_logger()


def periodos(actos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Junta nombramientos y ceses de un mismo puesto en periodos.

    Cada acto es un dict con `tipo` («nombramiento» o «cese»), `fecha`
    (date), `puesto`, `cargo`, `organismo`, `boe` y `url`.

    Por puesto, en orden de fecha: un nombramiento abre un periodo y el
    siguiente cese del mismo puesto lo cierra. Lo que no se puede emparejar
    se enseña tal cual, sin rellenar:

    - un cese sin nombramiento (fue nombrado antes de lo que se ha leído)
      sale con `desde` vacío;
    - un nombramiento sin cese sale con `hasta` vacío, que quiere decir «no
      consta cese», no «sigue en el cargo»;
    - dos nombramientos seguidos sin cese entre medias —un cese colectivo
      que no se lee, por ejemplo— dan dos periodos, el primero sin fin. No
      se inventa la fecha en que acabó.

    El mismo día, el cese va antes que el nombramiento: es lo que pasa
    cuando se forma un gobierno y se vuelve a nombrar a alguien en el mismo
    cargo, y al revés cerraría el periodo nuevo en el día en que empieza.
    """
    orden = {"cese": 0, "nombramiento": 1}
    por_puesto: dict[str, list[dict[str, Any]]] = {}
    for a in actos:
        por_puesto.setdefault(a["puesto"], []).append(a)

    salida: list[dict[str, Any]] = []
    for lista in por_puesto.values():
        lista.sort(key=lambda a: (a["fecha"], orden.get(a["tipo"], 2)))
        abierto: dict[str, Any] | None = None
        for a in lista:
            if a["tipo"] == "nombramiento":
                if abierto is not None:
                    salida.append(abierto)
                abierto = {
                    "puesto": a["puesto"],
                    "cargo": a["cargo"],
                    "organismo": a.get("organismo") or "",
                    "desde": a["fecha"],
                    "boeDesde": a["boe"],
                    "urlDesde": a["url"],
                    **_fuente_no_boe(a),
                }
            elif a["tipo"] == "cese":
                cierre = {
                    "hasta": a["fecha"],
                    "boeHasta": a["boe"],
                    "urlHasta": a["url"],
                    **({"motivoCese": a["motivo"]} if a.get("motivo") else {}),
                }
                if abierto is not None:
                    salida.append({**abierto, **cierre})
                    abierto = None
                else:
                    salida.append(
                        {
                            "puesto": a["puesto"],
                            "cargo": a["cargo"],
                            "organismo": a.get("organismo") or "",
                            **cierre,
                            **_fuente_no_boe(a),
                        }
                    )
        if abierto is not None:
            salida.append(abierto)

    def reciente(p: dict[str, Any]) -> date:
        return p.get("hasta") or p.get("desde") or date.min

    # Lo más reciente arriba, y a igualdad, lo que sigue abierto primero.
    salida.sort(key=lambda p: (reciente(p), "hasta" not in p), reverse=True)
    return salida


def _plano(texto: str) -> str:
    sin = "".join(
        c for c in unicodedata.normalize("NFKD", texto or "") if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^a-z0-9]+", " ", sin.lower()).strip()


def organos_del_estado(store: Store) -> dict[str, list[tuple[str, str]]]:
    """{nombre normalizado: [(clave, nombre)]} de los órganos del Estado.

    Sólo los que la jerarquía de su propia fuente sitúa en la Administración
    del Estado: «Dirección General de Carreteras» existe también en alguna
    comunidad autónoma, y quien fue director general del Estado no dirigió
    la de la comunidad.
    """
    filas = store.conn.execute(
        """
        SELECT caption, dedupe_key, properties FROM entities
        WHERE canonical_id IS NULL AND ftm_schema = 'PublicBody'
          AND dedupe_key NOT LIKE 'boe:%'
        """
    ).fetchall()
    por_nombre: dict[str, list[tuple[str, str]]] = {}
    for f in filas:
        props = {**(f["properties"] or {}), "name": f["caption"]}
        if clasificar_entidad(props).nivel != "estatal":
            continue
        por_nombre.setdefault(_plano(f["caption"]), []).append((f["dedupe_key"], f["caption"]))
    return por_nombre


def organo_de(puesto: str, organos: dict[str, list[tuple[str, str]]]) -> dict[str, str] | None:
    """El órgano que dirigía el puesto, si su nombre es el de UNO del Estado."""
    nombre = organo_del_puesto(puesto)
    if not nombre:
        return None
    hallados = organos.get(_plano(nombre), [])
    if len(hallados) != 1:
        # Ninguno, o varios con el mismo nombre: no se elige.
        return None
    clave, caption = hallados[0]
    return {"clave": clave, "nombre": caption}


def _fuente_no_boe(acto: dict[str, Any]) -> dict[str, str]:
    """La fuente de un periodo, sólo si no es el BOE: la web lo dice."""
    fuente = acto.get("fuente") or "boe"
    return {} if fuente == "boe" else {"fuente": fuente}


def _serializable(p: dict[str, Any]) -> dict[str, Any]:
    return {k: (v.isoformat() if isinstance(v, date) else v) for k, v in p.items()}


#: Las puertas: el prefijo de clave que pone cada conector, y la ÚNICA fuente
#: cuya procedencia vale para él. Una ficha con clave del BOE pero sin
#: documento del BOE no sale, y al revés.
PUERTAS = {"boe:persona:": "boe", "oci:persona:": "oci"}

#: Días de margen entre la fecha de cese que da la Oficina de Conflictos de
#: Intereses y la que publica el BOE: la una es la del cese y la otra la de su
#: publicación, que suele ser el día siguiente.
MARGEN_CESE = 10


def _filas_de_la_puerta(store: Store, esquema: str, extra: str = "") -> list[Any]:
    """Aristas de las personas que pasan la puerta, con su procedencia."""
    condiciones = " OR ".join("(p.dedupe_key LIKE %s AND rd.source_id = %s)" for _ in PUERTAS)
    parametros: list[Any] = []
    for prefijo, fuente in PUERTAS.items():
        parametros += [prefijo + "%", fuente]
    return store.conn.execute(
        f"""
        SELECT p.id, p.caption, p.dedupe_key, COALESCE(p.nif, '') AS nif,
               p.properties AS props_persona,
               t.caption AS destino, t.dedupe_key AS clave_destino,
               r.start_date, r.end_date, r.properties
        FROM relationships r
        JOIN entities p ON p.id = r.source_entity_id AND p.canonical_id IS NULL
        JOIN entities t ON t.id = r.target_entity_id AND t.canonical_id IS NULL
        WHERE r.ftm_schema = %s
          AND r.status <> 'retracted'
          AND p.ftm_schema = 'Person'
          AND (p.properties ->> 'cargo_publico') = 'true'
          {extra}
          AND EXISTS (
              SELECT 1 FROM provenance pv
              JOIN raw_documents rd ON rd.id = pv.raw_document_id
              WHERE pv.relationship_id = r.id AND ({condiciones})
          )
        """,
        [esquema, *parametros],
    ).fetchall()


def _palabras(texto: str) -> list[str]:
    """Las palabras de un nombre, con las siglas juntas.

    «S.L.U.», «S. L. U.» y «SLU» son la misma forma societaria, y la fuente
    escribe las tres («REDEIA,SL»): letras sueltas seguidas se juntan en una.
    """
    salida: list[str] = []
    sigla = False
    for palabra in _plano(texto).split():
        if len(palabra) == 1:
            if sigla:
                salida[-1] += palabra
            else:
                salida.append(palabra)
            sigla = True
        else:
            salida.append(palabra)
            sigla = False
    return salida


def empresas_por_nombre(store: Store) -> dict[str, list[tuple[str, str]]]:
    """{denominación normalizada: [(clave, nombre)]} de las sociedades del mapa.

    Sólo las que llevan forma societaria en el nombre. La denominación social
    es única en España —el Registro Mercantil Central no inscribe dos
    iguales—, así que «EL CORTE INGLES, S.A.» dentro del texto de una
    autorización es esa sociedad y no otra. Un nombre sin forma societaria
    («LOGISTA», «OESIA») no tiene esa garantía y no se cruza.
    """
    filas = store.conn.execute(
        """
        SELECT caption, dedupe_key, COALESCE(nif, '') AS nif FROM entities
        WHERE canonical_id IS NULL
          AND ftm_schema IN ('Company', 'Organization', 'LegalEntity')
          AND dedupe_key NOT LIKE 'oci:%'
          AND dedupe_key NOT LIKE 'boe:%'
        """
    ).fetchall()
    mapa: dict[str, list[tuple[str, str]]] = {}
    for f in filas:
        if es_identificador_personal(f["nif"]) or not parece_forma_societaria(f["caption"]):
            continue
        mapa.setdefault(" ".join(_palabras(f["caption"])), []).append(
            (f["dedupe_key"], f["caption"])
        )
    return mapa


def empresa_en(texto: str, mapa: dict[str, list[tuple[str, str]]]) -> dict[str, str] | None:
    """La sociedad del mapa que nombra un texto, entera y sin dudas.

    Se busca la denominación completa, palabra a palabra: «SOCIO DE EY
    ABOGADOS, S.L.P.» contiene «EY ABOGADOS, S.L.P.». Si caben dos
    sociedades distintas, o el nombre es de varias fichas, no se elige.
    """
    palabras = _palabras(texto)
    halladas: dict[str, tuple[str, str]] = {}
    for i in range(len(palabras)):
        for j in range(len(palabras), i, -1):
            nombre = " ".join(palabras[i:j])
            if nombre in mapa:
                if len(mapa[nombre]) == 1:
                    halladas[nombre] = mapa[nombre][0]
                break
    # Una denominación dentro de otra («X, S.A.» y «GRUPO X, S.A.») cuenta
    # como la más larga.
    largas = [n for n in halladas if not any(n != m and n in m for m in halladas)]
    if len(largas) != 1:
        return None
    clave, nombre = halladas[largas[0]]
    return {"clave": clave, "nombre": nombre}


def exportar_cargos(store: Store, destino: Path) -> dict[str, Any]:
    """Escribe `destino` con las personas que pasan las condiciones de §12."""
    filas = _filas_de_la_puerta(store, "Occupancy")

    personas: dict[str, dict[str, Any]] = {}
    actos: dict[str, list[dict[str, Any]]] = {}
    para_cruzar: dict[str, str] = {}
    descartadas = 0
    for f in filas:
        # La condición del DNI en Python, con la misma función que usa el
        # grafo: así no hay dos definiciones de «identificador personal».
        if es_identificador_personal(f["nif"]):
            descartadas += 1
            continue
        props = f["properties"] or {}
        tipo = props.get("acto")
        fecha = f["start_date"] if tipo == "nombramiento" else f["end_date"]
        if tipo not in {"nombramiento", "cese"} or fecha is None:
            continue
        clave = f["dedupe_key"]
        fuente = "oci" if clave.startswith("oci:") else "boe"
        personas.setdefault(clave, {"clave": clave, "nombre": f["caption"]})
        if fuente == "oci":
            para_cruzar[clave] = (f["props_persona"] or {}).get("nombreParaCruzar", "")
        actos.setdefault(clave, []).append(
            {
                "tipo": tipo,
                "fecha": fecha,
                "puesto": f["destino"],
                "cargo": props.get("cargo") or f["destino"],
                "organismo": props.get("departamento") or "",
                "boe": props.get("boe") or "",
                "url": props.get("url") or "",
                "motivo": props.get("motivo") or "",
                "fuente": fuente,
            }
        )
    if descartadas:
        log.error(
            "cargos: fichas con identificador personal; no vienen de donde dicen",
            descartadas=descartadas,
        )

    # Las autorizaciones de actividad privada tras el cese.
    autorizaciones: dict[str, list[dict[str, Any]]] = {}
    for f in _filas_de_la_puerta(
        store, "UnknownLink", "AND (r.properties ->> 'relacion') = 'autorizacion_actividad_privada'"
    ):
        if f["dedupe_key"] not in personas:
            continue
        props = f["properties"] or {}
        autorizaciones.setdefault(f["dedupe_key"], []).append(
            {
                "actividad": props.get("actividad") or f["destino"],
                **({"fecha": f["start_date"]} if f["start_date"] else {}),
                "cargoAnterior": props.get("cargoAnterior", ""),
                **({"fechaCese": props["fechaCese"]} if props.get("fechaCese") else {}),
                "url": props.get("url", ""),
            }
        )

    # La misma persona en las dos fuentes: nombre entero y fecha de cese a la
    # vez. Una sola de las dos señales no basta —con dos apellidos los
    # homónimos son menos, no ninguno (§12)—; las dos juntas sí.
    boe_por_nombre: dict[str, list[str]] = {}
    for clave, persona in personas.items():
        if clave.startswith("boe:"):
            boe_por_nombre.setdefault(_plano(persona["nombre"]), []).append(clave)
    unida_a: dict[str, str] = {}
    for clave_oci, nombre in para_cruzar.items():
        candidatas = boe_por_nombre.get(nombre, [])
        if len(candidatas) != 1:
            continue
        ceses_oci = [a["fecha"] for a in actos[clave_oci] if a["tipo"] == "cese"]
        ceses_boe = [a["fecha"] for a in actos[candidatas[0]] if a["tipo"] == "cese"]
        if any(abs((a - b).days) <= MARGEN_CESE for a in ceses_oci for b in ceses_boe):
            unida_a[clave_oci] = candidatas[0]

    organos = organos_del_estado(store)
    empresas_mapa = empresas_por_nombre(store) if autorizaciones else {}
    # Y al revés: de cada órgano, quién lo dirigió; de cada sociedad, qué ex
    # altos cargos fueron autorizados a trabajar en ella.
    al_frente: dict[str, list[dict[str, Any]]] = {}
    en_empresas: dict[str, list[dict[str, Any]]] = {}

    salida = []
    for clave, persona in personas.items():
        if clave in unida_a:
            continue
        ps = periodos(actos[clave])
        for p in ps:
            organo = organo_de(p["puesto"], organos)
            if organo is None:
                continue
            p["organo"] = organo
            al_frente.setdefault(organo["clave"], []).append(
                _serializable(
                    {
                        "persona": clave,
                        "nombre": persona["nombre"],
                        "cargo": p["cargo"],
                        **{k: p[k] for k in ("desde", "hasta") if k in p},
                    }
                )
            )
        propias = list(autorizaciones.get(clave, []))
        cruces = [c for c, b in unida_a.items() if b == clave]
        for c in cruces:
            propias += [{**a, "cruce": "nombre y fecha de cese"} for a in autorizaciones.get(c, [])]
        for a in propias:
            empresa = empresa_en(a["actividad"], empresas_mapa)
            if empresa is None:
                continue
            a["empresa"] = empresa
            en_empresas.setdefault(empresa["clave"], []).append(
                _serializable(
                    {
                        "persona": clave,
                        "nombre": persona["nombre"],
                        "actividad": a["actividad"],
                        "cargoAnterior": a.get("cargoAnterior", ""),
                        **({"fecha": a["fecha"]} if a.get("fecha") else {}),
                    }
                )
            )
        propias.sort(key=lambda a: a.get("fecha") or date.min, reverse=True)
        salida.append(
            {
                **persona,
                "periodos": [_serializable(p) for p in ps],
                **({"autorizaciones": [_serializable(a) for a in propias]} if propias else {}),
            }
        )
    for lista in (*al_frente.values(), *en_empresas.values()):
        lista.sort(
            key=lambda x: x.get("hasta") or x.get("desde") or x.get("fecha") or "", reverse=True
        )

    def ultima(p: dict[str, Any]) -> str:
        fechas_p = [x.get("hasta") or x.get("desde") or "" for x in p["periodos"]]
        fechas_p += [a.get("fecha", "") for a in p.get("autorizaciones", [])]
        return max(fechas_p or [""])

    salida.sort(key=lambda p: (ultima(p), p["nombre"]), reverse=True)

    fechas = [a["fecha"] for lista in actos.values() for a in lista]
    documento = {
        "generado": datetime.now(UTC).isoformat(),
        "fuente": "Boletín Oficial del Estado",
        # Lo que se ha leído, no lo que existe: un nombramiento anterior a
        # `desde` no está, y la web lo tiene que poder decir.
        "actosDesde": min(fechas).isoformat() if fechas else None,
        "actosHasta": max(fechas).isoformat() if fechas else None,
        "nActos": len(fechas),
        "nAutorizaciones": sum(len(v) for v in autorizaciones.values()),
        "personas": salida,
        "organos": al_frente,
        "empresas": en_empresas,
    }
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(documento, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    por_fuente = {
        fuente: sum(1 for c in personas if c.startswith(prefijo))
        for prefijo, fuente in PUERTAS.items()
    }
    resumen = {
        "cargos_personas": len(salida),
        "cargos_actos": len(fechas),
        "cargos_organos": len(al_frente),
        "cargos_por_fuente": por_fuente,
    }
    log.info("cargos exportados", destino=str(destino), **resumen)
    return resumen
