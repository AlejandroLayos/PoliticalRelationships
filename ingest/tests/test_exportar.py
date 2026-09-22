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

from sinapsis_ingest.exportar import (
    _SQL_IDENTIFICADOR_PERSONAL,
    MARCA_NOMBRE_RETIRADO,
    exportar,
)
from sinapsis_ingest.store import Source, Store
from sinapsis_ingest.util import es_identificador_personal

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


def _contrato(store: Store, organo: str, empresa: str, importe: str, caption: str = "") -> str:
    """Órgano --UnknownLink--> expediente --ContractAward--> adjudicatario."""
    exp = _entidad(store, caption or f"EXPEDIENTE {uuid.uuid4().hex[:6]}", "Contract")
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


# --- el expediente nunca se publica sin su órgano --------------------------
#
# El 18/9/2026, al doblarse los datos ingeridos, 1.070 de los 1.368
# expedientes publicados salieron SIN órgano: un nodo colgando que dice que
# alguien adjudicó algo sin decir quién. El grafo pasó de 354 a 601 pedazos.
#
# La causa: la arista que cuelga el expediente de su órgano no lleva importe,
# y todo se recorre por importe descendente, así que van las últimas. Cuando
# les llega el turno el cupo de nodos está agotado.


def test_ningun_expediente_se_publica_sin_su_organo(store, tmp_path):
    # Muchas adjudicaciones caras compitiendo por un cupo pequeño: es la
    # situación exacta que destapó el fallo.
    for i in range(40):
        organo = _entidad(store, f"ÓRGANO {i}", "PublicBody")
        empresa = _entidad(store, f"EMPRESA {i}")
        _contrato(store, organo, empresa, str(10_000_000 - i))
    store.conn.commit()

    g = _exportado(store, tmp_path, max_entidades=30)
    publicados = {n["id"] for n in g["nodes"]}
    expedientes = {n["id"] for n in g["nodes"] if n["schema"] == "Contract"}
    con_organo = {
        a["target"]
        for a in g["edges"]
        if a["schema"] == "UnknownLink" and a["target"] in expedientes
    }
    assert expedientes, "el caso de prueba no publicó ningún expediente"
    assert expedientes == con_organo, "hay expedientes publicados sin su órgano"
    assert publicados >= expedientes


def test_el_triple_no_se_salta_el_tope(store, tmp_path):
    # Reservar tres nodos en vez de dos no puede colarse por encima del cupo.
    for i in range(40):
        organo = _entidad(store, f"ÓRGANO {i}", "PublicBody")
        empresa = _entidad(store, f"EMPRESA {i}")
        _contrato(store, organo, empresa, str(10_000_000 - i))
    store.conn.commit()

    g = _exportado(store, tmp_path, max_entidades=30)
    assert len(g["nodes"]) <= 30


def test_los_organos_se_comparten_entre_sus_contratos(store, tmp_path):
    # El precio del triple es un nodo más la PRIMERA vez: si un órgano adjudica
    # veinte contratos, entra una sola vez.
    organo = _entidad(store, "ÓRGANO ÚNICO", "PublicBody")
    for i in range(20):
        empresa = _entidad(store, f"EMPRESA {i}")
        _contrato(store, organo, empresa, str(1_000_000 - i))
    store.conn.commit()

    g = _exportado(store, tmp_path)
    organismos = [n for n in g["nodes"] if n["schema"] == "PublicBody"]
    assert len(organismos) == 1
    expedientes = {n["id"] for n in g["nodes"] if n["schema"] == "Contract"}
    assert len(expedientes) == 20


def test_una_adjudicacion_sin_organo_conocido_sigue_publicandose(store, tmp_path):
    # Si la fuente no dice qué órgano adjudicó, el hueco se tolera: no se
    # descarta la adjudicación por no poder completar el triple.
    exp = _entidad(store, "EXPEDIENTE SUELTO", "Contract")
    empresa = _entidad(store, "EMPRESA SL")
    store.conn.execute(
        """
        INSERT INTO relationships
            (ftm_schema, source_entity_id, target_entity_id, amount, currency,
             confidence, status, dedupe_key)
        VALUES ('ContractAward', %s, %s, '5000', 'EUR', 1.0, 'asserted', %s)
        """,
        (exp, empresa, f"test:{uuid.uuid4()}"),
    )
    store.conn.commit()

    g = _exportado(store, tmp_path)
    assert "EXPEDIENTE SUELTO" in {n["caption"] for n in g["nodes"]}


