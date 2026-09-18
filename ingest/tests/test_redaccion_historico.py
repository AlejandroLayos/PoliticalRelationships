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


def test_se_va_entera_la_ficha_identificada_con_un_dni(volcado):
    """Quitar sólo el identificador no bastaba.

    En el historial había una UTE identificada con el DNI de uno de sus socios
    y cuyo NOMBRE OFICIAL eran los nombres y apellidos de los dos. Retirado el
    DNI, seguían publicados los dos nombres.

    Si la fuente identificó a esa parte contratante con un DNI, es una persona
    física a efectos de publicar, y aquí sólo salen personas jurídicas.
    """
    volcado["nodes"].append(
        {
            "id": "ute",
            "schema": "Company",
            "caption": "UTE EJEMPLO (Nombre Apellido y Otro Apellido)",
            "nif": "12345678Z",
        }
    )
    salida, cuantas = redaccion.redactar(volcado)
    assert "ute" not in {n["id"] for n in salida["nodes"]}
    texto = json.dumps(salida, ensure_ascii=False)
    assert "12345678Z" not in texto
    assert "Nombre Apellido" not in texto
    assert cuantas == 2  # la persona y la UTE


def test_tambien_quita_los_nie(volcado):
    volcado["nodes"].append(
        {"id": "x", "schema": "Company", "caption": "EMPRESA", "nif": "X1234567L"}
    )
    salida, _ = redaccion.redactar(volcado)
    assert "X1234567L" not in json.dumps(salida, ensure_ascii=False)


def test_redacta_tambien_el_indice_que_tiene_otra_forma():
    """El grafo guarda las entidades en `nodes`; el índice, en `entidades`.

    Mirando sólo `nodes`, el índice pasaba entero por el filtro sin que nadie
    lo notara — con cuatro identificadores personales dentro, y un DNI que en
    el grafo ya se había retirado. Dos ficheros publicados, dos formas, una
    sola puerta.
    """
    indice = {
        "total": 3,
        "entidades": [
            {"id": "a", "schema": "PublicBody", "caption": "AYUNTAMIENTO"},
            {"id": "b", "schema": "Company", "caption": "EMPRESA SL", "nif": "B12345678"},
            {
                "id": "c",
                "schema": "Company",
                "caption": "UTE (Nombre Apellido)",
                "nif": "47877961B",
            },
        ],
    }
    salida, cuantas = redaccion.redactar(indice)
    assert cuantas == 1
    assert {e["id"] for e in salida["entidades"]} == {"a", "b"}
    assert "47877961B" not in json.dumps(salida, ensure_ascii=False)


def test_un_fichero_sin_entidades_no_se_toca():
    datos = {"algo": "otra cosa"}
    salida, cuantas = redaccion.redactar(datos)
    assert cuantas == 0
    assert salida == {"algo": "otra cosa"}


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
        "edges": [{"id": "e", "source": "a", "target": "b", "amount": "1000"}],
    }
    salida, cuantas = redaccion.redactar(datos)
    assert cuantas == 1
    assert "12345678Z" not in json.dumps(salida, ensure_ascii=False)
    assert len(salida["nodes"]) == 1
    # Y su arista se va con ella: no puede quedar colgando de un nodo ausente.
    assert salida["edges"] == []


@pytest.mark.parametrize("nif", ["12345678Z", "X1234567L", "Y7654321M", "z0000000A", " 12345678Z "])
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


def test_retira_por_id_aunque_en_ese_volcado_ya_no_se_note():
    """La señal puede estar en un fichero y el dato personal en otro.

    Pasó de verdad: una pasada anterior le quitó el DNI a esa UTE en el
    grafo y dejó la ficha publicada.
    Con el DNI fuera, esa ficha quedó indistinguible de una empresa normal —y
    con los nombres de los dos socios todavía en el nombre—. La señal seguía
    existiendo, pero en el índice, que es otro fichero.

    El id sí es estable entre ficheros y entre reescrituras.
    """
    grafo = {
        "nodes": [
            {"id": "org", "schema": "PublicBody", "caption": "AYUNTAMIENTO"},
            # Sin nif: aquí ya no se nota que es una persona.
            {"id": "ute", "schema": "Company", "caption": "UTE (Nombre Apellido y Otro)"},
        ],
        "edges": [{"id": "a", "source": "org", "target": "ute", "amount": "1000"}],
    }
    salida, cuantas = redaccion.redactar(grafo, {"ute"})
    assert cuantas == 1
    assert "Nombre Apellido" not in json.dumps(salida, ensure_ascii=False)
    assert salida["edges"] == []


