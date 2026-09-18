"""Exporta el grafo a JSON estático.

Sirve para publicar sin base de datos: GitHub Actions ingiere contra un
Postgres efímero, exporta aquí, y el fichero resultante se sirve como un
activo más desde Vercel.

Tiene un límite claro y conviene decirlo: es una **instantánea**, no una
consulta viva. No escala a millones de aristas ni permite buscar en el
servidor. Para eso está la API (`backend/` o `api/`). Pero para publicar un
primer mapa real sin depender de nadie, es suficiente.

Lo que NO cambia: cada arista sigue llevando su `confidence` y su `status`, y
cada entidad su procedencia. Un formato más ligero no es excusa para perder lo
que hace auditable el proyecto.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import structlog

from sinapsis_ingest.store import Store
from sinapsis_ingest.util import es_identificador_personal

log = structlog.get_logger()

# El esquema FtM de una persona física. Nunca se publica: ver §12 de la spec.
PERSONALES = "Person"

# Cota del volcado. Por encima de esto el navegador sufre y la vista deja de
# ser útil: si hace falta más, lo que hace falta es la API, no un JSON mayor.
MAX_ENTIDADES = 4000

# El presupuesto que de verdad manda: se eligen aristas y los nodos salen de
# sus extremos. Ver el docstring de `exportar`.
MAX_ARISTAS = 6000


# Lo que sustituye a un nombre de persona hallado dentro de un texto. Se marca
# en vez de borrarse: el hueco tiene que verse, porque una descripción a la que
# le falta una palabra sin avisar es otra forma de mentir.
MARCA_NOMBRE_RETIRADO = "(nombre retirado)"

_ESPACIO = re.compile(r"\s")

# Un nombre de una sola palabra no se busca dentro de un texto, y no por
# pereza: el riesgo se invierte. Un apellido corriente aparece en topónimos, en
# razones sociales y en descripciones de obra —«taller de Sant Genís», «calle
# Adell»— y taparlo destrozaría el texto sin proteger a nadie que no estuviera
# ya protegido por la retirada de su ficha.
MIN_PALABRAS_NOMBRE = 2
MIN_LETRAS_NOMBRE = 6

# Partículas que van en minúscula dentro de un nombre propio perfectamente
# normal. Sin esta lista, «Juan de la Cruz» no parecería un nombre.
_PARTICULAS = frozenset(
    [
        "de",
        "del",
        "la",
        "las",
        "el",
        "los",
        "y",
        "e",
        "i",
        "da",
        "das",
        "do",
        "dos",
        "van",
        "von",
        "der",
        "den",
        "bin",
        "ben",
    ]
)


def _parece_nombre_de_persona(nombre: str) -> bool:
    """¿Esta cadena es lo bastante nombre como para buscarla dentro de un texto?

    El filtro que importa no es la longitud sino las mayúsculas. Las fuentes
    traen basura en el campo del nombre —la instantánea tenía una ficha de
    persona cuyo «nombre» era una frase corriente en minúscula—, y buscar esa
    frase con `IGNORECASE` dentro de todas las descripciones publicadas taparía
    prosa legítima a puñados sin proteger a nadie.

    Así que se exige lo que sí distingue a un nombre: que todas sus palabras
    empiecen por mayúscula, salvo las partículas.
    """
    palabras = nombre.split()
    if len(palabras) < MIN_PALABRAS_NOMBRE:
        return False
    if sum(len(p) for p in palabras) < MIN_LETRAS_NOMBRE:
        return False
    propias = 0
    for palabra in palabras:
        if palabra.lower().strip(".,;:()") in _PARTICULAS:
            continue
        letra = palabra.lstrip("'\u2019(«\"")[:1]
        if not letra.isalpha() or not letra.isupper():
            return False
        propias += 1
    return propias >= MIN_PALABRAS_NOMBRE


# La misma prueba que `es_identificador_personal`, escrita para Postgres.
# Va en SQL porque la lista de nombres se saca de TODA la base —decenas de
# miles de filas— y no sólo del trozo que se publica: traérselas a Python para
# descartarlas aquí sería pasear la base entera por la red en cada volcado.
# Hay un test que compara las dos contra los mismos casos; si alguien cambia
# una y no la otra, salta.
_SQL_IDENTIFICADOR_PERSONAL = r"^([0-9]{8}|[XYZxyz][0-9]{7})[A-Za-z]$"


def nombres_de_persona(store: Store) -> list[str]:
    """Los nombres que no pueden aparecer en NINGÚN texto publicado.

    Retirar la ficha de una persona física no basta. Los pliegos la nombran en
    prosa: «el contracte per al projecte de creació "Veus de Parets" de <nombre>»
    salió publicado en la descripción de un expediente durante semanas, con la
    ficha de esa persona correctamente omitida del mapa. La regla de §12 miraba
    las entidades y no el texto que las rodea.

    Se buscan en toda la base, no sólo entre lo que se publica: la persona
    puede no caber en el mapa y estar nombrada igualmente en la descripción de
    un contrato que sí cabe.
    """
    filas = store.conn.execute(
        """
        SELECT DISTINCT caption
        FROM entities
        WHERE canonical_id IS NULL
          AND caption IS NOT NULL AND caption <> ''
          AND (ftm_schema = %s OR COALESCE(nif,'') ~ %s)
        """,
        (PERSONALES, _SQL_IDENTIFICADOR_PERSONAL),
    ).fetchall()
    return [f["caption"].strip() for f in filas if f["caption"].strip()]


def censor(nombres: Iterable[str]) -> re.Pattern[str] | None:
    """Compila el patrón que tapa esos nombres, o `None` si no hay ninguno."""
    piezas = []
    for nombre in sorted(set(nombres), key=len, reverse=True):
        if not _parece_nombre_de_persona(nombre):
            continue
        palabras = nombre.split()
        # `\s+` y no un espacio literal. El mismo nombre viene partido por un
        # salto de línea en cuanto el texto es un pliego copiado tal cual, y un
        # patrón que exige el espacio encuentra CERO ocurrencias donde hay una.
        # No es hipotético: costó seis intentos en el guion que limpia el
        # historial, porque el borrado y su comprobación compartían el fallo.
        piezas.append(r"\s+".join(re.escape(p) for p in palabras))
    if not piezas:
        return None
    # Sin `\b`: un nombre puede empezar o acabar en apóstrofo o guion, y ahí
    # `\b` se comporta al revés de lo que parece.
    return re.compile(r"(?<!\w)(?:" + "|".join(piezas) + r")(?!\w)", re.IGNORECASE)


def tapar_nombres(valor: Any, patron: re.Pattern[str], cuenta: list[int]) -> Any:
    """Sustituye los nombres en cualquier cadena que cuelgue de `valor`.

    Recorre diccionarios y listas porque las propiedades de un nodo son un
    JSON arbitrario que viene de la fuente: acotar la búsqueda a las claves que
    hoy existen sería dejar abierta la siguiente.
    """
    if isinstance(valor, str):
        # Un nombre lleva al menos dos palabras, así que una cadena sin un solo
        # espacio no puede contener ninguno. El volcado son 3,4 millones de
        # caracteres repartidos en 113.000 cadenas, y la inmensa mayoría son
        # UUID, fechas, hashes y códigos: descartarlos con una prueba de una
        # línea deja el recorrido en una fracción de lo que costaba.
        if not _ESPACIO.search(valor):
            return valor
        nuevo, n = patron.subn(MARCA_NOMBRE_RETIRADO, valor)
        cuenta[0] += n
        return nuevo
    if isinstance(valor, dict):
        return {k: tapar_nombres(v, patron, cuenta) for k, v in valor.items()}
    if isinstance(valor, list):
        return [tapar_nombres(v, patron, cuenta) for v in valor]
    return valor


def exportar(
    store: Store,
    destino: Path,
    max_entidades: int = MAX_ENTIDADES,
    max_aristas: int = MAX_ARISTAS,
) -> dict[str, Any]:
    """Escribe el grafo en `destino`. Devuelve el resumen de lo exportado.

    Se eligen **aristas primero**, y los nodos salen de sus extremos.

    Antes era al revés: se cogían las N entidades de mayor grado y luego sólo
    las aristas con los dos extremos dentro. Suena razonable y destroza el
    grafo. Un nodo muy conectado entra, pero sus vecinos de grado 1 se quedan
    fuera del corte, así que sus aristas se caen y el nodo acaba suelto. El
    resultado medido sobre la instantánea del 3/8/2026: 4.000 nodos, 4.351
    aristas, **1.393 componentes conexas** y 548 nodos aislados *entre los más
    conectados de la base*. Un mapa de influencia troceado en 1.393 pedazos no
    enseña ninguna influencia.

    Eligiendo aristas primero eso no puede pasar: cada nodo publicado tiene al
    menos una arista y ninguna arista queda colgando. Se ordenan por importe
    porque el dinero es de lo que va esto; las que no lo llevan van después,
    por grado de sus extremos, para no perder el tejido que une los núcleos.
    """
    # La selección crece POR EL GRAFO, no sólo por dinero. Tres pasadas.
    #
    # Sólo por importe no funciona, y costó dos intentos verlo. El enlace del
    # órgano de contratación con su contrato no lleva importe a propósito —el
    # dinero lo lleva la adjudicación y duplicarlo lo contaría dos veces—, así
    # que ordenando por importe ese enlace nunca entra. Y peor: el órgano de
    # PLACSP no tiene NINGUNA arista con dinero, sólo ese enlace, de modo que
    # tampoco entra él. Quedaban 129 organismos frente a 1.646 contratos, y el
    # grafo llegaba en 1.274 pedazos aunque ningún nodo estuviera aislado.
    #
    # Pedir que los dos extremos estuvieran ya dentro tampoco valía: es
    # circular, porque el órgano sólo puede entrar por esa misma arista.
    todas = store.conn.execute(
        """
        SELECT r.id, r.ftm_schema, r.source_entity_id, r.target_entity_id,
               r.amount, r.currency, r.confidence, r.status,
               r.start_date, r.end_date, r.properties
        FROM relationships r
        JOIN entities es ON es.id = r.source_entity_id AND es.canonical_id IS NULL
        JOIN entities et ON et.id = r.target_entity_id AND et.canonical_id IS NULL
        WHERE r.status <> 'retracted'
        ORDER BY r.amount DESC NULLS LAST, r.id
        """
    ).fetchall()

    elegidas: list[Any] = []
    ids_set: set[Any] = set()
    usadas: set[Any] = set()

    # Una adjudicación y el enlace de su órgano viajan JUNTOS.
    #
    # Entre el organismo y la empresa siempre hay un expediente, y la arista
    # que lo cuelga de su órgano no lleva importe. Como todo se recorre por
    # importe descendente, esas aristas van las últimas: cuando les llega el
    # turno el cupo de nodos está agotado y el órgano ya no entra.
    #
    # El resultado no es "un poco menos de detalle". El 18/9/2026, al doblarse
    # los datos ingeridos, 1.070 de los 1.368 expedientes publicados salieron
    # SIN órgano: un nodo colgando que dice que alguien adjudicó algo sin decir
    # quién. El grafo pasó de 354 a 601 pedazos y la componente mayor se quedó
    # en la mitad.
    #
    # Un expediente sin su órgano no es medio dato, es ninguno. Así que el
    # triple (órgano, expediente, adjudicatario) se reserva entero o no se
    # reserva: cuesta un nodo más la primera vez y los órganos se comparten
    # entre sus contratos, así que el precio real es pequeño.
    expedientes = {
        f["id"]
        for f in store.conn.execute(
            "SELECT id FROM entities WHERE canonical_id IS NULL AND ftm_schema = 'Contract'"
        ).fetchall()
    }
    enlace_organo: dict[Any, Any] = {}
    for a in todas:
        if a["ftm_schema"] == "UnknownLink" and a["target_entity_id"] in expedientes:
            enlace_organo.setdefault(a["target_entity_id"], a)

    def _con_organo(a: Any) -> tuple[set[Any], Any]:
        """Los nodos que hace falta reservar por esta arista, y el enlace extra."""
        ids = {a["source_entity_id"], a["target_entity_id"]}
        enlace = None
        if a["ftm_schema"] == "ContractAward":
            enlace = enlace_organo.get(a["source_entity_id"])
            if enlace is not None:
                ids |= {enlace["source_entity_id"], enlace["target_entity_id"]}
        return ids, enlace

    def cabe(a: Any, tope: int) -> bool:
        ids, _ = _con_organo(a)
        return len(ids_set | ids) <= tope

    def tomar(a: Any) -> None:
        ids, enlace = _con_organo(a)
        ids_set.update(ids)
        elegidas.append(a)
        usadas.add(a["id"])
        if enlace is not None and enlace["id"] not in usadas:
            elegidas.append(enlace)
            usadas.add(enlace["id"])

    # 0. Los partidos, antes que nada.
    #
    # Ordenar por importe los expulsa del mapa, y se comprobó: al coser bien el
    # grafo entraron 456 organismos y desaparecieron LOS 179 partidos. Una
    # subvención electoral es calderilla al lado de un contrato de
    # infraestructuras, así que compitiendo por dinero un partido nunca gana.
    #
    # En un mapa de financiación política eso no es una pérdida aceptable: es
    # perder el sujeto. El dinero ordena el resto; los partidos entran por
    # derecho propio.
    partidos = {
        f["id"]
        for f in store.conn.execute(
            """
            SELECT id FROM entities
            WHERE canonical_id IS NULL
              AND (properties ->> 'partido_politico') = 'true'
            """
        ).fetchall()
    }
    if partidos:
        for a in todas:
            if len(elegidas) >= max_aristas:
                break
            toca_partido = a["source_entity_id"] in partidos or a["target_entity_id"] in partidos
            if toca_partido and a["id"] not in usadas and cabe(a, max_entidades):
                tomar(a)

    # 1. El esqueleto de dinero: lo más caro primero. Es un mapa de dinero.
    #
    # Pero NO se gasta todo el presupuesto de nodos aquí, y esto es lo que
    # faltaba. Tres ejecuciones seguidas dieron números idénticos al byte pese
    # a dos correcciones: la prueba estaba en que el volcado traía exactamente
    # 4.000 nodos, o sea el tope clavado. La primera pasada lo agotaba con
    # extremos de aristas caras y luego `cabe()` rechazaba TODA arista que
    # trajera un nodo nuevo, así que la pasada 2 no podía traerse ni un
    # organismo. Reservar sitio no es un ajuste fino: sin él la pasada 2 no
    # existe.
    # El suelo de 2 no es cosmético: con un presupuesto pequeño, el 75 % puede
    # quedarse por debajo de los dos nodos que necesita UNA arista, y entonces
    # no entra nada en absoluto. Lo destapó el test del volcado mínimo.
    reserva = max(2, int(max_entidades * 0.75))
    for a in todas:
        if len(elegidas) >= max_aristas:
            break
        if a["id"] not in usadas and cabe(a, reserva):
            tomar(a)

    # 2. Crecer por los bordes: aristas que tocan algo ya elegido. Aquí entran
    #    los organismos, colgando del contrato que adjudicaron.
    for a in todas:
        if len(elegidas) >= max_aristas:
            break
        if a["id"] in usadas:
            continue
        toca = a["source_entity_id"] in ids_set or a["target_entity_id"] in ids_set
        if toca and cabe(a, max_entidades):
            tomar(a)

    # 3. Coser: lo que va entre nodos que ya están dentro es gratis —no trae
    #    ningún nodo nuevo— y es lo que convierte fragmentos en núcleos.
    for a in todas:
        if a["id"] in usadas:
            continue
        if a["source_entity_id"] in ids_set and a["target_entity_id"] in ids_set:
            elegidas.append(a)
            usadas.add(a["id"])

    ids = list(ids_set)
    aristas = [
        {
            "id": str(a["id"]),
            "schema": a["ftm_schema"],
            "source": str(a["source_entity_id"]),
            "target": str(a["target_entity_id"]),
            **({"amount": str(a["amount"])} if a["amount"] is not None else {}),
            **({"currency": a["currency"]} if a["currency"] else {}),
            # Nunca se omiten, ni aunque valgan lo esperable (invariante 5).
            "confidence": float(a["confidence"]),
            "status": a["status"],
            **({"start_date": a["start_date"].isoformat()} if a["start_date"] else {}),
            **({"end_date": a["end_date"].isoformat()} if a["end_date"] else {}),
            # Una arista sin importe puede serlo por dos motivos muy distintos:
            # porque la fuente no publicó cifra, o porque la ingesta no se creyó
            # la que publicó. La web tiene que poder decir cuál de los dos, y
            # para eso necesita las propiedades — ahí van `importeSinInterpretar`
            # y su motivo. Se omiten si están vacías para no engordar el volcado.
            **({"properties": a["properties"]} if a["properties"] else {}),
        }
        for a in elegidas
    ]

    filas = (
        store.conn.execute(
            """
        SELECT e.id, e.ftm_schema, e.caption, COALESCE(e.nif,'') AS nif,
               COALESCE(e.country,'') AS country, e.properties,
               (SELECT count(*) FROM relationships r
                 WHERE (r.source_entity_id = e.id OR r.target_entity_id = e.id)
                   AND r.status <> 'retracted') AS grado
        FROM entities e
        WHERE e.id = ANY(%s)
        ORDER BY grado DESC, e.caption
        """,
            (ids,),
        ).fetchall()
        if ids
        else []
    )

    # ÚLTIMA PUERTA ANTES DE PUBLICAR: aquí no pasa ninguna persona física.
    #
    # Los conectores ya agregan a los particulares en un nodo anónimo
    # («Personas físicas (convocatoria X)»), que es donde debe resolverse. Esta
    # comprobación es redundante a propósito, porque la redundancia es
    # exactamente lo que faltó: entre el 3 de agosto y el 18 de septiembre de
    # 2026 la corrección de los conectores existía y estaba probada, pero vivía
    # en una rama que no se desplegaba, y la instantánea diaria siguió
    # publicando nombres y apellidos con su DNI durante seis semanas sin que
    # fallara ni un test.
    #
    # Un conector nuevo, una fuente que cambie de formato o una regresión en
    # `parece_persona_fisica` vuelven a abrir esa puerta. Esta se cierra sola,
    # y se cierra en el sitio por el que pasa TODO lo que se publica.
    #
    # No se lanza excepción: se omite la entidad y se registra. Un volcado sin
    # una entidad es un hueco; un volcado con el DNI de un particular es una
    # infracción del RGPD que además no se puede retirar de internet.
    # Dos formas de ser una persona física aquí, y las dos salen.
    #
    # La obvia es el esquema. La otra la destapó el historial: una UTE
    # clasificada como `Company`, con forma societaria explícita y todo el
    # criterio bien aplicado, identificada con el DNI de uno de sus socios y
    # cuyo NOMBRE eran los nombres y apellidos de los dos. La regla de «esto es
    # una empresa» funcionaba y aun así se publicaban dos personas.
    #
    # Si la fuente identificó a esa parte contratante con un DNI o un NIE, es
    # una persona física a efectos de publicar. Se pierde alguna empresa real
    # cuyo NIF vino mal escrito, y es el lado correcto por el que equivocarse:
    # un falso positivo es una acusación falsa, un falso negativo es un hueco.
    personales = [f for f in filas if f["ftm_schema"] == PERSONALES]
    con_identificador = [
        f for f in filas if f["ftm_schema"] != PERSONALES and es_identificador_personal(f["nif"])
    ]
    if personales or con_identificador:
        log.error(
            "se han omitido personas físicas del volcado; revisa el conector que las creó",
            por_esquema=len(personales),
            por_identificador=len(con_identificador),
            ids=[str(f["id"]) for f in personales + con_identificador][:20],
        )
    omitidas = {f["id"] for f in personales + con_identificador}

    nodos = [
        {
            "id": str(f["id"]),
            "schema": f["ftm_schema"],
            "caption": f["caption"],
            **({"nif": f["nif"]} if f["nif"] else {}),
            **({"country": f["country"]} if f["country"] else {}),
            "properties": f["properties"] or {},
            "degree": int(f["grado"]),
        }
        for f in filas
        if f["id"] not in omitidas
    ]

    # Y sus aristas con ellas: una arista que cuelga de un nodo ausente rompe
    # el grafo, y además el par (organismo, importe) seguiría señalando a la
    # persona aunque su nombre no estuviera.
    if omitidas:
        aristas = [
            a
            for a in aristas
            if a["source"] not in {str(i) for i in omitidas}
            and a["target"] not in {str(i) for i in omitidas}
        ]
        ids = [i for i in ids if i not in omitidas]

    # Procedencia por entidad: es lo que permite volver al documento original
    # desde la interfaz, y sin ella el dato no debería publicarse.
    procedencia: dict[str, list[dict[str, Any]]] = {}
    if ids:
        for p in store.conn.execute(
            """
            SELECT p.entity_id, rd.source_id, rd.url, rd.content_hash,
                   rd.retrieved_at, p.extractor_version, COALESCE(p.excerpt,'') AS excerpt
            FROM provenance p
            JOIN raw_documents rd ON rd.id = p.raw_document_id
            WHERE p.entity_id = ANY(%s)
            ORDER BY rd.retrieved_at DESC
            """,
            (ids,),
        ).fetchall():
            procedencia.setdefault(str(p["entity_id"]), []).append(
                {
                    "source_id": p["source_id"],
                    "url": p["url"],
                    "content_hash": p["content_hash"],
                    "retrieved_at": p["retrieved_at"].isoformat(),
                    "extractor_version": p["extractor_version"],
                    **({"excerpt": p["excerpt"]} if p["excerpt"] else {}),
                }
            )

    # Y el último cierre: los nombres DENTRO del texto.
    #
    # Omitir la ficha de una persona física no la saca de la prosa que la
    # rodea. La descripción de un expediente nombraba al artista contratado, y
    # el expediente sí se publica: ficha retirada, nombre publicado igual, en
    # un campo que ninguna de las dos reglas anteriores mira.
    #
    # Se hace aquí, al final, sobre lo que ya está decidido que sale: así
    # cubre el caption, las propiedades, las aristas y los extractos de
    # procedencia a la vez, y no depende de que cada conector se acuerde.
    menciones = [0]
    patron = censor(nombres_de_persona(store))
    if patron is not None:
        nodos = tapar_nombres(nodos, patron, menciones)
        aristas = tapar_nombres(aristas, patron, menciones)
        procedencia = tapar_nombres(procedencia, patron, menciones)
        if menciones[0]:
            log.warning(
                "se han tapado nombres de persona dentro de texto publicado",
                menciones=menciones[0],
            )

    total = store.conn.execute(
        "SELECT count(*) AS n FROM entities WHERE canonical_id IS NULL"
    ).fetchone()
    total_entidades = int(total["n"]) if total else 0

    # Cuánto aporta cada fuente AL VOLCADO, no cuántas hay registradas.
    #
    # Las tres fuentes se dan de alta antes de ingerir, así que la tabla dice
    # "bdns, placsp, tcu" aunque una de ellas no haya traído nada. El 18/9/2026
    # BDNS no respondió y la instantánea salió con el 100 % de la procedencia
    # en PLACSP: sin subvenciones, sin partidos, la mitad del mapa. Y el
    # cartel de la web seguía diciendo "datos reales de BDNS, PLACSP y TdC".
    #
    # Eso es mentir por omisión, que es justo lo que este proyecto no puede
    # hacer. Si una fuente falla se tolera el hueco, pero se DICE.
    aporte = (
        {
            f["source_id"]: int(f["n"])
            for f in store.conn.execute(
                """
            SELECT rd.source_id, count(DISTINCT p.entity_id) AS n
            FROM provenance p
            JOIN raw_documents rd ON rd.id = p.raw_document_id
            WHERE p.entity_id = ANY(%s)
            GROUP BY rd.source_id
            """,
                (ids,),
            ).fetchall()
        }
        if ids
        else {}
    )

    fuentes = [
        {**dict(f), "entidades": aporte.get(f["id"], 0)}
        for f in store.conn.execute("SELECT id, name, url FROM sources ORDER BY id").fetchall()
    ]

    documento = {
        "generado": datetime.now(UTC).isoformat(),
        "instantanea": True,
        # Si se recortó, se dice. Un mapa incompleto que finge estar completo
        # miente, y aquí la mentira sería por omisión.
        "truncado": total_entidades > len(nodos),
        "total_entidades_en_base": total_entidades,
        "fuentes": fuentes,
        "nodes": nodos,
        "edges": aristas,
        "provenance": procedencia,
        "personasOmitidas": {
            "fichas": len(omitidas),
            "menciones_en_texto": menciones[0],
        },
    }

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(documento, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    indice = _exportar_indice(store, destino, {str(n["id"]) for n in nodos}, patron)

    resumen = {
        "entidades": len(nodos),
        "personas_omitidas": len(omitidas),
        "menciones_tapadas": menciones[0],
        "aristas": len(aristas),
        "con_procedencia": len(procedencia),
        "truncado": documento["truncado"],
        "bytes": destino.stat().st_size,
        **indice,
    }
    log.info("grafo exportado", destino=str(destino), **resumen)
    return resumen


def _exportar_indice(
    store: Store,
    destino: Path,
    en_mapa: set[str],
    patron: re.Pattern[str] | None = None,
) -> dict[str, Any]:
    """Escribe, junto al grafo, un índice de TODAS las entidades.

    El mapa está acotado a propósito: por encima de unos miles de nodos el
    navegador sufre y la vista deja de servir. Pero ese tope acotaba también la
    **búsqueda**, y ahí el efecto era otro: quien buscaba el ayuntamiento de su
    pueblo y no estaba entre los nodos publicados leía «Sin resultados», que es
    indistinguible de «esa entidad no existe en ninguna fuente». Lo que pasaba
    de verdad es que sí existe y no cupo.

    El índice no lleva aristas ni procedencia —que es lo que pesa—, sólo la
    entidad y cuánto mueve, así que cabe entero aunque la base crezca mucho. La
    web lo carga sólo cuando hace falta.

    `en_mapa` marca las que además están en el grafo publicado: de ésas se
    puede enseñar la red; del resto, sólo las cifras, y diciéndolo.

    ## El expediente se puentea aquí también

    Entre el organismo que adjudica y la empresa que cobra SIEMPRE hay un
    contrato de por medio: la arista con el dinero sale del expediente, no del
    organismo. Sumando en crudo, «quién reparte más dinero público» sale
    contestado con una lista de expedientes y todos los organismos aparecen
    repartiendo cero.

    Así que se hace en SQL lo mismo que el mapa hace al dibujar: el dinero de
    un expediente se le imputa a su órgano de contratación, y los
    adjudicatarios cuentan como receptores suyos. Los expedientes no entran en
    el índice —un contrato no es un actor y no se busca por él—.
    """
    filas = store.conn.execute(
        """
        WITH vivas AS (
            SELECT r.* FROM relationships r WHERE r.status <> 'retracted'
        ),
        -- Lo que entra y sale de cada entidad por una arista directa.
        directo AS (
            SELECT e.id,
                   coalesce(sum(CASE WHEN r.target_entity_id = e.id
                                      AND r.ftm_schema IN ('Payment','ContractAward')
                                     THEN r.amount END), 0) AS recibido,
                   coalesce(sum(CASE WHEN r.source_entity_id = e.id
                                      AND r.ftm_schema = 'Payment'
                                     THEN r.amount END), 0) AS pagado,
                   count(DISTINCT CASE WHEN r.target_entity_id = e.id
                                        AND r.ftm_schema = 'Payment'
                                       THEN r.source_entity_id END) AS pagadores,
                   count(DISTINCT CASE WHEN r.source_entity_id = e.id
                                        AND r.ftm_schema = 'Payment'
                                       THEN r.target_entity_id END) AS receptores
            FROM entities e
            LEFT JOIN vivas r ON r.source_entity_id = e.id OR r.target_entity_id = e.id
            WHERE e.canonical_id IS NULL
              AND e.ftm_schema NOT IN (%s, 'Contract')
            GROUP BY e.id
        ),
        -- Órgano -> (UnknownLink) -> expediente -> (ContractAward) -> empresa.
        -- El dinero del expediente es del órgano que lo adjudicó.
        puente AS (
            SELECT u.source_entity_id AS organo,
                   coalesce(sum(a.amount), 0) AS pagado,
                   count(DISTINCT a.target_entity_id) AS receptores
            FROM vivas u
            JOIN entities c ON c.id = u.target_entity_id AND c.ftm_schema = 'Contract'
            JOIN vivas a ON a.source_entity_id = c.id AND a.ftm_schema = 'ContractAward'
            WHERE u.ftm_schema = 'UnknownLink'
            GROUP BY u.source_entity_id
        ),
        -- Y al revés: de cuántos ÓRGANOS distintos cobra cada adjudicatario.
        -- Contar expedientes en vez de órganos exageraría el alcance de quien
        -- encadena muchos contratos con una sola administración.
        puente_inverso AS (
            SELECT a.target_entity_id AS empresa,
                   count(DISTINCT u.source_entity_id) AS pagadores
            FROM vivas a
            JOIN entities c ON c.id = a.source_entity_id AND c.ftm_schema = 'Contract'
            JOIN vivas u ON u.target_entity_id = c.id AND u.ftm_schema = 'UnknownLink'
            WHERE a.ftm_schema = 'ContractAward'
            GROUP BY a.target_entity_id
        )
        SELECT e.id, e.ftm_schema, e.caption, COALESCE(e.nif,'') AS nif, e.properties,
               d.recibido,
               d.pagado + coalesce(p.pagado, 0) AS pagado,
               d.pagadores + coalesce(pi.pagadores, 0) AS pagadores,
               d.receptores + coalesce(p.receptores, 0) AS receptores
        FROM directo d
        JOIN entities e ON e.id = d.id
        LEFT JOIN puente p ON p.organo = d.id
        LEFT JOIN puente_inverso pi ON pi.empresa = d.id
        ORDER BY d.recibido + d.pagado + coalesce(p.pagado, 0) DESC, e.caption
        """,
        (PERSONALES,),
    ).fetchall()

    entradas = []
    tapadas = [0]
    for f in filas:
        # Misma regla que en el grafo: el índice es otra puerta de publicación.
        if es_identificador_personal(f["nif"]):
            continue
        props = f["properties"] or {}
        entradas.append(
            {
                "id": str(f["id"]),
                "schema": f["ftm_schema"],
                # El caption de una ficha del índice es un nombre, no prosa,
                # pero es otra puerta y se cierra igual: la UTE que costó el
                # historial era una `Company` con forma societaria correcta y
                # los nombres de sus dos socios dentro del nombre.
                "caption": (
                    f["caption"] if patron is None else tapar_nombres(f["caption"], patron, tapadas)
                ),
                **({"nif": f["nif"]} if f["nif"] else {}),
                # Sólo se escriben si no son cero: multiplicado por decenas de
                # miles de entradas, un `0` de más es peso muerto en un fichero
                # que se descarga entero.
                **({"recibido": str(f["recibido"])} if f["recibido"] else {}),
                **({"pagado": str(f["pagado"])} if f["pagado"] else {}),
                **({"pagadores": int(f["pagadores"])} if f["pagadores"] else {}),
                **({"receptores": int(f["receptores"])} if f["receptores"] else {}),
                **({"partido": True} if props.get("partido_politico") else {}),
                **({"extranjera": True} if props.get("entidad_extranjera") else {}),
                **({"extranjeraIndicio": True} if props.get("entidad_extranjera_indicio") else {}),
                **({"enMapa": True} if str(f["id"]) in en_mapa else {}),
            }
        )

    # Los totales se calculan sobre TODO, aunque luego se publique un extracto:
    # el dinero se suma sólo por el lado que paga, porque sumar las dos
    # columnas contaría cada operación dos veces —una en quien la paga y otra
    # en quien la cobra— y el total saldría al doble.
    totales = {
        "dineroTotal": str(sum(Decimal(e.get("pagado", "0")) for e in entradas)),
        "nActores": len(entradas),
        "nPartidos": sum(1 for e in entradas if e.get("partido")),
        "nExtranjeras": sum(1 for e in entradas if e.get("extranjera")),
        "enMapa": len(en_mapa),
    }

    cabecera = {"generado": datetime.now(UTC).isoformat(), "total": len(entradas), **totales}

    ruta = destino.with_name("indice.json")
    ruta.write_text(
        json.dumps(
            {**cabecera, "entidades": entradas},
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    ruta_top = destino.with_name("indice-top.json")
    ruta_top.write_text(
        json.dumps(
            {**cabecera, "parcial": True, "entidades": _cabeza_del_indice(entradas)},
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    return {
        "indice_entidades": len(entradas),
        "indice_bytes": ruta.stat().st_size,
        "indice_top_bytes": ruta_top.stat().st_size,
        "indice_menciones_tapadas": tapadas[0],
    }


# Cuántas entidades se guardan por cada criterio en el extracto. Los rankings
# de la portada enseñan 25; 300 deja margen de sobra para que el recorte no
# pueda cambiar ninguno de esos 25, y sigue cabiendo en unas decenas de kB.
CABEZA_POR_CRITERIO = 300


def _cabeza_del_indice(entradas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """El extracto del índice que necesita la portada.

    El índice completo crece con la base: a 40.000 entidades son casi 6 MB, y
    descargarlo entero en cada visita para enseñar cuatro listas de 25 filas
    es cobrarle a todo el mundo el precio de la cobertura.

    Aquí van sólo las cabezas de cada ranking —más los partidos y el capital
    extranjero, que son listas enteras y son pocas—. Los rankings salen
    EXACTOS: el primero de los 25 por dinero repartido está por definición
    dentro de los 300 primeros por dinero repartido.

    El índice completo sigue publicándose, y la web lo pide sólo cuando alguien
    busca. Que es cuando hace falta: para buscar sí hay que tenerlo todo.
    """

    def cabeza(clave: str, numerico: bool) -> list[dict[str, Any]]:
        con_valor = [e for e in entradas if e.get(clave)]
        con_valor.sort(
            key=lambda e: Decimal(e[clave]) if numerico else int(e[clave]),
            reverse=True,
        )
        return con_valor[:CABEZA_POR_CRITERIO]

    elegidas: dict[str, dict[str, Any]] = {}
    for clave, numerico in (("pagado", True), ("recibido", True), ("pagadores", False)):
        for e in cabeza(clave, numerico):
            elegidas[e["id"]] = e
    for e in entradas:
        if e.get("partido") or e.get("extranjera") or e.get("extranjeraIndicio"):
            elegidas[e["id"]] = e
    return list(elegidas.values())
