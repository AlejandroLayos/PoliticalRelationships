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
2. Clave `boe:persona:…`, `oci:persona:…` o `congreso:persona:…`, que sólo
   ponen los conectores del BOE, de la Oficina de Conflictos de Intereses y
   del Congreso (ver `PUERTAS`).
3. Marca `cargo_publico`, que también ponen sólo esos conectores.
4. Ningún identificador personal (DNI/NIE): ninguna de las dos fuentes los
   publica, así que si hay uno, esa ficha no viene de donde dice.
5. Y lo que sale de ella son **sólo** sus actos de cargo (`Occupancy`), sus
   autorizaciones de actividad privada y las actividades que declaró al
   Congreso como diputado, con procedencia de SU fuente: ni una arista más,
   venga de donde venga. «Sólo en ese papel».

Un diputado sale si se une a un alto cargo del BOE (dos señales, ver abajo)
o si hizo declaración de actividades: la sección no es un censo de escaños,
y de quien sólo consta el escaño no hay nada que cruzar.

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
        # Un mandato del Congreso ya es un periodo entero, con su alta y su
        # baja: no hay que emparejar nada.
        for a in lista:
            if a["tipo"] == "mandato":
                salida.append(
                    {
                        "puesto": a["puesto"],
                        "cargo": a["cargo"],
                        "organismo": a.get("organismo") or "",
                        "desde": a["fecha"],
                        **({"hasta": a["hasta"]} if a.get("hasta") else {}),
                        "urlDesde": a["url"],
                        **_fuente_no_boe(a),
                        **{
                            k: a[k]
                            for k in ("formacion", "grupo", "circunscripcion", "cruce")
                            if a.get(k)
                        },
                    }
                )
        lista = [a for a in lista if a["tipo"] != "mandato"]
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
    # El guion une: «BESS-BEYOND» es una palabra, no dos.
    sin = re.sub(r"(?<=\w)-(?=\w)", "", sin)
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


def nombre_natural(nombre: str) -> str:
    """«Báñez García, María Fátima» → «María Fátima Báñez García».

    El Congreso y la Oficina de Conflictos de Intereses escriben primero los
    apellidos y el BOE no; en la misma página, la misma persona tiene que
    leerse igual venga de donde venga. Sólo se da la vuelta a lo que tiene
    exactamente una coma con texto a los dos lados.
    """
    partes = [p.strip() for p in nombre.split(",")]
    if len(partes) != 2 or not all(partes):
        return nombre
    return f"{partes[1]} {partes[0]}"


def _fuente_no_boe(acto: dict[str, Any]) -> dict[str, str]:
    """La fuente de un periodo, sólo si no es el BOE: la web lo dice."""
    fuente = acto.get("fuente") or "boe"
    return {} if fuente == "boe" else {"fuente": fuente}


def _serializable(p: dict[str, Any]) -> dict[str, Any]:
    return {k: (v.isoformat() if isinstance(v, date) else v) for k, v in p.items()}


#: Las puertas: el prefijo de clave que pone cada conector, y la ÚNICA fuente
#: cuya procedencia vale para él. Una ficha con clave del BOE pero sin
#: documento del BOE no sale, y al revés.
PUERTAS = {"boe:persona:": "boe", "oci:persona:": "oci", "congreso:persona:": "congreso"}

#: Días de margen entre la fecha de cese que da la Oficina de Conflictos de
#: Intereses y la que publica el BOE: la una es la del cese y la otra la de su
#: publicación, que suele ser el día siguiente.
MARGEN_CESE = 10

#: Lo que se lee de cada actividad que declara un diputado.
_CAMPOS_DECLARACION = ("empleador", "sector", "periodo", "descripcion", "fechaRegistro", "url")

#: Cuántos cruces del cargo a la empresa viajan con el grafo, para la portada.
#: El resto está en cargos.json, en la ficha de cada persona y sociedad.
MAX_CRUCES_EN_PORTADA = 40


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
          -- Lo que declaran los diputados es su texto, no una sociedad del
          -- mapa: sin esto, «UNIPREX S.A.U.» declarado se cruzaría consigo.
          AND dedupe_key NOT LIKE 'congreso:%'
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


# Lo que puede ir justo antes del nombre de una sociedad en el texto de una
# autorización: «socio DE Ey Abogados», «consejero DEL grupo», «EN Indra».
_ANTES_DEL_NOMBRE = frozenset(
    {"de", "del", "la", "el", "los", "las", "en", "para", "con", "y", "a", "al"}
)

