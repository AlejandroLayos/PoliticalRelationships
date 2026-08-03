-- Clave de idempotencia para entidades.
--
-- 0001 dejó `entities` sin forma de reinsertar sin duplicar. El NIF sirve
-- cuando existe, pero muchos beneficiarios y organismos llegan sin él, y una
-- reejecución del conector creaba una entidad nueva cada vez.
--
-- `dedupe_key` unifica los dos casos:
--   con NIF  -> 'nif:B12345678'   (dos fuentes que ven el mismo NIF convergen
--                                  en la misma clave, que es justamente la
--                                  resolución determinista del invariante 4)
--   sin NIF  -> 'bdns:organo:1234' (identificador estable dentro de la fuente)
--
-- El índice único parcial sobre `nif` de 0001 se mantiene como segunda red.

BEGIN;

ALTER TABLE entities ADD COLUMN dedupe_key TEXT;

-- La tabla puede tener filas de pruebas locales; les damos una clave derivada
-- del id para poder poner el NOT NULL sin perder nada.
UPDATE entities SET dedupe_key = 'legacy:' || id::text WHERE dedupe_key IS NULL;

ALTER TABLE entities ALTER COLUMN dedupe_key SET NOT NULL;

CREATE UNIQUE INDEX entities_dedupe_key_idx ON entities (dedupe_key);

COMMENT ON COLUMN entities.dedupe_key IS
    'Clave estable de la entidad en su fuente. Hace idempotente la ingesta.';

COMMIT;
