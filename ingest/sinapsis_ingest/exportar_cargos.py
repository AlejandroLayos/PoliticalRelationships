"""Exporta los cargos públicos a `cargos.json`, aparte del grafo.

Es la única puerta por la que sale el nombre de una persona física, y por eso
es una puerta propia y estrecha en vez de una excepción dentro de la general.
El volcado del grafo sigue sin dejar pasar a NINGUNA persona —como desde
septiembre de 2026—; una excepción metida ahí tendría que convivir con tres
reglas de bloqueo y con el tapado de nombres, y el día que alguien tocara una
de ellas podría abrirla sin querer.

## Qué tiene que cumplir una persona para salir aquí (spec §12)

Todo a la vez, comprobado en SQL sobre la base, no sobre lo que diga el
conector:

1. Esquema `Person`, canónica (no absorbida por una fusión).
2. Clave `boe:persona:…`, `oci:persona:…` o `congreso:persona:…`, que sólo
   ponen los conectores del BOE, de la Oficina de Conflictos de Intereses y
   del Congreso (ver `PUERTAS`).
3. Marca `cargo_publico`, que también ponen sólo esos conectores.
4. Ningún identificador personal (DNI/NIE): ninguna de las dos fuentes los
   publica, así que si hay uno, esa ficha no viene de donde dice.
5. Y lo que sale de ella son **sólo** sus actos de cargo (`Occupancy`), sus
   autorizaciones de actividad privada y las actividades que declaró al
   Congreso como diputado, con procedencia de SU fuente: ni una arista más,
   venga de donde venga. «Sólo en ese papel».

Un diputado sale si se une a un alto cargo del BOE (dos señales, ver abajo)
o si hizo declaración de actividades: la sección no es un censo de escaños,
y de quien sólo consta el escaño no hay nada que cruzar.

Lo demás de la persona —si administra una empresa, si cobró una subvención—
no sale por aquí. Cuando haya un vínculo así afirmado por una fuente, o
confirmado por una persona en la cola de revisión, entrará con su propia
regla y su propio test.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import structlog

from sinapsis_ingest.cargos import organo_del_puesto
from sinapsis_ingest.cnmv import es_medio_de_comunicacion, mismo_titular
from sinapsis_ingest.store import Store
from sinapsis_ingest.territorio import COMUNIDADES, clasificar_entidad
from sinapsis_ingest.util import es_identificador_personal, parece_forma_societaria

log = structlog.get_logger()


def periodos(actos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Junta nombramientos y ceses de un mismo puesto en periodos.

    Cada acto es un dict con `tipo` («nombramiento» o «cese»), `fecha`
    (date), `puesto`, `cargo`, `organismo`, `boe` y `url`.

    Por puesto, en orden de fecha: un nombramiento abre un periodo y el
    siguiente cese del mismo puesto lo cierra. Lo que no se puede emparejar
    se enseña tal cual, sin rellenar:

    - un cese sin nombramiento (fue nombrado antes de lo que se ha leído)
      sale con `desde` vacío;
    - un nombramiento sin cese sale con `hasta` vacío, que quiere decir «no
      consta cese», no «sigue en el cargo»;
    - dos nombramientos seguidos sin cese entre medias —un cese colectivo
      que no se lee, por ejemplo— dan dos periodos, el primero sin fin. No
      se inventa la fecha en que acabó.

    El mismo día, el cese va antes que el nombramiento: es lo que pasa
    cuando se forma un gobierno y se vuelve a nombrar a alguien en el mismo
    cargo, y al revés cerraría el periodo nuevo en el día en que empieza.
    """
    orden = {"cese": 0, "nombramiento": 1}
    por_puesto: dict[str, list[dict[str, Any]]] = {}
    for a in actos:
        por_puesto.setdefault(a["puesto"], []).append(a)

    salida: list[dict[str, Any]] = []
    for lista in por_puesto.values():
        # Un mandato del Congreso ya es un periodo entero, con su alta y su
        # baja: no hay que emparejar nada.
        for a in lista:
            if a["tipo"] == "mandato":
                salida.append(
                    {
                        "puesto": a["puesto"],
                        "cargo": a["cargo"],
                        "organismo": a.get("organismo") or "",
                        "desde": a["fecha"],
                        **({"hasta": a["hasta"]} if a.get("hasta") else {}),
                        "urlDesde": a["url"],
                        **_fuente_no_boe(a),
                        **{
                            k: a[k]
                            for k in ("formacion", "grupo", "circunscripcion", "cruce")
                            if a.get(k)
                        },
                    }
                )
        lista = [a for a in lista if a["tipo"] != "mandato"]
        lista.sort(key=lambda a: (a["fecha"], orden.get(a["tipo"], 2)))
        abierto: dict[str, Any] | None = None
        for a in lista:
            if a["tipo"] == "nombramiento":
                if abierto is not None:
                    salida.append(abierto)
                abierto = {
                    "puesto": a["puesto"],
                    "cargo": a["cargo"],
                    "organismo": a.get("organismo") or "",
                    "desde": a["fecha"],
                    "boeDesde": a["boe"],
                    "urlDesde": a["url"],
                    **_fuente_no_boe(a),
                    **({"ambito": a["ambito"]} if a.get("ambito") else {}),
                    **({"propuesta": a["propuesta"]} if a.get("propuesta") else {}),
                }
            elif a["tipo"] == "cese":
                cierre = {
                    "hasta": a["fecha"],
                    "boeHasta": a["boe"],
                    "urlHasta": a["url"],
                    **({"motivoCese": a["motivo"]} if a.get("motivo") else {}),
                }
                if abierto is not None:
                    salida.append({**abierto, **cierre})
                    abierto = None
                else:
                    salida.append(
                        {
                            "puesto": a["puesto"],
                            "cargo": a["cargo"],
                            "organismo": a.get("organismo") or "",
                            **cierre,
                            **_fuente_no_boe(a),
                            **({"ambito": a["ambito"]} if a.get("ambito") else {}),
                        }
                    )
        if abierto is not None:
            salida.append(abierto)

    def reciente(p: dict[str, Any]) -> date:
        return p.get("hasta") or p.get("desde") or date.min

    # Lo más reciente arriba, y a igualdad, lo que sigue abierto primero.
    salida.sort(key=lambda p: (reciente(p), "hasta" not in p), reverse=True)
    return salida


def _plano(texto: str) -> str:
    sin = "".join(
        c for c in unicodedata.normalize("NFKD", texto or "") if unicodedata.category(c) != "Mn"
    )
    # El guion une: «BESS-BEYOND» es una palabra, no dos.
    sin = re.sub(r"(?<=\w)-(?=\w)", "", sin)
    return re.sub(r"[^a-z0-9]+", " ", sin.lower()).strip()


