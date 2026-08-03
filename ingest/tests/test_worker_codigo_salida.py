"""Tests del código de salida del worker.

Van en su propio fichero, y no junto al resto del pipeline, porque
`test_pipeline.py` se salta entero cuando no hay `SINAPSIS_TEST_POSTGRES_DSN`.
Estas comprobaciones son funciones puras y deciden si una instantánea buena se
tira a la basura: tienen que ejecutarse siempre, con base de datos o sin ella.
"""

from __future__ import annotations

from sinapsis_ingest import pipeline, worker


def _resultado(entidades=0, aristas=0, descartados=0, errores=()):
    r = pipeline.Resultado()
    r.entidades = entidades
    r.aristas = aristas
    r.registros_descartados = descartados
    r.errores = list(errores)
    return r


def test_sin_errores_sale_bien():
    assert worker._codigo_salida(_resultado(entidades=10, aristas=5)) == 0


def test_no_ingerir_nada_es_un_fallo():
    """Una instantánea vacía no es un hueco: es que no funcionó."""
    assert worker._codigo_salida(_resultado(errores=["x"])) == 1
    assert worker._codigo_salida(_resultado()) == 1


def test_un_registro_malo_entre_muchos_es_un_hueco_tolerable():
    """El caso que rompía la instantánea de 12 páginas.

    Con 2 páginas por conector nunca se topaba con un registro raro; con 12
    —unos 12.000 registros— era casi seguro, y un solo error tiraba la
    ejecución entera y con ella datos perfectamente buenos.
    """
    assert worker._codigo_salida(_resultado(entidades=600, aristas=600, errores=["uno"])) == 0


def test_demasiados_errores_si_rompen():
    """Una proporción alta no es mala suerte: es un cambio de formato."""
    r = _resultado(entidades=50, aristas=50, errores=[f"e{i}" for i in range(40)])
    assert worker._codigo_salida(r) == 1


def test_el_umbral_se_mide_sobre_lo_procesado_no_sobre_lo_persistido():
    # Los registros descartados también se procesaron: si no contaran, un
    # conector que descarta casi todo parecería tener una tasa de error enorme.
    r = _resultado(entidades=0, aristas=0, descartados=1000, errores=["uno"])
    assert worker._codigo_salida(r) == 0
