"""Punto de entrada del worker de ingesta.

En fase 0 el worker sólo verifica que alcanza sus dependencias y se queda
esperando. La ejecución de conectores desde la cola llega en fase 2.
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time
from types import FrameType
from typing import TYPE_CHECKING

import structlog

from sinapsis_ingest import conectores, registry

if TYPE_CHECKING:
    from sinapsis_ingest import pipeline

log = structlog.get_logger()

_parando = False


def _manejar_senal(signum: int, _frame: FrameType | None) -> None:
    """Marca la parada para salir del bucle sin dejar trabajo a medias."""
    global _parando
    _parando = True
    log.info("señal recibida, parando", signal=signal.Signals(signum).name)


def comprobar_dependencias() -> dict[str, str]:
    """Comprueba Postgres y Redis. Devuelve {dependencia: "ok" | error}."""
    resultados: dict[str, str] = {}

    dsn = os.environ.get(
        "SINAPSIS_POSTGRES_DSN",
        "postgres://sinapsis:sinapsis@postgres:5432/sinapsis",
    )
    try:
        import psycopg

        with psycopg.connect(dsn, connect_timeout=5) as conn:
            conn.execute("SELECT 1")
        resultados["postgres"] = "ok"
    except Exception as exc:
        resultados["postgres"] = str(exc)

    redis_url = os.environ.get("SINAPSIS_REDIS_URL", "redis://redis:6379/0")
    try:
        import redis

        redis.Redis.from_url(redis_url, socket_connect_timeout=5).ping()
        resultados["redis"] = "ok"
    except Exception as exc:
        resultados["redis"] = str(exc)

    return resultados


def _ejecutar_conector(args: argparse.Namespace) -> int:
    """Ejecuta un conector una vez, de principio a fin."""
    from datetime import date

    from sinapsis_ingest import pipeline
    from sinapsis_ingest.store import Source, Store

    try:
        conector = registry.get(args.run)
    except KeyError as exc:
        log.error("conector desconocido", detalle=str(exc))
        return 2

    if not args.desde or not args.hasta:
        log.error("--run necesita --desde y --hasta")
        return 2
    try:
        desde = date.fromisoformat(args.desde)
        hasta = date.fromisoformat(args.hasta)
    except ValueError as exc:
        log.error("fecha inválida", detalle=str(exc))
        return 2

    dsn = os.environ.get(
        "SINAPSIS_POSTGRES_DSN",
        "postgres://sinapsis:sinapsis@postgres:5432/sinapsis",
    )

    with Store(dsn) as store:
        # La fuente debe existir antes que sus documentos: hay una FK.
        f = conectores.ficha(conector.source_id)
        store.upsert_source(Source(id=f.id, name=f.name, url=f.url, license=f.license))
        store.conn.commit()

        resultado = pipeline.ejecutar(
            store,
            conector,
            fecha_desde=desde,
            fecha_hasta=hasta,
            max_paginas=args.max_paginas,
        )
        store.conn.commit()

    log.info("ingesta completada", **resultado.resumen())
    return _codigo_salida(resultado)


# Por encima de esta proporción de registros con error, lo que falla no es un
# registro suelto: es que la fuente cambió de formato y el parser dejó de
# entenderla. Eso sí tiene que romper.
UMBRAL_ERRORES = 0.10


def _codigo_salida(resultado: pipeline.Resultado) -> int:
    """Distingue un hueco de un fallo.

    Antes bastaba UN registro con error para devolver 1 y tirar la ejecución
    entera. Con 2 páginas por conector no se notaba; al subir a 12 —unos
    12.000 registros— toparse con un registro raro pasó de improbable a casi
    seguro, y una instantánea buena se perdía por una fila mala.

    Eso contradice la regla del proyecto: si una fuente falla o cambió de
    formato, se registra el problema, se tolera el hueco y se sigue. Un hueco
    es un hueco; lo que no puede pasar desapercibido es que la fuente entera
    haya dejado de entenderse.

    Así que se rompe en dos casos, y sólo en dos:
      - no se ingirió nada, o
      - la proporción de registros con error supera el umbral, que es la
        firma de un cambio de formato y no de un dato suelto malo.
    """
    procesados = resultado.entidades + resultado.aristas + resultado.registros_descartados
    n_errores = len(resultado.errores)

    if procesados == 0:
        log.error("la ingesta no produjo nada", errores=n_errores)
        return 1

    if n_errores == 0:
        return 0

    proporcion = n_errores / max(procesados, 1)
    # Las primeras razones bastan para diagnosticar; volcarlas todas llenaría
    # el log de ruido idéntico.
    muestra = resultado.errores[:5]
    if proporcion > UMBRAL_ERRORES:
        log.error(
            "demasiados registros con error: ¿cambió el formato de la fuente?",
            errores=n_errores,
            procesados=procesados,
            proporcion=round(proporcion, 4),
            muestra=muestra,
        )
        return 1

    log.warning(
        "se toleraron huecos y se siguió",
        errores=n_errores,
        procesados=procesados,
        muestra=muestra,
    )
    return 0


def _dsn() -> str:
    return os.environ.get(
        "SINAPSIS_POSTGRES_DSN",
        "postgres://sinapsis:sinapsis@postgres:5432/sinapsis",
    )


def _exportar(ruta: str) -> int:
    """Vuelca el grafo a JSON para publicarlo sin base de datos."""
    from pathlib import Path

    from sinapsis_ingest.exportar import exportar
    from sinapsis_ingest.store import Store

    with Store(_dsn()) as store:
        resumen = exportar(store, Path(ruta))
    # Un volcado vacío no es un éxito: significa que la ingesta no trajo nada.
    if resumen["entidades"] == 0:
        log.error("el grafo exportado está vacío")
        return 1
    return 0


def _generar_candidatos() -> int:
    """Propone fusiones. Nunca las aplica: eso lo decide una persona."""
    from sinapsis_ingest import resolucion
    from sinapsis_ingest.store import Store

    with Store(_dsn()) as store:
        n = resolucion.generar_candidatos(store)
        store.conn.commit()
    log.info("candidatos encolados para revisión humana", n=n)
    return 0


def _listar_pendientes() -> int:
    from sinapsis_ingest import resolucion
    from sinapsis_ingest.store import Store

    with Store(_dsn()) as store:
        for c in resolucion.pendientes(store):
            print(f"{c.score:.3f}  {c.id}")
            print(f"        A: {c.izquierda_caption}")
            print(f"        B: {c.derecha_caption}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Arranca el worker. Devuelve el código de salida del proceso."""
    parser = argparse.ArgumentParser(prog="sinapsis-worker")
    parser.add_argument(
        "--check",
        action="store_true",
        help="comprueba dependencias, informa y sale (usado por la healthcheck)",
    )
    parser.add_argument(
        "--list-connectors",
        action="store_true",
        help="lista los conectores registrados y sale",
    )
    parser.add_argument(
        "--run",
        metavar="CONECTOR",
        help="ejecuta un conector una vez y sale (p. ej. --run bdns)",
    )
    parser.add_argument(
        "--desde",
        metavar="AAAA-MM-DD",
        help="fecha inicial para --run",
    )
    parser.add_argument(
        "--hasta",
        metavar="AAAA-MM-DD",
        help="fecha final para --run",
    )
    parser.add_argument(
        "--candidatos",
        action="store_true",
        help="genera candidatos de fusión en review_queue y sale (no fusiona nada)",
    )
    parser.add_argument(
        "--pendientes",
        action="store_true",
        help="lista los candidatos pendientes de revisión y sale",
    )
    parser.add_argument(
        "--exportar",
        metavar="RUTA",
        help="vuelca el grafo a un JSON estático y sale",
    )
    parser.add_argument(
        "--max-paginas",
        type=int,
        default=None,
        help="corta la paginación tras N páginas. Útil para probar",
    )
    args = parser.parse_args(argv)

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )

    conectores.registrar_todos()

    if args.list_connectors:
        for source_id in registry.available():
            print(source_id)
        return 0

    if args.exportar:
        return _exportar(args.exportar)

    if args.candidatos:
        return _generar_candidatos()

    if args.pendientes:
        return _listar_pendientes()

    if args.run:
        return _ejecutar_conector(args)

    if args.check:
        resultados = comprobar_dependencias()
        log.info("comprobación de dependencias", **resultados)
        return 0 if all(v == "ok" for v in resultados.values()) else 1

    signal.signal(signal.SIGTERM, _manejar_senal)
    signal.signal(signal.SIGINT, _manejar_senal)

    log.info("worker arrancado", conectores=registry.available())

    # Fase 0: sin cola todavía. Latimos para que el contenedor tenga un
    # proceso vivo y los logs muestren que sigue en pie.
    while not _parando:
        time.sleep(1)

    log.info("worker detenido")
    return 0


if __name__ == "__main__":
    sys.exit(main())