def organos_del_estado(store: Store) -> dict[str, list[tuple[str, str]]]:
    """{nombre normalizado: [(clave, nombre)]} de los órganos del Estado.

    Sólo los que la jerarquía de su propia fuente sitúa en la Administración
    del Estado: «Dirección General de Carreteras» existe también en alguna
    comunidad autónoma, y quien fue director general del Estado no dirigió
    la de la comunidad.
    """
    filas = store.conn.execute(
        """
        SELECT caption, dedupe_key, properties FROM entities
        WHERE canonical_id IS NULL AND ftm_schema = 'PublicBody'
          AND dedupe_key NOT LIKE 'boe:%'
        """
    ).fetchall()
    por_nombre: dict[str, list[tuple[str, str]]] = {}
    for f in filas:
        props = {**(f["properties"] or {}), "name": f["caption"]}
        if clasificar_entidad(props).nivel != "estatal":
            continue
        por_nombre.setdefault(_plano(f["caption"]), []).append((f["dedupe_key"], f["caption"]))
    return por_nombre


# Las abreviaturas con que la Oficina de Conflictos de Intereses escribe los
# cargos, en mayúsculas y sin tildes: «D. GRAL. DE ORDENACION PROFESIONAL»,
# «S.E. PARA LA AGENDA 2030». En orden: «D. GRAL.» antes que «D.».
_ABREVIATURAS_OCI = (
    (re.compile(r"^D\. ?GRAL\.? "), "DIRECTOR GENERAL "),
    (re.compile(r"^S\. ?E\.? "), "SECRETARIO DE ESTADO "),
    (re.compile(r"^D\. "), "DIRECTOR "),
)

# El principio del cargo, sin género, con la forma que esperan los patrones
# de `organo_del_puesto`. Lo que no empieza por uno de éstos no se busca.
_ROLES_OCI = {
    "director general": "Director General",
    "directora general": "Director General",
    "secretario de estado": "Secretario de Estado",
    "secretaria de estado": "Secretario de Estado",
    "secretario general": "Secretario General",
    "secretaria general": "Secretario General",
    "subsecretario": "Subsecretario",
    "subsecretaria": "Subsecretario",
    "ministro": "Ministro",
    "ministra": "Ministro",
    "delegado del gobierno en": "Delegado del Gobierno en",
    "delegada del gobierno en": "Delegado del Gobierno en",
    "presidente": "Presidente",
    "presidenta": "Presidente",
    "director": "Director",
    "directora": "Director",
}


def puesto_de_la_oci(cargo: str) -> str:
    """«D. GRAL. DE ORDENACION PROFESIONAL» → «Director General de ordenacion
    profesional», o '' si no es un cargo que dirija un órgano.

    SÓLO para buscar el órgano, que se compara sin tildes ni mayúsculas
    (`_plano`) y exige el nombre exacto de UNO del Estado: igual de estricto
    que con el BOE. Para enseñar, el cargo sigue siendo el de la fuente.
    """
    texto = " ".join((cargo or "").split()).upper()
    for patron, forma in _ABREVIATURAS_OCI:
        texto = patron.sub(forma, texto, count=1)
    bajo = texto.lower()
    for rol in sorted(_ROLES_OCI, key=len, reverse=True):
        if bajo.startswith(rol + " "):
            return _ROLES_OCI[rol] + bajo[len(rol) :]
    return ""


def organo_de(puesto: str, organos: dict[str, list[tuple[str, str]]]) -> dict[str, str] | None:
    """El órgano que dirigía el puesto, si su nombre es el de UNO del Estado."""
    nombre = organo_del_puesto(puesto)
    if not nombre:
        return None
    hallados = organos.get(_plano(nombre), [])
    if len(hallados) != 1:
        # Ninguno, o varios con el mismo nombre: no se elige.
        return None
    clave, caption = hallados[0]
    return {"clave": clave, "nombre": caption}


def nombre_natural(nombre: str) -> str:
    """«Báñez García, María Fátima» → «María Fátima Báñez García».

    El Congreso y la Oficina de Conflictos de Intereses escriben primero los
    apellidos y el BOE no; en la misma página, la misma persona tiene que
    leerse igual venga de donde venga. Sólo se da la vuelta a lo que tiene
    exactamente una coma con texto a los dos lados.
    """
    partes = [p.strip() for p in nombre.split(",")]
    if len(partes) != 2 or not all(partes):
        return nombre
    return f"{partes[1]} {partes[0]}"


PRESIDENCIA = "Presidente del Gobierno"


def formacion_en(mandatos: list[dict[str, Any]], fecha: str) -> str:
    """La formación del mandato del Congreso que cubre `fecha`, o la del
    último anterior. `mandatos`, ordenados por `desde`."""
    if not fecha:
        return ""
    cubre = [
        m for m in mandatos if m["desde"] <= fecha and (not m.get("hasta") or fecha <= m["hasta"])
    ]
    if cubre:
        return cubre[-1]["formacion"]
    antes = [m for m in mandatos if m["desde"] <= fecha]
    return antes[-1]["formacion"] if antes else ""


# Lo que puede ir entre «Presidente de» y el nombre de la comunidad. Se quita
# uno cada vez y lo que queda tiene que ser, entero, una forma de la comunidad.
_INSTITUCIONES = (
    "junta de comunidades de ",
    "junta de ",
    "comunidad autonoma de las ",
    "comunidad autonoma de la ",
    "comunidad autonoma de ",
    "comunidad foral de ",
    "comunidad de ",
    "generalitat de ",
    "xunta de ",
    "gobierno de ",
    "principado de ",
    "ciudad autonoma de ",
    "ciudad de ",
    "consejo de gobierno de ",
    "diputacion general de ",
)

# Las formas de COMUNIDADES que nombran la comunidad o su gobierno, no un
# servicio de salud.
_FORMAS_DE_COMUNIDAD = {
    _plano(forma): comunidad
    for comunidad, formas in COMUNIDADES.items()
    for forma in formas
    if not forma.startswith(("servicio", "servizo", "institut", "osakidetza", "osasunbidea"))
}


def comunidad_de_la_presidencia(puesto: str) -> str:
    """«Presidente de la Junta de Andalucía» → «Andalucía»; '' si el puesto no
    es, entero, la presidencia de una comunidad autónoma.

    Estricto a propósito: «Presidente de la Autoridad Portuaria de Baleares»
    lleva «Baleares» y no es la presidencia de las Islas Baleares.
    """
    if not puesto.startswith("Presidente "):
        return ""
    resto = _plano(puesto[len("Presidente ") :])
    for articulo in ("de la ", "de las ", "del ", "de "):
        if resto.startswith(articulo):
            resto = resto[len(articulo) :]
            break
    candidatos = {resto} | {resto[len(i) :] for i in _INSTITUCIONES if resto.startswith(i)}
    halladas = {_FORMAS_DE_COMUNIDAD[c] for c in candidatos if c in _FORMAS_DE_COMUNIDAD}
    return halladas.pop() if len(halladas) == 1 else ""


