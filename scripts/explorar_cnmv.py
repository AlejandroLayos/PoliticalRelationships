#!/usr/bin/env python3
"""Reconocimiento de la CNMV: consejos, directivos y participaciones significativas.

**Esto no es un conector.** Es mirar antes de escribirlo.

Para qué (spec §12, ampliación del 26/9/2026): los consejeros, altos
directivos y accionistas significativos de las sociedades cotizadas salen con
nombre, tal como los publica la CNMV y sólo en ese papel.

## Lo que ya se sabe (vueltas 1 y 2, `docs/fuentes/cnmv-reconocimiento.md`)

- La ficha de un emisor es `Consultas/DatosEntidad.aspx?nif=`, y enlaza a sus
  páginas: datos generales, participaciones significativas, gobierno
  corporativo, notificaciones de directivos.
- Con Telefónica, Prisa y Santander responden con datos. Con Iberdrola, ACS,
  Atresmedia, Indra y Redeia, las mismas páginas dicen «No se han encontrado
  datos», aunque la de participaciones sí pone su nombre en el título.
- Las participaciones no están en `ps_ac_ini`: esa página enlaza a
  `Notificaciones-Participaciones.aspx?qS={guid}` y `SociedadesParticipa…`,
  con un identificador propio por emisor.
- El informe anual de gobierno corporativo (IAGC) es un PDF por ejercicio
  (`webservices/verdocumento/ver?e=…`). Su apartado C.1.2 es la tabla del
  consejo: nombre, categoría, cargo, fechas de nombramiento… y **fecha de
  nacimiento**, que no hace falta para nada.

## Tercera vuelta

1. Participaciones: seguir los enlaces `qS` y describir sus tablas.
2. IAGC: bajar el más reciente de dos emisores, buscar en el PDF la tabla
   C.1.2 y anotar sus cabeceras. **El PDF no se guarda.** Si las cabeceras se
   reconocen, se guarda como muestra SÓLO nombre, categoría, cargo y fechas
   de nombramiento, en JSON; la columna de nacimiento no sale del runner.
3. Los emisores sin datos: reintentarlos con una sesión nueva (entrando
   antes por la portada) y con `&lang=es`, para ver si es cosa de la sesión.

Uso (desde una máquina con salida a internet; el runner de Actions vale):

    python scripts/explorar_cnmv.py
"""

from __future__ import annotations

import argparse
import html as html_lib
import io
import json
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
TOPE = 90.0
BASE = "https://www.cnmv.es/portal/Consultas/"
PORTADA = "https://www.cnmv.es/portal/home.aspx"

CON_DATOS = {"telefonica": "A28015865", "prisa": "A28297059", "santander": "A39000013"}
SIN_DATOS = {
    "iberdrola": "A48010615",
    "acs": "A28004885",
    "atresmedia": "A78839271",
    "indra": "A28599033",
    "redeia": "A78003662",
}

# Las columnas de la tabla C.1.2 que se pueden guardar. Todo lo demás —y en
# particular la fecha de nacimiento— se queda fuera.
COLUMNAS_PERMITIDAS = {
    "nombre": re.compile(r"(?i)nombre|denominaci"),
    "representante": re.compile(r"(?i)representante"),
    "categoria": re.compile(r"(?i)categor"),
    "cargo": re.compile(r"(?i)cargo"),
    "primer_nombramiento": re.compile(r"(?i)primer\s*nombramiento"),
    "ultimo_nombramiento": re.compile(r"(?i)[uú]ltimo\s*nombramiento"),
}
PROHIBIDA = re.compile(r"(?i)nacimiento")


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
            return (
                r.status_code,
                b"".join(trozos),
                r.headers.get("content-type", ""),
                str(r.url),
            )
    except httpx.HTTPError as exc:
        return 0, b"", f"error: {exc}", url


def texto(fragmento: str) -> str:
    return " ".join(html_lib.unescape(re.sub(r"<[^>]+>", " ", fragmento)).split())


def titulo(html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, flags=re.S | re.I)
    return texto(m.group(1)) if m else ""


