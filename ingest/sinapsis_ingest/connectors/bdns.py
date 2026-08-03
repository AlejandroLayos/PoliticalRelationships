"""Conector de la Base de Datos Nacional de Subvenciones (BDNS).

Ingiere **concesiones** —subvenciones efectivamente otorgadas— y las convierte
en aristas `Payment` del organismo concedente al beneficiario.

    organismo (PublicBody) --Payment--> beneficiario (Company | Person)

Endpoint y parámetros verificados contra `bdns-fetch` (GPLv3), la librería de
referencia citada en docs/data-sources.md §1. La respuesta es una página estilo
Spring: `{"content": [...], "totalPages": N, "number": p}`.

Límite real de la API: **10 peticiones GET por segundo y por IP**, y
`pageSize` máximo 10.000.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from datetime import UTC, date, datetime
from typing import Any

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

SOURCE_ID = "bdns"
BASE_URL = "https://www.infosubvenciones.es/bdnstrans/api"
ENDPOINT_CONCESIONES = f"{BASE_URL}/concesiones/busqueda"
ENDPOINT_PARTIDOS = f"{BASE_URL}/partidospoliticos/busqueda"

# Súbelo sólo con un motivo: al cambiar, todo lo derivado se recomputa desde el
# crudo ya guardado. Formato "<fuente>/<n>".
EXTRACTOR_VERSION = "bdns/1"

# La API admite hasta 10.000, pero páginas así de grandes producen documentos
# crudos enormes y difíciles de reprocesar. 1.000 es un equilibrio razonable.
PAGE_SIZE = 1000

# 10 GET/s por IP es el límite de la API. Vamos deliberadamente por debajo: es
# un servicio público y no hay ninguna prisa.
PETICIONES_POR_SEGUNDO = 4.0


class BDNSConnector:
    """Conector de concesiones de BDNS.

    Es también la base de los demás conjuntos de BDNS: todos comparten
    endpoint con la misma forma (paginación Spring, fechas dd/mm/aaaa) y los
    mismos campos por registro. Las subclases sólo cambian el endpoint y
    cómo se clasifica al beneficiario.
    """

    source_id = SOURCE_ID
    extractor_version = EXTRACTOR_VERSION
    endpoint = ENDPOINT_CONCESIONES

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
        transcurrido = time.monotonic() - self._ultima_peticion
        if transcurrido < self._intervalo:
            time.sleep(self._intervalo - transcurrido)
        self._ultima_peticion = time.monotonic()

    def fetch(
        self,
        *,
        fecha_desde: date,
        fecha_hasta: date,
        page_size: int = PAGE_SIZE,
        max_paginas: int | None = None,
        **_: Any,
    ) -> Iterator[RawDocument]:
        """Descarga concesiones paginando. Cada página es un RawDocument.

        Guardamos la página entera sin interpretar: es la prueba, y BDNS
        despublica registros pasado su plazo legal.
        """
        cliente = self._cliente or httpx.Client(timeout=30.0)
        cerrar = self._cliente is None

        params_base = {
            "pageSize": page_size,
            "fechaDesde": fecha_desde.strftime("%d/%m/%Y"),
            "fechaHasta": fecha_hasta.strftime("%d/%m/%Y"),
        }

        try:
            pagina = 0
            total_paginas: int | None = None

            while True:
                if max_paginas is not None and pagina >= max_paginas:
                    break

                params = {**params_base, "page": pagina}
                self._esperar_turno()

                try:
                    resp = cliente.get(self.endpoint, params=params)
                    resp.raise_for_status()
                except httpx.HTTPError as exc:
                    # No inventamos datos: se registra el hueco y se sigue.
                    log.warning(
                        "bdns: fallo al descargar página",
                        pagina=pagina,
                        error=str(exc),
                    )
                    break

                contenido = resp.content
                yield RawDocument(
                    source_id=SOURCE_ID,
                    url=str(resp.url),
                    content=contenido,
                    media_type=resp.headers.get("content-type", "application/json"),
                    retrieved_at=datetime.now(UTC),
                    metadata={
                        "pagina": pagina,
                        "page_size": page_size,
                        "fecha_desde": params_base["fechaDesde"],
                        "fecha_hasta": params_base["fechaHasta"],
                    },
                )

                if total_paginas is None:
                    try:
                        total_paginas = int(json.loads(contenido).get("totalPages", 1))
                    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
                        log.warning("bdns: no pude leer totalPages; paro tras esta página")
                        break

                pagina += 1
                if pagina >= total_paginas:
                    break
        finally:
            if cerrar:
                cliente.close()

    # --- parse ------------------------------------------------------------

    def parse(self, raw: RawDocument) -> Iterator[ParsedRecord]:
        """Extrae concesiones del crudo.

        Función pura de (bytes, extractor_version): es lo que da sentido a los
        golden tests y lo que permite recomputar sin volver a la fuente.
        """
        try:
            datos = json.loads(raw.content)
        except json.JSONDecodeError as exc:
            log.warning("bdns: la página no es JSON válido", error=str(exc), url=raw.url)
            return

        registros = datos.get("content") if isinstance(datos, dict) else datos
        if not isinstance(registros, list):
            log.warning("bdns: la respuesta no trae lista de concesiones", url=raw.url)
            return

        for item in registros:
            if not isinstance(item, dict):
                continue
            cod = item.get("codConcesion") or item.get("id")
            if cod is None:
                # Sin identificador no hay clave de idempotencia posible.
                log.warning("bdns: concesión sin codConcesion; se omite")
                continue

            yield ParsedRecord(
                raw_content_hash=raw.content_hash,
                extractor_version=EXTRACTOR_VERSION,
                data={
                    "cod_concesion": str(cod),
                    "id_registro": f"bdns:{cod}",
                    "numero_convocatoria": item.get("numeroConvocatoria"),
                    "convocatoria": item.get("convocatoria"),
                    "organo": self._nombre_organo(item),
                    **self._partir_beneficiario(item),
                    "importe": a_decimal(item.get("importe")),
                    "ayuda_equivalente": a_decimal(item.get("ayudaEquivalente")),
                    "fecha_concesion": a_fecha(item.get("fechaConcesion")),
                    "instrumento": item.get("instrumento"),
                    "url_bases_reguladoras": item.get("urlBR"),
                },
            )

    @staticmethod
    def _partir_beneficiario(item: dict[str, Any]) -> dict[str, Any]:
        """Separa el NIF del nombre dentro del campo `beneficiario`.

        BDNS **no** devuelve el NIF en un campo aparte —`nifCif` sólo existe
        como parámetro de búsqueda—. Lo concatena delante del nombre:

            "A10984433 BRITISH ROBERTSON, S.A."
            "***9282** DARIO SANCHEZ ESTORNELL"

        Y ahí está lo importante: **los NIF de personas físicas van
        enmascarados** con asteriscos, mientras que los de personas jurídicas
        van completos. Ese enmascarado es la propia fuente diciendo que ese
        beneficiario es un particular, y lo tratamos como tal (spec §12).
        """
        crudo = (item.get("beneficiario") or "").strip()
        if not crudo:
            return {"beneficiario": "", "nif_beneficiario": "", "es_persona_fisica": False}

        primero, _, resto = crudo.partition(" ")
        nombre = resto.strip() or crudo

        # NIF enmascarado: la fuente lo anonimiza porque es una persona física.
        if "*" in primero and len(primero) >= 6:
            return {"beneficiario": nombre, "nif_beneficiario": "", "es_persona_fisica": True}

        nif = normalizar_nif(primero)
        if nif:
            return {
                "beneficiario": nombre,
                "nif_beneficiario": nif,
                "es_persona_fisica": parece_persona_fisica(nif),
            }

        # Sin NIF reconocible: el campo entero es el nombre.
        return {"beneficiario": crudo, "nif_beneficiario": "", "es_persona_fisica": False}

    @staticmethod
    def _nombre_organo(item: dict[str, Any]) -> str:
        """Reconstruye el órgano concedente desde la jerarquía nivel1/2/3.

        BDNS publica el organismo en tres niveles administrativos; el más
        específico que exista es el que concede.
        """
        niveles = [item.get("nivel3"), item.get("nivel2"), item.get("nivel1")]
        for nivel in niveles:
            if nivel and str(nivel).strip():
                return str(nivel).strip()
        return ""

    # --- normalize --------------------------------------------------------

    def _beneficiario_anonimo(self, d: dict[str, Any], organo: str) -> Normalizado:
        """Conserva el pago pero no la identidad del particular.

        Se agrupa por convocatoria: así el mapa sigue mostrando cuánto reparte
        cada organismo y a través de qué convocatoria, sin nombrar a nadie.
        """
        convocatoria = str(d.get("numero_convocatoria") or "sin-convocatoria")
        clave_organo = f"bdns:organo:{slug(organo)}"
        clave_grupo = f"bdns:particulares:{convocatoria}"
        importe = d.get("importe")

        return Normalizado(
            entidades=[
                EntidadNormalizada(
                    ftm_schema="PublicBody",
                    caption=organo,
                    dedupe_key=clave_organo,
                    country="es",
                    properties={"name": organo},
                ),
                EntidadNormalizada(
                    ftm_schema="LegalEntity",
                    caption=f"Personas físicas (convocatoria {convocatoria})",
                    dedupe_key=clave_grupo,
                    country="es",
                    properties={
                        "agregado": True,
                        "motivo": "minimización de datos personales (RGPD)",
                        "convocatoria": d.get("convocatoria") or "",
                    },
                ),
            ],
            aristas=[
                AristaNormalizada(
                    ftm_schema="Payment",
                    source_key=clave_organo,
                    target_key=clave_grupo,
                    dedupe_key=f"bdns:concesion:{d['cod_concesion']}",
                    amount=importe,
                    currency="EUR" if importe is not None else "",
                    start_date=d.get("fecha_concesion"),
                    status="asserted",
                    # El pago consta; la identidad del receptor, no.
                    confidence=1.0,
                    properties={"beneficiario_anonimizado": True},
                )
            ],
        )

    def clasificar_beneficiario(self, nif: str) -> tuple[str, dict[str, Any]]:
        """Decide el esquema FtM del beneficiario y propiedades extra.

        Las subclases lo redefinen cuando el conjunto de datos ya dice qué es
        el beneficiario (p. ej. el de partidos políticos).
        """
        if not nif:
            # Sin identificador fiscal no afirmamos si es empresa o persona.
            return "LegalEntity", {}
        if parece_persona_fisica(nif):
            return "Person", {}
        return "Company", {}

    def normalize(self, record: ParsedRecord) -> Normalizado | None:
        """Traduce una concesión al vocabulario FollowTheMoney.

        Devuelve None si al registro le falta lo imprescindible. **No rellena
        huecos.**
        """
        d = record.data

        organo = (d.get("organo") or "").strip()
        beneficiario = (d.get("beneficiario") or "").strip()
        if not organo or not beneficiario:
            return None

        nif = d.get("nif_beneficiario") or ""

        # Minimización de datos personales (spec §12). BDNS enmascara el NIF de
        # las personas físicas pero publica su nombre completo. Republicar el
        # nombre de un particular que cobró una ayuda agraria en un mapa de
        # influencia política es una exposición desproporcionada: la fuente es
        # pública, pero el uso no sería el mismo.
        #
        # Se conserva el hecho —el organismo pagó esa cantidad— y se sustituye
        # la identidad por una etiqueta genérica. Ni siquiera se guarda el
        # nombre en properties: lo que no se persiste no se puede filtrar.
        if d.get("es_persona_fisica") and not nif:
            return self._beneficiario_anonimo(d, organo)

        # Sin NIF no podemos afirmar que dos "Construcciones García SL" sean la
        # misma: la clave queda acotada a esta fuente y la fusión, si procede,
        # la decidirá la resolución de entidades. Precisión sobre exhaustividad.
        clave_beneficiario = f"nif:{nif}" if nif else f"bdns:beneficiario:{slug(beneficiario)}"
        clave_organo = f"bdns:organo:{slug(organo)}"

        esquema, props_beneficiario = self.clasificar_beneficiario(nif)

        propiedades: dict[str, Any] = {}
        for clave in (
            "numero_convocatoria",
            "convocatoria",
            "instrumento",
            "url_bases_reguladoras",
        ):
            if d.get(clave):
                propiedades[clave] = d[clave]

        importe = d.get("importe")

        return Normalizado(
            entidades=[
                EntidadNormalizada(
                    ftm_schema="PublicBody",
                    caption=organo,
                    dedupe_key=clave_organo,
                    country="es",
                    properties={"name": organo},
                ),
                EntidadNormalizada(
                    ftm_schema=esquema,
                    caption=beneficiario,
                    dedupe_key=clave_beneficiario,
                    nif=nif,
                    country="es",
                    properties={"name": beneficiario, **props_beneficiario},
                ),
            ],
            aristas=[
                AristaNormalizada(
                    ftm_schema="Payment",
                    source_key=clave_organo,
                    target_key=clave_beneficiario,
                    dedupe_key=f"bdns:concesion:{d['cod_concesion']}",
                    amount=importe,
                    currency="EUR" if importe is not None else "",
                    start_date=d.get("fecha_concesion"),
                    # La fuente lo afirma; no lo inferimos nosotros.
                    status="asserted",
                    confidence=1.0 if nif else 0.7,
                    properties=propiedades,
                )
            ],
        )


class BDNSPartidosConnector(BDNSConnector):
    """Subvenciones a **partidos políticos**.

    Mismo universo de concesiones que el conector general, pero servido por un
    endpoint que ya viene filtrado a partidos. Eso aporta una cosa que el
    conjunto general no dice: que el beneficiario **es un partido político**.

    Comparte `source_id` y clave de arista con las concesiones generales a
    propósito. Si una misma concesión aparece en los dos conjuntos, debe
    quedar como **una sola arista**: duplicarla inflaría el dinero contabilizado,
    que es el peor error posible en un proyecto que va justamente de seguir el
    dinero. Los documentos crudos sí se guardan por separado —son URLs y bytes
    distintos— así que cada endpoint conserva su procedencia.
    """

    endpoint = ENDPOINT_PARTIDOS

    def clasificar_beneficiario(self, nif: str) -> tuple[str, dict[str, Any]]:
        # El conjunto de datos ya afirma que es un partido: no lo inferimos.
        # La propiedad se fusiona en el JSONB, así que la marca sobrevive
        # aunque el conector general procese antes la misma entidad.
        return "Organization", {"partido_politico": True}


def crear() -> BDNSConnector:
    """Fábrica del conector de concesiones generales."""
    return BDNSConnector()


def crear_partidos() -> BDNSPartidosConnector:
    """Fábrica del conector de subvenciones a partidos políticos."""
    return BDNSPartidosConnector()
