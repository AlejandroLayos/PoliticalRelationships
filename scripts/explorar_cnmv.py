#!/usr/bin/env python3
"""Reconocimiento de la CNMV: consejos, directivos y participaciones significativas.

**Esto no es un conector.** Es mirar antes de escribirlo.

Para qué (spec §12, ampliación del 26/9/2026): los consejeros, altos
directivos y accionistas significativos de las sociedades cotizadas salen con
nombre, tal como los publica la CNMV y sólo en ese papel. Antes de leerlos hay
que ver dónde y cómo los publica: qué páginas, qué tablas, qué columnas, y si
hay un listado de todas las cotizadas.

Se parte de la ficha de unas cuantas cotizadas conocidas en los registros
oficiales de la CNMV —por NIF— y se siguen los enlaces que hablan de consejo,
consejeros, directivos, derechos de voto o gobierno corporativo. De cada página
se anota la forma de sus tablas y se guarda como muestra para los golden tests.

Uso (desde una máquina con salida a internet; el runner de Actions vale):

    python scripts/explorar_cnmv.py
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    import httpx
except ImportError:  # pragma: no cover
    sys.exit("falta httpx: pip install httpx")

CABECERAS = {
    "User-Agent": "Sinapsis/0.1 (reconocimiento; proyecto abierto de transparencia)",
    "Accept-Language": "es-ES,es;q=0.9",
}
TOPE = 60.0

# Cotizadas conocidas, por NIF: una teleco, una eléctrica, una constructora y
# dos grupos de medios.
MUESTRA = {
    "telefonica": "A28015865",
    "iberdrola": "A48010615",
    "acs": "A28004885",
    "atresmedia": "A78839271",
    "prisa": "A28297059",
}

# Formas posibles de la ficha de una entidad en los registros oficiales. No
# están documentadas: se prueban y se anota cuál responde.
FICHAS = [
    "https://www.cnmv.es/Portal/Consultas/DatosEntidad.aspx?nif={nif}",
    "https://www.cnmv.es/portal/Consultas/EE/InformacionGeneral.aspx?nif={nif}",
    "https://www.cnmv.es/portal/Consultas/EE/ConsejoAdministracion.aspx?nif={nif}",
]

# Listados de todas las cotizadas, por si alguno responde.
LISTADOS = [
    "https://www.cnmv.es/portal/Consultas/Busqueda.aspx?id=29",
    "https://www.cnmv.es/portal/Consultas/MostrarListados.aspx?id=18",
    "https://www.cnmv.es/Portal/Consultas/ListadoEntidad.aspx?id=1&tipoent=0",
]

INTERESANTE = re.compile(
    r"(?i)consej|administrad|directiv|derechos de voto|participacion|participación|"
    r"gobierno corporativo|autocartera|accionista"
)


def pedir(cliente: httpx.Client, url: str) -> tuple[int, str, str, str]:
    print(f"→ {url}", flush=True)
    inicio = time.monotonic()
    try:
        with cliente.stream("GET", url, headers=CABECERAS) as r:
            trozos = []
            for t in r.iter_bytes():
                trozos.append(t)
                if time.monotonic() - inicio > TOPE:
                    return 0, "", "cortado", url
            cuerpo = b"".join(trozos)
            return r.status_code, cuerpo.decode(r.encoding or "utf-8", errors="replace"), r.headers.get(
                "content-type", ""
            ), str(r.url)
    except httpx.HTTPError as exc:
        return 0, "", f"error: {exc}", url


def enlaces(html: str, base: str) -> list[tuple[str, str]]:
    salida = []
    for href, texto in re.findall(r'<a[^>]+href="([^"#][^"]*)"[^>]*>(.*?)</a>', html, flags=re.S | re.I):
        texto = " ".join(re.sub(r"<[^>]+>", " ", texto).split())
        salida.append((urljoin(base, href.replace("&amp;", "&")), texto))
    return salida


def tablas(html: str) -> list[str]:
    lineas = []
    for i, t in enumerate(re.findall(r"<table.*?</table>", html, flags=re.S | re.I)[:8]):
        filas = re.findall(r"<tr.*?</tr>", t, flags=re.S | re.I)
        cab = []
        for fila in filas[:2]:
            celdas = [
                " ".join(re.sub(r"<[^>]+>", " ", c).split())[:40]
                for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", fila, flags=re.S | re.I)
            ]
            cab.append(celdas[:10])
        ident = re.search(r'<table[^>]*id="([^"]+)"', t)
        lineas.append(
            f"  - tabla {i + 1}{' #' + ident.group(1) if ident else ''}: {len(filas)} filas; "
            f"primeras: {cab}"
        )
    return lineas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="docs/fuentes/cnmv-reconocimiento.md")
    ap.add_argument("--golden", default="ingest/tests/golden/cnmv")
    args = ap.parse_args()
    golden = Path(args.golden)
    golden.mkdir(parents=True, exist_ok=True)

    informe = [
        "# Reconocimiento: CNMV (consejos y participaciones de cotizadas)",
        "",
        f"Generado el {datetime.now(UTC).isoformat()} por `scripts/explorar_cnmv.py`.",
        "",
    ]
    vistas: set[str] = set()
    with httpx.Client(timeout=45.0, follow_redirects=True) as c:
        informe += ["## Listados de cotizadas", ""]
        for url in LISTADOS:
            codigo, html, tipo, final = pedir(c, url)
            informe += [f"### `{url}`", "", f"HTTP {codigo} · `{tipo}` · {len(html):,} caracteres · final `{final}`", ""]
            if codigo == 200:
                informe += tablas(html)
                nifs = sorted(set(re.findall(r"nif=([A-Z]\d{8})", html)))
                informe.append(f"- NIF enlazados en la página: {len(nifs)} (primeros: {nifs[:10]})")
                if nifs:
                    nombre = "listado-" + re.sub(r"\W+", "-", urlparse(url).path.rsplit("/", 1)[-1] + urlparse(url).query)
                    (golden / f"{nombre[:60]}.html").write_text(html, encoding="utf-8")
            informe.append("")
            time.sleep(1.0)

        for empresa, nif in MUESTRA.items():
            informe += [f"## {empresa} ({nif})", ""]
            for plantilla in FICHAS:
                url = plantilla.format(nif=nif)
                codigo, html, tipo, final = pedir(c, url)
                informe.append(f"- `{url}` → HTTP {codigo} · {len(html):,} caracteres · final `{final}`")
                if codigo != 200 or not html:
                    continue
                (golden / f"{empresa}-{urlparse(url).path.rsplit('/', 1)[-1].lower()}.html").write_text(
                    html, encoding="utf-8"
                )
                informe += tablas(html)
                siguientes = [(u, t) for u, t in enlaces(html, final) if INTERESANTE.search(t + " " + u)]
                informe += [f"    - enlace {t[:60]!r} → `{u}`" for u, t in siguientes[:25]]
                for u, t in siguientes[:12]:
                    if u in vistas or "cnmv.es" not in u:
                        continue
                    vistas.add(u)
                    codigo2, html2, tipo2, final2 = pedir(c, u)
                    informe += ["", f"#### {t[:70]!r}", "", f"`{u}` → HTTP {codigo2} · `{tipo2}` · {len(html2):,} caracteres", ""]
                    if codigo2 == 200 and html2:
                        informe += tablas(html2)
                        nombre = re.sub(r"\W+", "-", urlparse(u).path.rsplit("/", 1)[-1].lower())
                        (golden / f"{empresa}-{nombre[:50]}.html").write_text(html2, encoding="utf-8")
                    time.sleep(0.7)
                informe.append("")
                time.sleep(0.7)

    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.salida).write_text("\n".join(informe) + "\n", encoding="utf-8")
    print("\n".join(informe))
    return 0


if __name__ == "__main__":
    sys.exit(main())
