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
from sinapsis_ingest.normalizado import Normalizado
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
        if normalizado is None or not normalizado.aristas:
            # El registro no traía lo imprescindible. No se rellena el hueco.
            resultado.registros_descartados += 1
            continue

        try:
            normalizado.validar()
            _persistir(store, doc_id, conector.extractor_version, normalizado, resultado)
        except Exception as exc:
            ref = registro.data.get("id_registro", "?")
            log.warning("no se pudo persistir un registro", ref=ref, error=str(exc))
            resultado.errores.append(f"registro {ref}: {exc}")


def _persistir(
    store: Store,
    doc_id: str,
    extractor_version: str,
    n: Normalizado,
    resultado: Resultado,
) -> None:
    """Escribe entidades, aristas y procedencias en una sola transacción."""
    with store.transaction():
        # Las aristas referencian entidades por dedupe_key; aquí se traduce a
        # los ids que asigna la base de datos.
        ids: dict[str, str] = {}
        for e in n.entidades:
            ids[e.dedupe_key] = store.upsert_entity(
                Entity(
                    ftm_schema=e.ftm_schema,
                    caption=e.caption,
                    dedupe_key=e.dedupe_key,
                    nif=e.nif,
                    country=e.country,
                    properties=e.properties,
                )
            )

        rel_ids: list[str] = []
        for a in n.aristas:
            rel_ids.append(
                store.upsert_relationship(
                    Relationship(
                        ftm_schema=a.ftm_schema,
                        source_entity_id=ids[a.source_key],
                        target_entity_id=ids[a.target_key],
                        dedupe_key=a.dedupe_key,
                        confidence=a.confidence,
                        status=a.status,
                        amount=a.amount,
                        currency=a.currency,
                        start_date=a.start_date,
                        end_date=a.end_date,
                        properties=a.properties,
                    )
                )
            )

        # Invariante 1: la procedencia va en la misma transacción que el hecho.
        for entidad_id in ids.values():
            store.add_provenance(
                raw_document_id=doc_id,
                entity_id=entidad_id,
                extractor_version=extractor_version,
            )
        for rel_id in rel_ids:
            store.add_provenance(
                raw_document_id=doc_id,
                relationship_id=rel_id,
                extractor_version=extractor_version,
            )

    resultado.entidades += len(ids)
    resultado.aristas += len(rel_ids)


def ejecutar(store: Store, conector: Any, **params: Any) -> Resultado:
    """Ejecuta un conector de principio a fin."""
    resultado = Resultado()
    log.info("ingesta iniciada", fuente=conector.source_id, params=str(params))

    for raw in conector.fetch(**params):
        ingerir_documento(store, conector, raw, resultado)

    log.info("ingesta terminada", fuente=conector.source_id, **resultado.resumen())
    return resultado
