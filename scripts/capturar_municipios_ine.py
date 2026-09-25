#!/usr/bin/env python3
"""Captura la relación oficial de municipios del INE, con su provincia y comunidad.

Para qué: BDNS cuelga cada entidad local del nombre de su municipio
(«LOCAL > BERGA > AYUNTAMIENTO DE BERGA»), sin provincia ni comunidad. Con
la tabla del INE, ese nombre dice dónde está —sin adivinar nada— siempre que
sea único en España. Los que se repiten («Villanueva», «Castrillo») no se
resuelven: `territorio.py` sólo usa los nombres de un único municipio.

La tabla se commitea como CSV (`ingest/sinapsis_ingest/datos/municipios_ine.csv`)
porque la ingesta nocturna no debe depender de que el INE responda para
clasificar lo que ya sabe clasificar. Se regenera con este script cuando el
INE publique la del año siguiente.

El INE la publica como hoja de cálculo, con esta forma (fila de título, fila
de cabecera, datos):

    CODAUTO  CPRO  CMUN  DC  NOMBRE
    16       01    001   4   Alegría-Dulantzi

y escribe los artículos detrás: «Coruña, A», «Rozas de Madrid, Las». Aquí se
guarda el nombre tal cual; darle la vuelta es cosa de quien lo lee.

Uso (desde una máquina con salida a internet; el runner de Actions vale):

    python scripts/capturar_municipios_ine.py
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from datetime import UTC, datetime
from pathlib import Path

try:
    import httpx
except ImportError:  # pragma: no cover
    sys.exit("falta httpx: pip install httpx")

# El INE nombra el fichero por el año de referencia. Se prueban del más nuevo
# al más viejo: en enero el del año todavía no está.
ANIOS = range(datetime.now(UTC).year % 100, 19, -1)
URL = "https://www.ine.es/daco/daco42/codmun/diccionario{aa:02d}.xlsx"


def filas_de(contenido: bytes) -> list[list[str]]:
    import openpyxl

    libro = openpyxl.load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    hoja = libro.worksheets[0]
    return [["" if c is None else str(c).strip() for c in fila] for fila in hoja.iter_rows(values_only=True)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--destino", default="ingest/sinapsis_ingest/datos/municipios_ine.csv")
    ap.add_argument("--informe", default="docs/fuentes/ine-municipios.md")
    args = ap.parse_args()

    informe = [
        "# Relación de municipios del INE",
        "",
        f"Generado el {datetime.now(UTC).isoformat()} por `scripts/capturar_municipios_ine.py`.",
        "",
    ]
    elegido = None
    with httpx.Client(timeout=60.0, follow_redirects=True, headers={"User-Agent": "Sinapsis/0.1"}) as c:
        for aa in ANIOS:
            url = URL.format(aa=aa)
            try:
                r = c.get(url)
            except httpx.HTTPError as exc:
                informe.append(f"- `{url}` → error: {exc}")
                continue
            informe.append(f"- `{url}` → HTTP {r.status_code} · {len(r.content)} bytes")
            if r.status_code == 200 and r.content[:2] == b"PK":
                elegido = (url, r.content)
                break

    if elegido is None:
        informe.append("\n**Ninguna URL devolvió la hoja.** No se escribe nada.")
        Path(args.informe).write_text("\n".join(informe) + "\n", encoding="utf-8")
        print("\n".join(informe))
        return 1

    url, contenido = elegido
    filas = filas_de(contenido)
    cabecera_i = next(
        (i for i, f in enumerate(filas[:10]) if {"CPRO", "CMUN", "NOMBRE"} <= {x.upper() for x in f}),
        None,
    )
    if cabecera_i is None:
        informe.append("\n**La hoja no trae la cabecera esperada** (CPRO, CMUN, NOMBRE).")
        informe.append(f"Primeras filas: {filas[:3]}")
        Path(args.informe).write_text("\n".join(informe) + "\n", encoding="utf-8")
        print("\n".join(informe))
        return 1

    cab = [x.upper() for x in filas[cabecera_i]]
    i_auto = cab.index("CODAUTO") if "CODAUTO" in cab else None
    i_pro, i_mun, i_nom = cab.index("CPRO"), cab.index("CMUN"), cab.index("NOMBRE")
    salida = []
    for f in filas[cabecera_i + 1 :]:
        if len(f) <= max(i_pro, i_mun, i_nom) or not f[i_nom]:
            continue
        salida.append(
            {
                "codauto": f[i_auto].zfill(2) if i_auto is not None else "",
                "cpro": f[i_pro].zfill(2),
                "cmun": f[i_mun].zfill(3),
                "nombre": f[i_nom],
            }
        )

    destino = Path(args.destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8", newline="") as fh:
        fh.write(f"# Fuente: {url}\n# Capturado: {datetime.now(UTC).date().isoformat()}\n")
        w = csv.DictWriter(fh, fieldnames=["codauto", "cpro", "cmun", "nombre"])
        w.writeheader()
        w.writerows(salida)

    informe += [
        "",
        f"Hoja usada: `{url}`",
        f"Cabecera real: `{filas[cabecera_i]}`",
        f"Municipios: **{len(salida)}**",
        "",
        "Primeras filas:",
        "",
        *[f"- {s}" for s in salida[:5]],
        "",
        f"Guardado en `{destino}`.",
    ]
    Path(args.informe).parent.mkdir(parents=True, exist_ok=True)
    Path(args.informe).write_text("\n".join(informe) + "\n", encoding="utf-8")
    print("\n".join(informe))
    return 0


if __name__ == "__main__":
    sys.exit(main())