def test_sin_ids_extra_se_comporta_igual_que_antes():
    grafo = {
        "nodes": [{"id": "x", "schema": "Company", "caption": "EMPRESA SL", "nif": "B1"}],
        "edges": [],
    }
    salida, cuantas = redaccion.redactar(grafo)
    assert cuantas == 0
    assert salida["nodes"][0]["caption"] == "EMPRESA SL"


def test_mira_los_dos_ficheros_publicados():
    # Mirar sólo el grafo dejó el índice entero sin filtrar, con un NIE dentro.
    assert any("indice.json" in r for r in redaccion.RUTAS)
    assert any("grafo.json" in r for r in redaccion.RUTAS)


def test_retira_los_captions_confirmados_a_mano():
    """Cuando una redacción parcial ha borrado su propia pista.

    La UTE cuyo nombre incluye el de sus dos socios tenía un DNI por NIF —lo
    que la delataba— pero una pasada anterior le quitó el NIF y dejó la ficha.
    Con la pista borrada quedó indistinguible de una empresa normal. Cruzar
    por id con el índice tampoco valía: los UUID se regeneran en cada ingesta.

    Lo único que queda es una lista explícita, y va por hash del nombre para
    que la lista no sea otra copia de los datos personales.
    """
    import hashlib

    caption = "UTE DE PRUEBA (Nombre Apellido y Otro Apellido)"
    h = hashlib.sha256(caption.encode()).hexdigest()
    original = redaccion.HASHES_CAPTION_PERSONAL
    redaccion.HASHES_CAPTION_PERSONAL = frozenset({h})
    try:
        datos = {
            "nodes": [
                {"id": "a", "schema": "PublicBody", "caption": "AYUNTAMIENTO"},
                {"id": "b", "schema": "Company", "caption": caption},
            ],
            "edges": [{"id": "e", "source": "a", "target": "b", "amount": "1"}],
        }
        salida, cuantas = redaccion.redactar(datos)
        assert cuantas == 1
        assert caption not in json.dumps(salida, ensure_ascii=False)
        assert salida["edges"] == []
    finally:
        redaccion.HASHES_CAPTION_PERSONAL = original


def test_la_lista_de_hashes_no_contiene_datos_personales():
    # Una lista de qué borrar por datos personales no puede ser, ella misma,
    # otra copia de esos datos.
    for h in redaccion.HASHES_CAPTION_PERSONAL:
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


def test_las_sustituciones_de_texto_no_nombran_a_nadie():
    """La lista de qué sustituir tampoco puede ser otra copia de los datos.

    El patrón casa la forma «UTE <topónimo> (…)» y conserva el topónimo, que
    es un nombre de lugar. Lo que se retira es el paréntesis, que es donde
    están los nombres de los socios.
    """
    import re

    for linea in redaccion.SUSTITUCIONES_TEXTO:
        patron, reemplazo = linea.split("==>")
        assert patron.startswith("regex:")
        rx = re.compile(patron[len("regex:") :])
        ejemplo = "cobró UTE PERAFITA (socios retirados) el contrato"
        salida = rx.sub(reemplazo, ejemplo)
        assert "Nombre Apellido" not in salida
        assert "socios retirados" in salida


def test_el_guion_sustituye_tambien_en_los_mensajes_de_commit():
    # Los mensajes de commit son parte del repositorio igual que los ficheros,
    # y no los toca el callback de blobs. Me pasó a mí: retiré los datos de los
    # ficheros de datos y los volví a publicar en la prosa que explicaba cómo
    # los había retirado.
    #
    # Va por `--message-callback` y no por `--replace-message`: esa opción no
    # sustituía nada, y la comprobación posterior paró tres reescrituras
    # seguidas antes de empujar.
    import inspect

    fuente = inspect.getsource(redaccion._ejecutar_filter_repo)
    assert "--message-callback" in fuente
    assert "sustituir_texto" in fuente


