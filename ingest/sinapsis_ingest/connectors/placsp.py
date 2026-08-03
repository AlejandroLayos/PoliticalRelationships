"""Conector de la Plataforma de Contratación del Sector Público (PLACSP).

Ingiere licitaciones y adjudicaciones y las convierte al modelo canónico de
FollowTheMoney para contratación:

    Contract (el expediente) --ContractAward--> adjudicatario (Company | Person)

**PLACSP no tiene API REST.** Publica por sindicación ATOM: ficheros `.atom`
encadenados por `link rel="next"`, cada uno con hasta 500 entradas, y el
contenido de cada entrada en CODICE (perfil español de UBL de OASIS). Los
`href` del encadenado son **relativos** al fichero que los contiene.

Ojo con la dirección del encadenado: `rel="next"` apunta al fichero
*anterior en el tiempo*, así que recorrerlo va hacia atrás en la historia.

Rutas verificadas contra una respuesta real (ver `tests/golden/README.md`).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import httpx
import structlog

from sinapsis_ingest.connectors.base import ParsedRecord, RawDocument
from sinapsis_ingest.normalizado import (
    AristaNormalizada,
    EntidadNormalizada,
    Normalizado,
)
from sinapsis_ingest.util import (
    a_decimal,
    a_fecha,
    normalizar_nif,
    parece_persona_fisica,
    slug,
)

log = structlog.get_logger()

SOURCE_ID = "placsp"
EXTRACTOR_VERSION = "placsp/1"

# Los cinco feeds nacionales. El de licitaciones sin menores es el que trae
# los contratos con importe relevante.
FEEDS = {
    "licitaciones": (
        "https://contrataciondelestado.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom"
    ),
    "agregadas": (
        "https://contrataciondelestado.es/sindicacion/sindicacion_1044/PlataformasAgregadasSinMenores.atom"
    ),
    "menores": (
        "https://contrataciondelestado.es/sindicacion/sindicacion_643/contratosMenoresPerfilesContratantes.atom"
    ),
}

# Los prefijos de namespace varían entre versiones de CODICE, pero las URI no.
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "cac": "urn:dgpe:names:draft:codice:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2",
    "cac-place-ext": (
        "urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonAggregateComponents-2"
    ),
    "cbc-place-ext": ("urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonBasicComponents-2"),
}

PETICIONES_POR_SEGUNDO = 2.0


def _texto(nodo: ET.Element | None, ruta: str) -> str:
    """Texto de un subelemento, o "" si no está."""
    if nodo is None:
        return ""
    hijo = nodo.find(ruta, NS)
    if hijo is None or hijo.text is None:
        return ""
    return hijo.text.strip()


def _atributo(nodo: ET.Element | None, ruta: str, attr: str) -> str:
    if nodo is None:
        return ""
    hijo = nodo.find(ruta, NS)
    if hijo is None:
        return ""
    return (hijo.get(attr) or "").strip()


class PLACSPConnector:
    """Conector de contratación pública."""

    source_id = SOURCE_ID
    extractor_version = EXTRACTOR_VERSION

    def __init__(
        self,
        cliente: httpx.Client | None = None,
        peticiones_por_segundo: float = PETICIONES_POR_SEGUNDO,
    ):
        self._cliente = cliente
        self._intervalo = 1.0 / peticiones_por_segundo if peticiones_por_segundo > 0 else 0.0
        self._ultima_peticion = 0.0

    # --- fetch ------------------------------------------------------------

    def _esperar_turno(self) -> None:
        if self._intervalo <= 0:
            return
        import time

        transcurrido = time.monotonic() - self._ultima_peticion
        if transcurrido < self._intervalo:
            time.sleep(self._intervalo - transcurrido)
        self._ultima_peticion = time.monotonic()

    def fetch(
        self,
        *,
        feed: str = "agregadas",
        url: str | None = None,
        max_paginas: int | None = 1,
        **_: Any,
    ) -> Iterator[RawDocument]:
        """Descarga ficheros ATOM siguiendo el encadenado `rel="next"`.

        Cada fichero se guarda entero y sin interpretar: es la prueba.
        """
        actual = url or FEEDS.get(feed)
        if not actual:
            raise ValueError(f"feed desconocido: {feed!r}. Conocidos: {', '.join(FEEDS)}")

        cliente = self._cliente or httpx.Client(timeout=120.0, follow_redirects=True)
        cerrar = self._cliente is None

        try:
            descargados = 0
            while actual and (max_paginas is None or descargados < max_paginas):
                self._esperar_turno()
                try:
                    resp = cliente.get(actual)
                    resp.raise_for_status()
                except httpx.HTTPError as exc:
                    # No inventamos datos: se registra el hueco y se para.
                    log.warning("placsp: fallo al descargar", url=actual, error=str(exc))
                    break

                contenido = resp.content
                yield RawDocument(
                    source_id=SOURCE_ID,
                    url=str(resp.url),
                    content=contenido,
                    media_type=resp.headers.get("content-type", "application/atom+xml"),
                    retrieved_at=datetime.now(UTC),
                    metadata={"feed": feed, "orden": descargados},
                )
                descargados += 1

                siguiente = self._siguiente(contenido, str(resp.url))
                if not siguiente:
                    break
                actual = siguiente
        finally:
            if cerrar:
                cliente.close()

    @staticmethod
    def _siguiente(contenido: bytes, url_base: str) -> str | None:
        """Resuelve el `link rel="next"`, que viene como href relativo."""
        try:
            raiz = ET.fromstring(contenido)
        except ET.ParseError:
            return None
        for link in raiz.findall("atom:link", NS):
            if link.get("rel") == "next":
                href = link.get("href")
                return urljoin(url_base, href) if href else None
        return None

    # --- parse ------------------------------------------------------------

    def parse(self, raw: RawDocument) -> Iterator[ParsedRecord]:
        """Extrae un registro por cada `<entry>` del feed."""
        try:
            raiz = ET.fromstring(raw.content)
        except ET.ParseError as exc:
            log.warning("placsp: XML inválido", error=str(exc), url=raw.url)
            return

        for entry in raiz.findall("atom:entry", NS):
            datos = self._leer_entry(entry)
            if datos is None:
                continue
            yield ParsedRecord(
                raw_content_hash=raw.content_hash,
                extractor_version=EXTRACTOR_VERSION,
                data=datos,
            )

    def _leer_entry(self, entry: ET.Element) -> dict[str, Any] | None:
        # El id del entry es una URI global; el ContractFolderID es sólo el
        # número de expediente interno del órgano y NO es único entre órganos.
        entry_id = _texto(entry, "atom:id")
        if not entry_id:
            log.warning("placsp: entry sin id; se omite")
            return None

        cfs = entry.find("cac-place-ext:ContractFolderStatus", NS)
        if cfs is None:
            return None

        proyecto = cfs.find("cac:ProcurementProject", NS)
        organo = cfs.find("cac-place-ext:LocatedContractingParty", NS)

        adjudicaciones: list[dict[str, Any]] = []
        for resultado in cfs.findall("cac:TenderResult", NS):
            importe = a_decimal(
                _texto(
                    resultado,
                    "cac:AwardedTenderedProject/cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount",
                )
            )
            moneda = _atributo(
                resultado,
                "cac:AwardedTenderedProject/cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount",
                "currencyID",
            )
            # Un contrato puede tener varios adjudicatarios: lotes o UTE.
            # Quedarnos con el primero perdería adjudicatarios reales.
            for ganador in resultado.findall("cac:WinningParty", NS):
                nombre = _texto(ganador, "cac:PartyName/cbc:Name")
                if not nombre:
                    continue
                adjudicaciones.append(
                    {
                        "nombre": nombre,
                        "nif": normalizar_nif(_texto(ganador, "cac:PartyIdentification/cbc:ID")),
                        "importe": importe,
                        "moneda": moneda or ("EUR" if importe is not None else ""),
                        "codigo_resultado": _texto(resultado, "cbc:ResultCode"),
                    }
                )

        return {
            "id_registro": entry_id,
            "entry_id": entry_id,
            "titulo": _texto(entry, "atom:title") or _texto(proyecto, "cbc:Name"),
            "actualizado": a_fecha(_texto(entry, "atom:updated")),
            "enlace": _atributo(entry, "atom:link", "href"),
            "expediente": _texto(cfs, "cbc:ContractFolderID"),
            "estado": _texto(cfs, "cbc-place-ext:ContractFolderStatusCode"),
            "organo": _texto(organo, "cac:Party/cac:PartyName/cbc:Name"),
            "organo_padre": _texto(
                organo, "cac-place-ext:ParentLocatedParty/cac:PartyName/cbc:Name"
            ),
            "perfil_contratante": _texto(organo, "cbc:BuyerProfileURIID"),
            "tipo_contrato": _texto(proyecto, "cbc:TypeCode"),
            "presupuesto": a_decimal(_texto(proyecto, "cac:BudgetAmount/cbc:TaxExclusiveAmount")),
            "cpv": _texto(
                proyecto,
                "cac:RequiredCommodityClassification/cbc:ItemClassificationCode",
            ),
            "nuts": _texto(proyecto, "cac:RealizedLocation/cbc:CountrySubentityCode"),
            "procedimiento": _texto(cfs, "cac:TenderingProcess/cbc:ProcedureCode"),
            "adjudicaciones": adjudicaciones,
        }

    # --- normalize --------------------------------------------------------

    def normalize(self, record: ParsedRecord) -> Normalizado | None:
        d = record.data

        organo = (d.get("organo") or "").strip()
        adjudicaciones = d.get("adjudicaciones") or []
        # Sin órgano o sin adjudicatario no hay arista que afirmar. Una
        # licitación aún no adjudicada es un hueco legítimo, no un error.
        if not organo or not adjudicaciones:
            return None

        clave_organo = f"placsp:organo:{slug(organo)}"
        clave_contrato = f"placsp:contrato:{d['entry_id']}"

        props_contrato: dict[str, Any] = {"authority": clave_organo}
        for origen, destino in (
            ("expediente", "procedureNumber"),
            ("procedimiento", "procedure"),
            ("estado", "status"),
            ("cpv", "cpvCode"),
            ("nuts", "nutsCode"),
            ("enlace", "sourceUrl"),
            ("tipo_contrato", "type"),
        ):
            if d.get(origen):
                props_contrato[destino] = d[origen]
        if d.get("presupuesto") is not None:
            props_contrato["budgetAmount"] = str(d["presupuesto"])

        entidades = [
            EntidadNormalizada(
                ftm_schema="PublicBody",
                caption=organo,
                dedupe_key=clave_organo,
                country="es",
                properties={"name": organo},
            ),
            EntidadNormalizada(
                ftm_schema="Contract",
                caption=(d.get("titulo") or d.get("expediente") or clave_contrato)[:500],
                dedupe_key=clave_contrato,
                country="es",
                properties=props_contrato,
            ),
        ]

        aristas: list[AristaNormalizada] = []
        vistos: set[str] = set()
        for adj in adjudicaciones:
            nif = adj.get("nif") or ""
            nombre = adj["nombre"]
            clave_adj = f"nif:{nif}" if nif else f"placsp:adjudicatario:{slug(nombre)}"

            if clave_adj not in vistos:
                vistos.add(clave_adj)
                if not nif:
                    esquema = "LegalEntity"
                elif parece_persona_fisica(nif):
                    esquema = "Person"
                else:
                    esquema = "Company"
                entidades.append(
                    EntidadNormalizada(
                        ftm_schema=esquema,
                        caption=nombre,
                        dedupe_key=clave_adj,
                        nif=nif,
                        country="es",
                        properties={"name": nombre},
                    )
                )

            importe = adj.get("importe")
            aristas.append(
                AristaNormalizada(
                    ftm_schema="ContractAward",
                    source_key=clave_contrato,
                    target_key=clave_adj,
                    # Única por (contrato, adjudicatario): un contrato con
                    # varios lotes al mismo proveedor no debe duplicarse.
                    dedupe_key=f"placsp:adjudicacion:{d['entry_id']}:{clave_adj}",
                    amount=importe,
                    currency=adj.get("moneda") or ("EUR" if importe is not None else ""),
                    start_date=d.get("actualizado"),
                    status="asserted",
                    confidence=1.0 if nif else 0.7,
                    properties={
                        k: v
                        for k, v in (
                            ("cpvCode", d.get("cpv")),
                            ("nutsCode", d.get("nuts")),
                            ("lotNumber", adj.get("codigo_resultado")),
                        )
                        if v
                    },
                )
            )

        return Normalizado(entidades=entidades, aristas=aristas)


def crear() -> PLACSPConnector:
    """Fábrica para el registro de conectores."""
    return PLACSPConnector()
