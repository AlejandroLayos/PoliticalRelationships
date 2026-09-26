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
from collections import Counter
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


# Cuarta vuelta: cuántas cotizadas responden por NIF. Una lista de NIF
# conocidos del Ibex y de grupos de medios; no es la fuente de nada, sólo la
# muestra con la que medir.
MUESTRA_AMPLIA = {
    "repsol": "A78374725",
    "bbva": "A48265169",
    "inditex": "A15075062",
    "aena": "A86212420",
    "endesa": "A81948077",
    "naturgy": "A08015497",
    "caixabank": "A08663619",
    "sabadell": "A08000143",
    "mapfre": "A08055741",
    "acciona": "A08001851",
    "grifols": "A58389123",
    "cellnex": "A64907306",
    "colonial": "A28027399",
    "merlin": "A86977790",
    "sacyr": "A28013811",
    "bankinter": "A28157360",
    "enagas": "A28294726",
    "amadeus": "A84236934",
    "acerinox": "A28250777",
    "unicaja": "A93139053",
    "vocento": "A48001655",
    "logista": "A87008579",
}

BUSCADOR_PARTICIPACIONES = BASE + "busqueda.aspx?id=7"


def cuantas_responden(c: httpx.Client) -> list[str]:
    salida = ["### DatosEntidad por NIF en una muestra amplia", ""]
    con, sin = [], []
    for empresa, nif in MUESTRA_AMPLIA.items():
        codigo, cuerpo, _, _ = pedir(c, urljoin(BASE, f"DatosEntidad.aspx?nif={nif}"))
        html = cuerpo.decode("utf-8", errors="replace")
        nombre = (
            titulo(html).replace("CNMV - Información de la Entidad", "").strip(" -")
        )
        (con if nombre else sin).append(empresa)
        salida.append(
            f"- {empresa} ({nif}) → HTTP {codigo} · «{nombre or 'sin datos'}»"
        )
        time.sleep(0.6)
    salida += ["", f"Con datos: {len(con)}; sin datos: {len(sin)} ({sin})", ""]
    return salida


def buscador(c: httpx.Client) -> list[str]:
    """El formulario de búsqueda de participaciones: sus campos, y una búsqueda."""
    salida = ["### El buscador de participaciones significativas", ""]
    codigo, cuerpo, _, final = pedir(c, BUSCADOR_PARTICIPACIONES)
    html = cuerpo.decode("utf-8", errors="replace")
    salida.append(
        f"- `{BUSCADOR_PARTICIPACIONES}` → HTTP {codigo} · «{titulo(html)[:80]}» · final `{final}`"
    )
    ocultos = dict(
        re.findall(
            r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"', html
        )
    )
    visibles = re.findall(r'<input[^>]+type="(?:text|search)"[^>]*name="([^"]+)"', html)
    botones = re.findall(
        r'<input[^>]+type="submit"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', html
    )
    selects = re.findall(r'<select[^>]*name="([^"]+)"', html)
    salida += [
        f"- ocultos: {sorted(ocultos)}",
        f"- de texto: {visibles}",
        f"- botones: {botones}",
        f"- desplegables: {selects}",
        f"- contenido: {contenido(html)[:500]!r}",
    ]
    # Los atributos del campo van en cualquier orden: se busca por su nombre.
    campo = next(
        iter(re.findall(r'name="([^"]*txtDenominacion[^"]*)"', html)),
        next(
            (v for v in visibles if re.search(r"(?i)nombre|denom|texto|entidad", v)),
            None,
        ),
    )
    salida.append(f"- campo de denominación: {campo}")
    boton = next(
        (b for b in botones if "ContentPrincipal" in b[0] and "Buscar" in b[1]), None
    )
    if not campo:
        return [*salida, "- no hay campo de texto reconocible", ""]
    for consulta in (
        "IBERDROLA",
        "INDRA SISTEMAS",
        "INDUSTRIA DE DISEÑO TEXTIL",
        "ATRESMEDIA",
    ):
        datos = {**ocultos, campo: consulta}
        if boton:
            datos[boton[0]] = boton[1]
        try:
            r = c.post(final, data=datos, headers=CABECERAS)
        except httpx.HTTPError as exc:
            salida.append(f"- «{consulta}» → error {exc}")
            continue
        enlaces = sorted(
            set(
                re.findall(
                    r'href="([^"]*(?:nif=|qS=|ps_ac|Notificaciones)[^"]*)"', r.text
                )
            )
        )
        salida.append(
            f"- «{consulta}» → HTTP {r.status_code} · {len(r.text):,} caracteres ·"
            f" enlaces: {[html_lib.unescape(e) for e in enlaces[:8]]}"
        )
        salida.append(f"  - contenido: {contenido(r.text)[:400]!r}")
        time.sleep(1.0)
    return [*salida, ""]


