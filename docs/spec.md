# Especificación de Sinapsis

Documento de referencia. Si el código contradice esto, gana este documento
hasta que se acuerde cambiarlo.

---

## 1. Objetivo

Hacer visible y auditable la red de financiación e influencia en la política
española, enlazando fuentes públicas dispersas en un único grafo navegable
donde cada hecho cita su documento original.

**No objetivos:** producir conclusiones, acusar, ni presentar inferencias como
hechos probados. Sinapsis muestra conexiones con su procedencia; interpretarlas
es del lector.

## 2. Invariantes

Las seis reglas que no se rompen. Están en el README y se repiten aquí porque
son el criterio de aceptación de cualquier cambio.

1. **Procedencia siempre.** Ningún hecho entra sin `raw_document` +
   `provenance`.
2. **Crudo inmutable.** `raw_documents` no se edita; lo derivado se recomputa.
3. **Ingesta idempotente** por `content_hash`.
4. **Resolución de entidades** determinista primero, con fusiones auditables y
   reversibles. El matching difuso nunca fusiona solo.
5. **Confianza explícita** en toda arista (`confidence`, `status`).
6. **Datos personales minimizados.**

## 3. Modelo de datos

Vocabulario [FollowTheMoney](adr/0002-followthemoney.md). Esquema en
`backend/migrations/0001_init.up.sql`.

### Entidades (`entities`)

`ftm_schema` admite esquemas FtM con `edge=False`: `Person`, `Company`,
`Organization`, `PublicBody`, `LegalEntity`, `Asset`, `Security`, `Position`,
`Contract`, `Project`, `CourtCase`, `Document`.

Campos propios sobre FtM:

- `nif` — identificador fiscal normalizado. Es la clave de la resolución
  determinista. Único entre entidades canónicas.
- `canonical_id` — si no es NULL, esta fila fue absorbida por otra. Nunca se
  borra una entidad fusionada: se marca, para poder deshacerlo.
- `dedupe_key` — clave estable que hace idempotente la ingesta. Con NIF
  conocido debe ser `nif:<NIF>`, de forma que dos fuentes que ven el mismo NIF
  converjan en la misma fila; sin NIF, un identificador estable dentro de la
  fuente (`bdns:organo:1234`).
- `geom` — punto geográfico opcional (PostGIS).

### Relaciones (`relationships`)

`ftm_schema` admite esquemas FtM con `edge=True`. Las direcciones son las
canónicas de FtM y no se negocian:

| Esquema | Origen → Destino | Uso en Sinapsis |
|---|---|---|
| `Payment` | payer → beneficiary | Subvenciones (BDNS) |
| `ContractAward` | contract → supplier | Adjudicaciones (PLACSP) |
| `Ownership` | owner → asset | Participaciones accionariales |
| `Directorship` | director → organization | Consejos de administración |
| `Occupancy` | holder → post | Cargos públicos, puertas giratorias |
| `Membership` | member → organization | Afiliaciones |
| `UnknownLink` | subject → object | Conexión observada, naturaleza incierta |

Campos propios:

- `confidence` — 0..1. **La API nunca lo omite.**
- `status` — `asserted` (lo dice la fuente), `inferred` (lo deducimos
  nosotros), `disputed`, `retracted`.
- `dedupe_key` — clave derivada de los campos identificadores en la fuente.
  Es lo que hace idempotente la ingesta a nivel de arista.

### Procedencia (`provenance`)

Enlaza una entidad **o** una arista (exactamente una, por `CHECK`) con el
`raw_document` que la sostiene, más el `extractor_version` que la produjo y un
`excerpt` citable.

## 4. Confianza y honestidad del dato

`status = 'inferred'` significa que la conexión la dedujimos nosotros y **nunca
puede presentarse igual que una afirmada por la fuente**. Esto se impone en la
capa API, no sólo en la interfaz: quien consuma la API en crudo debe recibir la
distinción. Una arista inferida sin `confidence` es un bug.

## 5. Resolución de entidades

El núcleo del proyecto. Orden estricto:

1. **Determinista por NIF.** Dos entidades con el mismo NIF normalizado son la
   misma. Fusión automática, registrada con `method = 'nif_exact'`.
2. **Matching difuso.** Genera candidatos en `review_queue` con su `score` y
   las `features` que lo motivaron. **No fusiona.**
3. **Revisión humana.** Un humano acepta o rechaza. La decisión va a
   `entity_resolution_decisions`.

Toda fusión es reversible: deshacerla rellena `reverted_at` en vez de borrar la
fila, para que el historial quede intacto.

**Precisión sobre exhaustividad.** Un falso positivo —fusionar dos empresas
distintas— produce una acusación falsa. Un falso negativo sólo produce un hueco.
No son errores simétricos y el sistema no los trata como tales.

## 6. Interfaz `Connector`

Definida en `ingest/sinapsis_ingest/connectors/base.py`. Tres etapas:

```
fetch     -> Iterator[RawDocument]     descarga bytes, no interpreta
parse     -> Iterator[ParsedRecord]    bytes -> registros estructurados
normalize -> entidades + aristas FtM   registros -> vocabulario FtM
```

La separación no es decorativa: es lo que permite arreglar un parser y
recomputar todo lo derivado desde el crudo ya guardado, sin volver a golpear la
fuente. Por eso `parse` debe ser una función pura de `(bytes, extractor_version)`
— si no lo es, los golden tests no significan nada.

Registro en `ingest/sinapsis_ingest/registry.py`.

## 7. Idempotencia

Dos niveles:

- **Documento:** `UNIQUE (source_id, content_hash)`. Va por fuente y no sólo
  por hash porque dos fuentes pueden servir bytes idénticos legítimamente, y
  colapsarlos perdería la procedencia de una.
