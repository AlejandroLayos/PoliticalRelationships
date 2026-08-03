"""Golden test del parser de BDNS contra una respuesta **real** de la API.

Se salta mientras no exista la captura. Para generarla, desde una máquina con
salida a internet:

    python scripts/capturar_muestra_bdns.py \\
        --salida ingest/tests/golden/bdns_concesiones_real.json

Mientras este test esté saltándose, el parser está probado contra una muestra
sintética y **no verificado contra el formato real de BDNS**.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from sinapsis_ingest.connectors.base import RawDocument
from sinapsis_ingest.connectors.bdns import BDNSConnector

MUESTRA_REAL = Path(__file__).parent / "golden" / "bdns_concesiones_real.json"

pytestmark = pytest.mark.skipif(
    not MUESTRA_REAL.is_file(),
    reason=(
        "falta ingest/tests/golden/bdns_concesiones_real.json; "
        "genérala con scripts/capturar_muestra_bdns.py"
    ),
)


@pytest.fixture
def crudo() -> RawDocument:
    return RawDocument(
        source_id="bdns",
        url="https://www.infosubvenciones.es/bdnstrans/api/concesiones/busqueda",
        content=MUESTRA_REAL.read_bytes(),
        media_type="application/json",
        retrieved_at=datetime.now(UTC),
    )


def test_la_muestra_real_tiene_la_envoltura_esperada():
    datos = json.loads(MUESTRA_REAL.read_bytes())
    assert "content" in datos, "la respuesta real ya no trae 'content': el formato cambió"
    assert isinstance(datos["content"], list)
    assert "totalPages" in datos, "la respuesta real ya no trae 'totalPages'"


def test_el_parser_extrae_algo_de_la_muestra_real(crudo):
    registros = list(BDNSConnector(peticiones_por_segundo=0).parse(crudo))
    assert registros, "el parser no sacó ninguna concesión de una respuesta real"


def test_los_campos_clave_estan_presentes_en_la_muestra_real(crudo):
    """Si BDNS renombra un campo, esto lo caza antes de que la ingesta calle."""
    registros = list(BDNSConnector(peticiones_por_segundo=0).parse(crudo))

    con_beneficiario = [r for r in registros if r.data.get("beneficiario")]
    assert con_beneficiario, "ninguna concesión real trae 'beneficiario'"

    con_importe = [r for r in registros if r.data.get("importe") is not None]
    assert con_importe, "ninguna concesión real trae 'importe'"
    assert all(isinstance(r.data["importe"], Decimal) for r in con_importe)

    con_organo = [r for r in registros if r.data.get("organo")]
    assert con_organo, "ninguna concesión real trae jerarquía de órgano (nivel1..3)"

    con_fecha = [r for r in registros if r.data.get("fecha_concesion") is not None]
    assert con_fecha, "ninguna fecha real se pudo parsear: revisa el formato"


def test_normalize_produce_aristas_validas_desde_la_muestra_real(crudo):
    conector = BDNSConnector(peticiones_por_segundo=0)
    normalizados = [n for r in conector.parse(crudo) if (n := conector.normalize(r)) is not None]
    assert normalizados, "ninguna concesión real llegó a producir una arista"

    for n in normalizados:
        rel = n.aristas[0]
        assert rel.ftm_schema == "Payment"
        assert 0.0 <= rel.confidence <= 1.0
        assert rel.status == "asserted"
        # El esquema rechaza importes sin moneda.
        if rel.amount is not None:
            assert rel.currency == "EUR"
        assert n.entidades[0].ftm_schema == "PublicBody"
