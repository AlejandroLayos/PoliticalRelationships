BEGIN;

DROP INDEX IF EXISTS entities_caption_norm_trgm_idx;
ALTER TABLE entities DROP COLUMN IF EXISTS caption_normalizado;
DROP FUNCTION IF EXISTS sinapsis_normalizar_nombre(TEXT);

-- Las extensiones no se retiran: pueden estar en uso por otro esquema.

COMMIT;
