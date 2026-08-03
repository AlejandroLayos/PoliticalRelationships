"""Alta de los conectores disponibles.

El registro se puebla llamando a `registrar_todos()`, no como efecto lateral de
importar un paquete: un import con efectos es frágil y hace que el orden de los
imports cambie el comportamiento de los tests.
"""

from __future__ import annotations

from sinapsis_ingest import registry
from sinapsis_ingest.connectors import bdns


def registrar_todos() -> None:
    """Registra todos los conectores. Idempotente."""
    for source_id, fabrica in ((bdns.SOURCE_ID, bdns.crear),):
        if source_id not in registry.available():
            registry.register(source_id, fabrica)
