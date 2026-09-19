"""Los nombres de persona tampoco pueden salir DENTRO del texto publicado.

Omitir la ficha de una persona física no la saca de la prosa que la rodea. El
18/9/2026, con la regla de §12 aplicándose bien a las entidades, la descripción
de un expediente seguía nombrando al artista contratado:

    «…la licitació del contracte per al projecte de creació "Veus de Parets"
    de <nombre y apellido>»

El expediente sí se publica. La ficha de esa persona estaba correctamente
retirada del mapa y su nombre salió igual, en un campo que ninguna de las dos
reglas anteriores —esquema `Person`, identificador de persona física— mira.

Estos tests son de las funciones puras, así que corren sin base de datos. Los
del volcado entero están en `test_exportar.py`.
"""

from __future__ import annotations

import pytest

from sinapsis_ingest.exportar import (
    MARCA_NOMBRE_RETIRADO,
    _parece_nombre_de_persona,
    censor,
    es_solo_un_nombre,
    tapar_nodo,
    tapar_nombres,
)


def _tapar(nombres, texto):
    patron = censor(nombres)
    assert patron is not None
    cuenta = [0]
    return tapar_nombres(texto, patron, cuenta), cuenta[0]


def test_el_caso_real_que_lo_destapo():
    texto = (
        "És objecte del present plec la contractació promoguda pel departament "
        "de Cultura consistent en la licitació del contracte per al projecte de "
        'creació "Veus de Parets" de Queralt Riera.'
    )
    salida, n = _tapar(["Queralt Riera"], texto)
    assert "Queralt" not in salida
    assert "Riera" not in salida
    assert n == 1
    # Lo demás se queda: el texto sigue diciendo qué se contrató.
    assert "Veus de Parets" in salida
    assert MARCA_NOMBRE_RETIRADO in salida


def test_el_hueco_se_marca_y_no_se_borra_a_escondidas():
    """Una descripción a la que le falta una palabra sin avisar miente.

    Es la misma razón por la que el volcado lleva `truncado`: un dato
    incompleto que finge estar completo es peor que uno que declara su hueco.
    """
    salida, _ = _tapar(["Ana Gil"], "el pago a Ana Gil del día 3")
    assert salida == f"el pago a {MARCA_NOMBRE_RETIRADO} del día 3"


def test_casa_aunque_el_nombre_venga_partido_por_un_salto_de_linea():
    """Los pliegos se copian tal cual, con sus saltos de línea dentro.

    Un patrón que exige un espacio literal encuentra cero ocurrencias donde
    hay una. Costó seis intentos aprenderlo en el guion que limpia el
    historial, porque allí el borrado y su comprobación compartían el fallo y
    por eso no podía delatarse solo.
    """
    for medio in (" ", "\n", "\n    ", "\t", "  \n\t  "):
        salida, n = _tapar(["Queralt Riera"], f"de Queralt{medio}Riera, artista")
        assert n == 1, medio
        assert "Riera" not in salida, medio


def test_no_casa_a_medias_de_una_palabra():
    salida, n = _tapar(["Ana Gil"], "la empresa Anagilsa y Ana Gilabert")
    assert n == 0
    assert salida == "la empresa Anagilsa y Ana Gilabert"


def test_da_igual_como_venga_escrito():
    """Las fuentes alternan mayúsculas sin criterio: «PEREZ», «Perez», «pérez»."""
    for escrito in ("Ana Gil", "ANA GIL", "ana gil", "AnA gIl"):
        _, n = _tapar(["Ana Gil"], f"pago a {escrito} hoy")
        assert n == 1, escrito


@pytest.mark.parametrize(
    "nombre",
    [
        "Ana Gil",
        "Juan de la Cruz",
        "JUAN PEREZ LOPEZ",
        "Queralt Riera",
        "O'Donnell Smith",
    ],
)
def test_reconoce_lo_que_es_un_nombre(nombre):
    assert _parece_nombre_de_persona(nombre)


@pytest.mark.parametrize(
    "cadena",
    [
        "la parada",  # salió de la base: basura en el campo del nombre
        "el taller de Sant Genis",
        "Solo",  # una palabra suelta no se busca dentro de un texto
        "ANA",
        "",
        "de la",
    ],
)
def test_no_confunde_con_un_nombre(cadena):
    assert not _parece_nombre_de_persona(cadena)


def test_una_frase_corriente_en_minuscula_no_tapa_medio_volcado():
    """El filtro que importa son las mayúsculas, no la longitud.

    La base traía una ficha de persona cuyo «nombre» era una frase corriente en
    minúscula. Buscarla con `IGNORECASE` dentro de todas las descripciones
    publicadas habría tapado prosa legítima a puñados sin proteger a nadie:
    esa frase aparece hasta en los comentarios de este repositorio.
    """
    patron = censor(["la parada"])
    assert patron is None


def test_un_apellido_suelto_no_se_persigue():
    """Taparlo destrozaría el texto sin proteger a nadie.

    «Genis» es un apellido y también el santo que da nombre a un taller
    municipal; «Adell», un apellido y una calle. La ficha de la persona ya está
    retirada; lo que queda es prosa sobre lugares.
    """
    assert censor(["Genis", "Adell"]) is None


