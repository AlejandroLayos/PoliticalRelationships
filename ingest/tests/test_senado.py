"""Los partidos del Senado, contra el fichero real que guardó el reconocimiento."""

from __future__ import annotations

from pathlib import Path

import httpx

from sinapsis_ingest.connectors.base import RawDocument
from sinapsis_ingest.connectors.senado import SenadoConnector

GOLDEN = Path(__file__).parent / "golden" / "senado"
XV = GOLDEN / "grupos-y-partidos-xv.xml"


def _registros() -> list:
    raw = RawDocument(
        source_id="senado",
        url="https://www.senado.es/web/ficopendataservlet?tipoFich=4&legis=15",
        content=XV.read_bytes(),
        media_type="application/xml",
        metadata={"legislatura": 15},
    )
    return list(SenadoConnector().parse(raw))


def test_se_leen_todos_los_partidos_de_la_legislatura():
    registros = _registros()
    # 21 partidos en siete grupos; alguno repetido en dos grupos.
    assert len(registros) == 21
    assert {r.data["legislatura"] for r in registros} == {15}


def test_las_siglas_y_el_nombre_oficial():
    pares = {(r.data["siglas"], r.data["nombre"]) for r in _registros()}
    assert ("PP", "PARTIDO POPULAR") in pares
    assert ("PSOE", "PARTIDO SOCIALISTA OBRERO ESPAÑOL") in pares
    assert ("EH Bildu", "EUSKAL HERRIA BILDU") in pares


def test_normaliza_una_entidad_por_pareja_de_siglas_y_nombre():
    [r] = [x for x in _registros() if x.data["siglas"] == "PP"]
    n = SenadoConnector().normalize(r)
    assert n is not None
    n.validar()
    partido = next(e for e in n.entidades if e.dedupe_key.startswith("senado:partido:"))
    assert partido.dedupe_key.startswith("senado:partido:")
    assert partido.properties["siglasSenado"] == "PP"
    assert partido.properties["nombreSenado"] == "PARTIDO POPULAR"
    # No es la ficha del partido en el mapa: no lleva la marca que la haría pasar por él.
    assert "partido_politico" not in partido.properties
    # El hecho de la fuente: en la XV, el PP forma parte de su grupo.
    [arista] = n.aristas
    assert arista.properties["relacion"] == "partido_en_grupo"
    assert arista.target_key == "senado:grupo:15:801"


def test_un_fichero_que_no_es_xml_no_rompe():
    raw = RawDocument(source_id="senado", url="x", content=b"<html>error", media_type="text/html")
    assert list(SenadoConnector().parse(raw)) == []


def test_fetch_pide_cada_legislatura():
    pedidas: list[str] = []

    def servidor(peticion: httpx.Request) -> httpx.Response:
        pedidas.append(str(peticion.url))
        return httpx.Response(200, content=XV.read_bytes())

    cliente = httpx.Client(transport=httpx.MockTransport(servidor))
    docs = list(SenadoConnector(cliente=cliente, desde=14, hasta=15).fetch())
    assert [d.metadata["legislatura"] for d in docs] == [14, 15]
    assert all("tipoFich=4" in u for u in pedidas)
