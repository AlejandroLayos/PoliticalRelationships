"""Resolución de entidades: el núcleo de Sinapsis.

Reconocer que "Construcciones García SL" del BORME, el adjudicatario de un
contrato en PLACSP y el beneficiario de una subvención en BDNS son la *misma*
entidad es de lo que va el proyecto. Y es también donde un error hace más daño:

    Un falso positivo —fusionar dos empresas distintas— produce una acusación
    falsa. Un falso negativo sólo produce un hueco.

Por eso el orden es estricto (spec §5):

1. **Determinista por NIF.** Lo impone el esquema: el índice único parcial
   sobre `nif` hace que dos entidades canónicas no puedan compartirlo. Ocurre
   en el momento del upsert, sin intervención de este módulo.
2. **Matching difuso.** Genera candidatos en `review_queue` con su puntuación
   y las razones. **Nunca fusiona.**
3. **Revisión humana.** Acepta o rechaza. La decisión queda en
   `entity_resolution_decisions`, auditable y reversible.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import structlog
from rigour.text.distance import levenshtein_similarity

from sinapsis_ingest.store import Store

log = structlog.get_logger()

# Por debajo de esto ni se propone: revisar candidatos malos cansa al revisor
# y un revisor cansado acepta cosas que no debería.
UMBRAL_CANDIDATO = 0.62

# Esquemas FtM que pueden ser la misma entidad. `LegalEntity` es el padre de
# `Company` y `Organization`, así que es compatible con ambos; una `Person`
# nunca es una `Company`.
_COMPATIBLES: dict[str, set[str]] = {
    "Company": {"Company", "Organization", "LegalEntity", "PublicBody"},
    "Organization": {"Organization", "Company", "LegalEntity", "PublicBody"},
    "PublicBody": {"PublicBody", "Organization", "LegalEntity"},
    "LegalEntity": {"LegalEntity", "Company", "Organization", "PublicBody"},
    "Person": {"Person"},
}


def esquemas_compatibles(a: str, b: str) -> bool:
    """True si dos esquemas FtM podrían describir la misma entidad."""
    return b in _COMPATIBLES.get(a, {a})


@dataclass
class Candidato:
    id: str
    izquierda_id: str
    derecha_id: str
    izquierda_caption: str
    derecha_caption: str
    score: float
    features: dict[str, Any]


def _puntuar(
    izq: dict[str, Any], der: dict[str, Any], similitud_trgm: float
) -> tuple[float, dict[str, Any]]:
    """Combina señales en una puntuación, dejando por escrito el porqué.

    Las `features` se guardan en la cola: un revisor tiene que poder ver en qué
    se basó la propuesta, y una puntuación sin explicación no es auditable.
    """
    nombre_izq = izq["caption_normalizado"] or ""
    nombre_der = der["caption_normalizado"] or ""
    lev = levenshtein_similarity(nombre_izq, nombre_der)

    mismo_esquema = izq["ftm_schema"] == der["ftm_schema"]
    uno_sin_nif = bool(izq["nif"]) != bool(der["nif"])

    # El trigrama capta reordenaciones y abreviaturas; la distancia de edición
    # penaliza los cambios de letras. Promediarlas es más estable que fiarse
    # de una sola.
    score = 0.6 * similitud_trgm + 0.4 * lev
    if mismo_esquema:
        score = min(1.0, score + 0.05)

    features = {
        "similitud_trigrama": round(float(similitud_trgm), 4),
        "similitud_levenshtein": round(float(lev), 4),
        "mismo_esquema": mismo_esquema,
        "esquema_izquierda": izq["ftm_schema"],
        "esquema_derecha": der["ftm_schema"],
        "solo_uno_tiene_nif": uno_sin_nif,
        "nombre_izquierda": nombre_izq,
        "nombre_derecha": nombre_der,
    }
    return round(min(1.0, max(0.0, score)), 3), features


def generar_candidatos(store: Store, *, umbral: float = UMBRAL_CANDIDATO, limite: int = 500) -> int:
    """Busca pares parecidos y los encola para revisión humana.

    Devuelve cuántos candidatos nuevos se encolaron. **No fusiona nada.**
    """
    # Bloqueo por índice de trigramas: sin esto sería O(n²) y no terminaría.
    # El umbral del operador `%` se baja un poco respecto al de aceptación para
    # que el filtro fino de Python tenga margen.
    # `SET` no admite parámetros; `set_config` sí, y con is_local=true el
    # cambio se deshace al terminar la transacción en vez de contaminar la
    # sesión entera.
    store.conn.execute(
        "SELECT set_config('pg_trgm.similarity_threshold', %s, true)",
        (str(max(0.3, umbral - 0.2)),),
    )

    filas = store.conn.execute(
        """
        SELECT a.id  AS a_id, a.caption AS a_caption, a.ftm_schema AS a_schema,
               COALESCE(a.nif,'') AS a_nif, a.caption_normalizado AS a_norm,
               b.id  AS b_id, b.caption AS b_caption, b.ftm_schema AS b_schema,
               COALESCE(b.nif,'') AS b_nif, b.caption_normalizado AS b_norm,
               similarity(a.caption_normalizado, b.caption_normalizado) AS sim
        FROM entities a
        JOIN entities b
          ON a.id < b.id
         AND a.caption_normalizado %% b.caption_normalizado
        WHERE a.canonical_id IS NULL
          AND b.canonical_id IS NULL
          AND a.caption_normalizado <> ''
          AND b.caption_normalizado <> ''
          -- Dos NIF distintos son prueba de que NO son la misma entidad.
          -- Proponerlas sería pedirle al revisor que se equivoque.
          AND NOT (a.nif IS NOT NULL AND b.nif IS NOT NULL AND a.nif <> b.nif)
          -- Ya resuelto o ya encolado.
          AND NOT EXISTS (
              SELECT 1 FROM review_queue q
              WHERE q.left_entity_id = a.id AND q.right_entity_id = b.id
          )
        ORDER BY sim DESC
        LIMIT %s
        """,
        (limite,),
    ).fetchall()

    encolados = 0
    for f in filas:
        izq = {
            "ftm_schema": f["a_schema"],
            "nif": f["a_nif"],
            "caption_normalizado": f["a_norm"],
        }
        der = {
            "ftm_schema": f["b_schema"],
            "nif": f["b_nif"],
            "caption_normalizado": f["b_norm"],
        }
        if not esquemas_compatibles(f["a_schema"], f["b_schema"]):
            continue

        score, features = _puntuar(izq, der, f["sim"])
        if score < umbral:
            continue

        # El CHECK del esquema exige left < right.
        store.conn.execute(
            """
            INSERT INTO review_queue (left_entity_id, right_entity_id, score, features)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (f["a_id"], f["b_id"], score, json.dumps(features)),
        )
        encolados += 1

    log.info("candidatos generados", encolados=encolados, examinados=len(filas))
    return encolados


