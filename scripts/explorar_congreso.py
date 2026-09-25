#!/usr/bin/env python3
"""Reconocimiento de los datos abiertos del Congreso: diputados y su formación.

**Esto no es un conector.** Es mirar antes de escribirlo.

Para qué (spec §15, fase 7, línea 4 —contexto de gobierno— y línea 3): el
Congreso publica quién fue diputado en cada legislatura, por qué formación y
en qué grupo. Es una de las fuentes oficiales que la regla de §12 admite para
nombrar a una persona, y la que da el partido: de qué formación era un
ministro que fue diputado, y qué formación gobernaba cuando se pagó algo.

Lo que se commitea: el informe (enlaces, formatos, claves, recuentos) y una
muestra de los ficheros de datos para los golden tests. Son diputados en su
papel de diputados.

Uso (desde una máquina con salida a internet; el runner de Actions vale):

    python scripts/explorar_congreso.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    import httpx
except ImportError:  # pragma: no cover
    sys.exit("falta httpx: pip install httpx")

PORTADA = "https://www.congreso.es/es/opendata/diputados"
CABECERAS = {"User-Agent": "Sinapsis/0.1 (reconocimiento; proyecto abierto de transparencia)"}
TOPE = 90.0


def pedir(cliente: httpx.Client, url: str) -> tuple[int, bytes, str]:
    print(f"→ {url}", flush=True)
    inicio = time.monotonic()
    try:
        with cliente.stream("GET", url, headers=CABECERAS) as r:
            trozos = []
            for t in r.iter_bytes():
                trozos.append(t)
                if time.monotonic() - inicio > TOPE:
                    return 0, b"", "cortado"
            return r.status_code, b"".join(trozos), r.headers.get("content-type", "")
    except httpx.HTTPError as exc:
        return 0, b"", f"error: {exc}"


def forma(valor, profundidad: int = 0):
    if profundidad > 6:
        return "…"
    if isinstance(valor, dict):
        return {k: forma(v, profundidad + 1) for k, v in list(valor.items())[:30]}
    if isinstance(valor, list):
        return [forma(valor[0], profundidad + 1)] if valor else []
    if isinstance(valor, str):
        return f"str[{len(valor)}]"
    return type(valor).__name__


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="docs/fuentes/congreso-reconocimiento.md")
    ap.add_argument("--golden", default="ingest/tests/golden/congreso")
    args = ap.parse_args()
    golden = Path(args.golden)
    golden.mkdir(parents=True, exist_ok=True)

    informe = [
        "# Reconocimiento: datos abiertos del Congreso (diputados)",
        "",
        f"Generado el {datetime.now(UTC).isoformat()} por `scripts/explorar_congreso.py`.",
        "",
    ]
    with httpx.Client(timeout=45.0, follow_redirects=True) as c:
        codigo, contenido, tipo = pedir(c, PORTADA)
        informe += [f"## `{PORTADA}`", "", f"HTTP {codigo} · `{tipo}` · {len(contenido)} bytes", ""]
        if codigo != 200:
            Path(args.salida).write_text("\n".join(informe) + "\n", encoding="utf-8")
            print("\n".join(informe))
            return 1
        html = contenido.decode("utf-8", errors="replace")
        enlaces = []
        for href, texto in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, flags=re.DOTALL):
            destino = urljoin(PORTADA, href.replace("&amp;", "&"))
            ruta = urlparse(destino).path.lower()
            texto = " ".join(re.sub(r"<[^>]+>", " ", texto).split())
            if re.search(r"\.(json|csv|xml)$", ruta) or "opendata" in ruta and ("json" in ruta or "csv" in ruta or "xml" in ruta):
                enlaces.append((destino, texto))
        informe += ["Ficheros enlazados:", "", *[f"- {t!r} → `{u}`" for u, t in enlaces[:80]], ""]

        # Los JSON: la forma y cuántos registros, y una muestra de los que
        # sirvan para cruzar (legislatura, formación, grupo).
        guardados = 0
        for url, texto in [e for e in enlaces if e[0].lower().endswith(".json")][:8]:
            codigo, contenido, tipo = pedir(c, url)
            informe += [f"### `{url}`", "", f"{texto!r} · HTTP {codigo} · `{tipo}` · {len(contenido)} bytes", ""]
            if codigo != 200:
                continue
            try:
                datos = json.loads(contenido.decode("utf-8-sig"))
            except ValueError as exc:
                informe.append(f"(no es JSON: {exc})\n")
                continue
            filas = datos if isinstance(datos, list) else next((v for v in datos.values() if isinstance(v, list)), [])
            informe += ["```json", json.dumps(forma(datos), ensure_ascii=False, indent=2)[:3000], "```", ""]
            informe.append(f"Registros: **{len(filas)}**")
            if filas and isinstance(filas[0], dict):
                for campo in list(filas[0].keys())[:30]:
                    valores = Counter(str(f.get(campo, ""))[:40] for f in filas)
                    if len(valores) < 40:
                        informe.append(f"- `{campo}`: {valores.most_common(8)}")
                    else:
                        informe.append(f"- `{campo}`: {len(valores)} valores distintos")
            informe.append("")
            if guardados < 3 and len(contenido) < 4_000_000:
                nombre = Path(urlparse(url).path).name
                (golden / nombre).write_bytes(contenido)
                guardados += 1
                informe.append(f"Guardado como `{golden / nombre}`.\n")
            time.sleep(0.5)

    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.salida).write_text("\n".join(informe) + "\n", encoding="utf-8")
    print("\n".join(informe))
    return 0


if __name__ == "__main__":
    sys.exit(main())