# --- el extracto del índice, para no cobrarle a todo el mundo la cobertura --
#
# El índice completo crece con la base: a 40.000 entidades son casi 6 MB.
# Descargarlo entero en cada visita para enseñar cuatro listas de 25 filas es
# cobrarle a todo el mundo el precio de la cobertura.


def _indice_top(store: Store, tmp_path: Path, **kw) -> dict:
    exportar(store, tmp_path / "g.json", **kw)
    return json.loads((tmp_path / "indice-top.json").read_text(encoding="utf-8"))


def test_el_extracto_trae_las_cabezas_de_los_rankings(store, tmp_path):
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    for i in range(10):
        empresa = _entidad(store, f"EMPRESA {i:02d}")
        _arista(store, organo, empresa, str((10 - i) * 1000))
    store.conn.commit()

    top = _indice_top(store, tmp_path)
    captions = [e["caption"] for e in top["entidades"]]
    assert "AYUNTAMIENTO" in captions
    assert "EMPRESA 00" in captions  # la que más cobra
    assert top["parcial"] is True


def test_los_totales_del_extracto_son_los_de_toda_la_base(store, tmp_path):
    # Si los totales se recalcularan sobre el extracto, la portada diría menos
    # dinero y menos entidades de las que hay, y nadie podría notarlo.
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    for i in range(5):
        _arista(store, organo, _entidad(store, f"EMPRESA {i}"), "1000")
    store.conn.commit()

    completo = (
        json.loads((tmp_path / "indice.json").read_text(encoding="utf-8"))
        if (tmp_path / "indice.json").exists()
        else None
    )
    top = _indice_top(store, tmp_path)
    completo = json.loads((tmp_path / "indice.json").read_text(encoding="utf-8"))

    assert top["total"] == completo["total"] == 6
    assert top["nActores"] == 6
    assert top["dineroTotal"] == completo["dineroTotal"] == "5000.00"


def test_el_extracto_conserva_partidos_y_extranjeras_enteros(store, tmp_path):
    # Son listas propias de la portada y son pocas: se llevan enteras aunque
    # no entren por dinero.
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    partido = _entidad(store, "PARTIDO MINÚSCULO", "Organization")
    store.conn.execute(
        "UPDATE entities SET properties = '{\"partido_politico\": true}'::jsonb WHERE id = %s",
        (partido,),
    )
    _arista(store, organo, partido, "1")
    for i in range(5):
        _arista(store, organo, _entidad(store, f"EMPRESA {i}"), "9000000")
    store.conn.commit()

    top = _indice_top(store, tmp_path)
    assert "PARTIDO MINÚSCULO" in {e["caption"] for e in top["entidades"]}


def test_el_extracto_no_es_mayor_que_el_indice(store, tmp_path):
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    for i in range(20):
        _arista(store, organo, _entidad(store, f"EMPRESA {i}"), str(1000 + i))
    store.conn.commit()

    exportar(store, tmp_path / "g.json")
    top = json.loads((tmp_path / "indice-top.json").read_text(encoding="utf-8"))
    completo = json.loads((tmp_path / "indice.json").read_text(encoding="utf-8"))
    assert len(top["entidades"]) <= len(completo["entidades"])
    ids_top = {e["id"] for e in top["entidades"]}
    ids_completo = {e["id"] for e in completo["entidades"]}
    assert ids_top <= ids_completo


def test_un_dni_no_se_publica_aunque_la_ficha_sea_de_una_empresa(store, tmp_path):
    # En el historial había una UTE —`Company`, con forma societaria
    # explícita— cuyo NIF era el DNI de uno de sus socios. La regla de «esto
    # es una empresa» funcionaba bien y aun así salía publicado un DNI.
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    fila = store.conn.execute(
        """
        INSERT INTO entities (ftm_schema, caption, nif, dedupe_key, properties)
        VALUES ('Company', 'UTE EJEMPLO', '12345678Z', %s, '{}'::jsonb) RETURNING id
        """,
        (f"test:{uuid.uuid4()}",),
    ).fetchone()
    ute = str(fila["id"])
    _arista(store, organo, ute, "5000")
    store.conn.commit()

    g = _exportado(store, tmp_path)
    idx = json.loads((tmp_path / "indice.json").read_text(encoding="utf-8"))

    # La ficha entera se va, no sólo el número: en el historial había una UTE
    # así cuyo NOMBRE eran los nombres y apellidos de los dos socios.
    assert "UTE EJEMPLO" not in {n["caption"] for n in g["nodes"]}
    assert "UTE EJEMPLO" not in {e["caption"] for e in idx["entidades"]}
    assert "12345678Z" not in json.dumps(g, ensure_ascii=False)
    assert "12345678Z" not in json.dumps(idx, ensure_ascii=False)


