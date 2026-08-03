# ADR 0002 — FollowTheMoney como modelo de datos

- **Estado:** aceptado
- **Fecha:** 2026-08-03

## Contexto

Hace falta un vocabulario para entidades («esto es una empresa, aquello un
organismo público») y para relaciones («esta empresa pagó a aquella», «esta
persona dirige aquella sociedad»).

La opción por defecto era inventar uno propio, ajustado a las fuentes
españolas.

## Decisión

**Adoptamos [FollowTheMoney](https://github.com/alephdata/followthemoney)
(FtM), la ontología de OCCRP para datos de investigación.**

Las columnas `ftm_schema` de `entities` y `relationships` guardan nombres de
esquema FtM: `Company`, `Person`, `PublicBody`, `Organization` para entidades;
`Payment`, `Ownership`, `Directorship`, `Membership`, `Contract`, `UnknownLink`
para aristas.

## Razones

**Precisión del vocabulario.** FtM distingue cosas que un esquema casero tiende
a colapsar. `Ownership` (participación accionarial, con porcentaje) y
`Directorship` (cargo en el consejo) son relaciones distintas con implicaciones
legales distintas. Los modelos improvisados acaban metiéndolas en un genérico
`RELATED_TO` que destruye la capacidad analítica justo donde importa.

**Interoperabilidad.** Es el modelo de Aleph, OpenSanctions y los datasets de
ICIJ. Un adjudicatario español con matriz en Luxemburgo tiene el otro lado del
hilo en esos conjuntos de datos. Con un esquema propio, ese cruce hay que
inventarlo; con FtM, existe.

**Ya modela la incertidumbre.** `UnknownLink` cubre exactamente el caso de una
conexión observada cuya naturaleza no está clara — que es la mitad de lo que
produce un pipeline de resolución de entidades.

## Consecuencias

- El vocabulario lo marca FtM, no nosotros. Cuando una fuente española no encaje
  limpiamente, se documenta el mapeo en el conector antes que forzar el modelo.
- Las restricciones `CHECK` de `0001_init.up.sql` enumeran los esquemas
  admitidos. Ampliarlos requiere migración, y eso es deliberado: obliga a pensar
  antes de meter un tipo nuevo.
- Nuestras columnas propias (`confidence`, `status`, `dedupe_key`, y toda la
  tabla `provenance`) son **añadidos** sobre FtM, no sustituciones. FtM no
  impone un modelo de procedencia tan estricto como el que queremos.
- Exportar a formato FtM debería ser casi directo. Es un objetivo explícito.
