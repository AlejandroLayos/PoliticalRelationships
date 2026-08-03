"""Tribunal de Cuentas: expedientes sancionadores a formaciones políticas.

    partido --Debt--> Tribunal de Cuentas

Una multa es una deuda del partido con el Estado, y `Debt` es la única arista
de FollowTheMoney que lo dice sin inventar nada: `Sanction` existe en FtM pero
es una **entidad** (edge=False), igual que `Contract`, así que no sirve para
enlazar dos nodos. Modelarlo como deuda además mantiene el importe dentro del
grafo, que es de lo que va el proyecto.

## Por qué el parser está escrito así

El organismo no tiene API: publica PDF. El reconocimiento
(`docs/fuentes/tcu-reconocimiento.md`) confirmó que no hay ni tablas HTML ni
ficheros tabulares, y la anatomía (`docs/fuentes/tcu-anatomia-pdf.md`) que los
PDF sí tienen capa de texto y tablas con bordes. O sea: `pdfplumber` con la
estrategia por líneas, sin OCR.

Tres cosas que se vieron en el fichero real y que romperían un parser escrito
a ojo:

1. **El número de columnas cambia de una página a otra** (16, 20 y 18 en el
   mismo documento de 2019), porque las celdas combinadas se reparten de forma
   distinta. Las etiquetas sí son estables. Por eso el mapeo va **por nombre
   de cabecera, nunca por posición**.
2. **La cabecera ocupa varias filas.** "RECURSO CONTENCIOSO-ADMINISTRATIVO
   ANTE TS" viene partida en cuatro filas consecutivas.
3. **Un registro lógico ocupa varias filas físicas.** Cuando un texto largo se
   parte, las filas siguientes traen sólo la cola y el resto vacío. Se
   reconocen porque la columna ORIGEN viene vacía.
"""

from __future__ import annotations

import io
import re
from collections.abc import Iterator
from datetime import UTC, date, datetime
from typing import Any

import httpx
import structlog

from sinapsis_ingest.connectors.base import ParsedRecord, RawDocument
from sinapsis_ingest.normalizado import AristaNormalizada, EntidadNormalizada, Normalizado
from sinapsis_ingest.util import a_decimal, normalizar_nif, slug

log = structlog.get_logger()

BASE = "https://www.tcu.es/export/sites/portal/.galleries/Documentos-oficiales/Partidos-politicos/"

# Sacados del reconocimiento, no inventados: son los enlaces que publica la
# propia página de sanciones a partidos del organismo.
DOCUMENTOS = (
    f"{BASE}Procedimientos-sancionadores-contabilidad-electoral-2015.pdf",
    f"{BASE}Procedimientos-sancionadores-contabilidad-electoral-2019.pdf",
    f"{BASE}Procedimientos-sancionadores-contabilidad-electoral-2023.pdf",
    f"{BASE}Procedimientos-sancionadores-contabilidad-ordinaria.pdf",
)

ORGANO = "Tribunal de Cuentas"
CLAVE_ORGANO = "tcu:organo:tribunal-de-cuentas"

# Las etiquetas tal y como salen del PDF, normalizadas. La clave es el nombre
# interno; el valor, los comienzos de etiqueta que lo identifican.
_COLUMNAS = {
    "origen": ("ORIGEN",),
    "formacion": ("FORMACION POLITICA",),
    "nif": ("NIF",),
    "fecha": ("FECHA RESOLUCION",),
    "ley": ("LEY APLICABLE",),
    "presunta_infraccion": ("PRESUNTA INFRACCION",),
    "infraccion": ("NO INICIAR PS", "NO INICIAR P S", "INFRACCION SANCIONADA"),
    "cuantia": ("CUANTIA SANCION", "CUANTIA"),
    "recurso": ("RECURSO",),
    "resolucion_recurso": ("RESOLUCION DEL RECURSO",),
}

_IMPORTE = re.compile(r"\d{1,3}(?:\.\d{3})*,\d{2}")
_FECHA = re.compile(r"(\d{2})/(\d{2})/(\d{4})")


def _limpiar(celda: Any) -> str:
    """Une los saltos de línea internos y colapsa espacios."""
    if celda is None:
        return ""
    return re.sub(r"\s+", " ", str(celda)).strip()


def _sin_tildes(texto: str) -> str:
    import unicodedata

    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    ).upper()


