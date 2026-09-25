#!/usr/bin/env python3
"""Reconocimiento de las autorizaciones de actividad privada tras el cese.

**Esto no es un conector.** Es mirar antes de escribirlo, como con el BOE y el
Tribunal de Cuentas.

Por qué esta fuente: es la que AFIRMA el vínculo de una puerta giratoria. La
Oficina de Conflictos de Intereses autoriza (o no) a un ex alto cargo a
trabajar en una empresa en los dos años siguientes a su cese (Ley 3/2015,
art. 15), y el Portal de Transparencia lo publica. Con eso, «X, ex secretario
de Estado, autorizado a trabajar en Y» es un hecho con documento, no una
coincidencia de nombres entre el BOE y el BORME (spec §12).

Lo que se commitea: el informe con la estructura (enlaces, tablas, cabeceras,
recuentos) y, como muestra para los golden tests, el HTML de las páginas con
las autorizaciones. Son ex altos cargos en su papel de ex altos cargos, que es
lo que §12 deja publicar.

Uso (desde una máquina con salida a internet; el runner de Actions vale):

    python scripts/explorar_oci.py
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    import httpx
except ImportError:  # pragma: no cover
    sys.exit("falta httpx: pip install httpx")

BASE = "https://transparencia.gob.es"
NOVEDADES = f"{BASE}/masinformacion/novedades-de-transparencia/2026novedades"
BUSCADOR = f"{BASE}/servicios-buscador/buscar.htm?categoria=autorizaciones_ind&lang=es&orderBy=fechaAutorizacion&or=DESC"
PORTADAS = (
    # La lista de ahora no está en el HTML de la portada: la sirve el buscador
    # del portal, paginado, y la portada enlaza a él por ministerio. El
    # segundo reconocimiento lo encontró así.
    BUSCADOR,
    f"{BUSCADOR}&historico=true",
    f"{BUSCADOR}&historico=false",
    f"{BUSCADOR}&pag=2",
    f"{BASE}/publicidad-activa/por-materias/altos-cargos/actividad-privada-cese",
    # Las novedades de 2026: el primer reconocimiento vio que las páginas de
    # seguimiento llegan a 2021 y que la portada no trae la tabla en el HTML.
    f"{NOVEDADES}/Autorizaciones-actividad-privada-cese-Altos-Cargos_abril2026",
    f"{NOVEDADES}/Autorizaciones_EjercicioActividadPrivada_TraselCese_AltosCargos",
    f"{BASE}/publicidad-activa/por-materias/altos-cargos/actividad-privada-cese/aac-graficos",
    f"{BASE}/publicidad-activa/por-materias/altos-cargos/actividad-privada-cese/seguimiento20211101",
)
# Las mismas páginas en otras lenguas: el primer reconocimiento gastó en ellas
# la mitad de su cupo.
_OTRA_LENGUA = re.compile(r"^/(ca|eu|gl|va|en)/")
CABECERAS = {
    "User-Agent": "Sinapsis/0.1 (reconocimiento; proyecto abierto de transparencia)"
}
TOPE = 60.0


class Lector(HTMLParser):
    """Enlaces y tablas de una página, sin dependencias."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.enlaces: list[tuple[str, str]] = []
        self.tablas: list[list[list[str]]] = []
        self._a: str | None = None
        self._texto_a: list[str] = []
        self._celda: list[str] | None = None
        self._fila: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and d.get("href"):
            self._a, self._texto_a = d["href"], []
        elif tag == "table":
            self.tablas.append([])
        elif tag == "tr" and self.tablas:
            self._fila = []
        elif tag in ("td", "th") and self._fila is not None:
            self._celda = []

    def handle_endtag(self, tag):
        if tag == "a" and self._a is not None:
            self.enlaces.append((self._a, " ".join("".join(self._texto_a).split())))
            self._a = None
        elif tag in ("td", "th") and self._celda is not None and self._fila is not None:
            self._fila.append(" ".join("".join(self._celda).split()))
            self._celda = None
        elif tag == "tr" and self._fila is not None and self.tablas:
            if self._fila:
                self.tablas[-1].append(self._fila)
            self._fila = None

    def handle_data(self, data):
        if self._a is not None:
            self._texto_a.append(data)
        if self._celda is not None:
            self._celda.append(data)


