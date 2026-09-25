"""De qué administración es un organismo: su nivel y su territorio.

Fase 7, línea 1 (spec §15): poder preguntar «qué empresas cobran de la Junta
de Andalucía» exige saber, de cada organismo que paga, si es del Estado, de
una comunidad autónoma o de una entidad local, y de cuál.

## De dónde sale

De lo que publica la fuente sobre DÓNDE CUELGA el organismo, nunca de su
nombre:

- **La jerarquía.** PLACSP anida cada órgano de contratación en su cadena de
  padres (`ParentLocatedParty`); BDNS publica tres niveles administrativos.
  Es la clasificación de la propia fuente.
- **La plataforma.** Un órgano que publica su perfil de contratante en la
  plataforma de la Generalitat es catalán: esa plataforma sólo aloja a los
  suyos. La inversa no vale —la del Estado la usa cualquiera—, así que sólo
  cuenta en un sentido.

Deducirlo del nombre sería más cómodo y daría más aciertos, pero el
«Servicio Andaluz de Salud» acierta y «Canal de Isabel II, S.A.» no dice nada.
Y un criterio que acierta a veces no se puede auditar.

## Lo que no encaja

Se devuelve `None` y el organismo sale como «sin clasificar». Si dos pistas se
contradicen —la jerarquía dice una comunidad y la plataforma otra—, también:
elegir una sería inventar. El volcado cuenta los que quedan así y cuáles son
sus jerarquías, para ir afinando las reglas con lo que publican de verdad.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import urlparse


def _normaliza(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto or "")
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s-]", " ", sin_tildes.lower())).strip()


# --- Comunidades ------------------------------------------------------------

#: Nombre con que se enseña cada comunidad, y las formas en que la escriben
#: las fuentes —en castellano y en su lengua—, ya normalizadas.
COMUNIDADES: dict[str, tuple[str, ...]] = {
    "Andalucía": ("andalucia", "junta de andalucia", "servicio andaluz de salud"),
    "Aragón": ("aragon", "gobierno de aragon", "servicio aragones de salud"),
    "Asturias": ("asturias", "principado de asturias"),
    "Baleares": ("illes balears", "islas baleares", "baleares", "balears"),
    "Canarias": ("canarias", "gobierno de canarias"),
    "Cantabria": ("cantabria", "servicio cantabro de salud"),
    "Castilla y León": ("castilla y leon", "junta de castilla y leon"),
    "Castilla-La Mancha": ("castilla-la mancha", "castilla la mancha"),
    "Cataluña": (
        "cataluna",
        "catalunya",
        "generalitat de catalunya",
        "institut catala de la salut",
    ),
    "Comunidad Valenciana": (
        "comunidad valenciana",
        "comunitat valenciana",
        "generalitat valenciana",
    ),
    "Extremadura": ("extremadura", "servicio extremeno de salud"),
    "Galicia": ("galicia", "xunta de galicia", "servizo galego de saude"),
    "Madrid": ("comunidad de madrid", "servicio madrileno de salud"),
    "Murcia": ("region de murcia", "servicio murciano de salud"),
    # Los servicios de salud van por su nombre propio entero, no por el
    # gentilicio: son lo que más contrata de cada comunidad, y la fuente los
    # pone como órgano padre sin nombrar la comunidad. «Navarro» suelto no
    # sirve; «Servicio Navarro de Salud» es uno y sólo uno.
    "Navarra": (
        "navarra",
        "nafarroa",
        "comunidad foral de navarra",
        "servicio navarro de salud",
        "osasunbidea",
    ),
    "País Vasco": ("pais vasco", "euskadi", "gobierno vasco", "eusko jaurlaritza", "osakidetza"),
    "La Rioja": ("la rioja", "servicio riojano de salud"),
    "Ceuta": ("ceuta",),
    "Melilla": ("melilla",),
}

#: Las provincias —y las islas con administración propia— con su comunidad.
#: Sirven para las entidades locales, que la fuente cuelga de su provincia.
PROVINCIAS: dict[str, str] = {
    "alava": "País Vasco",
    "araba": "País Vasco",
    "albacete": "Castilla-La Mancha",
    "alicante": "Comunidad Valenciana",
    "alacant": "Comunidad Valenciana",
    "almeria": "Andalucía",
    "avila": "Castilla y León",
    "badajoz": "Extremadura",
    "barcelona": "Cataluña",
    "burgos": "Castilla y León",
    "caceres": "Extremadura",
    "cadiz": "Andalucía",
    "castellon": "Comunidad Valenciana",
    "castello": "Comunidad Valenciana",
    "ciudad real": "Castilla-La Mancha",
    "cordoba": "Andalucía",
    "a coruna": "Galicia",
    "la coruna": "Galicia",
    "cuenca": "Castilla-La Mancha",
    "girona": "Cataluña",
    "gerona": "Cataluña",
    "granada": "Andalucía",
    "guadalajara": "Castilla-La Mancha",
    "gipuzkoa": "País Vasco",
    "guipuzcoa": "País Vasco",
    "huelva": "Andalucía",
    "huesca": "Aragón",
    "jaen": "Andalucía",
    "leon": "Castilla y León",
    "lleida": "Cataluña",
    "lerida": "Cataluña",
    "lugo": "Galicia",
    "madrid": "Madrid",
    "malaga": "Andalucía",
    "murcia": "Murcia",
    "ourense": "Galicia",
    "orense": "Galicia",
    "palencia": "Castilla y León",
    "las palmas": "Canarias",
    "pontevedra": "Galicia",
    "salamanca": "Castilla y León",
    "santa cruz de tenerife": "Canarias",
    "segovia": "Castilla y León",
    "sevilla": "Andalucía",
    "soria": "Castilla y León",
    "tarragona": "Cataluña",
    "teruel": "Aragón",
    "toledo": "Castilla-La Mancha",
    "valencia": "Comunidad Valenciana",
    "valladolid": "Castilla y León",
    "bizkaia": "País Vasco",
    "vizcaya": "País Vasco",
    "zamora": "Castilla y León",
    "zaragoza": "Aragón",
}

#: Plataformas autonómicas de contratación: el dominio del perfil de
#: contratante dice en cuál publica el órgano. Sólo las que alojan
#: exclusivamente a organismos de su comunidad.
PLATAFORMAS: dict[str, str] = {
    "contractaciopublica.gencat.cat": "Cataluña",
    # El dominio nuevo de la plataforma catalana. La primera ingesta real
    # (25/9/2026) dejó 66 organismos sin clasificar con este perfil —el
    # Ajuntament de Barcelona, TMB, el Área Metropolitana— porque sólo se
    # conocía el antiguo.
    "contractaciopublica.cat": "Cataluña",
    "contratos-publicos.comunidad.madrid": "Madrid",
    "www.contratos-publicos.comunidad.madrid": "Madrid",
    "www.contratacion.euskadi.eus": "País Vasco",
    "contratacion.euskadi.eus": "País Vasco",
    "www.juntadeandalucia.es": "Andalucía",
    "www.contratosdegalicia.gal": "Galicia",
    "contratosdegalicia.gal": "Galicia",
    "hacienda.navarra.es": "Navarra",
    "portalcontratacion.navarra.es": "Navarra",
    "www.larioja.org": "La Rioja",
    "contratacion.larioja.org": "La Rioja",
}

# --- Nivel ------------------------------------------------------------------

# Marcas de nivel en la jerarquía, normalizadas. Van en orden de prioridad:
# lo local antes que lo autonómico, porque «Entitats municipals de
# Catalunya» nombra una comunidad y es local.
_LOCAL = (
    "entidades locales",
    "entitats municipals",
    "entitats locals",
    # «Entitats de l'administració local»: la categoría con que la plataforma
    # catalana cuelga a sus ayuntamientos. 379 organismos en la primera
    # ingesta real.
    "administracio local",
    "administracion local",
    "ayuntamiento",
    "ajuntament",
    "concello",
    "udala",
    "diputacion provincial",
    "diputacio",
    "diputacion foral",
    "cabildo",
    "consell insular",
    "consell comarcal",
    "mancomunidad",
    "comarca",
)
_AUTONOMICO = (
    "comunidades y ciudades autonomas",
    "comunidad autonoma",
    "comunidades autonomas",
    "administracion autonomica",
    "autonomica",
    "generalitat",
    "xunta",
    "gobierno vasco",
    "eusko jaurlaritza",
    "comunidad foral",
    "junta de andalucia",
    "junta de castilla",
    "junta de extremadura",
    "junta de comunidades",
    "gobierno de aragon",
    "gobierno de canarias",
    "gobierno de cantabria",
    "gobierno de la rioja",
    "gobierno de navarra",
    "govern de les illes balears",
    "principado de asturias",
    "region de murcia",
    "comunidad de madrid",
)
_ESTATAL = (
    "administracion general del estado",
    "administracion del estado",
    "sector publico estatal",
    "gobierno de espana",
    "ministerio",
    "estado",
)
# `estado` y `local` y `autonomica` también sirven solos, que es como vienen
# en el primer nivel de BDNS; como palabra completa, para que «estado» no
# salte dentro de otra.


@dataclass(frozen=True)
class Clasificacion:
    nivel: str | None
    """`estatal`, `autonomico`, `local` o None si no se puede decir."""
    territorio: str | None
    """La comunidad, o None: del Estado, o sin clasificar."""
    por: str | None
    """De dónde sale el territorio: `jerarquia` o `plataforma`."""


def _contiene(texto: str, marca: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(marca)}(?![\w-])", texto) is not None


def _nivel(eslabones: list[str]) -> str | None:
    for marcas, nivel in ((_LOCAL, "local"), (_ESTATAL, "estatal"), (_AUTONOMICO, "autonomico")):
        if any(_contiene(e, m) for e in eslabones for m in marcas):
            return nivel
    if any(e == "local" for e in eslabones):
        return "local"
    return None


def _comunidades_en(eslabones: list[str]) -> set[str]:
    halladas: set[str] = set()
    for e in eslabones:
        # Las comunidades primero, y sus formas más largas antes: «Castilla y
        # León» no puede quedarse en la provincia de León.
        propia = {
            nombre for nombre, formas in COMUNIDADES.items() if any(_contiene(e, f) for f in formas)
        }
        if propia:
            halladas |= propia
            continue
        halladas |= {c for p, c in PROVINCIAS.items() if _contiene(e, p)}
    return halladas


def plataforma_de(perfil: str | None) -> str | None:
    """La comunidad de la plataforma autonómica en que publica, si es una."""
    if not perfil:
        return None
    host = (urlparse(perfil).hostname or "").lower()
    return PLATAFORMAS.get(host)


def clasificar(jerarquia: list[str] | None, perfil: str | None = None) -> Clasificacion:
    """Nivel y territorio de un organismo a partir de lo que publica la fuente.

    `jerarquia` son los organismos de los que cuelga, sin él mismo. `perfil`
    es la dirección de su perfil de contratante, si la hay.
    """
    eslabones = [_normaliza(e) for e in (jerarquia or []) if e and e.strip()]
    nivel = _nivel(eslabones)
    por_plataforma = plataforma_de(perfil)

    if nivel == "estatal":
        # Un organismo del Estado es de toda España aunque publique desde una
        # delegación: su territorio no es una comunidad.
        return Clasificacion("estatal", None, None)

    comunidades = _comunidades_en(eslabones)
    if len(comunidades) > 1:
        return Clasificacion(nivel, None, None)
    # Sin marca de nivel pero colgado de una comunidad —no de una provincia—:
    # es de la comunidad. Es como viene en BDNS cuando el primer nivel es la
    # propia comunidad.
    if nivel is None and any(
        _contiene(e, f) for e in eslabones for formas in COMUNIDADES.values() for f in formas
    ):
        nivel = "autonomico"
    territorio = next(iter(comunidades), None)
    por = "jerarquia" if territorio else None

    if por_plataforma:
        if territorio and territorio != por_plataforma:
            # Se contradicen: no se elige.
            return Clasificacion(nivel, None, None)
        if not territorio:
            territorio, por = por_plataforma, "plataforma"
        # Publicar en una plataforma autonómica no dice si el organismo es de
        # la comunidad o de un ayuntamiento suyo: el nivel sigue siendo el que
        # diga la jerarquía, o ninguno.

    return Clasificacion(nivel, territorio, por)


def clasificar_entidad(propiedades: dict) -> Clasificacion:
    """Clasifica con lo que haya guardado de cualquiera de las fuentes.

    PLACSP guarda los padres del órgano; BDNS guarda sus tres niveles, el
    último de los cuales es el propio organismo, que no cuenta.
    """
    placsp = list(propiedades.get("jerarquia_placsp") or [])
    bdns = list(propiedades.get("jerarquia_bdns") or [])
    nombre = _normaliza(propiedades.get("name") or "")
    if bdns and _normaliza(bdns[-1]) == nombre:
        bdns = bdns[:-1]
    return clasificar(placsp + bdns, propiedades.get("perfil_contratante"))


#: Cómo se dice cada nivel en la web.
NOMBRE_NIVEL = {
    "estatal": "Administración General del Estado",
    "autonomico": "Administración autonómica",
    "local": "Administración local",
}
