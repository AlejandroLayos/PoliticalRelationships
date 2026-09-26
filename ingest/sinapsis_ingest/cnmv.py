"""Qué dicen las páginas de la CNMV sobre quién es dueño de qué cotizada.

Reglas puras, como `cargos.py`: se prueban sin red contra las páginas reales
que guardó el reconocimiento (`ingest/tests/golden/cnmv/`).

## Las dos tablas

- `Notificaciones-Participaciones.aspx?qS=…`, tabla
  `gridAccionistasSignificativos`: los accionistas significativos de UNA
  cotizada, con su porcentaje de derechos de voto (por acciones, directo e
  indirecto, y por instrumentos financieros) y la fecha en que la CNMV
  registró la notificación.
- `SociedadesParticipa.aspx?qS=…`, tabla `gridSociedades`: las cotizadas en
  las que participa UNA sociedad.

Cada celda de dato lleva su columna en `data-th`, y se lee por ese nombre,
no por posición: si la CNMV añade o mueve una columna, lo que no se reconoce
se queda vacío en vez de leerse en la columna equivocada.

## La fecha no es la de la compra

«F. Registro Entrada CNMV» es cuándo se registró la última notificación, no
desde cuándo se tiene la participación. Se guarda con ese nombre y nunca como
fecha de inicio.

## Personas y sociedades

La CNMV escribe igual a una sociedad y a una persona: «BLACKROCK INC.» y «AL
THANI , KHALID THANI ABDULLAH» van en la misma columna. Una persona física
sólo se publica en su papel de accionista significativo (spec §12, ampliación
del 26/9/2026), y el volcado la trata aparte. Por eso aquí la duda cae del
lado de la persona: es sociedad sólo si su denominación lleva una forma
jurídica reconocible; si no, se trata como persona. Una sociedad tratada
como persona sale con menos (no entra en el mapa del dinero); una persona
tratada como sociedad saldría donde no debe.
"""

from __future__ import annotations

import html as html_lib
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class Participacion:
    """Una fila de una de las dos tablas."""

    titular: str
    """Quien tiene la participación, como lo escribe la CNMV."""

    sociedad: str
    """La cotizada participada."""

    porcentaje: Decimal | None
    """Derechos de voto en total (acciones más instrumentos), en %."""

    por_acciones: Decimal | None
    por_instrumentos: Decimal | None
    directo: Decimal | None
    indirecto: Decimal | None

    fecha_registro: date | None
    """Cuándo registró la CNMV la notificación. No es la fecha de compra."""


def _texto(fragmento: str) -> str:
    return " ".join(html_lib.unescape(re.sub(r"<[^>]+>", " ", fragmento)).split())


def _plano(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    ).lower()


def _numero(valor: str) -> Decimal | None:
    """«5,033» → Decimal("5.033"); vacío o ilegible → None."""
    v = (valor or "").strip().replace(".", "").replace(",", ".")
    if not v:
        return None
    try:
        return Decimal(v)
    except InvalidOperation:
        return None


def _fecha(valor: str) -> date | None:
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", (valor or "").strip())
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def emisor_del_titulo(html: str) -> str:
    """La sociedad de la página, del título: «CNMV - <qué> - <SOCIEDAD>»."""
    m = re.search(r"<title>(.*?)</title>", html or "", flags=re.S | re.I)
    partes = _texto(m.group(1)).split(" - ", 2) if m else []
    return partes[2].strip() if len(partes) == 3 else ""


def _filas_de(html: str, tabla: str) -> list[dict[str, str]]:
    """Las filas de datos de una tabla por su id, como {columna: texto}."""
    i = (html or "").find(tabla)
    if i < 0:
        return []
    inicio = html.rfind("<table", 0, i)
    fin = html.find("</table>", i)
    if inicio < 0 or fin < 0:
        return []
    filas = []
    for fila in re.findall(r"<tr.*?</tr>", html[inicio:fin], flags=re.S | re.I):
        celdas = re.findall(r'<td[^>]*data-th="([^"]*)"[^>]*>(.*?)</td>', fila, flags=re.S | re.I)
        if celdas:
            filas.append({" ".join(_texto(k).split()): _texto(v) for k, v in celdas})
    return filas


def _columna(fila: dict[str, str], *patrones: str) -> str:
    """El valor de la primera columna cuyo nombre casa con algún patrón."""
    for nombre, valor in fila.items():
        if any(re.search(p, nombre, flags=re.I) for p in patrones):
            return valor
    return ""


