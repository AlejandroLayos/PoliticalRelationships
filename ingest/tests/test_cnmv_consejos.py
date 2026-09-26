"""El conector de los consejos de la CNMV: la bajada, la caché y la forma.

Las reglas de lectura del cuadro C.1.2 se prueban en `test_cnmv.py` sobre las
tablas reales. Aquí, el recorrido del conector con la CNMV simulada, y lo que
normaliza a partir de esas mismas tablas.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from sinapsis_ingest.cnmv import nombre_de_persona
from sinapsis_ingest.connectors import cnmv_consejos
from sinapsis_ingest.connectors.base import RawDocument
from sinapsis_ingest.connectors.boe import clave
from sinapsis_ingest.connectors.cnmv_consejos import CNMVConsejosConnector

GOLDEN = Path(__file__).parent / "golden" / "cnmv"
TELEFONICA, PRISA = "A28015865", "A28297059"
PDF_FALSO = b"%PDF-1.4 informe de prueba"


class _Servidor:
    def __init__(self, cortes: int = 0) -> None:
        self.peticiones: list[str] = []
        self.cortes = cortes

    def __call__(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.peticiones.append(url)
        if "informaciongobcorp" in url and self.cortes:
            # La CNMV corta la conexión, como en la octava vuelta.
            self.cortes -= 1
            raise httpx.RemoteProtocolError("Server disconnected without sending a response.")
        if url.endswith("home.aspx"):
            return httpx.Response(200, text="<title>CNMV</title>")
        if f"ps_ac_ini.aspx?nif={TELEFONICA}" in url:
            return httpx.Response(
                200, text=(GOLDEN / "telefonica-participaciones.html").read_text(encoding="utf-8")
            )
        if f"informaciongobcorp.aspx?nif={TELEFONICA}" in url:
            return httpx.Response(
                200, text=(GOLDEN / "telefonica-gobcorp.html").read_text(encoding="utf-8")
            )
        if "verdocumento" in url:
            return httpx.Response(200, content=PDF_FALSO)
        return httpx.Response(404)


def _conector(servidor: _Servidor, cache: Path | None = None) -> CNMVConsejosConnector:
    return CNMVConsejosConnector(
        cliente=httpx.Client(transport=httpx.MockTransport(servidor)),
        semillas=[TELEFONICA],
        cache=cache,
        pausa=0,
        esperas=(0, 0),
    )


def test_baja_el_ultimo_iagc_y_lo_guarda_en_la_cache(tmp_path):
    servidor = _Servidor()
    [doc] = list(_conector(servidor, tmp_path).fetch())
    assert doc.content == PDF_FALSO and doc.media_type == "application/pdf"
    assert doc.metadata["emisor"] == "TELEFONICA, S.A."
    assert (doc.metadata["ejercicio"], doc.metadata["registro"]) == (2025, "2026028797")
    assert doc.metadata["url_publica"].endswith(f"informaciongobcorp.aspx?nif={TELEFONICA}")
    assert (tmp_path / "iagc-2026028797.pdf").read_bytes() == PDF_FALSO
    # La segunda noche, el PDF sale de la caché: no se vuelve a pedir.
    otro = _Servidor()
    [de_nuevo] = list(_conector(otro, tmp_path).fetch())
    assert de_nuevo.content == PDF_FALSO
    assert not any("verdocumento" in u for u in otro.peticiones)


def test_si_la_cnmv_corta_la_conexion_se_reintenta():
    servidor = _Servidor(cortes=2)
    assert len(list(_conector(servidor).fetch())) == 1
    assert sum("informaciongobcorp" in u for u in servidor.peticiones) == 3


def test_si_corta_siempre_no_hay_informe_y_no_se_rompe():
    servidor = _Servidor(cortes=99)
    assert list(_conector(servidor).fetch()) == []


def _tablas(empresa: str) -> list:
    datos = json.loads((GOLDEN / f"{empresa}-consejo-tablas.json").read_text(encoding="utf-8"))
    return [t["filas"] for t in datos["tablas"]], "Número de consejeros fijado por la junta 14"


@pytest.fixture
def consejo_de_prisa(monkeypatch):
    """El conector leyendo las tablas reales de Prisa, sin el PDF."""
    monkeypatch.setattr(cnmv_consejos, "tablas_del_cuadro", lambda _pdf: _tablas("prisa"))
    conector = CNMVConsejosConnector()
    raw = RawDocument(
        source_id="cnmv",
        url="https://www.cnmv.es/webservices/verdocumento/ver?e=x",
        content=PDF_FALSO,
        media_type="application/pdf",
        metadata={
            "nif": PRISA,
            "emisor": "PROMOTORA DE INFORMACIONES, S.A.",
            "ejercicio": 2025,
            "registro": "2026042679",
            "url_publica": f"https://www.cnmv.es/x/informaciongobcorp.aspx?nif={PRISA}",
        },
    )
    return [conector.normalize(r) for r in conector.parse(raw)]


def test_cada_consejero_unido_a_su_cotizada_sin_fechas(consejo_de_prisa):
    assert len(consejo_de_prisa) == 13
    aristas = [a for n in consejo_de_prisa for a in n.aristas]
    assert {a.ftm_schema for a in aristas} == {"Directorship"}
    assert {a.target_key for a in aristas} == {f"nif:{PRISA}"}
    presidente = next(a for a in aristas if a.properties["cargo"] == "Presidente")
    assert presidente.properties == {
        "cargo": "Presidente",
        "categoria": "Dominical",
        "ejercicio": 2025,
        "url": f"https://www.cnmv.es/x/informaciongobcorp.aspx?nif={PRISA}",
        "relacion": "consejo",
    }
    # Ninguna fecha: ni en las propiedades de la arista ni en sus fechas.
    assert all(a.start_date is None and a.end_date is None for a in aristas)


def test_el_consejero_que_es_accionista_es_el_mismo_nodo(consejo_de_prisa):
    """Oughourlian, presidente de Prisa y accionista significativo suyo."""
    personas = {
        e.caption: e for n in consejo_de_prisa for e in n.entidades if e.ftm_schema == "Person"
    }
    oughourlian = personas["JOSEPH OUGHOURLIAN"]
    # La clave del conector de participaciones para «OUGHOURLIAN , JOSEPH».
    assert (
        oughourlian.dedupe_key == f"cnmv:persona:{clave(nombre_de_persona('OUGHOURLIAN , JOSEPH'))}"
    )
    assert oughourlian.properties["consejero_cnmv"] is True
    assert all(p.dedupe_key.startswith("cnmv:persona:") for p in personas.values())


def test_un_pdf_real_sin_el_cuadro_no_da_tablas():
    """Las dos librerías sobre un PDF de verdad (uno del Tribunal de Cuentas)."""
    pdf = (Path(__file__).parent / "golden" / "tcu_sancionadores_2019.pdf").read_bytes()
    assert cnmv_consejos.tablas_del_cuadro(pdf) == ([], "")


class _ServidorConGuion(_Servidor):
    """Sin guion, «sin datos»; con guion, la página de verdad (o la de todos)."""

    def __init__(self, con_guion: str) -> None:
        super().__init__()
        self.con_guion = con_guion

    def __call__(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if f"informaciongobcorp.aspx?nif={TELEFONICA}" in url:
            self.peticiones.append(url)
            return httpx.Response(200, text="<p>No se han encontrado datos disponibles</p>")
        if f"informaciongobcorp.aspx?nif={TELEFONICA[0]}-{TELEFONICA[1:]}" in url:
            self.peticiones.append(url)
            return httpx.Response(200, text=(GOLDEN / self.con_guion).read_text(encoding="utf-8"))
        return super().__call__(request)


def test_sin_datos_por_nif_se_pide_con_guion():
    servidor = _ServidorConGuion("telefonica-gobcorp.html")
    [doc] = list(_conector(servidor).fetch())
    assert doc.metadata["registro"] == "2026028797"
    assert doc.metadata["url_publica"].endswith("nif=A-28015865")


def test_la_lista_de_todos_los_emisores_no_da_informe():
    # Con guion llega la lista de todos (empieza por Abanca): no es la suya.
    servidor = _ServidorConGuion("iberdrola-gobcorp-qs.html")
    assert list(_conector(servidor).fetch()) == []
    assert not any("verdocumento" in u for u in servidor.peticiones)
