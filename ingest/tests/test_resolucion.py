"""Tests de la resolución de entidades.

Es la parte del proyecto donde un error hace más daño, así que lo que más se
prueba aquí no es que fusione, sino que **no fusione de más**: que nunca lo
haga sola, que no proponga pares con NIF distinto, y que toda fusión se pueda
deshacer dejando la base como estaba.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from sinapsis_ingest import resolucion
from sinapsis_ingest.store import Entity, Store

DSN = os.environ.get("SINAPSIS_TEST_POSTGRES_DSN", "")

pytestmark = pytest.mark.skipif(not DSN, reason="SINAPSIS_TEST_POSTGRES_DSN sin definir")


@pytest.fixture
def store():
    with Store(DSN) as st:
        migraciones = sorted(
            (Path(__file__).resolve().parents[2] / "backend" / "migrations").glob("*.up.sql")
        )
        fila = st.conn.execute(
            """SELECT EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='entities' AND column_name='caption_normalizado') AS ok"""
        ).fetchone()
        if not fila or not fila["ok"]:
            for f in migraciones:
                try:
                    st.conn.execute(f.read_text(encoding="utf-8"))
                    st.conn.commit()
                except Exception:
                    st.conn.rollback()
        st.conn.execute(
            """TRUNCATE provenance, entity_resolution_decisions, review_queue,
                        relationships, entities, raw_documents, sources CASCADE"""
        )
        st.conn.commit()
        yield st


def _empresa(store: Store, caption: str, key: str, nif: str = "", schema: str = "Company") -> str:
    return store.upsert_entity(Entity(ftm_schema=schema, caption=caption, dedupe_key=key, nif=nif))


# --- compatibilidad de esquemas -------------------------------------------


@pytest.mark.parametrize(
    ("a", "b", "esperado"),
    [
        ("Company", "Company", True),
        ("Company", "LegalEntity", True),
        ("Company", "Organization", True),
        ("Person", "Person", True),
        # Una persona nunca es una empresa: proponerlo sería ruido puro.
        ("Person", "Company", False),
        ("Person", "LegalEntity", False),
    ],
)
def test_esquemas_compatibles(a, b, esperado):
    assert resolucion.esquemas_compatibles(a, b) is esperado


# --- generación de candidatos ---------------------------------------------


def test_propone_nombres_parecidos(store):
    _empresa(store, "CONSTRUCCIONES GARCÍA, S.L.", "k1")
    _empresa(store, "Construcciones Garcia SL", "k2")
    store.conn.commit()

    assert resolucion.generar_candidatos(store) == 1
    store.conn.commit()

    cands = resolucion.pendientes(store)
    assert len(cands) == 1
    assert cands[0].score >= resolucion.UMBRAL_CANDIDATO


def test_no_propone_nombres_distintos(store):
    _empresa(store, "Construcciones García SL", "k1")
    _empresa(store, "Panadería Martínez SA", "k2")
    store.conn.commit()

    resolucion.generar_candidatos(store)
    store.conn.commit()
    assert resolucion.pendientes(store) == []


def test_nunca_propone_dos_nif_distintos(store):
    """Dos NIF distintos son prueba de que NO son la misma entidad."""
    _empresa(store, "Construcciones García SL", "nif:B11111111", nif="B11111111")
    _empresa(store, "Construcciones Garcia S.L.", "nif:B22222222", nif="B22222222")
    store.conn.commit()

    resolucion.generar_candidatos(store)
    store.conn.commit()
    assert resolucion.pendientes(store) == []


def test_si_propone_cuando_solo_una_tiene_nif(store):
    # Éste es el caso útil: la misma empresa vista con y sin identificador.
    _empresa(store, "Construcciones García SL", "nif:B11111111", nif="B11111111")
    _empresa(store, "Construcciones Garcia S.L.", "bdns:beneficiario:x")
    store.conn.commit()

    assert resolucion.generar_candidatos(store) == 1
    store.conn.commit()
    assert len(resolucion.pendientes(store)) == 1


def test_no_mezcla_personas_con_empresas(store):
    _empresa(store, "Antonio García Pérez", "k1", schema="Person")
    _empresa(store, "Antonio Garcia Perez SL", "k2", schema="Company")
    store.conn.commit()

    resolucion.generar_candidatos(store)
    store.conn.commit()
    assert resolucion.pendientes(store) == []


def test_generar_candidatos_es_idempotente(store):
    _empresa(store, "CONSTRUCCIONES GARCÍA, S.L.", "k1")
    _empresa(store, "Construcciones Garcia SL", "k2")
    store.conn.commit()

    resolucion.generar_candidatos(store)
    store.conn.commit()
    antes = len(resolucion.pendientes(store))

    resolucion.generar_candidatos(store)
    store.conn.commit()
    assert len(resolucion.pendientes(store)) == antes


def test_no_propone_entidades_ya_fusionadas(store):
    a = _empresa(store, "CONSTRUCCIONES GARCÍA, S.L.", "k1")
    b = _empresa(store, "Construcciones Garcia SL", "k2")
    store.conn.commit()
    resolucion.fusionar(store, kept_id=a, merged_id=b, method="manual_review", decided_by="test")
    store.conn.commit()

    resolucion.generar_candidatos(store)
    store.conn.commit()
    assert resolucion.pendientes(store) == []


def test_las_features_explican_la_propuesta(store):
    _empresa(store, "CONSTRUCCIONES GARCÍA, S.L.", "k1")
    _empresa(store, "Construcciones Garcia SL", "k2")
    store.conn.commit()
    resolucion.generar_candidatos(store)
    store.conn.commit()

    f = resolucion.pendientes(store)[0].features
    # Un revisor tiene que poder ver en qué se basó la propuesta.
    for clave in ("similitud_trigrama", "similitud_levenshtein", "mismo_esquema"):
        assert clave in f, f"falta la señal {clave} en las features"


# --- el matching difuso NUNCA fusiona solo --------------------------------


def test_generar_candidatos_no_fusiona_nada(store):
    a = _empresa(store, "CONSTRUCCIONES GARCÍA, S.L.", "k1")
    b = _empresa(store, "Construcciones Garcia SL", "k2")
    store.conn.commit()

    resolucion.generar_candidatos(store)
    store.conn.commit()

    for eid in (a, b):
        fila = store.conn.execute(
            "SELECT canonical_id FROM entities WHERE id = %s", (eid,)
        ).fetchone()
        assert fila is not None
        assert fila["canonical_id"] is None, "el matching difuso fusionó por su cuenta"

    n = store.conn.execute("SELECT count(*) AS n FROM entity_resolution_decisions").fetchone()
    assert n is not None and n["n"] == 0


# --- fusión ----------------------------------------------------------------


def test_fusionar_marca_pero_no_borra(store):
    a = _empresa(store, "Empresa A", "k1")
    b = _empresa(store, "Empresa A SL", "k2")
    store.conn.commit()

    resolucion.fusionar(store, kept_id=a, merged_id=b, method="manual_review", decided_by="ana")
    store.conn.commit()

    fila = store.conn.execute("SELECT canonical_id FROM entities WHERE id = %s", (b,)).fetchone()
    assert fila is not None
    assert str(fila["canonical_id"]) == a

    # La absorbida sigue existiendo: las aristas que la referencian siguen
    # siendo válidas y la fusión se puede deshacer.
    n = store.conn.execute("SELECT count(*) AS n FROM entities").fetchone()
    assert n is not None and n["n"] == 2


def test_fusionar_registra_la_decision(store):
    a = _empresa(store, "Empresa A", "k1")
    b = _empresa(store, "Empresa A SL", "k2")
    store.conn.commit()

    did = resolucion.fusionar(
        store, kept_id=a, merged_id=b, method="manual_review", decided_by="ana", score=0.9
    )
    store.conn.commit()

    fila = store.conn.execute(
        "SELECT kept_entity_id, merged_entity_id, decided_by, method, score, reverted_at "
        "FROM entity_resolution_decisions WHERE id = %s",
        (did,),
    ).fetchone()
    assert fila is not None
    assert str(fila["kept_entity_id"]) == a
    assert fila["decided_by"] == "ana"
    assert fila["reverted_at"] is None


def test_no_se_fusiona_consigo_misma(store):
    a = _empresa(store, "Empresa A", "k1")
    store.conn.commit()
    with pytest.raises(ValueError, match="a sí misma"):
        resolucion.fusionar(store, kept_id=a, merged_id=a, method="manual_review", decided_by="x")


def test_no_se_fusiona_dos_veces(store):
    a = _empresa(store, "Empresa A", "k1")
    b = _empresa(store, "Empresa A SL", "k2")
    c = _empresa(store, "Empresa A SLU", "k3")
    store.conn.commit()
    resolucion.fusionar(store, kept_id=a, merged_id=b, method="manual_review", decided_by="x")
    store.conn.commit()
    with pytest.raises(ValueError, match="ya estaba fusionada"):
        resolucion.fusionar(store, kept_id=c, merged_id=b, method="manual_review", decided_by="x")


def test_el_nif_se_traslada_a_la_entidad_conservada(store):
    """Perder el NIF de la absorbida rompería la convergencia futura."""
    sin_nif = _empresa(store, "Construcciones Garcia", "bdns:x")
    con_nif = _empresa(store, "CONSTRUCCIONES GARCÍA SL", "nif:B11111111", nif="B11111111")
    store.conn.commit()

    resolucion.fusionar(
        store, kept_id=sin_nif, merged_id=con_nif, method="manual_review", decided_by="ana"
    )
    store.conn.commit()

    fila = store.conn.execute("SELECT nif FROM entities WHERE id = %s", (sin_nif,)).fetchone()
    assert fila is not None
    assert fila["nif"] == "B11111111"


# --- reversibilidad --------------------------------------------------------


def test_deshacer_fusion_restaura_la_entidad(store):
    a = _empresa(store, "Empresa A", "k1")
    b = _empresa(store, "Empresa A SL", "k2")
    store.conn.commit()
    did = resolucion.fusionar(
        store, kept_id=a, merged_id=b, method="manual_review", decided_by="ana"
    )
    store.conn.commit()

    resolucion.deshacer_fusion(store, decision_id=did, reverted_by="luis")
    store.conn.commit()

    fila = store.conn.execute("SELECT canonical_id FROM entities WHERE id = %s", (b,)).fetchone()
    assert fila is not None
    assert fila["canonical_id"] is None


def test_deshacer_no_borra_la_decision(store):
    """El historial no puede mentir sobre lo que se decidió en su momento."""
    a = _empresa(store, "Empresa A", "k1")
    b = _empresa(store, "Empresa A SL", "k2")
    store.conn.commit()
    did = resolucion.fusionar(
        store, kept_id=a, merged_id=b, method="manual_review", decided_by="ana"
    )
    store.conn.commit()
    resolucion.deshacer_fusion(store, decision_id=did, reverted_by="luis")
    store.conn.commit()

    fila = store.conn.execute(
        """SELECT reverted_at, reverted_by, decided_by
           FROM entity_resolution_decisions WHERE id = %s""",
        (did,),
    ).fetchone()
    assert fila is not None
    assert fila["reverted_at"] is not None
    assert fila["reverted_by"] == "luis"
    assert fila["decided_by"] == "ana"


def test_deshacer_devuelve_el_nif_trasladado(store):
    """Si no, las dos quedarían canónicas con el mismo NIF y romperían el índice."""
    sin_nif = _empresa(store, "Construcciones Garcia", "bdns:x")
    con_nif = _empresa(store, "CONSTRUCCIONES GARCÍA SL", "nif:B11111111", nif="B11111111")
    store.conn.commit()
    did = resolucion.fusionar(
        store, kept_id=sin_nif, merged_id=con_nif, method="manual_review", decided_by="ana"
    )
    store.conn.commit()

    resolucion.deshacer_fusion(store, decision_id=did, reverted_by="luis")
    store.conn.commit()

    filas = store.conn.execute(
        "SELECT id, COALESCE(nif,'') AS nif FROM entities ORDER BY dedupe_key"
    ).fetchall()
    nifs = [f["nif"] for f in filas]
    assert nifs.count("B11111111") == 1, f"el NIF quedó duplicado o perdido: {nifs}"


def test_no_se_deshace_dos_veces(store):
    a = _empresa(store, "Empresa A", "k1")
    b = _empresa(store, "Empresa A SL", "k2")
    store.conn.commit()
    did = resolucion.fusionar(
        store, kept_id=a, merged_id=b, method="manual_review", decided_by="ana"
    )
    store.conn.commit()
    resolucion.deshacer_fusion(store, decision_id=did, reverted_by="luis")
    store.conn.commit()
    with pytest.raises(ValueError, match="ya estaba revertida"):
        resolucion.deshacer_fusion(store, decision_id=did, reverted_by="luis")


# --- flujo de revisión -----------------------------------------------------


def test_aceptar_candidato_fusiona_y_marca_la_cola(store):
    _empresa(store, "CONSTRUCCIONES GARCÍA, S.L.", "k1")
    _empresa(store, "Construcciones Garcia SL", "k2")
    store.conn.commit()
    resolucion.generar_candidatos(store)
    store.conn.commit()

    cand = resolucion.pendientes(store)[0]
    did = resolucion.resolver_candidato(store, candidato_id=cand.id, aceptar=True, decided_by="ana")
    store.conn.commit()

    assert did is not None
    fila = store.conn.execute(
        "SELECT status, resolved_by FROM review_queue WHERE id = %s", (cand.id,)
    ).fetchone()
    assert fila is not None
    assert fila["status"] == "merged"
    assert fila["resolved_by"] == "ana"
    assert resolucion.pendientes(store) == []


def test_rechazar_candidato_no_fusiona(store):
    a = _empresa(store, "CONSTRUCCIONES GARCÍA, S.L.", "k1")
    _empresa(store, "Construcciones Garcia SL", "k2")
    store.conn.commit()
    resolucion.generar_candidatos(store)
    store.conn.commit()

    cand = resolucion.pendientes(store)[0]
    did = resolucion.resolver_candidato(
        store, candidato_id=cand.id, aceptar=False, decided_by="ana"
    )
    store.conn.commit()

    assert did is None
    n = store.conn.execute("SELECT count(*) AS n FROM entity_resolution_decisions").fetchone()
    assert n is not None and n["n"] == 0
    fila = store.conn.execute("SELECT canonical_id FROM entities WHERE id = %s", (a,)).fetchone()
    assert fila is not None and fila["canonical_id"] is None


def test_no_se_resuelve_dos_veces(store):
    _empresa(store, "CONSTRUCCIONES GARCÍA, S.L.", "k1")
    _empresa(store, "Construcciones Garcia SL", "k2")
    store.conn.commit()
    resolucion.generar_candidatos(store)
    store.conn.commit()

    cand = resolucion.pendientes(store)[0]
    resolucion.resolver_candidato(store, candidato_id=cand.id, aceptar=False, decided_by="ana")
    store.conn.commit()
    with pytest.raises(ValueError, match="ya estaba"):
        resolucion.resolver_candidato(store, candidato_id=cand.id, aceptar=True, decided_by="ana")


# --- cadenas de fusión -----------------------------------------------------


def test_entidad_canonica_sigue_la_cadena(store):
    a = _empresa(store, "Empresa A", "k1")
    b = _empresa(store, "Empresa A SL", "k2")
    c = _empresa(store, "Empresa A SLU", "k3")
    store.conn.commit()

    # C absorbida por B, y luego B absorbida por A.
    resolucion.fusionar(store, kept_id=b, merged_id=c, method="manual_review", decided_by="x")
    resolucion.fusionar(store, kept_id=a, merged_id=b, method="manual_review", decided_by="x")
    store.conn.commit()

    assert resolucion.entidad_canonica(store, c) == a
    assert resolucion.entidad_canonica(store, b) == a
    assert resolucion.entidad_canonica(store, a) == a


def test_entidad_canonica_falla_con_entidad_inexistente(store):
    with pytest.raises(ValueError, match="no existe"):
        resolucion.entidad_canonica(store, "00000000-0000-0000-0000-000000000000")
