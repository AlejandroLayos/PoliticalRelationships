#!/usr/bin/env python3
"""Reconocimiento: los nombramientos de las altas instancias judiciales en el BOE.

**Esto no es un conector.** Es mirar antes de escribirlo.

Para qué (spec §12, ampliación del 26/9/2026): Tribunal Supremo, Tribunal
Constitucional, CGPJ, Audiencia Nacional, presidencias de los TSJ, Fiscal
General y fiscales de sala salen con nombre por su nombramiento en el BOE. El
conector del BOE los descartaba a propósito (`cargos._CARRERAS`), y su caché
sólo guarda lo que entonces era candidato, así que no están. Se buscan con el
buscador del propio BOE —los códigos de sus campos se leen del formulario—, y
de cada disposición se lee el título y el departamento de su XML.

Lo que se commitea: el informe (consultas, recuentos, títulos) y unas cuantas
disposiciones como muestra para los golden tests. Son nombramientos oficiales
para cargos públicos.

## Segunda vuelta

La primera (commit f1b53e4) gastó su tope de 120 disposiciones en las dos
primeras consultas —el Supremo y el Constitucional, que tienen muchas— y no
llegó al CGPJ, los TSJ, la Audiencia Nacional ni la Fiscalía. Ahora el tope es
por consulta, se guardan muestras de cada una (nombramiento y cese) y se
anota cómo pagina el buscador y qué etiquetas trae el XML.

Uso (desde una máquina con salida a internet; el runner de Actions vale):

    python scripts/explorar_justicia_boe.py
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover
    sys.exit("falta httpx: pip install httpx")

CABECERAS = {"User-Agent": "Sinapsis/0.1 (reconocimiento; proyecto abierto de transparencia)"}
FORMULARIO = "https://www.boe.es/buscar/boe.php"
XML = "https://www.boe.es/diario_boe/xml.php?id={}"

CONSULTAS = [
    "Magistrado del Tribunal Supremo",
    "Presidente de la Sala del Tribunal Supremo",
    "Presidente del Tribunal Supremo",
    "Magistrado del Tribunal Constitucional",
    "Presidente del Tribunal Constitucional",
    "Vocal del Consejo General del Poder Judicial",
    "Presidente del Tribunal Superior de Justicia",
    "Presidente de la Audiencia Nacional",
    "Presidente de la Sala de la Audiencia Nacional",
    "Fiscal de Sala",
    "Fiscal General del Estado",
    "Teniente Fiscal del Tribunal Supremo",
]
POR_CONSULTA = 15
MUESTRAS_POR_CONSULTA = 2

NOMBRAMIENTO = re.compile(r"(?i)por (el|la) que se (nombra|promueve)")
CESE = re.compile(r"(?i)por (el|la) que se (declara el cese|dispone el cese|declara la jubilaci)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="docs/fuentes/justicia-boe-reconocimiento.md")
    ap.add_argument("--golden", default="ingest/tests/golden/boe_justicia")
    args = ap.parse_args()
    golden = Path(args.golden)

    informe = [
        "# Reconocimiento: altas instancias judiciales y fiscales en el BOE",
        "",
        f"Generado el {datetime.now(UTC).isoformat()} por `scripts/explorar_justicia_boe.py`.",
        "",
    ]
    identificadores: list[str] = []
    por_consulta: dict[str, list[str]] = {}
    with httpx.Client(timeout=60.0, follow_redirects=True, headers=CABECERAS) as c:
        html = c.get(FORMULARIO).text
        ocultos = re.findall(
            r'<input[^>]*type="hidden"[^>]*name="(campo\[\d+\])"[^>]*value="([^"]*)"',
            html,
            flags=re.I,
        )
        titulo = next(((n, v) for n, v in ocultos if v == "TITULOS"), None)
        informe += [f"Campos del formulario: {ocultos}", ""]
        if not titulo:
            informe.append("**No hay campo de título en el formulario: el buscador ha cambiado.**")
        else:
            indice = re.search(r"\d+", titulo[0]).group(0)
            for consulta in CONSULTAS:
                r = c.get(
                    FORMULARIO,
                    params={
                        f"campo[{indice}]": "TITULOS",
                        f"dato[{indice}]": consulta,
                        f"operador[{indice}]": "and",
                        "page_hits": "50",
                        "sort_field[0]": "FPU",
                        "sort_order[0]": "desc",
                        "accion": "Buscar",
                    },
                )
                ids = list(dict.fromkeys(re.findall(r"BOE-A-\d{4}-\d+", r.text)))
                total = re.search(
                    r"([\d.]+)\s+(?:resultados?|documentos?|disposiciones)", r.text, flags=re.I
                )
                informe.append(
                    f"- «{consulta}» → HTTP {r.status_code}, {len(ids)} en la primera página"
                    + (f", total {total.group(1)}" if total else "")
                )
                if consulta == CONSULTAS[0]:
                    # Cómo pagina: los enlaces de «siguiente» y el texto del recuento.
                    paginas = sorted(
                        set(
                            re.findall(
                                r'href="([^"]*(?:pag|page|accion=Mas)[^"]*)"', r.text, flags=re.I
                            )
                        )
                    )
                    informe.append(
                        f"  - enlaces de paginación: {[p.replace('&amp;', '&')[:200] for p in paginas[:6]]}"
                    )
                    recuento = re.search(
                        r"[^<>]{0,80}\b(?:resultado|encontrad)[^<>]{0,80}", r.text, flags=re.I
                    )
                    informe.append(
                        f"  - texto del recuento: {recuento.group(0).strip() if recuento else '(no aparece)'!r}"
                    )
                por_consulta[consulta] = ids
                for i in ids:
                    if i not in identificadores:
                        identificadores.append(i)
                time.sleep(1.0)
        informe.append("")

        hallados: list[dict[str, Any]] = []
        # Tope por consulta: cada una aporta sus primeras POR_CONSULTA que no
        # haya aportado otra antes.
        elegidos: list[tuple[str, str]] = []
        usados: set[str] = set()
        for consulta, ids in por_consulta.items():
            nuevos = [i for i in ids if i not in usados][:POR_CONSULTA]
            usados.update(nuevos)
            elegidos += [(consulta, i) for i in nuevos]
        for consulta, ident in elegidos:
            try:
                r = c.get(XML.format(ident))
            except httpx.HTTPError:
                continue
            t = re.search(r"<titulo>(.*?)</titulo>", r.text, flags=re.S)
            f = re.search(r"<fecha_publicacion>(\d+)</fecha_publicacion>", r.text)
            d = re.search(r"<departamento[^>]*>(.*?)</departamento>", r.text, flags=re.S)
            s = re.search(r"<seccion>(.*?)</seccion>", r.text)
            hallados.append(
                {
                    "consulta": consulta,
                    "id": ident,
                    "dia": f.group(1) if f else "",
                    "titulo": " ".join(t.group(1).split()) if t else "",
                    "departamento": " ".join(d.group(1).split()) if d else "",
                    "seccion": s.group(1) if s else "",
                    "xml": r.text if r.status_code == 200 else "",
                }
            )
            time.sleep(0.4)

    hallados.sort(key=lambda h: h["dia"], reverse=True)
    informe += [
        f"## Disposiciones: {len(hallados)}",
        "",
        f"Departamentos: {Counter(h['departamento'] for h in hallados).most_common(10)}",
        f"Secciones: {Counter(h['seccion'] for h in hallados).most_common(5)}",
        "",
    ]
    for consulta in CONSULTAS:
        suyos = [h for h in hallados if h["consulta"] == consulta]
        informe += ["", f"### «{consulta}» ({len(suyos)})", ""]
        informe += [
            f"- {h['dia']} · `{h['id']}` · {h['seccion']} · {h['departamento'][:40]} · {h['titulo'][:220]}"
            for h in suyos
        ]
    informe.append("")

    # La forma del XML de una disposición: qué etiquetas trae y cuáles se repiten.
    con_xml = [h for h in hallados if h["xml"]]
    if con_xml:
        etiquetas = Counter(re.findall(r"<([a-z_]+)[\s>]", con_xml[0]["xml"]))
        informe += [
            "## Forma del XML",
            "",
            f"`{con_xml[0]['id']}`: {etiquetas.most_common(40)}",
            "",
        ]
        meta = re.search(r"<metadatos>.*?</metadatos>", con_xml[0]["xml"], flags=re.S)
        if meta:
            informe += ["```xml", meta.group(0)[:2500], "```", ""]

    # Muestras: por consulta, hasta dos nombramientos y un cese.
    golden.mkdir(parents=True, exist_ok=True)
    guardados = 0
    for consulta in CONSULTAS:
        suyos = [h for h in hallados if h["consulta"] == consulta and h["xml"]]
        nombramientos = [h for h in suyos if NOMBRAMIENTO.search(h["titulo"])][
            :MUESTRAS_POR_CONSULTA
        ]
        ceses = [h for h in suyos if CESE.search(h["titulo"])][:1]
        for h in nombramientos + ceses:
            destino = golden / f"{h['id']}.xml"
            if not destino.exists():
                destino.write_text(h["xml"], encoding="utf-8")
                guardados += 1
    informe.append(f"Muestras nuevas guardadas en `{golden}`: {guardados}")

    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.salida).write_text("\n".join(informe) + "\n", encoding="utf-8")
    print("\n".join(informe))
    return 0


if __name__ == "__main__":
    sys.exit(main())
