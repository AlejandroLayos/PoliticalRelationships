"""Une conector y almacén: fetch → crudo → parse → normalize → upsert.

Todo lo que persiste pasa por aquí, y aquí es donde se hace cumplir el
invariante 1: cada entidad y cada arista se escriben junto con la procedencia
que las enlaza a su documento crudo, en la misma transacción. Si la procedencia
falla, el hecho no queda.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

from sinapsis_ingest.connectors.base import RawDocument
from sinapsis_ingest.store import Entity, Relationship, Store

log = structlog.get_logger()


@dataclass
class Resultado:
    """Recuento de una ejecución de ingesta."""

    documentos_nuevos: int = 0
    documentos_repetidos: int = 0
    entidades: int = 0
    aristas: int = 0
    registros_descartados: int = 0
    errores: list[str] = field(default_factory=list)

    def resumen(self) -> dict[str, Any]:
        return {
            "documentos_nuevos": self.documentos_nuevos,
            "documentos_repetidos": self.documentos_repetidos,
            "entidades": self.entidades,
            "aristas": self.aristas,
            "registros_descartados": self.registros_descartados,
            "errores": len(self.errores),
        }


def ingerir_documento(
    store: Store,
    conector: Any,
    raw: RawDocument,
    resultado: Resultado,
) -> None:
    """Persiste un documento crudo y todo lo que se derive de él."""
    doc_id, creado = store.upsert_raw_document(
        source_id=raw.source_id,
        url=raw.url,
        content=raw.content,
        content_hash=raw.content_hash,
        media_type=raw.media_type,
        retrieved_at=raw.retrieved_at,
        metadata=raw.metadata,
    )
    if creado:
        resultado.documentos_nuevos += 1
    else:
        resultado.documentos_repetidos += 1

    for registro in conector.parse(raw):
        normalizado = conector.normalize(registro)
        if normalizado is None:
            # El registro no traía lo imprescindible. No se rellena el hueco.
            resultado.registros_descartados += 1
            continue

        try:
            _persistir(store, doc_id, conector.extractor_version, normalizado, resultado)
        except Exception as exc:
            msg = f"registro {registro.data.get('cod_concesion', '?')}: {exc}"
            log.warning("no se pudo persistir un registro", error=str(exc))
            resultado.errores.append(msg)


def _persistir(
    store: Store,
    doc_id: str,
    extractor_version: str,
    normalizado: dict[str, Any],
    resultado: Resultado,
) -> None:
    """Escribe entidades, arista y procedencias en una sola transacción."""
    origen = normalizado["source_entity"]
    destino = normalizado["target_entity"]
    arista = normalizado["relationship"]

    with store.transaction():
        origen_id = store.upsert_entity(Entity(**origen))
        destino_id = store.upsert_entity(Entity(**destino))

        rel_id = store.upsert_relationship(
            Relationship(
                ftm_schema=arista["ftm_schema"],
                source_entity_id=origen_id,
                target_entity_id=destino_id,
                dedupe_key=arista["dedupe_key"],
                confidence=arista["confidence"],
                status=arista.get("status", "asserted"),
                amount=arista.get("amount"),
                currency=arista.get("currency", ""),
                start_date=arista.get("start_date"),
                end_date=arista.get("end_date"),
                properties=arista.get("properties", {}),
            )
        )

        # Invariante 1: la procedencia va en la misma transacción que el hecho.
        for entidad_id in (origen_id, destino_id):
            store.add_provenance(
                raw_document_id=doc_id,
                entity_id=entidad_id,
                extractor_version=extractor_version,
            )
        store.add_provenance(
            raw_document_id=doc_id,
            relationship_id=rel_id,
            extractor_version=extractor_version,
        )

    resultado.entidades += 2
    resultado.aristas += 1


def ejecutar(store: Store, conector: Any, **params: Any) -> Resultado:
    """Ejecuta un conector de principio a fin."""
    resultado = Resultado()
    log.info("ingesta iniciada", fuente=conector.source_id, params=str(params))

    for raw in conector.fetch(**params):
        ingerir_documento(store, conector, raw, resultado)

    log.info("ingesta terminada", fuente=conector.source_id, **resultado.resumen())
    return resultado
