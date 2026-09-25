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
    propiedades_extranjera,
    slug,
)

log = structlog.get_logger()

SOURCE_ID = "placsp"
EXTRACTOR_VERSION = "placsp/2"  # 2: guarda la jerarquía del órgano y su plataforma

# Los cinco feeds nacionales. El de licitaciones sin menores es el que trae
# los contratos con importe relevante.
FEEDS = {
    "licitaciones": (
        "https://contrataciondelestado.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom"
    ),
    "agregadas": (
        "https://contrataciondelestado.es/sindicacion/sindicacion_1044/PlataformasAgregadasSinMenores.atom"
    ),
    # 1143, no 643: la 643 responde desde septiembre de 2026 con una página
    # de redirección. La buena la da el reconocimiento del 25/9/2026
    # (docs/fuentes/placsp-reconocimiento.md): Atom, actualizado a diario.
    "menores": (
        "https://contrataciondelestado.es/sindicacion/sindicacion_1143/contratosMenoresPerfilesContratantes.atom"
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


def _props_organo(organo: str, d: dict[str, Any]) -> dict[str, Any]:
    """Propiedades del órgano de contratación: nombre, jerarquía y plataforma.

    La jerarquía y la dirección de su perfil de contratante son lo que dice
    la fuente de dónde cuelga el órgano. De ahí sale al volcar su nivel y su
    territorio (`territorio.py`); aquí sólo se guarda lo publicado.
    """
    props: dict[str, Any] = {"name": organo}
    if d.get("jerarquia"):
        props["jerarquia_placsp"] = list(d["jerarquia"])
    if d.get("perfil_contratante"):
        props["perfil_contratante"] = d["perfil_contratante"]
    return props


def _jerarquia(organo: ET.Element | None) -> list[str]:
    """La cadena de organismos padre, de lo general a lo concreto.

    CODICE anida un `ParentLocatedParty` dentro de otro: el del órgano es su
    padre inmediato, el de dentro es el abuelo, y así. El parser sólo leía el
    primero —«Entitats municipals de Catalunya»—, que dice que es municipal
    pero no siempre dónde. Se lee entera y se da la vuelta, para que empiece
    por lo más general. Los eslabones vacíos —la fuente cierra la cadena con
    un `ParentLocatedParty` sin nombre— no cuentan.
    """
    cadena: list[str] = []
    nodo = organo.find("cac-place-ext:ParentLocatedParty", NS) if organo is not None else None
    while nodo is not None and len(cadena) < 12:
        nombre = _texto(nodo, "cac:PartyName/cbc:Name")
        if nombre:
            cadena.append(nombre)
        nodo = nodo.find("cac-place-ext:ParentLocatedParty", NS)
    return list(reversed(cadena))


def _atributo(nodo: ET.Element | None, ruta: str, attr: str) -> str:
    if nodo is None:
        return ""
    hijo = nodo.find(ruta, NS)
    if hijo is None:
        return ""
    return (hijo.get(attr) or "").strip()


# El importe adjudicado no puede superar al presupuesto base de licitación más
# que por un margen pequeño: la ley lo prohíbe, y en los datos se ve —el 99,5 %
# de las adjudicaciones ingeridas está en 1,07 veces el presupuesto o por
# debajo—. Lo que hay por encima no son contratos caros, son erratas del
# formulario de origen.
#
# El caso que obligó a poner esto: un servicio de transporte para una
# exposición temporal, con un presupuesto de 22.000 €, publicado con un importe
# adjudicado de 1.954.023.643,40 € — 88.819 veces. Esa sola cifra era el 8 % de
# todo el dinero del mapa y ponía a la empresa adjudicataria en cabeza del
# ranking de quien más cobra del Estado, con dos mil millones de euros. Publicar
# eso es una acusación falsa, y da igual que el número venga de la fuente.
#
# El umbral es deliberadamente flojo —diez veces— para no tocar lo que puede
# tener una explicación legítima: IVA, lotes contados de distinta manera,
# prórrogas o un presupuesto anualizado frente a un importe por todo el plazo.
# A diez veces ya no queda ninguna de esas explicaciones.
#
# No se descarta la adjudicación: la adjudicación ocurrió y el adjudicatario es
# real. Lo que no se publica es LA CIFRA. Se deja en `amount` vacío, el valor
# original queda en las propiedades para quien quiera comprobarlo, y la
# confianza baja. Es el mismo trato que reciben en el conector del Tribunal de
# Cuentas las cuantías que no se pueden interpretar.
VECES_PRESUPUESTO_INVEROSIMIL = 10


def _importes_compartidos(adjudicaciones: list[dict[str, Any]]) -> dict[Any, int]:
    """Importes que se repiten entre adjudicatarios del MISMO contrato.

    En un acuerdo marco o un sistema dinámico de adquisición, PLACSP publica el
    valor del acuerdo —o del lote— en el resultado de CADA adjudicatario
    admitido. No es lo que va a cobrar cada uno: es el techo de gasto del
    marco, dentro del cual después compiten por los pedidos concretos.

    Sumarlo por adjudicatario multiplica el dinero por el número de empresas
    admitidas. En la instantánea del 18/9/2026 un solo acuerdo marco de
    servicios informáticos, con 20 adjudicatarios a 900.000.000 € cada uno,
    aportaba 18.000 millones: el 85 % del dinero de todo el mapa. Y la lectura
    que salía en la web era «INDRA recibió 908 millones de euros de este
    organismo», que es falsa.

    En total, el 90,5 % del dinero de las adjudicaciones venía de importes
    repetidos así.

    Basta con que se repita DOS veces. Podría ser la coincidencia de dos lotes
    de idéntico valor adjudicados a empresas distintas, pero desde fuera no hay
    manera de distinguir ese caso del acuerdo marco, y exigir tres o cinco
    repeticiones sólo rescata un 0,3 % del dinero. No merece la pena comprar
    ese 0,3 % al precio de publicar cifras falsas.
    """
    cuenta: dict[Any, int] = {}
    for adj in adjudicaciones:
        importe = adj.get("importe")
        if importe is None:
            continue
        cuenta[importe] = cuenta.get(importe, 0) + 1
    return {imp: n for imp, n in cuenta.items() if n > 1}


def _importe_inverosimil(importe: Any, presupuesto: Any) -> bool:
    """¿El importe adjudicado es imposible frente al presupuesto del contrato?"""
    if importe is None or presupuesto is None:
        return False
    try:
        if presupuesto <= 0:
            return False
        return importe > presupuesto * VECES_PRESUPUESTO_INVEROSIMIL
    except TypeError:
        return False


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
        # Un HTML donde debería haber un ATOM no es «XML inválido»: es que esa
        # ruta ya no sirve el feed. La Plataforma responde con una página de
        # redirección al portal —«Redireccionando… Se ha producido un error»—
        # y un 200, así que no lo caza ni `raise_for_status` ni el parser, que
        # sólo dice que la etiqueta no cuadra.
        #
        # Pasó con el feed de contratos menores el 18/9/2026. Con el mensaje
        # genérico había que abrir el documento crudo para entenderlo; dicho
        # así, se arregla mirando la especificación de sindicación.
        if raw.content[:200].lstrip()[:5].lower() == b"<html" or (raw.media_type or "").startswith(
            "text/html"
        ):
            log.error(
                "placsp: la ruta no sirve el feed, devuelve una página HTML",
                url=raw.url,
                content_type=raw.media_type,
                bytes=len(raw.content),
                pista=(
                    "la ruta del feed ha cambiado o ya no existe;"
                    " comprobar contra la especificación de sindicación"
                ),
            )
            return

        try:
            raiz = ET.fromstring(raw.content)
        except ET.ParseError as exc:
            # El error de `ExpatError` dice dónde falla, no QUÉ llegó, y eso no
            # basta para diagnosticar. El feed de contratos menores devolvió
            # «mismatched tag: line 1, column 200» el 18/9/2026 y con eso no se
            # puede saber si el servidor sirvió un HTML de error, otro formato,
            # o un ATOM de verdad con una etiqueta rota.
            #
            # El documento crudo queda guardado en `raw_documents` —es la
            # prueba— pero el log es lo que se lee. Así que va un trozo del
            # principio, que es donde está la cabecera que lo identifica.
            cabeza = raw.content[:300].decode("utf-8", errors="replace").replace("\n", " ")
            log.warning(
                "placsp: XML inválido",
                error=str(exc),
                url=raw.url,
                bytes=len(raw.content),
                content_type=raw.media_type,
                empieza_por=cabeza,
            )
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
            "jerarquia": _jerarquia(organo),
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

        compartidos = _importes_compartidos(adjudicaciones)

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
                properties=_props_organo(organo, d),
            ),
            EntidadNormalizada(
                ftm_schema="Contract",
                caption=(d.get("titulo") or d.get("expediente") or clave_contrato)[:500],
                dedupe_key=clave_contrato,
                country="es",
                properties=props_contrato,
            ),
        ]

        # El órgano de contratación tiene que quedar ENLAZADO con su contrato.
        # Sin esta arista el organismo era una entidad suelta: existía en el
        # grafo pero no colgaba de nada, y los contratos flotaban sujetos sólo
        # a su adjudicatario. El resultado eran 1.393 componentes conexas y
        # ningún núcleo visible — nadie podía ver qué organismo adjudicó qué.
        #
        # FollowTheMoney no tiene arista propia para esto: `Contract.authority`
        # es una *propiedad*, y `Contract` es una entidad, no una arista. La vía
        # canónica en FtM para "están relacionados y la naturaleza va aparte" es
        # `UnknownLink` con `role`, que es lo que se usa aquí.
        #
        # Sin importe a propósito: el dinero ya lo lleva el ContractAward y
        # ponerlo también aquí lo contaría dos veces.
        aristas: list[AristaNormalizada] = [
            AristaNormalizada(
                ftm_schema="UnknownLink",
                source_key=clave_organo,
                target_key=clave_contrato,
                dedupe_key=f"placsp:organo-contrato:{d['entry_id']}",
                status="asserted",
                confidence=1.0,
                properties={"role": "órgano de contratación"},
            )
        ]
        vistos: set[str] = set()
        for orden, adj in enumerate(adjudicaciones):
            nif = adj.get("nif") or ""
            nombre = adj["nombre"]
            clave_adj = f"nif:{nif}" if nif else f"placsp:adjudicatario:{slug(nombre)}"

            # Igual que en BDNS: se conserva el hecho —este órgano adjudicó
            # este contrato por este importe— y se sustituye la identidad por
            # una etiqueta. PLACSP, a diferencia de BDNS, no enmascara el NIF
            # del autónomo, así que aquí el aviso de que hay un particular lo
            # da el propio formato del identificador.
            #
            # Se descubrió mirando la instantánea publicada: 25 personas
            # físicas con nombre y apellidos en un mapa de influencia
            # política. Ver spec §12.
            es_particular = parece_persona_fisica(nif, nombre)
            if es_particular:
                clave_adj = f"placsp:particulares:{d['entry_id']}"

            if clave_adj not in vistos:
                vistos.add(clave_adj)
                if es_particular:
                    entidades.append(
                        EntidadNormalizada(
                            ftm_schema="LegalEntity",
                            caption="Personas físicas (adjudicatarias)",
                            dedupe_key=clave_adj,
                            country="es",
                            properties={
                                "agregado": True,
                                "motivo": "minimización de datos personales (RGPD)",
                            },
                        )
                    )
                else:
                    entidades.append(
                        EntidadNormalizada(
                            ftm_schema="LegalEntity" if not nif else "Company",
                            caption=nombre,
                            dedupe_key=clave_adj,
                            nif=nif,
                            country="es",
                            properties={"name": nombre, **propiedades_extranjera(nif, nombre)},
                        )
                    )

            importe = adj.get("importe")
            props_adj: dict[str, Any] = {
                k: v
                for k, v in (
                    ("cpvCode", d.get("cpv")),
                    ("nutsCode", d.get("nuts")),
                    # `resultCode`, no `lotNumber`. Se publicó como número de
                    # lote y no lo es: el propio documento lo dice en el
                    # atributo del elemento,
                    # `listURI=".../TenderResultCode-2.02.gc"`. Es el código de
                    # resultado de la adjudicación.
                    #
                    # Se notaba en los datos sin abrir el XML: 1.860
                    # adjudicaciones publicadas y sólo DOS valores distintos de
                    # «lote», 8 y 9. Ningún expediente real se lotea así.
                    #
                    # El código va en crudo y sin traducir. La lista de
                    # valores es de CODICE y no la he podido comprobar contra
                    # la especificación —el proxy de este entorno deniega
                    # contrataciondelestado.es—, así que poner «adjudicado» o
                    # «formalizado» sería inventarme el significado de un dato
                    # público. La lista está citada en docs/data-sources.md.
                    ("resultCode", adj.get("codigo_resultado")),
                )
                if v
            }
            confianza = 1.0 if nif else 0.7

            veces = compartidos.get(importe, 0)
            if veces > 1:
                # No se descarta la adjudicación —el adjudicatario entró en el
                # marco, y eso es el dato— sino la atribución de la cifra a él.
                props_adj["importeCompartido"] = str(importe)
                props_adj["adjudicatariosQueComparten"] = veces
                props_adj["motivoImporteDudoso"] = (
                    f"el mismo importe figura en {veces} adjudicaciones de este contrato:"
                    " es el valor del acuerdo marco o del lote, no lo que recibe cada"
                    " adjudicatario"
                )
                importe = None
                confianza = min(confianza, 0.5)

            if _importe_inverosimil(importe, d.get("presupuesto")):
                log.warning(
                    "placsp: importe inverosímil frente al presupuesto; no se publica la cifra",
                    entry_id=d["entry_id"],
                    importe=str(importe),
                    presupuesto=str(d.get("presupuesto")),
                )
                props_adj["importeSinInterpretar"] = str(importe)
                props_adj["motivoImporteDudoso"] = (
                    f"supera en más de {VECES_PRESUPUESTO_INVEROSIMIL} veces el presupuesto"
                    f" base de licitación ({d.get('presupuesto')})"
                )
                importe = None
                confianza = min(confianza, 0.5)

            aristas.append(
                AristaNormalizada(
                    ftm_schema="ContractAward",
                    source_key=clave_contrato,
                    target_key=clave_adj,
                    # Única por (contrato, adjudicatario): un contrato con
                    # varios lotes al mismo proveedor no debe duplicarse.
                    #
                    # Salvo con particulares, donde el nodo destino es un
                    # agregado compartido: dos autónomos adjudicatarios del
                    # mismo contrato colapsarían en una sola arista y se
                    # perdería uno de los dos importes. El ordinal dentro del
                    # documento los mantiene separados sin identificarlos, y
                    # es estable al reingerir el mismo documento.
                    dedupe_key=(
                        f"placsp:adjudicacion:{d['entry_id']}:{clave_adj}:{orden}"
                        if es_particular
                        else f"placsp:adjudicacion:{d['entry_id']}:{clave_adj}"
                    ),
                    amount=importe,
                    currency=adj.get("moneda") or ("EUR" if importe is not None else ""),
                    start_date=d.get("actualizado"),
                    status="asserted",
                    confidence=confianza,
                    properties=props_adj,
                )
            )

        return Normalizado(entidades=entidades, aristas=aristas)


