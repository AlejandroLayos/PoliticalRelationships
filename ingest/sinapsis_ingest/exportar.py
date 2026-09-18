"""Exporta el grafo a JSON estático.

Sirve para publicar sin base de datos: GitHub Actions ingiere contra un
Postgres efímero, exporta aquí, y el fichero resultante se sirve como un
activo más desde Vercel.

Tiene un límite claro y conviene decirlo: es una **instantánea**, no una
consulta viva. No escala a millones de aristas ni permite buscar en el
servidor. Para eso está la API (`backend/` o `api/`). Pero para publicar un
primer mapa real sin depender de nadie, es suficiente.

Lo que NO cambia: cada arista sigue llevando su `confidence` y su `status`, y
cada entidad su procedencia. Un formato más ligero no es excusa para perder lo
que hace auditable el proyecto.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from sinapsis_ingest.store import Store

log = structlog.get_logger()

# Cota del volcado. Por encima de esto el navegador sufre y la vista deja de
# ser útil: si hace falta más, lo que hace falta es la API, no un JSON mayor.
MAX_ENTIDADES = 4000

# El presupuesto que de verdad manda: se eligen aristas y los nodos salen de
# sus extremos. Ver el docstring de `exportar`.
MAX_ARISTAS = 6000


def exportar(
    store: Store,
    destino: Path,
    max_entidades: int = MAX_ENTIDADES,
    max_aristas: int = MAX_ARISTAS,
) -> dict[str, Any]:
    """Escribe el grafo en `destino`. Devuelve el resumen de lo exportado.

    Se eligen **aristas primero**, y los nodos salen de sus extremos.

    Antes era al revés: se cogían las N entidades de mayor grado y luego sólo
    las aristas con los dos extremos dentro. Suena razonable y destroza el
    grafo. Un nodo muy conectado entra, pero sus vecinos de grado 1 se quedan
    fuera del corte, así que sus aristas se caen y el nodo acaba suelto. El
    resultado medido sobre la instantánea del 3/8/2026: 4.000 nodos, 4.351
    aristas, **1.393 componentes conexas** y 548 nodos aislados *entre los más
    conectados de la base*. Un mapa de influencia troceado en 1.393 pedazos no
    enseña ninguna influencia.

    Eligiendo aristas primero eso no puede pasar: cada nodo publicado tiene al
    menos una arista y ninguna arista queda colgando. Se ordenan por importe
    porque el dinero es de lo que va esto; las que no lo llevan van después,
    por grado de sus extremos, para no perder el tejido que une los núcleos.
    """
    # Se recorren las aristas en orden de interés y se van tomando sus
    # extremos hasta agotar el presupuesto de nodos. Así el corte cae en el
    # borde del mapa y no por el medio.
    candidatas = store.conn.execute(
        """
        SELECT r.id, r.ftm_schema, r.source_entity_id, r.target_entity_id,
               r.amount, r.currency, r.confidence, r.status,
               r.start_date, r.end_date
        FROM relationships r
        JOIN entities es ON es.id = r.source_entity_id AND es.canonical_id IS NULL
        JOIN entities et ON et.id = r.target_entity_id AND et.canonical_id IS NULL
        WHERE r.status <> 'retracted'
        ORDER BY r.amount DESC NULLS LAST, r.id
        LIMIT %s
        """,
        (max_aristas * 4,),
    ).fetchall()

    elegidas = []
    ids_set: set[Any] = set()
    for a in candidatas:
        if len(elegidas) >= max_aristas:
            break
        nuevos = {a["source_entity_id"], a["target_entity_id"]} - ids_set
        if len(ids_set) + len(nuevos) > max_entidades:
            # Cabe todavía alguna arista entre nodos ya tomados: se sigue
            # mirando en vez de cortar en seco.
            continue
        ids_set |= nuevos
        elegidas.append(a)

    # Segunda pasada: el tejido conectivo.
    #
    # La primera ordena por importe, y eso deja fuera por construcción a las
    # aristas que no llevan dinero — entre ellas el enlace del órgano de
    # contratación con su contrato, que no lleva importe A PROPÓSITO para no
    # contar el mismo dinero dos veces. O sea que el criterio expulsaba
    # justamente lo que da cohesión al grafo, y el mapa volvía a salir en mil
    # pedazos pese a tener cero nodos aislados.
    #
    # Estas aristas son gratis: van entre nodos que YA están dentro, así que no
    # traen ningún nodo nuevo ni ensanchan el volcado. Sólo unen lo que ya hay.
    if ids_set:
        elegidas_ids = {a["id"] for a in elegidas}
        for a in store.conn.execute(
            """
            SELECT r.id, r.ftm_schema, r.source_entity_id, r.target_entity_id,
                   r.amount, r.currency, r.confidence, r.status,
                   r.start_date, r.end_date
            FROM relationships r
            WHERE r.status <> 'retracted'
              AND r.source_entity_id = ANY(%s)
              AND r.target_entity_id = ANY(%s)
            """,
            (list(ids_set), list(ids_set)),
        ).fetchall():
            if a["id"] not in elegidas_ids:
                elegidas.append(a)
                elegidas_ids.add(a["id"])

    ids = list(ids_set)
    aristas = [
        {
            "id": str(a["id"]),
            "schema": a["ftm_schema"],
            "source": str(a["source_entity_id"]),
            "target": str(a["target_entity_id"]),
            **({"amount": str(a["amount"])} if a["amount"] is not None else {}),
            **({"currency": a["currency"]} if a["currency"] else {}),
            # Nunca se omiten, ni aunque valgan lo esperable (invariante 5).
            "confidence": float(a["confidence"]),
            "status": a["status"],
            **({"start_date": a["start_date"].isoformat()} if a["start_date"] else {}),
            **({"end_date": a["end_date"].isoformat()} if a["end_date"] else {}),
        }
        for a in elegidas
    ]

    filas = (
        store.conn.execute(
            """
        SELECT e.id, e.ftm_schema, e.caption, COALESCE(e.nif,'') AS nif,
               COALESCE(e.country,'') AS country, e.properties,
               (SELECT count(*) FROM relationships r
                 WHERE (r.source_entity_id = e.id OR r.target_entity_id = e.id)
                   AND r.status <> 'retracted') AS grado
        FROM entities e
        WHERE e.id = ANY(%s)
        ORDER BY grado DESC, e.caption
        """,
            (ids,),
        ).fetchall()
        if ids
        else []
    )

    nodos = [
        {
            "id": str(f["id"]),
            "schema": f["ftm_schema"],
            "caption": f["caption"],
            **({"nif": f["nif"]} if f["nif"] else {}),
            **({"country": f["country"]} if f["country"] else {}),
            "properties": f["properties"] or {},
            "degree": int(f["grado"]),
        }
        for f in filas
    ]

    # Procedencia por entidad: es lo que permite volver al documento original
    # desde la interfaz, y sin ella el dato no debería publicarse.
    procedencia: dict[str, list[dict[str, Any]]] = {}
    if ids:
        for p in store.conn.execute(
            """
            SELECT p.entity_id, rd.source_id, rd.url, rd.content_hash,
                   rd.retrieved_at, p.extractor_version, COALESCE(p.excerpt,'') AS excerpt
            FROM provenance p
            JOIN raw_documents rd ON rd.id = p.raw_document_id
            WHERE p.entity_id = ANY(%s)
            ORDER BY rd.retrieved_at DESC
            """,
            (ids,),
        ).fetchall():
            procedencia.setdefault(str(p["entity_id"]), []).append(
                {
                    "source_id": p["source_id"],
                    "url": p["url"],
                    "content_hash": p["content_hash"],
                    "retrieved_at": p["retrieved_at"].isoformat(),
                    "extractor_version": p["extractor_version"],
                    **({"excerpt": p["excerpt"]} if p["excerpt"] else {}),
                }
            )

    total = store.conn.execute(
        "SELECT count(*) AS n FROM entities WHERE canonical_id IS NULL"
    ).fetchone()
    total_entidades = int(total["n"]) if total else 0

    fuentes = [
        dict(f)
        for f in store.conn.execute("SELECT id, name, url FROM sources ORDER BY id").fetchall()
    ]

    documento = {
        "generado": datetime.now(UTC).isoformat(),
        "instantanea": True,
        # Si se recortó, se dice. Un mapa incompleto que finge estar completo
        # miente, y aquí la mentira sería por omisión.
        "truncado": total_entidades > len(nodos),
        "total_entidades_en_base": total_entidades,
        "fuentes": fuentes,
        "nodes": nodos,
        "edges": aristas,
        "provenance": procedencia,
    }

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(documento, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    resumen = {
        "entidades": len(nodos),
        "aristas": len(aristas),
        "con_procedencia": len(procedencia),
        "truncado": documento["truncado"],
        "bytes": destino.stat().st_size,
    }
    log.info("grafo exportado", destino=str(destino), **resumen)
    return resumen
