"""Acceso a Postgres desde los workers de ingesta.

Es el gemelo en Python de `backend/internal/store`. No comparten código —Go y
Python sólo se comunican por la base de datos— así que el **esquema SQL es el
contrato**, y las mismas reglas de idempotencia se implementan a los dos lados.

Si cambias un upsert aquí, mira si el equivalente en Go necesita el mismo
cambio: ningún compilador te lo va a avisar.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import psycopg
from psycopg.rows import dict_row


@dataclass
class Source:
    id: str
    name: str
    url: str = ""
    license: str = ""
    description: str = ""


@dataclass
class Entity:
    """Nodo del grafo, con vocabulario FollowTheMoney."""

    ftm_schema: str
    caption: str
    dedupe_key: str
    nif: str = ""
    country: str = ""
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Relationship:
    """Arista del grafo.

    `amount` va como Decimal y nunca como float: el importe es el dato que da
    sentido al proyecto y un redondeo binario lo corrompería en silencio.
    """

    ftm_schema: str
    source_entity_id: str
    target_entity_id: str
    dedupe_key: str
    confidence: float
    status: str = "asserted"
    amount: Decimal | None = None
    currency: str = ""
    start_date: date | None = None
    end_date: date | None = None
    properties: dict[str, Any] = field(default_factory=dict)


class Store:
    """Conexión a la verdad canónica."""

    def __init__(self, dsn: str):
        self._dsn = dsn
        self._conn: psycopg.Connection | None = None

    def __enter__(self) -> Store:
        self._conn = psycopg.connect(self._dsn, row_factory=dict_row)
        return self

    def __exit__(self, *exc: object) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> psycopg.Connection:
        if self._conn is None:
            raise RuntimeError("Store sin abrir: úsalo como context manager")
        return self._conn

    @contextmanager
    def transaction(self) -> Iterator[psycopg.Connection]:
        with self.conn.transaction():
            yield self.conn

    # --- fuentes ----------------------------------------------------------

    def upsert_source(self, src: Source) -> None:
        self.conn.execute(
            """
            INSERT INTO sources (id, name, url, license, description)
            VALUES (%s, %s, NULLIF(%s,''), NULLIF(%s,''), NULLIF(%s,''))
            ON CONFLICT (id) DO UPDATE SET
                name        = EXCLUDED.name,
                url         = EXCLUDED.url,
                license     = EXCLUDED.license,
                description = EXCLUDED.description
            """,
            (src.id, src.name, src.url, src.license, src.description),
        )

    # --- documentos crudos ------------------------------------------------

    def upsert_raw_document(
        self,
        *,
        source_id: str,
        url: str,
        content: bytes,
        content_hash: str,
        media_type: str,
        retrieved_at: datetime,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[str, bool]:
        """Guarda un documento crudo. Devuelve (id, creado).

        No usa ON CONFLICT DO UPDATE a propósito: `raw_documents` tiene un
        trigger que rechaza cualquier UPDATE, así que un DO UPDATE —aunque
        fuera un no-op para recuperar el RETURNING— reventaría.
        """
        row = self.conn.execute(
            """
            INSERT INTO raw_documents
                (source_id, url, content, content_hash, media_type, retrieved_at, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_id, content_hash) DO NOTHING
            RETURNING id
            """,
            (
                source_id,
                url,
                content,
                content_hash,
                media_type,
                retrieved_at,
                json.dumps(metadata or {}),
            ),
        ).fetchone()

        if row is not None:
            return str(row["id"]), True

        existente = self.conn.execute(
            "SELECT id FROM raw_documents WHERE source_id = %s AND content_hash = %s",
            (source_id, content_hash),
        ).fetchone()
        if existente is None:  # pragma: no cover - no debería ocurrir
            raise RuntimeError(f"documento {content_hash} ni insertado ni encontrado")
        return str(existente["id"]), False

    # --- entidades y aristas ----------------------------------------------

    def upsert_entity(self, e: Entity) -> str:
        """Inserta o actualiza por dedupe_key. Devuelve el id.

        Las properties se fusionan (`||`) en vez de sustituirse: dos fuentes
        aportan campos distintos de la misma entidad y la segunda ingesta no
        debe borrar lo que trajo la primera.
        """
        if not e.dedupe_key:
            raise ValueError("la entidad necesita dedupe_key")

        row = self.conn.execute(
            """
            INSERT INTO entities (ftm_schema, caption, properties, nif, country, dedupe_key)
            VALUES (%s, %s, %s, NULLIF(%s,''), NULLIF(%s,''), %s)
            ON CONFLICT (dedupe_key) DO UPDATE SET
                caption    = EXCLUDED.caption,
                properties = entities.properties || EXCLUDED.properties,
                nif        = COALESCE(entities.nif, EXCLUDED.nif),
                country    = COALESCE(entities.country, EXCLUDED.country)
            RETURNING id
            """,
            (
                e.ftm_schema,
                e.caption,
                json.dumps(e.properties),
                e.nif,
                e.country,
                e.dedupe_key,
            ),
        ).fetchone()
        assert row is not None
        return str(row["id"])

    def upsert_relationship(self, r: Relationship) -> str:
        if not r.dedupe_key:
            raise ValueError("la arista necesita dedupe_key")

        row = self.conn.execute(
            """
            INSERT INTO relationships (
                ftm_schema, source_entity_id, target_entity_id, properties,
                start_date, end_date, amount, currency, confidence, status, dedupe_key
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NULLIF(%s,''), %s, %s, %s)
            ON CONFLICT (dedupe_key) DO UPDATE SET
                properties = relationships.properties || EXCLUDED.properties,
                start_date = COALESCE(EXCLUDED.start_date, relationships.start_date),
                end_date   = COALESCE(EXCLUDED.end_date,   relationships.end_date),
                amount     = COALESCE(EXCLUDED.amount,     relationships.amount),
                currency   = COALESCE(EXCLUDED.currency,   relationships.currency),
                confidence = EXCLUDED.confidence,
                status     = EXCLUDED.status
            RETURNING id
            """,
            (
                r.ftm_schema,
                r.source_entity_id,
                r.target_entity_id,
                json.dumps(r.properties),
                r.start_date,
                r.end_date,
                r.amount,
                r.currency,
                r.confidence,
                r.status,
                r.dedupe_key,
            ),
        ).fetchone()
        assert row is not None
        return str(row["id"])

    # --- procedencia ------------------------------------------------------

    def add_provenance(
        self,
        *,
        raw_document_id: str,
        extractor_version: str,
        entity_id: str | None = None,
        relationship_id: str | None = None,
        excerpt: str = "",
    ) -> None:
        """Invariante 1: sin esto, el hecho no debería existir."""
        if not raw_document_id:
            raise ValueError("un hecho no se persiste sin procedencia")
        if bool(entity_id) == bool(relationship_id):
            raise ValueError(
                "la procedencia apunta a una entidad o a una arista, no a ambas ni a ninguna"
            )

        self.conn.execute(
            """
            INSERT INTO provenance
                (raw_document_id, entity_id, relationship_id, extractor_version, excerpt)
            VALUES (%s, %s, %s, %s, NULLIF(%s,''))
            ON CONFLICT DO NOTHING
            """,
            (raw_document_id, entity_id, relationship_id, extractor_version, excerpt),
        )