CATEGORIAS = re.compile(
    r"(?i)^(ejecutiv[oa]s?|dominical(es)?|independientes?|otr[oa]s? extern[oa]s?)$"
)
FECHA = re.compile(r"^\d{2}/\d{2}/\d{4}$")


def filas_de_consejo(pdf: bytes) -> tuple[int, list[list[str]]]:
    """Las filas de tabla que parecen de un consejo: una categoría y fechas.

    No se busca la cabecera, que a veces cae en otra página, sino la forma de
    la fila. Devuelve (páginas, filas), y de cada fila SÓLO las cuatro
    primeras celdas que no son fechas —nombre, representante, categoría,
    cargo— y cuántas fechas trae. Ninguna fecha sale del runner: sin la
    cabecera no se puede saber si una es la de nacimiento.
    """
    import pdfplumber

    filas: list[list[str]] = []
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        for pagina in doc.pages:
            for tabla in pagina.extract_tables() or []:
                for fila in tabla:
                    celdas = [" ".join((c or "").split()) for c in fila]
                    if not any(CATEGORIAS.match(c) for c in celdas):
                        continue
                    fechas = [c for c in celdas if FECHA.match(c)]
                    if not fechas:
                        continue
                    textos = [c for c in celdas if c and not FECHA.match(c)]
                    # Sin la cabecera no se sabe si alguna fecha es la de
                    # nacimiento: de las fechas, sólo cuántas hay.
                    filas.append([*textos[:4], f"{len(fechas)} fechas"])
        return len(doc.pages), filas


def consejos(c: httpx.Client, empresas: dict[str, str]) -> list[str]:
    salida = ["### El consejo en el informe de gobierno corporativo, por filas", ""]
    for empresa, nif in empresas.items():
        codigo, cuerpo, tipo_o_error, _ = pedir(
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
        if not docs:
            # Por qué no: sin esto la vuelta anterior sólo dijo «sin informes»
            # y no se supo si era la página o la conexión.
            salida.append(
                f"- {empresa}: sin informes por NIF (HTTP {codigo}, {len(html):,}"
                f" caracteres, «{titulo(html)[:80]}», {tipo_o_error})"
            )
            continue
        codigo, pdf, _, _ = pedir(c, docs[0])
        if codigo != 200 or pdf[:4] != b"%PDF":
            salida.append(f"- {empresa}: el informe no es un PDF (HTTP {codigo})")
            continue
        paginas, filas = filas_de_consejo(pdf)
        categorias = Counter(
            next((x for x in f if CATEGORIAS.match(x)), "").lower() for f in filas
        )
        salida.append(
            f"- {empresa}: {paginas} páginas, {len(filas)} filas de consejo;"
            f" categorías {dict(categorias)}; forma de la primera: {[len(x) for x in filas[:1]]}"
        )
        if filas:
            (
                Path("ingest/tests/golden/cnmv") / f"{empresa}-consejo-filas.json"
            ).write_text(
                json.dumps(filas, ensure_ascii=False, indent=0), encoding="utf-8"
            )
        time.sleep(1.0)
    return [*salida, ""]


def directivos(c: httpx.Client, empresas: dict[str, str]) -> list[str]:
    """La forma de las notificaciones de directivos: columnas y tipos de fila.

    Traen personas estrechamente vinculadas —familiares—, así que de aquí no
    sale ningún nombre: sólo las cabeceras y cuántas filas hay de cada cargo.
    """
    salida = ["### Notificaciones de directivos: sólo la forma", ""]
    for empresa, nif in empresas.items():
        codigo, cuerpo, tipo_o_error, _ = pedir(
            c, urljoin(BASE, f"directivos-resultado.aspx?nif={nif}")
        )
        html = cuerpo.decode("utf-8", errors="replace")
        tablas_html = re.findall(r"<table.*?</table>", html, flags=re.S | re.I)
        salida.append(
            f"- {empresa}: HTTP {codigo}, {len(tablas_html)} tablas ({tipo_o_error})"
        )
        for t in tablas_html[:3]:
            cab = [
                texto(x)[:40]
                for x in re.findall(r"<th[^>]*>(.*?)</th>", t, flags=re.S | re.I)
            ]
            columnas = re.findall(r'data-th="([^"]*)"', t)
            salida.append(
                f"  - cabeceras: {cab[:12]}; columnas por data-th: {sorted(set(columnas))[:12]}"
            )
            cargos = Counter()
            for fila in re.findall(r"<tr.*?</tr>", t, flags=re.S | re.I):
                for col, valor in re.findall(
                    r'<td[^>]*data-th="([^"]*)"[^>]*>(.*?)</td>',
                    fila,
                    flags=re.S | re.I,
                ):
                    if re.search(r"(?i)cargo|relaci|v[ií]nculo|condici", col):
                        cargos[texto(valor)[:40]] += 1
            salida.append(f"  - valores de cargo o relación: {cargos.most_common(12)}")
        time.sleep(1.0)
    return [*salida, ""]


FECHA_EN = re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}")


