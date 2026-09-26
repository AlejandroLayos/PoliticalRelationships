#!/usr/bin/env python3
"""Reconocimiento de la CNMV: consejos, directivos y participaciones significativas.

**Esto no es un conector.** Es mirar antes de escribirlo.

Para qué (spec §12, ampliación del 26/9/2026): los consejeros, altos
directivos y accionistas significativos de las sociedades cotizadas salen con
nombre, tal como los publica la CNMV y sólo en ese papel. Antes de leerlos hay
que ver dónde y cómo los publica.

## Segunda vuelta

La primera (commit caaeac4) encontró la ficha de cada emisor
(`Consultas/DatosEntidad?nif=`) y, en ella, las páginas que la CNMV ofrece
por entidad. Las que interesan:

- `ee/datosgenerales.aspx?nif=` — los datos de la entidad;
- `derechosvoto/ps_ac_ini.aspx?nif=` — participaciones significativas;
- `ee/informaciongobcorp.aspx?nif=` — el informe anual de gobierno
  corporativo, que trae la composición del consejo;
- `directivos-resultado.aspx?nif=` — notificaciones de directivos.

La primera vuelta no llegó a entrar en ellas: seguía los doce primeros enlaces
de la ficha y éstas iban detrás. Ahora se piden directamente.

Las notificaciones de directivos traen también «personas estrechamente
vinculadas», que pueden ser familiares (spec §12: familias, no). De esa página
se anota la forma —tablas, cabeceras, recuentos— y **no se guarda**.

El listado que la primera vuelta tomó por el de cotizadas era el de agencias y
sociedades de valores. Aquí se prueban los demás identificadores del mismo
listado y se anota el título de cada uno.

Uso (desde una máquina con salida a internet; el runner de Actions vale):

    python scripts/explorar_cnmv.py
"""

from __future__ import annotations

import argparse
import html as html_lib
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

CABECERAS = {
    "User-Agent": "Sinapsis/0.1 (reconocimiento; proyecto abierto de transparencia)",
    "Accept-Language": "es-ES,es;q=0.9",
}
TOPE = 60.0
BASE = "https://www.cnmv.es/portal/Consultas/"

# Cotizadas conocidas, por NIF: teleco, eléctrica, constructora, dos grupos de
# medios, la tecnológica de defensa que ya sale en la red de poder, un banco y
# una sociedad con participación pública.
MUESTRA = {
    "telefonica": "A28015865",
    "iberdrola": "A48010615",
    "acs": "A28004885",
    "atresmedia": "A78839271",
    "prisa": "A28297059",
    "indra": "A28599033",
    "santander": "A39000013",
    "redeia": "A78003662",
}

# Páginas por entidad (relativas a BASE), y si la muestra se guarda.
PAGINAS = {
    "datosentidad": ("DatosEntidad.aspx?nif={nif}", True),
    "datosgenerales": ("ee/datosgenerales.aspx?nif={nif}", True),
    "participaciones": ("derechosvoto/ps_ac_ini.aspx?nif={nif}", True),
    "gobcorp": ("ee/informaciongobcorp.aspx?nif={nif}", True),
    # Personas vinculadas: sólo la forma, nunca la página.
    "directivos": ("directivos-resultado.aspx?nif={nif}", False),
}

LISTADO = BASE + "ListadoEntidad.aspx?id={id}&tipoent=0"


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


def texto(fragmento: str) -> str:
    return " ".join(html_lib.unescape(re.sub(r"<[^>]+>", " ", fragmento)).split())


def titulo(html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, flags=re.S | re.I)
    return texto(m.group(1)) if m else ""