# Las formas societarias, ya normalizadas: son el final de una denominación.
_FORMAS = frozenset(
    {
        "sa",
        "sau",
        "sl",
        "slu",
        "slp",
        "sll",
        "sal",
        "sme",
        "mp",
        "scoop",
        "coop",
        "aie",
        "ute",
        "sad",
        "se",
    }
)


def es_sociedad_mercantil(nombre: str) -> bool:
    """Si la denominación acaba en una forma de sociedad (S.A., S.L.…).

    `parece_forma_societaria` reconoce también universidades, fundaciones o
    asociaciones, que es lo que hace falta para no tratarlas como personas.
    Para decir «una sociedad que cobra dinero público» hace falta una
    sociedad de verdad: la Universidad de Cantabria no lo es.
    """
    palabras = _palabras(nombre)
    return bool(palabras) and palabras[-1] in _FORMAS


def empresa_en(texto: str, mapa: dict[str, list[tuple[str, str]]]) -> dict[str, str] | None:
    """La sociedad del mapa que nombra un texto, entera y sin dudas.

    Se busca la denominación completa, palabra a palabra: «SOCIO DE EY
    ABOGADOS, S.L.P.» contiene «EY ABOGADOS, S.L.P.». Pero entera de verdad:

    - por delante, el principio del texto o una preposición o artículo.
      «BESS-BEYOND SOLUCIONES Y SERVICIOS, S.L.» contiene las palabras de
      «BEYOND SOLUCIONES Y SERVICIOS S.L.», que es OTRA sociedad; salió así
      en el primer cruce con los datos reales;
    - por detrás, una forma societaria, que cierra la denominación, o el
      final del texto.

    Si caben dos sociedades distintas, o el nombre es de varias fichas, no
    se elige.
    """
    palabras = _palabras(texto)
    halladas: dict[str, tuple[str, str]] = {}
    for i in range(len(palabras)):
        if i > 0 and palabras[i - 1] not in _ANTES_DEL_NOMBRE:
            continue
        for j in range(len(palabras), i, -1):
            nombre = " ".join(palabras[i:j])
            if nombre not in mapa:
                continue
            if palabras[j - 1] not in _FORMAS and j != len(palabras):
                continue
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
    biografias: dict[str, list[str]] = {}
    descartadas = 0
    for f in filas:
        # La condición del DNI en Python, con la misma función que usa el
        # grafo: así no hay dos definiciones de «identificador personal».
        if es_identificador_personal(f["nif"]):
            descartadas += 1
            continue
        props = f["properties"] or {}
        tipo = props.get("acto")
        fecha = f["end_date"] if tipo == "cese" else f["start_date"]
        if tipo not in {"nombramiento", "cese", "mandato"} or fecha is None:
            continue
        clave = f["dedupe_key"]
        fuente = next(v for k, v in PUERTAS.items() if clave.startswith(k))
        nombre = f["caption"] if fuente == "boe" else nombre_natural(f["caption"])
        personas.setdefault(clave, {"clave": clave, "nombre": nombre})
        if fuente in {"oci", "congreso"}:
            para_cruzar[clave] = (f["props_persona"] or {}).get("nombreParaCruzar", "")
        if fuente == "congreso":
            biografias[clave] = [
                _plano(m) for m in (f["props_persona"] or {}).get("cargosEnBiografia", [])
            ]
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
                **({"hasta": f["end_date"]} if tipo == "mandato" and f["end_date"] else {}),
                **{k: props[k] for k in ("formacion", "grupo", "circunscripcion") if props.get(k)},
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

    # Las actividades que declaró cada diputado al Congreso.
    declaraciones: dict[str, list[dict[str, Any]]] = {}
    for f in _filas_de_la_puerta(
        store, "UnknownLink", "AND (r.properties ->> 'relacion') = 'actividad_declarada'"
    ):
        if f["dedupe_key"] not in personas:
            continue
        props = f["properties"] or {}
        declaraciones.setdefault(f["dedupe_key"], []).append(
            {k: props[k] for k in _CAMPOS_DECLARACION if props.get(k)}
        )

    # La misma persona en las dos fuentes: nombre entero y fecha de cese a la
    # vez. Una sola de las dos señales no basta —con dos apellidos los
    # homónimos son menos, no ninguno (§12)—; las dos juntas sí.
    boe_por_nombre: dict[str, list[str]] = {}
    for clave, persona in personas.items():
        if clave.startswith("boe:"):
            boe_por_nombre.setdefault(_plano(persona["nombre"]), []).append(clave)
    unida_a: dict[str, str] = {}
    for clave_otra, nombre in para_cruzar.items():
        candidatas = boe_por_nombre.get(nombre, [])
        if len(candidatas) != 1:
            continue
        del_boe = actos[candidatas[0]]
        if clave_otra.startswith("oci:"):
            ceses_oci = [a["fecha"] for a in actos[clave_otra] if a["tipo"] == "cese"]
            ceses_boe = [a["fecha"] for a in del_boe if a["tipo"] == "cese"]
            if any(abs((a - b).days) <= MARGEN_CESE for a in ceses_oci for b in ceses_boe):
                unida_a[clave_otra] = candidatas[0]
        else:
            # Congreso: el nombre entero y, además, que su biografía en el
            # Congreso mencione uno de sus cargos del BOE. La segunda señal la
            # da la propia fuente.
            cargos_boe = {_plano(a["cargo"]) for a in del_boe} | {
                _plano(a["puesto"]) for a in del_boe
            }
            cargos_boe = {c for c in cargos_boe if len(c.split()) >= 3}
            if any(c in m for c in cargos_boe for m in biografias.get(clave_otra, [])):
                unida_a[clave_otra] = candidatas[0]

    organos = organos_del_estado(store)
    empresas_mapa = empresas_por_nombre(store) if autorizaciones or declaraciones else {}
    # Y al revés: de cada órgano, quién lo dirigió; de cada sociedad, qué ex
    # altos cargos fueron autorizados a trabajar en ella y qué diputados
    # declararon haber trabajado en ella.
    al_frente: dict[str, list[dict[str, Any]]] = {}
    en_empresas: dict[str, list[dict[str, Any]]] = {}
    declarantes: dict[str, list[dict[str, Any]]] = {}
    formacion_de: dict[str, str] = {}

    salida = []
    for clave, persona in personas.items():
        if clave in unida_a:
            continue
        # Un diputado que no se une a ningún alto cargo sale sólo si declaró
        # actividades: de quien sólo consta el escaño no hay nada que cruzar.
        if clave.startswith("congreso:") and not declaraciones.get(clave):
            continue
        propios_actos = list(actos[clave])
        for c, b in unida_a.items():
            if b == clave and c.startswith("congreso:"):
                propios_actos += [
                    {**a, "cruce": "nombre y cargo en su biografía del Congreso"} for a in actos[c]
                ]
        ps = periodos(propios_actos)
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
        declaradas = list(declaraciones.get(clave, []))
        for c in cruces:
            if c.startswith("congreso:"):
                declaradas += [
                    {**d, "cruce": "nombre y cargo en su biografía del Congreso"}
                    for d in declaraciones.get(c, [])
                ]
        # La formación con la que fue elegido, para decirla junto al nombre
        # donde la persona sale fuera de su ficha. La del último mandato.
        mandatos = sorted(
            (p for p in ps if p.get("fuente") == "congreso" and p.get("formacion")),
            key=lambda p: p["desde"],
        )
        formacion = mandatos[-1]["formacion"] if mandatos else ""
        formacion_de[clave] = formacion
        for d in declaradas:
            empresa = empresa_en(d.get("empleador", ""), empresas_mapa)
            if empresa is None:
                continue
            d["empresa"] = empresa
            # Una persona, una vez por sociedad: quien declaró tres etapas en
            # la misma universidad es un declarante, no tres.
            if any(x["persona"] == clave for x in declarantes.get(empresa["clave"], [])):
                continue
            declarantes.setdefault(empresa["clave"], []).append(
                {
                    "persona": clave,
                    "nombre": persona["nombre"],
                    **({"formacion": formacion} if formacion else {}),
                    **{k: d[k] for k in ("empleador", "descripcion", "periodo") if d.get(k)},
                }
            )
        salida.append(
            {
                **persona,
                "periodos": [_serializable(p) for p in ps],
                **({"autorizaciones": [_serializable(a) for a in propias]} if propias else {}),
                **({"declaraciones": declaradas} if declaradas else {}),
            }
        )
    for lista in (*al_frente.values(), *en_empresas.values()):
        lista.sort(
            key=lambda x: x.get("hasta") or x.get("desde") or x.get("fecha") or "", reverse=True
        )

    for lista in declarantes.values():
        lista.sort(key=lambda x: x["nombre"])

    def ultima(p: dict[str, Any]) -> str:
        fechas_p = [x.get("hasta") or x.get("desde") or "" for x in p["periodos"]]
        fechas_p += [a.get("fecha", "") for a in p.get("autorizaciones", [])]
        return max(fechas_p or [""])

    salida.sort(key=lambda p: (ultima(p), p["nombre"]), reverse=True)

    # Los actos del BOE, y sólo ésos: «nombradas o cesadas por Real Decreto
    # entre el … y el …» no puede contar un cese que sólo da la Oficina de
    # Conflictos de Intereses, ni el alta de un diputado en 2008.
    fechas = [
        a["fecha"] for clave, lista in actos.items() if clave.startswith("boe:") for a in lista
    ]
    documento = {
        "generado": datetime.now(UTC).isoformat(),
        "fuente": "Boletín Oficial del Estado",
        # Lo que se ha leído, no lo que existe: un nombramiento anterior a
        # `desde` no está, y la web lo tiene que poder decir.
        "actosDesde": min(fechas).isoformat() if fechas else None,
        "actosHasta": max(fechas).isoformat() if fechas else None,
        "nActos": len(fechas),
        "nAutorizaciones": sum(len(v) for v in autorizaciones.values()),
        "nDeclaraciones": sum(len(p.get("declaraciones", [])) for p in salida),
        "personas": salida,
        "organos": al_frente,
        "empresas": en_empresas,
        "declarantes": declarantes,
    }
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(documento, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    por_fuente = {
        fuente: sum(1 for c in personas if c.startswith(prefijo))
        for prefijo, fuente in PUERTAS.items()
    }
    # Los cruces del cargo a la empresa, para la portada: cada autorización
    # que nombra una sociedad del mapa del dinero. Van en el grafo, que la
    # portada ya tiene, para no hacerle descargar todos los cargos.
    cruces = sorted(
        (
            {
                "persona": p["clave"],
                "nombre": p["nombre"],
                "cargoAnterior": a.get("cargoAnterior", ""),
                "actividad": a["actividad"],
                "empresa": a["empresa"],
                **({"fecha": a["fecha"]} if a.get("fecha") else {}),
            }
            for p in salida
            for a in p.get("autorizaciones", [])
            if a.get("empresa")
        ),
        key=lambda c: c.get("fecha", ""),
        reverse=True,
    )
    # Y de lo declarado al Congreso: cada sociedad mercantil del mapa que
    # nombra una actividad, una vez por persona. Por nombre, no por dinero: no
    # es una lista de sospechosos.
    declarados: list[dict[str, Any]] = []
    vistos: set[tuple[str, str]] = set()
    for p in salida:
        for d in p.get("declaraciones", []):
            empresa = d.get("empresa")
            if not empresa or not es_sociedad_mercantil(empresa["nombre"]):
                continue
            if (p["clave"], empresa["clave"]) in vistos:
                continue
            vistos.add((p["clave"], empresa["clave"]))
            declarados.append(
                {
                    "persona": p["clave"],
                    "nombre": p["nombre"],
                    **{k: d[k] for k in ("empleador", "descripcion", "periodo") if d.get(k)},
                    "empresa": empresa,
                    **(
                        {"formacion": formacion_de[p["clave"]]}
                        if formacion_de.get(p["clave"])
                        else {}
                    ),
                }
            )
    declarados.sort(key=lambda c: (c["empresa"]["nombre"], c["nombre"]))
    resumen = {
        "cargos_personas": len(salida),
        "cargos_actos": len(fechas),
        "cargos_organos": len(al_frente),
        "cargos_por_fuente": por_fuente,
        "cruces": cruces[:MAX_CRUCES_EN_PORTADA],
        "n_cruces": len(cruces),
        "declarados": declarados[:MAX_CRUCES_EN_PORTADA],
        "n_declarados": len(declarados),
    }
    log.info(
        "cargos exportados",
        destino=str(destino),
        **{k: v for k, v in resumen.items() if k not in {"cruces", "declarados"}},
    )
    return resumen