def _enmascarar(celda: str | None) -> str:
    """Una celda con cualquier fecha sustituida: ninguna fecha sale del runner.

    Tampoco un año suelto: el BBVA publica «Año de nacimiento» en su propio
    cuadro, y un año no tiene forma de fecha. La octava vuelta lo dejó pasar
    (26/9/2026).
    """
    texto = FECHA_EN.sub("<fecha>", " ".join((celda or "").split()))
    return re.sub(r"^(19|20)\d\d$", "<año>", texto)


def _sin_nacimiento(filas: list[list[str]]) -> list[list[str]]:
    """Vacía la columna cuya cabecera habla de nacimiento, sea cual sea su forma."""
    if not filas:
        return filas
    malas = {j for j, h in enumerate(filas[0]) if re.search(r"(?i)nacimiento", h)}
    return [filas[0]] + [
        ["<retirado>" if j in malas and c else c for j, c in enumerate(f)]
        for f in filas[1:]
    ]


def iagc_del_ultimo_ejercicio(html: str) -> tuple[str, str, str]:
    """(ejercicio, registro, url) del IAGC más reciente, de su propia tabla.

    La página de gobierno corporativo tiene una tabla por tipo de informe; la
    del IAGC es `wGridIAGC_gridDatos`. Se elige por ejercicio, no por el orden.
    """
    i = html.find("wGridIAGC_gridDatos")
    if i < 0:
        return "", "", ""
    tabla = html[i : html.find("</table>", i)]
    mejor = ("", "", "")
    for fila in re.findall(r"<tr.*?</tr>", tabla, flags=re.S | re.I):
        ej = re.search(r'data-th="Ejercicio">\s*(\d{4})', fila)
        reg = re.search(r'data-th="N[^"]*registro oficial">\s*(\d+)', fila)
        url = re.search(
            r'href="(https://www\.cnmv\.es/webservices/verdocumento/ver\?e=[^"]+)"',
            fila,
        )
        if ej and url:
            candidato = (
                ej.group(1),
                reg.group(1) if reg else "",
                html_lib.unescape(url.group(1)),
            )
            if candidato[:2] > mejor[:2]:
                mejor = candidato
    return mejor


def tablas_de_consejo(pdf: bytes) -> tuple[int, list[dict]]:
    """Cada tabla del PDF con alguna fila de consejo, entera y sin fechas.

    De cada una: página, columnas, el texto que tiene justo encima (para
    distinguir el cuadro del consejo del de bajas o del de comisiones), si
    cerca se habla de nacimiento, y todas sus filas con las fechas
    enmascaradas. Las celdas vacías se dejan en su sitio: es la posición lo
    que se quiere ver.
    """
    import pdfplumber

    salida: list[dict] = []
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        for n, pagina in enumerate(doc.pages):
            for t in pagina.find_tables():
                filas = t.extract()
                if not any(
                    any(CATEGORIAS.match(" ".join((c or "").split())) for c in f)
                    for f in filas
                ):
                    continue
                arriba = pagina.crop(
                    (0, max(0, t.bbox[1] - 90), pagina.width, t.bbox[1])
                )
                encima = " ".join((arriba.extract_text() or "").split())
                salida.append(
                    {
                        "pagina": n + 1,
                        "columnas": max(len(f) for f in filas),
                        "encima": FECHA_EN.sub("<fecha>", encima[-300:]),
                        "nacimiento_en_la_pagina": bool(
                            re.search(r"(?i)nacimiento", pagina.extract_text() or "")
                        ),
                        "filas": _sin_nacimiento(
                            [[_enmascarar(c) for c in f] for f in filas]
                        ),
                    }
                )
        return len(doc.pages), salida