def presidencias_autonomicas(personas: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """{comunidad: [presidencias]} de lo leído del BOE, de la más antigua a la
    más reciente. Sin el partido: el BOE no lo dice, y el Congreso no sirve
    para quien no fue diputado.
    """
    salida: dict[str, list[dict[str, Any]]] = {}
    for persona in personas:
        for p in persona["periodos"]:
            if p.get("fuente"):
                continue
            comunidad = comunidad_de_la_presidencia(p.get("puesto", ""))
            if not comunidad:
                continue
            salida.setdefault(comunidad, []).append(
                {
                    "persona": persona["clave"],
                    "nombre": persona["nombre"],
                    **{k: p[k] for k in ("desde", "hasta") if p.get(k)},
                }
            )
    # A igual fecha, el cese del saliente antes que el nombramiento del
    # entrante: el relevo de Lambán por Azcón es del mismo día.
    for lista in salida.values():
        lista.sort(key=lambda x: (x.get("desde") or x.get("hasta") or "", "desde" in x))
    return salida


def presidencias_del_gobierno(personas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Las presidencias del Gobierno de lo leído, con la formación con la que
    fue elegido diputado cada presidente, si su ficha está unida al Congreso.

    Salen de los Reales Decretos del Presidente, sin inferir nada: si falta un
    nombramiento o un cese, el periodo queda abierto por ese lado.
    """
    salida = []
    for persona in personas:
        mandatos = sorted(
            (
                p
                for p in persona["periodos"]
                if p.get("fuente") == "congreso" and p.get("formacion") and p.get("desde")
            ),
            key=lambda p: p["desde"],
        )
        for p in persona["periodos"]:
            if p.get("puesto") != PRESIDENCIA or p.get("fuente"):
                continue
            salida.append(
                {
                    "persona": persona["clave"],
                    "nombre": persona["nombre"],
                    "desde": p.get("desde"),
                    "hasta": p.get("hasta"),
                    "formacion": formacion_en(mandatos, p.get("desde") or p.get("hasta") or ""),
                }
            )
    salida.sort(key=lambda x: x["desde"] or x["hasta"] or "")
    return salida


def gobierno_en(presidencias: list[dict[str, Any]], fecha: str) -> dict[str, str] | None:
    """Bajo qué presidencia del Gobierno cae `fecha`, o None si no se sabe.

    El día del relevo cuenta ya como del nuevo presidente: el cese del
    saliente y el nombramiento del entrante llevan la misma fecha. Una
    presidencia sin cese leído dura hasta la siguiente que se haya leído.
    """
    candidatas = [
        x
        for x in presidencias
        if (not x["desde"] or x["desde"] <= fecha) and (not x["hasta"] or fecha < x["hasta"])
    ]
    if not candidatas:
        return None
    x = max(candidatas, key=lambda x: x["desde"] or "")
    return {
        "persona": x["persona"],
        "nombre": x["nombre"],
        **({"formacion": x["formacion"]} if x["formacion"] else {}),
    }


def _fuente_no_boe(acto: dict[str, Any]) -> dict[str, str]:
    """La fuente de un periodo, sólo si no es el BOE: la web lo dice."""
    fuente = acto.get("fuente") or "boe"
    return {} if fuente == "boe" else {"fuente": fuente}


def _serializable(p: dict[str, Any]) -> dict[str, Any]:
    return {k: (v.isoformat() if isinstance(v, date) else v) for k, v in p.items()}


#: Las puertas: el prefijo de clave que pone cada conector, y la ÚNICA fuente
#: cuya procedencia vale para él. Una ficha con clave del BOE pero sin
#: documento del BOE no sale, y al revés.
PUERTAS = {"boe:persona:": "boe", "oci:persona:": "oci", "congreso:persona:": "congreso"}

#: Días de margen entre la fecha de cese que da la Oficina de Conflictos de
#: Intereses y la que publica el BOE: la una es la del cese y la otra la de su
#: publicación, que suele ser el día siguiente.
MARGEN_CESE = 10

#: Lo que se lee de cada actividad que declara un diputado.
_CAMPOS_DECLARACION = ("empleador", "sector", "periodo", "descripcion", "fechaRegistro", "url")

#: Cuántos cruces del cargo a la empresa viajan con el grafo, para la portada.
#: El resto está en cargos.json, en la ficha de cada persona y sociedad.
MAX_CRUCES_EN_PORTADA = 40


def _filas_de_la_puerta(store: Store, esquema: str, extra: str = "") -> list[Any]:
    """Aristas de las personas que pasan la puerta, con su procedencia."""
    condiciones = " OR ".join("(p.dedupe_key LIKE %s AND rd.source_id = %s)" for _ in PUERTAS)
    parametros: list[Any] = []
    for prefijo, fuente in PUERTAS.items():
        parametros += [prefijo + "%", fuente]
    return store.conn.execute(
        f"""
        SELECT p.id, p.caption, p.dedupe_key, COALESCE(p.nif, '') AS nif,
               p.properties AS props_persona,
               t.caption AS destino, t.dedupe_key AS clave_destino,
               r.start_date, r.end_date, r.properties
        FROM relationships r
        JOIN entities p ON p.id = r.source_entity_id AND p.canonical_id IS NULL
        JOIN entities t ON t.id = r.target_entity_id AND t.canonical_id IS NULL
        WHERE r.ftm_schema = %s
          AND r.status <> 'retracted'
          AND p.ftm_schema = 'Person'
          AND (p.properties ->> 'cargo_publico') = 'true'
          {extra}
          AND EXISTS (
              SELECT 1 FROM provenance pv
              JOIN raw_documents rd ON rd.id = pv.raw_document_id
              WHERE pv.relationship_id = r.id AND ({condiciones})
          )
        """,
        [esquema, *parametros],
    ).fetchall()


def _palabras(texto: str) -> list[str]:
    """Las palabras de un nombre, con las siglas juntas.

    «S.L.U.», «S. L. U.» y «SLU» son la misma forma societaria, y la fuente
    escribe las tres («REDEIA,SL»): letras sueltas seguidas se juntan en una.
    """
    salida: list[str] = []
    sigla = False
    for palabra in _plano(texto).split():
        if len(palabra) == 1:
            if sigla:
                salida[-1] += palabra
            else:
                salida.append(palabra)
            sigla = True
        else:
            salida.append(palabra)
            sigla = False
    return salida


def empresas_por_nombre(store: Store) -> dict[str, list[tuple[str, str]]]:
    """{denominación normalizada: [(clave, nombre)]} de las sociedades del mapa.

    Sólo las que llevan forma societaria en el nombre. La denominación social
    es única en España —el Registro Mercantil Central no inscribe dos
    iguales—, así que «EL CORTE INGLES, S.A.» dentro del texto de una
    autorización es esa sociedad y no otra. Un nombre sin forma societaria
    («LOGISTA», «OESIA») no tiene esa garantía y no se cruza.
    """
    filas = store.conn.execute(
        """
        SELECT caption, dedupe_key, COALESCE(nif, '') AS nif FROM entities
        WHERE canonical_id IS NULL
          AND ftm_schema IN ('Company', 'Organization', 'LegalEntity')
          AND dedupe_key NOT LIKE 'oci:%'
          AND dedupe_key NOT LIKE 'boe:%'
          -- Lo que declaran los diputados es su texto, no una sociedad del
          -- mapa: sin esto, «UNIPREX S.A.U.» declarado se cruzaría consigo.
          AND dedupe_key NOT LIKE 'congreso:%'
          AND dedupe_key NOT LIKE 'senado:%'
        """
    ).fetchall()
    mapa: dict[str, list[tuple[str, str]]] = {}
    for f in filas:
        if es_identificador_personal(f["nif"]) or not parece_forma_societaria(f["caption"]):
            continue
        mapa.setdefault(" ".join(_palabras(f["caption"])), []).append(
            (f["dedupe_key"], f["caption"])
        )
    return mapa


# Lo que puede ir justo antes del nombre de una sociedad en el texto de una
# autorización: «socio DE Ey Abogados», «consejero DEL grupo», «EN Indra».
_ANTES_DEL_NOMBRE = frozenset(
    {"de", "del", "la", "el", "los", "las", "en", "para", "con", "y", "a", "al"}
)

# Las formas societarias, ya normalizadas: son el final de una denominación.
_FORMAS = frozenset(
    {
        "sa",
        "sau",
        "sl",
        "slu",
        "slp",
        "sll",
        "sal",
        "sme",
        "mp",
        "scoop",
        "coop",
        "aie",
        "ute",
        "sad",
        "se",
    }
)


def es_sociedad_mercantil(nombre: str) -> bool:
    """Si la denominación acaba en una forma de sociedad (S.A., S.L.…).

    `parece_forma_societaria` reconoce también universidades, fundaciones o
    asociaciones, que es lo que hace falta para no tratarlas como personas.
    Para decir «una sociedad que cobra dinero público» hace falta una
    sociedad de verdad: la Universidad de Cantabria no lo es.
    """
    palabras = _palabras(nombre)
    return bool(palabras) and palabras[-1] in _FORMAS


def empresa_en(texto: str, mapa: dict[str, list[tuple[str, str]]]) -> dict[str, str] | None:
    """La sociedad del mapa que nombra un texto, entera y sin dudas.

    Se busca la denominación completa, palabra a palabra: «SOCIO DE EY
    ABOGADOS, S.L.P.» contiene «EY ABOGADOS, S.L.P.». Pero entera de verdad:

    - por delante, el principio del texto o una preposición o artículo.
      «BESS-BEYOND SOLUCIONES Y SERVICIOS, S.L.» contiene las palabras de
      «BEYOND SOLUCIONES Y SERVICIOS S.L.», que es OTRA sociedad; salió así
      en el primer cruce con los datos reales;
    - por detrás, una forma societaria, que cierra la denominación, o el
      final del texto.

    Si caben dos sociedades distintas, o el nombre es de varias fichas, no
    se elige.
    """
    palabras = _palabras(texto)
    halladas: dict[str, tuple[str, str]] = {}
    for i in range(len(palabras)):
        if i > 0 and palabras[i - 1] not in _ANTES_DEL_NOMBRE:
            continue
        for j in range(len(palabras), i, -1):
            nombre = " ".join(palabras[i:j])
            if nombre not in mapa:
                continue
            if palabras[j - 1] not in _FORMAS and j != len(palabras):
                continue
            if len(mapa[nombre]) == 1:
                halladas[nombre] = mapa[nombre][0]
            break
    # Una denominación dentro de otra («X, S.A.» y «GRUPO X, S.A.») cuenta
    # como la más larga.
    largas = [n for n in halladas if not any(n != m and n in m for m in halladas)]
    if len(largas) != 1:
        return None
    clave, nombre = halladas[largas[0]]
    return {"clave": clave, "nombre": nombre}


def partidos_por_siglas(store: Store) -> dict[str, dict[str, Any]]:
    """{siglas normalizadas: {"nombre": nombre oficial, "entidad"?: {clave, nombre}}}.

    El puente entre la formación de un diputado —unas siglas, en el Congreso—
    y el partido del mapa del dinero, sin tabla hecha a mano: las siglas y el
    nombre los da el Senado para cada legislatura, y el partido del mapa se
    busca por ese nombre exacto. Unas siglas con dos nombres distintos en
    distintas legislaturas no se usan; un nombre con dos fichas en el mapa,
    tampoco.
    """
    nombres: dict[str, set[str]] = {}
    for f in store.conn.execute(
        """
        SELECT properties FROM entities
        WHERE canonical_id IS NULL AND dedupe_key LIKE 'senado:partido:%'
        """
    ).fetchall():
        props = f["properties"] or {}
        siglas, nombre = props.get("siglasSenado"), props.get("nombreSenado")
        if siglas and nombre:
            nombres.setdefault(_plano(siglas), set()).add(nombre)
    en_el_mapa: dict[str, list[tuple[str, str]]] = {}
    for f in store.conn.execute(
        """
        SELECT caption, dedupe_key FROM entities
        WHERE canonical_id IS NULL
          AND (properties ->> 'partido_politico') = 'true'
          AND dedupe_key NOT LIKE 'senado:%'
        """
    ).fetchall():
        en_el_mapa.setdefault(_plano(f["caption"]), []).append((f["dedupe_key"], f["caption"]))
    salida: dict[str, dict[str, Any]] = {}
    for siglas, suyos in nombres.items():
        if len({_plano(n) for n in suyos}) != 1:
            continue
        nombre = sorted(suyos)[0]
        fichas = en_el_mapa.get(_plano(nombre), [])
        salida[siglas] = {
            "nombre": nombre,
            **(
                {"entidad": {"clave": fichas[0][0], "nombre": fichas[0][1]}}
                if len(fichas) == 1
                else {}
            ),
        }
    return salida


def dinero_del_organo(store: Store, organo: str, empresa: str) -> dict[str, Any] | None:
    """Lo que el órgano `organo` pagó o adjudicó a la sociedad `empresa` (claves),
    en lo leído; None si nada.

    El mismo puente que el índice: el dinero de un expediente es del órgano
    que lo adjudicó. Las fechas son las que trae cada fuente —la concesión
    en BDNS, la publicación del expediente en PLACSP—, no la del contrato, y
    así se dicen.
    """
    filas = store.conn.execute(
        """
        WITH o AS (SELECT id FROM entities WHERE dedupe_key = %s AND canonical_id IS NULL),
             e AS (SELECT id FROM entities WHERE dedupe_key = %s AND canonical_id IS NULL)
        SELECT r.amount, r.start_date, 'pago' AS via
        FROM relationships r, o, e
        WHERE r.ftm_schema = 'Payment' AND r.status <> 'retracted'
          AND r.source_entity_id = o.id AND r.target_entity_id = e.id
        UNION ALL
        SELECT a.amount, a.start_date, 'adjudicacion'
        FROM relationships u
        JOIN entities c ON c.id = u.target_entity_id AND c.ftm_schema = 'Contract'
        JOIN relationships a ON a.source_entity_id = c.id
             AND a.ftm_schema = 'ContractAward' AND a.status <> 'retracted',
             o, e
        WHERE u.ftm_schema = 'UnknownLink' AND u.status <> 'retracted'
          AND u.source_entity_id = o.id AND a.target_entity_id = e.id
        """,
        (organo, empresa),
    ).fetchall()
    filas = [f for f in filas if f["amount"] is not None]
    if not filas:
        return None
    fechas = sorted(f["start_date"] for f in filas if f["start_date"])
    return {
        "importe": str(sum(f["amount"] for f in filas)),
        "pagos": sum(1 for f in filas if f["via"] == "pago"),
        "adjudicaciones": sum(1 for f in filas if f["via"] == "adjudicacion"),
        **({"desde": fechas[0].isoformat(), "hasta": fechas[-1].isoformat()} if fechas else {}),
    }


def _orden_en_el_consejo(cargo: str) -> int:
    c = cargo.lower()
    if c.startswith("presidente") or c.startswith("presidenta"):
        return 0
    if c.startswith("vicepresident"):
        return 1
    if "delegad" in c:
        return 2
    return 3


def cruzar_consejo(
    cotizadas: dict[str, dict[str, Any]],
    personas: list[dict[str, Any]],
    en_empresas: dict[str, list[dict[str, Any]]],
    declarantes: dict[str, list[dict[str, Any]]],
) -> int:
    """Une a un consejero de la CNMV con un cargo público, con dos señales.

    La primera es el nombre, normalizado igual en los dos lados (`_plano`). No
    basta: dos personas se llaman igual. La segunda es que ese cargo público
    ya esté unido a ESA MISMA sociedad por su propia fuente: una autorización
    de la Oficina de Conflictos de Intereses para trabajar en ella, o una
    actividad que declaró al Congreso. Sólo con las dos se pone
    `cargoPublico` en el consejero, con el porqué en `cruce`; la web entonces
    los presenta como una sola persona. Con el nombre solo, no: se ven como
    dos nodos unidos a la misma sociedad, que es lo que dicen las fuentes.

    Una filial no es la sociedad: una autorización para el consejo de «MAPFRE
    GLOBAL RISKS» no une con el consejo de MAPFRE, S.A. Devuelve cuántos unió.
    """
    por_nombre: dict[str, list[str]] = {}
    for p in personas:
        por_nombre.setdefault(_plano(p["nombre"]), []).append(p["clave"])
    unidos = 0
    for clave_sociedad, c in cotizadas.items():
        autorizados = {a["persona"] for a in en_empresas.get(clave_sociedad, [])}
        declarados = {a["persona"] for a in declarantes.get(clave_sociedad, [])}
        for m in c.get("consejo", []):
            if not m.get("persona"):
                continue
            candidatos = [
                (clave, "nombre y autorización de la OCI para esta misma sociedad")
                for clave in por_nombre.get(_plano(m["nombre"]), [])
                if clave in autorizados
            ] + [
                (clave, "nombre y actividad declarada al Congreso en esta misma sociedad")
                for clave in por_nombre.get(_plano(m["nombre"]), [])
                if clave in declarados and clave not in autorizados
            ]
            # Dos cargos públicos que casan: no se elige.
            if len({clave for clave, _ in candidatos}) == 1:
                m["cargoPublico"], m["cruce"] = candidatos[0]
                unidos += 1
    return unidos


def participaciones_cnmv(store: Store) -> dict[str, dict[str, Any]]:
    """Las cotizadas, sus accionistas significativos y su consejo, según la CNMV.

    Por la clave de la cotizada (`nif:…` si está en la lista, o la de la
    CNMV). Una persona física sólo sale si pasa SU puerta: la clave
    `cnmv:persona:`, la marca de la CNMV (`accionista_cnmv` o
    `consejero_cnmv`) y la arista con procedencia de la CNMV. En su papel de
    accionista significativo o de consejero y en ningún otro (spec §12,
    ampliación del 26/9/2026): no entra en `personas`, ni en el grafo, ni se
    une a nadie de otra fuente.
    """
    filas = store.conn.execute(
        """
        SELECT es.dedupe_key AS clave_titular, es.caption AS titular,
               es.ftm_schema AS esquema_titular, es.properties AS props_titular,
               et.dedupe_key AS clave_cotizada, et.caption AS cotizada,
               COALESCE(et.nif, '') AS nif_cotizada, et.properties AS props_cotizada,
               r.properties, r.ftm_schema AS esquema
        FROM relationships r
        JOIN entities es ON es.id = r.source_entity_id AND es.canonical_id IS NULL
        JOIN entities et ON et.id = r.target_entity_id AND et.canonical_id IS NULL
        WHERE r.ftm_schema IN ('Ownership', 'Directorship')
          AND r.status <> 'retracted'
          AND EXISTS (
              SELECT 1 FROM provenance pv
              JOIN raw_documents rd ON rd.id = pv.raw_document_id
              WHERE pv.relationship_id = r.id AND rd.source_id = 'cnmv'
          )
        """
    ).fetchall()
    cotizadas: dict[str, dict[str, Any]] = {}
    descartadas = 0
    for f in filas:
        props = f["properties"] or {}
        persona = f["esquema_titular"] == "Person"
        marcas = f["props_titular"] or {}
        if persona and not (
            f["clave_titular"].startswith("cnmv:persona:")
            and (marcas.get("accionista_cnmv") is True or marcas.get("consejero_cnmv") is True)
        ):
            descartadas += 1
            continue
        sector = (f["props_cotizada"] or {}).get("sectorCNMV") or ""
        c = cotizadas.setdefault(
            f["clave_cotizada"],
            {
                "clave": f["clave_cotizada"],
                "nombre": f["cotizada"],
                **({"nif": f["nif_cotizada"]} if f["nif_cotizada"] else {}),
                # El sector es el que le da la CNMV en su ficha; «medio» sale
                # de ese sector, no de una lista nuestra.
                **({"sector": sector} if sector else {}),
                # El nombre corto que le da la CNMV en su ficha: PRISA, BBVA…
                **(
                    {"abreviada": (f["props_cotizada"] or {})["alias"]}
                    if (f["props_cotizada"] or {}).get("alias")
                    else {}
                ),
                **({"medio": True} if es_medio_de_comunicacion(sector) else {}),
                "url": props.get("url", "") if f["esquema"] == "Ownership" else "",
                "accionistas": [],
                "consejo": [],
            },
        )
        if f["esquema"] == "Directorship":
            c["consejo"].append(
                {
                    "clave": f["clave_titular"],
                    "nombre": f["titular"],
                    **({"persona": True} if persona else {}),
                    **{
                        k: props[k]
                        for k in ("cargo", "categoria", "ejercicio", "url", "representa")
                        if props.get(k)
                    },
                }
            )
            continue
        if not c["url"] and props.get("url"):
            c["url"] = props["url"]
        c["accionistas"].append(
            {
                "clave": f["clave_titular"],
                "nombre": f["titular"],
                **({"persona": True} if persona else {}),
                **{
                    k: props[k]
                    for k in ("porcentaje", "porAcciones", "porInstrumentos", "fechaRegistroCNMV")
                    if props.get(k)
                },
            }
        )
    for c in cotizadas.values():
        c["accionistas"].sort(key=lambda a: -float(a.get("porcentaje") or 0))
        # El dominical, unido al accionista que representa sólo si ese
        # accionista está registrado en ESTA cotizada con el mismo nombre
        # (misma fuente, misma sociedad). Si no, se queda el texto.
        for m in c["consejo"]:
            if not m.get("representa"):
                continue
            for a in c["accionistas"]:
                if mismo_titular(m["representa"], a["nombre"]):
                    m["representaClave"] = a["clave"]
                    break
        # La presidencia primero, luego las vicepresidencias; el resto, por nombre.
        c["consejo"].sort(key=lambda m: (_orden_en_el_consejo(m.get("cargo", "")), m["nombre"]))
        for vacia in ("url", "consejo"):
            if not c[vacia]:
                c.pop(vacia)
    if descartadas:
        log.error("cnmv: accionistas personas sin su marca; no salen", descartadas=descartadas)
    return cotizadas


def exportar_cargos(store: Store, destino: Path) -> dict[str, Any]:
    """Escribe `destino` con las personas que pasan las condiciones de §12."""
    filas = _filas_de_la_puerta(store, "Occupancy")

    personas: dict[str, dict[str, Any]] = {}
    actos: dict[str, list[dict[str, Any]]] = {}
    para_cruzar: dict[str, str] = {}
    biografias: dict[str, set[str]] = {}
    descartadas = 0
    for f in filas:
        # La condición del DNI en Python, con la misma función que usa el
        # grafo: así no hay dos definiciones de «identificador personal».
        if es_identificador_personal(f["nif"]):
            descartadas += 1
            continue
        props = f["properties"] or {}
        tipo = props.get("acto")
        fecha = f["end_date"] if tipo == "cese" else f["start_date"]
        if tipo not in {"nombramiento", "cese", "mandato"} or fecha is None:
            continue
        clave = f["dedupe_key"]
        fuente = next(v for k, v in PUERTAS.items() if clave.startswith(k))
        nombre = f["caption"] if fuente == "boe" else nombre_natural(f["caption"])
        personas.setdefault(clave, {"clave": clave, "nombre": nombre})
        if fuente in {"oci", "congreso"}:
            # Otra vez por `_plano`, el mismo que el lado del BOE: el del
            # conector deja el guion y éste lo junta, y «Pérez-Castejón» no
            # casaba con «Pérez-Castejón». Pedro Sánchez no se unía a su escaño.
            para_cruzar[clave] = _plano((f["props_persona"] or {}).get("nombreParaCruzar", ""))
        if fuente == "congreso":
            # Lo que dicen las biografías de TODAS sus legislaturas: la de la
            # persona (la última leída) y la de cada mandato.
            menciones = (f["props_persona"] or {}).get("cargosEnBiografia", []) + props.get(
                "cargosEnBiografia", []
            )
            biografias.setdefault(clave, set()).update(_plano(m) for m in menciones)
        actos.setdefault(clave, []).append(
            {
                "tipo": tipo,
                "fecha": fecha,
                "puesto": f["destino"],
                "cargo": props.get("cargo") or f["destino"],
                "organismo": props.get("departamento") or "",
                "boe": props.get("boe") or "",
                "url": props.get("url") or "",
                "motivo": props.get("motivo") or "",
                "fuente": fuente,
                **({"ambito": props["ambito"]} if props.get("ambito") else {}),
                **({"propuesta": props["propuestaDe"]} if props.get("propuestaDe") else {}),
                **({"hasta": f["end_date"]} if tipo == "mandato" and f["end_date"] else {}),
                **{k: props[k] for k in ("formacion", "grupo", "circunscripcion") if props.get(k)},
            }
        )
    if descartadas:
        log.error(
            "cargos: fichas con identificador personal; no vienen de donde dicen",
            descartadas=descartadas,
        )

    # Las autorizaciones de actividad privada tras el cese.
    autorizaciones: dict[str, list[dict[str, Any]]] = {}
    for f in _filas_de_la_puerta(
        store, "UnknownLink", "AND (r.properties ->> 'relacion') = 'autorizacion_actividad_privada'"
    ):
        if f["dedupe_key"] not in personas:
            continue
        props = f["properties"] or {}
        autorizaciones.setdefault(f["dedupe_key"], []).append(
            {
                "actividad": props.get("actividad") or f["destino"],
                **({"fecha": f["start_date"]} if f["start_date"] else {}),
                "cargoAnterior": props.get("cargoAnterior", ""),
                **({"fechaCese": props["fechaCese"]} if props.get("fechaCese") else {}),
                "url": props.get("url", ""),
            }
        )

    # Las actividades que declaró cada diputado al Congreso.
    declaraciones: dict[str, list[dict[str, Any]]] = {}
    for f in _filas_de_la_puerta(
        store, "UnknownLink", "AND (r.properties ->> 'relacion') = 'actividad_declarada'"
    ):
        if f["dedupe_key"] not in personas:
            continue
        props = f["properties"] or {}
        declaraciones.setdefault(f["dedupe_key"], []).append(
            {k: props[k] for k in _CAMPOS_DECLARACION if props.get(k)}
        )

    # La misma persona en las dos fuentes: nombre entero y fecha de cese a la
    # vez. Una sola de las dos señales no basta —con dos apellidos los
    # homónimos son menos, no ninguno (§12)—; las dos juntas sí.
    boe_por_nombre: dict[str, list[str]] = {}
    for clave, persona in personas.items():
        if clave.startswith("boe:"):
            boe_por_nombre.setdefault(_plano(persona["nombre"]), []).append(clave)
    unida_a: dict[str, str] = {}
    for clave_otra, nombre in para_cruzar.items():
        candidatas = boe_por_nombre.get(nombre, [])
        if len(candidatas) != 1:
            continue
        del_boe = actos[candidatas[0]]
        if clave_otra.startswith("oci:"):
            ceses_oci = [a["fecha"] for a in actos[clave_otra] if a["tipo"] == "cese"]
            ceses_boe = [a["fecha"] for a in del_boe if a["tipo"] == "cese"]
            if any(abs((a - b).days) <= MARGEN_CESE for a in ceses_oci for b in ceses_boe):
                unida_a[clave_otra] = candidatas[0]
        else:
            # Congreso: el nombre entero y, además, que su biografía en el
            # Congreso mencione uno de sus cargos del BOE. La segunda señal la
            # da la propia fuente.
            cargos_boe = {_plano(a["cargo"]) for a in del_boe} | {
                _plano(a["puesto"]) for a in del_boe
            }
            cargos_boe = {c for c in cargos_boe if len(c.split()) >= 3}
            if any(c in m for c in cargos_boe for m in biografias.get(clave_otra, [])):
                unida_a[clave_otra] = candidatas[0]

    organos = organos_del_estado(store)
    empresas_mapa = empresas_por_nombre(store) if autorizaciones or declaraciones else {}
    # Y al revés: de cada órgano, quién lo dirigió; de cada sociedad, qué ex
    # altos cargos fueron autorizados a trabajar en ella y qué diputados
    # declararon haber trabajado en ella.
    al_frente: dict[str, list[dict[str, Any]]] = {}
    en_empresas: dict[str, list[dict[str, Any]]] = {}
    declarantes: dict[str, list[dict[str, Any]]] = {}
    formacion_de: dict[str, str] = {}
    dinero_cache: dict[tuple[str, str], dict[str, Any] | None] = {}

    salida = []
    for clave, persona in personas.items():
        if clave in unida_a:
            continue
        # Un diputado que no se une a ningún alto cargo sale sólo si declaró
        # actividades: de quien sólo consta el escaño no hay nada que cruzar.
        if clave.startswith("congreso:") and not declaraciones.get(clave):
            continue
        propios_actos = list(actos[clave])
        for c, b in unida_a.items():
            if b == clave and c.startswith("congreso:"):
                propios_actos += [
                    {**a, "cruce": "nombre y cargo en su biografía del Congreso"} for a in actos[c]
                ]
        ps = periodos(propios_actos)
        for p in ps:
            # El cargo de la OCI viene abreviado y en mayúsculas; el del BOE,
            # como se escribe. Un escaño del Congreso no dirige nada.
            if p.get("fuente") == "oci":
                puesto_p = puesto_de_la_oci(p["puesto"])
            elif p.get("fuente") == "congreso":
                puesto_p = ""
            else:
                puesto_p = p["puesto"]
            organo = organo_de(puesto_p, organos) if puesto_p else None
            if organo is None:
                continue
            p["organo"] = organo
            al_frente.setdefault(organo["clave"], []).append(
                _serializable(
                    {
                        "persona": clave,
                        "nombre": persona["nombre"],
                        "cargo": p["cargo"],
                        **{k: p[k] for k in ("desde", "hasta") if k in p},
                        **_fuente_no_boe(p),
                    }
                )
            )
        propias = list(autorizaciones.get(clave, []))
        cruces = [c for c, b in unida_a.items() if b == clave]
        for c in cruces:
            propias += [{**a, "cruce": "nombre y fecha de cese"} for a in autorizaciones.get(c, [])]
        # Y la pregunta de las puertas giratorias, con dos hechos documentados
        # uno al lado del otro: el órgano que la persona dirigió, ¿pagó a la
        # sociedad en la que se le autorizó a trabajar? Sólo con los dos
        # enlaces estrictos —el órgano por su nombre exacto, la sociedad por su
        # denominación completa—; ninguno de los dos dice nada del otro.
        con_organo = [p for p in ps if p.get("organo")]
        for a in propias:
            empresa = empresa_en(a["actividad"], empresas_mapa)
            if empresa is None:
                continue
            a["empresa"] = empresa
            for p in con_organo:
                par = (p["organo"]["clave"], empresa["clave"])
                if par not in dinero_cache:
                    dinero_cache[par] = dinero_del_organo(store, *par)
                if dinero_cache[par]:
                    a.setdefault("delOrgano", []).append(
                        {"organo": p["organo"], "cargo": p["cargo"], **dinero_cache[par]}
                    )
            en_empresas.setdefault(empresa["clave"], []).append(
                _serializable(
                    {
                        "persona": clave,
                        "nombre": persona["nombre"],
                        "actividad": a["actividad"],
                        "cargoAnterior": a.get("cargoAnterior", ""),
                        **({"fecha": a["fecha"]} if a.get("fecha") else {}),
                        # Para el panel de la sociedad: si el órgano que
                        # dirigía le pagó, se dice allí también.
                        **({"delOrgano": a["delOrgano"]} if a.get("delOrgano") else {}),
                    }
                )
            )
        propias.sort(key=lambda a: a.get("fecha") or date.min, reverse=True)
        declaradas = list(declaraciones.get(clave, []))
        for c in cruces:
            if c.startswith("congreso:"):
                declaradas += [
                    {**d, "cruce": "nombre y cargo en su biografía del Congreso"}
                    for d in declaraciones.get(c, [])
                ]
        # La formación con la que fue elegido, para decirla junto al nombre
        # donde la persona sale fuera de su ficha. La del último mandato.
        mandatos = sorted(
            (p for p in ps if p.get("fuente") == "congreso" and p.get("formacion")),
            key=lambda p: p["desde"],
        )
        formacion = mandatos[-1]["formacion"] if mandatos else ""
        formacion_de[clave] = formacion
        for d in declaradas:
            empresa = empresa_en(d.get("empleador", ""), empresas_mapa)
            if empresa is None:
                continue
            d["empresa"] = empresa
            # Una persona, una vez por sociedad: quien declaró tres etapas en
            # la misma universidad es un declarante, no tres.
            if any(x["persona"] == clave for x in declarantes.get(empresa["clave"], [])):
                continue
            declarantes.setdefault(empresa["clave"], []).append(
                {
                    "persona": clave,
                    "nombre": persona["nombre"],
                    **({"formacion": formacion} if formacion else {}),
                    **{k: d[k] for k in ("empleador", "descripcion", "periodo") if d.get(k)},
                }
            )
        salida.append(
            {
                **persona,
                "periodos": [_serializable(p) for p in ps],
                **({"autorizaciones": [_serializable(a) for a in propias]} if propias else {}),
                **({"declaraciones": declaradas} if declaradas else {}),
            }
        )
    for lista in (*al_frente.values(), *en_empresas.values()):
        lista.sort(
            key=lambda x: x.get("hasta") or x.get("desde") or x.get("fecha") or "", reverse=True
        )

    for lista in declarantes.values():
        lista.sort(key=lambda x: x["nombre"])

    def ultima(p: dict[str, Any]) -> str:
        fechas_p = [x.get("hasta") or x.get("desde") or "" for x in p["periodos"]]
        fechas_p += [a.get("fecha", "") for a in p.get("autorizaciones", [])]
        return max(fechas_p or [""])

    salida.sort(key=lambda p: (ultima(p), p["nombre"]), reverse=True)

    # Línea 4: bajo qué Gobierno se nombró cada alto cargo. Es la fecha del
    # Real Decreto contra las presidencias leídas, nada más: dice quién
    # gobernaba, no a qué partido pertenece la persona nombrada.
    presidencias = presidencias_del_gobierno(salida)
    autonomicas = presidencias_autonomicas(salida)
    puente = partidos_por_siglas(store)
    formaciones = {
        f: puente[_plano(f)]
        for f in sorted(
            {
                p["formacion"]
                for persona in salida
                for p in persona["periodos"]
                if p.get("fuente") == "congreso" and p.get("formacion")
            }
        )
        if _plano(f) in puente
    }
    for persona in salida:
        for p in persona["periodos"]:
            if p.get("fuente") or p.get("puesto") == PRESIDENCIA or not p.get("desde"):
                continue
            # A un presidente autonómico lo elige el parlamento de su
            # comunidad; el Real Decreto lo firma el Rey con el refrendo del
            # presidente del Gobierno, pero decir «nombramiento con el Gobierno
            # de …» leería al revés.
            if comunidad_de_la_presidencia(p.get("puesto", "")):
                continue
            # Ni a un magistrado del Supremo o del Constitucional, ni a un
            # fiscal de sala: los propone el CGPJ, las Cortes o el propio
            # Tribunal, y el Real Decreto sólo lo formaliza. Salvo que el
            # Real Decreto diga que la propuesta es del Gobierno: entonces sí
            # es un nombramiento con el Gobierno de entonces.
            if p.get("ambito") == "justicia" and p.get("propuesta") != "Gobierno":
                continue
            gobierno = gobierno_en(presidencias, p["desde"])
            if gobierno is not None:
                p["gobierno"] = gobierno
        # Y la autorización, el Gobierno que nombró a la persona en el cargo
        # que dejaba: el periodo del BOE cuyo cese casa con el que da la OCI.
        for a in persona.get("autorizaciones", []):
            if not a.get("fechaCese"):
                continue
            cese = date.fromisoformat(a["fechaCese"])
            for p in persona["periodos"]:
                if not p.get("gobierno") or not p.get("hasta"):
                    continue
                if abs((date.fromisoformat(p["hasta"]) - cese).days) <= MARGEN_CESE:
                    a["gobierno"] = p["gobierno"]
                    break

    # Los actos del BOE, y sólo ésos: «nombradas o cesadas por Real Decreto
    # entre el … y el …» no puede contar un cese que sólo da la Oficina de
    # Conflictos de Intereses, ni el alta de un diputado en 2008.
    fechas = [
        a["fecha"] for clave, lista in actos.items() if clave.startswith("boe:") for a in lista
    ]
    cotizadas = participaciones_cnmv(store)
    consejeros_cruzados = cruzar_consejo(cotizadas, salida, en_empresas, declarantes)
    documento = {
        "generado": datetime.now(UTC).isoformat(),
        "fuente": "Boletín Oficial del Estado",
        # Lo que se ha leído, no lo que existe: un nombramiento anterior a
        # `desde` no está, y la web lo tiene que poder decir.
        "actosDesde": min(fechas).isoformat() if fechas else None,
        "actosHasta": max(fechas).isoformat() if fechas else None,
        "nActos": len(fechas),
        "nAutorizaciones": sum(len(v) for v in autorizaciones.values()),
        "nDeclaraciones": sum(len(p.get("declaraciones", [])) for p in salida),
        "personas": salida,
        "presidencias": presidencias,
        "presidenciasAutonomicas": autonomicas,
        # Cada formación de los diputados que salen, con su nombre oficial y
        # su ficha en el mapa del dinero, si el puente del Senado la da.
        "formaciones": formaciones,
        "organos": al_frente,
        "empresas": en_empresas,
        "declarantes": declarantes,
        # Las cotizadas y sus accionistas significativos, según la CNMV.
        "cotizadas": cotizadas,
    }
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(documento, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    por_fuente = {
        fuente: sum(1 for c in personas if c.startswith(prefijo))
        for prefijo, fuente in PUERTAS.items()
    }
    # Los cruces del cargo a la empresa, para la portada: cada autorización
    # que nombra una sociedad del mapa del dinero. Van en el grafo, que la
    # portada ya tiene, para no hacerle descargar todos los cargos.
    cruces = sorted(
        (
            {
                "persona": p["clave"],
                "nombre": p["nombre"],
                "cargoAnterior": a.get("cargoAnterior", ""),
                "actividad": a["actividad"],
                "empresa": a["empresa"],
                **({"fecha": a["fecha"]} if a.get("fecha") else {}),
                **({"gobierno": a["gobierno"]} if a.get("gobierno") else {}),
                **({"delOrgano": a["delOrgano"]} if a.get("delOrgano") else {}),
            }
            for p in salida
            for a in p.get("autorizaciones", [])
            if a.get("empresa")
        ),
        key=lambda c: c.get("fecha", ""),
        reverse=True,
    )
    # Y de lo declarado al Congreso: cada sociedad mercantil del mapa que
    # nombra una actividad, una vez por persona. Por nombre, no por dinero: no
    # es una lista de sospechosos.
    declarados: list[dict[str, Any]] = []
    vistos: set[tuple[str, str]] = set()
    for p in salida:
        for d in p.get("declaraciones", []):
            empresa = d.get("empresa")
            if not empresa or not es_sociedad_mercantil(empresa["nombre"]):
                continue
            if (p["clave"], empresa["clave"]) in vistos:
                continue
            vistos.add((p["clave"], empresa["clave"]))
            declarados.append(
                {
                    "persona": p["clave"],
                    "nombre": p["nombre"],
                    **{k: d[k] for k in ("empleador", "descripcion", "periodo") if d.get(k)},
                    "empresa": empresa,
                    **(
                        {"formacion": formacion_de[p["clave"]]}
                        if formacion_de.get(p["clave"])
                        else {}
                    ),
                }
            )
    declarados.sort(key=lambda c: (c["empresa"]["nombre"], c["nombre"]))
    resumen = {
        "cargos_personas": len(salida),
        "cargos_actos": len(fechas),
        "cargos_organos": len(al_frente),
        # El Senado no aporta personas sino el puente de las siglas: cuenta lo
        # que dio, para que la web no lo anuncie como caído el día que respondió.
        # Y la CNMV, las participaciones: si respondió, no está caída.
        "cargos_por_fuente": {
            **por_fuente,
            "senado": len(puente),
            "cnmv": sum(len(c["accionistas"]) for c in cotizadas.values()),
        },
        "cotizadas": len(cotizadas),
        # Las que la CNMV clasifica como medios de comunicación.
        "medios": sum(1 for c in cotizadas.values() if c.get("medio")),
        # Personas con algún cargo de alta instancia judicial o fiscal.
        # Consejeros de la CNMV unidos a un cargo público con dos señales.
        "consejeros_cruzados": consejeros_cruzados,
        "altas_instancias": sum(
            1 for p in salida if any(x.get("ambito") == "justicia" for x in p["periodos"])
        ),
        "cruces": cruces[:MAX_CRUCES_EN_PORTADA],
        "n_cruces": len(cruces),
        "declarados": declarados[:MAX_CRUCES_EN_PORTADA],
        # Pocas —una por comunidad y legislatura— y la portada de cada
        # comunidad las enseña sin tener que descargar todos los cargos.
        "presidencias_autonomicas": autonomicas,
        "n_declarados": len(declarados),
    }
    log.info(
        "cargos exportados",
        destino=str(destino),
        **{
            k: v
            for k, v in resumen.items()
            if k not in {"cruces", "declarados", "presidencias_autonomicas"}
        },
    )
    return resumen
