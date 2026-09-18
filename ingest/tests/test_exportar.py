"""Tests del volcado que publica la web.

Lo que se comprueba aquí es una invariante de *forma del grafo*, no de
contenido: **ningún nodo publicado puede quedarse sin aristas, y ninguna
arista puede colgar de un nodo ausente.**

Parece obvio y no lo era. Hasta el 18/9/2026 el volcado elegía las N
entidades de mayor grado y después se quedaba sólo con las aristas cuyos dos
extremos estuvieran dentro. El corte caía por el medio del grafo: un nodo muy
conectado entraba, sus vecinos de grado 1 no, y sus aristas desaparecían. La
instantánea publicada tenía 4.000 nodos repartidos en **1.393 componentes
conexas**, con 548 nodos aislados entre los más conectados de la base. No se
veía ni un núcleo porque no quedaba ninguno que ver.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest

from sinapsis_ingest.exportar import exportar
from sinapsis_ingest.store import Source, Store

DSN = os.environ.get("SINAPSIS_TEST_POSTGRES_DSN", "")

pytestmark = pytest.mark.skipif(not DSN, reason="SINAPSIS_TEST_POSTGRES_DSN sin definir")


def _entidad(store: Store, caption: str, esquema: str = "Company") -> str:
    fila = store.conn.execute(
        """
        INSERT INTO entities (ftm_schema, caption, dedupe_key, properties)
        VALUES (%s, %s, %s, '{}'::jsonb) RETURNING id
        """,
        (esquema, caption, f"test:{uuid.uuid4()}"),
    ).fetchone()
    assert fila is not None
    return str(fila["id"])


def _arista(store: Store, a: str, b: str, importe: str | None) -> None:
    store.conn.execute(
        """
        INSERT INTO relationships
            (ftm_schema, source_entity_id, target_entity_id, amount, currency,
             confidence, status, dedupe_key)
        VALUES ('Payment', %s, %s, %s, %s, 1.0, 'asserted', %s)
        """,
        (a, b, importe, "EUR" if importe else "", f"test:{uuid.uuid4()}"),
    )


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
        s.upsert_source(Source(id="test", name="Test", url="https://ejemplo.test"))
        s.conn.commit()
        yield s


def _exportado(store: Store, tmp_path: Path, **kw) -> dict:
    exportar(store, tmp_path / "g.json", **kw)
    return json.loads((tmp_path / "g.json").read_text(encoding="utf-8"))


def test_ningun_nodo_publicado_se_queda_sin_aristas(store, tmp_path):
    """La invariante que rompía el volcado anterior."""
    # Una cadena larga de pagos: al recortar, el método viejo la troceaba.
    ids = [_entidad(store, f"EMPRESA {i}") for i in range(40)]
    for i in range(39):
        _arista(store, ids[i], ids[i + 1], f"{(i + 1) * 100}.00")
    store.conn.commit()

    d = _exportado(store, tmp_path, max_entidades=20, max_aristas=15)

    publicados = {n["id"] for n in d["nodes"]}
    con_arista = set()
    for a in d["edges"]:
        con_arista.add(a["source"])
        con_arista.add(a["target"])

    aislados = publicados - con_arista
    assert not aislados, f"{len(aislados)} nodos publicados sin ninguna arista"


def test_ninguna_arista_cuelga_de_un_nodo_ausente(store, tmp_path):
    ids = [_entidad(store, f"E{i}") for i in range(30)]
    for i in range(29):
        _arista(store, ids[i], ids[i + 1], f"{i + 1}.00")
    store.conn.commit()

    d = _exportado(store, tmp_path, max_entidades=12, max_aristas=10)

    publicados = {n["id"] for n in d["nodes"]}
    for a in d["edges"]:
        assert a["source"] in publicados, "arista con origen fuera del volcado"
        assert a["target"] in publicados, "arista con destino fuera del volcado"


def test_se_respetan_los_topes(store, tmp_path):
    ids = [_entidad(store, f"E{i}") for i in range(60)]
    for i in range(59):
        _arista(store, ids[i], ids[i + 1], f"{i + 1}.00")
    store.conn.commit()

    d = _exportado(store, tmp_path, max_entidades=20, max_aristas=15)
    assert len(d["nodes"]) <= 20
    assert len(d["edges"]) <= 15


def test_manda_el_dinero_al_elegir_que_publicar(store, tmp_path):
    """Con sitio justo, entra lo caro: es un mapa de dinero."""
    a, b = _entidad(store, "PAGO GRANDE A"), _entidad(store, "PAGO GRANDE B")
    c, e = _entidad(store, "PAGO CHICO A"), _entidad(store, "PAGO CHICO B")
    _arista(store, a, b, "9000000.00")
    _arista(store, c, e, "1.00")
    store.conn.commit()

    d = _exportado(store, tmp_path, max_entidades=2, max_aristas=1)
    captions = {n["caption"] for n in d["nodes"]}
    assert captions == {"PAGO GRANDE A", "PAGO GRANDE B"}


def test_un_grafo_vacio_no_revienta(store, tmp_path):
    d = _exportado(store, tmp_path)
    assert d["nodes"] == []
    assert d["edges"] == []


def test_las_aristas_sin_importe_no_se_quedan_fuera(store, tmp_path):
    """El tejido conectivo entra aunque no lleve dinero.

    Ordenar por importe es correcto para elegir QUÉ publicar, pero deja fuera
    por construcción a las aristas sin cifra — entre ellas el enlace del órgano
    de contratación con su contrato, que no lleva importe a propósito para no
    contar el mismo dinero dos veces. Sin ellas el grafo publicado volvía a
    salir en pedazos aunque ningún nodo estuviera aislado.
    """
    a = _entidad(store, "ORGANISMO", "PublicBody")
    b = _entidad(store, "EXPEDIENTE", "Contract")
    c = _entidad(store, "EMPRESA")
    _arista(store, b, c, "1000000.00")  # la adjudicación lleva el dinero
    # El enlace órgano -> contrato, sin importe.
    store.conn.execute(
        """
        INSERT INTO relationships
            (ftm_schema, source_entity_id, target_entity_id, confidence, status, dedupe_key)
        VALUES ('UnknownLink', %s, %s, 1.0, 'asserted', %s)
        """,
        (a, b, "test:enlace-organo"),
    )
    store.conn.commit()

    d = _exportado(store, tmp_path, max_entidades=10, max_aristas=10)
    esquemas = {e["schema"] for e in d["edges"]}
    assert "UnknownLink" in esquemas, "el enlace sin importe se quedó fuera"
    # Y la que sí lleva dinero sigue estando: el helper la crea como Payment.
    assert "Payment" in esquemas
    assert len(d["edges"]) == 2


def test_la_segunda_pasada_no_mete_nodos_nuevos(store, tmp_path):
    """Sólo une lo que ya está dentro; no ensancha el volcado."""
    ids = [_entidad(store, f"E{i}") for i in range(10)]
    for i in range(9):
        _arista(store, ids[i], ids[i + 1], f"{(i + 1) * 1000}.00")
    store.conn.commit()

    d = _exportado(store, tmp_path, max_entidades=4, max_aristas=3)
    assert len(d["nodes"]) <= 4
    publicados = {n["id"] for n in d["nodes"]}
    for a in d["edges"]:
        assert a["source"] in publicados
        assert a["target"] in publicados


def test_el_organismo_entra_aunque_no_tenga_ninguna_arista_con_dinero(store, tmp_path):
    """El caso real de PLACSP, que dejó el mapa sin organismos.

    El órgano de contratación cuelga de su contrato por una arista sin importe
    —el dinero lo lleva la adjudicación—, así que ordenando por importe no
    entra nunca. Y no basta con admitir después las aristas cuyos dos extremos
    ya estén dentro: es circular, porque el órgano sólo puede entrar por esa
    misma arista.
    """
    organo = _entidad(store, "MINISTERIO", "PublicBody")
    expediente = _entidad(store, "EXPEDIENTE", "Contract")
    empresa = _entidad(store, "EMPRESA")
    _arista(store, expediente, empresa, "5000000.00")
    store.conn.execute(
        """
        INSERT INTO relationships
            (ftm_schema, source_entity_id, target_entity_id, confidence, status, dedupe_key)
        VALUES ('UnknownLink', %s, %s, 1.0, 'asserted', %s)
        """,
        (organo, expediente, "test:organo"),
    )
    store.conn.commit()

    d = _exportado(store, tmp_path, max_entidades=10, max_aristas=10)

    captions = {n["caption"] for n in d["nodes"]}
    assert "MINISTERIO" in captions, "el organismo se quedó fuera del mapa"
    assert "UnknownLink" in {e["schema"] for e in d["edges"]}

    # Y queda de verdad conectado, no suelto.
    enlaces = [e for e in d["edges"] if e["schema"] == "UnknownLink"]
    assert len(enlaces) == 1
    assert {enlaces[0]["source"], enlaces[0]["target"]} <= {n["id"] for n in d["nodes"]}


def test_el_dinero_no_agota_el_sitio_del_tejido_conectivo(store, tmp_path):
    """El fallo que dio tres instantáneas idénticas al byte.

    Si la primera pasada gasta todo el presupuesto de nodos con aristas caras,
    la segunda no puede traerse ningún nodo nuevo y los organismos —que sólo
    cuelgan por aristas sin importe— se quedan fuera para siempre. La señal
    era que el volcado traía exactamente el tope de nodos, clavado.
    """
    # Muchas parejas caras, suficientes para llenar el tope por sí solas.
    for i in range(30):
        a = _entidad(store, f"PAGADOR {i}", "PublicBody")
        b = _entidad(store, f"COBRADOR {i}")
        _arista(store, a, b, f"{9_000_000 - i}.00")

    # Y un organismo que sólo cuelga por una arista sin importe.
    organo = _entidad(store, "ORGANO TARDIO", "PublicBody")
    expediente = _entidad(store, "EXPEDIENTE TARDIO", "Contract")
    empresa = _entidad(store, "EMPRESA TARDIA")
    _arista(store, expediente, empresa, "100.00")
    store.conn.execute(
        """
        INSERT INTO relationships
            (ftm_schema, source_entity_id, target_entity_id, confidence, status, dedupe_key)
        VALUES ('UnknownLink', %s, %s, 1.0, 'asserted', %s)
        """,
        (organo, expediente, "test:organo-tardio"),
    )
    store.conn.commit()

    d = _exportado(store, tmp_path, max_entidades=20, max_aristas=40)

    # Con el tope clavado en la pasada 1 esto era imposible.
    assert len(d["nodes"]) <= 20
    publicados = {n["id"] for n in d["nodes"]}
    aristas = [e for e in d["edges"] if e["schema"] == "UnknownLink"]
    if aristas:
        for e in aristas:
            assert e["source"] in publicados and e["target"] in publicados

    # Lo que de verdad se comprueba: queda sitio libre tras la pasada del
    # dinero, que es la condición para que el tejido conectivo pueda entrar.
    assert len(d["nodes"]) < 20 or any(n["schema"] == "Contract" for n in d["nodes"])


def test_los_partidos_no_pierden_contra_un_contrato_grande(store, tmp_path):
    """Un mapa de financiación política sin partidos no sirve de nada.

    Se comprobó sobre datos reales: al coser bien el grafo entraron 456
    organismos y desaparecieron los 179 partidos. Una subvención electoral es
    calderilla al lado de un contrato de infraestructuras, así que compitiendo
    por importe un partido nunca gana.
    """
    for i in range(20):
        a = _entidad(store, f"MINISTERIO {i}", "PublicBody")
        b = _entidad(store, f"CONSTRUCTORA {i}")
        _arista(store, a, b, f"{50_000_000 - i}.00")

    fila = store.conn.execute(
        """
        INSERT INTO entities (ftm_schema, caption, dedupe_key, properties)
        VALUES ('Organization', 'PARTIDO DE PRUEBA', 'nif:G00000000',
                '{"partido_politico": true}'::jsonb)
        RETURNING id
        """
    ).fetchone()
    assert fila is not None
    partido = str(fila["id"])
    organo = _entidad(store, "MINISTERIO DEL INTERIOR", "PublicBody")
    _arista(store, organo, partido, "12000.00")  # subvención electoral, calderilla
    store.conn.commit()

    d = _exportado(store, tmp_path, max_entidades=12, max_aristas=12)

    captions = {n["caption"] for n in d["nodes"]}
    assert "PARTIDO DE PRUEBA" in captions, "el partido perdió contra los contratos"
    assert "MINISTERIO DEL INTERIOR" in captions, "el partido entró pero suelto"


def test_el_volcado_dice_que_fuente_no_aporto_nada(store, tmp_path):
    """Una fuente caída no puede pasar desapercibida.

    Las fuentes se dan de alta antes de ingerir, así que la tabla las lista
    aunque no hayan traído nada. El 18/9/2026 BDNS no respondió y la
    instantánea salió con toda la procedencia en PLACSP —sin subvenciones y
    sin partidos, la mitad del mapa— mientras el cartel seguía diciendo "datos
    reales de BDNS, PLACSP y Tribunal de Cuentas". Mentir por omisión.
    """
    store.upsert_source(Source(id="caida", name="Fuente Caída", url="https://ejemplo.test"))
    a = _entidad(store, "A")
    b = _entidad(store, "B")
    _arista(store, a, b, "100.00")
    store.conn.commit()

    d = _exportado(store, tmp_path)

    por_id = {f["id"]: f for f in d["fuentes"]}
    assert por_id["caida"]["entidades"] == 0, "la fuente sin aporte no se distingue"
    # Y la que sí aportó no puede salir a cero.
    assert "entidades" in por_id["test"]
