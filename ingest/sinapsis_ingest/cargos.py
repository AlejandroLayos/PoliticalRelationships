"""Qué dice un Real Decreto de nombramiento o de cese, y si es un alto cargo.

Va aparte del conector porque son reglas puras: se prueban sin red, sin base
de datos y contra los títulos reales que guardó el reconocimiento
(`ingest/tests/golden/boe_altos_cargos_*.json`).

## Por qué sólo el título

El BOE escribe los nombramientos con una fórmula fija desde hace décadas:

    Real Decreto 714/2026, de 1 de septiembre, por el que se nombra
    Secretaria General de Transporte Terrestre a doña Sara Hernández del Olmo.

    Real Decreto 712/2026, de 1 de septiembre, por el que se dispone el cese
    de doña Rocío Báguena Rodríguez como Secretaria General de Transporte
    Terrestre.

El cuerpo repite lo mismo con «Vengo en nombrar…». Leer el título basta, y
leer sólo lo que tiene forma fija es lo que permite no equivocarse: lo que no
encaja en la fórmula —nombramientos de varias personas a la vez, ceses
colectivos de un gobierno— **no se interpreta**, se cuenta como no leído.

## Qué es un alto cargo aquí

La regla de §12 deja publicar con nombre a quien tiene un cargo público
acreditado, y sólo en ese papel. Un Real Decreto lo acredita, pero no todo lo
que se nombra por Real Decreto es un cargo político: también se nombran así
fiscales, magistrados y generales, que son carreras profesionales. Para las
puertas giratorias interesan los de la Ley 3/2015, de altos cargos de la
Administración General del Estado: miembros del Gobierno, secretarios de
Estado, subsecretarios, secretarios generales, directores generales,
delegados del Gobierno, embajadores y quien preside o dirige un organismo o
empresa pública.

Así que la regla es una lista de lo que SÍ, no de lo que no: un cargo que no
reconoce ninguna entrada no se publica. Falla por el lado del hueco, que es
el bueno.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date

MESES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


@dataclass(frozen=True)
class Acto:
    """Un nombramiento o un cese, tal y como lo dice el título."""

    tipo: str
    """«nombramiento» o «cese»."""

    cargo: str
    """El cargo tal y como sale, con su género: «Secretaria General de…»."""

    nombre: str
    """Nombre y apellidos, sin «don» ni «doña»."""

    numero: str
    """Número del Real Decreto: «714/2026»."""

    fecha_decreto: date | None
    """La fecha del Real Decreto, que no es la de publicación."""

    motivo: str = ""
    """En los ceses, lo que la fuente añade: «a petición propia», «por pase a
    otro destino»… Se guarda tal cual; no se interpreta."""


_CABEZA = re.compile(
    r"^Real Decreto (?P<numero>\d+/(?P<anio>\d{4})), de (?P<dia>\d{1,2}) de (?P<mes>[a-z]+)"
    # «por el que dispone», sin «se», también sale en el BOE: una errata de
    # origen que no cambia lo que dice.
    r"(?: de \d{4})?, por (?:el|la) que (?:se )?(?P<resto>.+?)\.?\s*$",
    re.IGNORECASE,
)

_TRATAMIENTO = r"(?:don|doña|D\.|D\.ª|Dña\.)"

# «Designa» se usa para algunos puestos de representación permanente, y es un
# nombramiento a todos los efectos.
_NOMBRA = re.compile(rf"^(?:nombra|designa) (?P<cargo>.+?) a {_TRATAMIENTO} (?P<nombre>.+)$")

# Lo que el BOE añade detrás del cargo en un cese. Sólo lo conocido: si viene
# otra cosa detrás de una coma, puede ser parte del nombre del cargo —«Ministra
# de Trabajo, Migraciones y Seguridad Social» lleva comas— y cortar ahí
# publicaría un cargo mutilado.
_MOTIVOS = (
    r"a petición propia",
    r"por pase a otro destino",
    r"por pase a la situación de [^,]+",
    r"por jubilación(?: forzosa)?",
    r"por fallecimiento",
    r"por renuncia",
    r"agradeciéndole los servicios prestados",
)
_MOTIVO = "(?:" + "|".join(_MOTIVOS) + ")"

_CESE = re.compile(
    # El «de» es opcional porque el BOE a veces se lo come («se dispone el
    # cese doña Anunciación…»).
    rf"^dispone el cese(?:, (?P<motivo_antes>{_MOTIVO}),)?(?: de)? {_TRATAMIENTO} (?P<nombre>.+?)"
    rf" como (?P<cargo>.+?)(?:,? (?P<motivo_despues>{_MOTIVO}(?:, {_MOTIVO})*))?$"
)

# Palabras que pueden ir en minúscula dentro de un nombre propio.
_PARTICULAS = frozenset({"de", "del", "la", "las", "los", "y", "i", "e", "da", "do", "dos", "van"})

# Una palabra de un nombre: empieza por mayúscula y sigue con letras, y admite
# apellidos compuestos con guion o apóstrofo («Martínez-Pardo», «D'Ors»). El
# BOE escribe el apóstrofo de tres maneras —recta, curva y con el acento agudo
# suelto (U+00B4) en «D'Olhaberriague»— y abrevia María como «Mª».
_PALABRA_NOMBRE = re.compile(r"^[A-ZÁÉÍÓÚÑÜÇ][a-záéíóúñüçàèòïl·ªº'\u2019\u00b4A-ZÁÉÍÓÚÑÜÇ.-]*$")


def _es_nombre(texto: str) -> bool:
    """¿Tiene forma de un nombre de UNA persona?

    Lo que no la tiene se descarta: «los miembros del Gobierno», «don X y doña
    Y», o un título que la fórmula leyó mal. Mejor no leer un acto que
    atribuirle un cargo a quien no es.
    """
    palabras = texto.split()
    if len(palabras) < 2:
        return False
    propias = 0
    for p in palabras:
        if p in _PARTICULAS:
            continue
        if not _PALABRA_NOMBRE.match(p):
            return False
        propias += 1
    # Nombre y al menos un apellido.
    return propias >= 2


def _fecha(anio: str, mes: str, dia: str) -> date | None:
    try:
        return date(int(anio), MESES[mes.lower()], int(dia))
    except (KeyError, ValueError):
        return None


def leer_titulo(titulo: str) -> Acto | None:
    """Lee un título de Real Decreto. `None` si no es un acto de una persona."""
    t = re.sub(r"\s+", " ", titulo or "").strip()
    m = _CABEZA.match(t)
    if not m:
        return None
    resto = m.group("resto")
    comun = {
        "numero": m.group("numero"),
        # El año del número, no el de la fecha: la fecha del título no lo trae
        # casi nunca, y el número siempre.
        "fecha_decreto": _fecha(m.group("anio"), m.group("mes"), m.group("dia")),
    }

    n = _NOMBRA.match(resto)
    if n:
        nombre, cargo = n.group("nombre").strip(), n.group("cargo").strip()
        if not _es_nombre(nombre) or not cargo:
            return None
        return Acto(tipo="nombramiento", cargo=cargo, nombre=nombre, **comun)

    c = _CESE.match(resto)
    if c:
        nombre, cargo = c.group("nombre").strip(), c.group("cargo").strip()
        if not _es_nombre(nombre) or not cargo:
            return None
        motivo = ", ".join(x for x in (c.group("motivo_antes"), c.group("motivo_despues")) if x)
        return Acto(tipo="cese", cargo=cargo, nombre=nombre, motivo=motivo, **comun)

    return None


def _plano(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    ).lower()


# La primera palabra del cargo lleva el género de quien lo ocupa. El cargo es
# el mismo: «Secretaria General de Transporte Terrestre» y «Secretario General
# de Transporte Terrestre» son un solo puesto, con dos personas distintas.
_MASCULINO = {
    "ministra": "Ministro",
    "vicepresidenta": "Vicepresidente",
    "presidenta": "Presidente",
    "secretaria": "Secretario",
    "subsecretaria": "Subsecretario",
    "directora": "Director",
    "delegada": "Delegado",
    "subdelegada": "Subdelegado",
    "comisionada": "Comisionado",
    "embajadora": "Embajador",
    "enviada": "Enviado",
    "gobernadora": "Gobernador",
    "subgobernadora": "Subgobernador",
    "interventora": "Interventor",
    "abogada": "Abogado",
    "consejera": "Consejero",
    "consejera delegada": "Consejero Delegado",
    "directora adjunta": "Director Adjunto",
    "vicesecretaria": "Vicesecretario",
    "jefa": "Jefe",
    "vicepresidenta primera": "Vicepresidente primero",
    "vicepresidenta segunda": "Vicepresidente segundo",
    "vicepresidenta tercera": "Vicepresidente tercero",
    "vicepresidenta cuarta": "Vicepresidente cuarto",
}


def puesto(cargo: str) -> str:
    """El nombre del puesto, sin el género de quien lo ocupa.

    Sólo se toca la primera palabra (o las dos de «Vicepresidenta primera»):
    más adentro, «Secretaría» con tilde es el órgano y no se cambia.
    """
    palabras = cargo.split(" ")
    for n in (2, 1):
        clave = " ".join(palabras[:n]).lower()
        if clave in _MASCULINO:
            return " ".join([_MASCULINO[clave], *palabras[n:]])
    return cargo


# Lo que SÍ es alto cargo, por cómo empieza el puesto (ya en masculino y sin
# tildes). Ley 3/2015, art. 1.2.
_ALTOS_CARGOS = tuple(
    re.compile(p)
    for p in (
        r"^presidente del gobierno\b",
        r"^vicepresidente (primero |segundo |tercero |cuarto )?del gobierno\b",
        r"^ministro\b",
        r"^secretario de estado\b",
        r"^subsecretario\b",
        r"^secretario general\b",
        r"^director general\b",
        r"^director (de|del)\b",
        r"^director adjunto (de|del)\b",
        r"^vicesecretario general\b",
        r"^delegado del gobierno\b",
        r"^comisionado\b",
        r"^alto comisionado\b",
        r"^embajador\b",
        r"^representante permanente\b",
        r"^enviado especial\b",
        r"^presidente (de|del)\b",
        r"^vicepresidente (de|del)\b",
        r"^vicepresidente ejecutivo\b",
        r"^consejero delegado\b",
        r"^gobernador del banco de espana\b",
        r"^subgobernador del banco de espana\b",
        r"^interventor general\b",
        r"^abogado general del estado\b",
        r"^jefe del gabinete\b",
    )
)

# Carreras profesionales que también se nombran por Real Decreto. Aunque el
# puesto empiece como uno de arriba —«Presidente de la Audiencia Provincial»,
# «Director de la Escuela Judicial»—, no es un cargo político y su titular no
# entra en la regla de §12.
_CARRERAS = re.compile(
    r"\b(fiscal|fiscalia|magistrad[oa]|juez|jueza|juzgado|audiencia|tribunal supremo"
    r"|tribunal superior de justicia|sala de lo|escuela judicial|poder judicial"
    r"|general de brigada|general de division|teniente general|almirante"
    # «Notario» y «registrador» son la persona; «Dirección General de los
    # Registros y del Notariado» es un alto cargo, y la regla vieja —«notari»
    # a secas— la tachaba.
    r"|\bregistrador|\bnotari[oa]s?\b)"
)


# Nombrados por el Gobierno aunque el puesto sea de una carrera: la Fiscalía
# General del Estado la elige el Consejo de Ministros, y el paso de un
# ministerio a la Fiscalía General es precisamente de lo que va esto.
_NOMBRADOS_POR_EL_GOBIERNO = re.compile(r"^fiscal general del estado$")


def es_alto_cargo(cargo: str) -> bool:
    """¿El puesto es un alto cargo en el sentido de la Ley 3/2015?"""
    p = _plano(puesto(cargo))
    if _NOMBRADOS_POR_EL_GOBIERNO.search(p):
        return True
    if _CARRERAS.search(p):
        return False
    return any(r.search(p) for r in _ALTOS_CARGOS)
