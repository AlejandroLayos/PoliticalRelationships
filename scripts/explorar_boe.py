#!/usr/bin/env python3
"""Reconocimiento del BOE y del BORME, para las puertas giratorias (fase 7).

**Esto no es un conector.** Es el paso previo, el mismo que se hizo con el
Tribunal de Cuentas (`explorar_tcu.py`): mirar qué publican de verdad y en qué
forma antes de escribir un parser. En BDNS se dedujo un campo sin mirarlo y el
79 % de la primera ingesta salió sin NIF.

Las dos fuentes, por la API de datos abiertos del BOE:

- **BOE**, sumario diario. La sección II.A (nombramientos, situaciones e
  incidencias) es donde se publica que alguien entra o sale de un cargo.
- **BORME**, sumario diario. La sección primera lleva, por provincia, un PDF
  con los actos inscritos: nombramientos y ceses de administradores.

Lo que se commitea:

- El informe (`docs/fuentes/boe-reconocimiento.md`), sólo con estructura:
  claves, secciones, recuentos y las etiquetas que aparecen.
- Una muestra del sumario del BOE con **sólo** los nombramientos y ceses por
  Real Decreto: son altos cargos, que es lo único que la regla de §12 deja
  publicar con nombre.
- Una muestra de texto del BORME con **los nombres de persona sustituidos**
  por un marcador. El parser se prueba contra la forma del texto; los nombres
  de particulares no tienen por qué estar en el repositorio.

Uso (desde una máquina con salida a internet; el runner de Actions vale):

    python scripts/explorar_boe.py
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover
    sys.exit("falta httpx: pip install httpx")

TIMEOUT = 30.0
API = "https://www.boe.es/datosabiertos/api"
CABECERAS = {"Accept": "application/json", "User-Agent": "Sinapsis/0.1 (reconocimiento)"}

# Las etiquetas de cargo que se buscan en el texto del BORME, para contar
# cuáles aparecen. No para parsear: para saber qué hay.
ETIQUETAS_BORME = re.compile(
    r"(Adm\. Unico|Adm\. Solid\.|Adm\. Mancom\.|Administrador|Consejero|Presidente|"
    r"Vicepresid\.|Secretario|Cons\. Del\.|Apoderado|Liquidador|Auditor|Socio único)"
    r"\s*:",
)
ACTOS_BORME = re.compile(
    r"(Nombramientos|Ceses/Dimisiones|Revocaciones|Reelecciones|Constitución|"
    r"Disolución|Extinción|Cambio de domicilio social|Cambio de denominación social|"
    r"Ampliación de capital|Reducción de capital|Declaración de unipersonalidad)\.",
)


def pedir(cliente: httpx.Client, url: str, json_: bool = True) -> tuple[int, Any, str]:
    for intento in range(2):
        try:
            r = cliente.get(url, headers=CABECERAS if json_ else {"User-Agent": CABECERAS["User-Agent"]})
            if json_:
                try:
                    return r.status_code, r.json(), r.headers.get("content-type", "")
                except ValueError:
                    return r.status_code, None, r.headers.get("content-type", "")
            return r.status_code, r.content, r.headers.get("content-type", "")
        except httpx.HTTPError as exc:
            if intento:
                return 0, None, f"error: {exc}"
            time.sleep(2)
    return 0, None, ""


def forma(valor: Any, profundidad: int = 0) -> Any:
    """La forma de un JSON, sin su contenido: claves y tipos."""
    if profundidad > 7:
        return "…"
    if isinstance(valor, dict):
        return {k: forma(v, profundidad + 1) for k, v in list(valor.items())[:25]}
    if isinstance(valor, list):
        return [forma(valor[0], profundidad + 1)] if valor else []
    if isinstance(valor, str):
        return f"str[{len(valor)}]"
    return type(valor).__name__


def como_lista(x: Any) -> list:
    """La API devuelve un objeto cuando hay uno y una lista cuando hay varios."""
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def dias_recientes(n: int = 8) -> list[str]:
    hoy = datetime.now(UTC).date()
    return [(hoy - timedelta(days=i)).strftime("%Y%m%d") for i in range(n)]


# --- BOE ------------------------------------------------------------------


def secciones_boe(sumario: dict) -> list[dict]:
    diarios = como_lista(sumario.get("data", {}).get("sumario", {}).get("diario"))
    salida = []
    for d in diarios:
        salida.extend(como_lista(d.get("seccion")))
    return salida


def items_de(seccion: dict) -> list[dict]:
    items = []
    for dep in como_lista(seccion.get("departamento")):
        for ep in como_lista(dep.get("epigrafe")):
            for it in como_lista(ep.get("item")):
                items.append({**it, "_departamento": dep.get("nombre"), "_epigrafe": ep.get("nombre")})
        for it in como_lista(dep.get("item")):
            items.append({**it, "_departamento": dep.get("nombre"), "_epigrafe": None})
    return items


ALTO_CARGO = re.compile(r"^Real Decreto\b.*\b(se nombra|se dispone el cese)\b", re.IGNORECASE)


def reconocer_boe(cliente: httpx.Client, informe: list[str], golden: Path | None) -> None:
    informe += ["## BOE — sumario diario", ""]
    for dia in dias_recientes():
        url = f"{API}/boe/sumario/{dia}"
        codigo, datos, tipo = pedir(cliente, url)
        informe.append(f"- `{url}` → HTTP {codigo} · `{tipo}`")
        if codigo != 200 or not isinstance(datos, dict):
            continue
        informe += ["", "Forma de la respuesta (claves reales, sin contenido):", "", "```json"]
        informe.append(json.dumps(forma(datos), ensure_ascii=False, indent=2)[:6000])
        informe += ["```", ""]
        secciones = secciones_boe(datos)
        informe.append("Secciones del día:")
        informe.append("")
        for s in secciones:
            informe.append(f"- `{s.get('codigo')}` {s.get('nombre')} — {len(items_de(s))} disposiciones")
        s2a = next((s for s in secciones if str(s.get("codigo", "")).upper() == "2A"), None)
        if s2a:
            items = items_de(s2a)
            epigrafes = Counter(i["_epigrafe"] for i in items)
            informe += ["", "Epígrafes de la II.A:", ""]
            informe += [f"- {e!r}: {n}" for e, n in epigrafes.most_common()]
            altos = [i for i in items if ALTO_CARGO.search(i.get("titulo") or "")]
            informe += [
                "",
                f"Disposiciones por Real Decreto de nombramiento o cese (altos cargos): **{len(altos)}**",
                "",
                "Claves de un `item`:",
                "",
                "```json",
                json.dumps(forma(items[0]) if items else {}, ensure_ascii=False, indent=2),
                "```",
                "",
                "Títulos de altos cargos (son publicables: §12):",
                "",
            ]
            informe += [f"- {i.get('titulo')}" for i in altos[:15]]
            if golden is not None and altos:
                golden.parent.mkdir(parents=True, exist_ok=True)
                muestra = {
                    "fuente": url,
                    "capturado": datetime.now(UTC).isoformat(),
                    "nota": "Sólo los ítems de la sección 2A por Real Decreto de nombramiento o cese.",
                    "items": [{k: v for k, v in i.items()} for i in altos],
                }
                golden.write_text(json.dumps(muestra, ensure_ascii=False, indent=2), encoding="utf-8")
                informe.append(f"\nMuestra guardada en `{golden}` ({len(altos)} ítems).")
            informe.append("")
            return
    informe.append("\n**Ningún día reciente devolvió un sumario legible.**\n")


# --- BORME ----------------------------------------------------------------


# Una secuencia de dos o más palabras en mayúsculas: así escribe el BORME los
# nombres de persona («GARCIA LOPEZ JUAN») y los de sociedad.
_MAYUSCULAS = re.compile(
    r"\b[A-ZÁÉÍÓÚÑÜÇ][A-ZÁÉÍÓÚÑÜÇ'\-]+(?:,?\s+[A-ZÁÉÍÓÚÑÜÇ][A-ZÁÉÍÓÚÑÜÇ'.\-]+){1,7}"
)
_SOCIEDAD = re.compile(
    r"\b(S\.?L\.?U?|S\.?A\.?U?|S\.?L\.?L\.?|SLP|S\.?COOP\.?|AIE|UTE|SOCIEDAD|LIMITADA|ANONIMA|ANÓNIMA|"
    r"COOPERATIVA|FUNDACION|FUNDACIÓN|ASOCIACION|ASOCIACIÓN)\b"
)


def anonimizar(texto: str) -> tuple[str, int]:
    """Sustituye todo lo que pueda ser un nombre de persona.

    Seguro por construcción, no por acierto: en vez de buscar nombres detrás
    de cada etiqueta de cargo —y arriesgarse a que un formato no previsto deje
    pasar uno—, se sustituye TODA secuencia de palabras en mayúsculas que no
    lleve una forma societaria. Se lleva por delante también algún topónimo
    o cabecera, que no hace falta para probar un parser; lo que no puede
    pasar es que un nombre llegue al repositorio.
    """
    cuenta = 0

    def sustituir(m: re.Match) -> str:
        nonlocal cuenta
        if _SOCIEDAD.search(m.group(0)):
            return m.group(0)
        cuenta += 1
        # El punto final es del texto, no del nombre: «JUAN. Datos registrales».
        return "APELLIDO1 APELLIDO2 NOMBRE" + ("." if m.group(0).endswith(".") else "")

    return _MAYUSCULAS.sub(sustituir, texto), cuenta


def reconocer_borme(cliente: httpx.Client, informe: list[str], golden: Path | None) -> None:
    informe += ["## BORME — sumario diario y sección primera", ""]
    for dia in dias_recientes():
        url = f"{API}/borme/sumario/{dia}"
        codigo, datos, tipo = pedir(cliente, url)
        informe.append(f"- `{url}` → HTTP {codigo} · `{tipo}`")
        if codigo != 200 or not isinstance(datos, dict):
            continue
        informe += ["", "Forma de la respuesta (claves reales, sin contenido):", "", "```json"]
        informe.append(json.dumps(forma(datos), ensure_ascii=False, indent=2)[:6000])
        informe += ["```", ""]
        secciones = secciones_boe(datos)
        for s in secciones:
            informe.append(f"- sección `{s.get('codigo')}` {s.get('nombre')}")
        primera = next((s for s in secciones if str(s.get("codigo", "")).upper() in {"A", "1", "I"}), None)
        if primera is None and secciones:
            primera = secciones[0]
        if primera is None:
            continue
        items = [
            *[i for i in como_lista(primera.get("item"))],
            *[i for _, i in ((None, it) for dep in como_lista(primera.get("departamento")) for it in como_lista(dep.get("item")))],
        ]
        informe += ["", f"Ítems de la sección primera: **{len(items)}**", "", "Claves de un `item`:", ""]
        informe += ["```json", json.dumps(forma(items[0]) if items else {}, ensure_ascii=False, indent=2), "```", ""]
        informe += [f"- {i.get('titulo')}" for i in items[:12]]
        # El PDF más pequeño, para no bajar cien páginas en un reconocimiento.
        def tam(i: dict) -> int:
            pdf = i.get("url_pdf")
            if isinstance(pdf, dict):
                try:
                    return int(pdf.get("szBytes") or pdf.get("szbytes") or 10**9)
                except (TypeError, ValueError):
                    return 10**9
            return 10**9

        elegido = min(items, key=tam) if items else None
        if not elegido:
            continue
        pdf = elegido.get("url_pdf")
        url_pdf = pdf.get("texto") if isinstance(pdf, dict) else pdf
        codigo_pdf, contenido, tipo_pdf = pedir(cliente, url_pdf, json_=False)
        informe.append(f"\nPDF de muestra: `{url_pdf}` → HTTP {codigo_pdf} · `{tipo_pdf}` · {len(contenido or b'')} bytes")
        if codigo_pdf != 200 or not contenido:
            continue
        try:
            import pdfplumber
        except ImportError:
            informe.append("(falta pdfplumber: no se puede leer el PDF)")
            return
        with pdfplumber.open(io.BytesIO(contenido)) as doc:
            texto = "\n".join((p.extract_text() or "") for p in doc.pages)
        actos = Counter(m.group(1) for m in ACTOS_BORME.finditer(texto))
        etiquetas = Counter(m.group(1) for m in ETIQUETAS_BORME.finditer(texto))
        asientos = re.findall(r"^\s*(\d{5,7})\s*-\s*", texto, re.MULTILINE)
        informe += [
            "",
            f"Páginas: {len(texto.splitlines())} renglones · asientos numerados: **{len(asientos)}**",
            "",
            "Actos que aparecen:",
            "",
            *[f"- {a}: {n}" for a, n in actos.most_common()],
            "",
            "Etiquetas de cargo que aparecen:",
            "",
            *[f"- `{e}:` {n}" for e, n in etiquetas.most_common()],
        ]
        if golden is not None:
            anonimo, n = anonimizar(texto)
            golden.parent.mkdir(parents=True, exist_ok=True)
            golden.write_text(
                f"# Fuente: {url_pdf}\n# Capturado: {datetime.now(UTC).isoformat()}\n"
                f"# Nombres de persona sustituidos: {n}\n\n{anonimo}",
                encoding="utf-8",
            )
            informe.append(f"\nMuestra de texto guardada en `{golden}`, con {n} nombres de persona sustituidos.")
        informe.append("")
        return
    informe.append("\n**Ningún día reciente devolvió un sumario legible.**\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="docs/fuentes/boe-reconocimiento.md")
    ap.add_argument("--golden-boe", default="ingest/tests/golden/boe_altos_cargos_muestra.json")
    ap.add_argument("--golden-borme", default="ingest/tests/golden/borme_seccion1_muestra.txt")
    args = ap.parse_args()

    informe = [
        "# Reconocimiento del BOE y del BORME",
        "",
        f"Generado automáticamente el {datetime.now(UTC).isoformat()} por `scripts/explorar_boe.py`.",
        "",
        "**No es documentación de una fuente integrada**: es lo que se ve desde fuera,",
        "anotado sin interpretar, para escribir los conectores de las puertas giratorias",
        "(spec §15, fase 7) sobre la forma real de los datos.",
        "",
    ]
    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as cliente:
        reconocer_boe(cliente, informe, Path(args.golden_boe))
        reconocer_borme(cliente, informe, Path(args.golden_borme))

    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.salida).write_text("\n".join(informe) + "\n", encoding="utf-8")
    print("\n".join(informe))
    return 0


if __name__ == "__main__":
    sys.exit(main())
