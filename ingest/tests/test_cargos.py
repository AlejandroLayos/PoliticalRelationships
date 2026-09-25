"""Lectura de títulos de Real Decreto, contra los títulos reales del BOE.

La muestra la guardó el reconocimiento (`scripts/explorar_boe.py`) desde la
API de datos abiertos del BOE: son títulos tal cual, sin retocar.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from sinapsis_ingest.cargos import es_alto_cargo, leer_titulo, puesto

GOLDEN = Path(__file__).parent / "golden"


def _titulos(fichero: str) -> list[str]:
    ruta = GOLDEN / fichero
    if not ruta.exists():
        pytest.skip(f"falta la muestra {fichero}")
    return [i["titulo"] for i in json.loads(ruta.read_text(encoding="utf-8"))["items"]]


def test_nombramiento_real():
    a = leer_titulo(
        "Real Decreto 714/2026, de 1 de septiembre, por el que se nombra Secretaria "
        "General de Transporte Terrestre a doña Sara Hernández del Olmo."
    )
    assert a is not None
    assert a.tipo == "nombramiento"
    assert a.cargo == "Secretaria General de Transporte Terrestre"
    assert a.nombre == "Sara Hernández del Olmo"
    assert a.numero == "714/2026"
    assert a.fecha_decreto == date(2026, 9, 1)


def test_cese_real():
    a = leer_titulo(
        "Real Decreto 712/2026, de 1 de septiembre, por el que se dispone el cese de "
        "doña Rocío Báguena Rodríguez como Secretaria General de Transporte Terrestre."
    )
    assert a is not None
    assert a.tipo == "cese"
    assert a.cargo == "Secretaria General de Transporte Terrestre"
    assert a.nombre == "Rocío Báguena Rodríguez"
    assert a.motivo == ""


def test_un_cargo_con_comas_no_se_corta():
    # Los nombres de ministerio llevan comas. Cortar en la primera publicaría
    # «Ministra de Trabajo» a secas.
    a = leer_titulo(
        "Real Decreto 5/2020, de 13 de enero, por el que se dispone el cese de doña "
        "Magdalena Valerio Cordero como Ministra de Trabajo, Migraciones y Seguridad Social."
    )
    assert a is not None
    assert a.cargo == "Ministra de Trabajo, Migraciones y Seguridad Social"


@pytest.mark.parametrize(
    ("titulo", "motivo"),
    [
        (
            "Real Decreto 1/2024, de 2 de enero, por el que se dispone el cese, a petición "
            "propia, de don Juan Pérez García como Director General de Carreteras.",
            "a petición propia",
        ),
        (
            "Real Decreto 1/2024, de 2 de enero, por el que se dispone el cese de don Juan "
            "Pérez García como Director General de Carreteras, por pase a otro destino.",
            "por pase a otro destino",
        ),
        (
            "Real Decreto 1/2024, de 2 de enero, por el que se dispone el cese de don Juan "
            "Pérez García como Director General de Carreteras, agradeciéndole los servicios "
            "prestados.",
            "agradeciéndole los servicios prestados",
        ),
    ],
)
def test_el_motivo_del_cese_no_es_parte_del_cargo(titulo, motivo):
    a = leer_titulo(titulo)
    assert a is not None
    assert a.cargo == "Director General de Carreteras"
    assert a.motivo == motivo


@pytest.mark.parametrize(
    "titulo",
    [
        # Varias personas a la vez: no se reparte a ciegas quién es qué.
        "Real Decreto 1/2024, de 2 de enero, por el que se nombran Vocales del Consejo a "
        "don Juan Pérez García y a doña Ana López Ruiz.",
        # El cese colectivo de un gobierno no dice a quién ni de qué.
        "Real Decreto 1/2024, de 2 de enero, por el que se dispone el cese de los "
        "Vicepresidentes y Ministros del Gobierno.",
        # No es un Real Decreto.
        "Orden HFP/1/2024, de 2 de enero, por la que se nombra Subdirector General a don "
        "Juan Pérez García.",
        # Un nombre de una sola palabra no es un nombre y apellido.
        "Real Decreto 1/2024, de 2 de enero, por el que se nombra Director General de "
        "Carreteras a don Juan.",
    ],
)
def test_lo_que_no_encaja_en_la_formula_no_se_lee(titulo):
    assert leer_titulo(titulo) is None


def test_todos_los_titulos_reales_se_leen():
    """La muestra entera son actos de una persona: tienen que salir todos."""
    titulos = _titulos("boe_altos_cargos_muestra.json")
    no_leidos = [t for t in titulos if leer_titulo(t) is None]
    assert not no_leidos, no_leidos
    # Y ninguno se come el tratamiento ni el punto final.
    for t in titulos:
        a = leer_titulo(t)
        assert a is not None
        assert not a.nombre.startswith(("don ", "doña "))
        assert not a.nombre.endswith(".")
        assert a.cargo and a.cargo[0].isupper()


def test_puesto_quita_el_genero_de_quien_lo_ocupa():
    assert puesto("Secretaria General de Transporte Terrestre") == (
        "Secretario General de Transporte Terrestre"
    )
    assert puesto("Ministra de Hacienda") == "Ministro de Hacienda"
    assert puesto("Vicepresidenta primera del Gobierno") == "Vicepresidente primero del Gobierno"
    # Más adentro no se toca: «Secretaría», con tilde, es el órgano.
    assert puesto(
        "Directora del Departamento de Comunicación Institucional de la Secretaría de Estado"
    ) == ("Director del Departamento de Comunicación Institucional de la Secretaría de Estado")


@pytest.mark.parametrize(
    "cargo",
    [
        "Secretaria General de Transporte Terrestre",
        "Secretaria de Estado de Vivienda y Agenda Urbana",
        "Presidenta de CASA 47 Entidad Pública Empresarial",
        "Directora General de Financiación Internacional",
        "Director del Departamento de Comunicación Institucional de la Secretaría de "
        "Estado de Comunicación",
        "Enviado Especial para Siria",
        "Ministra de Trabajo, Migraciones y Seguridad Social",
        "Vicepresidenta Primera del Gobierno",
        "Presidente del Gobierno",
        "Subsecretario de Hacienda",
        "Delegado del Gobierno en Andalucía",
        "Embajador de España en la República Francesa",
        "Fiscal General del Estado",
    ],
)
def test_altos_cargos(cargo):
    assert es_alto_cargo(cargo)


@pytest.mark.parametrize(
    "cargo",
    [
        # Carreras que también se nombran por Real Decreto.
        "Fiscal de la Fiscalía Especial Antidroga",
        "Fiscal Jefe de la Fiscalía Provincial de Madrid",
        "Inspectora Fiscal de la Inspección Fiscal de la Fiscalía General del Estado",
        "Presidente de la Audiencia Provincial de Sevilla",
        "Magistrado de la Sala Tercera del Tribunal Supremo",
        "General de Brigada del Cuerpo General del Ejército de Tierra",
        # Y lo que no reconoce ninguna regla no pasa.
        "Vocal del Consejo Asesor",
        "Subdirector General de Coordinación",
    ],
)
def test_no_son_altos_cargos(cargo):
    assert not es_alto_cargo(cargo)


def test_la_muestra_real_separa_fiscales_de_altos_cargos():
    titulos = _titulos("boe_altos_cargos_muestra.json")
    actos = [a for a in (leer_titulo(t) for t in titulos) if a]
    altos = {a.cargo for a in actos if es_alto_cargo(a.cargo)}
    fuera = {a.cargo for a in actos if not es_alto_cargo(a.cargo)}
    assert "Secretaria General de Transporte Terrestre" in altos
    assert "Directora General de Financiación Internacional" in altos
    assert fuera, "la muestra trae fiscales y ninguno debería pasar"
    assert all("Fiscal" in c for c in fuera), fuera


# --- El histórico: días de cambio de gobierno (2011, 2018) -------------------

# Lo que se deja sin leer A PROPÓSITO, por su forma. Si aparece un título sin
# leer que no encaja en ninguna, es una forma nueva y hay que mirarla: por eso
# esto es una lista cerrada y no un porcentaje.
_SIN_LEER_A_PROPOSITO = (
    "se nombran Ministros",  # colectivo: los nombres van en el cuerpo
    "asuma las funciones",  # encarga una función a quien ya tiene cargo
    "se promueve al empleo",  # ascensos militares
    "se confiere",  # representación de la Corona
    "se declara la jubilación",
    "del General",  # militares: el empleo va delante del nombre
    "del Teniente General",
    "al Almirante",
    "al General",
)


def test_el_historico_se_lee_entero_salvo_lo_que_no_se_lee_a_proposito():
    titulos = _titulos("boe_altos_cargos_historico.json")
    sin_leer = [
        t
        for t in titulos
        if leer_titulo(t) is None and not any(f in t for f in _SIN_LEER_A_PROPOSITO)
    ]
    assert not sin_leer, sin_leer


@pytest.mark.parametrize(
    ("titulo", "nombre", "cargo"),
    [
        (
            # Apóstrofo escrito con el acento agudo suelto.
            "Real Decreto 1863/2011, de 23 de diciembre, por el que se dispone el cese de doña "
            "Isabel Aymerich D\u00b4Olhaberriague como Directora del Gabinete del Ministro "
            "de Educación.",
            "Isabel Aymerich D\u00b4Olhaberriague",
            "Directora del Gabinete del Ministro de Educación",
        ),
        (
            # El BOE se comió el «de».
            "Real Decreto 1969/2011, de 30 de diciembre, por el que se dispone el cese doña "
            "Anunciación Romero González como Secretaria General de Vivienda.",
            "Anunciación Romero González",
            "Secretaria General de Vivienda",
        ),
        (
            "Real Decreto 1991/2011, de 30 de diciembre, por el que se dispone el cese de doña "
            "Mª del Pilar Pin Vega como Directora General de la Ciudadanía Española en el "
            "Exterior.",
            "Mª del Pilar Pin Vega",
            "Directora General de la Ciudadanía Española en el Exterior",
        ),
        (
            # Y aquí, el «se».
            "Real Decreto 567/2018, de 18 de junio, por el que dispone el cese de doña Elena "
            "Collado Martínez como Secretaria de Estado de Función Pública.",
            "Elena Collado Martínez",
            "Secretaria de Estado de Función Pública",
        ),
        (
            "Real Decreto 1925/2011, de 30 de diciembre, por el que se designa Embajador "
            "Representante Permanente de España ante la Unión Europea a don Alfonso María "
            "Dastis Quecedo.",
            "Alfonso María Dastis Quecedo",
            "Embajador Representante Permanente de España ante la Unión Europea",
        ),
    ],
)
def test_formas_reales_del_historico(titulo, nombre, cargo):
    a = leer_titulo(titulo)
    assert a is not None
    assert (a.nombre, a.cargo) == (nombre, cargo)
    assert es_alto_cargo(a.cargo)


@pytest.mark.parametrize(
    "cargo",
    [
        # La regla vieja de carreras la tachaba por «notari».
        "Directora General de los Registros y del Notariado",
        "Director Adjunto del Gabinete de la Presidencia del Gobierno",
        "Vicepresidente Ejecutivo del Instituto Español de Comercio Exterior (ICEX)",
        "Consejera Delegada del Instituto Español de Comercio Exterior (ICEX)",
        "Vicesecretario General de la Presidencia del Gobierno",
    ],
)
def test_altos_cargos_del_historico(cargo):
    assert es_alto_cargo(cargo)


def test_puesto_de_dos_palabras():
    assert puesto("Consejera Delegada del ICEX") == "Consejero Delegado del ICEX"
