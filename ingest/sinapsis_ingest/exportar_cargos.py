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
2. Clave `boe:persona:…`, que sólo pone el conector del BOE.
3. Marca `cargo_publico`, que también pone sólo ese conector.
4. Ningún identificador personal (DNI/NIE): el BOE no los publica en un
   nombramiento, así que si hay uno, esa ficha no viene de donde dice.
5. Y lo que sale de ella son **sólo** sus actos `Occupancy` con procedencia
   del BOE: ni una arista más, venga de donde venga. «Sólo en ese papel».

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
from sinapsis_ingest.util import es_identificador_personal

log = structlog.get_logger()

PREFIJO_PERSONA = "boe:persona:"
FUENTE = "boe"


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


def _serializable(p: dict[str, Any]) -> dict[str, Any]:
    return {k: (v.isoformat() if isinstance(v, date) else v) for k, v in p.items()}


def exportar_cargos(store: Store, destino: Path) -> dict[str, Any]:
    """Escribe `destino` con las personas que pasan las cinco condiciones."""
    filas = store.conn.execute(
        """
        SELECT p.id, p.caption, p.dedupe_key, COALESCE(p.nif, '') AS nif,
               pos.caption AS puesto,
               r.start_date, r.end_date, r.properties
        FROM relationships r
        JOIN entities p   ON p.id = r.source_entity_id AND p.canonical_id IS NULL
        JOIN entities pos ON pos.id = r.target_entity_id AND pos.canonical_id IS NULL
        WHERE r.ftm_schema = 'Occupancy'
          AND r.status <> 'retracted'
          AND pos.ftm_schema = 'Position'
          AND p.ftm_schema = 'Person'
          AND p.dedupe_key LIKE %s
          AND (p.properties ->> 'cargo_publico') = 'true'
          AND EXISTS (
              SELECT 1 FROM provenance pv
              JOIN raw_documents rd ON rd.id = pv.raw_document_id
              WHERE pv.relationship_id = r.id AND rd.source_id = %s
          )
        """,
        (PREFIJO_PERSONA + "%", FUENTE),
    ).fetchall()

    personas: dict[str, dict[str, Any]] = {}
    actos: dict[str, list[dict[str, Any]]] = {}
    descartadas = 0
    for f in filas:
        # La cuarta condición en Python, con la misma función que usa el
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
        personas.setdefault(clave, {"clave": clave, "nombre": f["caption"]})
        actos.setdefault(clave, []).append(
            {
                "tipo": tipo,
                "fecha": fecha,
                "puesto": f["puesto"],
                "cargo": props.get("cargo") or f["puesto"],
                "organismo": props.get("departamento") or "",
                "boe": props.get("boe") or "",
                "url": props.get("url") or "",
                "motivo": props.get("motivo") or "",
            }
        )
    if descartadas:
        log.error(
            "cargos: fichas con identificador personal; no vienen del BOE",
            descartadas=descartadas,
        )

    organos = organos_del_estado(store)
    # Y al revés: de cada órgano, quién lo dirigió. Es lo que la ficha de un
    # órgano del mapa del dinero enseña: quién estaba al frente cuando pagó.
    al_frente: dict[str, list[dict[str, Any]]] = {}

    salida = []
    for clave, persona in personas.items():
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
        salida.append({**persona, "periodos": [_serializable(p) for p in ps]})
    for lista in al_frente.values():
        lista.sort(key=lambda x: x.get("hasta") or x.get("desde") or "", reverse=True)

    def ultima(p: dict[str, Any]) -> str:
        return max((x.get("hasta") or x.get("desde") or "") for x in p["periodos"])

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
        "personas": salida,
        "organos": al_frente,
    }
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(documento, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    resumen = {
        "cargos_personas": len(salida),
        "cargos_actos": len(fechas),
        "cargos_organos": len(al_frente),
    }
    log.info("cargos exportados", destino=str(destino), **resumen)
    return resumen