def test_no_corta_cuando_solo_quedan_sustituciones_de_texto():
    """El corte de «no hay nada que hacer» tiene que cubrir todo el trabajo.

    Miraba sólo las entidades dentro de los volcados. Cuando lo que quedaba
    eran nombres en el texto de los ficheros y en los mensajes de commit,
    decía «no hay nada que reescribir» y filter-repo —que es quien aplica las
    sustituciones— no llegaba a ejecutarse. El job terminaba en verde sin
    haber tocado nada.
    """
    import inspect

    fuente = inspect.getsource(redaccion.main)
    assert "SUSTITUCIONES_TEXTO" in fuente, (
        "el corte anticipado no tiene en cuenta las sustituciones de texto"
    )


def test_sustituir_texto_funciona_sobre_bytes_y_con_saltos_de_linea():
    """Se hace en Python, no con --replace-text / --replace-message.

    Esas dos opciones no sustituían nada en los mensajes de commit: tres
    ejecuciones seguidas reescribieron el historial y la comprobación
    posterior las paró a las tres antes de empujar. Con `regex:`, con
    literales, y con un fichero para cada una — las tres igual.

    El callback de blobs, que es Python, funcionaba a la primera.
    """
    plano = b"cobro UTE PERAFITA (socios retirados) el contrato"
    assert b"Nombre Apellido" not in redaccion.sustituir_texto(plano)
    assert b"socios retirados" in redaccion.sustituir_texto(plano)

    # Partido por un salto de línea, como queda al ajustar el ancho de un
    # párrafo en un mensaje de commit.
    partido = "«UTE PERAFITA (socios retirados)» en el grafo".encode()
    salida = redaccion.sustituir_texto(partido)
    assert b"Apellido" not in salida
    assert b"socios retirados" in salida


def test_sustituir_texto_no_toca_lo_que_no_casa():
    intacto = b"UTE ACCIONA CONSTRUCCION SA Y DRAGADOS SA (CIUDAD DE LA JUSTICIA)"
    assert redaccion.sustituir_texto(intacto) == intacto


def test_el_reemplazo_no_se_cuenta_como_pendiente():
    """El reemplazo CASA con el patrón que lo encontró.

    «UTE <topónimo> (socios retirados)» pasa el filtro de
    «UTE <topónimo> (cualquier cosa)». Buscando el patrón a secas, la
    comprobación daba positivo para siempre y se negaba a empujar un
    repositorio ya limpio: cinco ejecuciones seguidas. El borrado funcionaba
    desde hacía cuatro; lo roto era lo que decidía si había funcionado.
    """
    import re

    for linea in redaccion.SUSTITUCIONES_TEXTO:
        patron, reemplazo = linea.split("==>")
        rx = re.compile(patron[len("regex:") :])
        # La trampa, explícita: el reemplazo casa con su propio patrón.
        assert rx.search(reemplazo), "este test dejaría de comprobar nada"
        # Y aun así, aplicarlo dos veces no cambia nada.
        una = redaccion.sustituir_texto(b"x UTE PERAFITA (socios retirados) y")
        dos = redaccion.sustituir_texto(una)
        assert una == dos, "la sustitución no es idempotente"


def test_casa_aunque_el_salto_de_linea_caiga_antes_del_parentesis():
    """El sexto intento falló por un espacio literal en el patrón.

    Al ajustar el ancho de un párrafo, el nombre quedó partido justo entre el
    topónimo y el paréntesis: «UTE <topónimo>\\n   (nombres)». El patrón exigía
    un espacio ahí, así que encontraba una ocurrencia donde había dos, y la
    mitad sobrevivía a la reescritura sin que nada lo dijera.
    """
    partido = b"vease la\n   UTE PERAFITA\n   (Nombre Apellido, Otro Apellido)\n   y su NIF"
    salida = redaccion.sustituir_texto(partido)
    assert b"Apellido" not in salida, "el salto de linea salva el nombre"
    assert b"socios retirados" in salida

    # Y con tabulador, y sin separacion ninguna.
    for medio in (b"\t", b"", b"  \n\t"):
        uno = b"UTE PERAFITA" + medio + b"(Nombre Apellido)"
        assert b"Apellido" not in redaccion.sustituir_texto(uno), medio
