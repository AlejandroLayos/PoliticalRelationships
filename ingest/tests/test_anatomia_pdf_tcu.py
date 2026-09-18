"""Tests del enmascarado de los PDF del Tribunal de Cuentas.

Estas funciones viven en `scripts/`, fuera del paquete, pero se prueban aquí
por una razón concreta: **son las que deciden qué se publica sobre personas**.
Los expedientes sancionadores del TdC nombran a particulares, y el informe que
genera ese script se commitea en un repositorio público.

Ya pasó una vez. La primera instantánea de BDNS publicó los nombres de unos
970 particulares que habían cobrado ayudas, porque nadie había comprobado que
no lo hiciera. Un fallo de este enmascarado tendría el mismo efecto con una
fuente más delicada todavía, así que la comprobación no puede quedarse en un
script que se ejecuta a mano: tiene que correr en la CI con todo lo demás.

Por eso `anatomia_pdf_tcu.py` importa pdfplumber de forma perezosa, dentro de
`analizar()`. Si lo importara arriba, este módulo no se podría cargar sin esa
dependencia —que la CI de `ingest` no instala— y el test se saltaría en
silencio justo donde más importa que no se salte.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from anatomia_pdf_tcu import (  # noqa: E402
    _es_cabecera,
    enmascarar,
    perfilar_columnas,
)

# --- enmascarado ----------------------------------------------------------


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("A10984433", "A99999999"),  # NIF de empresa
        ("12345678Z", "99999999A"),  # DNI
        ("JUAN PEREZ GOMEZ", "AAAA AAAAA AAAAA"),
        ("12/03/2019", "99/99/9999"),
        ("1.234.567,89 €", "9.999.999,99 €"),
        ("", ""),
        (None, ""),
    ],
)
def test_enmascarar_conserva_la_forma_y_no_el_dato(entrada, esperado):
    assert enmascarar(entrada) == esperado


def test_enmascarar_no_deja_pasar_ningun_digito_original():
    """Lo que importa: del original no puede sobrevivir ninguna cifra."""
    salida = enmascarar("Expediente SAN-2019/447 por 12.345,67 €")
    assert not any(c.isdigit() and c != "9" for c in salida)


def test_enmascarar_conserva_los_acentos_como_letra():
    # 'ó' es alfabética: debe salir como A, no colarse tal cual.
    assert enmascarar("Formación") == "AAAAAAAAA"


def test_enmascarar_recorta_las_celdas_largas():
    assert len(enmascarar("A" * 500)) == 40


# --- detección de cabecera ------------------------------------------------


def test_una_fila_de_etiquetas_es_cabecera():
    assert _es_cabecera(["Formación política", "Expediente", "Importe"])


@pytest.mark.parametrize(
    "fila",
    [
        ["PARTIDO X", "SAN 2019/3", "12.000,00"],
        ["JUAN PEREZ", "12345678Z", "500,00"],
        ["", "", ""],
        [None, None],
    ],
)
def test_una_fila_con_datos_nunca_es_cabecera(fila):
    """El caso que de verdad importa: no publicar datos creyéndolos etiquetas."""
    assert not _es_cabecera(fila)


# --- perfil de columnas ---------------------------------------------------


def test_el_perfil_publica_la_cabecera_pero_no_los_datos():
    tabla = [
        ["Formación política", "Expediente", "NIF", "Importe"],
        ["PARTIDO A", "SAN 2019/3", "G12345678", "12.000,00"],
        ["PARTIDO B", "SAN 2019/4", "G87654321", "3.500,00"],
    ]
    perfil = perfilar_columnas(tabla)

    assert perfil["cabecera"] == ["Formación política", "Expediente", "NIF", "Importe"]
    assert perfil["patrones"][2] == "A99999999"

    # Ningún valor real puede aparecer en la salida.
    plano = " ".join(perfil["patrones"])
    for prohibido in ("PARTIDO A", "G12345678", "12.000", "3.500"):
        assert prohibido not in plano


def test_sin_cabecera_reconocible_no_se_publica_ninguna_fila():
    """Si la primera fila lleva cifras, puede ser un dato: no se publica."""
    tabla = [
        ["JUAN PEREZ GOMEZ", "12345678Z", "500,00"],
        ["ANA LOPEZ RUIZ", "87654321X", "700,00"],
    ]
    perfil = perfilar_columnas(tabla)

    assert "cabecera" not in perfil
    plano = " ".join(perfil["patrones"])
    for prohibido in ("JUAN", "PEREZ", "ANA", "LOPEZ", "12345678", "87654321"):
        assert prohibido not in plano


def test_el_perfil_no_revienta_con_filas_desiguales():
    # pdfplumber devuelve filas cortas cuando una celda se fusiona.
    tabla = [["A", "B", "C"], ["x"], ["y", "z"]]
    perfil = perfilar_columnas(tabla)
    assert perfil["columnas"] == 3
    assert len(perfil["patrones"]) == 3


def test_tabla_vacia_da_perfil_vacio():
    assert perfilar_columnas([]) == {}