def pedir(cliente: httpx.Client, url: str) -> tuple[int, bytes, str]:
    print(f"→ {url}", flush=True)
    inicio = time.monotonic()
    try:
        with cliente.stream("GET", url, headers=CABECERAS) as r:
            trozos = []
            for t in r.iter_bytes():
                trozos.append(t)
                if time.monotonic() - inicio > TOPE:
                    return 0, b"", "cortado"
            return r.status_code, b"".join(trozos), r.headers.get("content-type", "")
    except httpx.HTTPError as exc:
        return 0, b"", f"error: {exc}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="docs/fuentes/oci-reconocimiento.md")
    ap.add_argument("--golden", default="ingest/tests/golden/oci")
    args = ap.parse_args()
    golden = Path(args.golden)
    golden.mkdir(parents=True, exist_ok=True)

    informe = [
        "# Reconocimiento: actividad privada tras el cese de altos cargos",
        "",
        f"Generado el {datetime.now(UTC).isoformat()} por `scripts/explorar_oci.py`.",
        "",
        "Lo que se ve desde fuera, sin interpretar, para escribir el conector de",
        "la fuente que afirma las puertas giratorias (spec §12 y §15, fase 7).",
        "",
    ]
    vistas: set[str] = set()
    pendientes = list(PORTADAS)
    ficheros = Counter()
    guardadas = 0
    with httpx.Client(timeout=30.0, follow_redirects=True) as c:
        while pendientes and len(vistas) < 25:
            url = pendientes.pop(0)
            if url in vistas:
                continue
            vistas.add(url)
            codigo, contenido, tipo = pedir(c, url)
            informe.append(f"## `{url}`")
            informe.append("")
            informe.append(f"HTTP {codigo} · `{tipo}` · {len(contenido)} bytes")
            informe.append("")
            if codigo != 200 or "html" not in tipo:
                continue
            html = contenido.decode("utf-8", errors="replace")
            lector = Lector()
            lector.feed(html)
            for i, tabla in enumerate(lector.tablas):
                if not tabla:
                    continue
                informe.append(
                    f"- tabla {i}: {len(tabla)} filas · cabecera: `{tabla[0]}`"
                )
            relevantes = []
            for href, texto in lector.enlaces:
                destino = urljoin(url, href)
                ruta = urlparse(destino).path.lower()
                ext = ruta.rsplit(".", 1)[-1] if "." in ruta.rsplit("/", 1)[-1] else ""
                if "/bin/" in ruta:
                    continue
                if ext in {"pdf", "xlsx", "xls", "csv", "ods", "json", "xml"}:
                    ficheros[ext] += 1
                    relevantes.append(f"- [{ext}] {texto!r} → `{destino}`")
                    # Los dos primeros ficheros de datos, como muestra: si la
                    # relación vive en un PDF o en una hoja, el parser se
                    # escribe sobre ellos.
                    if ficheros[ext] <= 2 and destino not in vistas:
                        vistas.add(destino)
                        f_codigo, f_contenido, f_tipo = pedir(c, destino)
                        relevantes.append(
                            f"  - HTTP {f_codigo} · `{f_tipo}` · {len(f_contenido)} bytes"
                        )
                        if (
                            f_codigo == 200
                            and f_contenido
                            and len(f_contenido) < 3_000_000
                        ):
                            nombre_f = Path(urlparse(destino).path).name
                            (golden / nombre_f).write_bytes(f_contenido)
                elif (
                    ("actividad-privada" in ruta or "autorizacion" in ruta)
                    and not _OTRA_LENGUA.match(urlparse(destino).path)
                    and "/bin/" not in ruta
                ):
                    relevantes.append(f"- {texto!r} → `{destino}`")
                    if urlparse(destino).netloc.endswith("transparencia.gob.es"):
                        pendientes.append(destino.split("#")[0])
            informe += [
                "",
                "Enlaces relevantes:",
                "",
                *sorted(set(relevantes))[:60],
                "",
            ]
            # Lo que la página carga aparte: si la tabla de ahora no está en
            # el HTML, vendrá de un script, un iframe o un fichero de datos.
            cargas = sorted(
                set(
                    re.findall(
                        r"""(?:src|data-[a-z-]+|href)=["']([^"']+\.(?:json|csv|xlsx?|js)(?:\?[^"']*)?)["']""",
                        html,
                    )
                )
            )
            cargas = [x for x in cargas if "clientlib" not in x and "/etc." not in x][
                :30
            ]
            if cargas:
                informe += [
                    "Lo que la página carga aparte:",
                    "",
                    *[f"- `{x}`" for x in cargas],
                    "",
                ]
            iframes = re.findall(r"<iframe[^>]+src=[\"']([^\"']+)", html)
            if iframes:
                informe += ["Iframes:", "", *[f"- `{x}`" for x in iframes], ""]
            ids_tabla = re.findall(r"<table[^>]*\bid=[\"']([^\"']+)", html)
            if ids_tabla:
                informe.append(f"Tablas por id: {ids_tabla}")
                informe.append("")
            es_portada = url == PORTADAS[0] or url == PORTADAS[1]
            if "servicios-buscador" in url:
                texto_plano = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
                for patron in (
                    r"[Ss]e han encontrado[^.]{0,80}",
                    r"\d[\d.]* resultados?[^.]{0,40}",
                    r"[Pp]ágina \d+ de \d+",
                ):
                    hallado = re.findall(patron, texto_plano)
                    if hallado:
                        informe.append(f"- `{patron}`: {hallado[:3]}")
                paginas = sorted(set(re.findall(r"pag=(\d+)", html)), key=int)
                informe.append(f"- páginas enlazadas: {paginas[:5]} … {paginas[-3:]}")
                # La forma de un resultado, para escribir el lector: el primer
                # bloque que lleve «Fecha de autorización» o una tabla.
                k = html.find("Fecha de autoriza")
                if k > 0:
                    informe += [
                        "",
                        "Un resultado, en crudo:",
                        "",
                        "```html",
                        html[max(0, k - 2500) : k + 1500],
                        "```",
                        "",
                    ]
            if (
                es_portada or (lector.tablas and any(len(t) > 3 for t in lector.tablas))
            ) and guardadas < 4:
                nombre = re.sub(r"[^a-z0-9]+", "-", urlparse(url).path.lower()).strip(
                    "-"
                )
                (golden / f"{nombre}.html").write_bytes(contenido)
                guardadas += 1
                informe.append(
                    f"Página guardada como muestra: `{golden / (nombre + '.html')}`\n"
                )
            time.sleep(0.5)

    informe += [
        "## Resumen",
        "",
        f"- páginas vistas: {len(vistas)}",
        f"- ficheros enlazados: {dict(ficheros)}",
        "",
    ]
    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.salida).write_text("\n".join(informe) + "\n", encoding="utf-8")
    print("\n".join(informe))
    return 0


if __name__ == "__main__":
    sys.exit(main())
