"""Tests de la detección de capital extranjero.

Se apoya en la letra inicial del NIF, que la Orden EHA/451/2008 define: N para
entidades extranjeras y W para establecimientos permanentes de no residentes.

Deducirlo del nombre —"Gmbh", "Ltd", "Inc"— sería mucho más frágil: hay
empresas españolas con nombre inglés y filiales extranjeras con nombre
español. La letra del NIF es la Agencia Tributaria afirmándolo; el sufijo del
nombre seríamos nosotros suponiéndolo.
"""

from __future__ import annotations

import pytest

from sinapsis_ingest.util import es_entidad_extranjera, motivo_extranjera


@pytest.mark.parametrize("nif", ["N0080317A", "W0172868B", "w8263042g", "n1234567a"])
def test_reconoce_a_las_no_residentes(nif):
    assert es_entidad_extranjera(nif)


@pytest.mark.parametrize(
    "nif",
    [
        "A28526275",  # sociedad anónima española
        "B12345678",  # sociedad limitada española
        "G41091570",  # asociación española
        "12345678Z",  # DNI
        "X1234567L",  # NIE: persona física extranjera, no una entidad
        "",
        None,
    ],
)
def test_no_marca_lo_que_no_toca(nif):
    assert not es_entidad_extranjera(nif)


def test_el_nie_no_es_una_entidad_extranjera():
    """Un NIE es una persona física.

    Importa mantenerlo separado: una persona física recibe el trato de
    minimización de datos personales sea de donde sea, y lo que interesa del
    extranjero es el capital, no quién.
    """
    assert not es_entidad_extranjera("Z4420824E")
    assert "persona física" in motivo_extranjera("Z4420824E")


def test_siempre_se_puede_decir_por_que():
    """Sin procedencia no se afirma nada, tampoco esto."""
    assert motivo_extranjera("N0080317A") == "NIF de entidad extranjera (letra N)"
    assert "no residente" in motivo_extranjera("W0172868B")
    assert motivo_extranjera("A28526275") == ""
    assert motivo_extranjera(None) == ""
