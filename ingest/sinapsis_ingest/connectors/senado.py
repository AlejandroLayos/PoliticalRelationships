"""Senado: los partidos políticos, con sus siglas y su nombre oficial.

    partido (Organization) --UnknownLink{partido_en_grupo}--> grupo parlamentario (Organization)

El hecho es el que publica el Senado: en tal legislatura, tal partido formó
parte de tal grupo. Lo que se usa de él es otra cosa:

Sirve para UNA cosa: el puente entre unas siglas y un partido. El Congreso dice
que un diputado fue elegido por «PSOE»; el mapa del dinero tiene a «PARTIDO
SOCIALISTA OBRERO ESPAÑOL» cobrando subvenciones. Unirlos con una tabla hecha a
mano sería una inferencia nuestra; el Senado publica, para cada legislatura,
qué partidos hay en cada grupo con sus siglas y su nombre, y eso es la fuente
oficial de esa equivalencia.

## La forma

La verificó el reconocimiento (`docs/fuentes/senado-reconocimiento.md`):
`ficopendataservlet?tipoFich=4&legis=N` devuelve

    <GruposYpartidos>
      <Grupo>
        <datosCabecera><codigo/><nombre/><siglas/>…</datosCabecera>
        <listaPartidosPoliticos>
          <partido><partidoCod/><partidoSiglas/><partidoNombre/>…</partido>

## Lo que no se lee

Las fichas de cada senador traen estado civil, hijos y fecha de nacimiento.
Este conector no las pide: para el puente basta la lista de partidos.
"""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

from sinapsis_ingest.connectors.base import ParsedRecord, RawDocument
from sinapsis_ingest.connectors.boe import clave
from sinapsis_ingest.normalizado import AristaNormalizada, EntidadNormalizada, Normalizado

log = structlog.get_logger()

GRUPOS_Y_PARTIDOS = "https://www.senado.es/web/ficopendataservlet?tipoFich=4&legis={}"


def _texto(nodo: ET.Element | None) -> str:
    return " ".join((nodo.text or "").split()) if nodo is not None else ""


class SenadoConnector:
    """Los partidos de cada legislatura del Senado, con sus siglas."""

    source_id = "senado"
    extractor_version = "senado-partidos/1"

    def __init__(
        self, cliente: httpx.Client | None = None, desde: int = 9, hasta: int = 15
    ) -> None:
        self._cliente = cliente
        # Desde la IX, como el Congreso: las legislaturas de los gobiernos que
        # cubre el BOE que se lee y la anterior.
        self._desde = desde
        self._hasta = hasta

    def fetch(self, **_: Any) -> Iterator[RawDocument]:
        cliente = self._cliente or httpx.Client(
            timeout=60.0,
            follow_redirects=True,
            headers={"User-Agent": "Sinapsis/0.1 (proyecto abierto de transparencia)"},
        )
        propio = self._cliente is None
        try:
            for n in range(self._desde, self._hasta + 1):
                url = GRUPOS_Y_PARTIDOS.format(n)
                try:
                    r = cliente.get(url)
                    r.raise_for_status()
                except httpx.HTTPError as exc:
                    log.warning("senado: fichero no disponible", url=url, detalle=str(exc))
                    continue
                yield RawDocument(
                    source_id=self.source_id,
                    url=url,
                    content=r.content,
                    media_type="application/xml",
                    retrieved_at=datetime.now(UTC),
                    metadata={"legislatura": n},
                )
                time.sleep(0.3)
        finally:
            if propio:
                cliente.close()

    def parse(self, raw: RawDocument) -> Iterator[ParsedRecord]:
        try:
            raiz = ET.fromstring(raw.content)
        except ET.ParseError as exc:
            log.warning("senado: el fichero no es XML", url=raw.url, detalle=str(exc))
            return
        legislatura = raw.metadata.get("legislatura")
        i = 0
        for grupo in raiz.iter("Grupo"):
            cabecera = grupo.find("datosCabecera")
            codigo = _texto(cabecera.find("codigo")) if cabecera is not None else ""
            nombre_grupo = _texto(cabecera.find("nombre")) if cabecera is not None else ""
            for partido in grupo.iter("partido"):
                siglas = _texto(partido.find("partidoSiglas"))
                nombre = _texto(partido.find("partidoNombre"))
                i += 1
                if not siglas or not nombre or not codigo:
                    continue
                yield ParsedRecord(
                    raw_content_hash=raw.content_hash,
                    extractor_version=self.extractor_version,
                    data={
                        "id_registro": f"{raw.url}#{i}",
                        "url": raw.url,
                        "legislatura": legislatura,
                        "siglas": siglas,
                        "nombre": nombre,
                        "grupo_codigo": codigo,
                        "grupo_nombre": nombre_grupo,
                    },
                )

    def normalize(self, record: ParsedRecord) -> Normalizado | None:
        d = record.data
        # Una entidad por pareja siglas-nombre: si en otra legislatura el mismo
        # partido usa otras siglas, es otra pareja, y las dos se conservan.
        clave_partido = f"senado:partido:{clave(d['siglas'])}:{clave(d['nombre'])}"
        clave_grupo = f"senado:grupo:{d.get('legislatura')}:{d['grupo_codigo']}"
        return Normalizado(
            entidades=[
                EntidadNormalizada(
                    ftm_schema="Organization",
                    caption=d["nombre"],
                    dedupe_key=clave_partido,
                    country="es",
                    properties={
                        "name": d["nombre"],
                        "siglasSenado": d["siglas"],
                        "nombreSenado": d["nombre"],
                    },
                ),
                EntidadNormalizada(
                    ftm_schema="Organization",
                    caption=d.get("grupo_nombre") or d["grupo_codigo"],
                    dedupe_key=clave_grupo,
                    country="es",
                    properties={"name": d.get("grupo_nombre") or d["grupo_codigo"]},
                ),
            ],
            aristas=[
                AristaNormalizada(
                    ftm_schema="UnknownLink",
                    source_key=clave_partido,
                    target_key=clave_grupo,
                    dedupe_key=f"senado:{d.get('legislatura')}:{clave(d['siglas'])}:{d['grupo_codigo']}",
                    confidence=1.0,
                    properties={
                        "relacion": "partido_en_grupo",
                        "legislatura": d.get("legislatura"),
                        "url": d.get("url", ""),
                    },
                )
            ],
        )


def crear() -> SenadoConnector:
    return SenadoConnector()
