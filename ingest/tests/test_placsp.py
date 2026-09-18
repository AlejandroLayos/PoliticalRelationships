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

from sinapsis_ingest.connectors.base import ParsedRecord, RawDocument
from sinapsis_ingest.connectors.placsp import (
    FEEDS,
    NS,
    PLACSPConnector,
    PLACSPLicitacionesConnector,
    PLACSPMenoresConnector,
)

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
    # Dos clases de arista, y las dos hacen falta: la adjudicación lleva el
    # dinero al proveedor, y el enlace del órgano cuelga el contrato de quien
    # lo adjudicó. Sin la segunda el organismo queda suelto en el grafo.
    assert {a.ftm_schema for a in n.aristas} == {"ContractAward", "UnknownLink"}


def test_la_arista_va_del_contrato_al_adjudicatario(conector, crudo):
    n = _normalizado(conector, crudo)
    contrato = next(e for e in n.entidades if e.ftm_schema == "Contract")
    # Dirección canónica de FtM: contract -> supplier.
    for a in n.aristas:
        if a.ftm_schema != "ContractAward":
            continue
        assert a.source_key == contrato.dedupe_key
        assert a.target_key != contrato.dedupe_key


def test_hay_una_arista_por_adjudicatario(conector, crudo):
    n = _normalizado(conector, crudo)
    adjudicaciones = [a for a in n.aristas if a.ftm_schema == "ContractAward"]
    assert len(adjudicaciones) == 2
    assert len({a.dedupe_key for a in n.aristas}) == len(n.aristas), (
        "las claves de arista colisionan"
    )


def test_el_adjudicatario_con_nif_converge_con_otras_fuentes(conector, crudo):
    # La clave nif: es la misma que usa BDNS: es lo que permite que el mapa
    # conecte subvenciones y contratos de la misma empresa.
    n = _normalizado(conector, crudo)
    claves = {e.dedupe_key for e in n.entidades}
    assert "nif:A28526275" in claves


def test_el_adjudicatario_sin_nif_baja_la_confianza(conector):
    # Sobre un registro propio y no sobre la muestra: los dos adjudicatarios de
    # la muestra van en el MISMO TenderResult —es una UTE— y comparten importe,
    # así que la regla del importe compartido les baja la confianza a los dos y
    # tapaba lo que este test quiere mirar, que es el efecto del NIF.
    registro = ParsedRecord(
        raw_content_hash="z" * 64,
        extractor_version="test",
        data={
            "id_registro": "urn:nif:1",
            "entry_id": "urn:nif:1",
            "titulo": "Obra menor",
            "actualizado": date(2026, 3, 1),
            "organo": "Ayuntamiento de Ejemplo",
            "presupuesto": Decimal("200000"),
            "adjudicaciones": [
                {"nombre": "CON NIF SA", "nif": "A28526275", "importe": Decimal("120000"),
                 "moneda": "EUR", "codigo_resultado": "8"},
                {"nombre": "SIN NIF SL", "nif": "", "importe": Decimal("55000"),
                 "moneda": "EUR", "codigo_resultado": "8"},
            ],
        },
    )
    n = conector.normalize(registro)
    assert n is not None
    adjudicaciones = [a for a in n.aristas if a.ftm_schema == "ContractAward"]
    assert len([a for a in adjudicaciones if a.confidence == 1.0]) == 1
    assert len([a for a in adjudicaciones if a.confidence == 0.7]) == 1


