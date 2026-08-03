"""Tests del conector de BDNS.

Ojo con el alcance: la muestra de `golden/bdns_concesiones_sintetica.json` es
**sintética**. Verifica la lógica del parser, no el formato real de la API.
El golden test contra una respuesta auténtica está en `test_bdns_golden.py` y
se salta hasta que exista la captura. Ver `tests/golden/README.md`.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from sinapsis_ingest.connectors.base import RawDocument
from sinapsis_ingest.connectors.bdns import (
    EXTRACTOR_VERSION,
    BDNSConnector,
    normalizar_nif,
)

MUESTRA = Path(__file__).parent / "golden" / "bdns_concesiones_sintetica.json"


@pytest.fixture
def conector() -> BDNSConnector:
    # Sin espera entre peticiones: los tests no salen a la red.
    return BDNSConnector(peticiones_por_segundo=0)


@pytest.fixture
def crudo() -> RawDocument:
    return RawDocument(
        source_id="bdns",
        url="https://www.infosubvenciones.es/bdnstrans/api/concesiones/busqueda?page=0",
        content=MUESTRA.read_bytes(),
        media_type="application/json",
        retrieved_at=datetime(2026, 8, 3, tzinfo=UTC),
    )


# --- normalización de NIF -------------------------------------------------


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("B-12345678", "B12345678"),
        ("b12345678", "B12345678"),
        (" B 12345678 ", "B12345678"),
        ("12345678Z", "12345678Z"),
        ("", ""),
        (None, ""),
        # Longitud incorrecta: preferimos no afirmar nada.
        ("B123", ""),
        ("B123456789012", ""),
    ],
)
def test_normalizar_nif(entrada, esperado):
    assert normalizar_nif(entrada) == esperado


def test_nif_normalizado_converge(conector, crudo):
    # "B-12345678" y "b12345678" deben dar la misma clave: de esto depende
    # toda la resolución determinista.
    assert normalizar_nif("B-12345678") == normalizar_nif("b12345678")


# --- parse ----------------------------------------------------------------


def test_parse_extrae_las_concesiones_con_codigo(conector, crudo):
    registros = list(conector.parse(crudo))
    # La muestra trae 5 elementos; uno no tiene codConcesion y se descarta.
    assert len(registros) == 4


def test_parse_enlaza_con_el_crudo(conector, crudo):
    for r in conector.parse(crudo):
        assert r.raw_content_hash == crudo.content_hash
        assert r.extractor_version == EXTRACTOR_VERSION


def test_parse_es_puro(conector, crudo):
    # Dos pasadas sobre los mismos bytes dan lo mismo. Sin esto, los golden
    # tests no significarían nada.
    primera = [r.data for r in conector.parse(crudo)]
    segunda = [r.data for r in conector.parse(crudo)]
    assert primera == segunda


def test_parse_usa_el_nivel_mas_especifico_del_organo(conector, crudo):
    registros = {r.data["cod_concesion"]: r.data for r in conector.parse(crudo)}
    # 1001 tiene nivel3 relleno: gana el más específico.
    assert registros["1001"]["organo"] == "DIRECCIÓN GENERAL DE PRUEBAS"
    # 1002 tiene nivel3 vacío: cae a nivel2.
    assert registros["1002"]["organo"] == "MINISTERIO DE EJEMPLO"
    # 1003 no trae nivel3: cae a nivel2.
    assert registros["1003"]["organo"] == "CONSEJERÍA DE PRUEBAS"


def test_parse_acepta_las_dos_formas_de_fecha(conector, crudo):
    registros = {r.data["cod_concesion"]: r.data for r in conector.parse(crudo)}
    assert registros["1001"]["fecha_concesion"] == date(2025, 3, 14)  # ISO
    assert registros["1002"]["fecha_concesion"] == date(2025, 3, 14)  # dd/mm/aaaa


def test_parse_conserva_los_decimales_del_importe(conector, crudo):
    registros = {r.data["cod_concesion"]: r.data for r in conector.parse(crudo)}
    assert registros["1001"]["importe"] == Decimal("50000.5")
    # Un importe grande no debe perder precisión por pasar por float.
    assert registros["1002"]["importe"] == Decimal("1234567890123.45")


def test_parse_tolera_json_invalido(conector):
    roto = RawDocument(
        source_id="bdns",
        url="https://ejemplo.test",
        content=b"{esto no es json",
        media_type="application/json",
    )
    # No revienta: registra el hueco y no produce nada.
    assert list(conector.parse(roto)) == []


def test_parse_tolera_respuesta_sin_content(conector):
    raro = RawDocument(
        source_id="bdns",
        url="https://ejemplo.test",
        content=b'{"mensaje":"servicio no disponible"}',
        media_type="application/json",
    )
    assert list(conector.parse(raro)) == []


# --- normalize ------------------------------------------------------------


def _normalizados(conector, crudo) -> dict[str, dict]:
    salida = {}
    for r in conector.parse(crudo):
        n = conector.normalize(r)
        if n is not None:
            salida[r.data["cod_concesion"]] = n
    return salida


def test_normalize_produce_arista_payment(conector, crudo):
    n = _normalizados(conector, crudo)["1001"]
    assert n.entidades[0].ftm_schema == "PublicBody"
    assert n.aristas[0].ftm_schema == "Payment"
    assert n.entidades[1].ftm_schema == "Company"


def test_normalize_distingue_persona_fisica(conector, crudo):
    # NIF que empieza por dígito -> persona física -> Person, no Company.
    n = _normalizados(conector, crudo)["1002"]
    assert n.entidades[1].ftm_schema == "Person"
    assert n.entidades[1].nif == "12345678Z"


def test_normalize_sin_nif_usa_legal_entity_y_baja_la_confianza(conector, crudo):
    # Sin NIF no podemos afirmar de qué tipo de entidad se trata ni fusionarla
    # con seguridad: se refleja en el esquema y en la confianza.
    n = _normalizados(conector, crudo)["1003"]
    assert n.entidades[1].ftm_schema == "LegalEntity"
    assert n.entidades[1].nif == ""
    assert n.aristas[0].confidence == 0.7
    assert not n.entidades[1].dedupe_key.startswith("nif:")


def test_normalize_con_nif_da_confianza_maxima(conector, crudo):
    n = _normalizados(conector, crudo)["1001"]
    assert n.aristas[0].confidence == 1.0
    assert n.entidades[1].dedupe_key == "nif:B12345678"


def test_normalize_descarta_registro_sin_beneficiario(conector, crudo):
    # 1004 no tiene beneficiario: no se inventa uno, se descarta.
    assert "1004" not in _normalizados(conector, crudo)


def test_normalize_marca_status_asserted(conector, crudo):
    # Lo afirma la fuente; no lo inferimos nosotros.
    for n in _normalizados(conector, crudo).values():
        assert n.aristas[0].status == "asserted"


def test_normalize_dedupe_key_de_arista_es_la_concesion(conector, crudo):
    n = _normalizados(conector, crudo)["1001"]
    assert n.aristas[0].dedupe_key == "bdns:concesion:1001"


def test_normalize_importe_sin_moneda_no_ocurre(conector, crudo):
    # El esquema rechaza un importe sin moneda; el conector no debe producirlo.
    for n in _normalizados(conector, crudo).values():
        rel = n.aristas[0]
        if rel.amount is not None:
            assert rel.currency == "EUR"


def test_normalize_el_mismo_organo_da_la_misma_clave(conector, crudo):
    n = _normalizados(conector, crudo)
    # 1001 y 1002 son del mismo ministerio pero con nivel3 distinto, así que
    # sus claves de órgano deben diferir (son órganos distintos).
    assert n["1001"].entidades[0].dedupe_key != n["1002"].entidades[0].dedupe_key


# --- fetch (con transporte simulado) --------------------------------------


def test_fetch_pagina_hasta_agotar_total_pages():
    paginas_servidas = []

    def handler(request: httpx.Request) -> httpx.Response:
        pagina = int(request.url.params.get("page", 0))
        paginas_servidas.append(pagina)
        return httpx.Response(
            200,
            json={"content": [{"codConcesion": pagina}], "totalPages": 3, "number": pagina},
            headers={"content-type": "application/json"},
        )

    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    conector = BDNSConnector(cliente=cliente, peticiones_por_segundo=0)

    docs = list(conector.fetch(fecha_desde=date(2025, 1, 1), fecha_hasta=date(2025, 1, 31)))

    assert paginas_servidas == [0, 1, 2]
    assert len(docs) == 3
    assert all(d.source_id == "bdns" for d in docs)
    assert docs[0].metadata["pagina"] == 0


def test_fetch_respeta_max_paginas():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"content": [], "totalPages": 100, "number": 0})

    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    conector = BDNSConnector(cliente=cliente, peticiones_por_segundo=0)

    docs = list(
        conector.fetch(fecha_desde=date(2025, 1, 1), fecha_hasta=date(2025, 1, 31), max_paginas=2)
    )
    assert len(docs) == 2


def test_fetch_tolera_error_http_sin_inventar_datos():
    llamadas = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            return httpx.Response(200, json={"content": [{"codConcesion": 1}], "totalPages": 5})
        return httpx.Response(500, text="error del servidor")

    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    conector = BDNSConnector(cliente=cliente, peticiones_por_segundo=0)

    docs = list(conector.fetch(fecha_desde=date(2025, 1, 1), fecha_hasta=date(2025, 1, 31)))

    # La primera página se conserva; el fallo corta la ingesta sin fabricar
    # nada para las páginas que faltan.
    assert len(docs) == 1


def test_fetch_envia_las_fechas_en_formato_de_la_api():
    capturado = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado.update(dict(request.url.params))
        return httpx.Response(200, json={"content": [], "totalPages": 1})

    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    conector = BDNSConnector(cliente=cliente, peticiones_por_segundo=0)
    list(conector.fetch(fecha_desde=date(2025, 1, 1), fecha_hasta=date(2025, 12, 31)))

    assert capturado["fechaDesde"] == "01/01/2025"
    assert capturado["fechaHasta"] == "31/12/2025"


def test_el_crudo_guardado_son_los_bytes_literales():
    cuerpo = {"content": [{"codConcesion": 7}], "totalPages": 1}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=cuerpo)

    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    conector = BDNSConnector(cliente=cliente, peticiones_por_segundo=0)
    docs = list(conector.fetch(fecha_desde=date(2025, 1, 1), fecha_hasta=date(2025, 1, 2)))

    # El crudo es la prueba: debe poder reparsearse tal cual.
    assert json.loads(docs[0].content) == cuerpo
