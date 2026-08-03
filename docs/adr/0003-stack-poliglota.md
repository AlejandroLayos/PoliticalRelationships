# ADR 0003 — Go para la API, Python para la ingesta

- **Estado:** aceptado
- **Fecha:** 2026-08-03

## Contexto

El proyecto tiene dos cargas de trabajo con perfiles muy distintos:

- **Servir la API.** Concurrencia, latencia baja, despliegue simple.
- **Ingerir fuentes.** Parsear PDFs y XML, OCR, extracción de entidades
  nombradas en español, deduplicación difusa. Procesos por lotes que tardan
  horas.

## Decisión

**`backend/` en Go. `ingest/` en Python. Se comunican sólo a través de Postgres
y de la cola en Redis** — no hay RPC ni librería compartida entre ellos.

## Razones

El ecosistema de la segunda carga de trabajo es Python y no está cerca de
serlo en Go: `followthemoney` y `nomenklatura` (resolución de entidades),
`splink` y `dedupe` (matching probabilístico), los `ingestors` de Aleph
(extracción de decenas de formatos documentales). Reimplementar eso en Go sería
reescribir años de trabajo especializado para no ganar nada.

Al mismo tiempo, Go da un binario estático sin dependencias para la API, que es
exactamente lo que quieres en un VPS pequeño.

La frontera es limpia porque el estado compartido es la base de datos. Ninguno
de los dos importa código del otro, así que la doble cadena de herramientas no
se contagia.

## Alternativas consideradas

**Todo en Go.** Un solo lenguaje, CI y despliegue más simples. Descartado por
el coste de reimplementar el parseo documental y el matching difuso.

**Todo en Python.** Máxima velocidad de desarrollo, sobre todo para un equipo
pequeño. Es la alternativa más defendible de las dos, y si el mantenimiento de
dos cadenas de herramientas resulta pesado, migrar la API a Python es un cambio
acotado. Se eligió Go por el perfil de la API y por el despliegue.

## Consecuencias

- Dos cadenas de herramientas: dos jobs de CI, dos Dockerfiles, dos ficheros de
  dependencias.
- Contribuir a una mitad no requiere conocer la otra.
- El esquema de la base de datos es el contrato de verdad entre ambas. Un
  cambio de esquema puede romper las dos, y ninguna prueba de tipos lo va a
  detectar: los tests de integración son la única red.
- PyICU, dependencia de `followthemoney`, se compila desde fuente y necesita
  `libicu-dev` y `pkg-config`. Está reflejado en `ingest/Dockerfile` y en la CI.
