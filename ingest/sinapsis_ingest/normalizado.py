"""Forma que devuelve `Connector.normalize`.

Un registro de una fuente puede producir **varias** entidades y **varias**
aristas: un contrato público tiene un órgano, un expediente y N adjudicatarios
si se reparte en lotes o lo gana una UTE. Modelarlo como una sola tripleta
origen-arista-destino obligaría a inventar registros o a perder adjudicatarios,
y las dos cosas están prohibidas.

Las aristas referencian entidades por su `dedupe_key`, no por id: el conector
no conoce los ids, que los asigna la base de datos. El pipeline resuelve las
claves después de insertar las entidades.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any


@dataclass
class EntidadNormalizada:
    ftm_schema: str
    caption: str
    dedupe_key: str
    nif: str = ""
    country: str = ""
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class AristaNormalizada:
    ftm_schema: str
    source_key: str
    """`dedupe_key` de la entidad origen."""
    target_key: str
    """`dedupe_key` de la entidad destino."""
    dedupe_key: str
    confidence: float
    status: str = "asserted"
    amount: Decimal | None = None
    currency: str = ""
    start_date: date | None = None
    end_date: date | None = None
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Normalizado:
    """Lo que un registro aporta al grafo."""

    entidades: list[EntidadNormalizada] = field(default_factory=list)
    aristas: list[AristaNormalizada] = field(default_factory=list)

    def claves_de_entidad(self) -> set[str]:
        return {e.dedupe_key for e in self.entidades}

    def validar(self) -> None:
        """Comprueba que las aristas referencian entidades que se van a crear.

        Una arista que apunta a una clave inexistente sería una violación de
        integridad referencial detectada tarde y con un error opaco de
        Postgres; aquí sale con el nombre de la clave que falta.
        """
        claves = self.claves_de_entidad()
        for a in self.aristas:
            for extremo, clave in (("origen", a.source_key), ("destino", a.target_key)):
                if clave not in claves:
                    raise ValueError(
                        f"la arista {a.dedupe_key!r} referencia como {extremo} la clave "
                        f"{clave!r}, que no está entre las entidades normalizadas"
                    )