def test_el_contrato_referencia_a_su_organo(conector, crudo):
    n = _normalizado(conector, crudo)
    contrato = next(e for e in n.entidades if e.ftm_schema == "Contract")
    organo = next(e for e in n.entidades if e.ftm_schema == "PublicBody")
    # En FollowTheMoney la autoridad es una propiedad del contrato: no existe
    # esquema de arista órgano->contrato.
    assert contrato.properties["authority"] == organo.dedupe_key

    # Pero una propiedad no se puede recorrer en un grafo, así que además hay
    # una arista `UnknownLink` con su `role`. Es la vía canónica de FtM para
    # "están relacionados y la naturaleza va aparte", y es lo que permite ver
    # qué organismo adjudicó qué.
    enlace = next(a for a in n.aristas if a.ftm_schema == "UnknownLink")
    assert enlace.source_key == organo.dedupe_key
    assert enlace.target_key == contrato.dedupe_key
    assert enlace.properties["role"] == "órgano de contratación"
    # Sin importe: el dinero lo lleva el ContractAward y duplicarlo aquí lo
    # contaría dos veces.
    assert enlace.amount is None


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
    adjudicacion = next(a for a in n.aristas if a.ftm_schema == "ContractAward")
    assert adjudicacion.amount is not None
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
    adjudicaciones = [a for a in n.aristas if a.ftm_schema == "ContractAward"]
    claves = {a.dedupe_key for a in adjudicaciones}
    assert len(claves) == 2, "una adjudicación se perdió al agregar a los particulares"
    # Y las dos apuntan al mismo nodo agregado.
    assert len({a.target_key for a in adjudicaciones}) == 1


# --- importes inverosímiles -----------------------------------------------
#
# El caso real: un transporte de obras para una exposición temporal, con
# presupuesto de 22.000 €, publicado con un importe adjudicado de
# 1.954.023.643,40 €. Esa sola cifra era el 8 % del dinero de todo el mapa y
# ponía a la adjudicataria en cabeza del ranking de quien más cobra del
# Estado. La adjudicación es real; la cifra, no.
#
# Se prueba `normalize` sobre su dict de entrada en vez de retocar el XML de la
# muestra: lo que se comprueba es la regla, y el camino del XML al dict ya lo
# cubren los tests de `parse` de más arriba.


def _registro(importe: str | None, presupuesto: str | None) -> ParsedRecord:
    return ParsedRecord(
        raw_content_hash="x" * 64,
        extractor_version="test",
        data={
            "id_registro": "urn:ejemplo:1",
            "entry_id": "urn:ejemplo:1",
            "titulo": "Transporte de una exposición temporal",
            "actualizado": date(2026, 3, 1),
            "organo": "Fundación Artium de Álava-Directora",
            "presupuesto": Decimal(presupuesto) if presupuesto is not None else None,
            "adjudicaciones": [
                {
                    "nombre": "CRISOSTOMO FINE ART SERVICES SL",
                    "nif": "B86179926",
                    "importe": Decimal(importe) if importe is not None else None,
                    "moneda": "EUR",
                    "codigo_resultado": "8",
                }
            ],
        },
    )


def _adjudicacion(conector, importe, presupuesto):
    n = conector.normalize(_registro(importe, presupuesto))
    assert n is not None
    return next(a for a in n.aristas if a.ftm_schema == "ContractAward")


def test_un_importe_imposible_no_se_publica_como_cifra(conector):
    adj = _adjudicacion(conector, "1954023643.40", "22000")
    # La adjudicación se conserva: ocurrió, y el adjudicatario es real.
    assert adj.target_key
    # Lo que no se publica es la cifra.
    assert adj.amount is None
    # Pero no se pierde: queda a la vista de quien quiera comprobarla.
    assert adj.properties["importeSinInterpretar"] == "1954023643.40"
    assert "22000" in adj.properties["motivoImporteDudoso"]
    assert adj.confidence <= 0.5


def test_un_importe_algo_por_encima_del_presupuesto_se_respeta(conector):
    # IVA, lotes contados de otra manera o una prórroga pueden dejar el importe
    # por encima del presupuesto sin que sea una errata. Sólo se descarta lo que
    # no tiene ninguna explicación posible. En los datos ingeridos, el 99,5 % de
    # las adjudicaciones está en 1,07 veces el presupuesto o por debajo.
    adj = _adjudicacion(conector, "26000", "22000")
    assert adj.amount == Decimal("26000")
    assert "importeSinInterpretar" not in adj.properties


def test_sin_presupuesto_no_hay_nada_contra_lo_que_comparar(conector):
    # Sin presupuesto publicado no se puede juzgar el importe, y descartarlo por
    # las dudas sería inventar un criterio: se publica tal cual.
    adj = _adjudicacion(conector, "1954023643.40", None)
    assert adj.amount == Decimal("1954023643.40")
    assert "importeSinInterpretar" not in adj.properties