def pendientes(store: Store, *, limite: int = 50) -> list[Candidato]:
    """Candidatos sin resolver, los más probables primero."""
    filas = store.conn.execute(
        """
        SELECT q.id, q.left_entity_id, q.right_entity_id, q.score, q.features,
               a.caption AS a_caption, b.caption AS b_caption
        FROM review_queue q
        JOIN entities a ON a.id = q.left_entity_id
        JOIN entities b ON b.id = q.right_entity_id
        WHERE q.status = 'pending'
        ORDER BY q.score DESC
        LIMIT %s
        """,
        (limite,),
    ).fetchall()
    return [
        Candidato(
            id=str(f["id"]),
            izquierda_id=str(f["left_entity_id"]),
            derecha_id=str(f["right_entity_id"]),
            izquierda_caption=f["a_caption"],
            derecha_caption=f["b_caption"],
            score=float(f["score"]),
            features=f["features"],
        )
        for f in filas
    ]


def fusionar(
    store: Store,
    *,
    kept_id: str,
    merged_id: str,
    method: str,
    decided_by: str,
    score: float | None = None,
    evidence: dict[str, Any] | None = None,
) -> str:
    """Marca `merged_id` como absorbida por `kept_id`. Devuelve el id de la decisión.

    La entidad absorbida **no se borra**: se le pone `canonical_id`. Así la
    fusión es reversible y las aristas que la referencian siguen siendo válidas.
    """
    if kept_id == merged_id:
        raise ValueError("una entidad no puede absorberse a sí misma")

    with store.transaction():
        filas = store.conn.execute(
            "SELECT id, canonical_id, nif FROM entities WHERE id IN (%s, %s)",
            (kept_id, merged_id),
        ).fetchall()
        por_id = {str(f["id"]): f for f in filas}
        if len(por_id) != 2:
            raise ValueError("alguna de las dos entidades no existe")
        if por_id[kept_id]["canonical_id"] is not None:
            raise ValueError("la entidad que se conserva ya fue absorbida por otra")
        if por_id[merged_id]["canonical_id"] is not None:
            raise ValueError("la entidad absorbida ya estaba fusionada")

        # Si la absorbida aportaba el NIF y la que se conserva no lo tenía, se
        # traslada: perderlo rompería la convergencia determinista futura. El
        # índice único parcial no se queja porque la absorbida deja de contar.
        nif_propagado = False
        nif_absorbida = por_id[merged_id]["nif"]
        if nif_absorbida and not por_id[kept_id]["nif"]:
            store.conn.execute(
                "UPDATE entities SET canonical_id = %s WHERE id = %s", (kept_id, merged_id)
            )
            store.conn.execute(
                "UPDATE entities SET nif = %s WHERE id = %s", (nif_absorbida, kept_id)
            )
            nif_propagado = True
        else:
            store.conn.execute(
                "UPDATE entities SET canonical_id = %s WHERE id = %s", (kept_id, merged_id)
            )

        pruebas = dict(evidence or {})
        pruebas["nif_propagado"] = nif_propagado

        fila = store.conn.execute(
            """
            INSERT INTO entity_resolution_decisions
                (kept_entity_id, merged_entity_id, method, score, evidence, decided_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (kept_id, merged_id, method, score, json.dumps(pruebas), decided_by),
        ).fetchone()
        assert fila is not None

    log.info("entidades fusionadas", conservada=kept_id, absorbida=merged_id, metodo=method)
    return str(fila["id"])


def deshacer_fusion(store: Store, *, decision_id: str, reverted_by: str) -> None:
    """Revierte una fusión. La decisión no se borra: se marca como revertida.

    Borrar la fila haría que el historial mintiera sobre lo que se decidió en
    su momento, y ese historial es justamente lo que hace auditable el sistema.
    """
    with store.transaction():
        fila = store.conn.execute(
            """
            SELECT kept_entity_id, merged_entity_id, evidence, reverted_at
            FROM entity_resolution_decisions WHERE id = %s
            """,
            (decision_id,),
        ).fetchone()
        if fila is None:
            raise ValueError(f"no existe la decisión {decision_id}")
        if fila["reverted_at"] is not None:
            raise ValueError("esa fusión ya estaba revertida")

        # El orden importa. Si al fusionar se trasladó el NIF, hay que quitarlo
        # de la que se conservó ANTES de devolver la absorbida: en cuanto ésta
        # deja de tener `canonical_id` vuelve a entrar en el índice único
        # parcial de `nif`, y las dos lo tendrían a la vez.
        evidencia = fila["evidence"] or {}
        if evidencia.get("nif_propagado"):
            store.conn.execute(
                "UPDATE entities SET nif = NULL WHERE id = %s", (fila["kept_entity_id"],)
            )

        store.conn.execute(
            "UPDATE entities SET canonical_id = NULL WHERE id = %s",
            (fila["merged_entity_id"],),
        )

        store.conn.execute(
            """
            UPDATE entity_resolution_decisions
            SET reverted_at = now(), reverted_by = %s
            WHERE id = %s
            """,
            (reverted_by, decision_id),
        )

    log.info("fusión revertida", decision=decision_id, por=reverted_by)


def resolver_candidato(
    store: Store, *, candidato_id: str, aceptar: bool, decided_by: str
) -> str | None:
    """Aplica la decisión humana sobre un candidato de `review_queue`.

    Devuelve el id de la decisión de fusión si se aceptó, o None si se rechazó.
    """
    fila = store.conn.execute(
        """SELECT left_entity_id, right_entity_id, score, features, status
           FROM review_queue WHERE id = %s""",
        (candidato_id,),
    ).fetchone()
    if fila is None:
        raise ValueError(f"no existe el candidato {candidato_id}")
    if fila["status"] != "pending":
        raise ValueError(f"el candidato ya estaba {fila['status']}")

    decision_id = None
    if aceptar:
        decision_id = fusionar(
            store,
            kept_id=str(fila["left_entity_id"]),
            merged_id=str(fila["right_entity_id"]),
            method="manual_review",
            decided_by=decided_by,
            score=float(fila["score"]),
            evidence={"review_queue_id": candidato_id, "features": fila["features"]},
        )

    store.conn.execute(
        """
        UPDATE review_queue
        SET status = %s, resolved_at = now(), resolved_by = %s
        WHERE id = %s
        """,
        ("merged" if aceptar else "rejected", decided_by, candidato_id),
    )
    return decision_id


def entidad_canonica(store: Store, entity_id: str) -> str:
    """Sigue la cadena de fusiones hasta la entidad viva.

    Las cadenas se dan cuando A absorbe a B y luego C absorbe a A.
    """
    actual = entity_id
    for _ in range(16):  # cota: una cadena más larga es un bug o un ciclo
        fila = store.conn.execute(
            "SELECT canonical_id FROM entities WHERE id = %s", (actual,)
        ).fetchone()
        if fila is None:
            raise ValueError(f"no existe la entidad {entity_id}")
        if fila["canonical_id"] is None:
            return actual
        actual = str(fila["canonical_id"])
    raise RuntimeError(f"cadena de fusiones demasiado larga desde {entity_id}")
