#!/usr/bin/env python3
"""Guarda una muestra real de un PDF del Tribunal de Cuentas.

CLAUDE.md lo pide explícitamente: «en parsers de fuentes, golden tests
obligatorios (muestra real guardada → salida esperada). Los formatos oficiales
cambian sin avisar». Un parser de PDF probado sólo contra un PDF que me he
inventado yo no prueba nada: prueba que sé generar el fichero que sé leer.

El entorno de desarrollo no alcanza `www.tcu.es`, así que la captura ocurre en
el runner y el fichero se commitea.

Qué se guarda y por qué se puede guardar: el expediente sancionador de 2019,
que es el más pequeño de los cuatro (305 KB, 3 páginas) y trae las mismas
columnas que el resto. Es un documento oficial publicado por el organismo
sobre **formaciones políticas**, no sobre particulares — el perfil de columnas
de `anatomia_pdf_tcu.py` confirmó que la columna de identificador lleva NIF de
persona jurídica. Si algún día la muestra elegida contuviera datos de personas
físicas, no se commitea: se usa como artefacto y el golden test se construye
sobre la parte no personal.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

try:
    import httpx
except ImportError:  # pragma: no cover
    sys.exit("falta httpx: pip install httpx")

from explorar_tcu import CABECERAS_HTML, TIMEOUT, _completar_cadena

URL = (
    "https://www.tcu.es/export/sites/portal/.galleries/Documentos-oficiales/"
    "Partidos-politicos/Procedimientos-sancionadores-contabilidad-electoral-2019.pdf"
)

# Si el organismo republica el documento, el hash cambia y conviene enterarse:
# el golden test dejaría de reflejar lo que la fuente sirve hoy. No se falla
# por ello —el formato oficial cambia sin avisar y eso es justo lo que el
# golden test existe para detectar—, pero se deja constancia.
MAX_BYTES = 5 * 1024 * 1024


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--destino", type=Path, required=True)
    p.add_argument("--url", default=URL)
    args = p.parse_args()

    bundle = _completar_cadena("www.tcu.es")
    verify = bundle if bundle else True

    try:
        with httpx.Client(
            timeout=TIMEOUT, follow_redirects=True, headers=CABECERAS_HTML, verify=verify
        ) as cliente:
            r = cliente.get(args.url)
            r.raise_for_status()
    except httpx.HTTPError as exc:
        # Tolerar el hueco: que la fuente no responda hoy no debe romper el
        # workflow ni borrar la muestra que ya hubiera guardada.
        print(f"::warning title=No se pudo capturar la muestra::{exc}")
        return 0

    datos = r.content
    if not datos.startswith(b"%PDF"):
        print("::warning title=La respuesta no es un PDF::no se guarda nada")
        return 0
    if len(datos) > MAX_BYTES:
        print(f"::warning title=Muestra demasiado grande::{len(datos)} bytes, no se guarda")
        return 0

    digest = hashlib.sha256(datos).hexdigest()
    if args.destino.exists() and hashlib.sha256(args.destino.read_bytes()).hexdigest() == digest:
        print(f"la muestra no ha cambiado ({digest[:12]}…)", file=sys.stderr)
        return 0

    args.destino.parent.mkdir(parents=True, exist_ok=True)
    args.destino.write_bytes(datos)
    print(f"muestra guardada en {args.destino} ({len(datos):,} bytes, sha256 {digest[:12]}…)")
    print(f"::notice title=Muestra del TdC actualizada::sha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
