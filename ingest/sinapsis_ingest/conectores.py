"""Alta de los conectores disponibles.

El registro se puebla llamando a `registrar_todos()`, no como efecto lateral de
importar un paquete: un import con efectos es frágil y hace que el orden de los
imports cambie el comportamiento de los tests.

Ojo con la distinción: la **clave del registro** es el nombre del conector
(`bdns-partidos`), mientras que `source_id` es la fuente de la que salen los
datos (`bdns`). Varios conectores pueden compartir fuente.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sinapsis_ingest import registry
from sinapsis_ingest.connectors import bdns, placsp, tcu


@dataclass(frozen=True)
class FichaFuente:
    """Metadatos de una fuente, para darla de alta antes de ingerir."""

    id: str
    name: str
    url: str
    license: str


# Una entrada por `source_id`, no por conector.
FUENTES: dict[str, FichaFuente] = {
    "bdns": FichaFuente(
        id="bdns",
        name="Base de Datos Nacional de Subvenciones",
        url="https://www.infosubvenciones.es",
        license="Reutilización libre (Ley 37/2007)",
    ),
    "placsp": FichaFuente(
        id="placsp",
        name="Plataforma de Contratación del Sector Público",
        url="https://contrataciondelestado.es",
        license="Reutilización libre (Ley 37/2007)",
    ),
    "tcu": FichaFuente(
        id="tcu",
        name="Tribunal de Cuentas",
        url="https://www.tcu.es",
        license="Reutilización libre (Ley 37/2007)",
    ),
}

_CONECTORES: dict[str, Any] = {
    "bdns": bdns.crear,
    "bdns-partidos": bdns.crear_partidos,
    "placsp": placsp.crear,
    "tcu": tcu.crear,
}


def registrar_todos() -> None:
    """Registra todos los conectores. Idempotente."""
    for nombre, fabrica in _CONECTORES.items():
        if nombre not in registry.available():
            registry.register(nombre, fabrica)


def ficha(source_id: str) -> FichaFuente:
    """Devuelve los metadatos de una fuente."""
    try:
        return FUENTES[source_id]
    except KeyError:
        raise KeyError(f"fuente sin ficha: {source_id!r}") from None
