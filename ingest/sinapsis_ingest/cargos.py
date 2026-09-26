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
# «por el que se promueve a la categoría de Magistrado de la Sala Quinta del
# Tribunal Supremo a don Celso Rodríguez Padrón»: así se nombra a los
# magistrados del Supremo que vienen de la carrera.
_PROMUEVE = re.compile(
    rf"^promueve a la categor[ií]a de (?P<cargo>.+?) a {_TRATAMIENTO} (?P<nombre>.+)$"
)
# «por el que se nombra en propiedad a don Manuel Marchena Gómez, Magistrado de
# la Sala Segunda del Tribunal Supremo» y «se nombra a don Manuel Marchena
# Gómez, Presidente de la Sala Segunda»: el nombre delante y el cargo detrás.
_NOMBRA_A_QUIEN = re.compile(
    rf"^nombra(?: en propiedad)? a {_TRATAMIENTO} (?P<nombre>[^,]+), (?P<cargo>.+)$"
)
# «se nombra Presidente de la Sala Segunda del Tribunal Supremo don Juan
# Saavedra Ruiz», sin la «a».
_NOMBRA_SIN_A = re.compile(rf"^nombra (?P<cargo>.+?) {_TRATAMIENTO} (?P<nombre>.+)$")

# «Vocal del Consejo General del Poder Judicial a propuesta del Senado».
_PROPUESTA_EN_EL_TITULO = re.compile(r"^(?P<cargo>.+?) a propuesta del? .+$")
# «se dispone el cese por renuncia al cargo de Vocal del Consejo General del
# Poder Judicial de doña María Concepción Sáez Rodríguez».
_CESE_AL_CARGO = re.compile(
    rf"^dispone el cese(?: por (?P<motivo>[a-záéíóúñ ]{{3,40}}?))? al cargo de (?P<cargo>.+?)"
    rf" de {_TRATAMIENTO} (?P<nombre>.+)$"
)

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
    # «Declara» en vez de «dispone» cuando cesa un Presidente del Gobierno.
    rf"^(?:dispone|declara) el cese(?:, (?P<motivo_antes>{_MOTIVO}),)?(?: de)? {_TRATAMIENTO}"
    rf" (?P<nombre>.+?)"
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
        # «Vocal del Consejo General del Poder Judicial a propuesta del Senado»:
        # el proponente va en medio y no es parte del cargo. Sólo se quita en
        # una alta instancia; quién propuso lo lee el conector del texto.
        entre = _PROPUESTA_EN_EL_TITULO.match(cargo)
        if entre and es_alta_instancia(entre.group("cargo")):
            cargo = entre.group("cargo")
        if _es_nombre(nombre) and cargo:
            return Acto(tipo="nombramiento", cargo=cargo, nombre=nombre, **comun)
        # «se nombra en propiedad a don X, Magistrado…» también encaja aquí,
        # con «en propiedad» de cargo y el resto de nombre, que no lo es. Se
        # sigue probando con las fórmulas de la carrera judicial.

    # Las fórmulas de la carrera judicial. Sólo se aceptan si el cargo es de
    # una alta instancia (`es_alta_instancia`): fuera de ahí son ascensos de
    # carrera, y una fórmula nueva no puede colar lo que antes no pasaba.
    for formula in (_PROMUEVE, _NOMBRA_A_QUIEN, _NOMBRA_SIN_A):
        j = formula.match(resto)
        if not j:
            continue
        nombre, cargo = j.group("nombre").strip(), j.group("cargo").strip()
        if _es_nombre(nombre) and cargo and es_alta_instancia(cargo):
            return Acto(tipo="nombramiento", cargo=cargo, nombre=nombre, **comun)

    c = _CESE_AL_CARGO.match(resto)
    if c:
        nombre, cargo = c.group("nombre").strip(), c.group("cargo").strip()
        if _es_nombre(nombre) and es_alta_instancia(cargo):
            motivo = f"por {c.group('motivo')}" if c.group("motivo") else ""
            return Acto(tipo="cese", cargo=cargo, nombre=nombre, motivo=motivo, **comun)

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
    "magistrada": "Magistrado",
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
    # En la Fiscalía el género va en la cuarta palabra: «Fiscal de Sala Jefa».
    return re.sub(r"^Fiscal de Sala Jefa\b", "Fiscal de Sala Jefe", cargo)


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