def contenido(html: str) -> str:
    """El texto de la zona de contenido de una página del portal."""
    limpio = re.sub(r'<input type="hidden"[^>]*>', "", html)
    limpio = re.sub(r"<script.*?</script>|<style.*?</style>", " ", limpio, flags=re.S)
    i = limpio.find("ContentPrincipal")
    trozo = limpio[i:] if i >= 0 else limpio
    j = trozo.find("footer")
    return texto(trozo[: j if j > 0 else 30000])


def tablas(html: str, filas_max: int = 4) -> list[str]:
    lineas = []
    for i, t in enumerate(
        re.findall(r"<table.*?</table>", html, flags=re.S | re.I)[:10]
    ):
        filas = re.findall(r"<tr.*?</tr>", t, flags=re.S | re.I)
        ident = re.search(r'<table[^>]*id="([^"]+)"', t)
        muestra = [
            [
                texto(c)[:50]
                for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", f, flags=re.S | re.I)
            ][:12]
            for f in filas[:filas_max]
        ]
        lineas.append(
            f"  - tabla {i + 1}{' #' + ident.group(1) if ident else ''}: {len(filas)} filas;"
            f" primeras: {muestra}"
        )
    return lineas


def participaciones(c: httpx.Client, empresa: str, nif: str, golden: Path) -> list[str]:
    salida = [f"### Participaciones de {empresa}", ""]
    codigo, cuerpo, _, final = pedir(
        c, urljoin(BASE, f"derechosvoto/ps_ac_ini.aspx?nif={nif}")
    )
    html = cuerpo.decode("utf-8", errors="replace")
    enlaces = [
        urljoin(final, html_lib.unescape(h))
        for h in re.findall(r'href="([^"]*qS=[^"]+)"', html)
    ]
    salida.append(f"- `ps_ac_ini` → HTTP {codigo}; enlaces con qS: {enlaces}")
    for url in enlaces[:2]:
        time.sleep(0.8)
        codigo, cuerpo, tipo, _ = pedir(c, url)
        html = cuerpo.decode("utf-8", errors="replace")
        nombre = re.sub(r"\W+", "-", url.rsplit("/", 1)[-1].split("?")[0].lower())
        salida += [
            "",
            f"`{url}` → HTTP {codigo} · `{tipo}` · {len(html):,} caracteres · «{titulo(html)[:90]}»",
        ]
        salida.append(f"- contenido: {contenido(html)[:600]!r}")
        salida += tablas(html)
        if codigo == 200 and "<table" in html.lower():
            (golden / f"{empresa}-{nombre}.html").write_text(html, encoding="utf-8")
            salida.append(f"- guardado como `{empresa}-{nombre}.html`")
    return [*salida, ""]


