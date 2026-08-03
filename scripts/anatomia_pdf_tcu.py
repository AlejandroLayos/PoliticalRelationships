#!/usr/bin/env python3
"""Anatomía de los PDF del Tribunal de Cuentas.

El reconocimiento (`explorar_tcu.py`) ya contestó la primera pregunta: el TdC
no publica tablas HTML ni ficheros tabulares, sólo PDF. Queda la segunda, que
es la que decide el coste del conector y **no se puede responder mirando una
URL**:

1. ¿Tienen capa de texto o son escaneos? Un escaneo obliga a OCR, y el OCR
   sobre cifras de financiación introduce errores que un mapa de dinero
   público no se puede permitir.
2. ¿`pdfplumber` reconoce tablas, o el «cuadro» es texto maquetado con
   tabulaciones? Son dos parsers distintos.
3. ¿Cuántas páginas y con qué densidad? Decide si esto es un fin de semana o
   un mes.

Se responde descargando ficheros reales y midiéndolos. Nada de suponer.

## Lo que este script NO publica

Los expedientes sancionadores nombran a personas. Volcar su texto en un
informe que se commitea en un repositorio público sería repetir, con la
fuente más delicada del proyecto, el error que ya se cometió con los nombres
de particulares de BDNS.

Por eso hay dos salidas:

- **El informe Markdown** (`--salida`), que se commitea, lleva sólo
  estructura: páginas, si hay capa de texto, cuántas tablas y de qué forma.
  Números, no contenido.
- **El detalle** (`--detalle`), con el texto extraído, se sube como artefacto
  del workflow y no entra en git. Sirve para escribir el parser mirando datos
  reales sin publicarlos.

Uso:

    python scripts/anatomia_pdf_tcu.py \
        --salida docs/fuentes/tcu-anatomia-pdf.md \
        --detalle detalle-pdf/
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

try:
    import httpx
except ImportError:  # pragma: no cover
    sys.exit("falta httpx: pip install httpx")

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    sys.exit("falta pdfplumber: pip install pdfplumber")

from explorar_tcu import CABECERAS_HTML, TIMEOUT, _completar_cadena

# Sacados del reconocimiento del 2026-08-03, no inventados: son los enlaces
# que la propia página de sanciones a partidos publica.
# Ver docs/fuentes/tcu-reconocimiento.md.
BASE = "https://www.tcu.es/export/sites/portal/.galleries/Documentos-oficiales/Partidos-politicos/"
OBJETIVOS = [
    f"{BASE}Procedimientos-sancionadores-contabilidad-electoral-2015.pdf",
    f"{BASE}Procedimientos-sancionadores-contabilidad-electoral-2019.pdf",
    f"{BASE}Procedimientos-sancionadores-contabilidad-electoral-2023.pdf",
    f"{BASE}Procedimientos-sancionadores-contabilidad-ordinaria.pdf",
]

# Un PDF con capa de texto da miles de caracteres por página. Un escaneo da
# cero, o unas pocas decenas si lleva una portada generada.
UMBRAL_CAPA_TEXTO = 200


def descargar(cliente: httpx.Client, url: str) -> bytes | None:
    try:
        r = cliente.get(url)
        r.raise_for_status()
        return r.content
    except httpx.HTTPError as exc:
        print(f"  no se pudo descargar: {exc}", file=sys.stderr)
        return None


def _tablas_por_texto(pagina) -> list:
    """Busca tablas por alineación de texto, no por líneas dibujadas.

    Muchos cuadros oficiales no llevan bordes: son columnas alineadas. La
    estrategia por defecto de pdfplumber no los ve. Esta sí, a costa de
    encontrar a veces «tablas» donde sólo hay párrafos alineados — por eso se
    informan las dos por separado y no se mezclan.
    """
    try:
        return (
            pagina.extract_tables({"vertical_strategy": "text", "horizontal_strategy": "text"})
            or []
        )
    except Exception:
        return []


def analizar(datos: bytes, destino_detalle: Path | None) -> dict:
    """Mide el PDF. Devuelve sólo estructura; el texto va al detalle."""
    import io

    info: dict = {"bytes": len(datos)}
    textos: list[str] = []
    try:
        with pdfplumber.open(io.BytesIO(datos)) as pdf:
            info["paginas"] = len(pdf.pages)
            caracteres: list[int] = []
            formas: list[tuple[int, int]] = []
            # Muestrear: en un PDF de 300 páginas no hace falta abrirlas todas
            # para saber si tiene capa de texto y si hay tablas.
            muestra = pdf.pages[:15]
            info["paginas_analizadas"] = len(muestra)
            formas_texto: list[tuple[int, int]] = []
            for pagina in muestra:
                texto = pagina.extract_text() or ""
                caracteres.append(len(texto))
                textos.append(texto)
                # Dos estrategias, porque distinguen dos mundos. La de por
                # defecto se apoya en las líneas de la tabla; si el cuadro no
                # lleva bordes no encuentra nada aunque esté ahí. Se comprobó
                # con un PDF de prueba con tabla sin bordes: 0 tablas.
                for tabla in pagina.extract_tables() or []:
                    if tabla:
                        formas.append((len(tabla), len(tabla[0])))
                for tabla in _tablas_por_texto(pagina):
                    if tabla:
                        formas_texto.append((len(tabla), len(tabla[0])))
            info["caracteres_por_pagina"] = caracteres
            info["caracteres_media"] = sum(caracteres) // max(len(caracteres), 1)
            info["capa_texto"] = info["caracteres_media"] >= UMBRAL_CAPA_TEXTO
            info["n_tablas"] = len(formas)
            info["formas_tablas"] = formas[:20]
            info["n_tablas_texto"] = len(formas_texto)
            info["formas_tablas_texto"] = formas_texto[:20]
    except Exception as exc:
        info["error"] = f"{type(exc).__name__}: {exc}"
        return info

    if destino_detalle is not None:
        # El texto completo NO va al informe commiteado: nombra a personas.
        destino_detalle.write_text("\n\n--- página ---\n\n".join(textos), encoding="utf-8")
    return info


def formatear(resultados: list[dict]) -> str:
    hoy = datetime.now(UTC).isoformat()
    lineas = [
        "# Anatomía de los PDF del Tribunal de Cuentas",
        "",
        f"Generado automáticamente el {hoy} por `scripts/anatomia_pdf_tcu.py`.",
        "",
        "Responde a la pregunta que decide el coste del conector: si estos PDF",
        "tienen capa de texto o son escaneos, y si `pdfplumber` reconoce sus",
        "tablas. Medido sobre ficheros reales descargados del organismo.",
        "",
        "**Aquí sólo hay estructura, nunca contenido.** Los expedientes",
        "sancionadores nombran a personas; el texto extraído se sube como",
        "artefacto del workflow y no entra en git. Ver [spec §12](../spec.md).",
        "",
    ]
    for r in resultados:
        lineas.append(f"## `{r['nombre']}`")
        lineas.append("")
        lineas.append(f"- URL: `{r['url']}`")
        if r.get("no_descargado"):
            lineas.append("- **No se pudo descargar.**")
            lineas.append("")
            continue
        if r.get("error"):
            lineas.append(f"- **Ilegible:** `{r['error']}`")
            lineas.append("")
            continue
        lineas.append(f"- {r['bytes']:,} bytes · **{r['paginas']} páginas**")
        lineas.append(f"- Páginas analizadas: {r['paginas_analizadas']}")
        capa = "sí" if r["capa_texto"] else "**NO — es un escaneo, haría falta OCR**"
        lineas.append(f"- ¿Capa de texto?: {capa} ({r['caracteres_media']} car./página de media)")
        lineas.append(f"- Tablas con bordes (estrategia por líneas): **{r['n_tablas']}**")
        if r.get("formas_tablas"):
            formas = ", ".join(f"{f}x{c}" for f, c in r["formas_tablas"])
            lineas.append(f"  - Formas (filas x columnas): {formas}")
        lineas.append(
            f"- Tablas sin bordes (estrategia por texto): **{r.get('n_tablas_texto', 0)}**"
        )
        if r.get("formas_tablas_texto"):
            formas = ", ".join(f"{f}x{c}" for f, c in r["formas_tablas_texto"])
            lineas.append(f"  - Formas (filas x columnas): {formas}")
        lineas.append("")

    con_texto = [r for r in resultados if r.get("capa_texto")]
    con_bordes = [r for r in resultados if r.get("n_tablas", 0) > 0]
    con_alineacion = [r for r in resultados if r.get("n_tablas_texto", 0) > 0]
    lineas += [
        "---",
        "",
        "## Veredicto",
        "",
        f"- Con capa de texto: **{len(con_texto)} de {len(resultados)}**",
        f"- Con tablas con bordes: **{len(con_bordes)} de {len(resultados)}**",
        f"- Con tablas sin bordes: **{len(con_alineacion)} de {len(resultados)}**",
        "",
        "Lectura, de más barato a más caro:",
        "",
        "1. **Capa de texto + tablas con bordes** → conector medio:",
        "   `pdfplumber` con la estrategia por líneas, golden test con una",
        "   muestra real guardada, y a funcionar.",
        "2. **Capa de texto + tablas sólo por alineación** → el cuadro no",
        "   lleva bordes; se reconstruye por posiciones. Funciona, pero es",
        "   frágil: cualquier rediseño del PDF lo rompe. Exige golden tests y",
        "   tolerar el hueco cuando cambien el formato.",
        "3. **Capa de texto sin ninguna tabla** → es prosa, no un cuadro. Hay",
        "   que extraer con expresiones regulares sobre el texto corrido, que",
        "   es lo más frágil de todo.",
        "4. **Sin capa de texto** → OCR. Sobre cifras de financiación un error",
        "   de OCR es un dato falso con aspecto de dato bueno. Antes de ir por",
        "   ahí conviene agotar la vía de pedir los datos al organismo.",
        "",
        "La distinción 1 vs 2 importa y por eso se miden las dos estrategias:",
        "la de por defecto se apoya en las líneas dibujadas y devuelve cero",
        "tablas en un cuadro sin bordes aunque el cuadro esté ahí. Quedarse",
        "sólo con ella haría parecer caro algo que no lo es.",
        "",
        "Nada de esto se decide por lo que «suele pasar» con los PDF de la",
        "administración: se decide por los números de arriba.",
    ]
    return "\n".join(lineas) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--salida", type=Path, default=Path("docs/fuentes/tcu-anatomia-pdf.md"))
    p.add_argument(
        "--detalle",
        type=Path,
        default=None,
        help="carpeta donde volcar el texto extraído (artefacto, NO se commitea)",
    )
    p.add_argument("--url", action="append", help="analizar esta URL en vez de las conocidas")
    args = p.parse_args()

    urls = args.url or OBJETIVOS
    if args.detalle:
        args.detalle.mkdir(parents=True, exist_ok=True)

    # www.tcu.es omite el certificado intermedio; se completa por AIA igual
    # que en el reconocimiento, sin desactivar la verificación.
    bundle = _completar_cadena("www.tcu.es")
    verify = bundle if bundle else True

    resultados = []
    with httpx.Client(
        timeout=TIMEOUT, follow_redirects=True, headers=CABECERAS_HTML, verify=verify
    ) as cliente:
        for url in urls:
            nombre = url.rsplit("/", 1)[-1]
            print(f"descargando {nombre}…", file=sys.stderr)
            datos = descargar(cliente, url)
            if datos is None:
                resultados.append({"nombre": nombre, "url": url, "no_descargado": True})
                continue
            destino = (args.detalle / f"{nombre}.txt") if args.detalle else None
            info = analizar(datos, destino)
            info.update({"nombre": nombre, "url": url})
            estado = "error" if info.get("error") else f"{info['paginas']} pág."
            print(f"  {estado}", file=sys.stderr)
            resultados.append(info)

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(formatear(resultados), encoding="utf-8")
    print(f"informe escrito en {args.salida}", file=sys.stderr)

    # Igual que en el reconocimiento: no responder es un hallazgo, no un fallo.
    if not any(r.get("paginas") for r in resultados):
        print("::warning title=Ningún PDF legible::el informe registra por qué")
    return 0


if __name__ == "__main__":
    sys.exit(main())
