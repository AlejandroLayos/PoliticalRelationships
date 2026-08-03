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

import structlog

from sinapsis_ingest import conectores, registry

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
        store.upsert_source(
            Source(
                id="bdns",
                name="Base de Datos Nacional de Subvenciones",
                url="https://www.infosubvenciones.es",
                license="Reutilización libre (Ley 37/2007)",
            )
        )
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
    return 0 if not resultado.errores else 1


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