def test_el_nif_de_una_empresa_de_verdad_sigue_publicandose(store, tmp_path):
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    fila = store.conn.execute(
        """
        INSERT INTO entities (ftm_schema, caption, nif, dedupe_key, properties)
        VALUES ('Company', 'EMPRESA SL', 'B12345678', %s, '{}'::jsonb) RETURNING id
        """,
        (f"test:{uuid.uuid4()}",),
    ).fetchone()
    _arista(store, organo, str(fila["id"]), "5000")
    store.conn.commit()

    g = _exportado(store, tmp_path)
    empresa = next(n for n in g["nodes"] if n["caption"] == "EMPRESA SL")
    assert empresa["nif"] == "B12345678"


# --- El nombre dentro del texto -------------------------------------------
#
# Omitir la ficha no saca a la persona de la prosa que la rodea. El 18/9/2026,
# con la regla de §12 aplicándose bien a las entidades, la descripción de un
# expediente seguía nombrando al artista contratado. El expediente sí se
# publica; la ficha de esa persona estaba correctamente retirada del mapa y su
# nombre salió igual. Los tests de las funciones puras están en
# `test_censura_de_nombres.py`; éstos comprueban el volcado entero.


def test_el_nombre_de_una_persona_no_sale_dentro_de_la_descripcion(store, tmp_path):
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    empresa = _entidad(store, "EMPRESA SL")
    _entidad(store, "Queralt Riera", "Person")
    _contrato(
        store,
        organo,
        empresa,
        "5000",
        'licitació del contracte per al projecte de creació "Veus de Parets" de Queralt Riera',
    )
    store.conn.commit()

    g = _exportado(store, tmp_path)
    crudo = json.dumps(g, ensure_ascii=False)
    assert "Queralt" not in crudo
    assert "Riera" not in crudo
    # Y el resto de la descripción se queda: el expediente sigue diciendo qué
    # se contrató. Tapar el nombre no es motivo para perder el dato.
    assert "Veus de Parets" in crudo


def test_tambien_si_la_persona_no_cupo_en_el_mapa(store, tmp_path):
    """Por eso la lista de nombres se saca de TODA la base.

    La persona puede no tener ni una arista —y entonces no aparece por ninguna
    parte del volcado— y estar nombrada igualmente en la descripción de un
    contrato que sí cabe. Mirar sólo las fichas publicadas no la habría visto.
    """
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    empresa = _entidad(store, "EMPRESA SL")
    _entidad(store, "Marta Solanes", "Person")  # sin ninguna arista
    _contrato(store, organo, empresa, "5000", "taller impartido por Marta Solanes")
    store.conn.commit()

    g = _exportado(store, tmp_path)
    assert "Solanes" not in json.dumps(g, ensure_ascii=False)


def test_tambien_se_tapa_en_el_extracto_de_procedencia(store, tmp_path):
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    empresa = _entidad(store, "EMPRESA SL")
    _entidad(store, "Marta Solanes", "Person")
    _arista(store, organo, empresa, "9000")
    doc = store.conn.execute(
        """
        INSERT INTO raw_documents (source_id, url, content_hash, media_type, retrieved_at, content)
        VALUES ('test', 'https://ejemplo.test/y', %s, 'application/json', now(), '{}'::bytea)
        RETURNING id
        """,
        ("e" * 64,),
    ).fetchone()
    store.conn.execute(
        """
        INSERT INTO provenance (entity_id, raw_document_id, extractor_version, excerpt)
        VALUES (%s, %s, 'test', 'representada por Marta Solanes ante el órgano')
        """,
        (empresa, doc["id"]),
    )
    store.conn.commit()

    g = _exportado(store, tmp_path)
    assert "Solanes" not in json.dumps(g, ensure_ascii=False)
    assert "ante el órgano" in json.dumps(g, ensure_ascii=False)


