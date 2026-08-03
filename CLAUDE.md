# Contexto para agentes de código

Lee primero [docs/spec.md](docs/spec.md). Este fichero sólo añade lo operativo.

## Qué es esto

Sinapsis mapea financiación e influencia en la política española a partir de
fuentes públicas. El reto no es descargar datos, es **enlazarlos**: reconocer
que la misma empresa aparece con nombres distintos en BDNS, PLACSP, BORME y los
informes del Tribunal de Cuentas.

## Estructura

```
backend/    Go   — API HTTP (cmd/api, internal/)
  migrations/    — SQL con golang-migrate
ingest/     Python — conectores, parsers, resolución de entidades
docs/            — spec, fuentes, ADRs
```

Go y Python **no comparten código**. Se comunican por Postgres y Redis. Ver
[ADR 0003](docs/adr/0003-stack-poliglota.md).

## Invariantes que no se rompen

Están en [docs/spec.md §2](docs/spec.md). Resumen operativo: sin procedencia no
se persiste; el crudo no se edita; la ingesta es idempotente; el matching difuso
nunca fusiona solo; toda arista lleva `confidence` y `status`.

El esquema las hace cumplir con restricciones y triggers, no sólo con
convenciones. Si un test falla por una restricción, **casi siempre está mal el
código, no la restricción.**

## Cómo trabajar

- **Por fases** ([spec §15](docs/spec.md)). Completa una y verifica sus
  criterios antes de seguir. No las mezcles.
- **Ramas y PRs pequeños**, uno por paso lógico. Nada de push directo a `main`.
- **Tests con cada pieza.** En parsers de fuentes, golden tests obligatorios
  (muestra real guardada → salida esperada). Los formatos oficiales cambian sin
  avisar.
- **No inventes datos.** Si una fuente falla o cambió de formato, registra el
  problema, tolera el hueco, sigue.
- **Nada destructivo sin avisar**: borrar datos, reescribir historia de git, o
  cambiar un esquema ya migrado en un despliegue real.

## Comandos

```bash
make up          # levanta la pila
make health      # /healthz y /readyz
make test        # tests de Go y de Python
make lint        # linters de ambos
make help        # el resto
```

Sin Docker:

```bash
cd backend && go test ./...
cd ingest  && pytest        # requiere pkg-config y libicu-dev en el sistema
```

## Detalles que muerden

- **`Contract` es una entidad en FollowTheMoney, no una arista.** La arista de
  adjudicación es `ContractAward`. Hay un test
  (`ingest/tests/test_esquema_ftm.py`) que valida los `CHECK` del esquema
  contra la librería FtM; si añades un esquema, ese test te dirá si te has
  equivocado de lado.
- **pgx v5.10 exige Go >= 1.25.** La CI lo fija.
- **`followthemoney` compila PyICU desde fuente** y necesita `pkg-config` y
  `libicu-dev`. Está en el Dockerfile y en la CI.
- **`/healthz` no consulta dependencias** a propósito. Es liveness. La
  comprobación de dependencias está en `/readyz`.
- **`UNIQUE` de `raw_documents` va por `(source_id, content_hash)`**, no sólo
  por hash: dos fuentes pueden servir bytes idénticos legítimamente.

## Sensibilidad del proyecto

Esto publica datos que conectan personas y dinero público. El riesgo mayor no
es técnico sino legal y reputacional: difamación y RGPD. Ante la duda entre
mostrar un enlace dudoso u ocultarlo, **se oculta**; entre exhaustividad y
precisión, **precisión**. Un falso positivo es una acusación falsa; un falso
negativo es sólo un hueco. Ver [spec §12](docs/spec.md).
