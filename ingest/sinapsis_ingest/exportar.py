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
    # La selección crece POR EL GRAFO, no sólo por dinero. Tres pasadas.
    #
    # Sólo por importe no funciona, y costó dos intentos verlo. El enlace del
    # órgano de contratación con su contrato no lleva importe a propósito —el
    # dinero lo lleva la adjudicación y duplicarlo lo contaría dos veces—, así
    # que ordenando por importe ese enlace nunca entra. Y peor: el órgano de
    # PLACSP no tiene NINGUNA arista con dinero, sólo ese enlace, de modo que
    # tampoco entra él. Quedaban 129 organismos frente a 1.646 contratos, y el
    # grafo llegaba en 1.274 pedazos aunque ningún nodo estuviera aislado.
    #
    # Pedir que los dos extremos estuvieran ya dentro tampoco valía: es
    # circular, porque el órgano sólo puede entrar por esa misma arista.
    todas = store.conn.execute(
        """
        SELECT r.id, r.ftm_schema, r.source_entity_id, r.target_entity_id,
               r.amount, r.currency, r.confidence, r.status,
               r.start_date, r.end_date, r.properties
        FROM relationships r
        JOIN entities es ON es.id = r.source_entity_id AND es.canonical_id IS NULL
        JOIN entities et ON et.id = r.target_entity_id AND et.canonical_id IS NULL
        WHERE r.status <> 'retracted'
        ORDER BY r.amount DESC NULLS LAST, r.id
        """
    ).fetchall()

    elegidas: list[Any] = []
    ids_set: set[Any] = set()
    usadas: set[Any] = set()

    def cabe(a: Any, tope: int) -> bool:
        nuevos = {a["source_entity_id"], a["target_entity_id"]} - ids_set
        return len(ids_set) + len(nuevos) <= tope

    def tomar(a: Any) -> None:
        ids_set.update({a["source_entity_id"], a["target_entity_id"]})
        elegidas.append(a)
        usadas.add(a["id"])

    # 0. Los partidos, antes que nada.
    #
    # Ordenar por importe los expulsa del mapa, y se comprobó: al coser bien el
    # grafo entraron 456 organismos y desaparecieron LOS 179 partidos. Una
    # subvención electoral es calderilla al lado de un contrato de
    # infraestructuras, así que compitiendo por dinero un partido nunca gana.
    #
    # En un mapa de financiación política eso no es una pérdida aceptable: es
    # perder el sujeto. El dinero ordena el resto; los partidos entran por
    # derecho propio.
    partidos = {
        f["id"]
        for f in store.conn.execute(
            """
            SELECT id FROM entities
            WHERE canonical_id IS NULL
              AND (properties ->> 'partido_politico') = 'true'
            """
        ).fetchall()
    }
    if partidos:
        for a in todas:
            if len(elegidas) >= max_aristas:
                break
            toca_partido = a["source_entity_id"] in partidos or a["target_entity_id"] in partidos
            if toca_partido and a["id"] not in usadas and cabe(a, max_entidades):
                tomar(a)

    # 1. El esqueleto de dinero: lo más caro primero. Es un mapa de dinero.
    #
    # Pero NO se gasta todo el presupuesto de nodos aquí, y esto es lo que
    # faltaba. Tres ejecuciones seguidas dieron números idénticos al byte pese
    # a dos correcciones: la prueba estaba en que el volcado traía exactamente
    # 4.000 nodos, o sea el tope clavado. La primera pasada lo agotaba con
    # extremos de aristas caras y luego `cabe()` rechazaba TODA arista que
    # trajera un nodo nuevo, así que la pasada 2 no podía traerse ni un
    # organismo. Reservar sitio no es un ajuste fino: sin él la pasada 2 no
    # existe.
    # El suelo de 2 no es cosmético: con un presupuesto pequeño, el 75 % puede
    # quedarse por debajo de los dos nodos que necesita UNA arista, y entonces
    # no entra nada en absoluto. Lo destapó el test del volcado mínimo.
    reserva = max(2, int(max_entidades * 0.75))
    for a in todas:
        if len(elegidas) >= max_aristas:
            break
        if a["id"] not in usadas and cabe(a, reserva):
            tomar(a)

    # 2. Crecer por los bordes: aristas que tocan algo ya elegido. Aquí entran
    #    los organismos, colgando del contrato que adjudicaron.
    for a in todas:
        if len(elegidas) >= max_aristas:
            break
        if a["id"] in usadas:
            continue
        toca = a["source_entity_id"] in ids_set or a["target_entity_id"] in ids_set
        if toca and cabe(a, max_entidades):
            tomar(a)

    # 3. Coser: lo que va entre nodos que ya están dentro es gratis —no trae
    #    ningún nodo nuevo— y es lo que convierte fragmentos en núcleos.
    for a in todas:
        if a["id"] in usadas:
            continue
        if a["source_entity_id"] in ids_set and a["target_entity_id"] in ids_set:
            elegidas.append(a)
            usadas.add(a["id"])

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
            # Una arista sin importe puede serlo por dos motivos muy distintos:
            # porque la fuente no publicó cifra, o porque la ingesta no se creyó
            # la que publicó. La web tiene que poder decir cuál de los dos, y
            # para eso necesita las propiedades — ahí van `importeSinInterpretar`
            # y su motivo. Se omiten si están vacías para no engordar el volcado.
            **({"properties": a["properties"]} if a["properties"] else {}),
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

    # Cuánto aporta cada fuente AL VOLCADO, no cuántas hay registradas.
    #
    # Las tres fuentes se dan de alta antes de ingerir, así que la tabla dice
    # "bdns, placsp, tcu" aunque una de ellas no haya traído nada. El 18/9/2026
    # BDNS no respondió y la instantánea salió con el 100 % de la procedencia
    # en PLACSP: sin subvenciones, sin partidos, la mitad del mapa. Y el
    # cartel de la web seguía diciendo "datos reales de BDNS, PLACSP y TdC".
    #
    # Eso es mentir por omisión, que es justo lo que este proyecto no puede
    # hacer. Si una fuente falla se tolera el hueco, pero se DICE.
    aporte = (
        {
            f["source_id"]: int(f["n"])
            for f in store.conn.execute(
                """
            SELECT rd.source_id, count(DISTINCT p.entity_id) AS n
            FROM provenance p
            JOIN raw_documents rd ON rd.id = p.raw_document_id
            WHERE p.entity_id = ANY(%s)
            GROUP BY rd.source_id
            """,
                (ids,),
            ).fetchall()
        }
        if ids
        else {}
    )

    fuentes = [
        {**dict(f), "entidades": aporte.get(f["id"], 0)}
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
