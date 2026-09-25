"""El nivel y el territorio de un organismo salen de lo que publica la fuente.

Las jerarquías de PLACSP de estos tests salen de su árbol de organismos y de la
muestra real (`golden/placsp_agregadas_muestra.atom`). Las de BDNS siguen la
forma de la muestra sintética, a falta de una real (ver golden/README.md): si
la API las publica de otra manera, esos organismos saldrán «sin clasificar» y
lo dirá el informe del volcado, que es lo que tiene que pasar.
"""

from __future__ import annotations

import pytest

from sinapsis_ingest.territorio import (
    Clasificacion,
    clasificar,
    clasificar_entidad,
    plataforma_de,
)


@pytest.mark.parametrize(
    ("jerarquia", "esperado"),
    [
        # La muestra real: un ayuntamiento catalán.
        (["Entitats municipals de Catalunya"], Clasificacion("local", "Cataluña", "jerarquia")),
        (
            ["COMUNIDADES Y CIUDADES AUTÓNOMAS", "Andalucía", "Consejería de Salud"],
            Clasificacion("autonomico", "Andalucía", "jerarquia"),
        ),
        (
            ["ENTIDADES LOCALES", "Castilla y León", "León"],
            Clasificacion("local", "Castilla y León", "jerarquia"),
        ),
        (
            ["ADMINISTRACIÓN GENERAL DEL ESTADO", "MINISTERIO DE HACIENDA"],
            Clasificacion("estatal", None, None),
        ),
        # Forma de BDNS: el primer nivel dice el nivel, el segundo la provincia.
        (["LOCAL", "SEVILLA"], Clasificacion("local", "Andalucía", "jerarquia")),
        (["ESTADO", "MINISTERIO DE CULTURA"], Clasificacion("estatal", None, None)),
        # Colgado de una comunidad sin más marca: es de la comunidad.
        (
            ["ANDALUCÍA", "CONSEJERÍA DE SALUD"],
            Clasificacion("autonomico", "Andalucía", "jerarquia"),
        ),
    ],
)
def test_la_jerarquia_de_la_fuente_dice_nivel_y_territorio(jerarquia, esperado):
    assert clasificar(jerarquia) == esperado


def test_un_organismo_del_estado_no_tiene_comunidad_aunque_la_nombre():
    # Una delegación del Estado en una comunidad sigue siendo del Estado.
    c = clasificar(["ADMINISTRACIÓN GENERAL DEL ESTADO", "Delegación del Gobierno en Andalucía"])
    assert c == Clasificacion("estatal", None, None)


def test_castilla_y_leon_no_se_queda_en_la_provincia_de_leon():
    assert clasificar(["COMUNIDADES Y CIUDADES AUTÓNOMAS", "Castilla y León"]).territorio == (
        "Castilla y León"
    )


def test_una_palabra_dentro_de_otra_no_cuenta():
    # «Leonesa» no es León, ni «Estadística» es el Estado.
    c = clasificar(["Asociación Leonesa de Estadística"])
    assert c == Clasificacion(None, None, None)


def test_lo_que_no_encaja_queda_sin_clasificar():
    assert clasificar(["Universidades"]) == Clasificacion(None, None, None)
    assert clasificar([]) == Clasificacion(None, None, None)
    assert clasificar(None) == Clasificacion(None, None, None)


def test_dos_comunidades_a_la_vez_no_se_resuelven_eligiendo_una():
    c = clasificar(["ENTIDADES LOCALES", "Madrid", "Barcelona"])
    assert c.territorio is None


# --- La plataforma --------------------------------------------------------


def test_la_plataforma_autonomica_dice_la_comunidad():
    perfil = "https://contractaciopublica.gencat.cat/ecofin_pscp/AppJava/cap.pscp?idCap=1"
    assert plataforma_de(perfil) == "Cataluña"
    c = clasificar([], perfil)
    # Dice dónde, no a qué nivel: un ayuntamiento también publica ahí.
    assert c == Clasificacion(None, "Cataluña", "plataforma")


def test_la_plataforma_del_estado_no_dice_nada():
    assert plataforma_de("https://contrataciondelestado.es/wps/poc?uri=x") is None


def test_si_jerarquia_y_plataforma_se_contradicen_no_se_elige():
    perfil = "https://contractaciopublica.gencat.cat/x"
    c = clasificar(["ENTIDADES LOCALES", "Sevilla"], perfil)
    assert c.territorio is None
    assert c.nivel == "local"


def test_si_coinciden_manda_la_jerarquia():
    perfil = "https://contractaciopublica.gencat.cat/x"
    c = clasificar(["Entitats municipals de Catalunya"], perfil)
    assert c == Clasificacion("local", "Cataluña", "jerarquia")


# --- Con lo guardado de las dos fuentes -----------------------------------


def test_de_bdns_no_cuenta_el_propio_organismo():
    # El último nivel de BDNS es el organismo mismo, y su nombre no clasifica:
    # «Servicio Andaluz de Salud» no dice nada que la fuente no diga arriba.
    props = {
        "name": "SERVICIO ANDALUZ DE SALUD",
        "jerarquia_bdns": ["OTROS", "SERVICIO ANDALUZ DE SALUD"],
    }
    assert clasificar_entidad(props) == Clasificacion(None, None, None)


def test_se_combinan_las_dos_fuentes():
    props = {
        "name": "Ajuntament de Sant Ramon",
        "jerarquia_placsp": ["Entitats municipals de Catalunya"],
        "perfil_contratante": "https://contractaciopublica.gencat.cat/x",
    }
    assert clasificar_entidad(props) == Clasificacion("local", "Cataluña", "jerarquia")
