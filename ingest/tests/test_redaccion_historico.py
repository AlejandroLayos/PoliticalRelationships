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


# --- un DNI es un dato personal esté pegado a lo que esté ------------------
#
# Quitar los nodos `Person` dejó limpio lo que estaba clasificado como
# persona. Pero en el historial quedaba una UTE —`Company`, con forma
# societaria explícita, clasificada con todo el criterio— cuyo NIF era el DNI
# de uno de sus socios. La regla de «esto es una empresa» funcionaba
# perfectamente y aun así se seguía publicando un DNI.


def test_le_quita_el_dni_a_una_empresa_sin_borrar_la_empresa(volcado):
    # La ficha se queda: una UTE adjudicataria de un contrato público es un
    # dato. Lo que no se publica es el identificador personal.
    volcado["nodes"].append(
        {"id": "ute", "schema": "Company", "caption": "UTE EJEMPLO", "nif": "12345678Z"}
    )
    salida, cuantas = redaccion.redactar(volcado)
    ute = next(n for n in salida["nodes"] if n["id"] == "ute")
    assert "nif" not in ute
    assert ute["caption"] == "UTE EJEMPLO"
    assert "12345678Z" not in json.dumps(salida, ensure_ascii=False)
    assert salida["redactado"]["identificadores_retirados"] == 1
    assert cuantas == 2  # la persona entera + el identificador


def test_tambien_quita_los_nie(volcado):
    volcado["nodes"].append(
        {"id": "x", "schema": "Company", "caption": "EMPRESA", "nif": "X1234567L"}
    )
    salida, _ = redaccion.redactar(volcado)
    assert "X1234567L" not in json.dumps(salida, ensure_ascii=False)


def test_no_toca_el_nif_de_una_empresa_de_verdad(volcado):
    salida, _ = redaccion.redactar(volcado)
    emp = next(n for n in salida["nodes"] if n["id"] == "emp")
    assert emp["nif"] == "B12345678"


def test_un_volcado_con_solo_un_dni_mal_puesto_tambien_se_redacta():
    # Sin ningún nodo `Person`, la primera versión decía «aquí no hay nada».
    datos = {
        "nodes": [
            {"id": "a", "schema": "PublicBody", "caption": "AYUNTAMIENTO"},
            {"id": "b", "schema": "Company", "caption": "UTE", "nif": "12345678Z"},
        ],
        "edges": [],
    }
    salida, cuantas = redaccion.redactar(datos)
    assert cuantas == 1
    assert "12345678Z" not in json.dumps(salida, ensure_ascii=False)
    assert len(salida["nodes"]) == 2


@pytest.mark.parametrize(
    "nif", ["12345678Z", "X1234567L", "Y7654321M", "z0000000A", " 12345678Z "]
)
def test_reconoce_los_identificadores_personales(nif):
    assert redaccion.es_identificador_personal(nif)


@pytest.mark.parametrize("nif", ["B12345678", "A08736431", "N0012345H", "W0172868B", "", None])
def test_no_confunde_un_nif_de_persona_juridica(nif):
    assert not redaccion.es_identificador_personal(nif)


# --- que el guion se pueda EJECUTAR ----------------------------------------


def test_el_guion_tiene_punto_de_entrada_y_se_ejecuta():
    """Lo importante no es que las funciones estén bien, es que se llamen.

    Al reescribir el final del fichero desapareció el bloque
    `if __name__ == "__main__"`. El guion se cargaba, definía todo y salía con
    código 0 sin imprimir nada: una herramienta de seguridad que en silencio
    no hace nada, y que además dice «todo correcto» al hacerlo.

    Los tests de `redactar()` seguían pasando todos.
    """
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, str(RUTA), "--ayuda-inexistente"],
        capture_output=True,
        text=True,
        check=False,
    )
    # argparse contesta a un argumento desconocido: prueba de que main() corre.
    assert r.returncode == 2
    assert "unrecognized arguments" in r.stderr or "argumentos" in r.stderr


def test_comprobar_desde_la_linea_de_ordenes_dice_algo():
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, str(RUTA), "--comprobar"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(RUTA.parents[1]),
    )
    # Encuentre o no algo, tiene que DECIRLO. El silencio era el fallo.
    assert r.stdout.strip(), "el guion no imprimió nada"
    assert r.returncode in (0, 1)


def test_el_informe_no_imprime_ningun_dato_personal():
    # Un informe sobre datos personales no puede ser otra copia de los datos
    # personales: se cuenta cuántos hay, no quiénes son.
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, str(RUTA), "--comprobar"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(RUTA.parents[1]),
    )
    import re as _re

    assert not _re.search(r"\b[0-9]{8}[A-Za-z]\b", r.stdout), "hay un DNI en el informe"
