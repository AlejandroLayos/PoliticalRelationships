#!/usr/bin/env python3
"""Reconocimiento del Tribunal de Cuentas.

**Esto no es un conector.** Es el paso previo: averiguar qué publica realmente
el TdC y en qué formato, antes de escribir una línea de parser.

El motivo es una lección que ya costó cara en este proyecto. Para BDNS deduje
el nombre de un campo (`nifCif`) del enumerado de parámetros de búsqueda, lo di
por bueno, y estaba mal: el 79 % de las aristas de la primera ingesta salió sin
identificador fiscal. Escribir un parser de PDF sobre suposiciones sería el
mismo error, multiplicado — los PDFs no avisan cuando los lees mal, sólo
devuelven basura con aspecto de dato.

Así que este script mira y **anota lo que ve**, sin interpretar. Su salida es
un informe en Markdown que se commitea, y a partir de ahí se decide.

Dos rutas independientes, a propósito:

- El **sitio del organismo** (`www.tcu.es`, `sede.tcu.es`), que es donde están
  los documentos pero también donde está el cortafuegos.
- El **catálogo nacional** (`datos.gob.es`), que es una API JSON y no depende
  de que el portal del TdC quiera hablar con nosotros. Si el TdC publica algo
  legible por máquina, está registrado ahí.

Que una ruta se caiga no invalida el reconocimiento: se anota la caída, que
también es un dato sobre la fuente, y se sigue con la otra.

Uso (desde una máquina con salida a internet; el runner de Actions vale):

    python scripts/explorar_tcu.py --salida docs/fuentes/tcu-reconocimiento.md
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

try:
    import httpx
except ImportError:  # pragma: no cover
    sys.exit("falta httpx: pip install httpx")

try:
    from cryptography import x509
    from cryptography.hazmat.primitives.serialization import Encoding
except ImportError:  # pragma: no cover
    sys.exit("falta cryptography: pip install cryptography")

# Un host caído no debe costar tres cuartos de minuto por URL: con cuatro
# candidatos eso son tres minutos de runner mirando a la pared.
TIMEOUT = 20.0
INTENTOS = 2

# Puntos de entrada conocidos, sacados de la navegación pública del organismo
# y del catálogo nacional de datos abiertos.
#
# `tipo` no es una suposición sobre lo que devuelven: es lo que se pide en la
# cabecera Accept y cómo se describe la respuesta si llega. Si un candidato
# JSON devuelve HTML, el informe lo dirá.
CANDIDATOS: list[dict[str, str]] = [
    # --- portal del organismo ---
    {
        "nombre": "portal_partidos",
        "url": "https://www.tcu.es/es/partidos-politicos/",
        "tipo": "html",
    },
    {
        "nombre": "sanciones",
        "url": "https://www.tcu.es/es/fiscalizacion/sanciones-a-partidos/",
        "tipo": "html",
    },
    {
        "nombre": "sede_rendicion",
        "url": "https://sede.tcu.es/es/sede-electronica/GRCuentas/PartidosPoliticos/",
        "tipo": "html",
    },
    {
        "nombre": "buscador",
        "url": (
            "https://www.tcu.es/searcher/document/DocumentSearch.action"
            "?docCheckFis=true&docCheckFisSelect=FIS:+PARTIDOS+POL%C3%8DTICOS"
            "&submitSearch=true"
        ),
        "tipo": "html",
    },
    # --- catálogo nacional (ruta independiente del portal del TdC) ---
    {
        "nombre": "datosgob_titulo_partidos",
        "url": (
            "https://datos.gob.es/apidata/catalog/dataset/title/partidos%20politicos"
            "?_pageSize=25&_page=0"
        ),
        "tipo": "json",
    },
    {
        "nombre": "datosgob_titulo_tribunal_cuentas",
        "url": (
            "https://datos.gob.es/apidata/catalog/dataset/title/tribunal%20de%20cuentas"
            "?_pageSize=25&_page=0"
        ),
        "tipo": "json",
    },
    {
        "nombre": "datosgob_keyword_financiacion",
        "url": (
            "https://datos.gob.es/apidata/catalog/dataset/keyword/financiacion?_pageSize=25&_page=0"
        ),
        "tipo": "json",
    },
]

CABECERAS_HTML = {
    # Identificarse es lo correcto al raspar un servicio público. Si un
    # cortafuegos nos descarta por decir quiénes somos, eso se anota; no se
    # disfraza el cliente de navegador para colarse.
    "User-Agent": (
        "Sinapsis/0.1 (proyecto abierto de transparencia; "
        "+https://github.com/AlejandroLayos/PoliticalRelationships)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
}

CABECERAS_JSON = {**CABECERAS_HTML, "Accept": "application/json,*/*;q=0.8"}


# --- diagnóstico de fallos -------------------------------------------------


def clasificar_fallo(exc: Exception) -> tuple[str, str]:
    """Devuelve (categoría, detalle).

    La categoría importa porque cada una lleva a una acción distinta, y
    confundirlas fue justo lo que pasó en el segundo reconocimiento: se
    arregló una cadena SSL cuando el problema real era que el servidor había
    dejado de responder.
    """
    texto = str(exc) or exc.__class__.__name__
    # Primero, porque es la confusión más cara: un proxy que nos corta la
    # salida se parece a una fuente caída y significa lo contrario.
    # `ProxyError` cuelga de `TransportError`, no de `ConnectError`.
    if isinstance(exc, httpx.ProxyError):
        return "proxy_local", f"la salida de esta máquina bloqueó la petición: {texto}"
    if isinstance(exc, httpx.ConnectTimeout):
        return "timeout_conexion", f"no completó el saludo TCP/TLS en {TIMEOUT:.0f}s"
    if isinstance(exc, httpx.ReadTimeout | httpx.PoolTimeout | httpx.TimeoutException):
        return "timeout_lectura", f"conectó pero no envió respuesta en {TIMEOUT:.0f}s"
    if "CERTIFICATE_VERIFY_FAILED" in texto:
        return "cadena_ssl", texto
    if isinstance(exc, ssl.SSLError) or "SSL" in texto:
        return "tls", texto
    if isinstance(exc, httpx.ConnectError):
        return "conexion", texto
    return "otro", texto


ACCION_POR_CATEGORIA = {
    "proxy_local": (
        "**no dice nada sobre la fuente.** El bloqueo es de la máquina que "
        "ejecuta el script, no del organismo. Hay que repetirlo desde un "
        "runner de Actions, que sí tiene salida."
    ),
    "timeout_conexion": (
        "el servidor no contesta desde esta IP. Puede ser caída, filtrado "
        "geográfico o un cortafuegos que descarta al cliente. No se reintenta "
        "en bucle ni se disfraza el agente: se vuelve a mirar otro día."
    ),
    "timeout_lectura": "el servidor acepta la conexión pero no responde a tiempo.",
    "cadena_ssl": (
        "el servidor omite el certificado intermedio. Se recupera por AIA como "
        "hace un navegador; no se desactiva la verificación."
    ),
    "tls": "negociación TLS fallida por otra razón.",
    "conexion": "no se pudo establecer la conexión (DNS, ruta o puerto).",
    "otro": "sin clasificar.",
}


def _completar_cadena(host: str, puerto: int = 443) -> str | None:
    """Descarga el certificado intermedio que el servidor omite.

    Varios servidores de la administración española envían sólo su certificado
    hoja, sin el intermedio que lo enlaza con una raíz de confianza. Los
    navegadores lo disimulan porque siguen la extensión AIA del certificado y
    se descargan el intermedio ellos solos; Python no.

    Esto hace lo mismo. **No se desactiva la verificación**: se le suministra a
    OpenSSL el certificado que el servidor debería haber mandado, y la cadena
    se sigue validando contra las raíces del sistema. Bajar a `verify=False`
    sería aceptar un intermediario, y en un proyecto cuyo valor es la
    procedencia del dato eso no es negociable.

    Devuelve la ruta de un bundle PEM ampliado, o None si no se pudo.
    """
    import socket
    import tempfile

    import certifi

    # Contexto sin verificar SÓLO para leer el certificado que sirve el host.
    # No se envía nada ni se confía en él: se inspecciona su extensión AIA.
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with (
            socket.create_connection((host, puerto), timeout=TIMEOUT) as cruda,
            ctx.wrap_socket(cruda, server_hostname=host) as tls,
        ):
            der = tls.getpeercert(binary_form=True)
        hoja = x509.load_der_x509_certificate(der)
        aia = hoja.extensions.get_extension_for_class(x509.AuthorityInformationAccess).value
        urls = [
            d.access_location.value
            for d in aia
            if d.access_method == x509.oid.AuthorityInformationAccessOID.CA_ISSUERS
        ]
    except Exception as exc:
        print(f"  no pude leer la cadena de {host}: {exc}", file=sys.stderr)
        return None

    for url in urls:
        try:
            r = httpx.get(url, timeout=TIMEOUT)
            r.raise_for_status()
            inter = x509.load_der_x509_certificate(r.content)
        except Exception:
            continue

        # `delete=False` a propósito: el bundle tiene que sobrevivir al bloque
        # porque lo que se devuelve es su ruta, para que httpx lo lea después.
        with tempfile.NamedTemporaryFile("wb", suffix=".pem", delete=False) as bundle:
            bundle.write(Path(certifi.where()).read_bytes())
            bundle.write(b"\n")
            bundle.write(inter.public_bytes(Encoding.PEM))
        print(f"  intermedio recuperado de {url}", file=sys.stderr)
        return bundle.name
    return None


# --- descripción de respuestas ---------------------------------------------


def _describir_html(texto: str, url_final: str) -> dict[str, Any]:
    info: dict[str, Any] = {}

    # Enlaces a ficheros descargables: es lo que decide si hay datos
    # estructurados o sólo documentos para leer con los ojos.
    enlaces = re.findall(r'href="([^"]+\.(?:pdf|xlsx?|csv|json|xml|zip))"', texto, re.IGNORECASE)
    info["descargables"] = sorted({urljoin(url_final, e) for e in enlaces})[:25]
    info["n_descargables"] = len(set(enlaces))

    # Desglose por extensión: cuatro CSV valen más que cuarenta PDF.
    extensiones: dict[str, int] = {}
    for e in enlaces:
        ext = e.rsplit(".", 1)[-1].lower()
        extensiones[ext] = extensiones.get(ext, 0) + 1
    info["extensiones"] = dict(sorted(extensiones.items(), key=lambda kv: -kv[1]))

    # ¿Hay tablas HTML? Sería mucho mejor que un PDF.
    info["tablas_html"] = len(re.findall(r"<table", texto, re.IGNORECASE))

    # ¿Algún endpoint que huela a datos?
    info["pistas_api"] = sorted(
        set(
            re.findall(
                r'["\'](/[^"\']*(?:api|json|rest|datos|opendata)[^"\']*)["\']',
                texto,
                re.IGNORECASE,
            )
        )
    )[:10]
    return info


def _forma(valor: Any, prof: int = 0) -> Any:
    """Describe la *forma* de un JSON sin volcar su contenido.

    Se anota qué claves trae de verdad la respuesta. Es exactamente lo que
    faltó con BDNS: allí se dio por bueno un nombre de campo deducido de la
    documentación en vez de mirado en una respuesta real.
    """
    if prof > 3:
        return "…"
    if isinstance(valor, dict):
        return {k: _forma(v, prof + 1) for k, v in list(valor.items())[:15]}
    if isinstance(valor, list):
        return [_forma(valor[0], prof + 1), f"…({len(valor)} elementos)"] if valor else []
    if isinstance(valor, str):
        return f"str[{len(valor)}]"
    return type(valor).__name__


def _describir_json(contenido: bytes) -> dict[str, Any]:
    info: dict[str, Any] = {}
    try:
        datos = json.loads(contenido)
    except (ValueError, UnicodeDecodeError) as exc:
        info["json_invalido"] = str(exc)[:200]
        return info

    info["forma"] = _forma(datos)

    # Formatos de distribución: es lo que decide si el conector es barato.
    # Se buscan por texto en el JSON entero para no depender de conocer la
    # estructura de antemano.
    crudo = contenido.decode("utf-8", "replace")
    formatos = sorted(set(re.findall(r"/NTI/REST/Recursos/[a-zA-Z]+#([a-zA-Z0-9+.-]+)", crudo)))
    formatos += sorted(set(re.findall(r'"format"\s*:\s*"([^"]{1,40})"', crudo)))
    info["formatos_declarados"] = sorted(set(formatos))[:20]

    # URLs de descarga presentes en la respuesta, por extensión.
    urls = re.findall(r'https?://[^"\s]+\.(?:csv|xlsx?|json|xml|zip|pdf)', crudo, re.IGNORECASE)
    extensiones: dict[str, int] = {}
    for u in urls:
        ext = u.rsplit(".", 1)[-1].lower()
        extensiones[ext] = extensiones.get(ext, 0) + 1
    info["extensiones"] = dict(sorted(extensiones.items(), key=lambda kv: -kv[1]))
    info["descargables"] = sorted(set(urls))[:15]
    info["n_descargables"] = len(set(urls))

    # ¿Menciona al Tribunal de Cuentas? Las búsquedas por palabra clave
    # devuelven de todo; esto dice si hay algo del organismo que nos importa.
    info["menciona_tcu"] = bool(re.search(r"tribunal\s+de\s+cuentas", crudo, re.IGNORECASE))
    return info


def explorar(cliente: httpx.Client, candidato: dict[str, str]) -> dict[str, Any]:
    """Pide una URL y describe lo que devuelve, sin interpretarlo."""
    info: dict[str, Any] = {"nombre": candidato["nombre"], "url": candidato["url"]}

    ultimo: Exception | None = None
    r: httpx.Response | None = None
    for intento in range(1, INTENTOS + 1):
        try:
            r = cliente.get(candidato["url"])
            break
        except httpx.HTTPError as exc:
            ultimo = exc
            if intento < INTENTOS:
                time.sleep(2 * intento)

    if r is None:
        categoria, detalle = clasificar_fallo(ultimo or RuntimeError("desconocido"))
        info["error"] = detalle
        info["categoria"] = categoria
        info["intentos"] = INTENTOS
        return info

    info["status"] = r.status_code
    info["content_type"] = r.headers.get("content-type", "")
    info["bytes"] = len(r.content)
    info["url_final"] = str(r.url)

    if r.status_code != 200:
        return info

    ct = info["content_type"].lower()
    if candidato["tipo"] == "json" or "json" in ct:
        info.update(_describir_json(r.content))
        if candidato["tipo"] == "json" and "json" not in ct:
            info["aviso"] = f"se pidió JSON y devolvió `{ct or 'sin content-type'}`"
    elif "text" in ct or "html" in ct:
        info.update(_describir_html(r.text, str(r.url)))
    else:
        info["aviso"] = f"cuerpo no textual (`{ct or 'sin content-type'}`), no se describe"
    return info


# --- informe ---------------------------------------------------------------


def formatear(resultados: list[dict[str, Any]]) -> str:
    hoy = datetime.now(UTC).isoformat()
    ok = [r for r in resultados if r.get("status") == 200]
    fallidos = [r for r in resultados if "error" in r]

    lineas = [
        "# Reconocimiento del Tribunal de Cuentas",
        "",
        f"Generado automáticamente el {hoy} por `scripts/explorar_tcu.py`.",
        "",
        "**No es documentación de una fuente ya integrada.** Es lo que se ve",
        "desde fuera, anotado sin interpretar, para decidir si merece la pena",
        "escribir un conector y de qué tipo.",
        "",
        f"Resumen: **{len(ok)} de {len(resultados)}** candidatos respondieron.",
        "",
    ]

    if fallidos:
        lineas += [
            "> Los candidatos que no responden se anotan igual. La",
            "> disponibilidad de una fuente es información sobre la fuente, no",
            "> un fallo del script, y decide si se puede depender de ella.",
            "",
        ]

    for r in resultados:
        lineas.append(f"## {r['nombre']}")
        lineas.append("")
        lineas.append(f"- URL: `{r['url']}`")

        if "error" in r:
            lineas.append(f"- **No accesible** ({r['categoria']}, {r.get('intentos', 1)} intentos)")
            lineas.append(f"  - `{r['error']}`")
            lineas.append(f"  - {ACCION_POR_CATEGORIA.get(r['categoria'], '')}")
            lineas.append("")
            continue

        lineas.append(f"- HTTP {r['status']} · `{r['content_type']}` · {r['bytes']:,} bytes")
        if r.get("nota"):
            lineas.append(f"- ⚠️ {r['nota']}")
        if r.get("aviso"):
            lineas.append(f"- ⚠️ {r['aviso']}")
        if r.get("url_final") != r["url"]:
            lineas.append(f"- Redirige a: `{r['url_final']}`")

        if "tablas_html" in r:
            lineas.append(f"- Tablas HTML en la página: **{r['tablas_html']}**")
        if "menciona_tcu" in r:
            lineas.append(
                f"- ¿Menciona «Tribunal de Cuentas»?: **{'sí' if r['menciona_tcu'] else 'no'}**"
            )
        if "n_descargables" in r:
            lineas.append(f"- Ficheros descargables enlazados: **{r['n_descargables']}**")
        if r.get("extensiones"):
            desglose = ", ".join(f"`{k}`: {v}" for k, v in r["extensiones"].items())
            lineas.append(f"  - Por extensión: {desglose}")
        if r.get("formatos_declarados"):
            lineas.append(
                "- Formatos declarados: " + ", ".join(f"`{f}`" for f in r["formatos_declarados"])
            )
        if r.get("json_invalido"):
            lineas.append(f"- ⚠️ JSON ilegible: `{r['json_invalido']}`")

        if r.get("descargables"):
            lineas.append("")
            lineas.append("  Primeros enlaces:")
            for d in r["descargables"][:10]:
                lineas.append(f"  - `{d}`")
        if r.get("pistas_api"):
            lineas.append("")
            lineas.append("  Rutas que podrían servir datos:")
            for a in r["pistas_api"]:
                lineas.append(f"  - `{a}`")
        if r.get("forma"):
            lineas.append("")
            lineas.append("  Forma de la respuesta (claves reales, sin contenido):")
            lineas.append("")
            lineas.append("  ```json")
            for linea in json.dumps(r["forma"], ensure_ascii=False, indent=2).splitlines()[:40]:
                lineas.append(f"  {linea}")
            lineas.append("  ```")
        lineas.append("")

    lineas += [
        "---",
        "",
        "## Qué mirar en este informe",
        "",
        "1. **¿Hay CSV, XLSX o JSON?** Si los hay, el conector es sencillo y no",
        "   hace falta tocar un PDF.",
        "2. **¿Hay tablas HTML?** Segunda mejor opción: se parsean sin OCR.",
        "3. **Si sólo hay PDF**, el conector necesita extracción de tablas",
        "   (`pdfplumber`) y, si están escaneados, OCR. Eso es trabajo de otra",
        "   magnitud y conviene decidirlo a la vista de un fichero real, no",
        "   antes.",
        "",
        "Sea cual sea el caso: los datos de financiación de partidos son la zona",
        "más delicada del proyecto en RGPD. Los donantes personas físicas se",
        "tratan como en BDNS — el hecho se conserva, la identidad no. Ver",
        "[spec §12](../spec.md).",
    ]
    return "\n".join(lineas) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--salida", type=Path, default=Path("docs/fuentes/tcu-reconocimiento.md"))
    args = p.parse_args()

    resultados: list[dict[str, Any]] = []
    with (
        httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers=CABECERAS_HTML) as c_html,
        httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers=CABECERAS_JSON) as c_json,
    ):
        for cand in CANDIDATOS:
            print(f"explorando {cand['nombre']}…", file=sys.stderr)
            cliente = c_json if cand["tipo"] == "json" else c_html
            r = explorar(cliente, cand)
            if "error" in r:
                print(f"  {r['categoria']}: {r['error'][:120]}", file=sys.stderr)
            resultados.append(r)

    # Los que fallaron por cadena SSL incompleta merecen un segundo intento con
    # el intermedio recuperado: el problema es del servidor, no del dato.
    fallos_ssl = [r for r in resultados if r.get("categoria") == "cadena_ssl"]
    if fallos_ssl:
        hosts = {httpx.URL(r["url"]).host for r in fallos_ssl}
        for host in hosts:
            print(f"reintentando {host} con la cadena completada…", file=sys.stderr)
            bundle = _completar_cadena(host)
            if not bundle:
                continue
            with httpx.Client(
                timeout=TIMEOUT,
                follow_redirects=True,
                headers=CABECERAS_HTML,
                verify=bundle,
            ) as cliente:
                for i, r in enumerate(resultados):
                    if httpx.URL(r["url"]).host != host or r.get("categoria") != "cadena_ssl":
                        continue
                    cand = next(c for c in CANDIDATOS if c["nombre"] == r["nombre"])
                    nuevo = explorar(cliente, cand)
                    nuevo["nota"] = (
                        "el servidor no envía el certificado intermedio; "
                        "se recuperó por AIA como hace un navegador"
                    )
                    resultados[i] = nuevo

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(formatear(resultados), encoding="utf-8")
    print(f"informe escrito en {args.salida}", file=sys.stderr)

    # Un reconocimiento donde nada respondió NO es un error del script: es un
    # hallazgo, y se commitea igual. Se avisa, no se rompe. («Si una fuente
    # falla o cambió de formato, registra el problema, tolera el hueco, sigue.»)
    alcanzables = [r for r in resultados if r.get("status") == 200]
    caidos = [r for r in resultados if "error" in r]
    for r in caidos:
        print(f"::warning title=Fuente no accesible::{r['nombre']}: {r['categoria']}")
    if not alcanzables:
        print(
            "::warning title=Reconocimiento sin respuestas::"
            "ningún candidato respondió; el informe registra por qué"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
