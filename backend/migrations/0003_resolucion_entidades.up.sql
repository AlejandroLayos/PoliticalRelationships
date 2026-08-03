-- Soporte para la resolución de entidades.
--
-- El matching difuso no puede comparar todas las entidades contra todas: con
-- cientos de miles de filas eso es O(n²) y no termina. Se necesita *blocking*:
-- reducir de antemano los pares candidatos usando un índice.
--
-- Aquí se añade el nombre normalizado como columna generada —así ni Go ni
-- Python tienen que acordarse de rellenarla— y un índice de trigramas encima.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- `unaccent()` no es IMMUTABLE en su forma de un argumento porque depende del
-- diccionario por defecto, y una columna generada exige inmutabilidad. Pasar
-- el diccionario explícitamente sí lo es.
CREATE OR REPLACE FUNCTION sinapsis_normalizar_nombre(texto TEXT)
RETURNS TEXT
LANGUAGE sql
IMMUTABLE
STRICT
PARALLEL SAFE
AS $$
    SELECT trim(regexp_replace(
        lower(unaccent('unaccent', texto)),
        '[^a-z0-9]+', ' ', 'g'
    ))
$$;

COMMENT ON FUNCTION sinapsis_normalizar_nombre IS
    'Minúsculas, sin acentos y sin puntuación. Base del blocking de candidatos.';

ALTER TABLE entities
    ADD COLUMN caption_normalizado TEXT
    GENERATED ALWAYS AS (sinapsis_normalizar_nombre(caption)) STORED;

CREATE INDEX entities_caption_norm_trgm_idx
    ON entities USING gin (caption_normalizado gin_trgm_ops);

COMMENT ON COLUMN entities.caption_normalizado IS
    'Nombre normalizado, generado. No se escribe a mano.';

COMMIT;
