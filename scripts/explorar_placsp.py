#!/usr/bin/env python3
"""Reconocimiento de los feeds de sindicación de PLACSP.

**Esto no es un conector.** Es mirar antes de tocarlo.

Para qué: desde el 18/9/2026 la ruta de contratos menores que usa el
conector (`sindicacion_643/contratosMenoresPerfilesContratantes.atom`)
responde 200 con una página HTML de redirección, y el tramo de los contratos
menores —el gasto municipal del día a día— no entra. Antes de cambiar la ruta
hay que ver cuál publica de verdad el Ministerio de Hacienda en su página de
datos abiertos, y que esa ruta sirve un Atom y no otra página.

Lo que se commitea: el informe (enlaces encontrados y, de cada feed, código,
tipo, si es Atom, cuántas entradas trae la primera página y el enlace a la
siguiente). Nada de contenido: los contratos menores nombran a autónomos.

Uso (desde una máquina con salida a internet; el runner de Actions vale):

    python scripts/explorar_placsp.py
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

try:
    import httpx
except ImportError:  # pragma: no cover
    sys.exit("falta httpx: pip install httpx")

CABECERAS = {"User-Agent": "Sinapsis/0.1 (reconocimiento; proyecto abierto de transparencia)"}
TOPE = 60.0
# De cada feed basta con el principio: la cabecera del Atom, unas entradas y
# el enlace a la página siguiente. Las páginas enteras pesan megas.
BYTES = 400_000

# Páginas donde el Ministerio de Hacienda y la propia Plataforma enumeran los
# conjuntos de datos abiertos de contratación.
PAGINAS = [
    "https://www.hacienda.gob.es/es-ES/GobiernoAbierto/Datos%20Abiertos/Paginas/LicitacionesContratante.aspx",
    "https://www.hacienda.gob.es/es-ES/GobiernoAbierto/Datos%20Abiertos/Paginas/licitaciones_plataforma_contratacion.aspx",
    "https://contrataciondelestado.es/wps/portal/DatosAbiertos",
]

# Las rutas que usa hoy el conector, y la que se sospecha buena para los
# menores. Se prueban aunque no salgan en ninguna página.
CONOCIDAS = [
    "https://contrataciondelestado.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom",
    "https://contrataciondelestado.es/sindicacion/sindicacion_1044/PlataformasAgregadasSinMenores.atom",
    "https://contrataciondelestado.es/sindicacion/sindicacion_643/contratosMenoresPerfilesContratantes.atom",
    "https://contrataciondelestado.es/sindicacion/sindicacion_1143/contratosMenoresPerfilesContratantes.atom",
]


def pedir(cliente: httpx.Client, url: str) -> tuple[int, bytes, str, str]:
    """(código, primeros bytes, tipo, URL final). Corta por tiempo y tamaño."""
    print(f"→ {url}", flush=True)
    inicio = time.monotonic()
    try:
        with cliente.stream("GET", url, headers=CABECERAS) as r:
            trozos: list[bytes] = []
            total = 0
            for t in r.iter_bytes():
                trozos.append(t)
                total += len(t)
                if total >= BYTES or time.monotonic() - inicio > TOPE:
                    break
            return r.status_code, b"".join(trozos), r.headers.get("content-type", ""), str(r.url)
    except httpx.HTTPError as exc:
        return 0, b"", f"error: {exc}", url


def describir_feed(contenido: bytes) -> list[str]:
    texto = contenido.decode("utf-8", errors="replace")
    es_atom = "<feed" in texto[:3000]
    lineas = [f"- ¿Atom?: **{'sí' if es_atom else 'no'}**"]
    if not es_atom:
        # Lo justo para reconocer la página: su título.
        titulo = re.search(r"<title>(.*?)</title>", texto, flags=re.S | re.I)
        lineas.append(f"- título de la página: {titulo.group(1).strip()[:120]!r}" if titulo else "- sin <title>")
        return lineas
    lineas.append(f"- entradas en los primeros {len(contenido):,} bytes: {texto.count('<entry')}")
    actualizado = re.search(r"<updated>(.*?)</updated>", texto)
    if actualizado:
        lineas.append(f"- `updated` del feed: `{actualizado.group(1)}`")
    siguiente = re.search(r'<link[^>]+rel="next"[^>]+href="([^"]+)"', texto) or re.search(
        r'<link[^>]+href="([^"]+)"[^>]+rel="next"', texto
    )
    lineas.append(f"- página siguiente: `{siguiente.group(1)}`" if siguiente else "- sin enlace a la página siguiente")
    # El tipo de contrato de las primeras entradas, para distinguir menores.
    tipos = re.findall(r"<cbc:TypeCode[^>]*>(\d+)</cbc:TypeCode>", texto)[:20]
    if tipos:
        lineas.append(f"- `TypeCode` de las primeras entradas: {sorted(set(tipos))}")
    menor = texto.count("ContractingSystemCode") + texto.count("menor")
    lineas.append(f"- menciones a «menor»/`ContractingSystemCode` en lo leído: {menor}")
    return lineas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="docs/fuentes/placsp-reconocimiento.md")
    args = ap.parse_args()

    informe = [
        "# Reconocimiento: feeds de sindicación de PLACSP",
        "",
        f"Generado el {datetime.now(UTC).isoformat()} por `scripts/explorar_placsp.py`.",
        "",
        "Sólo estructura: códigos, tipos y recuentos. Ningún contenido de los contratos.",
        "",
    ]
    feeds: list[str] = list(CONOCIDAS)
    with httpx.Client(timeout=45.0, follow_redirects=True) as c:
        for pagina in PAGINAS:
            codigo, contenido, tipo, final = pedir(c, pagina)
            informe += [f"## `{pagina}`", "", f"HTTP {codigo} · `{tipo}` · {len(contenido):,} bytes · final `{final}`", ""]
            if codigo != 200:
                continue
            html = contenido.decode("utf-8", errors="replace")
            enlaces = sorted(
                {
                    urljoin(final, h.replace("&amp;", "&"))
                    for h in re.findall(r'href="([^"]+)"', html)
                    if "sindicacion" in h or h.lower().endswith((".atom", ".zip"))
                }
            )
            lista = [f"- `{e}`" for e in enlaces[:60]] or ["- ninguno"]
            informe += ["Enlaces a feeds o ficheros:", "", *lista, ""]
            for e in enlaces:
                if e.lower().endswith(".atom") and e not in feeds:
                    feeds.append(e)
            time.sleep(0.5)

        informe += ["## Los feeds", ""]
        for url in feeds:
            codigo, contenido, tipo, final = pedir(c, url)
            informe += [f"### `{url}`", "", f"HTTP {codigo} · `{tipo}` · final `{final}`", ""]
            if codigo == 200:
                informe += describir_feed(contenido)
            informe.append("")
            time.sleep(0.5)

    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.salida).write_text("\n".join(informe) + "\n", encoding="utf-8")
    print("\n".join(informe))
    return 0


if __name__ == "__main__":
    sys.exit(main())
