"""CNMV: el consejo de administración de cada cotizada, de su informe de gobierno.

    consejero (Person | Company) --Directorship--> cotizada (Company)

Los consejeros de una cotizada salen con nombre, tal como los publica la CNMV
y sólo en ese papel (spec §12, ampliación del 26/9/2026). La fuente es el
cuadro C.1.2 del informe anual de gobierno corporativo (IAGC), un PDF por
ejercicio que la CNMV registra y publica.

## Cómo se llega

1. `ee/informaciongobcorp.aspx?nif=…` lista los informes de la cotizada, uno
   por fila y por tipo. Se lee la tabla del IAGC (no la del informe de
   remuneraciones, que también nombra consejeros) y se toma el del último
   ejercicio (`informes_de_gobierno`).
2. El PDF se guarda como crudo tal cual, y se lee con las reglas de
   `sinapsis_ingest/cnmv.py`.

Antes de pedir nada se pasa por la portada: sin la sesión hecha, la página de
informes vuelve vacía (octava vuelta del reconocimiento,
`docs/fuentes/cnmv-reconocimiento.md`).

## Caché

El IAGC es anual y pesa de 4 a 20 MB. Con `cache` los PDF se guardan por su
número de registro en la CNMV, que no cambia: una versión modificada tiene
otro número. La primera noche se bajan todos; las demás, sólo los nuevos.

## La CNMV corta conexiones

La octava vuelta del reconocimiento se quedó sin nada: la CNMV cerró cada
conexión, portada incluida; media hora después respondió a todo. Cada
petición se reintenta con esperas crecientes, y el conector deja de pedir
informes nuevos al llegar a su tope de tiempo (`tope_segundos`), para
terminar bien en vez de que el paso lo corte a medias.

## Lo que se pierde, se cuenta

Una fila del cuadro partida entre dos páginas llega sin categoría y se deja
(ver `miembros_del_consejo`). El apartado C.1.1 dice cuántos consejeros fijó
la junta; si se leen menos, se anota en el registro de la ingesta.

## Fechas

Del cuadro no se guarda ninguna fecha. El informe trae las de nombramiento y,
en algunos modelos, la de nacimiento, que no hace falta para nada: lo que se
afirma es «consejero según el IAGC del ejercicio N», con su enlace.
"""

from __future__ import annotations

import io
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import structlog

from sinapsis_ingest.cnmv import (
    a_quien_representan,
    consejeros_fijados,
    emisor_del_titulo,
    informes_de_gobierno,
    miembros_del_consejo,
    variantes_de_nif,
)
from sinapsis_ingest.connectors.base import ParsedRecord, RawDocument
from sinapsis_ingest.connectors.boe import clave
from sinapsis_ingest.connectors.cnmv import BASE, CABECERAS, PS_AC_INI, leer_semillas
from sinapsis_ingest.normalizado import AristaNormalizada, EntidadNormalizada, Normalizado

log = structlog.get_logger()

PORTADA = "https://www.cnmv.es/portal/home.aspx"
GOBIERNO_CORPORATIVO = BASE + "ee/informaciongobcorp.aspx?nif={}"


