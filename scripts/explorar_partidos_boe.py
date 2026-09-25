#!/usr/bin/env python3
"""Reconocimiento: la fiscalización de las cuentas de los partidos, en el BOE.

**Esto no es un conector.** Es mirar antes de escribirlo.

Para qué (spec §15, fase 7, línea 2 —financiación de partidos—): el Tribunal
de Cuentas fiscaliza cada año los estados contables de los partidos, y la
Comisión Mixta Congreso-Senado aprueba una resolución sobre cada informe que
se publica en el BOE. Su buscador web va con JavaScript y no se deja leer; el
BOE sí, y trae las tablas como tablas, no como un PDF.

Se busca con el buscador del propio BOE (varias formas de la consulta, por si
alguna no responde), y de cada disposición encontrada se lee el título de su
XML. La caché de la ingesta nocturna no sirve: sólo guarda los candidatos de
la sección II.A, no el sumario entero. De los informes más recientes se
describe la disposición: cuántas tablas, sus cabeceras y su tamaño.

Lo que se commitea: el informe (títulos, identificadores, forma de las
tablas) y, como muestra para los golden tests, la disposición más reciente
que sea el informe sobre las cuentas de los partidos. Es un documento
oficial sobre formaciones políticas, personas jurídicas.

Uso (desde una máquina con salida a internet; el runner de Actions vale):

    python scripts/explorar_partidos_boe.py
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

try:
    import httpx
except ImportError:  # pragma: no cover
    sys.exit("falta httpx: pip install httpx")

CABECERAS = {"User-Agent": "Sinapsis/0.1 (reconocimiento; proyecto abierto de transparencia)"}
XML = "https://www.boe.es/diario_boe/xml.php?id={}"

# El buscador del BOE, con el título como campo. Varias formas, porque los
# nombres de los parámetros no están documentados y se prueba cuál responde.
BUSQUEDAS = [
    "https://www.boe.es/buscar/boe.php?campo%5B1%5D=TIT&dato%5B1%5D={q}&operador%5B1%5D=and"
    "&sort_field%5B0%5D=FPU&sort_order%5B0%5D=desc&accion=Buscar",
    "https://www.boe.es/buscar/boe.php?campo%5B0%5D=TIT&dato%5B0%5D={q}&accion=Buscar",
    "https://www.boe.es/buscar/boe.php?campo%5B0%5D=TODOS&dato%5B0%5D={q}&accion=Buscar",
]
CONSULTAS = [
    "estados contables de los partidos políticos",
    "fiscalización partidos políticos",
]

# El informe anual del Tribunal de Cuentas sobre las cuentas de los partidos.
EL_INFORME = re.compile(r"estados contables de los partidos pol[ií]ticos", re.IGNORECASE)


def describir_tablas(xml: str) -> list[str]:
    tablas = re.findall(r"<table.*?</table>", xml, flags=re.S | re.I)
    lineas = [f"- tablas: **{len(tablas)}**; texto: {len(xml):,} caracteres"]
    for i, t in enumerate(tablas[:12]):
        filas = re.findall(r"<tr.*?</tr>", t, flags=re.S | re.I)
        primera = filas[0] if filas else ""
        celdas = [
            " ".join(re.sub(r"<[^>]+>", " ", c).split())[:40]
            for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", primera, flags=re.S | re.I)
        ]
        lineas.append(f"  - tabla {i + 1}: {len(filas)} filas; cabecera: {celdas[:10]}")
    return lineas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="docs/fuentes/partidos-boe-reconocimiento.md")
    ap.add_argument("--golden", default="ingest/tests/golden/partidos_boe")
    args = ap.parse_args()

    informe = [
        "# Reconocimiento: las cuentas de los partidos en el BOE",
        "",
        f"Generado el {datetime.now(UTC).isoformat()} por `scripts/explorar_partidos_boe.py`.",
        "",
    ]
    identificadores: list[str] = []
    with httpx.Client(timeout=60.0, follow_redirects=True, headers=CABECERAS) as c:
        for consulta in CONSULTAS:
            for plantilla in BUSQUEDAS:
                url = plantilla.format(q=quote_plus(consulta))
                try:
                    r = c.get(url)
                except httpx.HTTPError as exc:
                    informe += [f"- `{url}` → error: {exc}"]
                    continue
                ids = list(dict.fromkeys(re.findall(r"BOE-A-\d{4}-\d+", r.text)))
                informe.append(f"- «{consulta}» · `{url}` → HTTP {r.status_code}, {len(ids)} disposiciones")
                for i in ids:
                    if i not in identificadores:
                        identificadores.append(i)
                time.sleep(1.0)
        informe.append("")

        # El título de cada una, de su XML: lo que dice el BOE, no el buscador.
        hallados: list[dict[str, Any]] = []
        for ident in identificadores[:40]:
            try:
                r = c.get(XML.format(ident))
            except httpx.HTTPError:
                continue
            titulo = re.search(r"<titulo>(.*?)</titulo>", r.text, flags=re.S)
            fecha = re.search(r"<fecha_publicacion>(\d+)</fecha_publicacion>", r.text)
            dep = re.search(r"<departamento[^>]*>(.*?)</departamento>", r.text, flags=re.S)
            hallados.append(
                {
                    "identificador": ident,
                    "dia": fecha.group(1) if fecha else "",
                    "titulo": " ".join(titulo.group(1).split()) if titulo else "",
                    "_seccion": "",
                    "_departamento": " ".join(dep.group(1).split()) if dep else "",
                    "_xml": r.text if r.status_code == 200 else "",
                }
            )
            time.sleep(0.5)
    hallados.sort(key=lambda h: h["dia"])

    informe += [f"## Disposiciones encontradas: {len(hallados)}", ""]
    for h in hallados:
        informe.append(
            f"- {h['dia']} · `{h['identificador']}` · {h['_departamento'][:50]} · {h['titulo'][:220]}"
        )
    informe.append("")

    # De los informes sobre las cuentas de los partidos, los más recientes.
    informes = [h for h in hallados if EL_INFORME.search(h.get("titulo") or "")]
    informe += [f"## Informes sobre los estados contables: {len(informes)}", ""]
    golden = Path(args.golden)
    guardado = False
    for h in list(reversed(informes))[:3]:
        ident = h["identificador"]
        informe += [f"### `{ident}` ({h['dia']})", "", h["titulo"], ""]
        xml = h["_xml"]
        if not xml:
            informe += ["- sin XML", ""]
            continue
        informe += describir_tablas(xml)
        if not guardado and len(xml) < 6_000_000:
            golden.mkdir(parents=True, exist_ok=True)
            (golden / f"{ident}.xml").write_text(xml, encoding="utf-8")
            informe.append(f"- guardado como `{golden / (ident + '.xml')}`")
            guardado = True
        informe.append("")

    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.salida).write_text("\n".join(informe) + "\n", encoding="utf-8")
    print("\n".join(informe))
    return 0


if __name__ == "__main__":
    sys.exit(main())
