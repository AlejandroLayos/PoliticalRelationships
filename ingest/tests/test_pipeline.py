"""Tests del pipeline completo contra un Postgres real.

Se saltan si no hay SINAPSIS_TEST_POSTGRES_DSN. Verifican el criterio de
aceptación de la fase 2: ejecutar el conector puebla entidades y aristas, cada
arista enlaza a su raw_document, y la reejecución es idempotente.
"""

from __future__ import annotations

import json
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from sinapsis_ingest import pipeline
from sinapsis_ingest.connectors.bdns import BDNSConnector
from sinapsis_ingest.store import Source, Store

MUESTRA = Path(__file__).parent / "golden" / "bdns_concesiones_sintetica.json"

DSN = os.environ.get("SINAPSIS_TEST_POSTGRES_DSN", "")

pytestmark = pytest.mark.skipif(
    not DSN, reason="SINAPSIS_TEST_POSTGRES_DSN sin definir; se salta la integración"
)


def _migraciones() -> list[Path]:
    d = Path(__file__).resolve().parents[2] / "backend" / "migrations"
    return sorted(d.glob("*.up.sql"))


@pytest.fixture
def store():
    with Store(DSN) as st:
        # Esquema al día.
        existe = st.conn.execute(
            """SELECT EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='entities' AND column_name='dedupe_key')"""
        ).fetchone()
        if not existe or not existe["exists"]:
            for f in _migraciones():
                st.conn.execute(f.read_text(encoding="utf-8"))
        st.conn.commit()

        st.conn.execute(
            """TRUNCATE provenance, entity_resolution_decisions, review_queue,
                        relationships, entities, raw_documents, sources CASCADE"""
        )
        st.upsert_source(Source(id="bdns", name="BDNS", url="https://ejemplo.test"))
        st.conn.commit()
        yield st


@pytest.fixture
def conector():
    """Conector que sirve la muestra sintética en lugar de salir a la red."""
    cuerpo = json.loads(MUESTRA.read_bytes())

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=cuerpo, headers={"content-type": "application/json"})

    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    return BDNSConnector(cliente=cliente, peticiones_por_segundo=0)


def _contar(store: Store, tabla: str) -> int:
    fila = store.conn.execute(f"SELECT count(*) AS n FROM {tabla}").fetchone()
    assert fila is not None
    return int(fila["n"])


def test_ingesta_puebla_entidades_y_aristas(store, conector):
    resultado = pipeline.ejecutar(
        store, conector, fecha_desde=date(2025, 1, 1), fecha_hasta=date(2025, 1, 31)
    )
    store.conn.commit()

    assert resultado.documentos_nuevos == 1
    assert resultado.aristas == 3  # 4 con código, uno sin beneficiario se descarta
    assert resultado.registros_descartados == 1
    assert not resultado.errores

    assert _contar(store, "raw_documents") == 1
    assert _contar(store, "relationships") == 3
    assert _contar(store, "entities") > 0


def test_cada_arista_enlaza_a_su_documento_crudo(store, conector):
    pipeline.ejecutar(store, conector, fecha_desde=date(2025, 1, 1), fecha_hasta=date(2025, 1, 31))
    store.conn.commit()

    huerfanas = store.conn.execute(
        """
        SELECT count(*) AS n FROM relationships r
        WHERE NOT EXISTS (SELECT 1 FROM provenance p WHERE p.relationship_id = r.id)
        """
    ).fetchone()
    assert huerfanas is not None
    assert huerfanas["n"] == 0, "hay aristas sin procedencia: viola el invariante 1"


def test_se_puede_volver_de_la_arista_al_documento_original(store, conector):
    pipeline.ejecutar(store, conector, fecha_desde=date(2025, 1, 1), fecha_hasta=date(2025, 1, 31))
    store.conn.commit()

    fila = store.conn.execute(
        """
        SELECT rel.amount, rel.currency, rd.url, rd.content_hash, p.extractor_version
        FROM relationships rel
        JOIN provenance p ON p.relationship_id = rel.id
        JOIN raw_documents rd ON rd.id = p.raw_document_id
        WHERE rel.dedupe_key = 'bdns:concesion:1001'
        """
    ).fetchone()

    assert fila is not None, "no encuentro la concesión 1001"
    assert fila["amount"] == Decimal("50000.50")
    assert fila["currency"] == "EUR"
    assert fila["extractor_version"] == "bdns/1"
    assert len(fila["content_hash"]) == 64


def test_reejecucion_es_idempotente(store, conector):
    params = {"fecha_desde": date(2025, 1, 1), "fecha_hasta": date(2025, 1, 31)}

    primera = pipeline.ejecutar(store, conector, **params)
    store.conn.commit()
    conteos = {
        t: _contar(store, t) for t in ("raw_documents", "entities", "relationships", "provenance")
    }

    segunda = pipeline.ejecutar(store, conector, **params)
    store.conn.commit()

    assert primera.documentos_nuevos == 1
    assert segunda.documentos_nuevos == 0
    assert segunda.documentos_repetidos == 1

    for tabla, esperado in conteos.items():
        assert _contar(store, tabla) == esperado, f"{tabla} creció en la reejecución"


def test_el_importe_grande_no_pierde_precision(store, conector):
    pipeline.ejecutar(store, conector, fecha_desde=date(2025, 1, 1), fecha_hasta=date(2025, 1, 31))
    store.conn.commit()

    fila = store.conn.execute(
        "SELECT amount FROM relationships WHERE dedupe_key = 'bdns:concesion:1002'"
    ).fetchone()
    assert fila is not None
    assert fila["amount"] == Decimal("1234567890123.45")


def test_persona_fisica_se_guarda_como_person(store, conector):
    pipeline.ejecutar(store, conector, fecha_desde=date(2025, 1, 1), fecha_hasta=date(2025, 1, 31))
    store.conn.commit()

    fila = store.conn.execute("SELECT ftm_schema FROM entities WHERE nif = '12345678Z'").fetchone()
    assert fila is not None
    assert fila["ftm_schema"] == "Person"


def test_beneficiario_sin_nif_baja_la_confianza(store, conector):
    pipeline.ejecutar(store, conector, fecha_desde=date(2025, 1, 1), fecha_hasta=date(2025, 1, 31))
    store.conn.commit()

    fila = store.conn.execute(
        "SELECT confidence, status FROM relationships WHERE dedupe_key = 'bdns:concesion:1003'"
    ).fetchone()
    assert fila is not None
    assert float(fila["confidence"]) == 0.7
    assert fila["status"] == "asserted"
