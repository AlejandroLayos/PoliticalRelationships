"""La puerta de los cargos públicos: qué sale por ella y, sobre todo, qué no.

Las pruebas de `periodos` son puras. Las de la puerta necesitan Postgres,
porque lo que se prueba es la consulta que decide quién sale: una regla que
sólo existe en Python no protege nada si el SQL deja pasar otra cosa.
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from sinapsis_ingest.connectors.base import ParsedRecord, RawDocument
from sinapsis_ingest.connectors.boe import BOEConnector
from sinapsis_ingest.connectors.boe import clave as clave_boe
from sinapsis_ingest.exportar import exportar
from sinapsis_ingest.exportar_cargos import es_sociedad_mercantil, nombre_natural, periodos
from sinapsis_ingest.normalizado import AristaNormalizada, EntidadNormalizada, Normalizado
from sinapsis_ingest.pipeline import Resultado, ingerir_documento
from sinapsis_ingest.store import Source, Store

DSN = os.environ.get("SINAPSIS_TEST_POSTGRES_DSN", "")
con_base = pytest.mark.skipif(not DSN, reason="SINAPSIS_TEST_POSTGRES_DSN sin definir")


def _acto(tipo: str, fecha: date, puesto: str = "Secretario General de X", boe: str = "") -> dict:
    return {
        "tipo": tipo,
        "fecha": fecha,
        "puesto": puesto,
        "cargo": puesto,
        "organismo": "Ministerio de Pruebas",
        "boe": boe or f"BOE-A-{fecha.isoformat()}-{tipo}",
        "url": "https://www.boe.es/x",
    }


# --- periodos (puro) --------------------------------------------------------


def test_un_nombramiento_y_su_cese_son_un_periodo():
    ps = periodos([_acto("cese", date(2024, 3, 1)), _acto("nombramiento", date(2020, 1, 15))])
    assert len(ps) == 1
    assert ps[0]["desde"] == date(2020, 1, 15)
    assert ps[0]["hasta"] == date(2024, 3, 1)


def test_cesar_y_volver_a_ser_nombrado_el_mismo_dia_son_dos_periodos():
    """Lo que pasa al formarse un gobierno. Con una sola arista por persona y
    puesto, el segundo nombramiento se perdía y quien sigue en el cargo salía
    como ex alto cargo."""
    ps = periodos(
        [
            _acto("nombramiento", date(2018, 6, 19)),
            _acto("cese", date(2023, 11, 22)),
            _acto("nombramiento", date(2023, 11, 22)),
        ]
    )
    assert len(ps) == 2
    abierto, cerrado = ps
    assert abierto["desde"] == date(2023, 11, 22) and "hasta" not in abierto
    assert cerrado == {**cerrado, "desde": date(2018, 6, 19), "hasta": date(2023, 11, 22)}


def test_un_cese_sin_nombramiento_no_se_inventa_el_inicio():
    ps = periodos([_acto("cese", date(2012, 1, 1))])
    assert len(ps) == 1
    assert "desde" not in ps[0]
    assert ps[0]["hasta"] == date(2012, 1, 1)


def test_dos_nombramientos_seguidos_no_se_inventan_el_fin():
    ps = periodos(
        [_acto("nombramiento", date(2010, 1, 1)), _acto("nombramiento", date(2012, 1, 1))]
    )
    assert len(ps) == 2
    assert all("hasta" not in p for p in ps)


def test_cada_puesto_va_por_su_lado():
    ps = periodos(
        [
            _acto("nombramiento", date(2020, 1, 1), puesto="Director General de A"),
            _acto("cese", date(2021, 1, 1), puesto="Director General de B"),
        ]
    )
    assert {p["puesto"] for p in ps} == {"Director General de A", "Director General de B"}
    a = next(p for p in ps if p["puesto"] == "Director General de A")
    assert "hasta" not in a


def test_lo_mas_reciente_va_primero():
    ps = periodos(
        [
            _acto("nombramiento", date(2010, 1, 1), puesto="A"),
            _acto("cese", date(2012, 1, 1), puesto="A"),
            _acto("nombramiento", date(2020, 1, 1), puesto="B"),
        ]
    )
    assert [p["puesto"] for p in ps] == ["B", "A"]


# --- la puerta (con base) ----------------------------------------------------


@pytest.fixture
def store():
    with Store(DSN) as s:
        migraciones = Path(__file__).resolve().parents[2] / "backend" / "migrations"
        for f in sorted(migraciones.glob("*.up.sql")):
            try:
                s.conn.execute(f.read_text(encoding="utf-8"))
            except Exception:
                s.conn.rollback()
        s.conn.commit()
        s.conn.execute(
            """TRUNCATE provenance, entity_resolution_decisions, review_queue,
                        relationships, entities, raw_documents, sources CASCADE"""
        )
        for fuente in ("boe", "bdns"):
            s.upsert_source(Source(id=fuente, name=fuente.upper(), url="https://ejemplo.test"))
        s.conn.commit()
        yield s


class _Fijo:
    """Un conector que produce exactamente lo que se le da."""

    extractor_version = "test/1"

    def __init__(self, source_id: str, n: Normalizado) -> None:
        self.source_id = source_id
        self._n = n

    def parse(self, raw: RawDocument):
        yield ParsedRecord(raw.content_hash, self.extractor_version, {"id_registro": "x"})

    def normalize(self, record: ParsedRecord) -> Normalizado:
        return self._n


def _ingerir(store: Store, source_id: str, n: Normalizado, contenido: bytes) -> None:
    raw = RawDocument(
        source_id=source_id,
        url=f"https://ejemplo.test/{source_id}",
        content=contenido,
        media_type="application/xml",
    )
    ingerir_documento(store, _Fijo(source_id, n), raw, Resultado())
    store.conn.commit()


def _nombramiento_boe(nombre: str, identificador: str, cargo: str) -> Normalizado:
    """Lo que produce el conector del BOE para un nombramiento."""
    registro = ParsedRecord(
        raw_content_hash="x",
        extractor_version=BOEConnector.extractor_version,
        data={
            "identificador": identificador,
            "titulo": "",
            "departamento": "Ministerio de Pruebas",
            "fecha_publicacion": "20260902",
            "fecha_disposicion": "20260901",
            "tipo": "nombramiento",
            "cargo": cargo,
            "nombre": nombre,
            "numero": "714/2026",
            "motivo": "",
        },
    )
    n = BOEConnector().normalize(registro)
    assert n is not None
    return n


def _cese_boe(nombre: str, identificador: str, cargo: str, fecha: str) -> Normalizado:
    registro = ParsedRecord(
        raw_content_hash="x",
        extractor_version=BOEConnector.extractor_version,
        data={
            "identificador": identificador,
            "titulo": "",
            "departamento": "Ministerio de Pruebas",
            "fecha_publicacion": fecha,
            "fecha_disposicion": fecha,
            "tipo": "cese",
            "cargo": cargo,
            "nombre": nombre,
            "numero": "1/2018",
            "motivo": "",
        },
    )
    n = BOEConnector().normalize(registro)
    assert n is not None
    return n


def _persona(clave: str, nombre: str, props: dict[str, Any], nif: str = "") -> Normalizado:
    """Una persona con un acto de cargo, construida a mano: para probar que la
    puerta mira la base y no se fía de que lo haya creado el conector."""
    return Normalizado(
        entidades=[
            EntidadNormalizada("Person", nombre, clave, nif=nif, properties=props),
            EntidadNormalizada("Position", "Director General de Z", f"{clave}:puesto"),
        ],
        aristas=[
            AristaNormalizada(
                "Occupancy",
                clave,
                f"{clave}:puesto",
                f"{clave}:acto",
                confidence=1.0,
                start_date=date(2026, 1, 1),
                properties={"acto": "nombramiento", "cargo": "Director General de Z"},
            )
        ],
    )


def _volcar(store: Store, tmp_path: Path) -> tuple[dict, dict, dict]:
    exportar(store, tmp_path / "grafo.json")
    leer = lambda n: json.loads((tmp_path / n).read_text(encoding="utf-8"))  # noqa: E731
    return leer("grafo.json"), leer("indice.json"), leer("cargos.json")


@con_base
def test_un_alto_cargo_del_boe_sale_en_cargos(store, tmp_path):
    _ingerir(
        store,
        "boe",
        _nombramiento_boe(
            "Sara Hernández del Olmo", "BOE-A-2026-18440", "Secretaria General de Transporte"
        ),
        b"<documento>1</documento>",
    )
    _, _, cargos = _volcar(store, tmp_path)

    assert [p["nombre"] for p in cargos["personas"]] == ["Sara Hernández del Olmo"]
    periodo = cargos["personas"][0]["periodos"][0]
    assert periodo["puesto"] == "Secretario General de Transporte"
    assert periodo["cargo"] == "Secretaria General de Transporte"
    assert periodo["organismo"] == "Ministerio de Pruebas"
    assert periodo["desde"] == "2026-09-02"
    assert periodo["boeDesde"] == "BOE-A-2026-18440"
    assert periodo["urlDesde"].endswith("BOE-A-2026-18440")


@con_base
def test_el_alto_cargo_no_entra_en_el_grafo_ni_en_el_indice(store, tmp_path):
    """El grafo sigue sin dejar pasar a ninguna persona, tampoco a éstas."""
    _ingerir(
        store,
        "boe",
        _nombramiento_boe("Sara Hernández del Olmo", "BOE-A-1", "Directora General de X"),
        b"<documento>1</documento>",
    )
    grafo, indice, _ = _volcar(store, tmp_path)
    assert not grafo["nodes"]
    assert not grafo["edges"]
    assert grafo["personasOmitidas"]["fichas"] == 0
    assert not [e for e in indice["entidades"] if e["clave"].startswith("boe:")]


@pytest.mark.parametrize(
    ("fuente", "clave", "props", "nif"),
    [
        # Sin la marca.
        ("boe", "boe:persona:ana-gil-ruiz", {"name": "Ana Gil Ruiz"}, ""),
        # Con la marca, pero con una clave que no es del BOE.
        ("bdns", "bdns:persona:ana-gil-ruiz", {"cargo_publico": True}, ""),
        # Con marca y clave, pero sin procedencia del BOE.
        ("bdns", "boe:persona:ana-gil-ruiz", {"cargo_publico": True}, ""),
        # Con todo, pero identificada con un DNI: el BOE no los publica.
        ("boe", "boe:persona:ana-gil-ruiz", {"cargo_publico": True}, "12345678Z"),
    ],
)
@con_base
def test_sin_las_cinco_condiciones_no_sale(store, tmp_path, fuente, clave, props, nif):
    persona = _persona(clave, "Ana Gil Ruiz", props, nif)
    _ingerir(store, fuente, persona, b"<documento>2</documento>")
    _, _, cargos = _volcar(store, tmp_path)
    assert cargos["personas"] == []


@con_base
def test_solo_sale_el_papel_de_cargo_publico(store, tmp_path):
    """Si la misma ficha tuviera otra arista —una subvención, por ejemplo—,
    esa arista no sale por esta puerta ni por ninguna."""
    _ingerir(
        store,
        "boe",
        _nombramiento_boe("Sara Hernández del Olmo", "BOE-A-1", "Directora General de X"),
        b"<documento>1</documento>",
    )
    # La MISMA ficha que creó el conector: si la clave no coincidiera, la
    # prueba estaría mirando a otra persona y pasaría sin probar nada.
    clave = f"boe:persona:{clave_boe('Sara Hernández del Olmo')}"
    _ingerir(
        store,
        "bdns",
        Normalizado(
            entidades=[
                EntidadNormalizada("PublicBody", "Ayuntamiento de Prueba", "test:ayto"),
                EntidadNormalizada("Person", "Sara Hernández del Olmo", clave),
            ],
            aristas=[
                AristaNormalizada(
                    "Payment",
                    "test:ayto",
                    clave,
                    "test:pago",
                    confidence=1.0,
                    amount=None,
                )
            ],
        ),
        b"<documento>3</documento>",
    )
    grafo, _, cargos = _volcar(store, tmp_path)

    texto = json.dumps(cargos, ensure_ascii=False)
    assert "Ayuntamiento de Prueba" not in texto
    assert len(cargos["personas"][0]["periodos"]) == 1
    assert "Sara Hernández del Olmo" not in json.dumps(grafo, ensure_ascii=False)


@con_base
def test_el_nombre_del_cargo_se_sigue_tapando_en_el_texto_del_grafo(store, tmp_path):
    """Publicar a alguien como alto cargo no destapa su nombre en otros
    textos: el que aparece en la descripción de un contrato puede ser un
    homónimo, y ahí manda la regla general."""
    _ingerir(
        store,
        "boe",
        _nombramiento_boe("Sara Hernández del Olmo", "BOE-A-1", "Directora General de X"),
        b"<documento>1</documento>",
    )
    _ingerir(
        store,
        "bdns",
        Normalizado(
            entidades=[
                EntidadNormalizada("PublicBody", "Ayuntamiento de Prueba", "test:ayto"),
                EntidadNormalizada(
                    "Company",
                    "Teatro Estable SL",
                    "test:teatro",
                    properties={"descripcion": "Obra de Sara Hernández del Olmo"},
                ),
            ],
            aristas=[
                AristaNormalizada(
                    "Payment",
                    "test:ayto",
                    "test:teatro",
                    "test:pago2",
                    confidence=1.0,
                )
            ],
        ),
        b"<documento>4</documento>",
    )
    grafo, _, _ = _volcar(store, tmp_path)
    teatro = next(n for n in grafo["nodes"] if n["caption"] == "Teatro Estable SL")
    assert "Sara Hernández" not in teatro["properties"]["descripcion"]


@con_base
def test_la_fuente_de_los_cargos_no_se_anuncia_como_caida(store, tmp_path):
    """El BOE no aporta nodos al grafo —van a cargos.json—, y contarlo como
    cero hacía que la web dijera «hoy falta el BOE» el día que respondió."""
    _ingerir(
        store,
        "boe",
        _nombramiento_boe("Sara Hernández del Olmo", "BOE-A-1", "Directora General de X"),
        b"<documento>1</documento>",
    )
    grafo, _, _ = _volcar(store, tmp_path)
    boe = next(f for f in grafo["fuentes"] if f["id"] == "boe")
    assert boe["entidades"] == 1
    assert grafo["cargos"]["personas"] == 1 and grafo["cargos"]["actos"] == 1


@con_base
def test_el_puesto_se_enlaza_con_el_organo_del_estado_que_dirigia(store, tmp_path):
    """El director general de Carreteras estaba al frente de la Dirección
    General de Carreteras, que es quien adjudica. Y sólo de la del Estado."""
    _ingerir(
        store,
        "boe",
        _nombramiento_boe("Juan Pérez García", "BOE-A-9", "Director General de Carreteras"),
        b"<documento>9</documento>",
    )
    _ingerir(
        store,
        "bdns",
        Normalizado(
            entidades=[
                EntidadNormalizada(
                    "PublicBody",
                    "Dirección General de Carreteras",
                    "test:dgc-estado",
                    properties={
                        "jerarquia_placsp": [
                            "Sector Público",
                            "ADMINISTRACIÓN GENERAL DEL ESTADO",
                            "Ministerio de Transportes y Movilidad Sostenible",
                        ]
                    },
                ),
                EntidadNormalizada("Company", "Asfaltos SA", "test:asfaltos"),
            ],
            aristas=[AristaNormalizada("Payment", "test:dgc-estado", "test:asfaltos", "p1", 1.0)],
        ),
        b"<documento>10</documento>",
    )
    _, _, cargos = _volcar(store, tmp_path)
    periodo = cargos["personas"][0]["periodos"][0]
    assert periodo["organo"] == {
        "clave": "test:dgc-estado",
        "nombre": "Dirección General de Carreteras",
    }
    assert cargos["organos"]["test:dgc-estado"][0]["nombre"] == "Juan Pérez García"


@con_base
def test_un_organo_autonomico_con_el_mismo_nombre_no_se_enlaza(store, tmp_path):
    _ingerir(
        store,
        "boe",
        _nombramiento_boe("Juan Pérez García", "BOE-A-9", "Director General de Carreteras"),
        b"<documento>9</documento>",
    )
    _ingerir(
        store,
        "bdns",
        Normalizado(
            entidades=[
                EntidadNormalizada(
                    "PublicBody",
                    "Dirección General de Carreteras",
                    "test:dgc-madrid",
                    properties={"jerarquia_placsp": ["Comunidad de Madrid"]},
                ),
                EntidadNormalizada("Company", "Asfaltos SA", "test:asfaltos"),
            ],
            aristas=[AristaNormalizada("Payment", "test:dgc-madrid", "test:asfaltos", "p1", 1.0)],
        ),
        b"<documento>10</documento>",
    )
    _, _, cargos = _volcar(store, tmp_path)
    assert "organo" not in cargos["personas"][0]["periodos"][0]
    assert cargos["organos"] == {}


# --- Oficina de Conflictos de Intereses -------------------------------------


def _autorizacion_oci(
    nombre: str, cargo: str, cese: str, actividad: str, fecha: str
) -> Normalizado:
    """Lo que produce el conector de la OCI para una fila de su tabla."""
    from sinapsis_ingest.connectors.oci import OCIConnector

    registro = ParsedRecord(
        raw_content_hash="x",
        extractor_version=OCIConnector.extractor_version,
        data={
            "nombre": nombre,
            "cargo": cargo,
            "ministerio": "HACIENDA",
            "fecha_cese": cese,
            "actividad": actividad,
            "fecha_autorizacion": fecha,
            "curriculum": "",
            "url": "https://transparencia.gob.es/x",
        },
    )
    n = OCIConnector().normalize(registro)
    assert n is not None
    return n


@pytest.fixture
def store_oci(store):
    store.upsert_source(Source(id="oci", name="OCI", url="https://ejemplo.test"))
    store.conn.commit()
    return store


@con_base
def test_una_autorizacion_de_la_oci_sale_en_cargos(store_oci, tmp_path):
    _ingerir(
        store_oci,
        "oci",
        _autorizacion_oci(
            "MONTORO ROMERO, CRISTOBAL",
            "MINISTRO DE HACIENDA Y FUNCION PUBLICA",
            "2018/06/01",
            "CONSEJERO-ASESOR DE LA JUNTA DIRECTIVA DEL FORO",
            "2020/01/09",
        ),
        b"<html>1</html>",
    )
    grafo, indice, cargos = _volcar(store_oci, tmp_path)
    [persona] = cargos["personas"]
    assert persona["nombre"] == "Cristobal Montoro Romero"
    [periodo] = persona["periodos"]
    assert periodo["hasta"] == "2018-06-01" and "desde" not in periodo
    assert periodo["fuente"] == "oci"
    [autorizacion] = persona["autorizaciones"]
    assert autorizacion["actividad"] == "CONSEJERO-ASESOR DE LA JUNTA DIRECTIVA DEL FORO"
    assert autorizacion["fecha"] == "2020-01-09"
    # Ni la persona ni el texto de la autorización entran en el mapa del
    # dinero ni en el buscador general.
    assert not grafo["nodes"]
    assert not [e for e in indice["entidades"] if e["clave"].startswith("oci:")]
    assert next(f for f in grafo["fuentes"] if f["id"] == "oci")["entidades"] == 1


@con_base
def test_la_misma_persona_en_el_boe_y_la_oci_se_une_con_nombre_y_fecha(store_oci, tmp_path):
    _ingerir(
        store_oci,
        "boe",
        _cese_boe("Cristóbal Montoro Romero", "BOE-A-2", "Ministro de Hacienda", "20180602"),
        b"<documento>2</documento>",
    )
    _ingerir(
        store_oci,
        "oci",
        _autorizacion_oci(
            "MONTORO ROMERO, CRISTOBAL",
            "MINISTRO DE HACIENDA",
            "2018/06/01",
            "ASESOR",
            "2020/01/09",
        ),
        b"<html>1</html>",
    )
    _, _, cargos = _volcar(store_oci, tmp_path)
    [persona] = cargos["personas"]
    assert persona["clave"].startswith("boe:")
    [autorizacion] = persona["autorizaciones"]
    assert autorizacion["cruce"] == "nombre y fecha de cese"


@con_base
def test_con_el_nombre_solo_no_se_une(store_oci, tmp_path):
    """Mismo nombre, cese de otro año: pueden ser dos personas."""
    _ingerir(
        store_oci,
        "boe",
        _cese_boe("Cristóbal Montoro Romero", "BOE-A-2", "Ministro de Hacienda", "20120101"),
        b"<documento>2</documento>",
    )
    _ingerir(
        store_oci,
        "oci",
        _autorizacion_oci(
            "MONTORO ROMERO, CRISTOBAL",
            "MINISTRO DE HACIENDA",
            "2018/06/01",
            "ASESOR",
            "2020/01/09",
        ),
        b"<html>1</html>",
    )
    _, _, cargos = _volcar(store_oci, tmp_path)
    assert len(cargos["personas"]) == 2


@con_base
def test_la_autorizacion_nombra_una_sociedad_del_mapa(store_oci, tmp_path):
    _ingerir(
        store_oci,
        "oci",
        _autorizacion_oci(
            "SANCHEZ GONZALEZ, LUIS MARIA",
            "DIRECTOR DEL DEPARTAMENTO DE INSPECCION FINANCIERA",
            "2018/07/02",
            "EL CORTE INGLES, S.A.",
            "2019/11/21",
        ),
        b"<html>1</html>",
    )
    _ingerir(
        store_oci,
        "bdns",
        Normalizado(
            entidades=[
                EntidadNormalizada("PublicBody", "Ministerio de Prueba", "test:min"),
                EntidadNormalizada("Company", "El Corte Inglés, S.A.", "nif:A28017895"),
            ],
            aristas=[AristaNormalizada("Payment", "test:min", "nif:A28017895", "p1", 1.0)],
        ),
        b"<documento>3</documento>",
    )
    grafo, _, cargos = _volcar(store_oci, tmp_path)
    [autorizacion] = cargos["personas"][0]["autorizaciones"]
    assert autorizacion["empresa"] == {"clave": "nif:A28017895", "nombre": "El Corte Inglés, S.A."}
    assert cargos["empresas"]["nif:A28017895"][0]["nombre"] == "Luis Maria Sanchez Gonzalez"
    # Y viaja con el grafo, para la portada.
    [cruce] = grafo["cargos"]["cruces"]
    assert cruce["empresa"]["clave"] == "nif:A28017895"
    assert cruce["fecha"] == "2019-11-21"
    assert grafo["cargos"]["nCruces"] == 1


def test_una_sociedad_se_reconoce_entera_y_sin_dudas():
    from sinapsis_ingest.exportar_cargos import _palabras, empresa_en

    fichas = [
        ("nif:B1", "EY ABOGADOS, S.L.P."),
        ("nif:A2", "LABORATORIOS FARMACEUTICOS ROVI, S.A."),
        ("nif:A3", "GRUPO X, S.A."),
        ("nif:A4", "X, S.A."),
        ("nif:B5", "DUPLICADA, S.L."),
        ("nif:B6", "Duplicada SL"),
    ]
    # Las claves se construyen igual que en el volcado.
    mapa: dict[str, list[tuple[str, str]]] = {}
    for clave, nombre in fichas:
        mapa.setdefault(" ".join(_palabras(nombre)), []).append((clave, nombre))
    assert empresa_en("SOCIO DE EY ABOGADOS, S.L.P.", mapa)["clave"] == "nif:B1"
    assert (
        empresa_en(
            "MIEMBRO DEL CONSEJO DE ADMINISTRACION DE LABORATORIOS FARMACEUTICOS ROVI, S.A.", mapa
        )["clave"]
        == "nif:A2"
    )
    # La más larga manda: «GRUPO X, S.A.» no es «X, S.A.».
    assert empresa_en("CONSEJERO DE GRUPO X, S.A.", mapa)["clave"] == "nif:A3"
    # Pegado a otra palabra, es otra sociedad. Salió así con los datos reales.
    otras = {" ".join(_palabras("BEYOND SOLUCIONES Y SERVICIOS S.L.")): [("nif:B7", "BEYOND")]}
    assert empresa_en("BESS-BEYOND SOLUCIONES Y SERVICIOS, S.L.", otras) is None
    assert empresa_en("ASESOR EN BEYOND SOLUCIONES Y SERVICIOS S.L.", otras)["clave"] == "nif:B7"
    # Dos fichas con el mismo nombre: no se elige.
    assert empresa_en("ASESOR DE DUPLICADA, S.L.", mapa) is None
    # Sin denominación del mapa: nada.
    assert empresa_en("ECONOMISTA POR CUENTA PROPIA", mapa) is None


def test_la_forma_societaria_se_escribe_de_tres_maneras():
    from sinapsis_ingest.exportar_cargos import _palabras, empresa_en

    assert _palabras("REDEIA, S.L.") == _palabras("REDEIA,SL") == ["redeia", "sl"]
    assert _palabras("EY ABOGADOS, S. L. P.") == ["ey", "abogados", "slp"]
    mapa = {"redeia sl": [("nif:B9", "REDEIA, S.L.")]}
    assert empresa_en("REDEIA,SL", mapa)["clave"] == "nif:B9"


# --- Congreso de los Diputados -------------------------------------------------


def _diputado(nombre: str, formacion: str, alta: str, baja: str, cargos: list[str]) -> Normalizado:
    from sinapsis_ingest.connectors.congreso import CongresoConnector

    registro = ParsedRecord(
        raw_content_hash="x",
        extractor_version=CongresoConnector.extractor_version,
        data={
            "url": "https://www.congreso.es/x.json",
            "legislatura": 12,
            "nombre": nombre,
            "circunscripcion": "Huelva",
            "formacion": formacion,
            "grupo": "Grupo Parlamentario Popular en el Congreso",
            "alta": alta,
            "baja": baja,
            "cargos_en_biografia": cargos,
        },
    )
    n = CongresoConnector().normalize(registro)
    assert n is not None
    return n


@pytest.fixture
def store_congreso(store):
    store.upsert_source(Source(id="congreso", name="Congreso", url="https://ejemplo.test"))
    store.conn.commit()
    return store


@con_base
def test_un_diputado_se_une_al_alto_cargo_si_su_biografia_nombra_el_cargo(store_congreso, tmp_path):
    _ingerir(
        store_congreso,
        "boe",
        _nombramiento_boe(
            "María Fátima Báñez García", "BOE-A-7", "Ministra de Empleo y Seguridad Social"
        ),
        b"<documento>7</documento>",
    )
    _ingerir(
        store_congreso,
        "congreso",
        _diputado(
            "Báñez García, María Fátima",
            "PP",
            "15/07/2016",
            "21/05/2019",
            ["Ministra de Empleo y Seguridad Social"],
        ),
        b"[1]",
    )
    _, _, cargos = _volcar(store_congreso, tmp_path)
    [persona] = cargos["personas"]
    assert persona["clave"].startswith("boe:")
    diputada = next(p for p in persona["periodos"] if p.get("fuente") == "congreso")
    assert diputada["formacion"] == "PP"
    assert diputada["desde"] == "2016-07-15" and diputada["hasta"] == "2019-05-21"
    assert diputada["cruce"] == "nombre y cargo en su biografía del Congreso"


@con_base
def test_con_el_nombre_solo_un_diputado_no_se_une_ni_se_publica(store_congreso, tmp_path):
    _ingerir(
        store_congreso,
        "boe",
        _nombramiento_boe(
            "María Fátima Báñez García", "BOE-A-7", "Ministra de Empleo y Seguridad Social"
        ),
        b"<documento>7</documento>",
    )
    _ingerir(
        store_congreso,
        "congreso",
        _diputado("Báñez García, María Fátima", "PP", "15/07/2016", "", ["Directora General de X"]),
        b"[1]",
    )
    grafo, _, cargos = _volcar(store_congreso, tmp_path)
    [persona] = cargos["personas"]
    assert all(p.get("fuente") != "congreso" for p in persona["periodos"])
    # El diputado sí aportó: se leyó, aunque no se publique.
    assert next(f for f in grafo["fuentes"] if f["id"] == "congreso")["entidades"] == 1


def _declaracion(nombre: str, empleador: str, descripcion: str, periodo: str) -> Normalizado:
    from sinapsis_ingest.connectors.congreso import CongresoConnector

    n = CongresoConnector().normalize(
        ParsedRecord(
            raw_content_hash="x",
            extractor_version=CongresoConnector.extractor_version,
            data={
                "tipo": "actividad",
                "url": "https://www.congreso.es/docacteco.json",
                "nombre": nombre,
                "empleador": empleador,
                "sector": "Privado",
                "periodo": periodo,
                "descripcion": descripcion,
                "fecha_registro": "03/08/2023",
            },
        )
    )
    assert n is not None
    return n


def _sociedad_del_mapa(store: Store, nombre: str, nif: str) -> None:
    """Una sociedad que cobra de un órgano, como las del mapa del dinero."""
    _ingerir(
        store,
        "bdns",
        Normalizado(
            entidades=[
                EntidadNormalizada("PublicBody", "Ayuntamiento de Pruebas", "nif:P0000000A"),
                EntidadNormalizada("Company", nombre, f"nif:{nif}", nif=nif),
            ],
            aristas=[
                AristaNormalizada(
                    "Payment",
                    "nif:P0000000A",
                    f"nif:{nif}",
                    f"pago:{nif}",
                    confidence=1.0,
                    amount=1000,
                    currency="EUR",
                    start_date=date(2025, 1, 1),
                )
            ],
        ),
        f"<pago>{nif}</pago>".encode(),
    )


@con_base
def test_un_diputado_con_declaracion_sale_y_su_empleador_se_cruza(store_congreso, tmp_path):
    _sociedad_del_mapa(store_congreso, "UNIPREX, S.A.U.", "A28782936")
    _ingerir(
        store_congreso,
        "congreso",
        _diputado("Cobo Vega, Manuel", "PP", "17/08/2023", "", []),
        b"[15]",
    )
    _ingerir(
        store_congreso,
        "congreso",
        _declaracion("Cobo Vega,Manuel", "UNIPREX S.A.U.", "COLABORADOR", "2019-2021"),
        b"[declaracion]",
    )
    grafo, indice, cargos = _volcar(store_congreso, tmp_path)
    [persona] = cargos["personas"]
    assert persona["clave"].startswith("congreso:")
    [declarada] = persona["declaraciones"]
    assert declarada["empleador"] == "UNIPREX S.A.U."
    assert declarada["periodo"] == "2019-2021"
    assert declarada["empresa"]["nombre"] == "UNIPREX, S.A.U."
    [quien] = cargos["declarantes"][declarada["empresa"]["clave"]]
    assert quien["nombre"] == "Manuel Cobo Vega" and quien["formacion"] == "PP"
    assert grafo["cargos"]["nDeclarados"] == 1
    assert grafo["cargos"]["declarados"][0]["empresa"]["nombre"] == "UNIPREX, S.A.U."
    # Ni la persona ni el texto declarado entran en el mapa del dinero.
    # (El resumen de la portada, `cargos`, es aparte: viene de esta puerta.)
    mapa = {k: v for k, v in grafo.items() if k != "cargos"}
    texto = json.dumps(mapa, ensure_ascii=False) + json.dumps(indice, ensure_ascii=False)
    assert "congreso:" not in texto
    assert "UNIPREX S.A.U." not in texto
    assert "Cobo" not in texto


@con_base
def test_un_diputado_sin_declaracion_ni_cargo_no_sale(store_congreso, tmp_path):
    _ingerir(
        store_congreso,
        "congreso",
        _diputado("Pérez Gil, Ana", "PSOE", "17/08/2023", "", []),
        b"[15]",
    )
    _, _, cargos = _volcar(store_congreso, tmp_path)
    assert cargos["personas"] == []


@con_base
def test_lo_declarado_no_se_cruza_consigo_mismo(store_congreso, tmp_path):
    """El texto declarado se guarda como una entidad aparte; sin excluirla,
    «X, S.L.» declarado sería él mismo una sociedad del mapa."""
    _ingerir(
        store_congreso,
        "congreso",
        _diputado("Pérez Gil, Ana", "PSOE", "17/08/2023", "", []),
        b"[15]",
    )
    _ingerir(
        store_congreso,
        "congreso",
        _declaracion("Pérez Gil,Ana", "ACME ASESORES, S.L.", "GERENTE", "2019-2023"),
        b"[declaracion]",
    )
    _, _, cargos = _volcar(store_congreso, tmp_path)
    [persona] = cargos["personas"]
    [declarada] = persona["declaraciones"]
    assert "empresa" not in declarada
    assert cargos["declarantes"] == {}


@con_base
def test_las_fechas_de_lo_leido_son_solo_las_del_boe(store_congreso, tmp_path):
    _ingerir(
        store_congreso,
        "boe",
        _nombramiento_boe(
            "María Fátima Báñez García", "BOE-A-7", "Ministra de Empleo y Seguridad Social"
        ),
        b"<documento>7</documento>",
    )
    _ingerir(
        store_congreso,
        "congreso",
        _diputado(
            "Báñez García, María Fátima",
            "PP",
            "15/07/2008",
            "21/05/2019",
            ["Ministra de Empleo y Seguridad Social"],
        ),
        b"[1]",
    )
    _, _, cargos = _volcar(store_congreso, tmp_path)
    # El alta de 2008 no es un acto del BOE leído.
    assert cargos["actosDesde"] == cargos["actosHasta"]
    assert cargos["nActos"] == 1


def test_sociedad_mercantil_es_la_que_acaba_en_su_forma():
    assert es_sociedad_mercantil("URBASER, S.A.")
    assert es_sociedad_mercantil("UNIPREX S.A.U")
    assert es_sociedad_mercantil("SEDENA, S.L.")
    # Personas jurídicas, pero no sociedades: no van en «sociedades que cobran».
    assert not es_sociedad_mercantil("UNIVERSIDAD DE CANTABRIA")
    assert not es_sociedad_mercantil("Fundación ONCE")
    assert not es_sociedad_mercantil("")


@con_base
def test_en_la_portada_solo_sociedades_y_una_vez_por_persona(store_congreso, tmp_path):
    _sociedad_del_mapa(store_congreso, "UNIVERSIDAD DE CANTABRIA", "Q3918001C")
    _sociedad_del_mapa(store_congreso, "URBASER, S.A.", "A79524054")
    _ingerir(
        store_congreso,
        "congreso",
        _diputado("Pérez Gil, Ana", "PSOE", "17/08/2023", "", []),
        b"[15]",
    )
    for i, (empleador, periodo) in enumerate(
        [
            ("UNIVERSIDAD DE CANTABRIA", "2010-2015"),
            ("UNIVERSIDAD DE CANTABRIA", "2015-2023"),
            ("URBASER SA", "2005-2010"),
            ("URBASER SA", "2001-2005"),
        ]
    ):
        _ingerir(
            store_congreso,
            "congreso",
            _declaracion("Pérez Gil,Ana", empleador, "TÉCNICA", periodo),
            f"[declaracion {i}]".encode(),
        )
    grafo, _, cargos = _volcar(store_congreso, tmp_path)
    [persona] = cargos["personas"]
    # En su ficha, todo lo que declaró.
    assert len(persona["declaraciones"]) == 4
    # En el panel de cada una, una vez.
    assert all(len(v) == 1 for v in cargos["declarantes"].values())
    assert len(cargos["declarantes"]) == 2
    # En la portada, sólo la sociedad, una vez.
    [cruce] = grafo["cargos"]["declarados"]
    assert cruce["empresa"]["nombre"] == "URBASER, S.A."


def test_nombre_natural():
    assert nombre_natural("Báñez García, María Fátima") == "María Fátima Báñez García"
    assert nombre_natural("Ferrero y de Loma-Osorio, Gabriel") == "Gabriel Ferrero y de Loma-Osorio"
    # Lo que no tiene la forma «Apellidos, Nombre» se deja como está.
    assert nombre_natural("María Fátima Báñez García") == "María Fátima Báñez García"
    assert nombre_natural("A, B, C") == "A, B, C"
    assert nombre_natural("Báñez García,") == "Báñez García,"


# --- de punta a punta, con las muestras reales ----------------------------------


def _ingerir_real(store: Store, conector: Any, raw: RawDocument) -> None:
    ingerir_documento(store, conector, raw, Resultado())
    store.conn.commit()


@con_base
def test_los_presidentes_reales_se_unen_a_su_escano(store_congreso, tmp_path):
    """Los Reales Decretos que nombran a Rajoy (2011) y a Sánchez (2018), y los
    diputados de la XII y la XIV, por los conectores de verdad."""
    from sinapsis_ingest.connectors.congreso import CongresoConnector

    golden = Path(__file__).parent / "golden"
    for identificador in (
        "BOE-A-2011-19861",
        "BOE-A-2011-19942",
        "BOE-A-2018-7400",
        "BOE-A-2018-7577",
    ):
        _ingerir_real(
            store_congreso,
            BOEConnector(),
            RawDocument(
                source_id="boe",
                url=f"https://www.boe.es/diario_boe/xml.php?id={identificador}",
                content=(golden / "boe_disposiciones" / f"{identificador}.xml").read_bytes(),
                media_type="application/xml",
            ),
        )
    for fichero in ("odsDiputados12__20260925050024.json", "odsDiputados14__20260925050256.json"):
        _ingerir_real(
            store_congreso,
            CongresoConnector(),
            RawDocument(
                source_id="congreso",
                url=f"https://www.congreso.es/webpublica/opendata/diputados/{fichero}",
                content=(golden / "congreso" / fichero).read_bytes(),
                media_type="application/json",
            ),
        )
    _, _, cargos = _volcar(store_congreso, tmp_path)
    por_nombre = {p["nombre"]: p for p in cargos["personas"]}
    for nombre, formacion in (
        ("Mariano Rajoy Brey", "PP"),
        ("Pedro Sánchez Pérez-Castejón", "PSOE"),
    ):
        persona = por_nombre[nombre]
        assert persona["clave"].startswith("boe:")
        assert any(p.get("puesto") == "Presidente del Gobierno" for p in persona["periodos"])
        mandatos = [p for p in persona["periodos"] if p.get("fuente") == "congreso"]
        assert mandatos, nombre
        assert {p["formacion"] for p in mandatos} == {formacion}

    # Y con eso, bajo qué Gobierno se nombró a cada ministro: la fecha del
    # Real Decreto contra las presidencias leídas.
    #
    # La formación de Rajoy en diciembre de 2011 NO se sabe con esta muestra:
    # su único escaño guardado es el de la XII, de 2016, y lo posterior no se
    # proyecta hacia atrás. Con la X leída, sí.
    assert [(x["nombre"], x["formacion"]) for x in cargos["presidencias"]] == [
        ("Mariano Rajoy Brey", ""),
        ("Pedro Sánchez Pérez-Castejón", "PSOE"),
    ]
    banez = por_nombre["María Fátima Báñez García"]
    [ministra] = [p for p in banez["periodos"] if "fuente" not in p]
    assert ministra["gobierno"] == {
        "persona": por_nombre["Mariano Rajoy Brey"]["clave"],
        "nombre": "Mariano Rajoy Brey",
    }
    montero = por_nombre["María Jesús Montero Cuadrado"]
    [ministra] = [p for p in montero["periodos"] if "fuente" not in p]
    assert ministra["gobierno"]["nombre"] == "Pedro Sánchez Pérez-Castejón"
    assert ministra["gobierno"]["formacion"] == "PSOE"
    # El presidente no lleva «nombrado bajo sí mismo».
    rajoy = por_nombre["Mariano Rajoy Brey"]
    assert all(
        "gobierno" not in p
        for p in rajoy["periodos"]
        if p.get("puesto") == "Presidente del Gobierno"
    )


@con_base
def test_la_biografia_de_una_legislatura_no_tapa_la_de_otra(store_congreso, tmp_path):
    _ingerir(
        store_congreso,
        "boe",
        _nombramiento_boe(
            "María Fátima Báñez García", "BOE-A-7", "Ministra de Empleo y Seguridad Social"
        ),
        b"<documento>7</documento>",
    )
    # La XII menciona el ministerio; una legislatura leída después, otra cosa.
    _ingerir(
        store_congreso,
        "congreso",
        _diputado(
            "Báñez García, María Fátima",
            "PP",
            "15/07/2016",
            "21/05/2019",
            ["Ministra de Empleo y Seguridad Social"],
        ),
        b"[12]",
    )
    _ingerir(
        store_congreso,
        "congreso",
        _diputado("Báñez García, María Fátima", "PP", "21/05/2019", "", ["Portavoz adjunta"]),
        b"[13]",
    )
    _, _, cargos = _volcar(store_congreso, tmp_path)
    [persona] = cargos["personas"]
    assert persona["clave"].startswith("boe:")
    assert len([p for p in persona["periodos"] if p.get("fuente") == "congreso"]) == 2


def test_gobierno_en():
    from sinapsis_ingest.exportar_cargos import gobierno_en

    presidencias = [
        {"persona": "z", "nombre": "Z", "desde": None, "hasta": "2011-12-21", "formacion": "PSOE"},
        {
            "persona": "r",
            "nombre": "R",
            "desde": "2011-12-21",
            "hasta": "2018-06-02",
            "formacion": "PP",
        },
        {"persona": "s", "nombre": "S", "desde": "2018-06-02", "hasta": None, "formacion": ""},
    ]
    assert gobierno_en(presidencias, "2011-12-01")["nombre"] == "Z"
    # El día del relevo, ya el nuevo.
    assert gobierno_en(presidencias, "2011-12-21")["nombre"] == "R"
    assert gobierno_en(presidencias, "2018-06-02")["nombre"] == "S"
    # Sin formación conocida, no se pone.
    assert "formacion" not in gobierno_en(presidencias, "2020-01-01")
    # Antes de lo leído, nada.
    assert gobierno_en(presidencias[1:], "2010-01-01") is None


# --- del órgano que dirigió a la sociedad donde se le autorizó ------------------


def test_puesto_de_la_oci():
    from sinapsis_ingest.exportar_cargos import puesto_de_la_oci

    assert puesto_de_la_oci("D. GRAL. DE ORDENACION PROFESIONAL") == (
        "Director General de ordenacion profesional"
    )
    assert (
        puesto_de_la_oci("S.E. PARA LA AGENDA 2030") == "Secretario de Estado para la agenda 2030"
    )
    assert puesto_de_la_oci("DIRECTORA GENERAL DE CARRETERAS") == "Director General de carreteras"
    assert puesto_de_la_oci("SUBSECRETARIA DE HACIENDA") == "Subsecretario de hacienda"
    # Lo que no dirige un órgano, nada: un embajador, una consejera de la CNMC.
    assert puesto_de_la_oci("EMBAJADOR EN EL REINO DE MARRUECOS") == ""
    assert puesto_de_la_oci("CONSEJERA DE LA CNMC") == ""


def _organo_que_paga(store: Store, empresa: str, nif: str, importe: float) -> None:
    """La Dirección General de Carreteras del Estado, que paga a `empresa`."""
    _ingerir(
        store,
        "bdns",
        Normalizado(
            entidades=[
                EntidadNormalizada(
                    "PublicBody",
                    "Dirección General de Carreteras",
                    "test:dgc-estado",
                    properties={
                        "jerarquia_placsp": [
                            "Sector Público",
                            "ADMINISTRACIÓN GENERAL DEL ESTADO",
                            "Ministerio de Transportes y Movilidad Sostenible",
                        ]
                    },
                ),
                EntidadNormalizada("Company", empresa, f"nif:{nif}", nif=nif),
            ],
            aristas=[
                AristaNormalizada(
                    "Payment",
                    "test:dgc-estado",
                    f"nif:{nif}",
                    f"pago:{nif}",
                    confidence=1.0,
                    amount=importe,
                    currency="EUR",
                    start_date=date(2016, 3, 1),
                )
            ],
        ),
        f"<pago>{nif}</pago>".encode(),
    )


@con_base
def test_el_organo_que_dirigio_pago_a_la_sociedad_donde_se_le_autorizo(store_oci, tmp_path):
    _organo_que_paga(store_oci, "ASFALTOS DEL NORTE, S.A.", "A11111111", 250000)
    _ingerir(
        store_oci,
        "oci",
        _autorizacion_oci(
            "PEREZ GIL, ANA",
            "D. GRAL. DE CARRETERAS",
            "2018/06/20",
            "CONSEJERA DE ASFALTOS DEL NORTE, S.A.",
            "2019/01/15",
        ),
        b"<html>1</html>",
    )
    grafo, _, cargos = _volcar(store_oci, tmp_path)
    [persona] = cargos["personas"]
    # El cargo abreviado de la OCI lleva a su órgano, con el mismo rigor que el BOE.
    [periodo] = persona["periodos"]
    assert periodo["organo"]["clave"] == "test:dgc-estado"
    assert cargos["organos"]["test:dgc-estado"][0]["fuente"] == "oci"
    # Y el órgano pagó a la sociedad en la que se le autorizó a trabajar.
    [autorizacion] = persona["autorizaciones"]
    [del_organo] = autorizacion["delOrgano"]
    assert del_organo["organo"]["nombre"] == "Dirección General de Carreteras"
    assert float(del_organo["importe"]) == 250000
    assert del_organo["pagos"] == 1 and del_organo["adjudicaciones"] == 0
    assert del_organo["desde"] == "2016-03-01"
    # Viaja con el cruce de la portada, y al panel de la sociedad.
    [cruce] = grafo["cargos"]["cruces"]
    assert float(cruce["delOrgano"][0]["importe"]) == 250000
    [en_la_sociedad] = cargos["empresas"]["nif:A11111111"]
    assert en_la_sociedad["delOrgano"][0]["organo"]["clave"] == "test:dgc-estado"


@con_base
def test_sin_dinero_del_organo_a_la_sociedad_no_se_dice_nada(store_oci, tmp_path):
    _organo_que_paga(store_oci, "OTRA EMPRESA, S.L.", "B22222222", 1000)
    _sociedad_del_mapa(store_oci, "ASFALTOS DEL NORTE, S.A.", "A11111111")
    _ingerir(
        store_oci,
        "oci",
        _autorizacion_oci(
            "PEREZ GIL, ANA",
            "D. GRAL. DE CARRETERAS",
            "2018/06/20",
            "CONSEJERA DE ASFALTOS DEL NORTE, S.A.",
            "2019/01/15",
        ),
        b"<html>1</html>",
    )
    _, _, cargos = _volcar(store_oci, tmp_path)
    [autorizacion] = cargos["personas"][0]["autorizaciones"]
    assert autorizacion["empresa"]["clave"] == "nif:A11111111"
    assert "delOrgano" not in autorizacion


# --- las presidencias autonómicas ------------------------------------------------


@pytest.mark.parametrize(
    ("puesto", "comunidad"),
    [
        ("Presidente de la Junta de Andalucía", "Andalucía"),
        ("Presidente de Aragón", "Aragón"),
        ("Presidente de la Comunidad Autónoma de Extremadura", "Extremadura"),
        ("Presidente de la Junta de Castilla y León", "Castilla y León"),
        ("Presidente de la Junta de Comunidades de Castilla-La Mancha", "Castilla-La Mancha"),
        ("Presidente de la Generalitat de Cataluña", "Cataluña"),
        ("Presidente de la Generalitat Valenciana", "Comunidad Valenciana"),
        ("Presidente del Gobierno Vasco", "País Vasco"),
        ("Presidente de la Comunidad Autónoma de la Región de Murcia", "Murcia"),
        ("Presidente de la Comunidad Autónoma de La Rioja", "La Rioja"),
        ("Presidente de las Illes Balears", "Baleares"),
        ("Presidente de la Ciudad de Ceuta", "Ceuta"),
        # Lo que no es, entero, la presidencia de una comunidad.
        ("Presidente de la Generalitat", ""),
        ("Presidente de la Autoridad Portuaria de Baleares", ""),
        ("Presidente del Gobierno", ""),
        ("Presidente del Servicio Andaluz de Salud", ""),
        ("Delegado del Gobierno en la Comunidad Autónoma de Cantabria", ""),
    ],
)
def test_comunidad_de_la_presidencia(puesto, comunidad):
    from sinapsis_ingest.exportar_cargos import comunidad_de_la_presidencia

    assert comunidad_de_la_presidencia(puesto) == comunidad


@con_base
def test_las_presidencias_autonomicas_salen_por_comunidad_y_sin_gobierno_del_estado(
    store, tmp_path
):
    _ingerir(
        store,
        "boe",
        _nombramiento_boe(
            "Juan Manuel Moreno Bonilla", "BOE-A-1", "Presidente de la Junta de Andalucía"
        ),
        b"<documento>1</documento>",
    )
    _ingerir(
        store,
        "boe",
        _nombramiento_boe("Pedro Sánchez Pérez-Castejón", "BOE-A-2", "Presidente del Gobierno"),
        b"<documento>2</documento>",
    )
    grafo, _, cargos = _volcar(store, tmp_path)
    [andalucia] = cargos["presidenciasAutonomicas"]["Andalucía"]
    assert andalucia["nombre"] == "Juan Manuel Moreno Bonilla"
    assert (
        grafo["cargos"]["presidenciasAutonomicas"]["Andalucía"][0]["persona"]
        == andalucia["persona"]
    )
    # Lo elige el parlamento andaluz: nada de «nombramiento con el Gobierno de …».
    moreno = next(p for p in cargos["personas"] if p["nombre"] == "Juan Manuel Moreno Bonilla")
    assert all("gobierno" not in p for p in moreno["periodos"])


# --- el puente de las siglas (Senado) ------------------------------------------------


def _partidos_del_senado(store: Store) -> None:
    from sinapsis_ingest.connectors.senado import SenadoConnector

    store.upsert_source(Source(id="senado", name="Senado", url="https://ejemplo.test"))
    store.conn.commit()
    xml = (Path(__file__).parent / "golden" / "senado" / "grupos-y-partidos-xv.xml").read_bytes()
    ingerir_documento(
        store,
        SenadoConnector(),
        RawDocument(
            source_id="senado",
            url="https://www.senado.es/web/ficopendataservlet?tipoFich=4&legis=15",
            content=xml,
            media_type="application/xml",
            metadata={"legislatura": 15},
        ),
        Resultado(),
    )
    store.conn.commit()


def _partido_del_mapa(store: Store, nombre: str, nif: str) -> None:
    _ingerir(
        store,
        "bdns",
        Normalizado(
            entidades=[
                EntidadNormalizada("PublicBody", "Ministerio del Interior", "test:mir"),
                EntidadNormalizada(
                    "Organization",
                    nombre,
                    f"nif:{nif}",
                    nif=nif,
                    properties={"partido_politico": True},
                ),
            ],
            aristas=[
                AristaNormalizada(
                    "Payment",
                    "test:mir",
                    f"nif:{nif}",
                    f"subvencion:{nif}",
                    confidence=1.0,
                    amount=1000,
                    currency="EUR",
                )
            ],
        ),
        f"<subvencion>{nif}</subvencion>".encode(),
    )


@con_base
def test_la_formacion_del_diputado_lleva_al_partido_del_mapa(store_congreso, tmp_path):
    _partidos_del_senado(store_congreso)
    _partido_del_mapa(store_congreso, "PARTIDO SOCIALISTA OBRERO ESPAÑOL", "G28477727")
    _ingerir(
        store_congreso,
        "congreso",
        _diputado("Pérez Gil, Ana", "PSOE", "17/08/2023", "", []),
        b"[15]",
    )
    _ingerir(
        store_congreso,
        "congreso",
        _declaracion("Pérez Gil,Ana", "AYUNTAMIENTO DE X", "CONCEJALA", "2019-2023"),
        b"[declaracion]",
    )
    grafo, indice, cargos = _volcar(store_congreso, tmp_path)
    assert cargos["formaciones"] == {
        "PSOE": {
            "nombre": "PARTIDO SOCIALISTA OBRERO ESPAÑOL",
            "entidad": {"clave": "nif:G28477727", "nombre": "PARTIDO SOCIALISTA OBRERO ESPAÑOL"},
        }
    }
    # Los partidos del Senado no entran en el mapa: el que cobra ya está.
    texto = json.dumps({k: v for k, v in grafo.items() if k != "cargos"}) + json.dumps(indice)
    assert "senado:" not in texto.replace('"id": "senado"', "")
    # Pero el Senado aportó, y así consta.
    assert next(f for f in grafo["fuentes"] if f["id"] == "senado")["entidades"] > 0


@con_base
def test_sin_partido_en_el_mapa_la_formacion_sale_sin_ficha(store_congreso, tmp_path):
    _partidos_del_senado(store_congreso)
    _ingerir(
        store_congreso,
        "congreso",
        _diputado("Pérez Gil, Ana", "VOX", "17/08/2023", "", []),
        b"[15]",
    )
    _ingerir(
        store_congreso,
        "congreso",
        _declaracion("Pérez Gil,Ana", "AYUNTAMIENTO DE X", "CONCEJALA", "2019-2023"),
        b"[declaracion]",
    )
    _, _, cargos = _volcar(store_congreso, tmp_path)
    [vox] = cargos["formaciones"].values()
    assert "entidad" not in vox