# --- Altas instancias judiciales y fiscales -----------------------------------

# La ampliación de §12 del 26/9/2026: el Supremo, el Constitucional, el CGPJ,
# la Audiencia Nacional, las presidencias de los TSJ, el Fiscal General y los
# fiscales de sala, por su nombramiento en el BOE. La carrera judicial y fiscal
# ordinaria sigue fuera: jueces de instancia, audiencias provinciales,
# fiscales provinciales. Como con los altos cargos, es una lista de lo que SÍ.
_ALTAS_INSTANCIAS = tuple(
    re.compile(p)
    for p in (
        r"^presidente del tribunal supremo\b",
        r"^vicepresidente del tribunal supremo\b",
        r"^presidente de la sala (primera|segunda|tercera|cuarta|quinta) del tribunal supremo$",
        r"^magistrado (de la sala (primera|segunda|tercera|cuarta|quinta) )?del tribunal supremo$",
        r"^presidente del tribunal constitucional$",
        r"^vicepresidente del tribunal constitucional$",
        r"^magistrado del tribunal constitucional$",
        r"^presidente del consejo general del poder judicial$",
        r"^vocal del consejo general del poder judicial$",
        r"^presidente de la audiencia nacional$",
        r"^presidente de la sala de (lo penal|lo contencioso-administrativo|lo social|apelacion)"
        r" de la audiencia nacional$",
        r"^presidente del tribunal superior de justicia del? [a-z ,'().-]+$",
        r"^fiscal general del estado$",
        r"^teniente fiscal (de la fiscalia )?del tribunal supremo$",
        r"^fiscal de sala\b",
    )
)


def es_alta_instancia(cargo: str) -> bool:
    """¿El puesto es de una alta instancia judicial o fiscal de la lista?"""
    p = _plano(puesto(cargo)).strip()
    return any(r.search(p) for r in _ALTAS_INSTANCIAS)


def es_publicable(cargo: str) -> bool:
    """Lo que se lee del BOE: un alto cargo o una alta instancia."""
    return es_alto_cargo(cargo) or es_alta_instancia(cargo)


_INSTITUCIONES = (
    # La Fiscalía primero: «Fiscal de Sala del Tribunal Supremo» es de la
    # Fiscalía, aunque nombre al Supremo.
    (re.compile(r"^(fiscal|teniente fiscal)\b"), "Fiscalía General del Estado"),
    (re.compile(r"\btribunal constitucional\b"), "Tribunal Constitucional"),
    (re.compile(r"\btribunal supremo\b"), "Tribunal Supremo"),
    (re.compile(r"\bconsejo general del poder judicial\b"), "Consejo General del Poder Judicial"),
    (re.compile(r"\baudiencia nacional\b"), "Audiencia Nacional"),
)
_TSJ = re.compile(r"(Tribunal Superior de Justicia del? .+)$", re.IGNORECASE)


def institucion_judicial(cargo: str) -> str:
    """La institución de un cargo de alta instancia, por su propio nombre; ''.

    El departamento de estas disposiciones es quien las publica —el CGPJ, la
    Jefatura del Estado—, no donde está el puesto: «Magistrado del Supremo ·
    Consejo General del Poder Judicial» diría que es vocal del Consejo.
    """
    if not es_alta_instancia(cargo):
        return ""
    p = _plano(puesto(cargo))
    tsj = _TSJ.search(cargo)
    if tsj and not p.startswith(("fiscal", "teniente fiscal")):
        return tsj.group(1)[0].upper() + tsj.group(1)[1:]
    for patron, institucion in _INSTITUCIONES:
        if patron.search(p):
            return institucion
    return ""


