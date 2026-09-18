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


# Formas societarias que descartan que el adjudicatario sea una persona
# física, por mucho que su identificador lo parezca. Salió de datos reales:
# en la instantánea de PLACSP, "NACATUR 2 ESPAÑA, S.L." y "Explorance Inc"
# aparecían clasificados como `Person` porque su identificador empezaba por
# dígito. El nombre lo desmentía y nadie le estaba preguntando.
_FORMAS_SOCIETARIAS = re.compile(
    r"(?:^|[\s,.(])(?:"
    r"s\.?\s?l\.?(?:\s?u\.?)?|s\.?\s?a\.?(?:\s?u\.?)?|s\.?\s?c\.?|s\.?\s?coop\.?"
    r"|sociedad|asociaci[oó]n|fundaci[oó]n|federaci[oó]n|colegio|consorcio"
    r"|cooperativa|comunidad|ayuntamiento|universidad|instituto|agrupaci[oó]n"
    r"|inc|ltd|llc|gmbh|b\.?v\.?|s\.?p\.?a\.?|plc|corp|company|limited"
    r"|u\.?t\.?e\.?|a\.?i\.?e\.?|c\.?b\.?"
    r")(?:[\s,.)]|$)",
    re.IGNORECASE,
)


# La letra inicial del NIF dice la naturaleza del titular, y lo dice de forma
# oficial: lo fija la Orden EHA/451/2008. Dos letras marcan capital de fuera:
#
#   N  entidad extranjera
#   W  establecimiento permanente de una entidad no residente
#
# Y las de NIE —X, Y, Z— son personas físicas extranjeras. Se listan aparte
# porque una persona física recibe el trato de minimización (spec §12) tenga la
# nacionalidad que tenga: lo que interesa del extranjero es el capital, no quién.
# Formas societarias que sólo existen fuera de España, exigidas AL FINAL del
# nombre. Es la parte del nombre que designa el tipo de sociedad, y por tanto
# el ordenamiento bajo el que está constituida.
#
# Al final y no en cualquier posición: "AB MEDICA GROUP" es española y empieza
# por AB; "Reed Exhibitions Ltd." termina en Ltd. La posición es lo que
# distingue el tipo societario de una palabra suelta del nombre comercial.
#
# Quedan fuera a propósito formas ambiguas en castellano o catalán —SA, SL,
# SC— y siglas que colisionan con organismos españoles.
_FORMAS_EXTRANJERAS = re.compile(
    r"(?:^|[\s,.(])(?:"
    r"gmbh(?:\s?&\s?co\.?\s?kg)?|mbh|ltd|limited|llc|l\.?l\.?c\.?|inc|plc"
    r"|b\.?\s?v\.?|n\.?\s?v\.?|a\/s|aps|oy|oyj|kft|s\.?p\.?a\.?|s\.?r\.?l\.?"
    # Se cayó la turca «A.Ş.»: un test la pilló marcando como extranjera a
    # "ASOC PROV DE FAMILIAS Y AMIGOS DE PERSONAS SORDAS A.S.P.A.S.", que es
    # una asociación española — el nombre termina en ".A.S.". Dos letras no
    # bastan para afirmar bajo qué ordenamiento está constituida una entidad.
    r"|sp\.?\s?z\s?o\.?\s?o\.?|pte\.?\s?ltd"
    r")[\s,.)]*$",
    re.IGNORECASE,
)

_INICIALES_ENTIDAD_EXTRANJERA = "NW"
_INICIALES_NIE = "XYZ"


def es_entidad_extranjera(nif: str | None) -> bool:
    """True si el NIF corresponde a una entidad no residente.

    No es una deducción por el nombre —"Gmbh", "Ltd"— que sería frágil y daría
    falsos positivos con cualquier empresa española de nombre inglés. Es lo que
    la propia Agencia Tributaria codifica en la letra inicial, así que es la
    fuente afirmándolo, no nosotros dedujéndolo.
    """
    if not nif:
        return False
    return nif[0].upper() in _INICIALES_ENTIDAD_EXTRANJERA


def motivo_extranjera(nif: str | None) -> str:
    """Por qué se ha marcado como extranjera. Sin procedencia no se afirma nada."""
    if not nif:
        return ""
    letra = nif[0].upper()
    if letra == "N":
        return "NIF de entidad extranjera (letra N)"
    if letra == "W":
        return "NIF de establecimiento permanente de entidad no residente (letra W)"
    if letra in _INICIALES_NIE:
        return f"NIE de persona física extranjera (letra {letra})"
    return ""