def _mapear_cabecera(fila: list) -> dict[str, int]:
    """Devuelve {nombre interno: índice de columna}.

    Por nombre y no por posición: el mismo documento trae 16, 18 y 20 columnas
    en páginas distintas según cómo se repartan las celdas combinadas.
    """
    indices: dict[str, int] = {}
    for i, celda in enumerate(fila):
        etiqueta = _sin_tildes(_limpiar(celda))
        if not etiqueta:
            continue
        for nombre, comienzos in _COLUMNAS.items():
            if nombre in indices:
                continue
            if any(etiqueta.startswith(c) for c in comienzos):
                indices[nombre] = i
                break
    return indices


def _es_cabecera(fila: list) -> bool:
    etiquetas = _sin_tildes(" ".join(_limpiar(c) for c in fila))
    return "ORIGEN" in etiquetas and "FORMACION POLITICA" in etiquetas


def _filas_logicas(tabla: list, indices: dict[str, int]) -> Iterator[dict[str, str]]:
    """Agrupa las filas físicas en registros.

    Una fila con ORIGEN vacío no es un registro nuevo: es la continuación del
    anterior, con la cola de algún texto que no cupo. Tratarlas como registros
    produciría partidos fantasma llamados "ANULADA" o "SANCIÓN*".
    """
    i_origen = indices["origen"]
    actual: dict[str, str] | None = None

    for fila in tabla:
        if _es_cabecera(fila):
            actual = None
            continue
        origen = _limpiar(fila[i_origen]) if i_origen < len(fila) else ""

        if origen:
            if actual is not None:
                yield actual
            actual = {
                nombre: (_limpiar(fila[i]) if i < len(fila) else "")
                for nombre, i in indices.items()
            }
            continue

        if actual is None:
            # Cola sin cabeza: la tabla empieza a media fila partida. No se
            # inventa a qué registro pertenece.
            continue
        for nombre, i in indices.items():
            trozo = _limpiar(fila[i]) if i < len(fila) else ""
            if trozo:
                actual[nombre] = f"{actual[nombre]} {trozo}".strip()

    if actual is not None:
        yield actual


