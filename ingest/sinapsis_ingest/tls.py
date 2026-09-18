"""Completar cadenas de certificados que el servidor deja a medias.

Varios servidores de la administración española envían sólo su certificado
hoja y omiten el intermedio que lo enlaza con una raíz de confianza. Los
navegadores lo disimulan porque siguen la extensión AIA del certificado y se
descargan el intermedio ellos solos; Python no, y falla con

    [SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer certificate

Esto hace lo mismo que el navegador. **No se desactiva la verificación**: se
le suministra a OpenSSL el certificado que el servidor debería haber mandado,
y la cadena se sigue validando contra las raíces del sistema. Bajar a
`verify=False` sería una línea y sería aceptar un intermediario; en un
proyecto cuyo valor entero es poder decir de dónde viene cada dato, eso no es
negociable.

## Por qué vive aquí y no en scripts/

Esta lógica se escribió primero en `scripts/explorar_tcu.py`, para el
reconocimiento, y funcionó. Luego se escribió el conector del Tribunal de
Cuentas **sin ella**, y el 18/9/2026 la ingesta del TdC llevaba días fallando
con ese mismo error mientras el script de reconocimiento seguía pasando sin
problema: el arreglo estaba en el sitio de mirar y no en el de ingerir.

Estando en el paquete lo usan los dos.
"""

from __future__ import annotations

import socket
import ssl
import tempfile
from pathlib import Path
from typing import Any

import httpx
import structlog

log = structlog.get_logger()

TIMEOUT_CADENA = 20.0

# Se cachea por host: la cadena de un servidor no cambia entre documentos, y
# sin esto el conector del TdC abriría una conexión extra por cada PDF.
_cache: dict[str, str | None] = {}


def _descargar_intermedio(host: str, puerto: int) -> str | None:
    # Contexto sin verificar SÓLO para leer el certificado que sirve el host.
    # No se envía nada ni se confía en él: se inspecciona su extensión AIA para
    # averiguar dónde está su emisor.
    from cryptography import x509
    from cryptography.hazmat.primitives.serialization import Encoding

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with (
            socket.create_connection((host, puerto), timeout=TIMEOUT_CADENA) as cruda,
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
        log.warning("no se pudo leer la cadena", host=host, detalle=str(exc))
        return None

    import certifi

    for url in urls:
        try:
            r = httpx.get(url, timeout=TIMEOUT_CADENA)
            r.raise_for_status()
            inter = x509.load_der_x509_certificate(r.content)
        except Exception:
            continue

        # `delete=False` a propósito: lo que se devuelve es la ruta, para que
        # httpx la lea después.
        with tempfile.NamedTemporaryFile("wb", suffix=".pem", delete=False) as bundle:
            bundle.write(Path(certifi.where()).read_bytes())
            bundle.write(b"\n")
            bundle.write(inter.public_bytes(Encoding.PEM))
        log.info("intermedio recuperado por AIA", host=host, desde=url)
        return bundle.name
    return None


def completar_cadena(host: str, puerto: int = 443) -> str | None:
    """Devuelve la ruta de un bundle PEM ampliado, o None si no se pudo."""
    if host not in _cache:
        _cache[host] = _descargar_intermedio(host, puerto)
    return _cache[host]


def verificacion_para(host: str) -> Any:
    """Qué pasarle a httpx como `verify` para hablar con `host`.

    Devuelve el bundle ampliado si el servidor omite el intermedio, y `True`
    —verificación normal— si no hace falta o no se pudo recuperar. Nunca
    devuelve False: preferimos no descargar a descargar sin verificar.
    """
    return completar_cadena(host) or True


def _reset_cache_para_tests() -> None:
    _cache.clear()