def test_un_presupuesto_a_cero_no_dispara_la_regla(conector):
    # Dividir contra cero, o tratarlo como "todo es inverosímil", vaciaría de
    # importes a todos los contratos que publican el presupuesto como 0.
    adj = _adjudicacion(conector, "50000", "0")
    assert adj.amount == Decimal("50000")


# --- el importe del acuerdo marco no es el de cada adjudicatario -----------


def _registro_marco(importes: list[str | None]) -> ParsedRecord:
    return ParsedRecord(
        raw_content_hash="y" * 64,
        extractor_version="test",
        data={
            "id_registro": "urn:marco:1",
            "entry_id": "urn:marco:1",
            "titulo": "Acuerdo marco de servicios de desarrollo de sistemas",
            "actualizado": date(2026, 3, 1),
            "organo": "Dirección General de Sistemas",
            "presupuesto": Decimal("900000000"),
            "adjudicaciones": [
                {
                    "nombre": f"EMPRESA {i} SA",
                    "nif": f"A0000000{i}",
                    "importe": Decimal(imp) if imp is not None else None,
                    "moneda": "EUR",
                    "codigo_resultado": "8",
                }
                for i, imp in enumerate(importes)
            ],
        },
    )


def _adjudicaciones(conector, importes):
    n = conector.normalize(_registro_marco(importes))
    assert n is not None
    return [a for a in n.aristas if a.ftm_schema == "ContractAward"]


def test_el_valor_del_marco_no_se_atribuye_a_cada_adjudicatario(conector):
    # 20 adjudicatarios a 900 millones cada uno sumaban 18.000 millones: el
    # 85 % del dinero del mapa entero, y la web decía «INDRA recibió 908
    # millones de este organismo». Es falso: ese importe es el techo del
    # acuerdo, dentro del cual las 20 compiten por pedidos concretos.
    aristas = _adjudicaciones(conector, ["900000000"] * 20)
    assert len(aristas) == 20
    assert all(a.amount is None for a in aristas)
    for a in aristas:
        assert a.properties["importeCompartido"] == "900000000"
        assert a.properties["adjudicatariosQueComparten"] == 20
        assert "acuerdo marco" in a.properties["motivoImporteDudoso"]
        assert a.confidence <= 0.5


def test_la_adjudicacion_se_conserva_aunque_se_calle_la_cifra(conector):
    # Lo que se descarta es la atribución del importe, no el hecho: esas
    # empresas entraron en el marco y eso es un dato.
    aristas = _adjudicaciones(conector, ["900000000"] * 3)
    assert {a.target_key for a in aristas} == {
        "nif:A00000000",
        "nif:A00000001",
        "nif:A00000002",
    }


def test_con_importes_distintos_cada_uno_conserva_el_suyo(conector):
    # Lotes de valor distinto: aquí el importe sí es de cada adjudicatario.
    aristas = _adjudicaciones(conector, ["100000", "250000", "70000"])
    assert sorted(str(a.amount) for a in aristas) == ["100000", "250000", "70000"]
    assert all("importeCompartido" not in a.properties for a in aristas)


def test_solo_se_calla_el_importe_que_se_repite(conector):
    # Un contrato puede tener lotes repetidos y lotes únicos a la vez.
    aristas = _adjudicaciones(conector, ["500000", "500000", "31000"])
    porque = {str(a.target_key): a for a in aristas}
    assert porque["nif:A00000002"].amount == Decimal("31000")
    assert porque["nif:A00000000"].amount is None
    assert porque["nif:A00000001"].amount is None


def test_un_unico_adjudicatario_no_comparte_nada(conector):
    aristas = _adjudicaciones(conector, ["900000000"])
    assert aristas[0].amount == Decimal("900000000")