def parece_extranjera_por_forma(nif: str | None, nombre: str | None) -> bool:
    """Indicio —no prueba— de que la entidad está constituida fuera de España.

    El criterio del NIF es el bueno y no se toca: lo afirma la Agencia
    Tributaria. Pero en los datos reales hay adjudicatarios **sin NIF
    ninguno**, y no por casualidad: son justamente los proveedores extranjeros,
    que no tienen por qué tener uno. En la instantánea del 18/9/2026 eran siete
    —META PLATFORMS IRELAND LIMITED, VOESTALPINE RAIL TECHNOLOGY GMBH,
    NOVOGENE UK COMPANY LIMITED y cuatro más— cobrando de administraciones
    españolas y sin aparecer en el filtro de capital extranjero.

    Las dos condiciones son necesarias y ninguna basta sola:

    - **Sin NIF.** Con NIF manda el NIF, sea español o no. Deducir por el
      nombre teniendo el dato oficial delante sería sustituir una fuente por
      una corazonada.
    - **Forma societaria extranjera al final del nombre.** Al final, porque es
      ahí donde va el tipo de sociedad. "AB MEDICA GROUP" es española y empieza
      por AB.

    Aun así es un indicio, y se publica como tal: en propiedad aparte, con su
    motivo, y la interfaz no puede presentarlo como lo que afirma un NIF.
    """
    if nif:
        return False
    if not nombre:
        return False
    return bool(_FORMAS_EXTRANJERAS.search(nombre.strip()))


def propiedades_extranjera(nif: str | None, nombre: str | None = None) -> dict[str, object]:
    """Propiedades que marcan capital no residente, con su motivo.

    Devuelve {} si no lo es: así se puede mezclar en cualquier diccionario de
    propiedades sin ensuciar a las entidades españolas con una clave a False
    que luego habría que interpretar.

    Lo probado por el NIF y lo deducido por el nombre van en claves distintas.
    Mezclarlos haría que un indicio se leyera igual que un hecho, que es
    exactamente lo que la invariante 5 prohíbe para las aristas y no hay razón
    para permitir en las entidades.
    """
    if es_entidad_extranjera(nif):
        return {"entidad_extranjera": True, "motivo_extranjera": motivo_extranjera(nif)}
    if parece_extranjera_por_forma(nif, nombre):
        return {
            "entidad_extranjera_indicio": True,
            "motivo_extranjera_indicio": (
                "sin NIF español y con forma societaria extranjera en el nombre"
            ),
        }
    return {}


def parece_forma_societaria(nombre: str | None) -> bool:
    """True si el nombre delata una persona jurídica.

    Se usa para no llamar `Person` a una empresa. Es una comprobación de
    seguridad, no de exhaustividad: reconocer de más aquí sólo evita tratar
    a una empresa como si fuera un particular, que es el error inocuo. El
    error caro es el contrario.
    """
    if not nombre:
        return False
    return bool(_FORMAS_SOCIETARIAS.search(nombre))


def parece_persona_fisica(nif: str, nombre: str | None = None) -> bool:
    """True si el registro corresponde a una persona física.

    Sirve para elegir entre `Person` y `Company`, y por tanto para saber
    cuándo estamos tocando datos personales (spec §12).

    El NIF manda, pero el nombre puede desmentirlo: una S.L. con un
    identificador que empieza por dígito sigue siendo una S.L. Cuando los dos
    indicios se contradicen gana el nombre, porque la forma societaria es una
    afirmación explícita de la fuente y la inicial del NIF es una inferencia
    nuestra.
    """
    if not nif:
        return False
    if parece_forma_societaria(nombre):
        return False
    return nif[0].isdigit() or nif[0] in _INICIALES_PERSONA_FISICA


# DNI: ocho dígitos y una letra de control. NIE: X, Y o Z, siete dígitos y
# letra. Los dos identifican a UNA PERSONA y a nadie más.
_IDENTIFICADOR_PERSONAL = re.compile(r"^(?:[0-9]{8}|[XYZxyz][0-9]{7})[A-Za-z]$")


def es_identificador_personal(nif: str | None) -> bool:
    """¿Este NIF identifica a una persona física, sea de quién sea la ficha?

    Distinto de `parece_persona_fisica`, y la diferencia importa. Aquélla
    decide si la FICHA es de una persona, y deja que el nombre desmienta al
    NIF: una S.L. con un identificador raro sigue siendo una S.L., y está
    bien que así sea.

    Ésta pregunta otra cosa: si ese número, por sí solo, es un identificador
    personal. Y lo es aunque cuelgue de una empresa.

    En el historial del repositorio había una UTE —persona jurídica, forma
    societaria explícita, clasificada como `Company` con todo el criterio—
    cuyo NIF era el DNI de uno de sus socios, y con los nombres de los dos
    dentro del propio nombre de la UTE. La regla de «esto es una empresa»
    funcionaba perfectamente y aun así se estaba publicando un DNI.

    Un DNI es un dato personal esté pegado a lo que esté.
    """
    return bool(nif) and bool(_IDENTIFICADOR_PERSONAL.match(nif.strip()))


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
