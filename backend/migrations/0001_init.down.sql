-- Revierte 0001_init.
--
-- Orden inverso a las dependencias. No borramos las extensiones postgis ni
-- pgcrypto: pueden estar en uso por otro esquema de la misma base.

BEGIN;

DROP TRIGGER IF EXISTS relationships_updated_at ON relationships;
DROP TRIGGER IF EXISTS entities_updated_at ON entities;
DROP TRIGGER IF EXISTS sources_updated_at ON sources;
DROP FUNCTION IF EXISTS tocar_updated_at();

DROP TABLE IF EXISTS entity_resolution_decisions;
DROP TABLE IF EXISTS review_queue;
DROP TABLE IF EXISTS provenance;
DROP TABLE IF EXISTS relationships;
DROP TABLE IF EXISTS entities;

DROP TRIGGER IF EXISTS raw_documents_sin_update ON raw_documents;
DROP FUNCTION IF EXISTS raw_documents_rechazar_update();
DROP TABLE IF EXISTS raw_documents;

DROP TABLE IF EXISTS sources;

COMMIT;
