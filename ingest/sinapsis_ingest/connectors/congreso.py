"""Congreso de los Diputados: quién fue diputado, cuándo y por qué formación.

    diputado (Person) --Occupancy--> escaño de la legislatura (Position)

Para la línea 4 de la fase 7 —qué partido gobernaba— y para dar contexto a
los altos cargos: de qué formación era un ministro que fue diputado. El
Congreso es una de las fuentes oficiales que la regla de §12 admite para
nombrar a una persona, y sólo en su papel de diputado.

## La forma

La verificó el reconocimiento (`docs/fuentes/congreso-reconocimiento.md`):
un JSON por legislatura (`odsDiputadosNN__<marca>.json`, la marca cambia a
diario, así que los enlaces se leen de la página), una lista de objetos con

    NOMBRE («Apellidos, Nombre»), CIRCUNSCRIPCION, FORMACIONELECTORAL,
    FECHACONDICIONPLENA, FECHAALTA, FECHABAJA, GRUPOPARLAMENTARIO,
    FECHAALTAENGRUPOPARLAMENTARIO, FECHABAJAENGRUPOPARLAMENTARIO, BIOGRAFIA

y la legislatura en curso aparte, en los ficheros de diputados activos y de
baja. Fechas `dd/mm/aaaa`.

## Las declaraciones de actividades

Cada diputado declara al Congreso, al tomar posesión, sus actividades de los
años anteriores y las que mantiene (Reglamento del Congreso, art. 18 del
Código de Conducta de las Cortes). El Congreso las publica en un fichero
aparte (`docacteco__<marca>.json`), sólo de la legislatura en curso, una fila
por cosa declarada: `TIPO` ACTIVIDAD (con EMPLEADOR, SECTOR, PERIODO,
DESCRIPCION), FUNDACIONES, DONACION u OBSERVACIONES.

Se guardan **sólo las actividades**: para quién trabajó el diputado. Es lo
que une el escaño con una empresa, y lo afirma el propio diputado ante la
Cámara. Las donaciones, las aportaciones a fundaciones y las observaciones
no se guardan: no hacen falta para nada de lo que se publica.

## La biografía no se guarda

Trae la trayectoria profesional de cada diputado y no hace falta para nada de
lo que se publica. De ella se saca sólo una cosa: los cargos públicos que
menciona («Ministro de Fomento (2018-2020)»). Es la segunda señal que pide
§12 para unir a un diputado con un alto cargo del BOE: además del nombre, que
la fuente misma diga que ocupó ese cargo.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Iterator
from datetime import UTC, date, datetime
from typing import Any

import httpx
import structlog

from sinapsis_ingest.connectors.base import ParsedRecord, RawDocument
from sinapsis_ingest.connectors.boe import clave
from sinapsis_ingest.connectors.oci import nombre_para_cruzar
from sinapsis_ingest.normalizado import AristaNormalizada, EntidadNormalizada, Normalizado

log = structlog.get_logger()

PORTADA = "https://www.congreso.es/es/opendata/diputados"

_POR_LEGISLATURA = re.compile(r"odsDiputados(\d{1,2})__\d+\.json$")
_EN_CURSO = re.compile(r"(DiputadosActivos|DiputadosDeBaja)__\d+\.json$")
_DECLARACIONES = re.compile(r"docacteco__\d+\.json$")

_ROMANOS = [
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
]


def romano(n: int) -> str:
    salida = ""
    for valor, letra in _ROMANOS:
        while n >= valor:
            salida += letra
            n -= valor
    return salida


# Los cargos públicos que puede mencionar una biografía. Sólo el comienzo de
# la mención y lo que sigue hasta un corte; no se interpreta más.
_CARGO_EN_BIOGRAFIA = re.compile(
    r"\b((?:Presidente|Presidenta) del Gobierno"
    r"|Vicepresident[ea](?: (?:primer[oa]|segund[oa]|tercer[oa]|cuart[oa]))? del Gobierno"
    r"|Ministr[oa] (?:de|del|para)\b[^.;:(\n]{2,110}"
    r"|Secretari[oa] de Estado\b[^.;:(\n]{0,110}"
    r"|Subsecretari[oa] (?:de|del)\b[^.;:(\n]{2,110}"
    r"|Secretari[oa] General (?:de|del)\b[^.;:(\n]{2,110}"
    r"|Director[a]? General (?:de|del)\b[^.;:(\n]{2,110}"
    r"|Delegad[oa] del Gobierno\b[^.;:(\n]{0,80})",
    re.IGNORECASE,
)


def cargos_en_biografia(biografia: str) -> list[str]:
    """Las menciones a cargos públicos de una biografía, y nada más."""
    return sorted({" ".join(m.split()) for m in _CARGO_EN_BIOGRAFIA.findall(biografia or "")})


def nombre_de_fila(texto: str) -> str:
    """«Abades Martínez,Cristina» → «Abades Martínez, Cristina».

    El fichero de declaraciones escribe la coma sin espacio y el de diputados
    con él; la ficha es la misma y tiene que llamarse igual.
    """
    return re.sub(r"\s*,\s*", ", ", " ".join(str(texto or "").split()))


def _texto(valor: Any) -> str:
    return " ".join(str(valor or "").split())


def _fecha(texto: str) -> date | None:
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", (texto or "").strip())
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


class CongresoConnector:
    """Diputados de cada legislatura, con su formación y su grupo."""

    source_id = "congreso"
    extractor_version = "congreso-diputados/2"

    def __init__(self, cliente: httpx.Client | None = None, desde_legislatura: int = 9) -> None:
        self._cliente = cliente
        # Desde la IX (2008): los gobiernos que cubre el BOE que se lee
        # (desde 2011) y la legislatura anterior, de la que vienen muchos de
        # sus altos cargos.
        self._desde = desde_legislatura

    def fetch(self, **_: Any) -> Iterator[RawDocument]:
        cliente = self._cliente or httpx.Client(
            timeout=60.0,
            follow_redirects=True,
            headers={"User-Agent": "Sinapsis/0.1 (proyecto abierto de transparencia)"},
        )
        propio = self._cliente is None
        try:
            try:
                r = cliente.get(PORTADA)
                r.raise_for_status()
            except httpx.HTTPError as exc:
                log.warning("congreso: la página de datos abiertos no responde", detalle=str(exc))
                return
            enlaces = sorted(
                {
                    str(httpx.URL(PORTADA).join(h.replace("&amp;", "&")))
                    for h in re.findall(r'href="([^"]+\.json)"', r.text)
                }
            )
            numeradas = {int(m.group(1)): u for u in enlaces if (m := _POR_LEGISLATURA.search(u))}
            if not numeradas:
                log.warning("congreso: la página ya no enlaza los ficheros por legislatura")
                return
            # La legislatura en curso no tiene fichero numerado: es la
            # siguiente a la última que lo tiene.
            en_curso = max(numeradas) + 1
            pedidos = [(n, u) for n, u in sorted(numeradas.items()) if n >= self._desde]
            pedidos += [(en_curso, u) for u in enlaces if _EN_CURSO.search(u)]
            # Las declaraciones de actividades son de la legislatura en curso.
            pedidos += [(en_curso, u) for u in enlaces if _DECLARACIONES.search(u)]
            for n, url in pedidos:
                try:
                    x = cliente.get(url)
                    x.raise_for_status()
                except httpx.HTTPError as exc:
                    log.warning("congreso: fichero no disponible", url=url, detalle=str(exc))
                    continue
                yield RawDocument(
                    source_id=self.source_id,
                    url=url,
                    content=x.content,
                    media_type="application/json",
                    retrieved_at=datetime.now(UTC),
                    metadata={
                        "legislatura": n,
                        **({"tipo": "declaraciones"} if _DECLARACIONES.search(url) else {}),
                    },
                )
                time.sleep(0.3)
        finally:
            if propio:
                cliente.close()

    def parse(self, raw: RawDocument) -> Iterator[ParsedRecord]:
        if raw.metadata.get("tipo") == "declaraciones" or _DECLARACIONES.search(raw.url):
            yield from self._parse_declaraciones(raw)
            return
        n = raw.metadata.get("legislatura")
        if n is None:
            m = _POR_LEGISLATURA.search(raw.url)
            n = int(m.group(1)) if m else None
        if n is None:
            log.warning("congreso: no se sabe de qué legislatura es", url=raw.url)
            return
        try:
            filas = json.loads(raw.content.decode("utf-8-sig"))
        except ValueError as exc:
            log.warning("congreso: el fichero no es JSON", url=raw.url, detalle=str(exc))
            return
        if not isinstance(filas, list):
            log.warning("congreso: el JSON no es una lista", url=raw.url)
            return
        for i, f in enumerate(filas):
            if not isinstance(f, dict) or not f.get("NOMBRE"):
                continue
            yield ParsedRecord(
                raw_content_hash=raw.content_hash,
                extractor_version=self.extractor_version,
                data={
                    "id_registro": f"{raw.url}#{i}",
                    "url": raw.url,
                    "legislatura": int(n),
                    "nombre": nombre_de_fila(f["NOMBRE"]),
                    "circunscripcion": f.get("CIRCUNSCRIPCION") or "",
                    "formacion": f.get("FORMACIONELECTORAL") or "",
                    "grupo": f.get("GRUPOPARLAMENTARIO") or "",
                    "alta": f.get("FECHAALTA") or f.get("FECHACONDICIONPLENA") or "",
                    "baja": f.get("FECHABAJA") or "",
                    # De la biografía, sólo los cargos públicos que menciona.
                    "cargos_en_biografia": cargos_en_biografia(f.get("BIOGRAFIA") or ""),
                },
            )

    def _parse_declaraciones(self, raw: RawDocument) -> Iterator[ParsedRecord]:
        """Sólo las filas de ACTIVIDAD; lo demás de la declaración se descarta."""
        try:
            filas = json.loads(raw.content.decode("utf-8-sig"))
        except ValueError as exc:
            log.warning("congreso: las declaraciones no son JSON", url=raw.url, detalle=str(exc))
            return
        if not isinstance(filas, list):
            log.warning("congreso: las declaraciones no son una lista", url=raw.url)
            return
        for i, f in enumerate(filas):
            if not isinstance(f, dict) or not f.get("NOMBRE"):
                continue
            if _texto(f.get("TIPO")).upper() != "ACTIVIDAD":
                continue
            empleador = _texto(f.get("EMPLEADOR"))
            descripcion = _texto(f.get("DESCRIPCION"))
            # Sin empleador ni descripción no hay nada que decir.
            if not empleador and not descripcion:
                continue
            yield ParsedRecord(
                raw_content_hash=raw.content_hash,
                extractor_version=self.extractor_version,
                data={
                    "id_registro": f"{raw.url}#{i}",
                    "url": raw.url,
                    "tipo": "actividad",
                    "nombre": nombre_de_fila(f["NOMBRE"]),
                    "empleador": empleador,
                    "sector": _texto(f.get("SECTOR")),
                    "periodo": _texto(f.get("PERIODO")),
                    "descripcion": descripcion,
                    "fecha_registro": _texto(f.get("FECHAREGISTRO")),
                },
            )

    def _normalizar_actividad(self, d: dict[str, Any]) -> Normalizado | None:
        """diputado --UnknownLink(actividad_declarada)--> para quién trabajó.

        El destino es el texto que declaró, tal cual: no se interpreta como
        una sociedad concreta. Que lo sea lo decide el volcado, y sólo con la
        denominación completa (exportar_cargos.empresa_en).
        """
        if not d.get("nombre"):
            return None
        # Otra vez aquí, y no sólo al leer: la clave de la ficha depende de
        # la coma, y la del mandato tiene que ser la misma.
        d = {**d, "nombre": nombre_de_fila(d["nombre"])}
        destino = d.get("empleador") or d.get("descripcion") or ""
        clave_persona = f"congreso:persona:{clave(d['nombre'])}"
        clave_destino = f"congreso:empleador:{clave(destino)}"
        # La misma actividad repetida en una modificación de la declaración
        # es la misma arista: la huella no lleva la fecha de registro.
        huella = hashlib.sha256(
            "|".join(
                [d.get("empleador", ""), d.get("periodo", ""), d.get("descripcion", "")]
            ).encode("utf-8")
        ).hexdigest()[:12]
        registrada = _fecha(d.get("fecha_registro", ""))
        return Normalizado(
            entidades=[
                EntidadNormalizada(
                    ftm_schema="Person",
                    caption=d["nombre"],
                    dedupe_key=clave_persona,
                    country="es",
                    properties={
                        "name": d["nombre"],
                        "cargo_publico": True,
                        "nombreParaCruzar": nombre_para_cruzar(d["nombre"]),
                    },
                ),
                EntidadNormalizada(
                    ftm_schema="Organization",
                    caption=destino,
                    dedupe_key=clave_destino,
                    country="es",
                    properties={"name": destino, "textoDeclarado": True},
                ),
            ],
            aristas=[
                AristaNormalizada(
                    ftm_schema="UnknownLink",
                    source_key=clave_persona,
                    target_key=clave_destino,
                    dedupe_key=f"congreso:actividad:{clave(d['nombre'])}:{huella}",
                    confidence=1.0,
                    properties={
                        "relacion": "actividad_declarada",
                        "empleador": d.get("empleador", ""),
                        "sector": d.get("sector", ""),
                        "periodo": d.get("periodo", ""),
                        "descripcion": d.get("descripcion", ""),
                        **({"fechaRegistro": registrada.isoformat()} if registrada else {}),
                        "url": d.get("url", ""),
                    },
                )
            ],
        )

    def normalize(self, record: ParsedRecord) -> Normalizado | None:
        d = record.data
        if d.get("tipo") == "actividad":
            return self._normalizar_actividad(d)
        alta = _fecha(d.get("alta", ""))
        baja = _fecha(d.get("baja", ""))
        if not d.get("nombre") or alta is None:
            return None
        d = {**d, "nombre": nombre_de_fila(d["nombre"])}
        if baja is not None and baja < alta:
            baja = None
        leg = romano(d["legislatura"])
        clave_persona = f"congreso:persona:{clave(d['nombre'])}"
        clave_escano = f"congreso:escano:{d['legislatura']}"
        # «Escaño», no «Diputado»: el fichero no dice si es diputado o
        # diputada, y el BOE sí escribe cada cargo con el género de quien lo
        # ocupa. Mejor una palabra neutra que acertar la mitad de las veces.
        entidades = [
            EntidadNormalizada(
                ftm_schema="Person",
                caption=d["nombre"],
                dedupe_key=clave_persona,
                country="es",
                properties={
                    "name": d["nombre"],
                    "cargo_publico": True,
                    "nombreParaCruzar": nombre_para_cruzar(d["nombre"]),
                    **(
                        {"cargosEnBiografia": d["cargos_en_biografia"]}
                        if d.get("cargos_en_biografia")
                        else {}
                    ),
                },
            ),
            EntidadNormalizada(
                ftm_schema="Position",
                caption=f"Escaño en la {leg} legislatura",
                dedupe_key=clave_escano,
                country="es",
                properties={"name": f"Escaño en la {leg} legislatura"},
            ),
        ]
        arista = AristaNormalizada(
            ftm_schema="Occupancy",
            source_key=clave_persona,
            target_key=clave_escano,
            dedupe_key=(
                f"congreso:mandato:{d['legislatura']}:{clave(d['nombre'])}:{d.get('alta', '')}"
            ),
            confidence=1.0,
            start_date=alta,
            end_date=baja,
            properties={
                "acto": "mandato",
                "cargo": f"Escaño en la {leg} legislatura",
                "legislatura": leg,
                "formacion": d.get("formacion", ""),
                "grupo": d.get("grupo", ""),
                "circunscripcion": d.get("circunscripcion", ""),
                "url": d.get("url", ""),
                # También en cada mandato, y no sólo en la persona: la ficha
                # es una para todas las legislaturas y la biografía de la
                # última taparía lo que decía la de otra.
                **(
                    {"cargosEnBiografia": d["cargos_en_biografia"]}
                    if d.get("cargos_en_biografia")
                    else {}
                ),
            },
        )
        return Normalizado(entidades=entidades, aristas=[arista])


def crear() -> CongresoConnector:
    return CongresoConnector()