def test_el_volcado_dice_cuantas_menciones_tapo(store, tmp_path):
    """Si se tapa algo, se dice. Un hueco callado es indistinguible de no haberlo."""
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    empresa = _entidad(store, "EMPRESA SL")
    _entidad(store, "Marta Solanes", "Person")
    _contrato(store, organo, empresa, "5000", "curso de Marta Solanes y taller")
    store.conn.commit()

    g = _exportado(store, tmp_path)
    assert g["personasOmitidas"]["menciones_en_texto"] >= 1
    assert g["personasOmitidas"]["fichas"] >= 0


def test_una_empresa_con_nombre_parecido_no_se_tapa(store, tmp_path):
    """Un falso positivo aquí destroza texto legítimo, así que se mide.

    `Solanes SL` no es `Marta Solanes`: el patrón busca el nombre entero, no
    un apellido suelto, precisamente porque un apellido corriente aparece en
    topónimos y razones sociales.
    """
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    empresa = _entidad(store, "CONSTRUCCIONES SOLANES SL")
    _entidad(store, "Marta Solanes", "Person")
    _arista(store, organo, empresa, "9000")
    store.conn.commit()

    g = _exportado(store, tmp_path)
    assert "CONSTRUCCIONES SOLANES SL" in json.dumps(g, ensure_ascii=False)


@pytest.mark.parametrize(
    "nif",
    ["12345678Z", "X1234567L", "z7654321b", "B12345678", "A1234567X", "", "1234567Z"],
)
def test_el_sql_y_el_python_deciden_lo_mismo(store, nif):
    """La prueba de «esto es un identificador de persona» está escrita dos veces.

    En Python, para filtrar las fichas que se publican; y en SQL, porque la
    lista de nombres a tapar se saca de toda la base y traérsela entera a
    Python para descartarla aquí sería pasear decenas de miles de filas por la
    red en cada volcado. Dos definiciones de la misma regla se separan solas;
    esto lo impide.
    """
    fila = store.conn.execute(
        "SELECT (%s ~ %s) AS casa", (nif, _SQL_IDENTIFICADOR_PERSONAL)
    ).fetchone()
    assert bool(fila["casa"]) is es_identificador_personal(nif)


def test_una_ficha_que_solo_es_un_nombre_no_se_publica(store, tmp_path):
    """El caso real de la primera ejecución del tapado.

    Una `Company` sin NIF cuyo caption era, entero, el nombre y los apellidos
    de una persona. Las dos reglas anteriores la dejaban pasar —ni esquema
    `Person` ni identificador de persona física— y el tapado la convertía en
    un nodo llamado «(nombre retirado)»: pinchable, con sus cifras y sin decir
    de quién. Peor que no publicarla.
    """
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    empresa = _entidad(store, "EMPRESA SL")
    _entidad(store, "Marta Solanes", "Person")
    disfrazada = _entidad(store, "Marta Solanes", "Company")
    _arista(store, organo, empresa, "9000")
    _arista(store, organo, disfrazada, "4000")
    store.conn.commit()

    g = _exportado(store, tmp_path)
    crudo = json.dumps(g, ensure_ascii=False)
    assert disfrazada not in [n["id"] for n in g["nodes"]]
    assert "Solanes" not in crudo
    # Y no queda un nodo mudo en su lugar.
    assert MARCA_NOMBRE_RETIRADO not in [n["caption"] for n in g["nodes"]]
    # Su arista se va con ella, como con cualquier otra persona física.
    publicados = {n["id"] for n in g["nodes"]}
    for a in g["edges"]:
        assert a["source"] in publicados
        assert a["target"] in publicados


def test_una_sociedad_con_nombre_de_persona_sigue_publicandose(store, tmp_path):
    """El falso positivo que habría destrozado el mapa.

    «Construcciones Marta Solanes SL» lleva el nombre de quien la fundó y
    sigue siendo una sociedad: una parte contratante que hay que poder
    nombrar. Lo que se retira es la ficha que NO es más que un nombre.
    """
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    empresa = _entidad(store, "CONSTRUCCIONES MARTA SOLANES SL")
    _entidad(store, "Marta Solanes", "Person")
    _arista(store, organo, empresa, "9000")
    store.conn.commit()

    g = _exportado(store, tmp_path)
    captions = [n["caption"] for n in g["nodes"]]
    assert "CONSTRUCCIONES MARTA SOLANES SL" in captions