def iagc(c: httpx.Client, empresa: str, nif: str, golden: Path) -> list[str]:
    salida = [f"### IAGC de {empresa}", ""]
    codigo, cuerpo, _, _ = pedir(
        c, urljoin(BASE, f"ee/informaciongobcorp.aspx?nif={nif}")
    )
    html = cuerpo.decode("utf-8", errors="replace")
    docs = [
        html_lib.unescape(h)
        for h in re.findall(
            r'href="(https://www\.cnmv\.es/webservices/verdocumento/ver\?e=[^"]+)"',
            html,
        )
    ]
    salida.append(f"- página → HTTP {codigo}; documentos: {len(docs)}")
    if not docs:
        return [*salida, ""]
    codigo, pdf, tipo, _ = pedir(c, docs[0])
    salida.append(
        f"- el más reciente → HTTP {codigo} · `{tipo}` · {len(pdf):,} bytes"
        f" · PDF: {pdf[:4] == b'%PDF'}"
    )
    if codigo != 200 or pdf[:4] != b"%PDF":
        return [*salida, ""]
    try:
        import pdfplumber
    except ImportError:
        return [*salida, "- sin pdfplumber: no se analiza", ""]

    filas_guardables: list[dict[str, str]] = []
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        salida.append(f"- páginas: {len(doc.pages)}")
        paginas = [
            i
            for i, p in enumerate(doc.pages)
            if re.search(r"C\.1\.2", p.extract_text() or "")
        ]
        salida.append(f"- páginas que citan C.1.2: {[i + 1 for i in paginas[:10]]}")
        for i in paginas[:4]:
            pagina = doc.pages[i]
            for n, tabla in enumerate(pagina.extract_tables()):
                if not tabla:
                    continue
                cabecera = [" ".join((x or "").split()) for x in tabla[0]]
                salida.append(
                    f"  - página {i + 1}, tabla {n + 1}: {len(tabla)} filas; cabecera: {cabecera}"
                )
                if not any(COLUMNAS_PERMITIDAS["nombre"].search(h) for h in cabecera):
                    continue
                # Qué columna es cada cosa, por su cabecera; la de nacimiento,
                # ninguna.
                indices: dict[str, int] = {}
                for clave, patron in COLUMNAS_PERMITIDAS.items():
                    for j, h in enumerate(cabecera):
                        if (
                            patron.search(h)
                            and not PROHIBIDA.search(h)
                            and j not in indices.values()
                        ):
                            indices[clave] = j
                            break
                salida.append(f"    - columnas reconocidas: {indices}")
                if "nombre" in indices and "cargo" in indices:
                    for fila in tabla[1:]:
                        registro = {
                            k: " ".join((fila[j] or "").split())
                            for k, j in indices.items()
                            if j < len(fila)
                        }
                        if registro.get("nombre"):
                            filas_guardables.append(registro)
    salida.append(f"- filas del consejo reconocidas: {len(filas_guardables)}")
    if filas_guardables:
        destino = golden / f"{empresa}-iagc-consejo.json"
        destino.write_text(
            json.dumps(filas_guardables, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        salida.append(
            f"- guardado como `{destino.name}` (sin fecha de nacimiento; el PDF no se guarda)"
        )
    return [*salida, ""]


def sin_datos(empresa: str, nif: str) -> list[str]:
    """Otra sesión, entrando por la portada, y con `&lang=es`."""
    salida = [f"### {empresa} ({nif}), con sesión nueva", ""]
    with httpx.Client(timeout=45.0, follow_redirects=True) as c:
        codigo, _, _, _ = pedir(c, PORTADA)
        salida.append(f"- portada → HTTP {codigo}; cookies: {sorted(c.cookies.keys())}")
        for ruta in (
            f"DatosEntidad.aspx?nif={nif}",
            f"DatosEntidad.aspx?nif={nif}&lang=es",
            f"ee/datosgenerales.aspx?nif={nif}",
        ):
            time.sleep(0.8)
            codigo, cuerpo, _, _ = pedir(c, urljoin(BASE, ruta))
            html = cuerpo.decode("utf-8", errors="replace")
            salida.append(
                f"- `{ruta}` → HTTP {codigo} · «{titulo(html)[:80]}» · {contenido(html)[:160]!r}"
            )
    return [*salida, ""]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="docs/fuentes/cnmv-reconocimiento.md")
    ap.add_argument("--golden", default="ingest/tests/golden/cnmv")
    args = ap.parse_args()
    golden = Path(args.golden)
    golden.mkdir(parents=True, exist_ok=True)

    salida = Path(args.salida)
    anterior = salida.read_text(encoding="utf-8") if salida.exists() else ""
    informe = [
        "# Reconocimiento: CNMV (consejos y participaciones de cotizadas)",
        "",
        f"Tercera vuelta: {datetime.now(UTC).isoformat()} (`scripts/explorar_cnmv.py`).",
        "La segunda vuelta sigue debajo.",
        "",
        "## Tercera vuelta",
        "",
    ]
    with httpx.Client(timeout=60.0, follow_redirects=True) as c:
        for empresa, nif in CON_DATOS.items():
            informe += participaciones(c, empresa, nif, golden)
            time.sleep(1.0)
        for empresa in ("telefonica", "prisa"):
            informe += iagc(c, empresa, CON_DATOS[empresa], golden)
            time.sleep(1.0)
    for empresa, nif in SIN_DATOS.items():
        informe += sin_datos(empresa, nif)

    if anterior:
        informe += [
            "",
            "---",
            "",
            anterior.replace("# Reconocimiento: CNMV", "## Segunda vuelta: CNMV", 1),
        ]
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text("\n".join(informe) + "\n", encoding="utf-8")
    print("\n".join(informe[:200]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