# Quién propone a una alta instancia, según el cuerpo del Real Decreto: «y a
# propuesta del Senado, Vengo en nombrar…». Lista cerrada; si el texto nombra
# a más de uno, o a ninguno de éstos, no se dice nada.
_PROPUESTAS = (
    (re.compile(r"a propuesta del gobierno\b"), "Gobierno"),
    (re.compile(r"a propuesta del congreso de los diputados\b"), "Congreso de los Diputados"),
    (re.compile(r"a propuesta del senado\b"), "Senado"),
    (
        re.compile(
            r"a propuesta del (?:pleno del )?consejo general del poder judicial\b"
            r"|por acuerdo (?:del pleno|de la comision permanente)"
            r" del consejo general del poder judicial\b"
        ),
        "Consejo General del Poder Judicial",
    ),
    (
        re.compile(r"a propuesta del (?:pleno del )?tribunal constitucional\b"),
        "Tribunal Constitucional",
    ),
)


def propuesta_de(parrafos: list[str]) -> str:
    """Quién propuso el nombramiento, si el cuerpo lo dice de uno solo; ''."""
    texto = re.sub(r"\s+", " ", _plano(" ".join(parrafos)))
    hallados = {nombre for patron, nombre in _PROPUESTAS if patron.search(texto)}
    return hallados.pop() if len(hallados) == 1 else ""


def es_alto_cargo(cargo: str) -> bool:
    """¿El puesto es un alto cargo en el sentido de la Ley 3/2015?"""
    p = _plano(puesto(cargo))
    if _NOMBRADOS_POR_EL_GOBIERNO.search(p):
        return True
    if _CARRERAS.search(p):
        return False
    return any(r.search(p) for r in _ALTOS_CARGOS)


# --- Cargos compuestos --------------------------------------------------------

# «Vicepresidenta del Gobierno y Ministra de la Presidencia y para las
# Administraciones Territoriales» son DOS cargos. Se parte en la «y» que va
# seguida de otro título de cargo; las demás «y» son del nombre del
# ministerio («Agricultura y Pesca, Alimentación y Medio Ambiente»).
_OTRO_CARGO = re.compile(
    r" y (?=(?:Ministr[oa]|Vicepresident[ea]|Secretari[oa] de Estado|Presidente|Presidenta)\b)"
)


def separar_cargos(cargo: str) -> list[str]:
    """Los cargos que nombra un texto, uno por uno."""
    return [c.strip() for c in _OTRO_CARGO.split(cargo) if c.strip()]


# --- Reales Decretos colectivos -------------------------------------------------

# Los que forman o disuelven un gobierno llevan los nombres en el cuerpo, no
# en el título: «por el que se nombran Ministros del Gobierno», «por el que
# se declara el cese de los miembros del Gobierno». Sólo ésos: un título
# plural que no es de gobierno —magistrados por antigüedad, por ejemplo— no
# se abre.
_COLECTIVO_NOMBRA = re.compile(r"por el que se nombran Ministros del Gobierno", re.IGNORECASE)
_COLECTIVO_CESE = re.compile(
    r"por el que se (?:declara|dispone) el cese de (?:los )?(?:siguientes )?"
    r"(?:miembros del Gobierno|Vicepresidentes y Ministros)",
    re.IGNORECASE,
)

# En el cuerpo: «Ministra de Justicia a doña María Dolores Delgado García.»
_PARRAFO_NOMBRA = re.compile(rf"^(?P<cargo>[A-ZÁÉÍÓÚ].+?) a {_TRATAMIENTO} (?P<nombre>.+?)\.?$")
# y «Don Rafael Catalá Polo, como Ministro de Justicia.»
_PARRAFO_CESE = re.compile(r"^(?:Don|Doña|D\.|Dña\.) (?P<nombre>.+?), como (?P<cargo>.+?)\.?$")


def tipo_colectivo(titulo: str) -> str | None:
    """«nombramiento» o «cese» si es un Real Decreto colectivo de gobierno."""
    t = re.sub(r"\s+", " ", titulo or "")
    if not t.startswith("Real Decreto"):
        return None
    if _COLECTIVO_NOMBRA.search(t):
        return "nombramiento"
    if _COLECTIVO_CESE.search(t):
        return "cese"
    return None