def leer_accionistas(html: str) -> tuple[str, list[Participacion]]:
    """Los accionistas significativos de la cotizada de la página."""
    emisor = emisor_del_titulo(html)
    salida = []
    for fila in _filas_de(html, "gridAccionistasSignificativos"):
        titular = _columna(fila, r"^denominaci")
        if not titular or not emisor:
            continue
        salida.append(
            Participacion(
                titular=titular,
                sociedad=emisor,
                porcentaje=_numero(_columna(fila, r"^\(A\+B\)$")),
                por_acciones=_numero(_columna(fila, r"total \(A\)")),
                por_instrumentos=_numero(_columna(fila, r"\(B\)$")),
                directo=_numero(_columna(fila, r"directo")),
                indirecto=_numero(_columna(fila, r"indirecto")),
                fecha_registro=_fecha(_columna(fila, r"registro")),
            )
        )
    return emisor, salida


def leer_participadas(html: str) -> tuple[str, list[Participacion]]:
    """Las cotizadas en las que participa la sociedad de la página."""
    titular = emisor_del_titulo(html)
    salida = []
    for fila in _filas_de(html, "gridSociedades"):
        sociedad = _columna(fila, r"^sociedad participada")
        if not sociedad or not titular:
            continue
        salida.append(
            Participacion(
                titular=titular,
                sociedad=sociedad,
                porcentaje=_numero(_columna(fila, r"^total")),
                por_acciones=_numero(_columna(fila, r"atribuidos a las acciones")),
                por_instrumentos=_numero(_columna(fila, r"instrumentos")),
                directo=None,
                indirecto=None,
                fecha_registro=_fecha(_columna(fila, r"registro")),
            )
        )
    return titular, salida


def enlaces_de_participaciones(html: str) -> dict[str, str]:
    """De `ps_ac_ini`: {"accionistas": url, "participadas": url}, relativas."""
    salida = {}
    for href in re.findall(r'href="([^"]*qS=[^"]+)"', html or ""):
        h = html_lib.unescape(href)
        if "Notificaciones-Participaciones" in h:
            salida["accionistas"] = h
        elif "SociedadesParticipa" in h:
            salida["participadas"] = h
    return salida


# Formas jurídicas y palabras que sólo lleva una sociedad o un fondo. Lista
# cerrada: lo que no la lleva se trata como persona (ver arriba).
_FORMAS = re.compile(
    r"\b("
    r"s\.?\s?a\.?\s?u?\.?|s\.?\s?l\.?\s?u?\.?|s\.?\s?c\.?\s?a\.?|sicav|socimi|s\.?\s?g\.?\s?i\.?\s?i\.?\s?c\.?"
    r"|f\.?\s?c\.?\s?r\.?|inc\.?|llc|l\.?l\.?p\.?|ltd\.?|limited|plc|p\.?l\.?c\.?|n\.?v\.?|b\.?v\.?"
    r"|gmbh|ag|se|s\.e\.?|s\.?a\.?s\.?|s\.?a\.?r\.?l\.?|s\.?p\.?a\.?|l\.?p\.?|icav|lp"
    r"|corp\.?|corporation|company|co\."
    r"|fund|fondo|fonds|trust|holdings?|group|grupo|capital|management|investments?|partners"
    r"|asset|advisors?|bank|banco|banca|caixa|fundacion|fundacio|foundation|asociacion"
    r"|sociedad|societe|compania|kingdom|republic|authority|ministry"
    r"|norges|sovereign|pension|pensiones|seguros|insurance|assurance|reaseguros"
    r")\b",
    re.IGNORECASE,
)


def es_persona_fisica(denominacion: str) -> bool:
    """¿Se trata como persona? Sí, salvo que lleve una forma de sociedad."""
    return not _FORMAS.search(_plano(denominacion))


def nombre_de_persona(denominacion: str) -> str:
    """«AL THANI , KHALID THANI ABDULLAH» → «KHALID THANI ABDULLAH AL THANI».

    La CNMV escribe a las personas «APELLIDOS , NOMBRE». Se da la vuelta sólo
    cuando la coma está; si no, se deja como viene.
    """
    partes = [p.strip() for p in (denominacion or "").split(",")]
    if len(partes) == 2 and all(partes):
        return f"{partes[1]} {partes[0]}"
    return " ".join((denominacion or "").split())
