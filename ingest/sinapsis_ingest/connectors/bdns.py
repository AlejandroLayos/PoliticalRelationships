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

import hashlib
import json
import re
import time
from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
import structlog

from sinapsis_ingest.connectors.base import ParsedRecord, RawDocument

log = structlog.get_logger()

SOURCE_ID = "bdns"
BASE_URL = "https://www.infosubvenciones.es/bdnstrans/api"
ENDPOINT_CONCESIONES = f"{BASE_URL}/concesiones/busqueda"

# Súbelo sólo con un motivo: al cambiar, todo lo derivado se recomputa desde el
# crudo ya guardado. Formato "<fuente>/<n>".
EXTRACTOR_VERSION = "bdns/1"

# La API admite hasta 10.000, pero páginas así de grandes producen documentos
# crudos enormes y difíciles de reprocesar. 1.000 es un equilibrio razonable.
PAGE_SIZE = 1000

# 10 GET/s por IP es el límite de la API. Vamos deliberadamente por debajo: es
# un servicio público y no hay ninguna prisa.
PETICIONES_POR_SEGUNDO = 4.0


def normalizar_nif(valor: str | None) -> str:
    """Deja el NIF/CIF en mayúsculas y sin separadores.

    Sin esto, "B-12345678" y "b12345678" serían dos entidades distintas y toda
    la resolución determinista se vendría abajo.
    """
    if not valor:
        return ""
    limpio = re.sub(r"[^0-9A-Za-z]", "", valor).upper()
    # Un NIF/CIF español tiene 9 caracteres. Si no encaja, preferimos no
    # afirmar nada: devolvemos vacío y la entidad se identificará por otra vía.
    return limpio if len(limpio) == 9 else ""


def _a_decimal(valor: Any) -> Decimal | None:
    """Convierte un importe a Decimal. Nunca pasa por float."""
    if valor is None or valor == "":
        return None
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return None


def _a_fecha(valor: Any) -> date | None:
    """Acepta los formatos que ha usado BDNS: ISO y dd/mm/aaaa."""
    if not valor:
        return None
    texto = str(valor).strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(texto[: len(formato) + 2], formato).date()
        except ValueError:
            continue
    return None


def _parece_persona_fisica(nif: str) -> bool:
    """Un NIF de persona física empieza por dígito, K, L, M, X, Y o Z.

    Los CIF de personas jurídicas empiezan por otra letra. Sirve para elegir
    entre `Person` y `Company`, y por tanto para saber cuándo estamos tocando
    datos personales (spec §12).
    """
    if not nif:
        return False
    return nif[0].isdigit() or nif[0] in "KLMXYZ"


class BDNSConnector:
    """Conector de concesiones de BDNS."""

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
                    resp = cliente.get(ENDPOINT_CONCESIONES, params=params)
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
                    "numero_convocatoria": item.get("numeroConvocatoria"),
                    "convocatoria": item.get("convocatoria"),
                    "organo": self._nombre_organo(item),
                    "beneficiario": item.get("beneficiario"),
                    "nif_beneficiario": normalizar_nif(item.get("nifCif")),
                    "importe": _a_decimal(item.get("importe")),
                    "ayuda_equivalente": _a_decimal(item.get("ayudaEquivalente")),
                    "fecha_concesion": _a_fecha(item.get("fechaConcesion")),
                    "instrumento": item.get("instrumento"),
                    "url_bases_reguladoras": item.get("urlBR"),
                },
            )

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

    def normalize(self, record: ParsedRecord) -> dict[str, Any] | None:
        """Traduce una concesión al vocabulario FollowTheMoney.

        Devuelve un dict con la entidad origen, la destino y la arista, o None
        si al registro le falta lo imprescindible. **No rellena huecos.**
        """
        d = record.data

        organo = (d.get("organo") or "").strip()
        beneficiario = (d.get("beneficiario") or "").strip()
        if not organo or not beneficiario:
            return None

        nif = d.get("nif_beneficiario") or ""

        # Sin NIF no podemos afirmar que dos "Construcciones García SL" sean la
        # misma: la clave queda acotada a esta fuente y la fusión, si procede,
        # la decidirá la resolución de entidades. Precisión sobre exhaustividad.
        if nif:
            clave_beneficiario = f"nif:{nif}"
            esquema = "Person" if _parece_persona_fisica(nif) else "Company"
        else:
            clave_beneficiario = f"bdns:beneficiario:{_slug(beneficiario)}"
            esquema = "LegalEntity"

        entidad_origen = {
            "ftm_schema": "PublicBody",
            "caption": organo,
            "dedupe_key": f"bdns:organo:{_slug(organo)}",
            "country": "es",
            "properties": {"name": organo},
        }
        entidad_destino = {
            "ftm_schema": esquema,
            "caption": beneficiario,
            "dedupe_key": clave_beneficiario,
            "nif": nif,
            "country": "es",
            "properties": {"name": beneficiario},
        }

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
        arista = {
            "ftm_schema": "Payment",
            "dedupe_key": f"bdns:concesion:{d['cod_concesion']}",
            "amount": importe,
            "currency": "EUR" if importe is not None else "",
            "start_date": d.get("fecha_concesion"),
            # La fuente lo afirma; no lo inferimos nosotros.
            "status": "asserted",
            "confidence": 1.0 if nif else 0.7,
            "properties": propiedades,
        }

        return {
            "source_entity": entidad_origen,
            "target_entity": entidad_destino,
            "relationship": arista,
        }


def _slug(texto: str) -> str:
    """Clave estable y legible a partir de un nombre.

    Se usa sólo cuando no hay NIF. Va con hash corto detrás porque dos
    organismos pueden normalizar al mismo slug y colapsarlos sería inventar una
    identidad que la fuente no afirma.
    """
    base = re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")[:60]
    digest = hashlib.sha256(texto.encode("utf-8")).hexdigest()[:8]
    return f"{base}-{digest}"


def crear() -> BDNSConnector:
    """Fábrica para el registro de conectores."""
    return BDNSConnector()
