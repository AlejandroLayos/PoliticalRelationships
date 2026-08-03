# Poner Sinapsis en marcha en Vercel

Sin servidor propio, en tres pasos. Ver
[ADR 0004](docs/adr/0004-despliegue-vercel.md) para el porqué.

## 1. Base de datos (una vez, ~2 minutos)

En el panel de Vercel → tu proyecto → **Storage** → **Neon** (marketplace) →
crear base de datos.

La integración define `DATABASE_URL` sola. Neon soporta PostGIS y `pg_trgm`,
que es lo que necesita el esquema.

Región recomendada: `eu-central-1` o similar. Los datos son de fuentes
públicas españolas, pero acercar la base a los usuarios reduce latencia.

## 2. Dar acceso a GitHub Actions (una vez)

Copia la cadena de conexión de Neon y créala como secreto en GitHub:

**Settings → Secrets and variables → Actions → New repository secret**
- Nombre: `NEON_DATABASE_URL`
- Valor: la cadena de conexión (la de *pooled connection*)

## 3. Primera ingesta

**Actions → Ingesta → Run workflow.** Elige conector y fechas; con
`max_paginas = 3` tarda poco y sirve para comprobar que todo encaja.

El workflow aplica las migraciones, ejecuta el conector y deja un resumen con
los recuentos. A partir de ahí corre solo cada noche a las 04:15 UTC.

---

## Qué verás en cada momento

| Situación | La web muestra |
|---|---|
| Sin Neon conectado | Grafo de demostración, con banda de aviso |
| Neon conectado, sin ingesta | Aviso de «conectada pero vacía» + demostración |
| Tras la primera ingesta | Datos reales, sin banda |

La banda de aviso **no se puede cerrar** mientras se estén mostrando datos que
no vienen de una fuente real. Es deliberado.

## Lo que no va en Vercel, y por qué

- **La ingesta.** No por el límite de tiempo, sino porque reimplementar los
  conectores en JavaScript daría dos parsers de la misma fuente divergiendo en
  silencio. Corre en GitHub Actions con el código Python real.
- **Neo4j.** Nada lo consume todavía: la API de vecindarios va sobre Postgres.
  Sigue en `docker-compose.yml` para desarrollo local.

## Alternativa: servidor propio

```bash
cp .env.example .env
make up
make health
```

Levanta la pila entera —Postgres, Neo4j, Redis, la API en Go y el worker— con
Docker Compose. Es la opción si quieres travesías de grafo largas o no quieres
depender de terceros.
