"""Diputados del Congreso, contra los ficheros reales que guardó el reconocimiento."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import httpx

from sinapsis_ingest.connectors.base import ParsedRecord, RawDocument
from sinapsis_ingest.connectors.congreso import (
    CongresoConnector,
    cargos_en_biografia,
    nombre_de_fila,
    romano,
)

GOLDEN = Path(__file__).parent / "golden" / "congreso"
XII = GOLDEN / "odsDiputados12__20260925050024.json"
XIV = GOLDEN / "odsDiputados14__20260925050256.json"
DECLARACIONES = GOLDEN / "docacteco__20260925050250.json"


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


# --- declaraciones de actividades --------------------------------------------


def test_de_las_declaraciones_solo_se_leen_las_actividades():
    registros = _registros(DECLARACIONES)
    # 1.224 filas de ACTIVIDAD; siete sin empleador ni descripción.
    assert len(registros) == 1217
    assert {r.data["tipo"] for r in registros} == {"actividad"}
    # Ni donaciones, ni fundaciones, ni observaciones: ninguna clave suya.
    for r in registros:
        assert not {"destinatario", "benefactor", "observaciones"} & {k.lower() for k in r.data}


def test_una_actividad_declarada_real():
    [r] = [x for x in _registros(DECLARACIONES) if x.data["empleador"] == "EFRIASA SA"]
    d = r.data
    # La coma sin espacio del fichero, con espacio: la misma ficha que su mandato.
    assert d["nombre"] == "Gallardo Barrena, Pedro Ignacio"
    assert d["periodo"] == "2018-2023"
    assert d["descripcion"] == "CONSEJERO"
    assert d["sector"] == "PRIVADO AGRICOLA"


def test_normaliza_la_actividad_como_arista_afirmada_por_el_diputado():
    [r] = [x for x in _registros(DECLARACIONES) if x.data["empleador"] == "UNIPREX S.A.U."]
    n = CongresoConnector().normalize(r)
    assert n is not None
    n.validar()
    persona = next(e for e in n.entidades if e.ftm_schema == "Person")
    assert persona.dedupe_key == "congreso:persona:" + persona.dedupe_key.split(":", 2)[2]
    assert persona.caption == "Cobo Vega, Manuel"
    assert persona.properties["cargo_publico"] is True
    destino = next(e for e in n.entidades if e.ftm_schema == "Organization")
    assert destino.dedupe_key.startswith("congreso:empleador:")
    [arista] = n.aristas
    assert arista.ftm_schema == "UnknownLink"
    assert arista.properties["relacion"] == "actividad_declarada"
    assert arista.properties["empleador"] == "UNIPREX S.A.U."
    assert arista.properties["fechaRegistro"] == "2023-08-16"
    assert arista.confidence == 1.0


def test_la_misma_persona_en_el_mandato_y_en_la_declaracion():
    mandato = CongresoConnector().normalize(
        next(x for x in _registros(XIV) if x.data["nombre"] == "Ábalos Meco, José Luis")
    )
    declarada = CongresoConnector().normalize(
        next(x for x in _registros(DECLARACIONES) if x.data["nombre"] == "Ábalos Meco, José Luis")
    )
    assert mandato is not None and declarada is not None
    clave = lambda n: next(e.dedupe_key for e in n.entidades if e.ftm_schema == "Person")  # noqa: E731
    assert clave(mandato) == clave(declarada)


def test_una_modificacion_que_repite_la_actividad_es_la_misma_arista():
    base = {
        "tipo": "actividad",
        "nombre": "Pérez Gil, Ana",
        "empleador": "ACME, S.L.",
        "sector": "Privado",
        "periodo": "2019-2023",
        "descripcion": "Gerente",
        "url": "https://www.congreso.es/x.json",
    }
    a = CongresoConnector().normalize(
        ParsedRecord("x", "t", {**base, "fecha_registro": "01/08/2023"})
    )
    b = CongresoConnector().normalize(
        ParsedRecord("y", "t", {**base, "fecha_registro": "19/09/2023"})
    )
    assert a is not None and b is not None
    assert a.aristas[0].dedupe_key == b.aristas[0].dedupe_key


def test_nombre_de_fila():
    assert nombre_de_fila("Abades Martínez,Cristina") == "Abades Martínez, Cristina"
    assert nombre_de_fila("  Abades  Martínez ,  Cristina ") == "Abades Martínez, Cristina"


def test_fetch_pide_tambien_las_declaraciones():
    pagina = (
        '<a href="/webpublica/opendata/diputados/odsDiputados14__1.json">JSON</a>'
        '<a href="/webpublica/opendata/diputados/docacteco__1.json">JSON</a>'
    )

    def servidor(peticion: httpx.Request) -> httpx.Response:
        if peticion.url.path.endswith("/diputados"):
            return httpx.Response(200, text=pagina)
        if "docacteco" in peticion.url.path:
            return httpx.Response(200, content=DECLARACIONES.read_bytes())
        return httpx.Response(200, content=XIV.read_bytes())

    cliente = httpx.Client(transport=httpx.MockTransport(servidor))
    docs = list(CongresoConnector(cliente=cliente, desde_legislatura=14).fetch())
    [declaraciones] = [d for d in docs if d.metadata.get("tipo") == "declaraciones"]
    assert declaraciones.metadata["legislatura"] == 15
