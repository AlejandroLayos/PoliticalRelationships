#!/usr/bin/env python3
"""Captura una respuesta real de BDNS para usarla como golden test.

Guarda los bytes literales que devuelve la API, sin reformatear: el golden test
compara contra lo que la fuente manda de verdad, no contra una versión
embellecida.

Uso:

    python scripts/capturar_muestra_bdns.py \\
        --salida ingest/tests/golden/bdns_concesiones_real.json

Requiere salida a internet hacia www.infosubvenciones.es.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

try:
    import httpx
except ImportError:  # pragma: no cover
    sys.exit("falta httpx: pip install httpx")

ENDPOINT = "https://www.infosubvenciones.es/bdnstrans/api/concesiones/busqueda"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--salida",
        type=Path,
        default=Path("ingest/tests/golden/bdns_concesiones_real.json"),
        help="fichero donde guardar la muestra",
    )
    p.add_argument("--desde", default="01/01/2025", help="fechaDesde (dd/mm/aaaa)")
    p.add_argument("--hasta", default="31/01/2025", help="fechaHasta (dd/mm/aaaa)")
    p.add_argument(
        "--tamano",
        type=int,
        default=25,
        help="pageSize. Pequeño a propósito: la muestra se versiona en git",
    )
    args = p.parse_args()

    params = {
        "pageSize": args.tamano,
        "page": 0,
        "fechaDesde": args.desde,
        "fechaHasta": args.hasta,
    }

    print(f"GET {ENDPOINT} {params}", file=sys.stderr)
    try:
        resp = httpx.get(ENDPOINT, params=params, timeout=60.0)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"error descargando de BDNS: {exc}", file=sys.stderr)
        print(
            "No se escribe nada: una muestra a medias es peor que ninguna.",
            file=sys.stderr,
        )
        return 1

    contenido = resp.content

    # Comprobación mínima antes de guardar: que sea la envoltura que esperamos.
    try:
        datos = json.loads(contenido)
    except json.JSONDecodeError:
        print("la respuesta no es JSON; no la guardo", file=sys.stderr)
        return 1
    if not isinstance(datos, dict) or "content" not in datos:
        print(
            "la respuesta no trae 'content'. Puede que la API haya cambiado; "
            "revísala a mano antes de usarla como golden.",
            file=sys.stderr,
        )
        return 1

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_bytes(contenido)

    n = len(datos["content"])
    print(
        f"guardadas {len(contenido)} bytes con {n} concesiones en {args.salida}",
        file=sys.stderr,
    )
    print(
        "Revisa el fichero antes de commitearlo: puede traer nombres de "
        "personas físicas (spec §12, minimización de datos personales).",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
