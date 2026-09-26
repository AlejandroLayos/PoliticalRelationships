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
from sinapsis_ingest.connectors import bdns, boe, cnmv, congreso, oci, placsp, senado, tcu


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
    "boe": FichaFuente(
        id="boe",
        name="Boletín Oficial del Estado",
        url="https://www.boe.es",
        license="Reutilización libre (Ley 37/2007; aviso legal del BOE)",
    ),
    "congreso": FichaFuente(
        id="congreso",
        name="Congreso de los Diputados",
        url="https://www.congreso.es/es/opendata/diputados",
        license="Datos abiertos del Congreso; reutilización libre (Ley 37/2007)",
    ),
    "senado": FichaFuente(
        id="senado",
        name="Senado",
        url="https://www.senado.es/web/relacionesciudadanos/datosabiertos/catalogodatos/index.html",
        license="Datos abiertos del Senado; reutilización libre (Ley 37/2007)",
    ),
    "cnmv": FichaFuente(
        id="cnmv",
        name="Comisión Nacional del Mercado de Valores",
        url="https://www.cnmv.es/portal/Consultas/busqueda.aspx?id=7",
        license="Registros oficiales de la CNMV; reutilización libre (Ley 37/2007)",
    ),
    "oci": FichaFuente(
        id="oci",
        name="Oficina de Conflictos de Intereses",
        url="https://transparencia.gob.es/publicidad-activa/por-materias/altos-cargos/actividad-privada-cese",
        license="Publicidad activa (Ley 19/2013); reutilización libre (Ley 37/2007)",
    ),
}

_CONECTORES: dict[str, Any] = {
    "bdns": bdns.crear,
    "bdns-partidos": bdns.crear_partidos,
    "placsp": placsp.crear,
    # La Plataforma publica tres feeds y hasta ahora sólo se leía uno.
    # `agregadas` trae lo que vuelcan las plataformas autonómicas; todo lo que
    # se publica directamente en la Plataforma del Estado, y todo el contrato
    # menor —donde vive el gasto municipal del día a día— quedaba fuera.
    "placsp-licitaciones": placsp.crear_licitaciones,
    "placsp-menores": placsp.crear_menores,
    "tcu": tcu.crear,
    # Altos cargos por Real Decreto. Sólo guarda lo que es alto cargo: ver
    # la regla de personas de la spec (§12) y `cargos.py`.
    "boe": boe.crear,
    # Autorizaciones de actividad privada tras el cese: la fuente que afirma
    # las puertas giratorias (§12).
    "oci": oci.crear,
    # Diputados por legislatura, con su formación: el partido, para el
    # contexto de gobierno (fase 7, línea 4).
    "congreso": congreso.crear,
    # Los partidos de cada legislatura con sus siglas: el puente oficial entre
    # la formación de un diputado y el partido del mapa del dinero.
    "senado": senado.crear,
    # Accionistas significativos de las cotizadas y sus participaciones: la
    # red empresarial (spec §12, ampliación del 26/9/2026).
    "cnmv": cnmv.crear,
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
