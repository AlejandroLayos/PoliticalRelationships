"""Diputados del Congreso, contra los ficheros reales que guardó el reconocimiento."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import httpx

from sinapsis_ingest.connectors.base import RawDocument
from sinapsis_ingest.connectors.congreso import CongresoConnector, cargos_en_biografia, romano

GOLDEN = Path(__file__).parent / "golden" / "congreso"
XII = GOLDEN / "odsDiputados12__20260925050024.json"
XIV = GOLDEN / "odsDiputados14__20260925050256.json"


def _raw(ruta: Path) -> RawDocument:
    return RawDocument(
        source_id="congreso",
        url=f"https://www.congreso.es/webpublica/opendata/diputados/{ruta.name}",
        content=ruta.read_bytes(),
        media_type="application/json",
    )


def _registros(ruta: Path) -> list:
    return list(CongresoConnector().parse(_raw(ruta)))


def test_cada_legislatura_se_lee_entera():
    assert len(_registros(XII)) == 393
    assert len(_registros(XIV)) == 413
    assert {r.data["legislatura"] for r in _registros(XIV)} == {14}


def test_un_diputado_real():
    [r] = [x for x in _registros(XIV) if x.data["nombre"] == "Ábalos Meco, José Luis"]
    d = r.data
    assert d["formacion"] == "PSOE"
    assert d["alta"] == "27/11/2019" and d["baja"] == "17/08/2023"
    assert "Ministro de Fomento desde el 7 de junio de 2018" in d["cargos_en_biografia"]


def test_la_biografia_no_se_guarda_solo_los_cargos_que_menciona():
    for r in _registros(XII):
        assert "biografia" not in {k.lower() for k in r.data}
        for mencion in r.data["cargos_en_biografia"]:
            assert (
                mencion.split()[0]
                .lower()
                .startswith(
                    (
                        "presidente",
                        "presidenta",
                        "vicepresident",
                        "ministr",
                        "secretari",
                        "subsecretari",
                        "director",
                        "delegad",
                    )
                )
            )


def test_cargos_en_biografia():
    assert cargos_en_biografia(
        "Ministra de Hacienda del Gobierno de España (2018-2019). Diputada."
    ) == ["Ministra de Hacienda del Gobierno de España"]
    assert cargos_en_biografia("Licenciada en Derecho por la Universidad de Santiago") == []


def test_normaliza_mandato_con_su_formacion():
    [r] = [x for x in _registros(XII) if x.data["nombre"] == "Báñez García, María Fátima"]
    n = CongresoConnector().normalize(r)
    assert n is not None
    n.validar()
    persona = next(e for e in n.entidades if e.ftm_schema == "Person")
    assert persona.properties["nombreParaCruzar"] == "maria fatima banez garcia"
    assert persona.properties["cargosEnBiografia"] == ["Ministra de Empleo y Seguridad Social"]
    assert "BIOGRAFIA" not in str(persona.properties)
    [mandato] = n.aristas
    assert mandato.start_date == date(2016, 7, 15) and mandato.end_date == date(2019, 5, 21)
    assert mandato.properties["formacion"] == "PP"
    assert mandato.properties["legislatura"] == "XII"
    assert mandato.properties["acto"] == "mandato"


def test_romanos():
    assert [romano(n) for n in (9, 10, 11, 12, 13, 14, 15)] == [
        "IX",
        "X",
        "XI",
        "XII",
        "XIII",
        "XIV",
        "XV",
    ]


def test_fetch_lee_los_enlaces_de_la_pagina_y_deduce_la_legislatura_en_curso():
    pagina = (
        '<a href="/webpublica/opendata/diputados/odsDiputados12__1.json">JSON</a>'
        '<a href="/webpublica/opendata/diputados/odsDiputados14__1.json">JSON</a>'
        '<a href="/webpublica/opendata/diputados/odsDiputados08__1.json">JSON</a>'
        '<a href="/webpublica/opendata/diputados/DiputadosActivos__1.json">JSON</a>'
    )
    pedidas: list[str] = []

    def servidor(peticion: httpx.Request) -> httpx.Response:
        pedidas.append(str(peticion.url))
        if peticion.url.path.endswith("/diputados"):
            return httpx.Response(200, text=pagina)
        return httpx.Response(200, content=XIV.read_bytes())

    cliente = httpx.Client(transport=httpx.MockTransport(servidor))
    docs = list(CongresoConnector(cliente=cliente).fetch())
    # La VIII queda fuera (antes de la IX); la en curso es la XV.
    assert [d.metadata["legislatura"] for d in docs] == [12, 14, 15]
