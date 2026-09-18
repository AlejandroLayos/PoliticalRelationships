"""Tests del volcado que publica la web.

Lo que se comprueba aquí es una invariante de *forma del grafo*, no de
contenido: **ningún nodo publicado puede quedarse sin aristas, y ninguna
arista puede colgar de un nodo ausente.**

Parece obvio y no lo era. Hasta el 18/9/2026 el volcado elegía las N
entidades de mayor grado y después se quedaba sólo con las aristas cuyos dos
extremos estuvieran dentro. El corte caía por el medio del grafo: un nodo muy
conectado entraba, sus vecinos de grado 1 no, y sus aristas desaparecían. La
instantánea publicada tenía 4.000 nodos repartidos en **1.393 componentes
conexas**, con 548 nodos aislados entre los más conectados de la base. No se
veía ni un núcleo porque no quedaba ninguno que ver.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest

from sinapsis_ingest.exportar import exportar
from sinapsis_ingest.store import Source, Store

DSN = os.environ.get("SINAPSIS_TEST_POSTGRES_DSN", "")

pytestmark = pytest.mark.skipif(not DSN, reason="SINAPSIS_TEST_POSTGRES_DSN sin definir")


def _entidad(store: Store, caption: str, esquema: str = "Company") -> str:
    fila = store.conn.execute(
        """
        INSERT INTO entities (ftm_schema, caption, dedupe_key, properties)
        VALUES (%s, %s, %s, '{}'::jsonb) RETURNING id
        """,
        (esquema, caption, f"test:{uuid.uuid4()}"),
    ).fetchone()
    assert fila is not None
    return str(fila["id"])


def _arista(store: Store, a: str, b: str, importe: str | None) -> None:
    store.conn.execute(
        """
        INSERT INTO relationships
            (ftm_schema, source_entity_id, target_entity_id, amount, currency,
             confidence, status, dedupe_key)
        VALUES ('Payment', %s, %s, %s, %s, 1.0, 'asserted', %s)
        """,
        (a, b, importe, "EUR" if importe else "", f"test:{uuid.uuid4()}"),
    )


@pytest.fixture
def store():
    with Store(DSN) as s:
        migraciones = Path(__file__).resolve().parents[2] / "backend" / "migrations"
        for f in sorted(migraciones.glob("*.up.sql")):
            try:
                s.conn.execute(f.read_text(encoding="utf-8"))
            except Exception:
                s.conn.rollback()
        s.conn.commit()
        s.conn.execute(
            """TRUNCATE provenance, entity_resolution_decisions, review_queue,
                        relationships, entities, raw_documents, sources CASCADE"""
        )
        s.upsert_source(Source(id="test", name="Test", url="https://ejemplo.test"))
        s.conn.commit()
        yield s


def _exportado(store: Store, tmp_path: Path, **kw) -> dict:
    exportar(store, tmp_path / "g.json", **kw)
    return json.loads((tmp_path / "g.json").read_text(encoding="utf-8"))


def test_ningun_nodo_publicado_se_queda_sin_aristas(store, tmp_path):
    """La invariante que rompía el volcado anterior."""
    # Una cadena larga de pagos: al recortar, el método viejo la troceaba.
    ids = [_entidad(store, f"EMPRESA {i}") for i in range(40)]
    for i in range(39):
        _arista(store, ids[i], ids[i + 1], f"{(i + 1) * 100}.00")
    store.conn.commit()

    d = _exportado(store, tmp_path, max_entidades=20, max_aristas=15)

    publicados = {n["id"] for n in d["nodes"]}
    con_arista = set()
    for a in d["edges"]:
        con_arista.add(a["source"])
        con_arista.add(a["target"])

    aislados = publicados - con_arista
    assert not aislados, f"{len(aislados)} nodos publicados sin ninguna arista"


def test_ninguna_arista_cuelga_de_un_nodo_ausente(store, tmp_path):
    ids = [_entidad(store, f"E{i}") for i in range(30)]
    for i in range(29):
        _arista(store, ids[i], ids[i + 1], f"{i + 1}.00")
    store.conn.commit()

    d = _exportado(store, tmp_path, max_entidades=12, max_aristas=10)

    publicados = {n["id"] for n in d["nodes"]}
    for a in d["edges"]:
        assert a["source"] in publicados, "arista con origen fuera del volcado"
        assert a["target"] in publicados, "arista con destino fuera del volcado"


def test_se_respetan_los_topes(store, tmp_path):
    ids = [_entidad(store, f"E{i}") for i in range(60)]
    for i in range(59):
        _arista(store, ids[i], ids[i + 1], f"{i + 1}.00")
    store.conn.commit()

    d = _exportado(store, tmp_path, max_entidades=20, max_aristas=15)
    assert len(d["nodes"]) <= 20
    assert len(d["edges"]) <= 15


def test_manda_el_dinero_al_elegir_que_publicar(store, tmp_path):
    """Con sitio justo, entra lo caro: es un mapa de dinero."""
    a, b = _entidad(store, "PAGO GRANDE A"), _entidad(store, "PAGO GRANDE B")
    c, e = _entidad(store, "PAGO CHICO A"), _entidad(store, "PAGO CHICO B")
    _arista(store, a, b, "9000000.00")
    _arista(store, c, e, "1.00")
    store.conn.commit()

    d = _exportado(store, tmp_path, max_entidades=2, max_aristas=1)
    captions = {n["caption"] for n in d["nodes"]}
    assert captions == {"PAGO GRANDE A", "PAGO GRANDE B"}


def test_un_grafo_vacio_no_revienta(store, tmp_path):
    d = _exportado(store, tmp_path)
    assert d["nodes"] == []
    assert d["edges"] == []


def test_las_aristas_sin_importe_no_se_quedan_fuera(store, tmp_path):
    """El tejido conectivo entra aunque no lleve dinero.

    Ordenar por importe es correcto para elegir QUÉ publicar, pero deja fuera
    por construcción a las aristas sin cifra — entre ellas el enlace del órgano
    de contratación con su contrato, que no lleva importe a propósito para no
    contar el mismo dinero dos veces. Sin ellas el grafo publicado volvía a
    salir en pedazos aunque ningún nodo estuviera aislado.
    """
    a = _entidad(store, "ORGANISMO", "PublicBody")
    b = _entidad(store, "EXPEDIENTE", "Contract")
    c = _entidad(store, "EMPRESA")
    _arista(store, b, c, "1000000.00")  # la adjudicación lleva el dinero
    # El enlace órgano -> contrato, sin importe.
    store.conn.execute(
        """
        INSERT INTO relationships
            (ftm_schema, source_entity_id, target_entity_id, confidence, status, dedupe_key)
        VALUES ('UnknownLink', %s, %s, 1.0, 'asserted', %s)
        """,
        (a, b, "test:enlace-organo"),
    )
    store.conn.commit()

    d = _exportado(store, tmp_path, max_entidades=10, max_aristas=10)
    esquemas = {e["schema"] for e in d["edges"]}
    assert "UnknownLink" in esquemas, "el enlace sin importe se quedó fuera"
    # Y la que sí lleva dinero sigue estando: el helper la crea como Payment.
    assert "Payment" in esquemas
    assert len(d["edges"]) == 2


def test_la_segunda_pasada_no_mete_nodos_nuevos(store, tmp_path):
    """Sólo une lo que ya está dentro; no ensancha el volcado."""
    ids = [_entidad(store, f"E{i}") for i in range(10)]
    for i in range(9):
        _arista(store, ids[i], ids[i + 1], f"{(i + 1) * 1000}.00")
    store.conn.commit()

    d = _exportado(store, tmp_path, max_entidades=4, max_aristas=3)
    assert len(d["nodes"]) <= 4
    publicados = {n["id"] for n in d["nodes"]}
    for a in d["edges"]:
        assert a["source"] in publicados
        assert a["target"] in publicados


def test_el_organismo_entra_aunque_no_tenga_ninguna_arista_con_dinero(store, tmp_path):
    """El caso real de PLACSP, que dejó el mapa sin organismos.

    El órgano de contratación cuelga de su contrato por una arista sin importe
    —el dinero lo lleva la adjudicación—, así que ordenando por importe no
    entra nunca. Y no basta con admitir después las aristas cuyos dos extremos
    ya estén dentro: es circular, porque el órgano sólo puede entrar por esa
    misma arista.
    """
    organo = _entidad(store, "MINISTERIO", "PublicBody")
    expediente = _entidad(store, "EXPEDIENTE", "Contract")
    empresa = _entidad(store, "EMPRESA")
    _arista(store, expediente, empresa, "5000000.00")
    store.conn.execute(
        """
        INSERT INTO relationships
            (ftm_schema, source_entity_id, target_entity_id, confidence, status, dedupe_key)
        VALUES ('UnknownLink', %s, %s, 1.0, 'asserted', %s)
        """,
        (organo, expediente, "test:organo"),
    )
    store.conn.commit()

    d = _exportado(store, tmp_path, max_entidades=10, max_aristas=10)

    captions = {n["caption"] for n in d["nodes"]}
    assert "MINISTERIO" in captions, "el organismo se quedó fuera del mapa"
    assert "UnknownLink" in {e["schema"] for e in d["edges"]}

    # Y queda de verdad conectado, no suelto.
    enlaces = [e for e in d["edges"] if e["schema"] == "UnknownLink"]
    assert len(enlaces) == 1
    assert {enlaces[0]["source"], enlaces[0]["target"]} <= {n["id"] for n in d["nodes"]}


def test_el_dinero_no_agota_el_sitio_del_tejido_conectivo(store, tmp_path):
    """El fallo que dio tres instantáneas idénticas al byte.

    Si la primera pasada gasta todo el presupuesto de nodos con aristas caras,
    la segunda no puede traerse ningún nodo nuevo y los organismos —que sólo
    cuelgan por aristas sin importe— se quedan fuera para siempre. La señal
    era que el volcado traía exactamente el tope de nodos, clavado.
    """
    # Muchas parejas caras, suficientes para llenar el tope por sí solas.
    for i in range(30):
        a = _entidad(store, f"PAGADOR {i}", "PublicBody")
        b = _entidad(store, f"COBRADOR {i}")
        _arista(store, a, b, f"{9_000_000 - i}.00")

    # Y un organismo que sólo cuelga por una arista sin importe.
    organo = _entidad(store, "ORGANO TARDIO", "PublicBody")
    expediente = _entidad(store, "EXPEDIENTE TARDIO", "Contract")
    empresa = _entidad(store, "EMPRESA TARDIA")
    _arista(store, expediente, empresa, "100.00")
    store.conn.execute(
        """
        INSERT INTO relationships
            (ftm_schema, source_entity_id, target_entity_id, confidence, status, dedupe_key)
        VALUES ('UnknownLink', %s, %s, 1.0, 'asserted', %s)
        """,
        (organo, expediente, "test:organo-tardio"),
    )
    store.conn.commit()

    d = _exportado(store, tmp_path, max_entidades=20, max_aristas=40)

    # Con el tope clavado en la pasada 1 esto era imposible.
    assert len(d["nodes"]) <= 20
    publicados = {n["id"] for n in d["nodes"]}
    aristas = [e for e in d["edges"] if e["schema"] == "UnknownLink"]
    if aristas:
        for e in aristas:
            assert e["source"] in publicados and e["target"] in publicados

    # Lo que de verdad se comprueba: queda sitio libre tras la pasada del
    # dinero, que es la condición para que el tejido conectivo pueda entrar.
    assert len(d["nodes"]) < 20 or any(n["schema"] == "Contract" for n in d["nodes"])


def test_los_partidos_no_pierden_contra_un_contrato_grande(store, tmp_path):
    """Un mapa de financiación política sin partidos no sirve de nada.

    Se comprobó sobre datos reales: al coser bien el grafo entraron 456
    organismos y desaparecieron los 179 partidos. Una subvención electoral es
    calderilla al lado de un contrato de infraestructuras, así que compitiendo
    por importe un partido nunca gana.
    """
    for i in range(20):
        a = _entidad(store, f"MINISTERIO {i}", "PublicBody")
        b = _entidad(store, f"CONSTRUCTORA {i}")
        _arista(store, a, b, f"{50_000_000 - i}.00")

    fila = store.conn.execute(
        """
        INSERT INTO entities (ftm_schema, caption, dedupe_key, properties)
        VALUES ('Organization', 'PARTIDO DE PRUEBA', 'nif:G00000000',
                '{"partido_politico": true}'::jsonb)
        RETURNING id
        """
    ).fetchone()
    assert fila is not None
    partido = str(fila["id"])
    organo = _entidad(store, "MINISTERIO DEL INTERIOR", "PublicBody")
    _arista(store, organo, partido, "12000.00")  # subvención electoral, calderilla
    store.conn.commit()

    d = _exportado(store, tmp_path, max_entidades=12, max_aristas=12)

    captions = {n["caption"] for n in d["nodes"]}
    assert "PARTIDO DE PRUEBA" in captions, "el partido perdió contra los contratos"
    assert "MINISTERIO DEL INTERIOR" in captions, "el partido entró pero suelto"


def test_el_volcado_dice_que_fuente_no_aporto_nada(store, tmp_path):
    """Una fuente caída no puede pasar desapercibida.

    Las fuentes se dan de alta antes de ingerir, así que la tabla las lista
    aunque no hayan traído nada. El 18/9/2026 BDNS no respondió y la
    instantánea salió con toda la procedencia en PLACSP —sin subvenciones y
    sin partidos, la mitad del mapa— mientras el cartel seguía diciendo "datos
    reales de BDNS, PLACSP y Tribunal de Cuentas". Mentir por omisión.
    """
    store.upsert_source(Source(id="caida", name="Fuente Caída", url="https://ejemplo.test"))
    a = _entidad(store, "A")
    b = _entidad(store, "B")
    _arista(store, a, b, "100.00")
    store.conn.commit()

    d = _exportado(store, tmp_path)

    por_id = {f["id"]: f for f in d["fuentes"]}
    assert por_id["caida"]["entidades"] == 0, "la fuente sin aporte no se distingue"
    # Y la que sí aportó no puede salir a cero.
    assert "entidades" in por_id["test"]


def test_una_arista_sin_cifra_explica_por_que(store, tmp_path):
    """Sin importe no significa lo mismo que con el importe descartado.

    Una arista puede no llevar cifra porque la fuente no publicó ninguna, o
    porque la ingesta no se creyó la que publicó —el caso de PLACSP: un
    contrato de 22.000 € con un importe adjudicado de 1.954 millones—. En la
    web se ven igual si el volcado no lleva el motivo, y entonces la ausencia
    de dato parece un dato.
    """
    a = _entidad(store, "ÓRGANO", "PublicBody")
    b = _entidad(store, "EMPRESA")
    store.conn.execute(
        """
        INSERT INTO relationships
            (ftm_schema, source_entity_id, target_entity_id, amount, currency,
             confidence, status, dedupe_key, properties)
        VALUES ('Payment', %s, %s, NULL, '', 0.5, 'asserted', %s,
                '{"importeSinInterpretar": "1954023643.40",
                  "motivoImporteDudoso": "supera en más de 10 veces el presupuesto"}'::jsonb)
        """,
        (a, b, f"test:{uuid.uuid4()}"),
    )
    store.conn.commit()

    g = _exportado(store, tmp_path)
    arista = next(x for x in g["edges"] if x["source"] == a)
    assert "amount" not in arista
    assert arista["properties"]["importeSinInterpretar"] == "1954023643.40"
    assert "presupuesto" in arista["properties"]["motivoImporteDudoso"]


def test_una_arista_sin_propiedades_no_engorda_el_volcado(store, tmp_path):
    # La inmensa mayoría no tiene propiedades; escribir `"properties": {}` en
    # cada una de miles de aristas es peso muerto en un fichero que se descarga
    # entero en cada visita.
    a = _entidad(store, "ÓRGANO", "PublicBody")
    b = _entidad(store, "EMPRESA")
    _arista(store, a, b, "1000")
    store.conn.commit()

    g = _exportado(store, tmp_path)
    arista = next(x for x in g["edges"] if x["source"] == a)
    assert "properties" not in arista


# --- ninguna persona física llega al volcado -------------------------------
#
# Entre el 3/8/2026 y el 18/9/2026 la instantánea diaria publicó nombres y
# apellidos de particulares con su DNI. La corrección de los conectores existía
# y estaba probada desde el primer día: vivía en una rama que no se desplegaba.
# Seis semanas sin que fallara un solo test.
#
# Estos comprueban la ÚLTIMA puerta, por la que pasa todo lo que se publica,
# venga del conector que venga.


def test_una_persona_fisica_no_llega_al_volcado(store, tmp_path):
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    persona = _entidad(store, "NOMBRE APELLIDO APELLIDO", "Person")
    empresa = _entidad(store, "EMPRESA SL")
    _arista(store, organo, persona, "3000")
    _arista(store, organo, empresa, "9000")
    store.conn.commit()

    g = _exportado(store, tmp_path)
    assert persona not in [n["id"] for n in g["nodes"]]
    assert "NOMBRE APELLIDO APELLIDO" not in json.dumps(g, ensure_ascii=False)
    assert "Person" not in {n["schema"] for n in g["nodes"]}


def test_la_arista_de_una_persona_fisica_se_va_con_ella(store, tmp_path):
    # Una arista colgando de un nodo ausente rompe el grafo, y además el par
    # (organismo, importe) seguiría señalando a la persona aunque su nombre no
    # estuviera publicado.
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    persona = _entidad(store, "OTRO NOMBRE APELLIDO", "Person")
    empresa = _entidad(store, "EMPRESA SL")
    _arista(store, organo, persona, "3000")
    _arista(store, organo, empresa, "9000")
    store.conn.commit()

    g = _exportado(store, tmp_path)
    publicados = {n["id"] for n in g["nodes"]}
    for a in g["edges"]:
        assert a["source"] in publicados
        assert a["target"] in publicados
    assert persona not in [a["source"] for a in g["edges"]]
    assert persona not in [a["target"] for a in g["edges"]]


def test_la_procedencia_de_una_persona_fisica_tampoco_se_publica(store, tmp_path):
    # El extracto del documento original lleva el nombre dentro.
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    persona = _entidad(store, "TERCER NOMBRE APELLIDO", "Person")
    empresa = _entidad(store, "EMPRESA SL")
    _arista(store, organo, persona, "3000")
    _arista(store, organo, empresa, "9000")
    doc = store.conn.execute(
        """
        INSERT INTO raw_documents (source_id, url, content_hash, media_type, retrieved_at, content)
        VALUES ('test', 'https://ejemplo.test/x', %s, 'application/json', now(), '{}'::bytea)
        RETURNING id
        """,
        ("f" * 64,),
    ).fetchone()
    store.conn.execute(
        """
        INSERT INTO provenance (entity_id, raw_document_id, extractor_version, excerpt)
        VALUES (%s, %s, 'test', 'concedido a TERCER NOMBRE APELLIDO')
        """,
        (persona, doc["id"]),
    )
    store.conn.commit()

    g = _exportado(store, tmp_path)
    assert "TERCER NOMBRE APELLIDO" not in json.dumps(g, ensure_ascii=False)


def test_el_agregado_anonimo_de_particulares_si_se_publica(store, tmp_path):
    # Lo que se retira es la identificación, no el hecho: que esa convocatoria
    # repartió dinero entre particulares es información pública y es la que
    # hace que el importe cuadre.
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    agregado = _entidad(store, "Personas físicas (convocatoria 123)", "LegalEntity")
    _arista(store, organo, agregado, "3000")
    store.conn.commit()

    g = _exportado(store, tmp_path)
    captions = {n["caption"] for n in g["nodes"]}
    assert "Personas físicas (convocatoria 123)" in captions


# --- el índice: todo lo que hay, no sólo lo que cabe en el mapa ------------
#
# El mapa está acotado a propósito. Ese tope acotaba también la BÚSQUEDA, y
# ahí el efecto era otro: quien buscaba el ayuntamiento de su pueblo y no
# estaba entre los nodos publicados leía «Sin resultados», indistinguible de
# «esa entidad no existe en ninguna fuente».


def _indice(store: Store, tmp_path: Path, **kw) -> dict:
    exportar(store, tmp_path / "g.json", **kw)
    return json.loads((tmp_path / "indice.json").read_text(encoding="utf-8"))


def test_el_indice_recoge_tambien_lo_que_no_cupo_en_el_mapa(store, tmp_path):
    organo = _entidad(store, "AYUNTAMIENTO GRANDE", "PublicBody")
    grande = _entidad(store, "EMPRESA GRANDE")
    pequena = _entidad(store, "EMPRESA PEQUEÑA DE UN PUEBLO")
    _arista(store, organo, grande, "9000000")
    _arista(store, organo, pequena, "500")
    store.conn.commit()

    # Un mapa tan apretado que sólo caben dos entidades.
    g = _exportado(store, tmp_path, max_entidades=2)
    idx = json.loads((tmp_path / "indice.json").read_text(encoding="utf-8"))

    en_mapa = {n["caption"] for n in g["nodes"]}
    assert "EMPRESA PEQUEÑA DE UN PUEBLO" not in en_mapa

    captions = {e["caption"] for e in idx["entidades"]}
    assert "EMPRESA PEQUEÑA DE UN PUEBLO" in captions
    assert idx["total"] == 3


def test_el_indice_marca_cual_esta_en_el_mapa(store, tmp_path):
    # De las que están se puede enseñar la red; de las demás, sólo las cifras,
    # y hay que poder decirlo.
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    dentro = _entidad(store, "DENTRO SL")
    fuera = _entidad(store, "FUERA SL")
    _arista(store, organo, dentro, "9000000")
    _arista(store, organo, fuera, "1")
    store.conn.commit()

    g = _exportado(store, tmp_path, max_entidades=2)
    idx = json.loads((tmp_path / "indice.json").read_text(encoding="utf-8"))
    publicados = {n["id"] for n in g["nodes"]}
    for e in idx["entidades"]:
        assert e.get("enMapa", False) == (e["id"] in publicados)


def test_el_indice_lleva_los_totales_de_cada_entidad(store, tmp_path):
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    empresa = _entidad(store, "EMPRESA SL")
    otra = _entidad(store, "OTRA SL")
    _arista(store, organo, empresa, "1000")
    _arista(store, organo, otra, "3000")
    store.conn.commit()

    idx = _indice(store, tmp_path)
    por_caption = {e["caption"]: e for e in idx["entidades"]}
    # Con dos decimales, igual que los importes del grafo: es el mismo tipo
    # `numeric` de Postgres y la web lo lee con el mismo conversor.
    assert por_caption["EMPRESA SL"]["recibido"] == "1000.00"
    assert por_caption["EMPRESA SL"]["pagadores"] == 1
    assert por_caption["AYUNTAMIENTO"]["pagado"] == "4000.00"
    assert por_caption["AYUNTAMIENTO"]["receptores"] == 2


def test_el_indice_no_escribe_ceros(store, tmp_path):
    # Multiplicado por decenas de miles de entradas, un `0` de más es peso
    # muerto en un fichero que se descarga entero.
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    empresa = _entidad(store, "EMPRESA SL")
    _arista(store, organo, empresa, "1000")
    store.conn.commit()

    idx = _indice(store, tmp_path)
    empresa_idx = next(e for e in idx["entidades"] if e["caption"] == "EMPRESA SL")
    assert "pagado" not in empresa_idx
    assert "receptores" not in empresa_idx


def test_ninguna_persona_fisica_entra_en_el_indice(store, tmp_path):
    # El índice es otra puerta de publicación: la regla vale igual.
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    persona = _entidad(store, "NOMBRE APELLIDO APELLIDO", "Person")
    empresa = _entidad(store, "EMPRESA SL")
    _arista(store, organo, persona, "3000")
    _arista(store, organo, empresa, "9000")
    store.conn.commit()

    idx = _indice(store, tmp_path)
    texto = json.dumps(idx, ensure_ascii=False)
    assert "NOMBRE APELLIDO APELLIDO" not in texto
    assert "Person" not in {e["schema"] for e in idx["entidades"]}


def test_el_indice_marca_partidos_y_extranjeras(store, tmp_path):
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    partido = _entidad(store, "PARTIDO EJEMPLO", "Organization")
    store.conn.execute(
        "UPDATE entities SET properties = '{\"partido_politico\": true}'::jsonb WHERE id = %s",
        (partido,),
    )
    _arista(store, organo, partido, "1000")
    store.conn.commit()

    idx = _indice(store, tmp_path)
    fila = next(e for e in idx["entidades"] if e["caption"] == "PARTIDO EJEMPLO")
    assert fila["partido"] is True


def test_el_indice_no_revienta_con_la_base_vacia(store, tmp_path):
    idx = _indice(store, tmp_path)
    assert idx["total"] == 0
    assert idx["entidades"] == []


# --- el índice puentea el expediente, como el mapa -------------------------


def _contrato(store: Store, organo: str, empresa: str, importe: str) -> str:
    """Órgano --UnknownLink--> expediente --ContractAward--> adjudicatario."""
    exp = _entidad(store, f"EXPEDIENTE {uuid.uuid4().hex[:6]}", "Contract")
    store.conn.execute(
        """
        INSERT INTO relationships
            (ftm_schema, source_entity_id, target_entity_id, amount, currency,
             confidence, status, dedupe_key)
        VALUES ('UnknownLink', %s, %s, NULL, '', 1.0, 'asserted', %s)
        """,
        (organo, exp, f"test:{uuid.uuid4()}"),
    )
    store.conn.execute(
        """
        INSERT INTO relationships
            (ftm_schema, source_entity_id, target_entity_id, amount, currency,
             confidence, status, dedupe_key)
        VALUES ('ContractAward', %s, %s, %s, 'EUR', 1.0, 'asserted', %s)
        """,
        (exp, empresa, importe, f"test:{uuid.uuid4()}"),
    )
    return exp


def test_el_dinero_del_expediente_se_le_imputa_a_su_organo(store, tmp_path):
    # Sin puentear, «quién reparte más dinero público» sale contestado con una
    # lista de expedientes y todos los organismos aparecen repartiendo cero.
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    empresa = _entidad(store, "CONSTRUCTORA SL")
    _contrato(store, organo, empresa, "250000")
    store.conn.commit()

    idx = _indice(store, tmp_path)
    por_caption = {e["caption"]: e for e in idx["entidades"]}
    assert por_caption["AYUNTAMIENTO"]["pagado"] == "250000.00"
    assert por_caption["AYUNTAMIENTO"]["receptores"] == 1
    assert por_caption["CONSTRUCTORA SL"]["recibido"] == "250000.00"
    assert por_caption["CONSTRUCTORA SL"]["pagadores"] == 1


def test_el_expediente_no_entra_en_el_indice(store, tmp_path):
    # Un contrato no es un actor y no se busca por él.
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    empresa = _entidad(store, "CONSTRUCTORA SL")
    _contrato(store, organo, empresa, "250000")
    store.conn.commit()

    idx = _indice(store, tmp_path)
    assert "Contract" not in {e["schema"] for e in idx["entidades"]}


def test_se_cuentan_organos_distintos_y_no_expedientes(store, tmp_path):
    # Contar expedientes exageraría el alcance de quien encadena muchos
    # contratos con una sola administración: diez contratos del mismo
    # ayuntamiento no son diez administraciones.
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    otro = _entidad(store, "DIPUTACIÓN", "PublicBody")
    empresa = _entidad(store, "CONSTRUCTORA SL")
    for _ in range(4):
        _contrato(store, organo, empresa, "1000")
    _contrato(store, otro, empresa, "1000")
    store.conn.commit()

    idx = _indice(store, tmp_path)
    fila = next(e for e in idx["entidades"] if e["caption"] == "CONSTRUCTORA SL")
    assert fila["pagadores"] == 2
    assert fila["recibido"] == "5000.00"


def test_se_suman_las_dos_vias_de_dinero(store, tmp_path):
    # Un organismo puede a la vez subvencionar (Payment directo) y adjudicar
    # (a través de un expediente). Las dos son dinero que reparte.
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    empresa = _entidad(store, "CONSTRUCTORA SL")
    asociacion = _entidad(store, "ASOCIACIÓN VECINAL")
    _arista(store, organo, asociacion, "2000")
    _contrato(store, organo, empresa, "8000")
    store.conn.commit()

    idx = _indice(store, tmp_path)
    fila = next(e for e in idx["entidades"] if e["caption"] == "AYUNTAMIENTO")
    assert fila["pagado"] == "10000.00"
    assert fila["receptores"] == 2
