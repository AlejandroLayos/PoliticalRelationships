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
del 26/9/2026), y el volcado la trata aparte.

La señal es la que usa la propia CNMV: a una persona la escribe «APELLIDOS ,
NOMBRE», con coma. La primera versión trataba como persona todo lo que no
llevara forma jurídica, y la primera instantánea real (26/9/2026) publicó
como personas a Morgan Stanley, Sonatrach, ENAIRE, el FROB o el Instituto
Vasco de Finanzas; ninguno lleva coma, y las 34 personas de verdad, todas.
Ahora es persona lo que lleva coma y no lleva forma jurídica (Bertelsmann y
Planeta llevan coma: «BERTELSMANN , A.G.»). Lo demás, sociedad. Las dos
cosas van con clave de la CNMV (`cnmv:persona:`, `cnmv:sociedad:`) y fuera
del grafo y del índice; lo que cambia es cómo se presentan.

«ACCION CONCERTADA» no es nadie: es como la CNMV rotula a un grupo de
titulares que votan juntos. Como nodo uniría cotizadas que no tienen nada en
común —el de ACS y el de Vocento serían el mismo—, así que no se publica.
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


@dataclass(frozen=True)
class DatosGenerales:
    """La ficha de una cotizada en `ee/datosgenerales.aspx?nif=…`."""

    emisor: str
    """El nombre completo, del título de la página."""

    nif: str
    lei: str
    abreviada: str
    """«Denominación abreviada»: PRISA, TELEFONICA…"""

    sector: str
    """El sector que le asigna la CNMV, tal como lo escribe."""


def leer_datos_generales(html: str) -> DatosGenerales | None:
    """La ficha de la tabla `gridDatos`, por el nombre de cada columna."""
    filas = _filas_de(html, "gridDatos")
    if not filas:
        return None
    fila = filas[0]
    # La CNMV guarda el de algunas con guion («A-48010615»): se compara sin él.
    nif = re.sub(r"[^A-Z0-9]", "", _columna(fila, r"^nif$").upper())
    if not nif:
        return None
    return DatosGenerales(
        emisor=emisor_del_titulo(html),
        nif=nif,
        lei=_columna(fila, r"^lei$"),
        abreviada=_columna(fila, r"abreviada"),
        sector=_columna(fila, r"^sector$"),
    )


@dataclass(frozen=True)
class InformeDeGobierno:
    """Un informe anual de gobierno corporativo (IAGC) de la lista de la CNMV."""

    ejercicio: int
    registro: str
    """Número de registro oficial en la CNMV."""

    url: str
    """El PDF, `webservices/verdocumento/ver?e=…`."""


def informes_de_gobierno(html: str, nif: str | None = None) -> list[InformeDeGobierno]:
    """Los IAGC de `ee/informaciongobcorp.aspx?nif=…`, del más reciente al más viejo.

    La página tiene una tabla por tipo de informe (el de remuneraciones, el
    IARC, también lista consejeros); se leen sólo las filas de la del IAGC,
    `wGridIAGC_gridDatos`. Dentro de un ejercicio, el registro más alto va
    primero: una versión modificada sustituye a la anterior.

    Con `nif`, sólo las filas cuyo emisor enlaza a ese NIF. No es un
    remilgo: con un parámetro que no reconoce, la página no dice «sin
    datos», sino que lista los informes de TODOS los emisores, por orden
    alfabético (novena vuelta, 26/9/2026). Sin este filtro, el consejo de
    Abanca habría salido como el de Iberdrola.
    """
    i = (html or "").find("wGridIAGC_gridDatos")
    if i < 0:
        return []
    fin = html.find("</table>", i)
    salida = []
    buscado = re.sub(r"[^A-Z0-9]", "", nif.upper()) if nif else None
    for fila in re.findall(r"<tr.*?</tr>", html[i:fin], flags=re.S | re.I):
        if buscado is not None:
            emisor = re.search(r'datosgenerales\.aspx\?nif=([^"&]+)', fila, flags=re.I)
            if not emisor or re.sub(r"[^A-Z0-9]", "", emisor.group(1).upper()) != buscado:
                continue
        ejercicio = re.search(r'data-th="Ejercicio"[^>]*>\s*(\d{4})\s*<', fila)
        registro = re.search(r'data-th="N[^"]*registro oficial"[^>]*>\s*(\d+)\s*<', fila)
        url = re.search(
            r'href="(https://www\.cnmv\.es/webservices/verdocumento/ver\?e=[^"]+)"', fila
        )
        if ejercicio and url:
            salida.append(
                InformeDeGobierno(
                    ejercicio=int(ejercicio.group(1)),
                    registro=registro.group(1) if registro else "",
                    url=html_lib.unescape(url.group(1)),
                )
            )
    salida.sort(key=lambda x: (x.ejercicio, x.registro), reverse=True)
    return salida


