"""Autorizaciones de actividad privada tras el cese de altos cargos.

    ex alto cargo (Person) --Occupancy--> puesto (Position)     hasta el cese
    ex alto cargo (Person) --UnknownLink--> actividad autorizada

Es la fuente que AFIRMA una puerta giratoria (spec §12): la Oficina de
Conflictos de Intereses autoriza —o no— a quien deja un alto cargo a trabajar
en el sector privado en los dos años siguientes (Ley 3/2015, art. 15), y el
Portal de Transparencia publica las autorizaciones. Que «X, ex ministra de
Empleo, fue autorizada a ser consejera de Y» lo dice un documento oficial.

Lo que NO dice, y por eso no se escribe en ninguna parte: que la persona
llegara a ocupar el puesto, ni nada sobre su actuación en el cargo. Una
autorización es una autorización.

## La forma

La verificó el reconocimiento (`docs/fuentes/oci-reconocimiento.md`): una
tabla HTML con estas columnas, en este orden, y fechas `aaaa/mm/dd`:

    Nombre | Alto Cargo | Ministerio | Fecha de Cese |
    Empresa/Actividad autorizada | Fecha de autorización

El nombre viene como «APELLIDOS, NOMBRE» en mayúsculas, y no siempre bien:
«LORA-TAMAYO, D'OCON» no trae nombre de pila. Por eso se publica en el orden
en que viene y no se reordena: darle la vuelta inventaría un nombre.
"""

from __future__ import annotations

import re
import time
import unicodedata
from collections.abc import Iterator
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from typing import Any

import httpx
import structlog

from sinapsis_ingest.connectors.base import ParsedRecord, RawDocument
from sinapsis_ingest.connectors.boe import clave
from sinapsis_ingest.normalizado import AristaNormalizada, EntidadNormalizada, Normalizado

log = structlog.get_logger()

BASE = "https://transparencia.gob.es"
PAGINAS = (f"{BASE}/publicidad-activa/por-materias/altos-cargos/actividad-privada-cese",)

COLUMNAS = (
    "nombre",
    "alto cargo",
    "ministerio",
    "fecha de cese",
    "empresa/actividad autorizada",
    "fecha de autorizacion",
)