def test_recorre_propiedades_anidadas():
    """Las propiedades de un nodo son un JSON arbitrario que viene de la fuente.

    Acotar la búsqueda a las claves que hoy existen sería dejar abierta la
    siguiente que añada cualquier conector.
    """
    dentro = {
        "caption": "obra de Ana Gil",
        "properties": {"desc": ["adjudicada a Ana Gil", {"nota": "firma Ana Gil"}]},
        "importe": 1000,
        "nada": None,
    }
    salida, n = _tapar(["Ana Gil"], dentro)
    assert n == 3
    assert "Gil" not in repr(salida)
    assert salida["importe"] == 1000
    assert salida["nada"] is None


def test_lo_que_no_casa_sale_igual():
    salida, n = _tapar(["Ana Gil"], {"a": "sin nombres aquí", "b": ["ni", "aquí"]})
    assert n == 0
    assert salida == {"a": "sin nombres aquí", "b": ["ni", "aquí"]}


def test_sin_nombres_no_hay_patron():
    assert censor([]) is None


# --- Cuando el nombre de la ficha ES el nombre -----------------------------
#
# Apareció en la primera ejecución real del tapado, el 18/9/2026: el volcado
# salió con un nodo `Company` cuyo caption era, entero, «(nombre retirado)».
# Taparlo dentro del texto no bastaba porque el texto era todo lo que había, y
# lo que quedaba en el mapa era un nodo pinchable, con sus cifras, que no
# protege a nadie ni dice nada. Esa ficha se omite entera.


def _patron(nombres=("Ana Gil", "Queralt Riera")):
    p = censor(nombres)
    assert p is not None
    return p


@pytest.mark.parametrize(
    "caption",
    [
        "Ana Gil",
        "ANA GIL",
        "  Ana Gil  ",
        "«Ana Gil»",
        "(Ana Gil)",
        "Ana Gil - Queralt Riera",  # dos personas y nada más
        "Ana\nGil",
    ],
)
def test_la_ficha_que_es_solo_un_nombre_se_va(caption):
    assert es_solo_un_nombre(caption, _patron())


@pytest.mark.parametrize(
    "caption",
    [
        # Una sociedad que lleva el nombre de quien la fundó sigue siendo una
        # sociedad, y es una parte contratante que hay que poder nombrar.
        "Ana Gil, S.L.",
        "CONSTRUCCIONES ANA GIL",
        "Ana Gil e Hijos SA",
        # A la UTE le queda el topónimo, que es un nombre de lugar.
        "UTE PERAFITA (Ana Gil)",
        "AYUNTAMIENTO DE MADRID",
        "",
    ],
)
def test_una_ficha_con_algo_mas_se_queda(caption):
    assert not es_solo_un_nombre(caption, _patron())


def test_sin_caption_no_decide_nada():
    assert not es_solo_un_nombre(None, _patron())


# --- Qué se tapa y qué no -------------------------------------------------
#
# Estos tests existen porque la CI encontró lo que estos tests no cubrían. El
# tapado se aplicaba a TODO, incluido el nombre propio de la ficha, y dejaba
# «Ana Gil, S.L.» en «(nombre retirado), S.L.» — el nombre de una sociedad que
# sí se publica, que es público y está en el Registro Mercantil.
#
# La comprobación vivía sólo en `test_exportar.py`, que necesita Postgres y
# aquí se salta. O sea que fallaba en la CI y pasaba en local, que es la peor
# forma de tener un test. La regla es pura y se prueba en pura.


def test_una_sociedad_conserva_su_razon_social():
    nodo = {
        "schema": "Company",
        "caption": "Ana Gil, S.L.",
        "properties": {"desc": "obra adjudicada a Ana Gil"},
    }
    salida = tapar_nodo(nodo, _patron(), [0])
    assert salida["caption"] == "Ana Gil, S.L."
    # Pero la prosa de alrededor sí se tapa.
    assert "Gil" not in salida["properties"]["desc"]


@pytest.mark.parametrize(
    "schema",
    ["PublicBody", "Company", "Organization", "LegalEntity"],
)
def test_ninguna_ficha_con_nombre_pierde_el_suyo(schema):
    nodo = {"schema": schema, "caption": "AYUNTAMIENTO DE ANA GIL"}
    assert tapar_nodo(nodo, _patron(), [0])["caption"] == "AYUNTAMIENTO DE ANA GIL"


def test_el_objeto_de_un_expediente_si_se_tapa():
    """El caption de un `Contract` no es un nombre: es prosa del pliego.

    Y es exactamente donde apareció el nombre del artista contratado.
    """
    nodo = {"schema": "Contract", "caption": 'projecte "Veus de Parets" de Queralt Riera'}
    salida = tapar_nodo(nodo, _patron(), [0])
    assert "Queralt" not in salida["caption"]
    assert "Veus de Parets" in salida["caption"]


def test_se_cuentan_las_menciones_tapadas_y_no_las_respetadas():
    cuenta = [0]
    tapar_nodo(
        {"schema": "Company", "caption": "Ana Gil, S.L.", "properties": {"x": "de Ana Gil"}},
        _patron(),
        cuenta,
    )
    assert cuenta[0] == 1


def test_un_nodo_sin_caption_no_revienta():
    salida = tapar_nodo({"schema": "Company", "properties": {}}, _patron(), [0])
    assert salida == {"schema": "Company", "properties": {}}