# --- El cuadro C.1.2 del IAGC: los miembros del consejo ---------------------------

# La cabecera del cuadro en el modelo de la CNMV, tal cual (sin acentos ni
# mayúsculas). Se repite en cada página por la que sigue el cuadro. El modelo
# no trae fecha de nacimiento; los cuadros propios de algunas cotizadas, sí (el
# del BBVA, «Año de nacimiento»), y por eso no se leen: sólo este.
CABECERA_DEL_CONSEJO = (
    "nombre o denominacion social del consejero",
    "representante",
    "categoria del consejero",
    "cargo en el consejo",
    "fecha primer nombramiento",
    "fecha ultimo nombramiento",
    "procedimiento de eleccion",
)
TEXTO_DEL_CUADRO = "Nombre o denominación social del consejero"

_CATEGORIAS_DE_CONSEJERO = {
    "ejecutivo": "Ejecutivo",
    "dominical": "Dominical",
    "independiente": "Independiente",
    "otro externo": "Otro externo",
}
# Los cargos, lista cerrada. Lo que no casa no se lee: en el cuadro de bajas,
# con la misma forma de fila, esa columna trae las comisiones.
_CARGO = re.compile(
    r"^(presidente|vicepresidente(?: \d+º)?|consejero delegado|consejero coordinador independiente"
    r"|consejero|secretario consejero|consejero secretario|vicesecretario consejero)$"
)


def _es_cargo(cargo: str) -> bool:
    """Un cargo de la lista, o varios unidos: «PRESIDENTE-CONSEJERO DELEGADO».

    Cada parte tiene que estar en la lista cerrada; unas comisiones no pasan.
    """
    partes = [p for p in re.split(r"\s*[-/]\s*|\s+y\s+", cargo) if p]
    return bool(partes) and all(
        _CARGO.match(p) or re.fullmatch(r"(presidente|vicepresidente(?: \d+º)?) ejecutivo", p)
        for p in partes
    )


@dataclass(frozen=True)
class MiembroDelConsejo:
    nombre: str
    """Sin «DON» ni «DOÑA», como lo escribe el informe."""

    persona: bool
    """Persona física («DON»/«DOÑA»); si no, una sociedad consejera."""

    representante: str
    """De una sociedad consejera, quien la representa en el consejo."""

    categoria: str
    cargo: str


def es_cuadro_del_consejo(cabecera: list[str | None]) -> bool:
    """¿Es esta la primera fila del cuadro C.1.2?"""
    return tuple(_plano(" ".join((c or "").split())) for c in cabecera) == CABECERA_DEL_CONSEJO


def _celda(c: str | None) -> str:
    # «CLERMONT- TONNERRE»: un guion partido por el salto de línea.
    return re.sub(r"(\w)- (\w)", r"\1-\2", " ".join((c or "").split()))


def miembros_del_consejo(
    tablas: list[list[list[str | None]]],
) -> tuple[list[MiembroDelConsejo], int]:
    """Los miembros del consejo de las tablas del cuadro C.1.2, y cuántas filas se dejaron.

    Sólo se leen las tablas cuya primera fila es la cabecera del cuadro. Una
    fila entra si su categoría y su cargo están en las listas cerradas; si no
    —la mitad de una fila partida entre dos páginas, que llega sin categoría—
    se cuenta y se deja: no se reconstruye un nombre a partir de un trozo. Las
    columnas de fechas no se leen.
    """
    miembros: dict[str, MiembroDelConsejo] = {}
    descartadas = 0
    for tabla in tablas:
        if not tabla or not es_cuadro_del_consejo(tabla[0]):
            continue
        for fila in tabla[1:]:
            celdas = [_celda(c) for c in fila] + [""] * 7
            nombre, representante, categoria, cargo, primera = celdas[:5]
            categoria_ok = _CATEGORIAS_DE_CONSEJERO.get(_plano(categoria))
            cargo_plano = _plano(cargo)
            # «VICEPRESIDENT» + «E 26/01/1994»: la E final del cargo cae en la
            # columna de al lado.
            if re.fullmatch(r"vicepresident( \d+º)?", cargo_plano) and primera.startswith("E"):
                cargo_plano = cargo_plano.replace("vicepresident", "vicepresidente")
            if not nombre or not categoria_ok or not _es_cargo(cargo_plano):
                descartadas += 1
                continue
            m = re.match(r"^(DON|DOÑA|D\.|DÑA\.)\s+(.+)$", nombre, flags=re.IGNORECASE)
            miembro = MiembroDelConsejo(
                nombre=m.group(2).strip() if m else nombre,
                persona=bool(m),
                representante=representante if not m else "",
                categoria=categoria_ok,
                cargo=cargo_plano.capitalize(),
            )
            # El mismo cuadro sale dos veces en algunos informes.
            miembros.setdefault(_plano(miembro.nombre), miembro)
    return list(miembros.values()), descartadas