- **Entidad y arista:** `UNIQUE (dedupe_key)`, derivada de los identificadores
  de la fuente.

El upsert de `raw_documents` usa `ON CONFLICT DO NOTHING` y una consulta
posterior, nunca `DO UPDATE`: el trigger de inmutabilidad rechaza cualquier
`UPDATE`, incluido el no-op que se usaría para recuperar el `RETURNING`. El
crudo es inmutable, y eso incluye al upsert.

Al reinsertar una entidad, las `properties` se **fusionan** (`||`) en vez de
sustituirse: dos fuentes aportan campos distintos de la misma empresa y la
segunda ingesta no debe borrar lo que trajo la primera.

## 8. Sincronización a Neo4j

Postgres → Neo4j, en un solo sentido. Neo4j es reconstruible: borrarlo entero y
repoblarlo debe dar el mismo grafo. Si algún dato existe sólo en Neo4j, es un
bug. Ver [ADR 0001](adr/0001-arquitectura.md).

## 9. API

Rutas actuales:

- `GET /healthz` — liveness. Devuelve `{"status":"ok"}` mientras el proceso
  sirva HTTP. **No consulta dependencias**: si lo hiciera, una caída de
  Postgres provocaría reinicios en bucle de un proceso sano.
- `GET /readyz` — readiness. Consulta las dependencias y devuelve 503 si alguna
  falla, para que el balanceador la saque del pool sin reiniciarla.

Previstas (fase 4): búsqueda de entidades, `GET /entity/{id}`, y
`GET /entity/{id}/neighbors?depth=n`. La API sirve **vecindarios**, no el grafo
entero: ver §11.

## 10. Fuentes

Ver [data-sources.md](data-sources.md).

## 11. Visualización

Grafo de fuerzas (Sigma.js + graphology, WebGL) con layout ForceAtlas2.

**El patrón es expansión de ego-red, no volcado completo.** El usuario busca
una entidad, ve su vecindario a 1-2 saltos y expande al hacer clic. Un
ForceAtlas2 con cien mil nodos es espectacular en una captura e inútil para
investigar; es la trampa estética que hay que evitar. Esto condiciona la API:
por eso hay `/entity/{id}/neighbors` y no `/graph/all`.

Las aristas con `status = 'inferred'` se dibujan visualmente distintas
(discontinuas) y la confianza es visible.

## 12. Datos personales y RGPD

El riesgo mayor del proyecto no es técnico. Publicar personas físicas e inferir
influencia expone simultáneamente a difamación y a incumplimiento del RGPD.

Reglas:

- **Minimización.** Sólo se persisten datos personales necesarios para el
  objetivo. Nada de direcciones particulares, DNI de particulares, datos de
  familiares no relevantes ni categorías especiales del art. 9 RGPD.
- **Personas físicas.** Por defecto la interfaz pública muestra personas
  jurídicas y cargos públicos. Una persona física aparece cuando ejerce
  función pública o representa a una entidad en un hecho documentado — y esa
  es la base de interés público (art. 6.1.e/f RGPD y LO 3/2018).
- **Base legal documentada** por fuente en `data-sources.md`.
- **Rectificación.** Canal público para solicitar corrección. Toda corrección
  se resuelve contra el documento original: si la fuente está mal, se marca la
  arista como `disputed` y se documenta, no se borra en silencio.
- **Retención.** El crudo se conserva porque es la prueba. Si un dato personal
  debe suprimirse, se suprime lo derivado y se registra la supresión.

## 13. Seguridad

- Nada de credenciales en el repositorio. `.env` está en `.gitignore`.
- Las contraseñas por defecto del compose son **sólo para desarrollo**.
- La API es de lectura pública; la escritura (revisión de fusiones) irá
  autenticada.

## 14. Despliegue

Docker Compose, local-first. El mismo fichero sirve en un VPS.

El frontend puede ir en Vercel (build estático). **El resto no**: Postgres,
Neo4j y Redis son servicios con estado, y el worker de ingesta corre durante
horas, muy por encima del límite de las funciones serverless.

## 15. Fases

Cada fase se completa y se verifican sus criterios antes de pasar a la
siguiente.

| Fase | Contenido | Criterio de aceptación |
|---|---|---|
| **0** | Andamiaje: compose, CI, API con `/healthz` | La pila levanta; `/healthz` da `{"status":"ok"}`; CI verde |
| **1** | Esquema + capa `store` con upserts idempotentes | Se inserta crudo, se deriva entidad y arista con procedencia, se recupera; reinsertar el mismo crudo no duplica |
| **2** | Conector BDNS end-to-end | El worker puebla entidades y aristas `Payment`; cada arista enlaza a su `raw_document`; reejecución idempotente; golden tests pasan ⚠️ *pendiente: golden test contra respuesta real* |
| **3** | Conector PLACSP (ATOM/CODICE) | Contratos y adjudicaciones ingeridos con procedencia |
| **4** | Resolución de entidades + sync a Neo4j + API de grafo | `review_queue` poblada; fusiones reversibles; `/entity/{id}/neighbors` responde |
| **5** | Frontend Vue + Sigma.js | Ego-red navegable con procedencia y confianza visibles |
| **6** | Más fuentes: Tribunal de Cuentas, BORME, lobbies, medios | Cada una con su golden test |

## 16. Tests

- Tests con cada pieza. Sin excepción.
- **Golden tests obligatorios en parsers de fuentes**: muestra real guardada →
  salida esperada. Los formatos oficiales cambian sin avisar y rompen los
  parsers en silencio; es la única forma de enterarse.
- Si una fuente cambia de formato o falla, **no se inventan datos**: se registra
  el problema, se tolera el hueco y se sigue.
