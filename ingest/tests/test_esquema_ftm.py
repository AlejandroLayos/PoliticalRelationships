"""Verifica que la migración SQL usa nombres FollowTheMoney reales.

Las restricciones CHECK de `0001_init.up.sql` enumeran a mano los esquemas FtM
admitidos. Un nombre inventado, o un esquema de entidad colocado en la lista de
aristas, sólo se descubriría al fallar una ingesta en producción.

Este test cierra ese hueco: lee el SQL y contrasta cada nombre contra la
librería. Fue quien detectó que `Contract` es una entidad en FtM (el contrato
en sí) y no una arista — la arista es `ContractAward`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from followthemoney import model

MIGRACION = Path(__file__).resolve().parents[2] / "backend" / "migrations" / "0001_init.up.sql"


def _nombres_del_check(nombre_constraint: str) -> list[str]:
    """Extrae los literales de un `CONSTRAINT <nombre> CHECK (... IN (...))`."""
    sql = MIGRACION.read_text(encoding="utf-8")
    patron = rf"CONSTRAINT\s+{nombre_constraint}\s+CHECK\s*\(.*?IN\s*\((.*?)\)"
    match = re.search(patron, sql, re.DOTALL)
    if match is None:
        raise AssertionError(f"no encontré la restricción {nombre_constraint} en {MIGRACION}")
    return re.findall(r"'([^']+)'", match.group(1))


@pytest.fixture(scope="module")
def esquemas_entidad() -> list[str]:
    return _nombres_del_check("entities_ftm_schema_valido")


@pytest.fixture(scope="module")
def esquemas_arista() -> list[str]:
    return _nombres_del_check("relationships_ftm_schema_valido")


def test_la_migracion_existe():
    assert MIGRACION.is_file(), f"no existe {MIGRACION}"


def test_hay_esquemas_declarados(esquemas_entidad, esquemas_arista):
    assert len(esquemas_entidad) >= 8
    assert len(esquemas_arista) >= 10


@pytest.mark.parametrize("nombre", _nombres_del_check("entities_ftm_schema_valido"))
def test_esquema_de_entidad_existe_en_ftm(nombre: str):
    assert model.get(nombre) is not None, f"{nombre!r} no es un esquema FollowTheMoney"


@pytest.mark.parametrize("nombre", _nombres_del_check("entities_ftm_schema_valido"))
def test_esquema_de_entidad_no_es_arista(nombre: str):
    schema = model.get(nombre)
    assert schema is not None
    assert not schema.edge, (
        f"{nombre!r} es una arista en FtM (edge=True); no puede estar en entities.ftm_schema"
    )


@pytest.mark.parametrize("nombre", _nombres_del_check("relationships_ftm_schema_valido"))
def test_esquema_de_arista_existe_en_ftm(nombre: str):
    assert model.get(nombre) is not None, f"{nombre!r} no es un esquema FollowTheMoney"


@pytest.mark.parametrize("nombre", _nombres_del_check("relationships_ftm_schema_valido"))
def test_esquema_de_arista_es_arista(nombre: str):
    schema = model.get(nombre)
    assert schema is not None
    assert schema.edge, (
        f"{nombre!r} es una entidad en FtM (edge=False); no puede estar en relationships.ftm_schema"
    )


def test_sin_duplicados(esquemas_entidad, esquemas_arista):
    assert len(esquemas_entidad) == len(set(esquemas_entidad))
    assert len(esquemas_arista) == len(set(esquemas_arista))


def test_las_fuentes_del_plan_estan_cubiertas(esquemas_entidad, esquemas_arista):
    """Los esquemas que necesitan las fases 2-4 deben estar ya admitidos."""
    # BDNS: organismo (PublicBody) --Payment--> beneficiario (Company/Person)
    assert "PublicBody" in esquemas_entidad
    assert "Payment" in esquemas_arista
    # PLACSP: Contract --ContractAward--> adjudicatario
    assert "Contract" in esquemas_entidad
    assert "ContractAward" in esquemas_arista
    # Puertas giratorias: Person --Occupancy--> Position
    assert "Position" in esquemas_entidad
    assert "Occupancy" in esquemas_arista
