# Sinapsis

Plataforma abierta que mapea las conexiones de financiación e influencia en la
política española: partidos, empresas, contratos públicos, subvenciones, grupos
de interés y medios.

Sinapsis **no genera datos**. Recolecta fuentes públicas, las normaliza,
resuelve identidades y expone las conexiones de forma navegable y auditable:
cada hecho enlaza al documento original del que salió.

> **Estado:** fase 0-1 (andamiaje y esquema). Todavía no ingiere datos reales.
> Ver [docs/spec.md §15](docs/spec.md) para el plan de fases.

## El problema no es descargar datos, es enlazarlos

Reconocer que «Construcciones García SL» del BORME, el donante de un informe
del Tribunal de Cuentas, el adjudicatario de un contrato en PLACSP y el
accionista de un medio son **la misma entidad** —pese a nombres distintos, NIFs
a veces ausentes y datos atrapados en PDFs— es el núcleo del proyecto. Toda la
arquitectura gira en torno a hacer eso bien, de forma trazable y reversible.

Por eso Sinapsis **prioriza la precisión sobre la exhaustividad**: preferimos
un mapa con huecos declarados a uno completo y falso.

## Qué no vas a encontrar aquí

Conviene decirlo antes que después:

- **Estructuras accionariales completas.** El BORME publica *actos*
  (constituciones, ceses, nombramientos), no participaciones. La nota simple
  con capital y socios es de pago, y la sentencia del TJUE C-37/20 restringió
  el acceso público a los registros de titularidad real en la UE. «Quién
  controla de verdad a esta empresa» tendrá huecos permanentes, y la interfaz
  los marca como tales.
- **Conclusiones.** Sinapsis muestra conexiones con su procedencia y su nivel
  de confianza. Interpretarlas es trabajo de quien las lee.

## Arquitectura

| Pieza | Tecnología | Papel |
|---|---|---|
| Verdad canónica | PostgreSQL + PostGIS | Dato fiable con procedencia auditable |
| Grafo | Neo4j | Proyección reconstruible desde Postgres; travesías y centralidad |
| API | Go (`backend/`) | Servicio HTTP |
| Ingesta | Python (`ingest/`) | Conectores, parsers y resolución de entidades |
| Cola | Redis | Trabajos de ingesta |
| Frontend | Vue 3 + Sigma.js | Grafo de fuerzas (fase 5) |

El modelo de datos es [FollowTheMoney](https://github.com/alephdata/followthemoney),
la ontología de OCCRP para periodismo de investigación. No es una preferencia
estética: permite cruzar datos españoles con OpenSanctions, Offshore Leaks y el
resto del ecosistema Aleph. Ver
[ADR 0002](docs/adr/0002-followthemoney.md).

Neo4j **nunca es fuente de verdad**. Si se corrompe o se borra, se reconstruye
desde Postgres.

## Invariantes

Son las reglas que no se rompen. El esquema las hace cumplir en la base de
datos, no sólo en el código.

1. **Procedencia siempre.** Ningún hecho entra sin `raw_document` +
   `provenance`. Si no se puede citar la fuente, no se persiste.
2. **Crudo inmutable.** `raw_documents` no se edita jamás — hay un trigger que
   rechaza el `UPDATE`. Todo lo derivado se recomputa desde el crudo, por eso
   los parsers llevan `extractor_version`.
3. **Ingesta idempotente** por `content_hash`. Reejecutar no duplica.
4. **Resolución de entidades:** determinista por NIF primero. El matching
   difuso propone candidatos en `review_queue` y **nunca fusiona solo**. Toda
   decisión queda en `entity_resolution_decisions`, auditable y reversible.
5. **Confianza explícita.** Toda arista lleva `confidence` y `status`. Nada
   inferido se presenta como probado, ni en la API ni en la interfaz.
6. **Datos personales minimizados** (RGPD). Ver [docs/spec.md §12](docs/spec.md).

## Arrancar en local

Necesitas Docker y Docker Compose.

```bash
git clone https://github.com/AlejandroLayos/PoliticalRelationships.git
cd PoliticalRelationships
cp .env.example .env      # opcional: hay defectos para todo
make up                   # levanta postgres, neo4j, redis, api y worker
make health               # debe responder {"status":"ok"}
```

Las migraciones se aplican solas al arrancar (el servicio `migrate` corre antes
que la API). `make help` lista el resto de comandos.

### Desarrollo sin Docker

```bash
cd backend && go test ./...       # API
cd ingest  && pip install -e ".[dev]" && pytest   # ingesta
```

El paquete Python compila PyICU, que necesita `pkg-config` y `libicu-dev`
instalados en el sistema.

## Contribuir

Es un proyecto de código libre y se agradece la ayuda, sobre todo en:

- **Conectores de fuentes nuevas.** Ver `ingest/sinapsis_ingest/connectors/base.py`
  para el contrato. Todo parser necesita un golden test con una muestra real.
- **Revisión de candidatos de fusión.** El trabajo humano de `review_queue` es
  lo que mantiene la precisión.
- **Correcciones.** Si un dato está mal, abre un issue con el enlace al
  documento original.

Ramas y PRs pequeños, un paso lógico cada uno. Los tests son obligatorios.

## Licencia

Código bajo [AGPL-3.0](LICENSE). Se eligió la variante *Affero* a propósito:
quien monte un servicio encima de Sinapsis tiene que publicar sus cambios.

Los datos derivados que publique el proyecto van bajo ODbL, y cada fuente
conserva la suya (ver [docs/data-sources.md](docs/data-sources.md)).
