#!/usr/bin/env python3
"""Reconocimiento del Tribunal de Cuentas.

**Esto no es un conector.** Es el paso previo: averiguar qué publica realmente
el TdC y en qué formato, antes de escribir una línea de parser.

El motivo es una lección que ya costó cara en este proyecto. Para BDNS deduje
el nombre de un campo (`nifCif`) del enumerado de parámetros de búsqueda, lo di
por bueno, y estaba mal: el 79 % de las aristas de la primera ingesta salió sin
identificador fiscal. Escribir un parser de PDF sobre suposiciones sería el
mismo error, multiplicado — los PDFs no avisan cuando los lees mal, sólo
devuelven basura con aspecto de dato.

Así que este script mira y **anota lo que ve**, sin interpretar. Su salida es
un informe en Markdown que se commitea, y a partir de ahí se decide.

Uso (desde una máquina con salida a internet; el runner de Actions vale):

    python scripts/explorar_tcu.py --salida docs/fuentes/tcu-reconocimiento.md
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

try:
    import httpx
except ImportError:  # pragma: no cover
    sys.exit("falta httpx: pip install httpx")

# Puntos de entrada conocidos, sacados de la navegación pública del organismo.
CANDIDATOS = {
    "portal_partidos": "https://www.tcu.es/es/partidos-politicos/",
    "sanciones": "https://www.tcu.es/es/fiscalizacion/sanciones-a-partidos/",
    "sede_rendicion": "https://sede.tcu.es/es/sede-electronica/GRCuentas/PartidosPoliticos/",
    "buscador": (
        "https://www.tcu.es/searcher/document/DocumentSearch.action"
        "?docCheckFis=true&docCheckFisSelect=FIS:+PARTIDOS+POL%C3%8DTICOS&submitSearch=true"
    ),
}

CABECERAS = {
    # Identificarse es lo correcto al raspar un servicio público.
    "User-Agent": "Sinapsis/0.1 (proyecto abierto de transparencia; +https://github.com/AlejandroLayos/PoliticalRelationships)",
    "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
}


def explorar(cliente: httpx.Client, nombre: str, url: str) -> dict:
    """Pide una URL y describe lo que devuelve, sin interpretarlo."""
    info: dict = {"nombre": nombre, "url": url}
    try:
        r = cliente.get(url)
    except httpx.HTTPError as exc:
        info["error"] = str(exc)
        return info

    info["status"] = r.status_code
    info["content_type"] = r.headers.get("content-type", "")
    info["bytes"] = len(r.content)
    info["url_final"] = str(r.url)

    if r.status_code != 200:
        return info

    texto = r.text if "text" in info["content_type"] or "html" in info["content_type"] else ""

    # Enlaces a ficheros descargables: es lo que decide si hay datos
    # estructurados o sólo documentos para leer con los ojos.
    enlaces = re.findall(r'href="([^"]+\.(?:pdf|xlsx?|csv|json|xml|zip))"', texto, re.I)
    info["descargables"] = sorted({urljoin(str(r.url), e) for e in enlaces})[:25]
    info["n_descargables"] = len(set(enlaces))

    # ¿Hay tablas HTML? Sería mucho mejor que un PDF.
    info["tablas_html"] = len(re.findall(r"<table", texto, re.I))

    # ¿Algún endpoint que huela a datos?
    info["pistas_api"] = sorted(
        {
            m
            for m in re.findall(r'["\'](/[^"\']*(?:api|json|rest|datos|opendata)[^"\']*)["\']', texto, re.I)
        }
    )[:10]
    return info


def formatear(resultados: list[dict]) -> str:
    hoy = datetime.now(UTC).isoformat()
    lineas = [
        "# Reconocimiento del Tribunal de Cuentas",
        "",
        f"Generado automáticamente el {hoy} por `scripts/explorar_tcu.py`.",
        "",
        "**No es documentación de una fuente ya integrada.** Es lo que se ve",
        "desde fuera, anotado sin interpretar, para decidir si merece la pena",
        "escribir un conector y de qué tipo.",
        "",
    ]
    for r in resultados:
        lineas.append(f"## {r['nombre']}")
        lineas.append("")
        lineas.append(f"- URL: `{r['url']}`")
        if "error" in r:
            lineas.append(f"- **No accesible:** `{r['error']}`")
            lineas.append("")
            continue
        lineas.append(f"- HTTP {r['status']} · `{r['content_type']}` · {r['bytes']:,} bytes")
        if r.get("url_final") != r["url"]:
            lineas.append(f"- Redirige a: `{r['url_final']}`")
        lineas.append(f"- Tablas HTML en la página: **{r.get('tablas_html', 0)}**")
        lineas.append(f"- Ficheros descargables enlazados: **{r.get('n_descargables', 0)}**")
        if r.get("descargables"):
            lineas.append("")
            lineas.append("  Primeros enlaces:")
            for d in r["descargables"][:10]:
                lineas.append(f"  - `{d}`")
        if r.get("pistas_api"):
            lineas.append("")
            lineas.append("  Rutas que podrían servir datos:")
            for a in r["pistas_api"]:
                lineas.append(f"  - `{a}`")
        lineas.append("")

    lineas += [
        "---",
        "",
        "## Qué mirar en este informe",
        "",
        "1. **¿Hay CSV, XLSX o JSON?** Si los hay, el conector es sencillo y no",
        "   hace falta tocar un PDF.",
        "2. **¿Hay tablas HTML?** Segunda mejor opción: se parsean sin OCR.",
        "3. **Si sólo hay PDF**, el conector necesita extracción de tablas",
        "   (`pdfplumber`) y, si están escaneados, OCR. Eso es trabajo de otra",
        "   magnitud y conviene decidirlo a la vista de un fichero real, no",
        "   antes.",
        "",
        "Sea cual sea el caso: los datos de financiación de partidos son la zona",
        "más delicada del proyecto en RGPD. Los donantes personas físicas se",
        "tratan como en BDNS — el hecho se conserva, la identidad no. Ver",
        "[spec §12](../spec.md).",
    ]
    return "\n".join(lineas) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--salida", type=Path, default=Path("docs/fuentes/tcu-reconocimiento.md")
    )
    args = p.parse_args()

    with httpx.Client(timeout=45.0, follow_redirects=True, headers=CABECERAS) as cliente:
        resultados = []
        for nombre, url in CANDIDATOS.items():
            print(f"explorando {nombre}…", file=sys.stderr)
            resultados.append(explorar(cliente, nombre, url))

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(formatear(resultados), encoding="utf-8")
    print(f"informe escrito en {args.salida}", file=sys.stderr)

    alcanzables = [r for r in resultados if r.get("status") == 200]
    if not alcanzables:
        print("ninguna URL respondió: el informe no dice nada útil", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
