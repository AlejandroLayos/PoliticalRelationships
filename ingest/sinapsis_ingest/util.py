"""Utilidades compartidas por los conectores."""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

# Las letras iniciales de un NIF de persona física. Los CIF de personas
# jurídicas empiezan por otra letra.
_INICIALES_PERSONA_FISICA = "KLMXYZ"

# Formato de NIF/CIF español: DNI (8 dígitos + letra), NIE (X/Y/Z + 7 dígitos +
# letra) y CIF (letra + 7 dígitos + dígito o letra) encajan todos aquí.
#
# Comprobar sólo la longitud NO basta: "ASOCIACION" también tiene 9 caracteres
# y se colaría como identificador fiscal, creando una entidad con la clave
# `nif:ASOCIACION` con la que después convergerían cosas que no tienen nada
# que ver.
_FORMATO_NIF = re.compile(r"^[A-Z0-9][0-9]{7}[A-Z0-9]$")


def normalizar_nif(valor: str | None) -> str:
    """Deja el NIF/CIF en mayúsculas y sin separadores.

    Sin esto, "B-12345678" y "b12345678" serían dos entidades distintas y toda
    la resolución determinista se vendría abajo. Es lo que hace que un mismo
    adjudicatario visto en BDNS y en PLACSP converja en una sola fila.

    Devuelve "" si no tiene los 9 caracteres de un NIF español: preferimos no
    afirmar nada a afirmar algo dudoso.
    """
    if not valor:
        return ""
    limpio = re.sub(r"[^0-9A-Za-z]", "", valor).upper()
    return limpio if _FORMATO_NIF.match(limpio) else ""


def parece_persona_fisica(nif: str) -> bool:
    """True si el NIF corresponde a una persona física.

    Sirve para elegir entre `Person` y `Company`, y por tanto para saber
    cuándo estamos tocando datos personales (spec §12).
    """
    if not nif:
        return False
    return nif[0].isdigit() or nif[0] in _INICIALES_PERSONA_FISICA


def slug(texto: str) -> str:
    """Clave estable y legible a partir de un nombre.

    Se usa cuando no hay identificador fiscal. Lleva un hash corto detrás
    porque dos nombres distintos pueden normalizar al mismo slug, y
    colapsarlos sería inventar una identidad que la fuente no afirma.
    """
    base = re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")[:60]
    digest = hashlib.sha256(texto.encode("utf-8")).hexdigest()[:8]
    return f"{base}-{digest}"


def a_decimal(valor: Any) -> Decimal | None:
    """Convierte un importe a Decimal. Nunca pasa por float."""
    if valor is None or valor == "":
        return None
    try:
        return Decimal(str(valor).strip())
    except (InvalidOperation, ValueError):
        return None


def a_fecha(valor: Any) -> date | None:
    """Convierte a fecha aceptando los formatos que usan las fuentes."""
    if not valor:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    # ISO con zona horaria: 2022-01-03T01:11:41.826+01:00
    try:
        return datetime.fromisoformat(texto).date()
    except ValueError:
        pass
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(texto[: len(formato) + 2], formato).date()
        except ValueError:
            continue
    return None
