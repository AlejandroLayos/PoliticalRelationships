"""Tests de la redacción de personas físicas del historial de git.

El script reescribe el historial y eso no se ensaya dos veces: lo que se
comprueba aquí es la transformación del volcado, que es donde está todo el
riesgo. Un borrado a medias —el nombre fuera pero el id dentro, o la arista
todavía señalando al organismo y al importe— no borra nada útil.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[2] / "scripts" / "redactar_particulares_del_historico.py"
_spec = importlib.util.spec_from_file_location("redaccion", RUTA)
assert _spec and _spec.loader
redaccion = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(redaccion)


@pytest.fixture
def volcado() -> dict:
    return {
        "generado": "2026-08-03T19:18:01+00:00",
        "nodes": [
            {"id": "org", "schema": "PublicBody", "caption": "AYUNTAMIENTO"},
            {
                "id": "p1",
                "schema": "Person",
                "caption": "NOMBRE APELLIDO APELLIDO",
                "nif": "12345678Z",
                "properties": {"name": "NOMBRE APELLIDO APELLIDO"},
            },
            {"id": "emp", "schema": "Company", "caption": "EMPRESA SL", "nif": "B12345678"},
        ],
        "edges": [
            {"id": "a1", "source": "org", "target": "p1", "amount": "3000", "schema": "Payment"},
            {"id": "a2", "source": "org", "target": "emp", "amount": "9000", "schema": "Payment"},
        ],
        "provenance": {
            "p1": [{"source_id": "bdns", "excerpt": "concedido a NOMBRE APELLIDO APELLIDO"}],
            "emp": [{"source_id": "bdns", "excerpt": "concedido a EMPRESA SL"}],
        },
    }


def test_retira_a_la_persona_y_no_queda_rastro(volcado):
    salida, cuantas = redaccion.redactar(volcado)
    assert cuantas == 1
    texto = json.dumps(salida, ensure_ascii=False)
    assert "NOMBRE APELLIDO APELLIDO" not in texto
    assert "12345678Z" not in texto
    # Ni el identificador, que por sí solo no dice nada pero permite cruzar.
    assert '"p1"' not in texto


def test_la_arista_se_va_con_la_persona(volcado):
    # El par (organismo, importe) seguiría señalando a la persona aunque su
    # nombre no estuviera publicado.
    salida, _ = redaccion.redactar(volcado)
    assert [a["id"] for a in salida["edges"]] == ["a2"]


def test_la_procedencia_se_va_con_la_persona(volcado):
    # El extracto del documento original lleva el nombre dentro.
    salida, _ = redaccion.redactar(volcado)
    assert set(salida["provenance"]) == {"emp"}


def test_no_se_lleva_por_delante_a_nadie_mas(volcado):
    salida, _ = redaccion.redactar(volcado)
    assert {n["id"] for n in salida["nodes"]} == {"org", "emp"}
    assert "EMPRESA SL" in json.dumps(salida, ensure_ascii=False)


def test_el_grafo_sigue_siendo_coherente(volcado):
    salida, _ = redaccion.redactar(volcado)
    publicados = {n["id"] for n in salida["nodes"]}
    for a in salida["edges"]:
        assert a["source"] in publicados
        assert a["target"] in publicados


def test_deja_dicho_que_se_redactó(volcado):
    salida, _ = redaccion.redactar(volcado)
    assert salida["redactado"]["entidades_retiradas"] == 1
    assert "RGPD" in salida["redactado"]["motivo"]


def test_un_volcado_limpio_no_se_toca(volcado):
    volcado["nodes"] = [n for n in volcado["nodes"] if n["schema"] != "Person"]
    volcado["edges"] = [a for a in volcado["edges"] if a["target"] != "p1"]
    salida, cuantas = redaccion.redactar(volcado)
    assert cuantas == 0
    assert "redactado" not in salida


def test_la_pista_encuentra_las_dos_serializaciones():
    # Los volcados de agosto de 2026 iban compactos y los de septiembre con
    # separadores por defecto. Buscar sólo una forma daba «no hay nada que
    # borrar» sobre dos blobs con 27 personas cada uno.
    compacto = json.dumps({"schema": "Person"}, separators=(",", ":")).encode()
    espaciado = json.dumps({"schema": "Person"}).encode()
    assert redaccion.PISTA in compacto
    assert redaccion.PISTA in espaciado