def _plano(texto: str) -> str:
    sin = "".join(
        c for c in unicodedata.normalize("NFKD", texto or "") if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", sin.lower()).strip()


class _Tablas(HTMLParser):
    """Las tablas de una página, con el enlace de la primera celda."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tablas: list[list[list[str]]] = []
        self.enlaces: list[list[str]] = []
        self._fila: list[str] | None = None
        self._celda: list[str] | None = None
        self._enlace_fila = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self.tablas.append([])
            self.enlaces.append([])
        elif tag == "tr" and self.tablas:
            self._fila, self._enlace_fila = [], ""
        elif tag in ("td", "th") and self._fila is not None:
            self._celda = []
        elif tag == "a" and self._celda is not None and not self._enlace_fila:
            self._enlace_fila = dict(attrs).get("href") or ""

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._celda is not None and self._fila is not None:
            self._fila.append(" ".join("".join(self._celda).split()))
            self._celda = None
        elif tag == "tr" and self._fila is not None and self.tablas:
            if self._fila:
                self.tablas[-1].append(self._fila)
                self.enlaces[-1].append(self._enlace_fila)
            self._fila = None

    def handle_data(self, data: str) -> None:
        if self._celda is not None:
            self._celda.append(data)


def _fecha(texto: str) -> date | None:
    """Las dos formas que usa la fuente, sin confundirlas.

    Las páginas de seguimiento escriben «2018/06/01» (año delante) y el
    buscador «24/09/2025» (día delante). Con el año de cuatro cifras en un
    extremo no hay ambigüedad; cualquier otra cosa no se interpreta.
    """
    t = (texto or "").strip()
    m = re.fullmatch(r"(\d{4})/(\d{1,2})/(\d{1,2})", t)
    if m:
        anio, mes, dia = m.groups()
    else:
        m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", t)
        if not m:
            return None
        dia, mes, anio = m.groups()
    try:
        return date(int(anio), int(mes), int(dia))
    except ValueError:
        return None


_PARTICULAS = {"de", "del", "la", "las", "los", "y", "i"}
_TRAS_SEPARADOR = re.compile(r"(^|[-'\u2019\u00b4])(\w)")


def en_minusculas(texto: str) -> str:
    """«ROSA CORDON, RUFINO DE LA» → «Rosa Cordon, Rufino de la».

    Sólo la caja: ni se reordena ni se añade una tilde que la fuente no puso.
    """
    palabras = []
    for p in texto.split(" "):
        bajo = p.lower()
        if bajo in _PARTICULAS:
            palabras.append(bajo)
            continue
        # Mayúscula tras guion y apóstrofo —recto, curvo o el acento agudo
        # suelto que usa la fuente—: «Lora-Tamayo», «D'Ocon».
        palabras.append(_TRAS_SEPARADOR.sub(lambda m: m.group(1) + m.group(2).upper(), bajo))
    return " ".join(palabras)


def nombre_para_cruzar(nombre_fuente: str) -> str:
    """«BAÑEZ GARCIA, FATIMA» → «fatima banez garcia», normalizado.

    SÓLO para buscar coincidencias con el BOE, nunca para enseñarlo: si la
    fuente trae mal el nombre, el reordenado también está mal, y lo único que
    pasa es que no coincide con nada.
    """
    if "," not in nombre_fuente:
        return _plano(nombre_fuente)
    apellidos, nombre = (x.strip() for x in nombre_fuente.split(",", 1))
    # «ROSA CORDON, RUFINO DE LA»: las partículas del final son del apellido.
    partes = nombre.split()
    cola = []
    while partes and partes[-1].lower() in _PARTICULAS:
        cola.insert(0, partes.pop())
    return _plano(" ".join([*partes, *cola, apellidos]))


def _cabecera(celda: str) -> str:
    """Una cabecera, como para compararla.

    El buscador del portal escribe «Empresa / Atividad autorizada» —espacios
    alrededor de la barra, y la errata tal cual—, y las páginas de
    seguimiento «Empresa/Actividad autorizada». Son la misma columna.
    """
    c = re.sub(r"\s*/\s*", "/", _plano(celda))
    return c.replace("atividad", "actividad")


def leer_tablas(html: str) -> list[dict[str, Any]]:
    """Las filas de las tablas de autorizaciones de una página.

    Se reconoce la tabla por sus cabeceras, no por su posición: la página
    lleva otras tablas («Fuente de los datos»). Una tabla cuyas cabeceras no
    son éstas no se lee. El buscador pinta la misma tabla dos veces —para
    pantalla ancha y estrecha—: una fila repetida es la misma autorización.
    """
    lector = _Tablas()
    lector.feed(html)
    filas: list[dict[str, Any]] = []
    vistas: set[tuple[str, ...]] = set()
    for tabla, enlaces in zip(lector.tablas, lector.enlaces, strict=True):
        if not tabla or tuple(_cabecera(c) for c in tabla[0]) != COLUMNAS:
            continue
        for celdas, enlace in zip(tabla[1:], enlaces[1:], strict=True):
            if len(celdas) != len(COLUMNAS) or not celdas[0] or not celdas[4]:
                continue
            # El pie de la tabla repite la cabecera.
            if tuple(_cabecera(c) for c in celdas) == COLUMNAS:
                continue
            if tuple(celdas) in vistas:
                continue
            vistas.add(tuple(celdas))
            filas.append(
                {
                    "nombre": celdas[0],
                    "cargo": celdas[1],
                    "ministerio": celdas[2],
                    "fecha_cese": celdas[3],
                    "actividad": celdas[4],
                    "fecha_autorizacion": celdas[5],
                    "curriculum": enlace,
                }
            )
    return filas


class OCIConnector:
    """Lee las autorizaciones que publica el Portal de Transparencia."""

    source_id = "oci"
    extractor_version = "oci-autorizaciones/1"

    def __init__(self, cliente: httpx.Client | None = None, paginas: tuple[str, ...] = PAGINAS):
        self._cliente = cliente
        self._paginas = paginas

    def fetch(self, **_: Any) -> Iterator[RawDocument]:
        """Las páginas con tablas de autorizaciones. Sin rango de fechas: la
        fuente publica listas acumuladas, y la idempotencia la da el hash."""
        cliente = self._cliente or httpx.Client(
            timeout=60.0,
            follow_redirects=True,
            headers={"User-Agent": "Sinapsis/0.1 (proyecto abierto de transparencia)"},
        )
        propio = self._cliente is None
        try:
            for url in self._paginas:
                try:
                    r = cliente.get(url)
                    r.raise_for_status()
                except httpx.HTTPError as exc:
                    log.warning("oci: página no disponible", url=url, detalle=str(exc))
                    continue
                if not leer_tablas(r.text):
                    log.warning("oci: la página no trae la tabla esperada", url=url)
                yield RawDocument(
                    source_id=self.source_id,
                    url=url,
                    content=r.content,
                    media_type="text/html",
                    retrieved_at=datetime.now(UTC),
                )
                time.sleep(0.5)
        finally:
            if propio:
                cliente.close()

    def parse(self, raw: RawDocument) -> Iterator[ParsedRecord]:
        html = raw.content.decode("utf-8", errors="replace")
        for n, fila in enumerate(leer_tablas(html)):
            yield ParsedRecord(
                raw_content_hash=raw.content_hash,
                extractor_version=self.extractor_version,
                data={**fila, "id_registro": f"{raw.url}#{n}", "url": raw.url},
            )

    def normalize(self, record: ParsedRecord) -> Normalizado | None:
        d = record.data
        cese = _fecha(d.get("fecha_cese", ""))
        autorizacion = _fecha(d.get("fecha_autorizacion", ""))
        if not d.get("nombre") or not d.get("cargo") or not d.get("actividad"):
            return None

        nombre = en_minusculas(d["nombre"])
        clave_persona = f"oci:persona:{clave(d['nombre'])}"
        clave_puesto = f"oci:puesto:{clave(d['cargo'])}"
        clave_actividad = f"oci:actividad:{clave(d['actividad'])}"
        curriculum = d.get("curriculum") or ""
        if curriculum.startswith("/"):
            curriculum = BASE + curriculum

        entidades = [
            EntidadNormalizada(
                ftm_schema="Person",
                caption=nombre,
                dedupe_key=clave_persona,
                country="es",
                # La misma marca que el BOE: la regla de §12 deja publicar a
                # quien la Oficina de Conflictos de Intereses trata como ex
                # alto cargo, y sólo en ese papel.
                properties={
                    "name": nombre,
                    "cargo_publico": True,
                    "nombreParaCruzar": nombre_para_cruzar(d["nombre"]),
                },
            ),
            EntidadNormalizada(
                ftm_schema="Position",
                caption=d["cargo"],
                dedupe_key=clave_puesto,
                country="es",
                properties={"name": d["cargo"], "ministerio": d.get("ministerio", "")},
            ),
            EntidadNormalizada(
                ftm_schema="Organization",
                caption=d["actividad"],
                dedupe_key=clave_actividad,
                country="es",
                # No es una organización identificada: es el texto de la
                # autorización, que a veces nombra una empresa y a veces dice
                # «economista por cuenta propia». Se guarda tal cual.
                properties={"name": d["actividad"], "textoDeAutorizacion": True},
            ),
        ]
        comun = {"fuente": "Oficina de Conflictos de Intereses", "url": d["url"]}
        aristas = [
            AristaNormalizada(
                ftm_schema="Occupancy",
                source_key=clave_persona,
                target_key=clave_puesto,
                # Una persona con dos autorizaciones tiene UN cese: la misma
                # clave, que es lo que lo hace idempotente.
                dedupe_key=(
                    f"oci:cese:{clave(d['nombre'])}:{clave(d['cargo'])}:{d.get('fecha_cese', '')}"
                ),
                confidence=1.0,
                end_date=cese,
                properties={
                    **comun,
                    "acto": "cese",
                    "cargo": d["cargo"],
                    "departamento": d.get("ministerio", ""),
                    **({"curriculum": curriculum} if curriculum else {}),
                },
            ),
            AristaNormalizada(
                ftm_schema="UnknownLink",
                source_key=clave_persona,
                target_key=clave_actividad,
                dedupe_key=(
                    f"oci:autorizacion:{clave(d['nombre'])}:{clave(d['actividad'])}"
                    f":{d.get('fecha_autorizacion', '')}"
                ),
                confidence=1.0,
                start_date=autorizacion,
                properties={
                    **comun,
                    "relacion": "autorizacion_actividad_privada",
                    "actividad": d["actividad"],
                    "cargoAnterior": d["cargo"],
                    **({"fechaCese": cese.isoformat()} if cese else {}),
                },
            ),
        ]
        return Normalizado(entidades=entidades, aristas=aristas)


def crear() -> OCIConnector:
    return OCIConnector()
