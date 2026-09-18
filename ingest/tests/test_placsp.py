"""Tests del conector de PLACSP contra una muestra ATOM/CODICE real.

La muestra es una respuesta auténtica del feed de plataformas agregadas, con
la reserva documentada en `tests/golden/README.md`: es un espejo de terceros y
lleva un segundo adjudicatario añadido para pruebas. La **estructura** está
verificada contra datos reales, que es lo que un golden test debe proteger.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from sinapsis_ingest.connectors.base import RawDocument
from sinapsis_ingest.connectors.placsp import FEEDS, NS, PLACSPConnector

MUESTRA = Path(__file__).parent / "golden" / "placsp_agregadas_muestra.atom"


@pytest.fixture
def conector() -> PLACSPConnector:
    return PLACSPConnector(peticiones_por_segundo=0)


@pytest.fixture
def crudo() -> RawDocument:
    return RawDocument(
        source_id="placsp",
        url="https://contrataciondelestado.es/sindicacion/sindicacion_1044/x.atom",
        content=MUESTRA.read_bytes(),
        media_type="application/atom+xml",
        retrieved_at=datetime(2026, 8, 3, tzinfo=UTC),
    )


# --- estructura: si PLACSP cambia el formato, esto lo caza -----------------


def test_los_namespaces_codice_siguen_siendo_los_esperados():
    contenido = MUESTRA.read_text(encoding="utf-8")
    for uri in NS.values():
        assert uri in contenido, f"la muestra real no declara el namespace {uri}"


def test_el_feed_trae_entries():
    assert b"<entry>" in MUESTRA.read_bytes()


# --- parse ----------------------------------------------------------------


def test_parse_extrae_el_contrato(conector, crudo):
    registros = list(conector.parse(crudo))
    assert len(registros) == 1


def test_parse_lee_los_campos_clave(conector, crudo):
    d = next(iter(conector.parse(crudo))).data

    assert d["entry_id"].startswith("https://contrataciondelestado.es/sindicacion/")
    assert d["expediente"] == "C. 2-2021"
    assert d["organo"] == "Ajuntament de Sant Ramon"
    assert d["organo_padre"] == "Entitats municipals de Catalunya"
    assert d["estado"] == "ADJ"
    assert d["cpv"] == "34928530"
    assert d["nuts"] == "ES513"
    assert d["presupuesto"] == Decimal("135553.26")
    assert d["actualizado"] == date(2022, 1, 3)


def test_parse_enlaza_con_el_crudo(conector, crudo):
    for r in conector.parse(crudo):
        assert r.raw_content_hash == crudo.content_hash
        assert r.extractor_version == "placsp/1"


def test_parse_es_puro(conector, crudo):
    assert [r.data for r in conector.parse(crudo)] == [r.data for r in conector.parse(crudo)]


def test_parse_recoge_todos_los_adjudicatarios(conector, crudo):
    """Un contrato puede tener varios: lotes o UTE. Perder uno es perder dinero."""
    d = next(iter(conector.parse(crudo))).data
    assert len(d["adjudicaciones"]) == 2

    primero = d["adjudicaciones"][0]
    assert primero["nif"] == "A28526275"
    assert "AERONAVAL" in primero["nombre"]
    assert primero["importe"] == Decimal("90078.51")
    assert primero["moneda"] == "EUR"


def test_parse_descarta_nif_mal_formado(conector, crudo):
    # El segundo adjudicatario de la muestra trae "A28526275 II", que no es un
    # NIF válido. Preferimos vacío a afirmar un identificador falso.
    d = next(iter(conector.parse(crudo))).data
    assert d["adjudicaciones"][1]["nif"] == ""


def test_parse_tolera_xml_invalido(conector):
    roto = RawDocument(
        source_id="placsp",
        url="https://ejemplo.test",
        content=b"<feed><entry> sin cerrar",
        media_type="application/atom+xml",
    )
    assert list(conector.parse(roto)) == []


def test_parse_tolera_entry_sin_contract_folder(conector):
    vacio = (
        b'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">'
        b"<entry><id>x</id></entry></feed>"
    )
    raw = RawDocument(
        source_id="placsp",
        url="https://ejemplo.test",
        content=vacio,
        media_type="application/atom+xml",
    )
    assert list(conector.parse(raw)) == []


# --- normalize ------------------------------------------------------------


def _normalizado(conector, crudo):
    registro = next(iter(conector.parse(crudo)))
    n = conector.normalize(registro)
    assert n is not None
    return n


def test_normalize_produce_contract_y_contract_awards(conector, crudo):
    n = _normalizado(conector, crudo)
    n.validar()  # las aristas deben referenciar entidades que se van a crear

    esquemas = {e.ftm_schema for e in n.entidades}
    assert "Contract" in esquemas  # el expediente es una entidad en FtM
    assert "PublicBody" in esquemas
    assert all(a.ftm_schema == "ContractAward" for a in n.aristas)


def test_la_arista_va_del_contrato_al_adjudicatario(conector, crudo):
    n = _normalizado(conector, crudo)
    contrato = next(e for e in n.entidades if e.ftm_schema == "Contract")
    # Dirección canónica de FtM: contract -> supplier.
    for a in n.aristas:
        assert a.source_key == contrato.dedupe_key
        assert a.target_key != contrato.dedupe_key


def test_hay_una_arista_por_adjudicatario(conector, crudo):
    n = _normalizado(conector, crudo)
    assert len(n.aristas) == 2
    assert len({a.dedupe_key for a in n.aristas}) == 2, "las claves de arista colisionan"


def test_el_adjudicatario_con_nif_converge_con_otras_fuentes(conector, crudo):
    # La clave nif: es la misma que usa BDNS: es lo que permite que el mapa
    # conecte subvenciones y contratos de la misma empresa.
    n = _normalizado(conector, crudo)
    claves = {e.dedupe_key for e in n.entidades}
    assert "nif:A28526275" in claves


def test_el_adjudicatario_sin_nif_baja_la_confianza(conector, crudo):
    n = _normalizado(conector, crudo)
    con_nif = [a for a in n.aristas if a.confidence == 1.0]
    sin_nif = [a for a in n.aristas if a.confidence == 0.7]
    assert len(con_nif) == 1
    assert len(sin_nif) == 1


def test_el_contrato_referencia_a_su_organo(conector, crudo):
    n = _normalizado(conector, crudo)
    contrato = next(e for e in n.entidades if e.ftm_schema == "Contract")
    organo = next(e for e in n.entidades if e.ftm_schema == "PublicBody")
    # En FollowTheMoney la autoridad es una propiedad del contrato, no una
    # arista: no existe esquema de arista órgano->contrato.
    assert contrato.properties["authority"] == organo.dedupe_key


def test_el_contrato_conserva_cpv_y_expediente(conector, crudo):
    n = _normalizado(conector, crudo)
    contrato = next(e for e in n.entidades if e.ftm_schema == "Contract")
    assert contrato.properties["cpvCode"] == "34928530"
    assert contrato.properties["procedureNumber"] == "C. 2-2021"


def test_importe_siempre_con_moneda(conector, crudo):
    # El esquema rechaza un importe sin moneda.
    n = _normalizado(conector, crudo)
    for a in n.aristas:
        if a.amount is not None:
            assert a.currency


def test_normalize_descarta_licitacion_sin_adjudicar(conector):
    """Una licitación aún no adjudicada es un hueco legítimo, no un error."""
    # Los namespaces se toman del propio conector para no repetir URIs largas.
    ns_decl = " ".join(f'xmlns:{pfx}="{uri}"' for pfx, uri in NS.items() if pfx != "atom")
    sin_adj = (
        '<?xml version="1.0"?>'
        f'<feed xmlns="http://www.w3.org/2005/Atom" {ns_decl}>'
        "<entry><id>https://ejemplo.test/1</id>"
        "<cac-place-ext:ContractFolderStatus>"
        "<cbc:ContractFolderID>EXP-1</cbc:ContractFolderID>"
        "<cac-place-ext:LocatedContractingParty><cac:Party><cac:PartyName>"
        "<cbc:Name>Ayuntamiento de Prueba</cbc:Name>"
        "</cac:PartyName></cac:Party></cac-place-ext:LocatedContractingParty>"
        "</cac-place-ext:ContractFolderStatus></entry></feed>"
    ).encode()

    raw = RawDocument(
        source_id="placsp",
        url="https://ejemplo.test",
        content=sin_adj,
        media_type="application/atom+xml",
    )
    registro = next(iter(conector.parse(raw)))
    assert registro.data["organo"] == "Ayuntamiento de Prueba"
    assert conector.normalize(registro) is None


# --- fetch: encadenado ATOM -----------------------------------------------


def test_el_encadenado_resuelve_hrefs_relativos(conector, crudo):
    # rel="next" viene como nombre de fichero, no como URL absoluta.
    siguiente = PLACSPConnector._siguiente(
        MUESTRA.read_bytes(),
        "https://contrataciondelestado.es/sindicacion/sindicacion_1044/actual.atom",
    )
    assert siguiente == (
        "https://contrataciondelestado.es/sindicacion/sindicacion_1044/"
        "PlataformasAgregadasSinMenores_20211231_030012.atom"
    )


def test_fetch_sigue_el_encadenado():
    servidas = []
    cuerpo = MUESTRA.read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        servidas.append(str(request.url))
        return httpx.Response(200, content=cuerpo, headers={"content-type": "application/atom+xml"})

    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    conector = PLACSPConnector(cliente=cliente, peticiones_por_segundo=0)

    docs = list(conector.fetch(feed="agregadas", max_paginas=3))
    assert len(docs) == 3
    # La segunda petición ya es la que apuntaba rel="next".
    assert "20211231" in servidas[1]


def test_fetch_para_en_max_paginas():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=MUESTRA.read_bytes())

    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    conector = PLACSPConnector(cliente=cliente, peticiones_por_segundo=0)
    assert len(list(conector.fetch(max_paginas=1))) == 1


def test_fetch_tolera_error_http_sin_inventar():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="no disponible")

    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    conector = PLACSPConnector(cliente=cliente, peticiones_por_segundo=0)
    assert list(conector.fetch(max_paginas=5)) == []


def test_feed_desconocido_falla_pronto(conector):
    with pytest.raises(ValueError, match="feed desconocido"):
        list(conector.fetch(feed="inventado"))


def test_los_feeds_conocidos_son_urls_de_placsp():
    for url in FEEDS.values():
        assert url.startswith("https://contrataciondelestado.es/sindicacion/")


# --- minimización de datos personales (spec §12) --------------------------


def _feed_con_adjudicatarios(*partes: tuple[str, str]) -> bytes:
    """Construye un feed CODICE mínimo con los adjudicatarios dados."""
    ns_decl = " ".join(f'xmlns:{pfx}="{uri}"' for pfx, uri in NS.items() if pfx != "atom")
    ganadores = "".join(
        "<cac:WinningParty>"
        f'<cac:PartyIdentification><cbc:ID schemeName="NIF">{nif}</cbc:ID>'
        "</cac:PartyIdentification>"
        f"<cac:PartyName><cbc:Name>{nombre}</cbc:Name></cac:PartyName>"
        "</cac:WinningParty>"
        for nif, nombre in partes
    )
    return (
        '<?xml version="1.0"?>'
        f'<feed xmlns="http://www.w3.org/2005/Atom" {ns_decl}>'
        "<entry><id>https://ejemplo.test/contrato-1</id>"
        "<cac-place-ext:ContractFolderStatus>"
        "<cbc:ContractFolderID>EXP-9</cbc:ContractFolderID>"
        "<cac-place-ext:LocatedContractingParty><cac:Party><cac:PartyName>"
        "<cbc:Name>Ayuntamiento de Prueba</cbc:Name>"
        "</cac:PartyName></cac:Party></cac-place-ext:LocatedContractingParty>"
        f"<cac:TenderResult><cbc:ResultCode>8</cbc:ResultCode>{ganadores}"
        "<cac:AwardedTenderedProject><cac:LegalMonetaryTotal>"
        '<cbc:TaxExclusiveAmount currencyID="EUR">1000.00</cbc:TaxExclusiveAmount>'
        "</cac:LegalMonetaryTotal></cac:AwardedTenderedProject>"
        "</cac:TenderResult>"
        "</cac-place-ext:ContractFolderStatus></entry></feed>"
    ).encode()


def _normalizar_feed(conector, contenido: bytes):
    raw = RawDocument(
        source_id="placsp",
        url="https://ejemplo.test",
        content=contenido,
        media_type="application/atom+xml",
    )
    return conector.normalize(next(iter(conector.parse(raw))))


def test_el_adjudicatario_persona_fisica_no_se_publica_con_nombre(conector):
    """PLACSP publica el nombre del autónomo; nosotros no lo republicamos.

    Se descubrió en la instantánea real: 25 personas físicas con nombre y
    apellidos en un mapa de influencia política. Mismo criterio que en BDNS —
    el hecho se conserva, la identidad no.
    """
    n = _normalizar_feed(conector, _feed_con_adjudicatarios(("12345678Z", "JUAN PEREZ GOMEZ")))
    assert n is not None

    plano = json.dumps(
        [e.__dict__ for e in n.entidades] + [a.__dict__ for a in n.aristas],
        default=str,
        ensure_ascii=False,
    )
    for prohibido in ("JUAN", "PEREZ", "GOMEZ", "12345678Z"):
        assert prohibido not in plano, f"se publicó {prohibido}"

    # Pero el dinero y el órgano siguen ahí: es un hueco de identidad, no de hecho.
    assert n.aristas[0].amount is not None
    assert any(e.ftm_schema == "PublicBody" for e in n.entidades)
    agregado = [e for e in n.entidades if e.dedupe_key.startswith("placsp:particulares:")]
    assert len(agregado) == 1
    assert agregado[0].properties["agregado"] is True


def test_una_sociedad_con_nif_de_aspecto_personal_no_es_persona(conector):
    """El nombre desmiente al NIF: una S.L. es una S.L.

    En la instantánea real, "NACATUR 2 ESPAÑA, S.L." y "Explorance Inc"
    salieron clasificadas como Person porque su identificador empezaba por
    dígito.
    """
    n = _normalizar_feed(
        conector, _feed_con_adjudicatarios(("12345678Z", "NACATUR 2 ESPAÑA, S.L."))
    )
    assert n is not None
    adjudicatario = next(e for e in n.entidades if e.ftm_schema not in ("PublicBody", "Contract"))
    assert adjudicatario.ftm_schema == "Company"
    assert adjudicatario.caption == "NACATUR 2 ESPAÑA, S.L."


def test_dos_particulares_en_el_mismo_contrato_no_pierden_dinero(conector):
    """El nodo es un agregado compartido; las aristas no pueden colapsar.

    Si las dos adjudicaciones compartieran clave, una de las dos desaparecería
    y el importe adjudicado saldría a la mitad.
    """
    n = _normalizar_feed(
        conector,
        _feed_con_adjudicatarios(("12345678Z", "JUAN PEREZ"), ("87654321X", "ANA LOPEZ")),
    )
    assert n is not None
    claves = {a.dedupe_key for a in n.aristas}
    assert len(claves) == 2, "una adjudicación se perdió al agregar a los particulares"
    # Y las dos apuntan al mismo nodo agregado.
    assert len({a.target_key for a in n.aristas}) == 1
