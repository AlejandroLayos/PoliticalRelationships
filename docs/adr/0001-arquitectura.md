# ADR 0001 — Arquitectura general

- **Estado:** aceptado
- **Fecha:** 2026-08-03

## Contexto

Sinapsis debe ingerir fuentes públicas heterogéneas (JSON de APIs, XML CODICE,
PDFs escaneados), enlazarlas resolviendo identidades de entidades, y servir un
grafo navegable con procedencia auditable de cada hecho.

Dos exigencias tiran en direcciones opuestas:

- **Auditabilidad y corrección.** Cada arista debe poder justificarse citando
  un documento. Las fusiones de entidades deben ser reversibles. Esto pide un
  modelo relacional con restricciones fuertes.
- **Travesías de grafo.** «Todos los caminos entre este donante y este
  contrato», centralidad, detección de comunidades. Esto pide un motor de
  grafos.

## Decisión

**PostgreSQL + PostGIS es la única fuente de verdad. Neo4j es una proyección
reconstruible.**

La escritura va siempre a Postgres, donde viven las restricciones de
integridad, la procedencia y la bitácora de decisiones de resolución. Un
proceso de sincronización proyecta el resultado a Neo4j, que sirve las
consultas de travesía y alimenta la visualización.

Neo4j se puede borrar entero y reconstruir desde Postgres sin pérdida. Si
alguna vez hace falta un dato que sólo está en Neo4j, eso es un bug.

Componentes:

- **`backend/`** — Go. API HTTP.
- **`ingest/`** — Python. Conectores, parsers, resolución de entidades.
- **Redis** — cola de trabajos de ingesta y caché.
- **Docker Compose** — la pila entera, en local y en el VPS.

## Alternativas consideradas

**Sólo Neo4j.** Descartado: modelar procedencia y restricciones de integridad
en un grafo es posible pero incómodo, y perderíamos las garantías
transaccionales que hacen creíble la auditoría. Además convierte al motor de
grafos en un punto único de fallo con datos irrecuperables.

**Sólo Postgres, con CTEs recursivas.** Es una opción real y más simple: a la
escala prevista, una tabla de aristas bien indexada resuelve la mayoría de las
consultas. Se descartó porque las consultas de caminos arbitrarios y los
algoritmos de centralidad sobre grafos grandes son precisamente donde Postgres
sufre, y son el corazón del producto. Queda registrado que **si el coste
operativo de Neo4j supera su beneficio, retirarlo es un cambio local**: nada
depende de él como fuente.

**Una base de grafos embebida (SQLite + extensión, DuckDB).** Descartado por
inmadurez para el caso de uso y por no aportar sobre la opción anterior.

## Consecuencias

- Toda escritura pasa por Postgres. No se escribe en Neo4j desde la aplicación.
- Hay que mantener un proceso de sincronización y vigilar su retraso.
- Neo4j Community Edition es GPLv3, sin clustering ni RBAC. Como lo ejecutamos
  vía contenedor y no lo redistribuimos, no afecta a la licencia AGPL del
  proyecto.
- El esquema relacional es el contrato. Cambiarlo requiere migración.
