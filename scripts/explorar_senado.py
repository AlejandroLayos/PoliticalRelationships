#!/usr/bin/env python3
"""Reconocimiento de los datos abiertos del Senado: senadores y su formación.

**Esto no es un conector.** Es mirar antes de escribirlo.

Para qué (spec §15, fase 7, líneas 3 y 4): el Senado es una de las fuentes
oficiales que la regla de §12 admite para nombrar a una persona, en su papel
de senador. Da la formación y la procedencia —elegido o designado por un
parlamento autonómico—, y muchos ministros y secretarios de Estado han sido
senadores: es una segunda vía, como el Congreso, para unir un alto cargo del
BOE con su partido.

Lo que se commitea: el informe (enlaces del catálogo, formatos, claves y
recuentos) y una muestra de los ficheros de senadores para los golden tests.
Son senadores en su papel de senadores.

Uso (desde una máquina con salida a internet; el runner de Actions vale):

    python scripts/explorar_senado.py
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    import httpx
except ImportError:  # pragma: no cover
    sys.exit("falta httpx: pip install httpx")

CATALOGO = "https://www.senado.es/web/relacionesciudadanos/datosabiertos/catalogodatos/index.html"

# Los ficheros que la primera vuelta encontró en el catálogo y que hacen falta
# para el conector: la composición desde 1977 y los grupos con sus partidos.
# Se guardan enteros como muestra y se describe un registro de cada uno.
FIJOS = {
    "composicion-desde-1977.xml": "https://www.senado.es/web/ficopendataservlet?tipoFich=10",
    "grupos-y-partidos-xv.xml": "https://www.senado.es/web/ficopendataservlet?tipoFich=4&legis=15",
}
CABECERAS = {"User-Agent": "Sinapsis/0.1 (reconocimiento; proyecto abierto de transparencia)"}
TOPE = 90.0


def pedir(cliente: httpx.Client, url: str) -> tuple[int, bytes, str, str]:
    print(f"→ {url}", flush=True)
    inicio = time.monotonic()
    try:
        with cliente.stream("GET", url, headers=CABECERAS) as r:
            trozos = []
            for t in r.iter_bytes():
                trozos.append(t)
                if time.monotonic() - inicio > TOPE:
                    return 0, b"", "cortado", url
            return r.status_code, b"".join(trozos), r.headers.get("content-type", ""), str(r.url)
    except httpx.HTTPError as exc:
        return 0, b"", f"error: {exc}", url


def enlaces_de(html: str, base: str) -> list[tuple[str, str]]:
    salida = []
    for href, texto in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, flags=re.S | re.I):
        destino = urljoin(base, href.replace("&amp;", "&"))
        texto = " ".join(re.sub(r"<[^>]+>", " ", texto).split())
        salida.append((destino, texto))
    return salida


def describir_xml(texto: str) -> list[str]:
    etiquetas = Counter(re.findall(r"<([A-Za-z_][\w.-]*)[\s>]", texto))
    lineas = [f"- etiquetas más frecuentes: {etiquetas.most_common(25)}"]
    # Los valores de las etiquetas que suenan a formación o procedencia.
    for etiqueta in [e for e in etiquetas if re.search(r"(?i)part|grup|form|proc|circ|legis|alta|baja", e)][:10]:
        valores = Counter(
            " ".join(re.sub(r"<!\[CDATA\[|\]\]>", "", v).split())[:40]
            for v in re.findall(rf"<{etiqueta}[^>]*>(.*?)</{etiqueta}>", texto, flags=re.S)
        )
        lineas.append(f"- `{etiqueta}`: {len(valores)} valores; {valores.most_common(8)}")
    return lineas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="docs/fuentes/senado-reconocimiento.md")
    ap.add_argument("--golden", default="ingest/tests/golden/senado")
    args = ap.parse_args()
    golden = Path(args.golden)

    informe = [
        "# Reconocimiento: datos abiertos del Senado (senadores)",
        "",
        f"Generado el {datetime.now(UTC).isoformat()} por `scripts/explorar_senado.py`.",
        "",
    ]
    with httpx.Client(timeout=45.0, follow_redirects=True) as c:
        codigo, contenido, tipo, final = pedir(c, CATALOGO)
        informe += [f"## `{CATALOGO}`", "", f"HTTP {codigo} · `{tipo}` · {len(contenido):,} bytes · final `{final}`", ""]
        if codigo != 200:
            Path(args.salida).write_text("\n".join(informe) + "\n", encoding="utf-8")
            print("\n".join(informe))
            return 1
        enlaces = enlaces_de(contenido.decode("utf-8", errors="replace"), final)
        interesantes = [
            (u, t)
            for u, t in enlaces
            if re.search(r"(?i)senador|composici|parlamentari|grupo|legislatura|opendata|datosabiertos", u + " " + t)
        ]
        informe += ["Enlaces del catálogo que hablan de senadores, grupos o legislaturas:", ""]
        informe += [f"- {t[:80]!r} → `{u}`" for u, t in interesantes[:80]]
        informe.append("")

        # Un nivel más: las páginas del catálogo sobre senadores, y de ellas
        # los ficheros (XML, JSON, CSV) o el servlet de datos abiertos.
        paginas = [u for u, t in interesantes if re.search(r"(?i)senador", u + " " + t)][:6]
        ficheros: list[tuple[str, str]] = []
        for pagina in paginas:
            codigo, contenido, tipo, final = pedir(c, pagina)
            informe += [f"### `{pagina}`", "", f"HTTP {codigo} · `{tipo}` · {len(contenido):,} bytes", ""]
            if codigo != 200 or "html" not in tipo:
                continue
            for u, t in enlaces_de(contenido.decode("utf-8", errors="replace"), final):
                ruta = urlparse(u).path.lower()
                if ruta.endswith((".xml", ".json", ".csv")) or "opendata" in u.lower() or "fichero" in u.lower():
                    if (u, t) not in ficheros:
                        ficheros.append((u, t))
            informe += [f"- {t[:80]!r} → `{u}`" for u, t in ficheros[-30:]]
            informe.append("")
            time.sleep(0.5)

        informe += ["## Ficheros", ""]
        guardados = 0
        for url, texto in ficheros[:10]:
            codigo, contenido, tipo, final = pedir(c, url)
            informe += [f"### {texto[:80]!r}", "", f"`{url}` → HTTP {codigo} · `{tipo}` · {len(contenido):,} bytes", ""]
            if codigo != 200 or not contenido:
                continue
            texto_fichero = contenido.decode("utf-8", errors="replace")
            if "xml" in tipo or texto_fichero.lstrip().startswith("<"):
                informe += describir_xml(texto_fichero)
            if guardados < 3 and len(contenido) < 3_000_000 and re.search(r"(?i)senador", url + texto):
                golden.mkdir(parents=True, exist_ok=True)
                nombre = re.sub(r"[^\w.-]+", "_", urlparse(url).path.rsplit("/", 1)[-1] + "_" + urlparse(url).query)[:80]
                destino = golden / (nombre + (".xml" if "xml" in tipo else ".dat"))
                destino.write_bytes(contenido)
                informe.append(f"- guardado como `{destino}`")
                guardados += 1
            informe.append("")
            time.sleep(0.5)

        informe += ["## Ficheros para el conector", ""]
        for nombre, url in FIJOS.items():
            codigo, contenido, tipo, final = pedir(c, url)
            informe += [f"### `{nombre}`", "", f"`{url}` → HTTP {codigo} · `{tipo}` · {len(contenido):,} bytes", ""]
            if codigo != 200 or not contenido:
                continue
            texto = contenido.decode("iso-8859-1" if b"ISO-8859-1" in contenido[:200] else "utf-8", errors="replace")
            informe += describir_xml(texto)
            # Un registro entero, tal cual, para ver la forma.
            primero = re.search(r"<(senador|grupo|grupoParlamentario|partido)\b.*?</\1>", texto, flags=re.S)
            if primero:
                informe += ["", "Primer registro:", "", "```xml", primero.group(0)[:2500], "```"]
            if len(contenido) < 4_000_000:
                golden.mkdir(parents=True, exist_ok=True)
                (golden / nombre).write_bytes(contenido)
                informe.append(f"- guardado como `{golden / nombre}`")
            informe.append("")
            time.sleep(0.5)

    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.salida).write_text("\n".join(informe) + "\n", encoding="utf-8")
    print("\n".join(informe))
    return 0


if __name__ == "__main__":
    sys.exit(main())