def test_varias_adjudicaciones_sin_importe_no_se_consideran_repetidas(conector):
    # `None` no es un importe compartido: es la ausencia de uno, y tratarla
    # como repetición añadiría un motivo falso a aristas que ya no tenían cifra.
    aristas = _adjudicaciones(conector, [None, None])
    assert all(a.amount is None for a in aristas)
    assert all("importeCompartido" not in a.properties for a in aristas)


# --- los tres feeds de la Plataforma ---------------------------------------
#
# Hasta el 18/9/2026 sólo se ingería `agregadas`, que trae lo que vuelcan las
# plataformas autonómicas. Todo lo publicado directamente en la Plataforma del
# Estado, y todo el contrato menor —donde vive el gasto municipal del día a
# día—, quedaba fuera del mapa sin que nada lo dijera.


class _ClienteFalso:
    """Devuelve la muestra pida lo que pida, y apunta a qué URL se le pidió."""

    def __init__(self):
        self.urls: list[str] = []

    def get(self, url, *a, **kw):
        self.urls.append(url)
        return httpx.Response(
            200,
            content=MUESTRA.read_bytes(),
            headers={"content-type": "application/atom+xml"},
            request=httpx.Request("GET", url),
        )

    def close(self):
        pass


@pytest.mark.parametrize(
    ("fabrica", "esperado"),
    [
        (PLACSPConnector, FEEDS["agregadas"]),
        (PLACSPLicitacionesConnector, FEEDS["licitaciones"]),
        (PLACSPMenoresConnector, FEEDS["menores"]),
    ],
    ids=["agregadas", "licitaciones", "menores"],
)
def test_cada_variante_pide_su_feed(fabrica, esperado):
    cliente = _ClienteFalso()
    conector = fabrica(cliente=cliente, peticiones_por_segundo=0)
    list(conector.fetch(max_paginas=1))
    assert cliente.urls[0] == esperado


def test_las_tres_variantes_comparten_fuente():
    # `source_id` es la fuente; la clave del registro es el conector. Si las
    # variantes declararan fuentes distintas, la misma empresa saldría
    # duplicada según por qué feed hubiera entrado.
    assert PLACSPLicitacionesConnector.source_id == PLACSPConnector.source_id
    assert PLACSPMenoresConnector.source_id == PLACSPConnector.source_id


def test_se_puede_pedir_otro_feed_a_una_variante():
    # El valor por defecto no puede impedir reutilizar el conector.
    cliente = _ClienteFalso()
    conector = PLACSPMenoresConnector(cliente=cliente, peticiones_por_segundo=0)
    list(conector.fetch(feed="licitaciones", max_paginas=1))
    assert cliente.urls[0] == FEEDS["licitaciones"]


def test_una_variante_normaliza_igual_que_la_base(crudo):
    # Mismo esquema CODICE: lo que cambia es de dónde se descarga.
    base = PLACSPConnector(peticiones_por_segundo=0)
    menores = PLACSPMenoresConnector(peticiones_por_segundo=0)
    r1 = next(iter(base.parse(crudo)))
    r2 = next(iter(menores.parse(crudo)))
    n1 = base.normalize(r1)
    n2 = menores.normalize(r2)
    assert n1 is not None and n2 is not None
    assert [a.dedupe_key for a in n1.aristas] == [a.dedupe_key for a in n2.aristas]


def test_un_feed_ilegible_dice_que_llego_y_no_solo_donde_falla(conector, capsys):
    # «mismatched tag: line 1, column 200» no permite saber si el servidor
    # sirvió un HTML de error, otro formato o un ATOM con una etiqueta rota.
    # El crudo queda guardado, pero el log es lo que se lee.
    raw = RawDocument(
        source_id="placsp",
        url="https://contrataciondelestado.es/sindicacion/x.atom",
        content=b"<html><head><title>Servicio no disponible</title></head><body>502</body>",
        media_type="text/html",
        retrieved_at=datetime(2026, 9, 18, tzinfo=UTC),
    )
    registros = list(conector.parse(raw))
    assert registros == []
    # structlog escribe por su cuenta, no por el logging de la librería
    # estándar, así que se mira la salida y no `caplog`.
    salida = capsys.readouterr().out
    assert "Servicio no disponible" in salida
    assert "text/html" in salida