class PLACSPLicitacionesConnector(PLACSPConnector):
    """El feed principal de la Plataforma, el que publican los perfiles del Estado.

    `agregadas` —el único que se ingería hasta ahora— trae lo que vuelcan las
    plataformas autonómicas agregadas. Todo lo que se publica directamente en
    la Plataforma del Sector Público estaba fuera del mapa.
    """

    def fetch(self, **kw: Any) -> Iterator[RawDocument]:
        kw.setdefault("feed", "licitaciones")
        return super().fetch(**kw)


class PLACSPMenoresConnector(PLACSPConnector):
    """Contratos menores.

    Es donde vive el gasto municipal del día a día: por debajo del umbral del
    contrato menor no hay licitación pública, y eso hace que sea justo el
    tramo que menos se mira y el que más aparece cuando alguien pregunta por su
    propio ayuntamiento.

    Trae muchos adjudicatarios que son personas físicas —autónomos—, y ahí
    manda la regla de siempre: se agregan en un nodo anónimo y no se publica ni
    un nombre. Ver `docs/spec.md` §12.
    """

    def fetch(self, **kw: Any) -> Iterator[RawDocument]:
        kw.setdefault("feed", "menores")
        return super().fetch(**kw)


def crear() -> PLACSPConnector:
    """Fábrica para el registro de conectores."""
    return PLACSPConnector()


def crear_licitaciones() -> PLACSPLicitacionesConnector:
    return PLACSPLicitacionesConnector()


def crear_menores() -> PLACSPMenoresConnector:
    return PLACSPMenoresConnector()