def test_tampoco_entra_en_el_indice(store, tmp_path):
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    empresa = _entidad(store, "EMPRESA SL")
    _entidad(store, "Marta Solanes", "Person")
    disfrazada = _entidad(store, "Marta Solanes", "Company")
    _arista(store, organo, empresa, "9000")
    _arista(store, organo, disfrazada, "4000")
    store.conn.commit()

    _exportado(store, tmp_path)
    indice = json.loads((tmp_path / "indice.json").read_text(encoding="utf-8"))
    assert "Solanes" not in json.dumps(indice, ensure_ascii=False)


# --- la clave estable: un enlace tiene que valer mañana --------------------
#
# El `id` de una entidad es un UUID que se genera en cada ingesta, y la base se
# levanta de cero todas las noches: el identificador de una entidad cambia a
# diario. Un enlace a una ficha dejaba de funcionar al día siguiente, y en un
# proyecto cuyo sentido es que alguien encuentre algo y lo pueda mandar, eso no
# es un detalle de implementación.


def test_cada_ficha_publica_su_clave_estable(store, tmp_path):
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    empresa = _entidad(store, "EMPRESA SL")
    _arista(store, organo, empresa, "9000")
    store.conn.commit()

    g = _exportado(store, tmp_path)
    for n in g["nodes"]:
        assert n["clave"], f"{n['caption']} sale sin clave"
        assert n["clave"] != n["id"], "la clave no puede ser el UUID, que cambia cada noche"


def test_la_clave_sobrevive_a_una_reingesta(store, tmp_path):
    """Lo que de verdad se comprueba: el UUID cambia y la clave no.

    Se simula la noche siguiente borrando las entidades y volviéndolas a crear
    con la misma `dedupe_key`, que es lo que hace el conector al reingerir.
    """
    claves = []
    for _ in range(2):
        store.conn.execute("TRUNCATE relationships, entities CASCADE")
        fila = store.conn.execute(
            """
            INSERT INTO entities (ftm_schema, caption, dedupe_key, properties)
            VALUES ('PublicBody', 'AYUNTAMIENTO', 'bdns:organo:1234', '{}'::jsonb)
            RETURNING id
            """
        ).fetchone()
        otra = _entidad(store, "EMPRESA SL")
        _arista(store, str(fila["id"]), otra, "9000")
        store.conn.commit()

        g = _exportado(store, tmp_path)
        ficha = next(n for n in g["nodes"] if n["caption"] == "AYUNTAMIENTO")
        claves.append((ficha["clave"], ficha["id"]))

    (clave1, id1), (clave2, id2) = claves
    assert clave1 == clave2 == "bdns:organo:1234"
    assert id1 != id2, "el escenario no vale si el UUID no cambia"


def test_el_indice_tambien_lleva_la_clave(store, tmp_path):
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    empresa = _entidad(store, "EMPRESA SL")
    _arista(store, organo, empresa, "9000")
    store.conn.commit()

    _exportado(store, tmp_path)
    indice = json.loads((tmp_path / "indice.json").read_text(encoding="utf-8"))
    assert indice["entidades"]
    for e in indice["entidades"]:
        assert e["clave"]


def test_ninguna_clave_de_persona_fisica_se_publica(store, tmp_path):
    """La clave de una persona física sería `nif:12345678Z`.

    No llega aquí —la ficha se retira tres pasos antes— pero conviene que
    alguien lo afirme, porque publicar la clave es publicar el DNI.
    """
    organo = _entidad(store, "AYUNTAMIENTO", "PublicBody")
    empresa = _entidad(store, "EMPRESA SL")
    store.conn.execute(
        """
        INSERT INTO entities (ftm_schema, caption, nif, dedupe_key, properties)
        VALUES ('Person', 'NOMBRE APELLIDO', '12345678Z', 'nif:12345678Z', '{}'::jsonb)
        """
    )
    _arista(store, organo, empresa, "9000")
    store.conn.commit()

    g = _exportado(store, tmp_path)
    crudo = json.dumps(g, ensure_ascii=False)
    assert "12345678Z" not in crudo