class TCUConnector:
    """Lee los expedientes sancionadores publicados en PDF."""

    source_id = "tcu"
    extractor_version = "tcu-pdf-1"

    def __init__(
        self,
        cliente: httpx.Client | None = None,
        documentos: tuple[str, ...] = DOCUMENTOS,
        verify: Any = True,
    ) -> None:
        self._cliente = cliente
        self._documentos = documentos
        self._verify = verify

    # --- fetch ------------------------------------------------------------

    def fetch(self, **params: Any) -> Iterator[RawDocument]:
        """Descarga los expedientes.

        No acepta rango de fechas porque la fuente no lo ofrece: son cuatro
        documentos acumulativos que el organismo reescribe. La idempotencia la
        da el `content_hash`, así que reejecutar sin cambios no crea nada.
        """
        cliente = self._cliente or httpx.Client(
            timeout=60.0,
            follow_redirects=True,
            verify=self._verify,
            headers={
                "User-Agent": (
                    "Sinapsis/0.1 (proyecto abierto de transparencia; "
                    "+https://github.com/AlejandroLayos/PoliticalRelationships)"
                )
            },
        )
        propio = self._cliente is None
        try:
            for url in self._documentos:
                try:
                    r = cliente.get(url)
                    r.raise_for_status()
                except httpx.HTTPError as exc:
                    # Tolerar el hueco: un documento que no baja hoy no debe
                    # llevarse por delante los otros tres.
                    log.warning("tcu: documento no disponible", url=url, detalle=str(exc))
                    continue
                if not r.content.startswith(b"%PDF"):
                    log.warning("tcu: la respuesta no es un PDF", url=url)
                    continue
                yield RawDocument(
                    source_id=self.source_id,
                    url=url,
                    content=r.content,
                    media_type="application/pdf",
                    retrieved_at=datetime.now(UTC),
                )
        finally:
            if propio:
                cliente.close()

    # --- parse ------------------------------------------------------------

    def parse(self, raw: RawDocument) -> Iterator[ParsedRecord]:
        import pdfplumber

        try:
            pdf = pdfplumber.open(io.BytesIO(raw.content))
        except Exception as exc:
            log.warning("tcu: PDF ilegible", url=raw.url, detalle=str(exc))
            return

        with pdf:
            for n_pagina, pagina in enumerate(pdf.pages):
                try:
                    tablas = pagina.extract_tables() or []
                except Exception as exc:
                    log.warning("tcu: página ilegible", pagina=n_pagina, detalle=str(exc))
                    continue

                for tabla in tablas:
                    if not tabla or len(tabla) < 3:
                        # Las cajas de 2x1 y 3x1 son encabezados y pies.
                        continue
                    cabecera = next((f for f in tabla if _es_cabecera(f)), None)
                    if cabecera is None:
                        continue
                    indices = _mapear_cabecera(cabecera)
                    # Sin estas tres no hay registro que valga: quién, cuándo y
                    # de qué proceso. Si faltan, el formato cambió.
                    if not {"origen", "formacion", "nif"} <= set(indices):
                        log.warning(
                            "tcu: la tabla no trae las columnas esperadas",
                            url=raw.url,
                            pagina=n_pagina,
                            encontradas=sorted(indices),
                        )
                        continue

                    for fila in _filas_logicas(tabla, indices):
                        if not fila.get("formacion"):
                            continue
                        yield ParsedRecord(
                            raw_content_hash=raw.content_hash,
                            extractor_version=self.extractor_version,
                            data={**fila, "url": raw.url, "pagina": n_pagina},
                        )

    # --- normalize --------------------------------------------------------

    def normalize(self, record: ParsedRecord) -> Normalizado | None:
        d = record.data
        formacion = d.get("formacion", "").strip()
        if not formacion:
            return None

        nif = normalizar_nif(d.get("nif"))
        clave_partido = f"nif:{nif}" if nif else f"tcu:formacion:{slug(formacion)}"

        # Un importe por celda es el caso normal. Cuando hay dos —pasa cuando
        # la resolución del recurso fija otra cuantía— no se puede afirmar
        # cuál es la sanción sin interpretarlo, así que no se pone importe y
        # se conserva el texto crudo. Meter el número equivocado sería
        # atribuirle a un partido una multa que no es la suya.
        crudo_cuantia = d.get("cuantia", "")
        importes = _IMPORTE.findall(crudo_cuantia)
        if len(importes) == 1:
            importe = a_decimal(importes[0].replace(".", "").replace(",", "."))
            confianza = 1.0
        else:
            importe = None
            confianza = 0.5 if importes else 1.0

        fecha = None
        m = _FECHA.search(d.get("fecha", ""))
        if m:
            try:
                fecha = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            except ValueError:
                fecha = None

        propiedades = {
            k: v
            for k, v in (
                ("origen", d.get("origen")),
                ("leyAplicable", d.get("ley")),
                ("presuntaInfraccion", d.get("presunta_infraccion")),
                ("infraccionSancionada", d.get("infraccion")),
                ("recurso", d.get("recurso")),
                ("resolucionRecurso", d.get("resolucion_recurso")),
            )
            if v
        }
        if importe is None and crudo_cuantia:
            propiedades["cuantiaSinInterpretar"] = crudo_cuantia

        entidades = [
            EntidadNormalizada(
                ftm_schema="Organization",
                caption=formacion,
                dedupe_key=clave_partido,
                nif=nif,
                country="es",
                properties={"name": formacion, "partido_politico": True},
            ),
            EntidadNormalizada(
                ftm_schema="PublicBody",
                caption=ORGANO,
                dedupe_key=CLAVE_ORGANO,
                country="es",
                properties={"name": ORGANO},
            ),
        ]

        # La multa es una deuda del partido con el Estado: debtor -> creditor.
        arista = AristaNormalizada(
            ftm_schema="Debt",
            source_key=clave_partido,
            target_key=CLAVE_ORGANO,
            dedupe_key=(
                f"tcu:sancion:{slug(d.get('origen', ''))}:{clave_partido}"
                f":{d.get('fecha', '')}:{slug(d.get('presunta_infraccion', ''))}"
            ),
            amount=importe,
            currency="EUR" if importe is not None else "",
            start_date=fecha,
            status="asserted",
            confidence=confianza,
            properties=propiedades,
        )
        return Normalizado(entidades=entidades, aristas=[arista])


def crear() -> TCUConnector:
    return TCUConnector()
