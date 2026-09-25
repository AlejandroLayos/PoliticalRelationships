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