class CNMVConsejosConnector:
    """Los consejeros de las cotizadas de la lista, del último IAGC de cada una."""

    source_id = "cnmv"
    extractor_version = "cnmv-consejos/1"

    def __init__(
        self,
        cliente: httpx.Client | None = None,
        semillas: list[str] | None = None,
        cache: Path | None = None,
        pausa: float = 1.0,
        esperas: tuple[float, ...] = (5.0, 20.0),
        tope_segundos: float | None = None,
    ) -> None:
        self._cliente = cliente
        self._semillas = semillas
        self._cache = cache
        self._pausa = pausa
        self._esperas = esperas
        self._tope = tope_segundos

    def _get(self, cliente: httpx.Client, url: str) -> httpx.Response | None:
        for intento, espera in enumerate((*self._esperas, None)):
            try:
                r = cliente.get(url, headers=CABECERAS)
                r.raise_for_status()
            except httpx.HTTPError as exc:
                if espera is None:
                    log.warning("cnmv: página no disponible", url=url, detalle=str(exc))
                    return None
                log.info("cnmv: se reintenta", url=url, intento=intento + 1, detalle=str(exc))
                time.sleep(espera)
                continue
            time.sleep(self._pausa)
            return r
        return None

    def _pdf(self, cliente: httpx.Client, registro: str, url: str) -> bytes | None:
        guardado = self._cache / f"iagc-{registro}.pdf" if self._cache and registro else None
        if guardado and guardado.exists():
            return guardado.read_bytes()
        r = self._get(cliente, url)
        if r is None or not r.content.startswith(b"%PDF"):
            log.warning("cnmv: el informe no es un PDF", url=url)
            return None
        if guardado:
            guardado.parent.mkdir(parents=True, exist_ok=True)
            guardado.write_bytes(r.content)
        return r.content

    def fetch(self, **_: Any) -> Iterator[RawDocument]:
        cliente = self._cliente or httpx.Client(timeout=120.0, follow_redirects=True)
        propio = self._cliente is None
        try:
            inicio = time.monotonic()
            # La sesión: sin ella la página de informes vuelve vacía.
            self._get(cliente, PORTADA)
            for nif in self._semillas if self._semillas is not None else leer_semillas():
                if self._tope is not None and time.monotonic() - inicio > self._tope:
                    log.warning("cnmv: tope de tiempo; quedan cotizadas sin leer", desde=nif)
                    break
                # El nombre de la cotizada lo da la CNMV, como en las
                # participaciones: es contra lo que se compara el informe.
                r = self._get(cliente, PS_AC_INI.format(nif))
                emisor = emisor_del_titulo(r.text) if r is not None else ""
                if not emisor:
                    log.warning("cnmv: la CNMV no reconoce el NIF", nif=nif)
                    continue
                # Tal cual y, si no hay nada, con guion: ver `variantes_de_nif`.
                informes, url_publica = [], ""
                for variante in variantes_de_nif(nif):
                    url_publica = GOBIERNO_CORPORATIVO.format(variante)
                    r = self._get(cliente, url_publica)
                    # Sólo los de ESTE emisor: la página puede listar todos.
                    informes = informes_de_gobierno(r.text, nif) if r is not None else []
                    if informes:
                        break
                if not informes:
                    log.warning("cnmv: sin informe de gobierno corporativo", nif=nif)
                    continue
                ultimo = informes[0]
                pdf = self._pdf(cliente, ultimo.registro, ultimo.url)
                if pdf is None:
                    continue
                yield RawDocument(
                    source_id=self.source_id,
                    url=ultimo.url,
                    content=pdf,
                    media_type="application/pdf",
                    retrieved_at=datetime.now(UTC),
                    metadata={
                        "nif": nif,
                        "emisor": emisor,
                        "ejercicio": ultimo.ejercicio,
                        "registro": ultimo.registro,
                        "url_publica": url_publica,
                    },
                )
        finally:
            if propio:
                cliente.close()

    def parse(self, raw: RawDocument) -> Iterator[ParsedRecord]:
        tablas, texto = tablas_del_cuadro(raw.content)
        miembros, descartadas = miembros_del_consejo(tablas)
        representa = a_quien_representan(tablas)
        fijados = consejeros_fijados(texto)
        nif = raw.metadata.get("nif", "")
        if not miembros:
            log.warning("cnmv: el informe no trae el cuadro del consejo", nif=nif)
        if descartadas or (fijados is not None and len(miembros) < fijados):
            log.warning(
                "cnmv: consejo incompleto",
                nif=nif,
                leidos=len(miembros),
                fijados=fijados,
                filas_dejadas=descartadas,
            )
        for m in miembros:
            yield ParsedRecord(
                raw_content_hash=raw.content_hash,
                extractor_version=self.extractor_version,
                data={
                    "id_registro": f"{nif}:consejo:{clave(m.nombre)}",
                    "nif": nif,
                    "emisor": raw.metadata.get("emisor", ""),
                    "ejercicio": raw.metadata.get("ejercicio"),
                    "url": raw.metadata.get("url_publica", ""),
                    "nombre": m.nombre,
                    "persona": m.persona,
                    "representante": m.representante,
                    "categoria": m.categoria,
                    "cargo": m.cargo,
                    # Si es dominical: el accionista en cuyo nombre se sienta,
                    # tal como lo escribe el informe.
                    "representa": representa.get(m.nombre, "")
                    if m.categoria == "Dominical"
                    else "",
                },
            )

    def normalize(self, record: ParsedRecord) -> Normalizado | None:
        d = record.data
        if not d.get("nif") or not d.get("emisor") or not d.get("nombre"):
            return None
        cotizada = EntidadNormalizada(
            ftm_schema="Company",
            caption=d["emisor"],
            dedupe_key=f"nif:{d['nif']}",
            nif=d["nif"],
            country="es",
            properties={"name": d["emisor"], "nombreCNMV": d["emisor"], "cotizada": True},
        )
        if d["persona"]:
            # La misma clave que un accionista de la CNMV con ese nombre: quien
            # es las dos cosas es un solo nodo. Sólo dentro de la CNMV; con
            # nadie de otra fuente.
            miembro = EntidadNormalizada(
                ftm_schema="Person",
                caption=d["nombre"],
                dedupe_key=f"cnmv:persona:{clave(d['nombre'])}",
                properties={"name": d["nombre"], "consejero_cnmv": True},
            )
        else:
            miembro = EntidadNormalizada(
                ftm_schema="Company",
                caption=d["nombre"],
                dedupe_key=f"cnmv:sociedad:{clave(d['nombre'])}",
                properties={"name": d["nombre"], "nombreCNMV": d["nombre"]},
            )
        propiedades = {
            k: d[k]
            for k in ("cargo", "categoria", "ejercicio", "url", "representante", "representa")
            if d.get(k)
        }
        return Normalizado(
            entidades=[miembro, cotizada],
            aristas=[
                AristaNormalizada(
                    ftm_schema="Directorship",
                    source_key=miembro.dedupe_key,
                    target_key=cotizada.dedupe_key,
                    dedupe_key=f"cnmv:consejo:{clave(d['nombre'])}:{d['nif']}",
                    confidence=1.0,
                    status="asserted",
                    properties={**propiedades, "relacion": "consejo"},
                )
            ],
        )