def consejos_enteros(c: httpx.Client, empresas: dict[str, str]) -> list[str]:
    salida = ["### El IAGC del último ejercicio, tabla a tabla", ""]
    for empresa, nif in empresas.items():
        codigo, cuerpo, tipo_o_error, _ = pedir(
            c, urljoin(BASE, f"ee/informaciongobcorp.aspx?nif={nif}")
        )
        html = cuerpo.decode("utf-8", errors="replace")
        ejercicio, registro, url = iagc_del_ultimo_ejercicio(html)
        if not url:
            salida.append(
                f"- {empresa}: sin IAGC en su tabla (HTTP {codigo}, {tipo_o_error})"
            )
            continue
        inicio = time.monotonic()
        codigo, pdf, _, _ = pedir(c, url)
        bajada = time.monotonic() - inicio
        if codigo != 200 or pdf[:4] != b"%PDF":
            salida.append(
                f"- {empresa}: el IAGC {ejercicio} no es un PDF (HTTP {codigo})"
            )
            continue
        inicio = time.monotonic()
        paginas, tablas = tablas_de_consejo(pdf)
        lectura = time.monotonic() - inicio
        salida.append(
            f"- {empresa}: IAGC {ejercicio} (registro {registro}), {len(pdf):,} bytes,"
            f" {paginas} páginas; bajada {bajada:.0f} s, lectura {lectura:.0f} s;"
            f" {len(tablas)} tablas con filas de consejo"
        )
        for t in tablas:
            salida.append(
                f"  - página {t['pagina']}, {t['columnas']} columnas, {len(t['filas'])} filas;"
                f" nacimiento en la página: {t['nacimiento_en_la_pagina']};"
                f" encima: «{t['encima'][-160:]}»"
            )
            salida.append(f"    - primera fila: {t['filas'][0]}")
        (
            Path("ingest/tests/golden/cnmv") / f"{empresa}-consejo-tablas.json"
        ).write_text(
            json.dumps(
                {
                    "ejercicio": ejercicio,
                    "registro": registro,
                    "paginas": paginas,
                    "tablas": tablas,
                },
                ensure_ascii=False,
                indent=0,
            ),
            encoding="utf-8",
        )
        time.sleep(1.0)
    return [*salida, ""]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="docs/fuentes/cnmv-reconocimiento.md")
    ap.add_argument("--golden", default="ingest/tests/golden/cnmv")
    args = ap.parse_args()
    salida = Path(args.salida)
    anterior = salida.read_text(encoding="utf-8") if salida.exists() else ""
    informe = [
        "# Reconocimiento: CNMV (consejos y participaciones de cotizadas)",
        "",
        f"Octava vuelta: {datetime.now(UTC).isoformat()} (`scripts/explorar_cnmv.py`).",
        "Las anteriores siguen debajo.",
        "",
        "## Octava vuelta: el consejo del IAGC, tabla a tabla",
        "",
    ]
    with httpx.Client(timeout=60.0, follow_redirects=True) as c:
        # La tercera vuelta llegó a los informes después de pasar por otras
        # páginas; la sexta entró en frío y no vio ninguno. Primero la
        # portada y la página de participaciones, que dejan la sesión hecha.
        codigo, _, tipo, _ = pedir(c, PORTADA)
        informe.append(f"- portada → HTTP {codigo} ({tipo}); cookies: {len(c.cookies)}")
        codigo, _, tipo, _ = pedir(
            c, urljoin(BASE, "derechosvoto/ps_ac_ini.aspx?nif=A28015865")
        )
        informe += [f"- participaciones de Telefónica → HTTP {codigo} ({tipo})", ""]
        muestra = {
            "telefonica": "A28015865",
            "prisa": "A28297059",
            "santander": "A39000013",
        }
        informe += consejos_enteros(
            c, {**muestra, "bbva": "A48265169", "repsol": "A78374725"}
        )
    if anterior:
        cuerpo_anterior = anterior.split("\n", 1)[1] if "\n" in anterior else anterior
        informe += ["", "---", "", cuerpo_anterior]
    salida.write_text("\n".join(informe) + "\n", encoding="utf-8")
    print("\n".join(informe[:120]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