def consejeros_fijados(texto: str) -> int | None:
    """«Número de consejeros fijado por la junta 15», del texto del apartado C.1.1."""
    m = re.search(r"(?i)n[uú]mero de consejeros fijado por la junta\s+(\d+)", texto or "")
    return int(m.group(1)) if m else None


def variantes_de_nif(nif: str) -> list[str]:
    """Cómo pedirle a la CNMV las páginas de un NIF: tal cual, y con guion.

    Con 16 de las cotizadas de la lista —Iberdrola, Inditex, Atresmedia,
    Vocento…— las páginas de ficha y de gobierno corporativo dicen «No se han
    encontrado datos» con el NIF tal cual y responden con «A-48010615»
    (novena vuelta del reconocimiento, 26/9/2026). La de participaciones, en
    cambio, lo reconoce sin guion.
    """
    limpio = re.sub(r"[^A-Z0-9]", "", (nif or "").upper())
    return [limpio, f"{limpio[0]}-{limpio[1:]}"] if len(limpio) > 1 else [limpio]


def sin_datos(html: str) -> bool:
    """La página de la CNMV que dice que no tiene nada de ese NIF."""
    return "No se han encontrado datos" in (html or "")


def es_medio_de_comunicacion(sector: str) -> bool:
    """¿El sector de la CNMV es el de los medios? Por su nombre, no por lista."""
    return "medios de comunicacion" in _plano(sector or "")


# Formas jurídicas y palabras que sólo lleva una sociedad o un fondo. Lista
# cerrada: lo que no la lleva se trata como persona (ver arriba).
_FORMAS = re.compile(
    r"\b("
    r"s\.?\s?a\.?\s?u?\.?|s\.?\s?l\.?\s?u?\.?|s\.?\s?c\.?\s?a\.?|sicav|socimi|s\.?\s?g\.?\s?i\.?\s?i\.?\s?c\.?"
    r"|f\.?\s?c\.?\s?r\.?|inc\.?|llc|l\.?l\.?p\.?|ltd\.?|limited|plc|p\.?l\.?c\.?|n\.?v\.?|b\.?v\.?"
    r"|gmbh|ag|a\.g\.?|se|s\.e\.?|s\.?a\.?s\.?|s\.?a\.?r\.?l\.?|s\.?r\.?l\.?|s\.?p\.?a\.?"
    r"|l\.?p\.?|icav|lp|f\.?i\.?|fi\s?l|sicav"
    r"|corp\.?|corporation|corporacion|company|co\."
    r"|fund|fondo|fonds|trust|holdings?|group|grupo|capital|management|investments?|partners"
    r"|asset|advisors?|bank|banco|banca|caixa|fundacion|fundacio|foundation|asociacion"
    r"|sociedad|societe|compania|kingdom|republic|authority|ministry"
    r"|norges|sovereign|pension|pensiones|seguros|insurance|assurance|reaseguros"
    r")\b",
    re.IGNORECASE,
)


def es_persona_fisica(denominacion: str) -> bool:
    """¿Es una persona? Si la CNMV la escribe con coma y sin forma de sociedad."""
    return "," in (denominacion or "") and not _FORMAS.search(_plano(denominacion))


def es_accion_concertada(denominacion: str) -> bool:
    """El rótulo de un grupo de titulares que votan juntos: no es un titular."""
    return _plano(" ".join((denominacion or "").split())) in {"accion concertada"}


def nombre_de_persona(denominacion: str) -> str:
    """«AL THANI , KHALID THANI ABDULLAH» → «KHALID THANI ABDULLAH AL THANI».

    La CNMV escribe a las personas «APELLIDOS , NOMBRE». Se da la vuelta sólo
    cuando la coma está; si no, se deja como viene.
    """
    partes = [p.strip() for p in (denominacion or "").split(",")]
    if len(partes) == 2 and all(partes):
        return f"{partes[1]} {partes[0]}"
    return " ".join((denominacion or "").split())
