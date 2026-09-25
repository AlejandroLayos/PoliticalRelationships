"""BOE: nombramientos y ceses de altos cargos, por Real Decreto.

    persona --Occupancy--> puesto --UnknownLink--> departamento

Es la primera pieza de las puertas giratorias (spec §15, fase 7): quién ocupó
qué cargo y cuándo, con el BOE como prueba. La regla de §12 manda y se aplica
aquí antes que en ningún otro sitio: **sólo se descarga y se guarda lo que es
un alto cargo**. Un fiscal o un magistrado nombrados por Real Decreto no
llegan a la base; no hace falta taparlos después.

## El sumario encuentra; la disposición prueba

El sumario diario de la API de datos abiertos lista todo lo publicado ese día.
De ahí se sacan los candidatos —sección II.A, Real Decreto, nombramiento o
cese de un alto cargo—, y de cada uno se baja **su XML**, que es lo que se
guarda como crudo. Cada acto queda así atado a su propia disposición, con su
identificador BOE-A-…, y no a un índice de 300 KB con todo lo del día.

## Cada acto es una arista

Un nombramiento y un cese son dos hechos, publicados en dos disposiciones, a
veces con años de diferencia. Aquí se guardan tal cual: una `Occupancy` por
disposición, con la fecha de entrada o la de salida. Juntarlos en periodos es
cosa del volcado, que los ve todos a la vez.

La alternativa —una arista por persona y puesto, rellenando `start_date` y
`end_date` según llegan— se equivoca en un caso que no es raro: al formarse
un gobierno, los secretarios de Estado cesan y se les vuelve a nombrar en el
mismo cargo. Con una sola arista el segundo nombramiento se pierde y alguien
en activo aparecería como ex alto cargo.

## El histórico y la caché

El BOE no cambia: lo publicado un día sigue igual para siempre. Por eso cada
día leído se guarda en disco (`cache`), y la siguiente ejecución no vuelve a
pedirlo. El trabajo nocturno reconstruye la base de cero y sin caché tendría
que pedir quince años de sumarios cada noche, que ni cabe en el tiempo ni es
forma de tratar a un servicio público.

`max_dias_nuevos` acota cuántos días SIN caché se piden en una ejecución: el
histórico se va completando noche a noche, de lo reciente hacia atrás, en vez
de en una sola carrera que agotaría el tiempo del trabajo.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import unicodedata
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import structlog

from sinapsis_ingest.cargos import (
    es_alto_cargo,
    leer_cuerpo,
    leer_titulo,
    organismo_del_acto,
    puesto,
    separar_cargos,
    tipo_colectivo,
)
from sinapsis_ingest.connectors.base import ParsedRecord, RawDocument
from sinapsis_ingest.normalizado import AristaNormalizada, EntidadNormalizada, Normalizado

log = structlog.get_logger()

API = "https://www.boe.es/datosabiertos/api/boe/sumario"
WEB = "https://www.boe.es"

CABECERAS = {
    "Accept": "application/json",
    "User-Agent": (
        "Sinapsis/0.1 (proyecto abierto de transparencia; "
        "+https://github.com/AlejandroLayos/PoliticalRelationships)"
    ),
}


def clave(texto: str) -> str:
    """La parte variable de una clave: sin tildes, sin mayúsculas, con hash.

    No es `util.slug`, y por dos motivos que se ven en el BOE. Uno: `slug`
    se come las letras con tilde («hern-ndez»), y la clave sale en la
    dirección de la web. Dos: el hash de `slug` va sobre el texto exacto, y
    el BOE escribe el mismo puesto como «Directora General» y «Directora
    general» según el día. Aquí el hash va sobre la forma normalizada, así
    que las dos grafías son un solo puesto —y un nombre escrito con y sin
    tilde, una sola persona—, pero dos textos con letras distintas nunca
    colapsan.
    """
    plano = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if unicodedata.category(c) != "Mn"
    ).lower()
    plano = re.sub(r"\s+", " ", plano).strip()
    base = re.sub(r"[^a-z0-9]+", "-", plano).strip("-")[:60]
    return f"{base}-{hashlib.sha256(plano.encode('utf-8')).hexdigest()[:8]}"


def como_lista(x: Any) -> list[Any]:
    """La API devuelve un objeto cuando hay uno y una lista cuando hay varios."""
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def items_2a(sumario: dict[str, Any]) -> list[dict[str, Any]]:
    """Los ítems de la sección II.A, con su departamento al lado.

    La forma la confirmó el reconocimiento (`docs/fuentes/boe-reconocimiento.md`):
    data.sumario.diario[].seccion[].departamento[].epigrafe[].item[], y a veces
    el ítem cuelga directamente del departamento, sin epígrafe.
    """
    salida = []
    datos = sumario.get("data") or {}
    for diario in como_lista((datos.get("sumario") or {}).get("diario")):
        for seccion in como_lista(diario.get("seccion")):
            if str(seccion.get("codigo", "")).upper() != "2A":
                continue
            for dep in como_lista(seccion.get("departamento")):
                nombre_dep = dep.get("nombre") or ""
                for ep in como_lista(dep.get("epigrafe")):
                    for it in como_lista(ep.get("item")):
                        salida.append({**it, "_departamento": nombre_dep})
                for it in como_lista(dep.get("item")):
                    salida.append({**it, "_departamento": nombre_dep})
    return salida


def es_candidato(item: dict[str, Any]) -> bool:
    """¿Merece la pena bajar esta disposición?

    Sólo se baja lo que ya por el título es un acto de UNA persona sobre UN
    alto cargo. Lo demás no llega a la base: minimizar es no guardar, no
    guardar y luego esconder.
    """
    titulo = item.get("titulo") or ""
    acto = leer_titulo(titulo)
    if acto is not None:
        return any(es_alto_cargo(c) for c in separar_cargos(acto.cargo))
    # Los que forman o disuelven un gobierno: los nombres van en el cuerpo, y
    # son ministros.
    return tipo_colectivo(titulo) is not None


class BOEConnector:
    """Altos cargos nombrados y cesados por Real Decreto."""

    source_id = "boe"
    extractor_version = "boe-cargos/2"

    def __init__(
        self,
        cliente: httpx.Client | None = None,
        cache: Path | None = None,
        max_dias_nuevos: int | None = None,
        pausa: float = 0.3,
        tope_segundos: float | None = None,
    ) -> None:
        self._cliente = cliente
        self._cache = cache
        self._max_dias_nuevos = max_dias_nuevos
        self._pausa = pausa
        # Tiempo de red de una ejecución. Pasado, no se piden más días: lo que
        # queda se lee de la caché y el resto, la noche siguiente. Es para
        # terminar ANTES de que el trabajo nocturno corte el paso, que es
        # peor: un corte a mitad no da tiempo a nada.
        self._tope = tope_segundos
        self._inicio = time.monotonic()

    # --- caché ------------------------------------------------------------

    def _ruta(self, *partes: str) -> Path | None:
        if self._cache is None:
            return None
        ruta = self._cache.joinpath(*partes)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        return ruta

    def _candidatos_del_dia(
        self, cliente: httpx.Client, dia: date, nuevos: list[int]
    ) -> list[dict[str, Any]] | None:
        """Los ítems de la II.A de un día, de la caché o de la API.

        Se guardan TODOS los de la II.A por Real Decreto, no sólo los que hoy
        pasan el filtro: si mañana se afina `es_alto_cargo`, la caché sigue
        sirviendo sin volver a pedir el día.

        `None` si el día no se pudo leer ni está en caché (o se agotó el cupo
        de días nuevos). Un día sin BOE —domingos, festivos— se guarda como
        lista vacía, para no volver a preguntar.
        """
        clave = dia.strftime("%Y%m%d")
        ruta = self._ruta("sumarios", clave[:4], f"{clave}.json")
        if ruta is not None and ruta.exists():
            return json.loads(ruta.read_text(encoding="utf-8"))

        if self._max_dias_nuevos is not None and nuevos[0] >= self._max_dias_nuevos:
            return None
        if self._tope is not None and time.monotonic() - self._inicio > self._tope:
            return None
        nuevos[0] += 1

        try:
            r = cliente.get(f"{API}/{clave}")
        except httpx.HTTPError as exc:
            log.warning("boe: sumario no disponible", dia=clave, detalle=str(exc))
            return None
        if r.status_code == 404:
            items: list[dict[str, Any]] = []
        elif r.status_code != 200:
            log.warning("boe: sumario con error", dia=clave, codigo=r.status_code)
            return None
        else:
            try:
                items = [
                    i
                    for i in items_2a(r.json())
                    if (i.get("titulo") or "").startswith("Real Decreto")
                ]
            except ValueError:
                log.warning("boe: el sumario no es JSON", dia=clave)
                return None
        if ruta is not None:
            ruta.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
        time.sleep(self._pausa)
        return items

    def _disposicion(self, cliente: httpx.Client, item: dict[str, Any]) -> bytes | None:
        identificador = item.get("identificador") or ""
        url = item.get("url_xml") or f"{WEB}/diario_boe/xml.php?id={identificador}"
        ruta = self._ruta("disposiciones", identificador[6:10] or "x", f"{identificador}.xml")
        if ruta is not None and ruta.exists():
            return ruta.read_bytes()
        try:
            r = cliente.get(url, headers={"User-Agent": CABECERAS["User-Agent"]})
            r.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("boe: disposición no disponible", id=identificador, detalle=str(exc))
            return None
        if b"<documento" not in r.content[:2000]:
            log.warning("boe: la disposición no es el XML esperado", id=identificador)
            return None
        if ruta is not None:
            ruta.write_bytes(r.content)
        time.sleep(self._pausa)
        return r.content

    # --- fetch ------------------------------------------------------------

    def fetch(
        self,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        **_: Any,
    ) -> Iterator[RawDocument]:
        """Recorre los días de lo más reciente a lo más antiguo.

        Al revés que el calendario a propósito: si el cupo de días nuevos se
        agota, lo que queda sin leer es lo más viejo, y lo reciente —que es lo
        que más se consulta— ya está.
        """
        hasta = fecha_hasta or datetime.now(UTC).date()
        desde = fecha_desde or hasta - timedelta(days=30)

        cliente = self._cliente or httpx.Client(
            timeout=60.0, follow_redirects=True, headers=CABECERAS
        )
        propio = self._cliente is None
        self._inicio = time.monotonic()
        nuevos = [0]
        sin_leer = 0
        try:
            dia = hasta
            while dia >= desde:
                items = self._candidatos_del_dia(cliente, dia, nuevos)
                if items is None:
                    sin_leer += 1
                else:
                    for item in items:
                        if not es_candidato(item):
                            continue
                        contenido = self._disposicion(cliente, item)
                        if contenido is None:
                            continue
                        yield RawDocument(
                            source_id=self.source_id,
                            url=item.get("url_xml")
                            or f"{WEB}/diario_boe/xml.php?id={item.get('identificador')}",
                            content=contenido,
                            media_type="application/xml",
                            retrieved_at=datetime.now(UTC),
                            metadata={
                                "fecha_sumario": dia.isoformat(),
                                "departamento_sumario": item.get("_departamento") or "",
                            },
                        )
                dia -= timedelta(days=1)
        finally:
            if propio:
                cliente.close()
        if sin_leer:
            # Un hueco que se dice: lo pendiente se lee en la próxima ejecución.
            log.warning("boe: días sin leer en esta ejecución", dias=sin_leer)

    # --- parse ------------------------------------------------------------

    def parse(self, raw: RawDocument) -> Iterator[ParsedRecord]:
        try:
            raiz = ET.fromstring(raw.content)
        except ET.ParseError as exc:
            log.warning("boe: XML ilegible", url=raw.url, detalle=str(exc))
            return
        meta = raiz.find("metadatos")
        if meta is None:
            log.warning("boe: el XML no trae metadatos", url=raw.url)
            return

        def texto(etiqueta: str) -> str:
            nodo = meta.find(etiqueta)
            return (nodo.text or "").strip() if nodo is not None else ""

        identificador = texto("identificador")
        titulo = texto("titulo")
        if not identificador:
            return

        acto = leer_titulo(titulo)
        if acto is not None:
            # «Vicepresidenta del Gobierno y Ministra de…» son dos cargos.
            actos = [replace(acto, cargo=c) for c in separar_cargos(acto.cargo)]
        else:
            # Colectivo: los nombres están en el cuerpo, párrafo a párrafo.
            nodo_texto = raiz.find("texto")
            parrafos = (
                ["".join(p.itertext()) for p in nodo_texto.findall("p")]
                if nodo_texto is not None
                else []
            )
            actos = leer_cuerpo(titulo, parrafos)
            if tipo_colectivo(titulo) and not actos:
                log.warning("boe: Real Decreto colectivo sin ningún acto leído", id=identificador)

        comun = {
            "identificador": identificador,
            "titulo": titulo,
            "departamento": texto("departamento") or raw.metadata.get("departamento_sumario", ""),
            "fecha_publicacion": texto("fecha_publicacion"),
            "fecha_disposicion": texto("fecha_disposicion"),
            "rango": texto("rango"),
        }
        for n, a in enumerate(a for a in actos if es_alto_cargo(a.cargo)):
            yield ParsedRecord(
                raw_content_hash=raw.content_hash,
                extractor_version=self.extractor_version,
                data={
                    **comun,
                    "id_registro": f"{identificador}#{n}",
                    "tipo": a.tipo,
                    "cargo": a.cargo,
                    "nombre": a.nombre,
                    "numero": a.numero,
                    "motivo": a.motivo,
                },
            )

    # --- normalize --------------------------------------------------------

    def normalize(self, record: ParsedRecord) -> Normalizado | None:
        d = record.data
        fecha = _fecha_boe(d.get("fecha_publicacion", ""))
        if fecha is None or not d.get("nombre") or not d.get("cargo"):
            return None

        nombre_puesto = puesto(d["cargo"])
        departamento = organismo_del_acto(d.get("departamento", "").strip(), d["cargo"])

        clave_persona = f"boe:persona:{clave(d['nombre'])}"
        clave_puesto = f"boe:puesto:{clave(nombre_puesto)}"
        entidades = [
            EntidadNormalizada(
                ftm_schema="Person",
                caption=d["nombre"],
                dedupe_key=clave_persona,
                country="es",
                # La marca que abre la puerta del volcado. No basta sola: el
                # volcado exige además la clave `boe:persona:`, que sólo pone
                # este conector, y que la persona tenga un acto del BOE.
                properties={"name": d["nombre"], "cargo_publico": True},
            ),
            EntidadNormalizada(
                ftm_schema="Position",
                caption=nombre_puesto,
                dedupe_key=clave_puesto,
                country="es",
                properties={"name": nombre_puesto},
            ),
        ]

        propiedades_acto = {
            "acto": d["tipo"],
            "cargo": d["cargo"],
            "boe": d["identificador"],
            "url": f"{WEB}/diario_boe/txt.php?id={d['identificador']}",
            "realDecreto": d.get("numero", ""),
            # El organismo del acto, y no el del puesto: el mismo puesto pasa
            # de un ministerio a otro en cada reorganización del Gobierno.
            **({"departamento": departamento} if departamento else {}),
            **({"fechaDisposicion": d["fecha_disposicion"]} if d.get("fecha_disposicion") else {}),
            **({"motivo": d["motivo"]} if d.get("motivo") else {}),
        }
        aristas = [
            AristaNormalizada(
                ftm_schema="Occupancy",
                source_key=clave_persona,
                target_key=clave_puesto,
                # Una disposición puede traer varios actos —un gobierno entero,
                # o dos cargos de una misma persona—: la clave los distingue.
                dedupe_key=f"boe:{d['identificador']}:{clave(d['nombre'])}:{clave(nombre_puesto)}",
                confidence=1.0,
                status="asserted",
                start_date=fecha if d["tipo"] == "nombramiento" else None,
                end_date=fecha if d["tipo"] == "cese" else None,
                properties=propiedades_acto,
            )
        ]

        if departamento:
            clave_dep = f"boe:departamento:{clave(departamento)}"
            entidades.append(
                EntidadNormalizada(
                    ftm_schema="PublicBody",
                    caption=departamento,
                    dedupe_key=clave_dep,
                    country="es",
                    properties={"name": departamento, "jerarquia_boe": [departamento]},
                )
            )
            aristas.append(
                AristaNormalizada(
                    ftm_schema="UnknownLink",
                    source_key=clave_puesto,
                    target_key=clave_dep,
                    dedupe_key=f"boe:puesto-en:{clave(nombre_puesto)}:{clave(departamento)}",
                    confidence=1.0,
                    status="asserted",
                    properties={"relacion": "puesto en"},
                )
            )
        return Normalizado(entidades=entidades, aristas=aristas)


def _fecha_boe(valor: str) -> date | None:
    """Las fechas del BOE vienen como AAAAMMDD."""
    try:
        return datetime.strptime(valor.strip(), "%Y%m%d").date()
    except ValueError:
        return None


def crear() -> BOEConnector:
    import os

    cache = os.environ.get("SINAPSIS_CACHE_BOE")
    tope = os.environ.get("SINAPSIS_BOE_MAX_DIAS_NUEVOS")
    minutos = os.environ.get("SINAPSIS_BOE_TOPE_MINUTOS")
    return BOEConnector(
        cache=Path(cache) if cache else None,
        max_dias_nuevos=int(tope) if tope else None,
        tope_segundos=float(minutos) * 60 if minutos else None,
    )