def leer_cuerpo(titulo: str, parrafos: list[str]) -> list[Acto]:
    """Los actos de un Real Decreto colectivo, uno por persona y cargo.

    Se leen sólo los párrafos que siguen la fórmula entera; el preámbulo
    («De conformidad con…»), la fecha y las firmas no la siguen y se saltan
    solos. Un párrafo que no encaja no se interpreta.
    """
    tipo = tipo_colectivo(titulo)
    m = _CABEZA.match(re.sub(r"\s+", " ", titulo or "").strip())
    if tipo is None or m is None:
        return []
    comun = {
        "numero": m.group("numero"),
        "fecha_decreto": _fecha(m.group("anio"), m.group("mes"), m.group("dia")),
    }
    patron = _PARRAFO_NOMBRA if tipo == "nombramiento" else _PARRAFO_CESE
    actos = []
    for parrafo in parrafos:
        p = re.sub(r"\s+", " ", parrafo or "").strip()
        if p.lower().startswith(("de conformidad", "dado en", "vengo en", "como consecuencia")):
            continue
        encaja = patron.match(p)
        if not encaja:
            continue
        nombre = encaja.group("nombre").strip()
        if not _es_nombre(nombre):
            continue
        for cargo in separar_cargos(encaja.group("cargo").strip()):
            actos.append(Acto(tipo=tipo, cargo=cargo, nombre=nombre, **comun))
    return actos


# --- El organismo de un acto ----------------------------------------------------

_MIEMBRO_DEL_GOBIERNO = re.compile(
    r"^(presidente del gobierno|vicepresidente( primero| segundo| tercero| cuarto)? del gobierno"
    r"|ministro)\b"
)


def organismo_del_acto(departamento: str, cargo: str) -> str:
    """El organismo que se enseña junto a un cargo, o '' si no aporta.

    El departamento de una disposición es quien la PUBLICA, que casi siempre
    es el ministerio del puesto. Con los miembros del Gobierno no: a todos
    los ministros los nombra un Real Decreto de Presidencia del Gobierno, y
    al Presidente, uno de la Jefatura del Estado. «Ministra de Justicia ·
    Presidencia del Gobierno» diría que la ministra es de Presidencia. Ahí
    el cargo ya nombra su ministerio, y no se pone nada.
    """
    if _MIEMBRO_DEL_GOBIERNO.search(_plano(puesto(cargo))):
        return ""
    if _plano(departamento).strip() == "jefatura del estado":
        return ""
    return departamento


# --- Del puesto a su órgano -------------------------------------------------------

# Quien es «Director General de Carreteras» está al frente de la «Dirección
# General de Carreteras», que es el órgano que contrata. La relación la da la
# propia estructura de la Administración, no un parecido de nombres: por eso
# sólo se usan las formas fijas de abajo, y el volcado sólo enlaza cuando el
# nombre resultante coincide con UN órgano del Estado.
_ORGANO_DEL_PUESTO = (
    (re.compile(r"^Director General (de|del) (.+)$"), r"Dirección General \1 \2"),
    (re.compile(r"^Secretario de Estado (de|del|para) (.+)$"), r"Secretaría de Estado \1 \2"),
    (re.compile(r"^Secretario General (de|del|para) (.+)$"), r"Secretaría General \1 \2"),
    (re.compile(r"^Subsecretario (de|del|para) (.+)$"), r"Subsecretaría \1 \2"),
    (re.compile(r"^Ministro (de|del|para) (.+)$"), r"Ministerio \1 \2"),
    (re.compile(r"^Delegado del Gobierno en (.+)$"), r"Delegación del Gobierno en \1"),
    # Quien preside o dirige un organismo o una empresa pública: el órgano es
    # el propio organismo. «Presidente de CASA 47 Entidad Pública
    # Empresarial», «Director de la Agencia Estatal de Meteorología».
    (re.compile(r"^(?:Presidente|Director) (?:de la |del |de los |de las |de )(.+)$"), r"\1"),
)


def organo_del_puesto(nombre_puesto: str) -> str:
    """El nombre del órgano que dirige quien ocupa el puesto, o ''."""
    for patron, forma in _ORGANO_DEL_PUESTO:
        m = patron.match(nombre_puesto)
        if m:
            organo = m.expand(forma).strip()
            # «Director del Departamento…» dirige un departamento de un
            # gabinete, no un órgano de contratación: se deja que el volcado
            # no lo encuentre, en vez de afinar aquí.
            return organo
    return ""
