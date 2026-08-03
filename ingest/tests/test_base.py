"""Tests del contrato común de conectores."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sinapsis_ingest.connectors.base import ParsedRecord, RawDocument


def _doc(content: bytes = b'{"a": 1}') -> RawDocument:
    return RawDocument(
        source_id="prueba",
        url="https://ejemplo.test/recurso",
        content=content,
        media_type="application/json",
    )


def test_content_hash_es_sha256_del_contenido():
    doc = _doc(b"contenido literal")
    assert doc.content_hash == hashlib.sha256(b"contenido literal").hexdigest()


def test_content_hash_es_estable_entre_instancias():
    # La idempotencia de la ingesta depende de esto: mismos bytes, mismo hash,
    # aunque cambien la hora de descarga y los metadatos de la petición.
    a = RawDocument(
        source_id="prueba",
        url="https://ejemplo.test/x",
        content=b"iguales",
        media_type="application/json",
        retrieved_at=datetime(2020, 1, 1, tzinfo=UTC),
        metadata={"pagina": 1},
    )
    b = RawDocument(
        source_id="prueba",
        url="https://ejemplo.test/y",
        content=b"iguales",
        media_type="text/plain",
        retrieved_at=datetime(2026, 8, 3, tzinfo=UTC),
        metadata={"pagina": 99},
    )
    assert a.content_hash == b.content_hash


def test_content_hash_cambia_con_el_contenido():
    assert _doc(b"uno").content_hash != _doc(b"dos").content_hash


def test_raw_document_es_inmutable():
    # Invariante 2: el crudo no se edita nunca.
    doc = _doc()
    try:
        doc.content = b"otra cosa"  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("RawDocument debería ser inmutable")


def test_retrieved_at_tiene_zona_horaria():
    # Sin tzinfo, comparar fechas de fuentes distintas es una fuente de bugs.
    assert _doc().retrieved_at.tzinfo is not None


def test_parsed_record_enlaza_con_el_crudo():
    doc = _doc()
    record = ParsedRecord(
        raw_content_hash=doc.content_hash,
        extractor_version="prueba/1",
        data={"campo": "valor"},
    )
    assert record.raw_content_hash == doc.content_hash
    assert record.extractor_version == "prueba/1"
