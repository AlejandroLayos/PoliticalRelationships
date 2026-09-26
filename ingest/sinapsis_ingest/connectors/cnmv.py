"""CNMV: accionistas significativos de las cotizadas y sus participaciones.

    titular (Company | Person) --Ownership--> cotizada (Company)

Lo que la CNMV publica de cada cotizada: quién tiene más del 3 % de sus
derechos de voto, y en qué otras cotizadas participa ella. Es la mitad
«empresarial» de la red de poder (spec §12, ampliación del 26/9/2026): los
accionistas significativos salen con nombre, tal como los publica la CNMV y
sólo en ese papel. Las reglas de lectura están en `sinapsis_ingest/cnmv.py`.

## Cómo se llega a las tablas

La forma la encontraron cinco vueltas de reconocimiento
(`docs/fuentes/cnmv-reconocimiento.md`):

1. `derechosvoto/ps_ac_ini.aspx?nif=…` da, en su título, el nombre que la
   CNMV tiene para ese NIF —la unión NIF ↔ nombre la hace la fuente, no
   nosotros— y, casi siempre, los enlaces a las dos tablas, con un
   identificador de sesión (`qS`).
2. Con un tercio de las cotizadas esa página no trae enlaces. Entonces se
   busca por ese mismo nombre en el buscador de participaciones, que sí los
   da.
3. Las dos tablas (accionistas y participadas) se guardan como crudo. De
   cada una se comprueba que su título nombra a la cotizada pedida; si no,
   no se usa.
4. Y su ficha, `ee/datosgenerales.aspx?nif=…`: el LEI y el sector en que la
   CNMV la clasifica. De ahí sale qué cotizadas son grupos de medios de
   comunicación: lo dice la CNMV, no una lista nuestra. La ficha sólo se usa
   si trae el NIF pedido.

El `qS` cambia en cada sesión, así que no sirve como enlace para la web: a
cada hecho se le pone como enlace la página estable de su cotizada.

## Las claves

Una cotizada de la lista va por su NIF (`nif:…`, la misma clave que en el
mapa del dinero). Una sociedad que sólo aparece nombrada en una tabla —un
fondo, una participada que no está en la lista— va por el nombre que le da
la CNMV; y si ese nombre es el de una cotizada de la lista, por su NIF. La
misma participación vista desde las dos tablas tiene la misma clave de
arista, porque en las dos la CNMV escribe igual los dos nombres.
"""

from __future__ import annotations

import csv
import re
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
import structlog

from sinapsis_ingest.cnmv import (
    emisor_del_titulo,
    enlaces_de_participaciones,
    es_persona_fisica,
    leer_accionistas,
    leer_datos_generales,
    leer_participadas,
    nombre_de_persona,
)
from sinapsis_ingest.connectors.base import ParsedRecord, RawDocument
from sinapsis_ingest.connectors.boe import clave
from sinapsis_ingest.normalizado import AristaNormalizada, EntidadNormalizada, Normalizado

log = structlog.get_logger()

BASE = "https://www.cnmv.es/portal/Consultas/"
PS_AC_INI = BASE + "derechosvoto/ps_ac_ini.aspx?nif={}"
DATOS_GENERALES = BASE + "ee/datosgenerales.aspx?nif={}"
BUSCADOR = BASE + "busqueda.aspx?id=7"
CAMPO_DENOMINACION = "ctl00$ContentPrincipal$wNombreEntidad$txtDenominacion"
BOTON_BUSCAR = "ctl00$ContentPrincipal$btnOk"
CABECERAS = {
    "User-Agent": "Sinapsis/0.1 (proyecto abierto de transparencia)",
    "Accept-Language": "es-ES,es;q=0.9",
}
SEMILLAS = Path(__file__).resolve().parent.parent / "datos" / "cotizadas.csv"


def leer_semillas(ruta: Path = SEMILLAS) -> list[str]:
    """Los NIF de la lista, sin comentarios ni cabecera."""
    lineas = [
        linea
        for linea in ruta.read_text(encoding="utf-8").splitlines()
        if linea.strip() and not linea.startswith("#")
    ]
    return [
        fila["nif"].strip() for fila in csv.DictReader(lineas, delimiter=";") if fila.get("nif")
    ]


