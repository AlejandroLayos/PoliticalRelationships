"""Registro de conectores disponibles.

El worker no importa conectores directamente: los pide aquí por nombre. Así
añadir una fuente nueva es registrarla en un sitio, y el worker puede listar
lo que sabe ejecutar sin conocer los módulos.
"""

from __future__ import annotations

from collections.abc import Callable

from sinapsis_ingest.connectors.base import Connector

_REGISTRY: dict[str, Callable[[], Connector]] = {}


def register(source_id: str, factory: Callable[[], Connector]) -> None:
    """Registra una fábrica de conector bajo `source_id`."""
    if source_id in _REGISTRY:
        raise ValueError(f"el conector {source_id!r} ya está registrado")
    _REGISTRY[source_id] = factory


def get(source_id: str) -> Connector:
    """Instancia el conector registrado como `source_id`."""
    try:
        factory = _REGISTRY[source_id]
    except KeyError:
        disponibles = ", ".join(sorted(_REGISTRY)) or "ninguno"
        raise KeyError(f"conector desconocido: {source_id!r}. Registrados: {disponibles}") from None
    return factory()


def available() -> list[str]:
    """Lista los `source_id` registrados, en orden alfabético."""
    return sorted(_REGISTRY)


def _reset_for_tests() -> None:
    """Vacía el registro. Sólo para tests."""
    _REGISTRY.clear()
