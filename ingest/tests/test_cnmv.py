"""CNMV: accionistas significativos y participaciones (spec §12, ampliación del 26/9/2026).

Golden tests (CLAUDE.md): `tests/golden/cnmv/*.html` son páginas reales que
guardó el reconocimiento (`scripts/explorar_cnmv.py`).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from sinapsis_ingest.cnmv import (
    consejeros_fijados,
    emisor_del_titulo,
    enlaces_de_participaciones,
    es_cuadro_del_consejo,
    es_medio_de_comunicacion,
    es_persona_fisica,
    informes_de_gobierno,
    leer_accionistas,
    leer_datos_generales,
    leer_participadas,
    miembros_del_consejo,
    nombre_de_persona,
)

GOLDEN = Path(__file__).parent / "golden" / "cnmv"


def _html(nombre: str) -> str:
    return (GOLDEN / nombre).read_text(encoding="utf-8")


def test_accionistas_de_telefonica():
    emisor, filas = leer_accionistas(_html("telefonica-notificaciones-participaciones-aspx.html"))
    assert emisor == "TELEFONICA, S.A."
    assert len(filas) == 6
    blackrock = filas[0]
    assert blackrock.titular == "BLACKROCK INC."
    assert blackrock.sociedad == "TELEFONICA, S.A."
    assert blackrock.por_acciones == Decimal("5.033")
    assert blackrock.directo == Decimal("0.000")
    assert blackrock.indirecto == Decimal("5.033")
    assert blackrock.por_instrumentos == Decimal("1.208")
    assert blackrock.porcentaje == Decimal("6.241")
    assert blackrock.fecha_registro == date(2026, 6, 23)
    assert "CRITERIA CAIXA, S.A.U." in {f.titular for f in filas}


def test_accionistas_de_prisa_con_una_persona():
    emisor, filas = leer_accionistas(_html("prisa-notificaciones-participaciones-aspx.html"))
    assert emisor == "PROMOTORA DE INFORMACIONES, S.A."
    titulares = {f.titular: f for f in filas}
    al_thani = titulares["AL THANI , KHALID THANI ABDULLAH"]
    assert al_thani.porcentaje == Decimal("3.353")
    assert es_persona_fisica(al_thani.titular)
    assert nombre_de_persona(al_thani.titular) == "KHALID THANI ABDULLAH AL THANI"
    assert not es_persona_fisica("AMBER CAPITAL UK LLP")


def test_participadas_de_santander():
    titular, filas = leer_participadas(_html("santander-sociedadesparticipa-aspx.html"))
    assert titular == "BANCO SANTANDER, S.A."
    por_sociedad = {f.sociedad: f for f in filas}
    assert por_sociedad["PROMOTORA DE INFORMACIONES, S.A."].porcentaje == Decimal("4.145")
    assert por_sociedad["METROVACESA, S.A."].porcentaje == Decimal("49.362")
    assert por_sociedad["METROVACESA, S.A."].fecha_registro == date(2018, 10, 4)
    assert all(f.titular == "BANCO SANTANDER, S.A." for f in filas)


def test_la_misma_participacion_vista_desde_los_dos_lados():
    """Santander en Prisa: la tabla de Prisa y la de Santander dicen lo mismo."""
    _, de_prisa = leer_accionistas(_html("prisa-notificaciones-participaciones-aspx.html"))
    _, de_santander = leer_participadas(_html("santander-sociedadesparticipa-aspx.html"))
    en_prisa = {f.titular: f.porcentaje for f in de_prisa}
    en_santander = {f.sociedad: f.porcentaje for f in de_santander}
    assert en_prisa.get("BANCO SANTANDER, S.A.") == en_santander["PROMOTORA DE INFORMACIONES, S.A."]


def test_una_pagina_sin_la_tabla_no_da_filas():
    # La de ps_ac_ini no trae tabla, sólo enlaces.
    assert leer_accionistas(_html("telefonica-participaciones.html"))[1] == []


def test_los_enlaces_de_ps_ac_ini():
    enlaces = enlaces_de_participaciones(_html("telefonica-participaciones.html"))
    assert enlaces["accionistas"].startswith("Notificaciones-Participaciones.aspx?qS={")
    assert enlaces["participadas"].startswith("SociedadesParticipa.aspx?qS={")


def test_el_emisor_sale_del_titulo():
    assert (
        emisor_del_titulo(
            "<title>CNMV - Sociedades cotizadas donde participa - BANCO SANTANDER, S.A.</title>"
        )
        == "BANCO SANTANDER, S.A."
    )
    assert emisor_del_titulo("<title>CNMV - Error</title>") == ""


@pytest.mark.parametrize(
    "denominacion",
    [
        "BLACKROCK INC.",
        "CRITERIA CAIXA, S.A.U.",
        "FUNDACION BANCARIA CAIXA D ESTALVIS I PENSIONS DE BARCELONA",
        "AMBER CAPITAL INVESTMENT MANAGEMENT ICAV - AMBER GLOBAL OPPORTUNITIES FUND",
        "NORGES BANK",
        "PONTEGADEA INVERSIONES, S.L.",
        "SOCIEDAD ESTATAL DE PARTICIPACIONES INDUSTRIALES",
        "THE CAPITAL GROUP COMPANIES",
        "STATE STREET CORPORATION",
        "VIVENDI, S.E.",
        "OVIEDO HOLDINGS S.A.R.L.",
        "CONTROL EMPRESARIAL DE CAPITALES, S.A. DE C.V.",
        "GLOBAL ALCONABA SL",
        # Los que la primera instantánea real publicó como personas (26/9/2026):
        # ninguno lleva la coma con la que la CNMV escribe a una persona.
        "MORGAN STANLEY",
        "DODGE & COX",
        "SONATRACH",
        "ENAIRE",
        "FROB",
        "INSTITUTO VASCO DE FINANZAS",
        "FI COBAS SELECCION",
        # Con coma, pero fondos de inversión: así los escribe la CNMV (26/9/2026).
        "COBAS SELECCION , FI",
        "COBAS IBERIA, F.I.",
        "INDEPENDANCE AM",
        "EDIZIONE S.R.L.",
        # Con coma, pero con forma jurídica.
        "BERTELSMANN , A.G.",
        "PLANETA CORPORACION , S.R.L.",
    ],
)
def test_sociedades(denominacion):
    assert not es_persona_fisica(denominacion)


@pytest.mark.parametrize(
    "denominacion",
    [
        "AL THANI , KHALID THANI ABDULLAH",
        "ORTEGA GAONA , AMANCIO",
        "PEREZ RODRIGUEZ , FLORENTINO",
        "UTOR MARTÍNEZ, JUAN ADOLFO",
        "GRIFOLS ROURA , ENRIQUE Y NURIA",
        "ANDERSEN , MARC P.",
        # «FI» sólo cuenta como forma cuando va suelto.
        "FIGUEROA FINCA , FILOMENA",
    ],
)
def test_personas(denominacion):
    assert es_persona_fisica(denominacion)


def test_nombre_de_persona_sin_coma_se_deja():
    assert nombre_de_persona("JUAN  PÉREZ") == "JUAN PÉREZ"


# --- El conector ----------------------------------------------------------------

import re  # noqa: E402

import httpx  # noqa: E402

from sinapsis_ingest.connectors.base import RawDocument  # noqa: E402
from sinapsis_ingest.connectors.cnmv import CNMVConnector, leer_semillas  # noqa: E402

TELEFONICA, SANTANDER, PRISA = "A28015865", "A39000013", "A28297059"
CONOCIDAS = {
    "TELEFONICA, S.A.": TELEFONICA,
    "BANCO SANTANDER, S.A.": SANTANDER,
    "PROMOTORA DE INFORMACIONES, S.A.": PRISA,
}


def _raw(nombre: str, nif: str, emisor: str, tabla: str) -> RawDocument:
    return RawDocument(
        source_id="cnmv",
        url=f"https://www.cnmv.es/x/{nombre}",
        content=(GOLDEN / nombre).read_bytes(),
        media_type="text/html",
        metadata={
            "nif": nif,
            "emisor": emisor,
            "tabla": tabla,
            "url_publica": f"https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif={nif}",
            "conocidas": CONOCIDAS,
        },
    )


def _normalizados(raw: RawDocument) -> list:
    c = CNMVConnector()
    return [c.normalize(r) for r in c.parse(raw)]


def test_accionistas_normalizados_de_prisa():
    raw = _raw(
        "prisa-notificaciones-participaciones-aspx.html",
        PRISA,
        "PROMOTORA DE INFORMACIONES, S.A.",
        "accionistas",
    )
    normalizados = [n for n in _normalizados(raw) if n]
    aristas = [a for n in normalizados for a in n.aristas]
    assert all(a.ftm_schema == "Ownership" for a in aristas)
    assert all(a.target_key == f"nif:{PRISA}" for a in aristas)
    entidades = {e.dedupe_key: e for n in normalizados for e in n.entidades}
    # Santander está en la lista: va por su NIF, como en el mapa del dinero.
    santander = next(a for a in aristas if a.source_key == f"nif:{SANTANDER}")
    assert santander.properties["porcentaje"] == "4.145"
    assert santander.properties["fechaRegistroCNMV"] == "2017-02-07"
    # Las personas: en su papel de accionista, con la marca del volcado.
    personas = {e.caption: e for e in entidades.values() if e.ftm_schema == "Person"}
    assert set(personas) == {
        "KHALID THANI ABDULLAH AL THANI",
        "JOSEPH OUGHOURLIAN",
        "JUAN ADOLFO UTOR MARTÍNEZ",
    }
    for persona in personas.values():
        assert persona.properties["accionista_cnmv"] is True
        assert persona.dedupe_key.startswith("cnmv:persona:")
    # «VIVENDI, S.E.» es una sociedad europea, no una persona.
    assert any(
        e.caption == "VIVENDI, S.E." and e.ftm_schema == "Company" for e in entidades.values()
    )
    # Un fondo que no está en la lista, por su nombre en la CNMV.
    assert any(k.startswith("cnmv:sociedad:amber-capital-uk-llp") for k in entidades)
    # Y el enlace es la página estable de la cotizada, no la de sesión.
    assert santander.properties["url"].endswith(f"ps_ac_ini.aspx?nif={PRISA}")


def test_la_misma_participacion_desde_las_dos_tablas_es_una_arista():
    de_prisa = _raw(
        "prisa-notificaciones-participaciones-aspx.html",
        PRISA,
        "PROMOTORA DE INFORMACIONES, S.A.",
        "accionistas",
    )
    de_santander = _raw(
        "santander-sociedadesparticipa-aspx.html",
        SANTANDER,
        "BANCO SANTANDER, S.A.",
        "participadas",
    )
    a = {x.dedupe_key: x for n in _normalizados(de_prisa) if n for x in n.aristas}
    b = {x.dedupe_key: x for n in _normalizados(de_santander) if n for x in n.aristas}
    comun = set(a) & set(b)
    assert len(comun) == 1
    [clave_comun] = comun
    assert (a[clave_comun].source_key, a[clave_comun].target_key) == (
        b[clave_comun].source_key,
        b[clave_comun].target_key,
    )


def test_una_pagina_de_otra_cotizada_no_se_usa():
    raw = _raw(
        "prisa-notificaciones-participaciones-aspx.html",
        TELEFONICA,
        "TELEFONICA, S.A.",
        "accionistas",
    )
    assert list(CNMVConnector().parse(raw)) == []


def test_la_lista_de_cotizadas():
    semillas = leer_semillas()
    assert TELEFONICA in semillas and PRISA in semillas
    assert all(re.fullmatch(r"[A-Z]\d{8}", s) for s in semillas)
    assert len(semillas) == len(set(semillas))


class _Servidor:
    """La CNMV con las páginas guardadas."""

    def __init__(self) -> None:
        self.peticiones: list[str] = []
        telefonica = _html("telefonica-participaciones.html")
        santander = _html("santander-participaciones.html")
        # Una cotizada cuya página por NIF no trae enlaces: hay que buscarla.
        self.sin_enlaces = re.sub(r'href="[^"]*qS=[^"]*"', 'href="#"', santander)
        self.paginas = {
            f"ps_ac_ini.aspx?nif={TELEFONICA}": telefonica,
            f"ps_ac_ini.aspx?nif={SANTANDER}": self.sin_enlaces,
            "ps_ac_ini.aspx?nif=A00000000": (
                "<title>CNMV - Participaciones Significativas y Autocartera de la entidad</title>"
            ),
        }
        self.buscado = santander

    def __call__(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.peticiones.append(f"{request.method} {url}")
        if request.method == "POST":
            cuerpo = request.content.decode()
            assert "txtDenominacion" in cuerpo and "BANCO+SANTANDER" in cuerpo
            return httpx.Response(200, text=self.buscado)
        if "busqueda.aspx?id=7" in url:
            oculto = '<input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="v" />'
            return httpx.Response(200, text=f"<form>{oculto}</form>")
        if "datosgenerales.aspx?nif=" in url:
            nif = url.rsplit("=", 1)[1]
            empresa = {TELEFONICA: "telefonica", SANTANDER: "santander"}.get(nif)
            if empresa is None:
                return httpx.Response(404)
            return httpx.Response(200, text=_html(f"{empresa}-datosgenerales.html"))
        for clave_url, pagina in self.paginas.items():
            if url.endswith(clave_url):
                return httpx.Response(200, text=pagina)
        # Cada cotizada, por el identificador de sesión de sus enlaces
        # guardados: d5f819df es Telefónica, b6ebcd10 Santander.
        if "Notificaciones-Participaciones" in url:
            empresa = "telefonica" if "d5f819df" in url else "santander"
            return httpx.Response(
                200, text=_html(f"{empresa}-notificaciones-participaciones-aspx.html")
            )
        if "SociedadesParticipa" in url and "b6ebcd10" in url:
            return httpx.Response(200, text=_html("santander-sociedadesparticipa-aspx.html"))
        if "SociedadesParticipa" in url:
            # Telefónica no participa en ninguna: la página no trae tabla.
            return httpx.Response(200, text=_html("telefonica-participaciones.html"))
        return httpx.Response(404)


def test_el_recorrido_entero():
    servidor = _Servidor()
    cliente = httpx.Client(transport=httpx.MockTransport(servidor))
    conector = CNMVConnector(
        cliente=cliente, semillas=[TELEFONICA, SANTANDER, "A00000000"], pausa=0
    )
    todos = list(conector.fetch())
    fichas = [d for d in todos if d.metadata["tabla"] == "datosgenerales"]
    docs = [d for d in todos if d.metadata["tabla"] != "datosgenerales"]
    # Una ficha por cotizada reconocida, y cada una es la de su NIF.
    assert {d.metadata["nif"] for d in fichas} == {TELEFONICA, SANTANDER}
    sectores = {r.data["nif"]: r.data["sector"] for d in fichas for r in conector.parse(d)}
    assert sectores[SANTANDER] == "FINANCIACIÓN Y SEGUROS/BANCOS"
    # Telefónica por su NIF; Santander, por el buscador; la tercera no existe.
    assert any(p.startswith("POST ") for p in servidor.peticiones)
    emisores = {d.metadata["emisor"] for d in docs}
    assert emisores == {"TELEFONICA, S.A.", "BANCO SANTANDER, S.A."}
    assert docs[0].metadata["conocidas"] == {
        "TELEFONICA, S.A.": TELEFONICA,
        "BANCO SANTANDER, S.A.": SANTANDER,
    }
    # Los enlaces relativos del buscador se resuelven en su carpeta.
    assert all("/derechosvoto/" in d.url for d in docs)
    # Y lo que se lee de la tabla de Santander es de Santander.
    tablas = [d for d in docs if d.metadata["emisor"] == "BANCO SANTANDER, S.A."]
    assert {d.metadata["tabla"] for d in tablas} == {"accionistas", "participadas"}


# --- La ficha: el sector según la CNMV ------------------------------------------


@pytest.mark.parametrize(
    ("fichero", "nif", "abreviada", "sector"),
    [
        ("prisa-datosgenerales.html", PRISA, "PRISA", "MEDIOS DE COMUNICACIÓN"),
        (
            "telefonica-datosgenerales.html",
            TELEFONICA,
            "TELEFONICA",
            "TRANSPORTES Y COMUNICACIONES/COMUNICACIONES",
        ),
        (
            "santander-datosgenerales.html",
            SANTANDER,
            "BANCO SANTANDER",
            "FINANCIACIÓN Y SEGUROS/BANCOS",
        ),
    ],
)
def test_la_ficha_de_cada_cotizada(fichero, nif, abreviada, sector):
    ficha = leer_datos_generales(_html(fichero))
    assert ficha is not None
    assert (ficha.nif, ficha.abreviada, ficha.sector) == (nif, abreviada, sector)
    assert len(ficha.lei) == 20


def test_la_prisa_tiene_lei_y_nombre_completo():
    ficha = leer_datos_generales(_html("prisa-datosgenerales.html"))
    assert ficha.lei == "959800U3NGPXSCQHQW54"
    assert ficha.emisor == "PROMOTORA DE INFORMACIONES, S.A."


def test_una_pagina_sin_ficha_no_da_nada():
    assert leer_datos_generales(_html("prisa-notificaciones-participaciones-aspx.html")) is None
    assert leer_datos_generales("") is None


@pytest.mark.parametrize(
    ("sector", "medio"),
    [
        ("MEDIOS DE COMUNICACIÓN", True),
        ("Medios de comunicacion y publicidad", True),
        ("TRANSPORTES Y COMUNICACIONES/COMUNICACIONES", False),
        ("FINANCIACIÓN Y SEGUROS/BANCOS", False),
        ("", False),
    ],
)
def test_que_sector_es_el_de_los_medios(sector, medio):
    assert es_medio_de_comunicacion(sector) is medio


def _ficha(nombre: str, nif: str, emisor: str) -> RawDocument:
    return RawDocument(
        source_id="cnmv",
        url=f"https://www.cnmv.es/x/{nombre}",
        content=(GOLDEN / nombre).read_bytes(),
        media_type="text/html",
        metadata={"nif": nif, "emisor": emisor, "tabla": "datosgenerales"},
    )


def test_la_ficha_normalizada_pone_el_sector_a_la_cotizada():
    [n] = _normalizados(
        _ficha("prisa-datosgenerales.html", PRISA, "PROMOTORA DE INFORMACIONES, S.A.")
    )
    assert n.aristas == [] and n.ficha is True
    [prisa] = n.entidades
    assert prisa.dedupe_key == f"nif:{PRISA}" and prisa.nif == PRISA
    assert prisa.caption == "PROMOTORA DE INFORMACIONES, S.A."
    assert prisa.properties["sectorCNMV"] == "MEDIOS DE COMUNICACIÓN"
    assert prisa.properties["leiCode"] == "959800U3NGPXSCQHQW54"
    assert prisa.properties["cotizada"] is True


def test_una_ficha_de_otro_nif_no_se_usa():
    # La ficha de Prisa servida al pedir la de Telefónica: no le pone sector.
    raw = _ficha("prisa-datosgenerales.html", TELEFONICA, "TELEFONICA, S.A.")
    assert list(CNMVConnector().parse(raw)) == []


# --- El informe anual de gobierno corporativo -----------------------------------


@pytest.mark.parametrize(
    ("empresa", "registro"),
    [("telefonica", "2026028797"), ("prisa", "2026042679"), ("santander", "2026029544")],
)
def test_el_iagc_mas_reciente_sale_de_su_propia_tabla(empresa, registro):
    informes = informes_de_gobierno(_html(f"{empresa}-gobcorp.html"))
    assert informes[0].ejercicio == 2025 and informes[0].registro == registro
    assert informes[0].url.startswith("https://www.cnmv.es/webservices/verdocumento/ver?e=")
    # Y el resto, más viejos, sin repetir.
    ejercicios = [i.ejercicio for i in informes]
    assert ejercicios == sorted(ejercicios, reverse=True)
    assert len({i.url for i in informes}) == len(informes)


def test_sin_la_tabla_del_iagc_no_hay_informes():
    assert informes_de_gobierno(_html("prisa-datosgenerales.html")) == []
    assert informes_de_gobierno("") == []


# --- Las muestras no llevan fechas de nadie ---------------------------------------


def test_ninguna_muestra_del_consejo_lleva_fechas_ni_nacimientos():
    """Las muestras del IAGC salen del runner sin fecha alguna.

    La octava vuelta del reconocimiento dejó pasar los años de nacimiento del
    cuadro propio del BBVA, porque un año no tiene forma de fecha. Esto lo
    comprueba sobre todo lo guardado, venga de la vuelta que venga.
    """
    import json

    for f in [*GOLDEN.glob("*consejo*.json"), *GOLDEN.glob("*dominicales*.json")]:
        texto = f.read_text(encoding="utf-8")
        assert not re.search(r"\b\d{1,2}/\d{1,2}/\d{4}\b", texto), f.name
        datos = json.loads(texto)
        for t in datos.get("tablas", []) if isinstance(datos, dict) else []:
            cabecera = t["filas"][0]
            for j, h in enumerate(cabecera):
                if re.search(r"(?i)nacimiento", h):
                    assert all(
                        fila[j] in ("", "<retirado>") for fila in t["filas"][1:] if j < len(fila)
                    ), f"{f.name}, página {t['pagina']}"
            for fila in t["filas"][1:]:
                assert not any(re.fullmatch(r"(19|20)\d\d", c) for c in fila), f.name
        if "dominicales" in f.name:
            # Aquí, ni un año dentro de un texto: los perfiles los traen.
            assert not re.search(
                r"\b(19|20)\d\d\b", texto.replace(datos.get("ejercicio", ""), "")
            ), f.name


# --- El consejo, del cuadro C.1.2 del IAGC ------------------------------------------


def _tablas(empresa: str) -> list:
    import json

    datos = json.loads((GOLDEN / f"{empresa}-consejo-tablas.json").read_text(encoding="utf-8"))
    return [t["filas"] for t in datos["tablas"]]


def test_el_consejo_de_telefonica_entero_y_sin_los_que_cesaron():
    miembros, descartadas = miembros_del_consejo(_tablas("telefonica"))
    assert len(miembros) == 15 and descartadas == 0
    por_nombre = {m.nombre: m for m in miembros}
    assert por_nombre["MARC THOMAS MURTRA MILLAR"].cargo == "Presidente"
    assert por_nombre["MARC THOMAS MURTRA MILLAR"].categoria == "Ejecutivo"
    # «VICEPRESIDENT» + «E <fecha>»: la E vuelve a su sitio.
    assert por_nombre["CARLOS OCAÑA ORBIS"].cargo == "Vicepresidente"
    assert por_nombre["CARLOS OCAÑA ORBIS"].categoria == "Dominical"
    assert por_nombre["PETER LÖSCHER"].cargo == "Consejero coordinador independiente"
    assert all(m.persona and not m.representante for m in miembros)
    # El cuadro de bajas del ejercicio tiene la misma forma de fila, pero no
    # su cabecera: quien cesó no sale como consejero.
    assert not any("PALLETE" in m.nombre or "VILÁ" in m.nombre for m in miembros)


def test_el_consejo_de_prisa_sin_repetir_y_sin_filas_partidas():
    miembros, descartadas = miembros_del_consejo(_tablas("prisa"))
    nombres = [m.nombre for m in miembros]
    # El cuadro sale dos veces en el informe; cada consejero, una.
    assert len(nombres) == len(set(nombres)) == 13
    # La fila partida entre dos páginas llega sin categoría: se deja, no se
    # recompone un nombre a partir de un trozo (una por cada copia del cuadro).
    assert descartadas == 2
    assert not any(n.startswith("FERNÁNDEZ DE ALARCÓN") for n in nombres)
    assert "BEATRICE DE CLERMONT-TONNERRE" in nombres
    oughourlian = next(m for m in miembros if m.nombre == "JOSEPH OUGHOURLIAN")
    assert (oughourlian.cargo, oughourlian.categoria) == ("Presidente", "Dominical")
    assert {m.cargo for m in miembros} >= {"Vicepresidente 1º", "Vicepresidente 2º"}


@pytest.mark.parametrize(("empresa", "cuantos"), [("santander", 15), ("bbva", 14), ("repsol", 15)])
def test_el_consejo_de_otras_cotizadas(empresa, cuantos):
    miembros, _ = miembros_del_consejo(_tablas(empresa))
    assert len(miembros) == cuantos
    assert sum(1 for m in miembros if m.cargo == "Presidente") == 1


def test_el_cuadro_propio_del_bbva_con_nacimientos_no_se_lee():
    # Su cabecera no es la del modelo: si se leyera, saldrían dos veces.
    tablas = _tablas("bbva")
    propio = next(t for t in tablas if "Año de nacimiento" in t[0])
    assert not es_cuadro_del_consejo(propio[0])
    assert miembros_del_consejo([propio]) == ([], 0)


def test_una_sociedad_consejera_con_su_representante():
    cabecera = [
        "Nombre o denominación social del consejero",
        "Representante",
        "Categoría del consejero",
        "Cargo en el consejo",
        "Fecha primer nombramiento",
        "Fecha último nombramiento",
        "Procedimiento de elección",
    ]
    tabla = [
        cabecera,
        ["CRITERIA CAIXA, S.A.U.", "DON ALGUIEN EJEMPLO", "Dominical", "CONSEJERO", "", "", "X"],
        # Una fila del cuadro de bajas colada: comisiones donde va el cargo.
        ["DON OTRO EJEMPLO", "", "Ejecutivo", "Comisión Delegada", "", "", ""],
    ]
    [sociedad], descartadas = miembros_del_consejo([tabla])
    assert sociedad.persona is False
    assert (sociedad.nombre, sociedad.representante) == (
        "CRITERIA CAIXA, S.A.U.",
        "DON ALGUIEN EJEMPLO",
    )
    assert descartadas == 1


def test_consejeros_fijados_por_la_junta():
    texto = "Número mínimo de consejeros 5 Número de consejeros fijado por la junta 14 C.1.2"
    assert consejeros_fijados(texto) == 14
    assert consejeros_fijados("nada") is None


def test_la_accion_concertada_no_es_un_titular():
    from sinapsis_ingest.cnmv import es_accion_concertada
    from sinapsis_ingest.connectors.base import ParsedRecord

    assert es_accion_concertada("ACCION CONCERTADA")
    assert es_accion_concertada("ACCIÓN  CONCERTADA")
    assert not es_accion_concertada("ACCIONA, S.A.")
    registro = ParsedRecord(
        raw_content_hash="x",
        extractor_version="x",
        data={"titular": "ACCION CONCERTADA", "sociedad": "VOCENTO, S.A.", "conocidas": {}},
    )
    # No se normaliza: como nodo uniría las cotizadas de grupos distintos.
    assert CNMVConnector().normalize(registro) is None


def test_una_lista_de_todos_los_emisores_no_se_toma_por_la_de_uno():
    """Con un parámetro que no reconoce, la CNMV lista los informes de todos.

    La novena vuelta lo trajo pidiendo por el identificador de sesión: cuatro
    cotizadas distintas, la misma lista, que empieza por Abanca y Abengoa.
    """
    for empresa, nif in (("iberdrola", "A48010615"), ("atresmedia", "A78839271")):
        html = _html(f"{empresa}-gobcorp-qs.html")
        assert informes_de_gobierno(html)  # la tabla está…
        assert informes_de_gobierno(html, nif) == []  # …pero no es suya.
    # La de Telefónica sí es de Telefónica, con guion o sin él.
    propia = _html("telefonica-gobcorp.html")
    assert informes_de_gobierno(propia, "A28015865") == informes_de_gobierno(propia)
    assert informes_de_gobierno(propia, "A-28015865") == informes_de_gobierno(propia)


def test_variantes_de_nif():
    from sinapsis_ingest.cnmv import variantes_de_nif

    assert variantes_de_nif("A48010615") == ["A48010615", "A-48010615"]
    assert variantes_de_nif("a-48010615") == ["A48010615", "A-48010615"]


@pytest.mark.parametrize(
    ("cargo", "vale"),
    [
        ("PRESIDENTE-CONSEJERO DELEGADO", True),
        ("PRESIDENTE EJECUTIVO", True),
        ("VICEPRESIDENTE 1º / CONSEJERO DELEGADO", True),
        ("CONSEJERO SECRETARIO", True),
        ("Comisión Delegada / Comisión de Nombramientos", False),
        ("PRESIDENTE-Comisión Delegada", False),
        ("-", False),
    ],
)
def test_cargos_compuestos(cargo, vale):
    cabecera = [
        "Nombre o denominación social del consejero",
        "Representante",
        "Categoría del consejero",
        "Cargo en el consejo",
        "Fecha primer nombramiento",
        "Fecha último nombramiento",
        "Procedimiento de elección",
    ]
    miembros, _ = miembros_del_consejo(
        [[cabecera, ["DON X Y Z", "", "Ejecutivo", cargo, "", "", ""]]]
    )
    assert bool(miembros) is vale
