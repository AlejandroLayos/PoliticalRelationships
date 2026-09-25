"""Autorizaciones de actividad privada tras el cese, contra páginas reales.

Golden tests (CLAUDE.md): `tests/golden/oci/*.html` son páginas del Portal de
Transparencia tal cual las sirvió, guardadas por el reconocimiento.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

from sinapsis_ingest.connectors.base import RawDocument
from sinapsis_ingest.connectors.oci import (
    OCIConnector,
    en_minusculas,
    leer_tablas,
    nombre_para_cruzar,
)

GOLDEN = Path(__file__).parent / "golden" / "oci"
PAGINA_2020 = GOLDEN / (
    "publicidad-activa-por-materias-altos-cargos-actividad-privada-cese-seguimiento20200121.html"
)


def _filas(ruta: Path) -> list[dict]:
    return leer_tablas(ruta.read_text(encoding="utf-8"))


def test_la_tabla_real_se_lee_entera():
    filas = _filas(PAGINA_2020)
    assert len(filas) == 15
    primera = filas[0]
    assert primera["nombre"] == "VELA OLMO, CARMEN"
    assert primera["cargo"] == "SECRETARIA DE ESTADO DE INVESTIGACION, DESARROLLO E INNOVACION"
    assert primera["fecha_cese"] == "2018/06/18"
    assert primera["actividad"] == "PATRONATO DE LA FUNDACION ASTRAZENECA"
    assert primera["fecha_autorizacion"] == "2020/01/16"
    assert primera["curriculum"].startswith("/servicios-buscador/contenido/curriculums?id=")


def test_una_persona_con_dos_autorizaciones_son_dos_filas():
    banez = [f for f in _filas(PAGINA_2020) if f["nombre"] == "BAÑEZ GARCIA, FATIMA"]
    assert [f["actividad"] for f in banez] == [
        "MIEMBRO DEL CONSEJO DE ADMINISTRACION DE LABORATORIOS FARMACEUTICOS ROVI, S.A.",
        "AUTONOMO CONSULTORIA Y ASESORIA EMPRESAS",
    ]


def test_todas_las_paginas_de_seguimiento_tienen_tabla():
    for ruta in sorted(GOLDEN.glob("*seguimiento*.html")):
        assert _filas(ruta), ruta.name


def test_la_portada_no_trae_la_tabla():
    """Lo que vio el reconocimiento: la lista de ahora no está en el HTML de
    la portada, sino en el buscador del portal. Si un día la trae, este test
    lo dice."""
    assert (
        _filas(GOLDEN / "publicidad-activa-por-materias-altos-cargos-actividad-privada-cese.html")
        == []
    )


def test_el_buscador_del_portal_se_lee_sin_repetir():
    """El buscador pinta la tabla dos veces y escribe la cabecera con otra
    forma («Empresa / Atividad autorizada»)."""
    filas = _filas(GOLDEN / "servicios-buscador-buscar-htm.html")
    # Diez por página; el pie de la tabla repite la cabecera y no cuenta.
    assert len(filas) == 10
    assert len({tuple(f.values()) for f in filas}) == 10
    # Y aquí la fecha va con el día delante.
    assert all(re.fullmatch(r"\d{2}/\d{2}/\d{4}", f["fecha_autorizacion"]) for f in filas)


@pytest.mark.parametrize(
    ("texto", "fecha"),
    [
        ("2018/06/01", date(2018, 6, 1)),
        ("24/09/2025", date(2025, 9, 24)),
        ("01/06/18", None),
        ("", None),
    ],
)
def test_las_dos_formas_de_fecha(texto, fecha):
    from sinapsis_ingest.connectors.oci import _fecha

    assert _fecha(texto) == fecha


def test_la_tabla_de_la_fuente_de_los_datos_no_se_confunde():
    html = (
        "<table><tr><th>Fuente de los datos</th><th>Oficina</th></tr>"
        "<tr><td>a</td><td>b</td></tr></table>"
    )
    assert leer_tablas(html) == []


def test_el_nombre_se_publica_en_el_orden_de_la_fuente():
    assert en_minusculas("VELA OLMO, CARMEN") == "Vela Olmo, Carmen"
    assert en_minusculas("ROSA CORDON, RUFINO DE LA") == "Rosa Cordon, Rufino de la"
    # Sin nombre de pila en la fuente: no se inventa uno reordenando.
    assert en_minusculas("LORA-TAMAYO, D\u00b4OCON") == "Lora-Tamayo, D\u00b4Ocon"


@pytest.mark.parametrize(
    ("fuente", "cruce"),
    [
        ("BAÑEZ GARCIA, FATIMA", "fatima banez garcia"),
        ("ROSA CORDON, RUFINO DE LA", "rufino de la rosa cordon"),
        ("MONTORO ROMERO, CRISTOBAL", "cristobal montoro romero"),
    ],
)
def test_el_nombre_para_cruzar_con_el_boe(fuente, cruce):
    assert nombre_para_cruzar(fuente) == cruce


def test_normaliza_la_autorizacion_y_el_cese():
    raw = RawDocument(
        source_id="oci",
        url="https://transparencia.gob.es/x",
        content=PAGINA_2020.read_bytes(),
        media_type="text/html",
    )
    conector = OCIConnector()
    registros = list(conector.parse(raw))
    montoro = next(r for r in registros if r.data["nombre"] == "MONTORO ROMERO, CRISTOBAL")
    n = conector.normalize(montoro)
    assert n is not None
    n.validar()
    persona = next(e for e in n.entidades if e.ftm_schema == "Person")
    assert persona.caption == "Montoro Romero, Cristobal"
    assert persona.properties["cargo_publico"] is True
    assert persona.dedupe_key.startswith("oci:persona:")
    cese = next(a for a in n.aristas if a.ftm_schema == "Occupancy")
    assert cese.end_date == date(2018, 6, 1) and cese.start_date is None
    assert cese.properties["cargo"] == "MINISTRO DE HACIENDA Y FUNCION PUBLICA"
    autorizacion = next(a for a in n.aristas if a.ftm_schema == "UnknownLink")
    assert autorizacion.start_date == date(2020, 1, 9)
    assert autorizacion.properties["relacion"] == "autorizacion_actividad_privada"
    assert autorizacion.properties["actividad"].startswith("CONSEJERO-ASESOR DE LA JUNTA DIRECTIVA")
    assert autorizacion.confidence == 1.0 and autorizacion.status == "asserted"
    # Cada autorización tiene su clave; el cese, en cambio, es uno por persona
    # y cargo aunque tenga dos autorizaciones.
    autorizaciones = [
        a.dedupe_key
        for r in registros
        for a in (conector.normalize(r) or n).aristas
        if a.ftm_schema == "UnknownLink"
    ]
    assert len(autorizaciones) == len(set(autorizaciones)) == 15
    ceses = {
        a.dedupe_key
        for r in registros
        for a in (conector.normalize(r) or n).aristas
        if a.ftm_schema == "Occupancy"
    }
    assert len(ceses) == 13


# --- La exportación del buscador: la forma con la que se ingiere ------------

import httpx  # noqa: E402

from sinapsis_ingest.connectors.oci import leer_hoja  # noqa: E402

HOJA = GOLDEN / "autorizaciones-vigentes.xlsx"
BUSCADOR_HTML = GOLDEN / "servicios-buscador-buscar-htm.html"


def test_la_hoja_exportada_trae_todas_las_autorizaciones():
    """El buscador decía 644 resultados; la hoja trae las 644."""
    filas = leer_hoja(HOJA.read_bytes())
    assert len(filas) == 644
    primera = filas[0]
    assert primera["nombre"] == "GOMEZ GONZALEZ, CELIA"
    assert primera["cargo"] == "D. GRAL. DE ORDENACION PROFESIONAL"
    assert primera["fecha_autorizacion"] == "28/04/2026"
    # Las de 2019 que se leían en las páginas de seguimiento también están.
    assert any(f["nombre"] == "BAÑEZ GARCIA, FATIMA" and "ROVI" in f["actividad"] for f in filas)


def test_una_hoja_que_no_es_la_esperada_no_se_lee():
    assert leer_hoja(b"PK\x03\x04no es un zip") == []


def test_toda_fila_de_la_hoja_se_normaliza_con_sus_fechas():
    conector = OCIConnector()
    raw = RawDocument(
        source_id="oci", url="https://x", content=HOJA.read_bytes(), media_type="application/zip"
    )
    registros = list(conector.parse(raw))
    assert len(registros) == 644
    sin_fecha = []
    for r in registros:
        n = conector.normalize(r)
        assert n is not None
        n.validar()
        autorizacion = next(a for a in n.aristas if a.ftm_schema == "UnknownLink")
        if autorizacion.start_date is None:
            sin_fecha.append(r.data["fecha_autorizacion"])
    assert not sin_fecha, sin_fecha[:5]


def test_fetch_baja_la_exportacion_que_enlaza_el_buscador():
    pedidas: list[str] = []

    def servidor(peticion: httpx.Request) -> httpx.Response:
        pedidas.append(str(peticion.url))
        if "expTab.htm" in str(peticion.url):
            return httpx.Response(
                200,
                content=HOJA.read_bytes(),
                headers={"content-type": "application/zip;charset=UTF-8"},
            )
        return httpx.Response(
            200, content=BUSCADOR_HTML.read_bytes(), headers={"content-type": "text/html"}
        )

    cliente = httpx.Client(transport=httpx.MockTransport(servidor))
    [doc] = list(OCIConnector(cliente=cliente).fetch())
    assert "expTab.htm" in doc.url and "&amp;" not in doc.url
    assert doc.media_type == "application/zip"
    assert len(pedidas) == 2
    assert len(list(OCIConnector().parse(doc))) == 644
