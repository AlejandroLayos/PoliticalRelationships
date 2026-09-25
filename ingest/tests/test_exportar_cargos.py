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
from sinapsis_ingest.exportar_cargos import periodos
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
    assert grafo["cargos"] == {"personas": 1, "actos": 1}


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
    assert persona["nombre"] == "Montoro Romero, Cristobal"
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
    _, _, cargos = _volcar(store_oci, tmp_path)
    [autorizacion] = cargos["personas"][0]["autorizaciones"]
    assert autorizacion["empresa"] == {"clave": "nif:A28017895", "nombre": "El Corte Inglés, S.A."}
    assert cargos["empresas"]["nif:A28017895"][0]["nombre"] == "Sanchez Gonzalez, Luis Maria"


def test_una_sociedad_se_reconoce_entera_y_sin_dudas():
    from sinapsis_ingest.exportar_cargos import empresa_en

    mapa = {
        "ey abogados s l p": [("nif:B1", "EY ABOGADOS, S.L.P.")],
        "laboratorios farmaceuticos rovi s a": [
            ("nif:A2", "LABORATORIOS FARMACEUTICOS ROVI, S.A.")
        ],
        "grupo x s a": [("nif:A3", "GRUPO X, S.A.")],
        "x s a": [("nif:A4", "X, S.A.")],
        "duplicada s l": [("nif:B5", "DUPLICADA, S.L."), ("nif:B6", "Duplicada SL")],
    }
    assert empresa_en("SOCIO DE EY ABOGADOS, S.L.P.", mapa)["clave"] == "nif:B1"
    assert (
        empresa_en(
            "MIEMBRO DEL CONSEJO DE ADMINISTRACION DE LABORATORIOS FARMACEUTICOS ROVI, S.A.", mapa
        )["clave"]
        == "nif:A2"
    )
    # La más larga manda: «GRUPO X, S.A.» no es «X, S.A.».
    assert empresa_en("CONSEJERO DE GRUPO X, S.A.", mapa)["clave"] == "nif:A3"
    # Dos fichas con el mismo nombre: no se elige.
    assert empresa_en("ASESOR DE DUPLICADA, S.L.", mapa) is None
    # Sin denominación del mapa: nada.
    assert empresa_en("ECONOMISTA POR CUENTA PROPIA", mapa) is None
