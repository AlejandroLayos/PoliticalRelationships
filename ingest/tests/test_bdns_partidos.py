"""Tests del conector de subvenciones a partidos políticos.

Comparte casi todo con el de concesiones generales; lo que se prueba aquí es
justamente lo que cambia, y sobre todo que **no duplica dinero** cuando la
misma concesión aparece en los dos conjuntos.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from sinapsis_ingest import conectores, pipeline, registry
from sinapsis_ingest.connectors.base import RawDocument
from sinapsis_ingest.connectors.bdns import (
    ENDPOINT_PARTIDOS,
    BDNSConnector,
    BDNSPartidosConnector,
)
from sinapsis_ingest.store import Source, Store

MUESTRA = Path(__file__).parent / "golden" / "bdns_concesiones_sintetica.json"
DSN = os.environ.get("SINAPSIS_TEST_POSTGRES_DSN", "")


@pytest.fixture
def crudo() -> RawDocument:
    return RawDocument(
        source_id="bdns",
        url=ENDPOINT_PARTIDOS,
        content=MUESTRA.read_bytes(),
        media_type="application/json",
        retrieved_at=datetime(2026, 8, 3, tzinfo=UTC),
    )


# --- registro -------------------------------------------------------------


def test_ambos_conectores_estan_registrados():
    registry._reset_for_tests()
    conectores.registrar_todos()
    disponibles = registry.available()
    assert "bdns" in disponibles
    assert "bdns-partidos" in disponibles
    registry._reset_for_tests()


def test_registrar_todos_es_idempotente():
    registry._reset_for_tests()
    conectores.registrar_todos()
    tras_una = registry.available()
    conectores.registrar_todos()  # no debe reventar ni añadir duplicados
    assert registry.available() == tras_una
    registry._reset_for_tests()


def test_los_dos_conectores_comparten_source_id():
    # Son dos vistas del mismo organismo emisor de datos.
    assert BDNSPartidosConnector().source_id == BDNSConnector().source_id == "bdns"


def test_hay_ficha_para_la_fuente():
    assert conectores.ficha("bdns").url.startswith("https://")
    with pytest.raises(KeyError):
        conectores.ficha("inexistente")


# --- comportamiento propio ------------------------------------------------


def test_usa_el_endpoint_de_partidos():
    assert BDNSPartidosConnector().endpoint == ENDPOINT_PARTIDOS
    assert BDNSPartidosConnector().endpoint != BDNSConnector().endpoint


def test_el_beneficiario_es_organization(crudo):
    conector = BDNSPartidosConnector(peticiones_por_segundo=0)
    vistos = 0
    for registro in conector.parse(crudo):
        n = conector.normalize(registro)
        if n is None:
            continue
        # Los beneficiarios anonimizados por minimización (spec §12) no pasan
        # por clasificar_beneficiario: son un agregado, no un partido.
        if n.aristas[0].properties.get("beneficiario_anonimizado"):
            continue
        # El conjunto de datos ya afirma que es un partido: nada de deducir
        # Company/Person por el NIF.
        assert n.entidades[1].ftm_schema == "Organization"
        assert n.entidades[1].properties["partido_politico"] is True
        vistos += 1
    assert vistos > 0, "ningún registro llegó a clasificarse como partido"


def test_la_clave_de_arista_es_la_misma_que_en_concesiones(crudo):
    """Duplicar una concesión inflaría el dinero contabilizado."""
    general = BDNSConnector(peticiones_por_segundo=0)
    partidos = BDNSPartidosConnector(peticiones_por_segundo=0)

    claves_g = {
        n.aristas[0].dedupe_key
        for r in general.parse(crudo)
        if (n := general.normalize(r)) is not None
    }
    claves_p = {
        n.aristas[0].dedupe_key
        for r in partidos.parse(crudo)
        if (n := partidos.normalize(r)) is not None
    }
    assert claves_g == claves_p


def test_la_clave_de_entidad_por_nif_tambien_converge(crudo):
    general = BDNSConnector(peticiones_por_segundo=0)
    partidos = BDNSPartidosConnector(peticiones_por_segundo=0)

    def claves(c):
        return {
            n.entidades[1].dedupe_key for r in c.parse(crudo) if (n := c.normalize(r)) is not None
        }

    assert claves(general) == claves(partidos)


# --- integración: la doble ingesta no duplica dinero ----------------------


@pytest.mark.skipif(not DSN, reason="SINAPSIS_TEST_POSTGRES_DSN sin definir")
def test_ingerir_los_dos_conjuntos_no_duplica_aristas():
    cuerpo = json.loads(MUESTRA.read_bytes())

    # El endpoint de partidos devuelve un subconjunto del universo de
    # concesiones, no una copia: dos respuestas byte-idénticas de la misma
    # fuente colapsarían en un solo raw_document por el UNIQUE
    # (source_id, content_hash), y no es eso lo que queremos probar aquí.
    subconjunto = {
        **cuerpo,
        "content": [c for c in cuerpo["content"] if c.get("codConcesion") == 1001],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        es_partidos = "partidospoliticos" in str(request.url)
        return httpx.Response(
            200,
            json=subconjunto if es_partidos else cuerpo,
            headers={"content-type": "application/json"},
        )

    with Store(DSN) as store:
        for f in sorted(
            (Path(__file__).resolve().parents[2] / "backend" / "migrations").glob("*.up.sql")
        ):
            try:
                store.conn.execute(f.read_text(encoding="utf-8"))
            except Exception:  # el esquema ya estaba
                store.conn.rollback()
        store.conn.commit()

        store.conn.execute(
            """TRUNCATE provenance, entity_resolution_decisions, review_queue,
                        relationships, entities, raw_documents, sources CASCADE"""
        )
        store.upsert_source(Source(id="bdns", name="BDNS", url="https://ejemplo.test"))
        store.conn.commit()

        params = {"fecha_desde": date(2025, 1, 1), "fecha_hasta": date(2025, 1, 31)}

        general = BDNSConnector(
            cliente=httpx.Client(transport=httpx.MockTransport(handler)),
            peticiones_por_segundo=0,
        )
        pipeline.ejecutar(store, general, **params)
        store.conn.commit()

        fila = store.conn.execute(
            "SELECT count(*) AS n, coalesce(sum(amount),0) AS total FROM relationships"
        ).fetchone()
        assert fila is not None
        aristas_tras_general = fila["n"]
        dinero_tras_general = fila["total"]

        partidos = BDNSPartidosConnector(
            cliente=httpx.Client(transport=httpx.MockTransport(handler)),
            peticiones_por_segundo=0,
        )
        pipeline.ejecutar(store, partidos, **params)
        store.conn.commit()

        fila = store.conn.execute(
            "SELECT count(*) AS n, coalesce(sum(amount),0) AS total FROM relationships"
        ).fetchone()
        assert fila is not None

        assert fila["n"] == aristas_tras_general, "la segunda ingesta duplicó aristas"
        assert fila["total"] == dinero_tras_general, "la segunda ingesta infló el dinero"
        assert Decimal(fila["total"]) > 0

        # Los dos endpoints son URLs distintas, así que cada uno conserva su
        # propio documento crudo y su procedencia.
        docs = store.conn.execute("SELECT count(*) AS n FROM raw_documents").fetchone()
        assert docs is not None
        assert docs["n"] == 2

        # Y la marca de partido sobrevive aunque el conector general escribiera
        # la entidad primero.
        marcados = store.conn.execute(
            "SELECT count(*) AS n FROM entities WHERE properties ? 'partido_politico'"
        ).fetchone()
        assert marcados is not None
        assert marcados["n"] > 0
