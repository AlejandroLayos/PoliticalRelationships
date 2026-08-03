# ADR 0004 — Despliegue completo en Vercel

- **Estado:** aceptado
- **Fecha:** 2026-08-03
- **Sustituye parcialmente a:** [ADR 0001](0001-arquitectura.md) §Despliegue

## Contexto

El [ADR 0001](0001-arquitectura.md) daba por hecho un VPS con Docker Compose, y
en su momento se afirmó que en Vercel «sólo cabe el frontend». **Esa afirmación
era incorrecta** y conviene dejar por escrito por qué, para que nadie repita el
razonamiento:

- Se dio por bloqueante el agotamiento del pool de conexiones a Postgres desde
  funciones efímeras. Lo resuelve el driver serverless de Neon, que habla por
  HTTP y no mantiene sockets.
- Se dio por imposible tener Postgres con PostGIS y `pg_trgm`. Neon soporta
  ambas.
- Se dio por necesario Neo4j desde el principio. Acabó no siéndolo: la API de
  vecindarios se implementó sobre Postgres y **nada consume Neo4j todavía**.

Lo único que sigue sin caber es un proceso de ingesta de larga duración, y eso
es real: las funciones tienen minutos y una carga histórica tiene horas.

## Decisión

**Tres piezas, cada una donde encaja:**

| Pieza | Dónde | Por qué |
|---|---|---|
| Frontend | Vercel (estático) | Para lo que Vercel es bueno |
| API de lectura | Vercel Functions (`api/`, Node + Neon) | Efímeras, cacheadas en el borde |
| Base de datos | Neon (marketplace de Vercel) | PostGIS y `pg_trgm`, escala a cero |
| Ingesta | GitHub Actions programado | Necesita horas y el código Python real |

## Por qué la ingesta no va en Vercel

No es por el límite de tiempo, que se podría trocear. Es porque **reimplementar
los conectores en JavaScript significaría dos parsers de la misma fuente
divergiendo en silencio**, y los golden tests sólo cubrirían uno. El daño de
eso es peor que la comodidad de tenerlo todo en un sitio.

GitHub Actions ejecuta el paquete `sinapsis_ingest` tal cual, con sus tests, y
escribe a la misma Neon. Es gratis en repositorios públicos.

## Por qué hay dos implementaciones de la API

`backend/` (Go) y `api/` (Node) sirven el mismo contrato. Un binario de larga
vida y una función efímera son modelos de ejecución distintos, y Vercel sólo
admite el segundo; el primero sigue siendo la opción para autoalojarse.

Es duplicación real y tiene un coste: **si cambia el contrato hay que tocar las
dos**. Se acepta porque la superficie es pequeña —tres rutas de lectura— y
porque el esquema SQL sigue siendo el árbitro. Si crece, habrá que elegir una.

## Consecuencias

- Desplegar deja de requerir un VPS. El proyecto se puede levantar entero desde
  el navegador, que baja mucho la barrera para quien quiera reproducirlo.
- Neo4j queda **fuera del despliegue por defecto**. Sigue en el compose para
  desarrollo local y para cuando hagan falta travesías largas o centralidad.
- La ingesta pasa a ser por tandas diarias, no continua. Para datos que las
  fuentes publican con días de retraso, es irrelevante.
- Aparece una dependencia de dos proveedores (Vercel y GitHub) donde antes
  había una máquina. A cambio, ninguno de los dos guarda la verdad: el crudo y
  el esquema son reproducibles desde cero.