def tablas_del_cuadro(pdf: bytes) -> tuple[list[list[list[str | None]]], str]:
    """Las tablas de las páginas del cuadro C.1.2, y el texto de esas páginas.

    Leer las tablas de un informe entero tardaba de 24 a 98 segundos. El texto
    de cada página, con pdfium, es casi inmediato: con él se buscan las
    páginas que traen la cabecera del cuadro (y la siguiente, por donde sigue),
    y sólo de ésas se sacan las tablas.
    """
    import pdfplumber
    import pypdfium2 as pdfium

    documento = pdfium.PdfDocument(pdf)
    paginas: set[int] = set()
    texto = []
    try:
        for i in range(len(documento)):
            plano = " ".join(documento[i].get_textpage().get_text_range().split())
            if "fijado por la junta" in plano:
                texto.append(plano)
            # El cuadro del consejo (C.1.2) y el de los dominicales (C.1.3).
            if "denominación social del consejero" in plano or "a quien representa" in plano:
                paginas.update({i, i + 1})
        total = len(documento)
    finally:
        documento.close()
    tablas: list[list[list[str | None]]] = []
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        for i in sorted(p for p in paginas if p < total):
            tablas.extend(doc.pages[i].extract_tables() or [])
    return tablas, " ".join(texto)


def crear() -> CNMVConsejosConnector:
    import os

    cache = os.environ.get("SINAPSIS_CACHE_CNMV")
    minutos = os.environ.get("SINAPSIS_CNMV_TOPE_MINUTOS")
    return CNMVConsejosConnector(
        cache=Path(cache) if cache else None,
        tope_segundos=float(minutos) * 60 if minutos else None,
    )
