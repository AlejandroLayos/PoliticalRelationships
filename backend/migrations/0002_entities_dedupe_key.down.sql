BEGIN;

DROP INDEX IF EXISTS entities_dedupe_key_idx;
ALTER TABLE entities DROP COLUMN IF EXISTS dedupe_key;

COMMIT;