def _ocultos(html: str) -> dict[str, str]:
    return dict(re.findall(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"', html))


class CNMVConnector:
    """Accionistas significativos y participaciones de las cotizadas de la lista."""

    source_id = "cnmv"
    extractor_version = "cnmv-participaciones/2"

    def __init__(
        self,
        cliente: httpx.Client | None = None,
        semillas: list[str] | None = None,
        pausa: float = 0.8,
    ) -> None:
        self._cliente = cliente
        self._semillas = semillas
        self._pausa = pausa

    def _get(self, cliente: httpx.Client, url: str) -> httpx.Response | None:
        try:
            r = cliente.get(url, headers=CABECERAS)
            r.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("cnmv: página no disponible", url=url, detalle=str(exc))
            return None
        time.sleep(self._pausa)
        return r

    def _buscar(self, cliente: httpx.Client, nombre: str) -> tuple[dict[str, str], str]:
        """Los enlaces de una cotizada por su nombre, con el buscador."""
        r = self._get(cliente, BUSCADOR)
        if r is None:
            return {}, ""
        datos = {**_ocultos(r.text), CAMPO_DENOMINACION: nombre, BOTON_BUSCAR: "Buscar"}
        try:
            respuesta = cliente.post(str(r.url), data=datos, headers=CABECERAS)
            respuesta.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("cnmv: el buscador no responde", nombre=nombre, detalle=str(exc))
            return {}, ""
        time.sleep(self._pausa)
        return enlaces_de_participaciones(respuesta.text), str(respuesta.url)

    def fetch(self, **_: Any) -> Iterator[RawDocument]:
        cliente = self._cliente or httpx.Client(timeout=60.0, follow_redirects=True)
        propio = self._cliente is None
        try:
            # 1. El nombre de cada NIF según la CNMV, y dónde están sus tablas.
            emisores: list[tuple[str, str, dict[str, str], str]] = []
            for nif in self._semillas if self._semillas is not None else leer_semillas():
                r = self._get(cliente, PS_AC_INI.format(nif))
                if r is None:
                    continue
                nombre = emisor_del_titulo(r.text)
                if not nombre:
                    log.warning("cnmv: la CNMV no reconoce el NIF", nif=nif)
                    continue
                enlaces, base = enlaces_de_participaciones(r.text), str(r.url)
                if not enlaces:
                    enlaces, base = self._buscar(cliente, nombre)
                if not enlaces:
                    log.warning("cnmv: sin enlaces a sus tablas", nif=nif, nombre=nombre)
                    continue
                # Los enlaces son relativos a la carpeta de derechos de voto.
                if "/derechosvoto/" not in base.lower():
                    base = BASE + "derechosvoto/"
                emisores.append((nif, nombre, enlaces, base))

            conocidas = {nombre: nif for nif, nombre, _, _ in emisores}
            # 2. La ficha de cada una: su sector.
            for nif, nombre, _, _ in emisores:
                url = DATOS_GENERALES.format(nif)
                r = self._get(cliente, url)
                if r is None:
                    continue
                yield RawDocument(
                    source_id=self.source_id,
                    url=url,
                    content=r.content,
                    media_type="text/html",
                    retrieved_at=datetime.now(UTC),
                    metadata={"nif": nif, "emisor": nombre, "tabla": "datosgenerales"},
                )
            # 3. Sus dos tablas.
            for nif, nombre, enlaces, base in emisores:
                for tabla in ("accionistas", "participadas"):
                    if tabla not in enlaces:
                        continue
                    url = urljoin(base, enlaces[tabla])
                    r = self._get(cliente, url)
                    if r is None:
                        continue
                    yield RawDocument(
                        source_id=self.source_id,
                        url=url,
                        content=r.content,
                        media_type="text/html",
                        retrieved_at=datetime.now(UTC),
                        metadata={
                            "nif": nif,
                            "emisor": nombre,
                            "tabla": tabla,
                            "url_publica": PS_AC_INI.format(nif),
                            "conocidas": conocidas,
                        },
                    )
        finally:
            if propio:
                cliente.close()

    def parse(self, raw: RawDocument) -> Iterator[ParsedRecord]:
        html = raw.content.decode("utf-8", errors="replace")
        tabla = raw.metadata.get("tabla")
        if tabla == "datosgenerales":
            yield from self._parse_ficha(raw, html)
            return
        leer = leer_accionistas if tabla == "accionistas" else leer_participadas
        de_la_pagina, filas = leer(html)
        # La página tiene que ser de la cotizada que se pidió.
        if de_la_pagina != raw.metadata.get("emisor"):
            log.warning(
                "cnmv: la página no es de la cotizada pedida",
                pedida=raw.metadata.get("emisor"),
                pagina=de_la_pagina,
            )
            return
        for i, p in enumerate(filas):
            yield ParsedRecord(
                raw_content_hash=raw.content_hash,
                extractor_version=self.extractor_version,
                data={
                    "id_registro": f"{raw.metadata.get('nif')}:{tabla}:{i}",
                    "tabla": tabla,
                    "nif": raw.metadata.get("nif"),
                    "titular": p.titular,
                    "sociedad": p.sociedad,
                    "porcentaje": str(p.porcentaje) if p.porcentaje is not None else "",
                    "porAcciones": str(p.por_acciones) if p.por_acciones is not None else "",
                    "porInstrumentos": str(p.por_instrumentos)
                    if p.por_instrumentos is not None
                    else "",
                    "directo": str(p.directo) if p.directo is not None else "",
                    "indirecto": str(p.indirecto) if p.indirecto is not None else "",
                    "fechaRegistro": p.fecha_registro.isoformat() if p.fecha_registro else "",
                    "url": raw.metadata.get("url_publica", ""),
                    "conocidas": raw.metadata.get("conocidas", {}),
                },
            )

    def _parse_ficha(self, raw: RawDocument, html: str) -> Iterator[ParsedRecord]:
        ficha = leer_datos_generales(html)
        # La ficha tiene que ser la del NIF pedido: una página de error o de
        # otra entidad no le pone sector a nadie.
        if ficha is None or ficha.nif != raw.metadata.get("nif"):
            log.warning(
                "cnmv: la ficha no es la del NIF pedido",
                pedido=raw.metadata.get("nif"),
                ficha=ficha.nif if ficha else None,
            )
            return
        yield ParsedRecord(
            raw_content_hash=raw.content_hash,
            extractor_version=self.extractor_version,
            data={
                "id_registro": f"{ficha.nif}:datosgenerales",
                "tabla": "datosgenerales",
                "nif": ficha.nif,
                "emisor": ficha.emisor or raw.metadata.get("emisor", ""),
                "lei": ficha.lei,
                "abreviada": ficha.abreviada,
                "sector": ficha.sector,
            },
        )

    def normalize(self, record: ParsedRecord) -> Normalizado | None:
        d = record.data
        if d.get("tabla") == "datosgenerales":
            return self._normalize_ficha(d)
        conocidas: dict[str, str] = d.get("conocidas") or {}

        def sociedad(nombre: str) -> EntidadNormalizada:
            nif = conocidas.get(nombre, "")
            return EntidadNormalizada(
                ftm_schema="Company",
                caption=nombre,
                dedupe_key=f"nif:{nif}" if nif else f"cnmv:sociedad:{clave(nombre)}",
                nif=nif,
                country="es" if nif else "",
                properties={
                    "name": nombre,
                    "nombreCNMV": nombre,
                    **({"cotizada": True} if nif else {}),
                },
            )

        cotizada = sociedad(d["sociedad"])
        if es_persona_fisica(d["titular"]) and d["titular"] not in conocidas:
            nombre = nombre_de_persona(d["titular"])
            titular = EntidadNormalizada(
                ftm_schema="Person",
                caption=nombre,
                dedupe_key=f"cnmv:persona:{clave(nombre)}",
                country="",
                # La marca del volcado: accionista significativo según la
                # CNMV, y en ese papel se publica (spec §12).
                properties={"name": nombre, "nombreCNMV": d["titular"], "accionista_cnmv": True},
            )
        else:
            titular = sociedad(d["titular"])
        if titular.dedupe_key == cotizada.dedupe_key:
            return None
        propiedades = {
            k: d[k]
            for k in ("porcentaje", "porAcciones", "porInstrumentos", "directo", "indirecto", "url")
            if d.get(k)
        }
        if d.get("fechaRegistro"):
            # No es la fecha de compra: es la de la última notificación.
            propiedades["fechaRegistroCNMV"] = d["fechaRegistro"]
        return Normalizado(
            entidades=[titular, cotizada],
            aristas=[
                AristaNormalizada(
                    ftm_schema="Ownership",
                    source_key=titular.dedupe_key,
                    target_key=cotizada.dedupe_key,
                    # Con los nombres de la CNMV: la misma participación vista
                    # desde la tabla de la cotizada y desde la de su accionista
                    # es una sola arista.
                    dedupe_key=f"cnmv:participacion:{clave(d['titular'])}:{clave(d['sociedad'])}",
                    confidence=1.0,
                    status="asserted",
                    properties={**propiedades, "relacion": "accionista_significativo"},
                )
            ],
        )

    def _normalize_ficha(self, d: dict[str, Any]) -> Normalizado | None:
        if not d.get("nif") or not d.get("emisor"):
            return None
        propiedades: dict[str, Any] = {
            "name": d["emisor"],
            "nombreCNMV": d["emisor"],
            "cotizada": True,
        }
        if d.get("sector"):
            propiedades["sectorCNMV"] = d["sector"]
        if d.get("lei"):
            propiedades["leiCode"] = d["lei"]
        if d.get("abreviada"):
            propiedades["alias"] = d["abreviada"]
        return Normalizado(
            entidades=[
                EntidadNormalizada(
                    ftm_schema="Company",
                    caption=d["emisor"],
                    dedupe_key=f"nif:{d['nif']}",
                    nif=d["nif"],
                    country="es",
                    properties=propiedades,
                )
            ],
            ficha=True,
        )


def crear() -> CNMVConnector:
    return CNMVConnector()
