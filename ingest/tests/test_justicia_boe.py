"""Altas instancias judiciales y fiscales en el BOE (spec §12, ampliación del 26/9/2026).

Golden tests (CLAUDE.md): `tests/golden/boe_justicia/*.xml` son disposiciones
reales que guardó el reconocimiento (`scripts/explorar_justicia_boe.py`). Se
leen con el mismo conector que los altos cargos: la caché de sumarios ya
guardaba todos los Reales Decretos de la II.A, y lo único que cambia es qué
cargos pasan.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from sinapsis_ingest.cargos import (
    es_alta_instancia,
    es_alto_cargo,
    es_publicable,
    institucion_judicial,
    leer_titulo,
    propuesta_de,
)
from sinapsis_ingest.connectors.base import RawDocument
from sinapsis_ingest.connectors.boe import BOEConnector

XML = Path(__file__).parent / "golden" / "boe_justicia"


def _registros(identificador: str) -> list:
    raw = RawDocument(
        source_id="boe",
        url=f"https://www.boe.es/diario_boe/xml.php?id={identificador}",
        content=(XML / f"{identificador}.xml").read_bytes(),
        media_type="application/xml",
    )
    return list(BOEConnector().parse(raw))


# --- Qué entra y qué no --------------------------------------------------------


@pytest.mark.parametrize(
    "cargo",
    [
        "Magistrado del Tribunal Constitucional",
        "Magistrada del Tribunal Constitucional",
        "Presidente del Tribunal Constitucional",
        "Magistrado de la Sala Segunda del Tribunal Supremo",
        "Magistrada de la Sala Tercera del Tribunal Supremo",
        "Presidente de la Sala Quinta del Tribunal Supremo",
        "Presidenta del Tribunal Supremo y del Consejo General del Poder Judicial",
        "Vocal del Consejo General del Poder Judicial",
        "Presidente de la Audiencia Nacional",
        "Presidente de la Sala de lo Penal de la Audiencia Nacional",
        "Presidenta del Tribunal Superior de Justicia de Castilla-La Mancha",
        "Presidente del Tribunal Superior de Justicia de Andalucía, Ceuta y Melilla",
        "Fiscal General del Estado",
        "Teniente Fiscal del Tribunal Supremo",
        "Fiscal de Sala del Tribunal Supremo",
        "Fiscal de Sala Jefe de la Fiscalía contra la Corrupción y la Criminalidad Organizada",
    ],
)
def test_altas_instancias(cargo):
    assert es_alta_instancia(cargo)
    assert es_publicable(cargo)


@pytest.mark.parametrize(
    "cargo",
    [
        # La carrera ordinaria sigue fuera.
        "Presidente de la Audiencia Provincial de Sevilla",
        "Magistrado de la Audiencia Provincial de Madrid",
        "Juez del Juzgado de Primera Instancia número 3 de Toledo",
        "Fiscal Jefe de la Fiscalía Provincial de Madrid",
        "Fiscal de la Fiscalía Especial Antidroga",
        "Presidente de la Sala de lo Civil y Penal del Tribunal Superior de Justicia de Madrid",
        "Magistrado de la Sala de lo Social del Tribunal Superior de Justicia de Galicia",
        # Ni lo que trabaja para el Supremo sin ser magistrado de él.
        "Jefe del Gabinete Técnico de Información y Documentación del Tribunal Supremo",
        "Letrado del Tribunal Constitucional",
        # Y los militares, que también se nombran por Real Decreto.
        "General de Brigada del Cuerpo General del Ejército de Tierra",
    ],
)
def test_no_son_altas_instancias(cargo):
    assert not es_alta_instancia(cargo)


def test_ninguna_alta_instancia_pasa_por_alto_cargo_salvo_el_fiscal_general():
    """Siguen siendo dos reglas: la de la Ley 3/2015 no se ha abierto."""
    assert es_alto_cargo("Fiscal General del Estado")
    assert not es_alto_cargo("Magistrado del Tribunal Constitucional")
    assert not es_alto_cargo("Presidente de la Sala Segunda del Tribunal Supremo")


@pytest.mark.parametrize(
    ("cargo", "institucion"),
    [
        ("Magistrado de la Sala Segunda del Tribunal Supremo", "Tribunal Supremo"),
        ("Magistrado del Tribunal Constitucional", "Tribunal Constitucional"),
        ("Vocal del Consejo General del Poder Judicial", "Consejo General del Poder Judicial"),
        ("Presidente de la Sala de lo Penal de la Audiencia Nacional", "Audiencia Nacional"),
        (
            "Presidente del Tribunal Superior de Justicia de Andalucía, Ceuta y Melilla",
            "Tribunal Superior de Justicia de Andalucía, Ceuta y Melilla",
        ),
        # La Fiscalía antes que el tribunal que nombra el cargo.
        ("Fiscal de Sala del Tribunal Supremo", "Fiscalía General del Estado"),
        ("Presidente de la Audiencia Provincial de Sevilla", ""),
    ],
)
def test_institucion_por_el_nombre_del_cargo(cargo, institucion):
    assert institucion_judicial(cargo) == institucion


# --- Las fórmulas de la carrera judicial ---------------------------------------------


@pytest.mark.parametrize(
    ("titulo", "nombre", "cargo"),
    [
        (
            "Real Decreto 532/2026, de 24 de junio, por el que se promueve a la categoría de "
            "Magistrado de la Sala Quinta del Tribunal Supremo a don Celso Rodríguez Padrón.",
            "Celso Rodríguez Padrón",
            "Magistrado de la Sala Quinta del Tribunal Supremo",
        ),
        (
            "Real Decreto 1276/2024, de 10 de diciembre, por el que se nombra en propiedad a don "
            "Manuel Marchena Gómez, Magistrado de la Sala Segunda del Tribunal Supremo.",
            "Manuel Marchena Gómez",
            "Magistrado de la Sala Segunda del Tribunal Supremo",
        ),
        (
            "Real Decreto 647/2019, de 8 de noviembre, por el que se nombra a don Manuel Marchena "
            "Gómez, Presidente de la Sala Segunda del Tribunal Supremo.",
            "Manuel Marchena Gómez",
            "Presidente de la Sala Segunda del Tribunal Supremo",
        ),
        (
            "Real Decreto 712/2005, de 10 de junio, por el que se nombra Presidente de la Sala "
            "Segunda del Tribunal Supremo don Juan Saavedra Ruiz.",
            "Juan Saavedra Ruiz",
            "Presidente de la Sala Segunda del Tribunal Supremo",
        ),
    ],
)
def test_formulas_de_la_carrera_judicial(titulo, nombre, cargo):
    a = leer_titulo(titulo)
    assert a is not None
    assert (a.tipo, a.nombre, a.cargo) == ("nombramiento", nombre, cargo)


@pytest.mark.parametrize(
    "titulo",
    [
        # Las fórmulas nuevas sólo valen para una alta instancia: un ascenso
        # de carrera o militar sigue sin leerse.
        "Real Decreto 1/2024, de 2 de enero, por el que se promueve a la categoría de "
        "Magistrado a don Juan Pérez García.",
        "Real Decreto 1/2024, de 2 de enero, por el que se nombra en propiedad a don Juan Pérez "
        "García, Magistrado de la Audiencia Provincial de Madrid.",
        "Real Decreto 1/2024, de 2 de enero, por el que se promueve al empleo de General de "
        "Brigada a don Juan Pérez García.",
        # El nombre va en el cuerpo, no en el título: no se lee.
        "Real Decreto 584/2026, de 8 de julio, por el que se nombra Magistrado del Tribunal "
        "Supremo competente para conocer de la autorización de las actividades del Centro "
        "Nacional de Inteligencia que afecten a los derechos fundamentales reconocidos en el "
        "artículo 18.2 y 3 de la Constitución Española.",
    ],
)
def test_lo_que_sigue_sin_leerse(titulo):
    a = leer_titulo(titulo)
    assert a is None or not es_publicable(a.cargo)


# --- Quién lo propuso ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "quien"),
    [
        (
            "De conformidad con el artículo 159 de la Constitución, y a propuesta "
            "del Senado, Vengo en nombrar",
            "Senado",
        ),
        (
            "A propuesta del Pleno del Consejo General del Poder Judicial, adoptada en su reunión",
            "Consejo General del Poder Judicial",
        ),
        (
            "por Acuerdo de la Comisión Permanente del Consejo General del Poder Judicial en su "
            "reunión",
            "Consejo General del Poder Judicial",
        ),
        ("a propuesta del Gobierno, Vengo en nombrar", "Gobierno"),
        (
            "a propuesta del Congreso de los Diputados, Vengo en nombrar",
            "Congreso de los Diputados",
        ),
        # Dos proponentes, o ninguno de la lista: no se dice nada.
        ("a propuesta del Senado y a propuesta del Gobierno", ""),
        ("a propuesta de la Ministra de Justicia", ""),
        ("Vengo en nombrar", ""),
    ],
)
def test_propuesta(texto, quien):
    assert propuesta_de([texto]) == quien


# --- Las disposiciones guardadas, de punta a punta ---------------------------------------


def test_magistrado_del_constitucional_a_propuesta_del_senado():
    [r] = _registros("BOE-A-2024-15661")
    d = r.data
    assert (d["tipo"], d["nombre"], d["cargo"]) == (
        "nombramiento",
        "José María Macías Castaño",
        "Magistrado del Tribunal Constitucional",
    )
    assert d["propuesta"] == "Senado"
    norm = BOEConnector().normalize(r)
    n = norm.aristas[0]
    # La institución es el Tribunal, no la Jefatura del Estado que publica.
    assert n.properties["departamento"] == "Tribunal Constitucional"
    assert n.properties["ambito"] == "justicia"
    assert n.properties["propuestaDe"] == "Senado"
    assert n.start_date == date(2024, 7, 30)
    # Y el puesto cuelga del Tribunal, como el de un alto cargo de su ministerio.
    assert any(e.caption == "Tribunal Constitucional" for e in norm.entidades)


def test_cese_de_un_magistrado_del_constitucional():
    [r] = _registros("BOE-A-2022-24435")
    assert r.data["tipo"] == "cese"
    assert r.data["nombre"] == "Pedro José González-Trevijano Sánchez"
    assert "propuesta" not in r.data


def test_presidencia_de_sala_del_supremo_a_propuesta_del_cgpj():
    [r] = _registros("BOE-A-2025-17263")
    assert r.data["cargo"] == "Presidente de la Sala Segunda del Tribunal Supremo"
    assert r.data["propuesta"] == "Consejo General del Poder Judicial"
    norm = BOEConnector().normalize(r)
    assert norm.aristas[0].properties["departamento"] == "Tribunal Supremo"
    # La misma clave de persona que el conector de altos cargos: quien fue
    # ministro y luego magistrado es UNA ficha.
    assert norm.entidades[0].dedupe_key.startswith("boe:persona:andres-martinez-arrieta-")


def test_en_propiedad():
    [r] = _registros("BOE-A-2025-349")
    assert (r.data["nombre"], r.data["cargo"]) == (
        "Manuel Marchena Gómez",
        "Magistrado de la Sala Segunda del Tribunal Supremo",
    )


def test_lo_que_no_es_de_la_lista_no_produce_nada():
    # Jefe del Gabinete Técnico del Supremo: no es magistrado del Supremo.
    assert _registros("BOE-A-2025-5527") == []
    # El nombre en el cuerpo y no en el título.
    assert _registros("BOE-A-2026-15203") == []


def test_todas_las_muestras_se_leen_o_se_dejan_a_proposito():
    """Lo que no es un Real Decreto —acuerdos del CGPJ, decretos de la Fiscal
    General, resoluciones— no se lee. De los Reales Decretos, sólo quedan
    fuera los que no son de la lista o no traen el nombre en el título."""
    a_proposito = {
        "BOE-A-2025-5527",  # Jefe del Gabinete Técnico del Supremo
        "BOE-A-2026-15203",  # el magistrado del CNI: el nombre va en el cuerpo
        "BOE-A-2026-15036",  # presidencia de una Sala de TSJ, no del TSJ
    }
    for xml in sorted(XML.glob("*.xml")):
        registros = _registros(xml.stem)
        real_decreto = b"<titulo>Real Decreto" in xml.read_bytes()
        if not real_decreto or xml.stem in a_proposito:
            assert registros == [], xml.name
        else:
            assert registros, xml.name


def test_campo_a_propuesta_del_gobierno():
    [r] = _registros("BOE-A-2022-24441")
    assert r.data["nombre"] == "Juan Carlos Campo Moreno"
    assert r.data["propuesta"] == "Gobierno"


def test_cese_por_renuncia_de_una_vocal_del_cgpj():
    [r] = _registros("BOE-A-2023-9418")
    d = r.data
    assert (d["tipo"], d["cargo"], d["nombre"], d["motivo"]) == (
        "cese",
        "Vocal del Consejo General del Poder Judicial",
        "María Concepción Sáez Rodríguez",
        "por renuncia",
    )


def test_teniente_fiscal_de_la_fiscalia_del_supremo():
    [r] = _registros("BOE-A-2022-813")
    assert r.data["cargo"] == "Teniente Fiscal de la Fiscalía del Tribunal Supremo"
    norm = BOEConnector().normalize(r)
    assert norm.aristas[0].properties["departamento"] == "Fiscalía General del Estado"


def test_un_tsj_con_su_nombre():
    [r] = _registros("BOE-A-2026-15580")
    norm = BOEConnector().normalize(r)
    assert norm.aristas[0].properties["departamento"] == "Tribunal Superior de Justicia de Canarias"


@pytest.mark.parametrize(
    ("titulo", "cargo", "institucion"),
    [
        (
            # El proponente en medio del título: no es parte del cargo.
            "Real Decreto 416/2018, de 8 de junio, por el que se nombra Vocal del Consejo General "
            "del Poder Judicial a propuesta del Senado a don José Antonio Ballestero Pascual.",
            "Vocal del Consejo General del Poder Judicial",
            "Consejo General del Poder Judicial",
        ),
        (
            "Real Decreto 477/2026, de 10 de junio, por el que se nombra Presidente del Tribunal "
            "Superior de Justicia del País Vasco a don Ignacio José Subijana Zunzunegui.",
            "Presidente del Tribunal Superior de Justicia del País Vasco",
            "Tribunal Superior de Justicia del País Vasco",
        ),
        (
            "Real Decreto 420/2026, de 27 de mayo, por el que se promueve a la categoría de Fiscal "
            "de Sala a doña María José Osuna Cerezo.",
            "Fiscal de Sala",
            "Fiscalía General del Estado",
        ),
    ],
)
def test_formas_del_segundo_reconocimiento(titulo, cargo, institucion):
    a = leer_titulo(titulo)
    assert a is not None
    assert a.cargo == cargo
    assert institucion_judicial(a.cargo) == institucion
    # Y el título dice quién propuso, cuando lo dice.
    if "a propuesta del Senado" in titulo:
        assert propuesta_de([titulo]) == "Senado"


def test_fiscal_de_sala_jefa_es_el_mismo_puesto_que_jefe():
    from sinapsis_ingest.cargos import puesto

    assert puesto("Fiscal de Sala Jefa de la Fiscalía del Tribunal Supremo (Sección Civil)") == (
        "Fiscal de Sala Jefe de la Fiscalía del Tribunal Supremo (Sección Civil)"
    )
