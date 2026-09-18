"""Tests de la detección de capital extranjero.

Se apoya en la letra inicial del NIF, que la Orden EHA/451/2008 define: N para
entidades extranjeras y W para establecimientos permanentes de no residentes.

Deducirlo del nombre —"Gmbh", "Ltd", "Inc"— sería mucho más frágil: hay
empresas españolas con nombre inglés y filiales extranjeras con nombre
español. La letra del NIF es la Agencia Tributaria afirmándolo; el sufijo del
nombre seríamos nosotros suponiéndolo.

Por eso, cuando el nombre es lo único que hay —adjudicatarios SIN NIF, que en
los datos reales son justamente los proveedores extranjeros—, lo que se
publica es un **indicio** en una propiedad aparte, nunca la misma afirmación
que hace un NIF.
"""

from __future__ import annotations

import pytest

from sinapsis_ingest.util import (
    es_entidad_extranjera,
    motivo_extranjera,
    propiedades_extranjera,
)


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


# --- indicio por forma societaria -----------------------------------------
#
# Hay adjudicatarios SIN NIF ninguno, y no por casualidad: son los proveedores
# extranjeros, que no tienen por qué tener uno. En la instantánea del
# 18/9/2026 eran siete cobrando de administraciones españolas sin aparecer en
# el filtro de capital extranjero.


class TestIndicioPorForma:
    @pytest.mark.parametrize(
        "nombre",
        [
            "META PLATFORMS IRELAND LIMITED",
            "VOESTALPINE RAIL TECHNOLOGY GMBH",
            "NOVOGENE UK COMPANY LIMITED",
            "Reed Exhibitions Ltd.",
            "BIOCRYST IRELAND LIMITED",
            "Franklyn Health Ltd",
            "TOPCON EUROPE MEDICAL B.V.",
            "BAVARIAN NORDIC A/S",
        ],
        ids=lambda n: n[:24],
    )
    def test_sin_nif_y_con_forma_extranjera_al_final(self, nombre):
        props = propiedades_extranjera(None, nombre)
        assert props["entidad_extranjera_indicio"] is True
        # Un indicio nunca se publica como lo que afirma un NIF.
        assert "entidad_extranjera" not in props
        assert "sin NIF" in props["motivo_extranjera_indicio"]

    @pytest.mark.parametrize(
        "nombre",
        [
            # La forma va al principio: es parte del nombre comercial, no el
            # tipo de sociedad. Esta empresa es española (A08736431).
            "AB MEDICA GROUP",
            # Las siglas contienen "S.P.A" por dentro; es una asociación
            # española de familias de personas sordas.
            "ASOC PROV DE FAMILIAS Y AMIGOS DE PERSONAS SORDAS A.S.P.A.S.",
            "CONSTRUCCIONES Y REFORMAS, S.L.",
            "EMOCIONA SOLUCIONES CREATIVAS, S.L.L.",
            "Servicio Andaluz de Salud",
            "UTE HARQUITECTES AREA PRODUCTIVA, SLP",
            "",
            None,
        ],
        ids=lambda n: (n or "vacío")[:28],
    )
    def test_no_se_marca_lo_que_no_toca(self, nombre):
        assert propiedades_extranjera(None, nombre) == {}

    def test_con_nif_manda_el_nif_aunque_el_nombre_suene_extranjero(self):
        # Deducir por el nombre teniendo el dato oficial delante sería
        # sustituir una fuente por una corazonada.
        assert propiedades_extranjera("B12345678", "Something Holdings Ltd") == {}

    def test_un_nif_de_no_residente_sigue_siendo_prueba_no_indicio(self):
        props = propiedades_extranjera("N0012345H", "CIPLA EUROPE NV SUCURSAL EN ESPAÑA")
        assert props["entidad_extranjera"] is True
        assert "entidad_extranjera_indicio" not in props

    def test_el_indicio_no_depende_de_llamar_sin_nombre(self):
        # La firma vieja —sólo NIF— sigue funcionando igual para quien no
        # tenga el nombre a mano.
        assert propiedades_extranjera("B12345678") == {}
        assert propiedades_extranjera("N0012345H")["entidad_extranjera"] is True