def tablas(html: str, filas_max: int = 4, con_valores: bool = True) -> list[str]:
    lineas = []
    for i, t in enumerate(re.findall(r"<table.*?</table>", html, flags=re.S | re.I)[:14]):
        filas = re.findall(r"<tr.*?</tr>", t, flags=re.S | re.I)
        ident = re.search(r'<table[^>]*id="([^"]+)"', t)
        muestra = []
        for fila in filas[: filas_max if con_valores else 1]:
            celdas = [texto(c)[:50] for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", fila, flags=re.S | re.I)]
            muestra.append(celdas[:12])
        lineas.append(
            f"  - tabla {i + 1}{' #' + ident.group(1) if ident else ''}: {len(filas)} filas; "
            f"{'primeras' if con_valores else 'cabecera'}: {muestra}"
        )
    return lineas


def enlaces(html: str, base: str) -> list[tuple[str, str]]:
    salida = []
    for href, cuerpo in re.findall(r'<a[^>]+href="([^"#][^"]*)"[^>]*>(.*?)</a>', html, flags=re.S | re.I):
        salida.append((urljoin(base, html_lib.unescape(href)), texto(cuerpo)))
    return salida


def encabezados(html: str) -> list[str]:
    """Los rótulos de sección de la página: h1-h4, legend y caption."""
    vistos = []
    for e in re.findall(r"<(?:h[1-4]|legend|caption)[^>]*>(.*?)</(?:h[1-4]|legend|caption)>", html, flags=re.S | re.I):
        t = texto(e)
        if t and t not in vistos and "cookie" not in t.lower():
            vistos.append(t[:90])
    return vistos[:25]


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
        f"Generado el {datetime.now(UTC).isoformat()} por `scripts/explorar_cnmv.py` (segunda vuelta).",
        "",
    ]
    # Dos informes de gobierno corporativo bastan para ver su forma; son PDF
    # grandes y el repositorio no es un archivo.
    iagc_guardados = 0
    with httpx.Client(timeout=45.0, follow_redirects=True) as c:
        informe += ["## Listados de entidades (`ListadoEntidad.aspx?id=N&tipoent=0`)", ""]
        for n in range(0, 16):
            url = LISTADO.format(id=n)
            codigo, cuerpo, tipo, final = pedir(c, url)
            html = cuerpo.decode("utf-8", errors="replace")
            nifs = sorted(set(re.findall(r"nif=([A-Z]\d{7}[0-9A-Z])", html)))
            informe.append(
                f"- id={n} → HTTP {codigo} · «{titulo(html)[:90]}» · {len(nifs)} NIF enlazados"
                + (f" (primeros: {nifs[:5]})" if nifs else "")
            )
            if codigo == 200 and nifs and re.search(r"(?i)emisor|cotiz|acciones|admitid", titulo(html)):
                (golden / f"listado-{n}.html").write_text(html, encoding="utf-8")
                informe.append(f"  - guardado como `listado-{n}.html`")
            time.sleep(0.6)
        informe.append("")

        for empresa, nif in MUESTRA.items():
            informe += [f"## {empresa} ({nif})", ""]
            for nombre, (ruta, guardar) in PAGINAS.items():
                url = urljoin(BASE, ruta.format(nif=nif))
                codigo, cuerpo, tipo, final = pedir(c, url)
                html = cuerpo.decode("utf-8", errors="replace")
                informe += [
                    f"### {nombre}",
                    "",
                    f"`{url}` → HTTP {codigo} · `{tipo}` · {len(html):,} caracteres · «{titulo(html)[:90]}»",
                    "",
                ]
                if codigo != 200 or not html:
                    time.sleep(1.0)
                    continue
                informe.append(f"- rótulos: {encabezados(html)}")
                informe += tablas(html, con_valores=guardar)
                if guardar:
                    (golden / f"{empresa}-{nombre}.html").write_text(html, encoding="utf-8")
                    informe.append(f"- guardado como `{empresa}-{nombre}.html`")
                else:
                    informe.append("- no se guarda: trae personas vinculadas")

                # Del informe de gobierno corporativo, el documento más reciente:
                # su formato decide cómo se lee la composición del consejo.
                if nombre == "gobcorp":
                    docs = [
                        (u, t)
                        for u, t in enlaces(html, final)
                        if re.search(r"(?i)verdoc|documento|\.pdf|\.xbrl|\.zip|\.xhtml|showfile|descarga", u)
                    ]
                    informe += [f"    - documento {t[:40]!r} → `{u}`" for u, t in docs[:8]]
                    if docs:
                        u, _ = docs[0]
                        codigo2, cuerpo2, tipo2, _ = pedir(c, u)
                        informe.append(f"- el primero → HTTP {codigo2} · `{tipo2}` · {len(cuerpo2):,} bytes")
                        if codigo2 == 200 and cuerpo2 and len(cuerpo2) < 3_000_000 and iagc_guardados < 2:
                            ext = (
                                "pdf" if cuerpo2[:4] == b"%PDF" else
                                "zip" if cuerpo2[:2] == b"PK" else
                                "html" if b"<html" in cuerpo2[:2000].lower() else "bin"
                            )
                            if ext == "html":
                                informe += tablas(cuerpo2.decode("utf-8", errors="replace"))
                            destino = golden / f"{empresa}-iagc.{ext}"
                            destino.write_bytes(cuerpo2)
                            iagc_guardados += 1
                            informe.append(f"  - guardado como `{destino.name}` ({ext})")
                informe.append("")
                time.sleep(0.8)

    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.salida).write_text("\n".join(informe) + "\n", encoding="utf-8")
    print("\n".join(informe))
    return 0


if __name__ == "__main__":
    sys.exit(main())
