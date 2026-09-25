"""Conector del BOE contra las disposiciones reales que guardó el reconocimiento.

Golden tests (CLAUDE.md): `tests/golden/boe_disposiciones/*.xml` son los XML
tal cual los sirvió www.boe.es, y `boe_altos_cargos_muestra.json` los ítems
del sumario en los que aparecían. La descarga se prueba con un transporte
falso que sirve esos mismos bytes: sin red, pero con la forma de verdad.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from sinapsis_ingest.connectors.base import RawDocument
from sinapsis_ingest.connectors.boe import BOEConnector, clave, es_candidato, items_2a

GOLDEN = Path(__file__).parent / "golden"
XML = GOLDEN / "boe_disposiciones"


def _raw(identificador: str) -> RawDocument:
    return RawDocument(
        source_id="boe",
        url=f"https://www.boe.es/diario_boe/xml.php?id={identificador}",
        content=(XML / f"{identificador}.xml").read_bytes(),
        media_type="application/xml",
    )


def _registros(identificador: str) -> list:
    return list(BOEConnector().parse(_raw(identificador)))


# --- parse -------------------------------------------------------------------


def test_un_nombramiento_real():
    [r] = _registros("BOE-A-2026-18440")
    d = r.data
    assert d["identificador"] == "BOE-A-2026-18440"
    assert d["tipo"] == "nombramiento"
    assert d["nombre"] == "Sara Hernández del Olmo"
    assert d["cargo"] == "Secretaria General de Transporte Terrestre"
    # Del XML, con su caja: el sumario lo trae en mayúsculas.
    assert d["departamento"] == "Ministerio de Transportes y Movilidad Sostenible"
    assert d["fecha_publicacion"] == "20260902"
    assert d["fecha_disposicion"] == "20260901"
    assert d["rango"] == "Real Decreto"
    assert d["numero"] == "714/2026"


def test_un_cese_real():
    [r] = _registros("BOE-A-2026-18438")
    assert r.data["tipo"] == "cese"
    assert r.data["nombre"] == "Rocío Báguena Rodríguez"
    assert r.data["cargo"] == "Secretaria General de Transporte Terrestre"


def test_todas_las_disposiciones_guardadas_se_leen():
    for xml in sorted(XML.glob("*.xml")):
        assert _registros(xml.stem), xml.name


def test_un_xml_roto_no_revienta():
    raw = RawDocument(source_id="boe", url="x", content=b"<documento><meta", media_type="x")
    assert list(BOEConnector().parse(raw)) == []


def test_un_xml_sin_alto_cargo_no_produce_nada():
    """Si un día llega el XML de un fiscal —no debería, el filtro va antes—,
    tampoco pasa de aquí."""
    contenido = (XML / "BOE-A-2026-18440.xml").read_text(encoding="utf-8")
    contenido = contenido.replace(
        "se nombra Secretaria General de Transporte Terrestre",
        "se nombra Fiscal de la Fiscalía Especial Antidroga",
    )
    raw = RawDocument(source_id="boe", url="x", content=contenido.encode(), media_type="x")
    assert list(BOEConnector().parse(raw)) == []


# --- normalize ---------------------------------------------------------------


def test_normaliza_a_persona_puesto_y_organismo():
    [r] = _registros("BOE-A-2026-18440")
    n = BOEConnector().normalize(r)
    assert n is not None
    n.validar()
    por_esquema = {e.ftm_schema: e for e in n.entidades}
    persona = por_esquema["Person"]
    assert persona.dedupe_key.startswith("boe:persona:sara-hernandez-del-olmo-")
    assert persona.properties["cargo_publico"] is True
    assert persona.nif == ""
    # El puesto, sin el género de quien lo ocupa: es el mismo que tuvo
    # Rocío Báguena Rodríguez hasta ese día.
    assert por_esquema["Position"].caption == "Secretario General de Transporte Terrestre"
    assert por_esquema["PublicBody"].caption == "Ministerio de Transportes y Movilidad Sostenible"

    [ocupacion] = [a for a in n.aristas if a.ftm_schema == "Occupancy"]
    assert ocupacion.dedupe_key == "boe:BOE-A-2026-18440"
    assert ocupacion.start_date == date(2026, 9, 2)
    assert ocupacion.end_date is None
    assert ocupacion.properties["url"].endswith("BOE-A-2026-18440")
    assert ocupacion.confidence == 1.0 and ocupacion.status == "asserted"


def test_nombramiento_y_cese_del_mismo_puesto_caen_en_el_mismo_puesto():
    conector = BOEConnector()
    [entra] = _registros("BOE-A-2026-18440")
    [sale] = _registros("BOE-A-2026-18438")
    a, b = conector.normalize(entra), conector.normalize(sale)
    assert a is not None and b is not None
    puesto = {e.dedupe_key for e in a.entidades if e.ftm_schema == "Position"}
    assert puesto == {e.dedupe_key for e in b.entidades if e.ftm_schema == "Position"}
    [cese] = [x for x in b.aristas if x.ftm_schema == "Occupancy"]
    assert cese.end_date == date(2026, 9, 2) and cese.start_date is None


# --- fetch -------------------------------------------------------------------


def _sumario(items: list[dict]) -> dict:
    """Un sumario con la forma que confirmó el reconocimiento."""
    por_dep: dict[str, list[dict]] = {}
    for i in items:
        limpio = {k: v for k, v in i.items() if not k.startswith("_")}
        por_dep.setdefault(i["_departamento"], []).append(limpio)
    return {
        "status": {"code": "200", "text": "ok"},
        "data": {
            "sumario": {
                "diario": [
                    {
                        "seccion": [
                            {
                                "codigo": "2A",
                                "departamento": [
                                    {
                                        "nombre": d,
                                        "epigrafe": {"nombre": "Nombramientos", "item": its},
                                    }
                                    for d, its in por_dep.items()
                                ],
                            }
                        ]
                    }
                ]
            }
        },
    }


@pytest.fixture
def muestra() -> list[dict]:
    return json.loads((GOLDEN / "boe_altos_cargos_muestra.json").read_text(encoding="utf-8"))[
        "items"
    ]


class _Servidor:
    """Sirve los sumarios y las disposiciones de la muestra, y cuenta."""

    def __init__(self, muestra: list[dict]) -> None:
        self.por_dia: dict[str, list[dict]] = {}
        for i in muestra:
            self.por_dia.setdefault(i["_fecha"], []).append(i)
        self.peticiones: list[str] = []

    def __call__(self, peticion: httpx.Request) -> httpx.Response:
        url = str(peticion.url)
        self.peticiones.append(url)
        if "/sumario/" in url:
            dia = url.rsplit("/", 1)[1]
            if dia not in self.por_dia:
                return httpx.Response(404)
            return httpx.Response(200, json=_sumario(self.por_dia[dia]))
        identificador = peticion.url.params.get("id", "")
        ruta = XML / f"{identificador}.xml"
        if ruta.exists():
            return httpx.Response(200, content=ruta.read_bytes())
        # Una disposición de la muestra sin XML guardado.
        return httpx.Response(200, content=b"<documento><metadatos/></documento>")


def _conector(servidor: _Servidor, **kw) -> BOEConnector:
    cliente = httpx.Client(transport=httpx.MockTransport(servidor))
    return BOEConnector(cliente=cliente, pausa=0, **kw)


def test_el_sumario_de_la_muestra_se_recorre(muestra):
    items = items_2a(_sumario(muestra))
    assert len(items) == len(muestra)
    assert all(i["_departamento"] for i in items)


def test_solo_se_baja_lo_que_es_alto_cargo(muestra):
    """Los fiscales de la muestra no llegan ni a pedirse."""
    servidor = _Servidor(muestra)
    docs = list(
        _conector(servidor).fetch(fecha_desde=date(2026, 8, 26), fecha_hasta=date(2026, 9, 16))
    )
    pedidos = [u for u in servidor.peticiones if "xml.php" in u]
    altos = [i for i in muestra if es_candidato(i)]
    assert len(pedidos) == len(altos) == len(docs)
    assert not any("Fiscal" in i["titulo"] for i in altos)
    assert len(altos) < len(muestra)


def test_la_cache_evita_volver_a_pedir(muestra, tmp_path):
    servidor = _Servidor(muestra)
    rango = {"fecha_desde": date(2026, 8, 26), "fecha_hasta": date(2026, 9, 16)}
    primera = list(_conector(servidor, cache=tmp_path).fetch(**rango))
    n = len(servidor.peticiones)
    segunda = list(_conector(servidor, cache=tmp_path).fetch(**rango))
    assert len(servidor.peticiones) == n, "la segunda vuelta no debería pedir nada"
    assert [d.content_hash for d in primera] == [d.content_hash for d in segunda]


def test_un_dia_sin_boe_se_recuerda(muestra, tmp_path):
    servidor = _Servidor(muestra)
    dia = {"fecha_desde": date(2026, 8, 30), "fecha_hasta": date(2026, 8, 30)}
    list(_conector(servidor, cache=tmp_path).fetch(**dia))
    list(_conector(servidor, cache=tmp_path).fetch(**dia))
    assert len(servidor.peticiones) == 1


def test_el_cupo_de_dias_nuevos_deja_lo_viejo_para_otra_noche(muestra, tmp_path):
    """De lo reciente hacia atrás: con cupo 1 sólo se lee el último día."""
    servidor = _Servidor(muestra)
    list(
        _conector(servidor, cache=tmp_path, max_dias_nuevos=1).fetch(
            fecha_desde=date(2026, 8, 26), fecha_hasta=date(2026, 9, 16)
        )
    )
    sumarios = [u for u in servidor.peticiones if "/sumario/" in u]
    assert sumarios == ["https://www.boe.es/datosabiertos/api/boe/sumario/20260916"]


def test_la_clave_no_depende_de_tildes_ni_mayusculas():
    assert clave("Directora General de Transporte") == clave("Directora general de transporte")
    assert clave("Sara Hernández del Olmo") == clave("Sara Hernandez del Olmo")
    assert clave("Sara Hernández del Olmo").startswith("sara-hernandez-del-olmo-")
    # Letras distintas son personas distintas.
    assert clave("Mª del Pilar Pin Vega") != clave("María del Pilar Pin Vega")
