"""Interfaz común a todos los conectores de fuentes.

Un conector recorre siempre las mismas tres etapas, y la separación entre
ellas no es decorativa: es lo que hace que el crudo sea reprocesable.

    fetch     -> descarga bytes de la fuente. No interpreta nada.
    parse     -> convierte esos bytes en registros estructurados.
    normalize -> convierte los registros en entidades y aristas FollowTheMoney.

`fetch` devuelve documentos crudos que se persisten tal cual y nunca se
editan (invariante 2). `parse` lleva un `extractor_version` para que, cuando
arreglemos un parser, se pueda recomputar todo lo derivado desde el crudo ya
guardado sin volver a golpear la fuente.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class RawDocument:
    """Un documento tal y como lo devolvió la fuente, sin interpretar.

    `content_hash` es la clave de idempotencia: reejecutar una ingesta que
    devuelve los mismos bytes no crea una fila nueva (invariante 3).
    """

    source_id: str
    """Identificador del conector que lo trajo, p. ej. "bdns"."""

    url: str
    """URL exacta de la que salió, para poder auditarlo."""

    content: bytes
    """Bytes literales de la respuesta."""

    media_type: str
    """Tipo MIME declarado por la fuente."""

    retrieved_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    metadata: dict[str, Any] = field(default_factory=dict)
    """Contexto de la petición (parámetros de paginación, cabeceras
    relevantes). Útil para reproducir la descarga."""

    @property
    def content_hash(self) -> str:
        """SHA-256 hex de `content`."""
        return hashlib.sha256(self.content).hexdigest()


@dataclass(frozen=True)
class ParsedRecord:
    """Un registro estructurado extraído de un RawDocument."""

    raw_content_hash: str
    """Enlaza con el crudo del que salió. Sin esto no hay procedencia."""

    extractor_version: str
    """Versión del parser que lo produjo. Al cambiarla se recomputa."""

    data: dict[str, Any]
    """Campos ya tipados pero todavía en el vocabulario de la fuente."""


class Connector(Protocol):
    """Contrato que implementa cada fuente."""

    source_id: str
    extractor_version: str

    def fetch(self, **params: Any) -> Iterator[RawDocument]:
        """Descarga de la fuente, paginando si hace falta."""
        ...

    def parse(self, raw: RawDocument) -> Iterator[ParsedRecord]:
        """Extrae registros del crudo. Debe ser una función pura de
        (bytes, extractor_version) para que los golden tests tengan sentido."""
        ...

    def normalize(self, record: ParsedRecord) -> Iterator[Any]:
        """Traduce un registro al vocabulario FollowTheMoney."""
        ...
