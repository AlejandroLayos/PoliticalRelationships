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


# --- Lo que dejó sin clasificar la primera ingesta real (25/9/2026) ---------


def test_la_plataforma_catalana_nueva():
    """379 organismos colgaban de «Entitats de l'administració local» con el
    perfil en contractaciopublica.cat, que no se conocía: el Ajuntament de
    Barcelona, TMB, el Área Metropolitana."""
    c = clasificar(
        ["Entitats de l'administració local"],
        "https://contractaciopublica.cat/perfil/BCNAJT",
    )
    assert (c.nivel, c.territorio, c.por) == ("local", "Cataluña", "plataforma")


def test_la_categoria_catalana_dice_local_aunque_no_diga_donde():
    c = clasificar(["Entitats de l'administració local"])
    assert c.nivel == "local"
    assert c.territorio is None


@pytest.mark.parametrize(
    ("padre", "comunidad"),
    [
        ("Servicio Navarro de Salud - Osasunbidea", "Navarra"),
        ("Servicio Andaluz de Salud", "Andalucía"),
        ("Servizo Galego de Saúde", "Galicia"),
        ("Osakidetza", "País Vasco"),
        ("Institut Català de la Salut", "Cataluña"),
        ("Servicio Madrileño de Salud", "Madrid"),
    ],
)
def test_los_servicios_de_salud_por_su_nombre_entero(padre, comunidad):
    assert clasificar([padre]).territorio == comunidad


def test_un_gentilicio_suelto_no_basta():
    # «Navarro» es también un apellido. Sólo el nombre entero del servicio.
    assert clasificar(["Fundación Navarro Villoslada"]).territorio is None


# --- Municipios del INE -------------------------------------------------------

from sinapsis_ingest.territorio import (  # noqa: E402
    formas_de_municipio,
    municipio_en,
    municipios_unicos,
)

_TABLA_DE_PRUEBA = municipios_unicos(
    [
        {"codauto": "09", "nombre": "Berga"},
        {"codauto": "15", "nombre": "Pamplona/Iruña"},
        {"codauto": "13", "nombre": "Rozas de Madrid, Las"},
        {"codauto": "09", "nombre": "Hospitalet de Llobregat, L'"},
        # Dos comunidades con el mismo nombre: no se resuelve.
        {"codauto": "07", "nombre": "Villanueva del Campo"},
        {"codauto": "08", "nombre": "Villanueva del Campo"},
        # Dos provincias de la misma comunidad: sí.
        {"codauto": "07", "nombre": "Castrillo de la Reina"},
        {"codauto": "07", "nombre": "Castrillo de la Reina"},
    ]
)


def test_formas_del_ine():
    assert "las rozas de madrid" in formas_de_municipio("Rozas de Madrid, Las")
    # Tal cual también: BDNS escribe «CORUÑA, A».
    assert set(formas_de_municipio("Coruña, A")) == {"coruna a", "a coruna"}
    assert set(formas_de_municipio("Donostia/San Sebastián")) == {
        "donostia san sebastian",
        "donostia",
        "san sebastian",
    }
    assert "l hospitalet de llobregat" in formas_de_municipio("Hospitalet de Llobregat, L'")


@pytest.mark.parametrize(
    ("eslabones", "comunidad"),
    [
        (["local", "berga"], "Cataluña"),  # como viene en BDNS
        (["ayuntamiento de pamplona"], "Navarra"),
        (["ayuntamiento de iruna"], "Navarra"),
        (["ayuntamiento de las rozas de madrid"], "Madrid"),
        (["ajuntament de l hospitalet de llobregat"], "Cataluña"),
        (["local", "castrillo de la reina"], "Castilla y León"),
        (["local", "villanueva del campo"], None),
        # Una palabra suelta dentro de otro nombre no cuenta.
        (["local", "mancomunidad de berga y otros"], None),
    ],
)
def test_el_municipio_dice_la_comunidad_si_no_duda(eslabones, comunidad):
    assert municipio_en(eslabones, _TABLA_DE_PRUEBA) == comunidad


def test_sin_tabla_no_se_adivina():
    assert municipio_en(["local", "berga"], {}) is None


def test_el_estado_dicho_explicitamente_manda_sobre_lo_local():
    c = clasificar(
        [
            "Sector Público",
            "ADMINISTRACIÓN GENERAL DEL ESTADO",
            "Ministerio para la Transición Ecológica y el Reto Demográfico",
            "Dirección General del Agua",
            "Mancomunidad de los Canales del Taibilla",
        ]
    )
    assert c.nivel == "estatal" and c.territorio is None


def test_la_tabla_real_del_ine():
    """Con la relación que se commitea, los casos de la primera ingesta real."""
    from sinapsis_ingest.territorio import MUNICIPIOS_INE, _municipios

    if not MUNICIPIOS_INE.exists():
        pytest.skip("sin la relación del INE")
    tabla = _municipios()
    assert municipio_en(["local", "berga"], tabla) == "Cataluña"
    assert municipio_en(["local", "coruna a"], tabla) == "Galicia"
    assert municipio_en(["ayuntamiento de donostia san sebastian"], tabla) == "País Vasco"
    assert municipio_en(["local", "espartinas"], tabla) == "Andalucía"
