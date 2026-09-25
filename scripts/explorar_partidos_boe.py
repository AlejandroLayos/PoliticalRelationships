#!/usr/bin/env python3
"""Reconocimiento: la fiscalización de las cuentas de los partidos, en el BOE.

**Esto no es un conector.** Es mirar antes de escribirlo.

Para qué (spec §15, fase 7, línea 2 —financiación de partidos—): el Tribunal
de Cuentas fiscaliza cada año los estados contables de los partidos, y la
Comisión Mixta Congreso-Senado aprueba una resolución sobre cada informe que
se publica en el BOE. Su buscador web va con JavaScript y no se deja leer; el
BOE sí, y trae las tablas como tablas, no como un PDF.

No se busca a ciegas: se recorren los sumarios del BOE que ya guarda la caché
de la ingesta nocturna (`/tmp/cache-boe/sumarios`, la restaura el workflow) y
se anotan los títulos que hablan de partidos o de su fiscalización. De los
más recientes se baja la disposición y se describe: cuántas tablas, sus
cabeceras y su tamaño.

Lo que se commitea: el informe (títulos, identificadores, forma de las
tablas) y, como muestra para los golden tests, la disposición más reciente
que sea el informe sobre las cuentas de los partidos. Es un documento
oficial sobre formaciones políticas, personas jurídicas.

Uso (en el runner de Actions, con la caché del BOE restaurada):

    python scripts/explorar_partidos_boe.py --cache /tmp/cache-boe
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover
    sys.exit("falta httpx: pip install httpx")

CABECERAS = {"User-Agent": "Sinapsis/0.1 (reconocimiento; proyecto abierto de transparencia)"}
XML = "https://www.boe.es/diario_boe/xml.php?id={}"

# Lo que interesa: la fiscalización de las cuentas de los partidos y de sus
# fundaciones, y las subvenciones a los grupos o a los gastos electorales.
TITULOS = re.compile(
    r"(estados contables de los partidos|partidos pol[ií]ticos|formaciones pol[ií]ticas"
    r"|financiaci[oó]n de (los )?partidos|subvenciones? (electorales|a (los )?partidos))",
    re.IGNORECASE,
)
EL_INFORME = re.compile(r"estados contables de los partidos pol[ií]ticos", re.IGNORECASE)


def items(sumario: dict[str, Any]) -> list[dict[str, Any]]:
    """Todos los ítems de un sumario, con su sección y departamento."""
    salida = []

    def lista(x: Any) -> list[Any]:
        return x if isinstance(x, list) else [x] if x else []

    datos = sumario.get("data") or {}
    for diario in lista((datos.get("sumario") or {}).get("diario")):
        for seccion in lista(diario.get("seccion")):
            codigo = str(seccion.get("codigo", ""))
            for dep in lista(seccion.get("departamento")):
                nombre = dep.get("nombre") or ""
                colgados = [*lista(dep.get("item"))]
                for ep in lista(dep.get("epigrafe")):
                    colgados += lista(ep.get("item"))
                for it in colgados:
                    if isinstance(it, dict):
                        salida.append({**it, "_seccion": codigo, "_departamento": nombre})
    return salida


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
    ap.add_argument("--cache", default="/tmp/cache-boe")
    ap.add_argument("--salida", default="docs/fuentes/partidos-boe-reconocimiento.md")
    ap.add_argument("--golden", default="ingest/tests/golden/partidos_boe")
    args = ap.parse_args()

    sumarios = sorted(Path(args.cache, "sumarios").rglob("*.json"))
    informe = [
        "# Reconocimiento: las cuentas de los partidos en el BOE",
        "",
        f"Generado el {datetime.now(UTC).isoformat()} por `scripts/explorar_partidos_boe.py`.",
        "",
        f"Sumarios recorridos en la caché: **{len(sumarios)}**"
        + (f" (del {sumarios[0].stem} al {sumarios[-1].stem})" if sumarios else ""),
        "",
    ]
    hallados: list[dict[str, Any]] = []
    for ruta in sumarios:
        try:
            sumario = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for it in items(sumario):
            titulo = it.get("titulo") or ""
            if TITULOS.search(titulo):
                hallados.append({"dia": ruta.stem, **it})

    informe += [f"## Títulos que hablan de partidos: {len(hallados)}", ""]
    for h in hallados[-80:]:
        informe.append(
            f"- {h['dia']} · `{h.get('identificador', '')}` · sección {h['_seccion']} · "
            f"{h['_departamento'][:50]} · {(h.get('titulo') or '')[:220]}"
        )
    informe.append("")

    # De los informes sobre las cuentas de los partidos, los más recientes.
    informes = [h for h in hallados if EL_INFORME.search(h.get("titulo") or "")]
    informe += [f"## Informes sobre los estados contables: {len(informes)}", ""]
    golden = Path(args.golden)
    guardado = False
    with httpx.Client(timeout=60.0, follow_redirects=True, headers=CABECERAS) as c:
        for h in list(reversed(informes))[:3]:
            ident = h.get("identificador", "")
            informe += [f"### `{ident}` ({h['dia']})", "", f"{h.get('titulo', '')}", ""]
            try:
                r = c.get(XML.format(ident))
            except httpx.HTTPError as exc:
                informe += [f"- error: {exc}", ""]
                continue
            informe.append(f"- HTTP {r.status_code} · `{r.headers.get('content-type', '')}` · {len(r.content):,} bytes")
            if r.status_code == 200:
                informe += describir_tablas(r.text)
                if not guardado and len(r.content) < 6_000_000:
                    golden.mkdir(parents=True, exist_ok=True)
                    (golden / f"{ident}.xml").write_bytes(r.content)
                    informe.append(f"- guardado como `{golden / (ident + '.xml')}`")
                    guardado = True
            informe.append("")
            time.sleep(1.0)

    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.salida).write_text("\n".join(informe) + "\n", encoding="utf-8")
    print("\n".join(informe))
    return 0


if __name__ == "__main__":
    sys.exit(main())
