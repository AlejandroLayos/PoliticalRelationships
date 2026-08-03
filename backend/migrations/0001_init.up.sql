-- Esquema inicial de Sinapsis.
--
-- Vocabulario: FollowTheMoney (OCCRP). Las columnas `ftm_schema` guardan
-- nombres de esquema FtM ("Company", "Person", "Payment", "Ownership"...) para
-- que los datos sean exportables e intercambiables con Aleph y OpenSanctions.
-- Ver docs/adr/0002-followthemoney.md.
--
-- Las cuatro invariantes que este esquema hace cumplir a nivel de base de
-- datos, no de código:
--   1. Procedencia siempre  -> provenance con FK a raw_documents
--   2. Crudo inmutable      -> trigger que rechaza UPDATE en raw_documents
--   3. Ingesta idempotente  -> UNIQUE (source_id, content_hash)
--   4. Fusión auditable     -> entity_resolution_decisions, reversible

BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- --------------------------------------------------------------------------
-- Fuentes
-- --------------------------------------------------------------------------

CREATE TABLE sources (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    url         TEXT,
    license     TEXT,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE sources IS
    'Catálogo de fuentes públicas. El id es el mismo que usa el conector, p. ej. "bdns".';

-- --------------------------------------------------------------------------
-- Documentos crudos (inmutables)
-- --------------------------------------------------------------------------

CREATE TABLE raw_documents (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id    TEXT NOT NULL REFERENCES sources (id) ON DELETE RESTRICT,
    url          TEXT NOT NULL,
    content      BYTEA NOT NULL,
    content_hash TEXT NOT NULL,
    media_type   TEXT NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL,
    metadata     JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT raw_documents_hash_format CHECK (content_hash ~ '^[0-9a-f]{64}$')
);

-- Clave de idempotencia. Va por (fuente, hash) y no sólo por hash: dos fuentes
-- distintas pueden servir bytes idénticos legítimamente (el mismo PDF
-- republicado), y colapsarlos perdería la procedencia de una de ellas.
CREATE UNIQUE INDEX raw_documents_source_hash_key
    ON raw_documents (source_id, content_hash);

CREATE INDEX raw_documents_retrieved_at_idx ON raw_documents (retrieved_at DESC);

COMMENT ON TABLE raw_documents IS
    'Respuestas literales de las fuentes. Nunca se editan: todo lo derivado se recomputa desde aquí.';

-- Invariante 2 en la propia base de datos. Sin esto, "el crudo es inmutable"
-- es una convención que el primer UPDATE apresurado rompe en silencio.
CREATE OR REPLACE FUNCTION raw_documents_rechazar_update()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'raw_documents es inmutable (id=%). Reprocesa desde el crudo en vez de editarlo.',
        OLD.id;
END;
$$;

CREATE TRIGGER raw_documents_sin_update
    BEFORE UPDATE ON raw_documents
    FOR EACH ROW
    EXECUTE FUNCTION raw_documents_rechazar_update();

-- --------------------------------------------------------------------------
-- Entidades
-- --------------------------------------------------------------------------

CREATE TABLE entities (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ftm_schema   TEXT NOT NULL,
    caption      TEXT NOT NULL,
    properties   JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Identificador fuerte para resolución determinista. Normalizado
    -- (mayúsculas, sin espacios ni guiones) antes de insertar.
    nif          TEXT,
    country      TEXT,

    -- Ubicación opcional, para las vistas geográficas. Justifica PostGIS.
    geom         geography(Point, 4326),

    -- Si no es NULL, esta fila quedó absorbida por otra en una fusión. Se
    -- conserva en vez de borrarse para que la decisión sea reversible.
    canonical_id UUID REFERENCES entities (id) ON DELETE RESTRICT,

    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Sólo esquemas FtM con edge=False. Ojo: en FollowTheMoney `Contract` es
    -- una entidad (el contrato en sí); la arista que lo adjudica a un
    -- proveedor es `ContractAward`. `Position` + la arista `Occupancy` son lo
    -- que modela los cargos públicos y, con ello, las puertas giratorias.
    CONSTRAINT entities_ftm_schema_valido CHECK (
        ftm_schema IN (
            'Person', 'Company', 'Organization', 'PublicBody',
            'LegalEntity', 'Asset', 'Security', 'Position',
            'Contract', 'Project', 'CourtCase', 'Document'
        )
    ),
    -- Una entidad no puede ser su propio canónico.
    CONSTRAINT entities_canonical_no_es_self CHECK (canonical_id IS DISTINCT FROM id)
);

-- El NIF identifica de forma única, pero sólo entre las entidades canónicas:
-- las absorbidas conservan el suyo y colisionarían.
CREATE UNIQUE INDEX entities_nif_key
    ON entities (nif)
    WHERE nif IS NOT NULL AND canonical_id IS NULL;

CREATE INDEX entities_canonical_id_idx ON entities (canonical_id) WHERE canonical_id IS NOT NULL;
CREATE INDEX entities_ftm_schema_idx ON entities (ftm_schema);
CREATE INDEX entities_properties_idx ON entities USING gin (properties);
CREATE INDEX entities_geom_idx ON entities USING gist (geom) WHERE geom IS NOT NULL;

COMMENT ON COLUMN entities.ftm_schema IS 'Nombre de esquema FollowTheMoney.';
COMMENT ON COLUMN entities.canonical_id IS
    'Entidad que absorbió a esta en una fusión. NULL = es canónica.';

-- --------------------------------------------------------------------------
-- Relaciones (aristas)
-- --------------------------------------------------------------------------

CREATE TABLE relationships (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ftm_schema       TEXT NOT NULL,
    source_entity_id UUID NOT NULL REFERENCES entities (id) ON DELETE RESTRICT,
    target_entity_id UUID NOT NULL REFERENCES entities (id) ON DELETE RESTRICT,
    properties       JSONB NOT NULL DEFAULT '{}'::jsonb,

    start_date       DATE,
    end_date         DATE,
    amount           NUMERIC(18, 2),
    currency         TEXT,

    -- Invariante 5: nada inferido se presenta como probado.
    confidence       NUMERIC(3, 2) NOT NULL,
    status           TEXT NOT NULL DEFAULT 'asserted',

    -- Clave de idempotencia de la arista, derivada de los campos que la
    -- identifican en la fuente. Reejecutar el conector no duplica.
    dedupe_key       TEXT NOT NULL,

    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Sólo esquemas FtM con edge=True, y en su dirección canónica:
    --   Payment       payer     -> beneficiary   (subvenciones BDNS)
    --   ContractAward contract  -> supplier      (adjudicaciones PLACSP)
    --   Ownership     owner     -> asset
    --   Directorship  director  -> organization
    --   Occupancy     holder    -> post          (cargos públicos)
    CONSTRAINT relationships_ftm_schema_valido CHECK (
        ftm_schema IN (
            'Ownership', 'Directorship', 'Membership', 'Employment',
            'Payment', 'ContractAward', 'Occupancy', 'Debt',
            'Representation', 'Associate', 'Family', 'Succession',
            'UnknownLink'
        )
    ),
    CONSTRAINT relationships_confidence_rango CHECK (confidence >= 0 AND confidence <= 1),
    CONSTRAINT relationships_status_valido CHECK (
        status IN ('asserted', 'inferred', 'disputed', 'retracted')
    ),
    CONSTRAINT relationships_fechas_coherentes CHECK (
        start_date IS NULL OR end_date IS NULL OR start_date <= end_date
    ),
    -- Un importe sin moneda no es un importe.
    CONSTRAINT relationships_importe_con_moneda CHECK (
        amount IS NULL OR currency IS NOT NULL
    ),
    CONSTRAINT relationships_sin_bucle CHECK (source_entity_id <> target_entity_id)
);

CREATE UNIQUE INDEX relationships_dedupe_key_idx ON relationships (dedupe_key);
CREATE INDEX relationships_source_idx ON relationships (source_entity_id);
CREATE INDEX relationships_target_idx ON relationships (target_entity_id);
CREATE INDEX relationships_ftm_schema_idx ON relationships (ftm_schema);
-- La viz pide vecindarios en ambos sentidos; este índice cubre la dirección
-- inversa sin recorrer la tabla.
CREATE INDEX relationships_target_source_idx ON relationships (target_entity_id, source_entity_id);

COMMENT ON COLUMN relationships.confidence IS
    'Confianza en la arista, 0..1. La API nunca la omite.';
COMMENT ON COLUMN relationships.status IS
    'asserted = afirmado por la fuente; inferred = deducido por nosotros.';

-- --------------------------------------------------------------------------
-- Procedencia
-- --------------------------------------------------------------------------

CREATE TABLE provenance (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_document_id   UUID NOT NULL REFERENCES raw_documents (id) ON DELETE RESTRICT,

    -- Exactamente uno de los dos: la procedencia apunta a una entidad o a una
    -- arista. Dos FK reales en vez de una polimórfica, para que la integridad
    -- referencial la garantice Postgres.
    entity_id         UUID REFERENCES entities (id) ON DELETE CASCADE,
    relationship_id   UUID REFERENCES relationships (id) ON DELETE CASCADE,

    extractor_version TEXT NOT NULL,
    excerpt           TEXT,
    extracted_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT provenance_un_solo_sujeto CHECK (
        num_nonnulls(entity_id, relationship_id) = 1
    )
);

CREATE UNIQUE INDEX provenance_entidad_key
    ON provenance (raw_document_id, entity_id, extractor_version)
    WHERE entity_id IS NOT NULL;

CREATE UNIQUE INDEX provenance_arista_key
    ON provenance (raw_document_id, relationship_id, extractor_version)
    WHERE relationship_id IS NOT NULL;

CREATE INDEX provenance_entity_idx ON provenance (entity_id) WHERE entity_id IS NOT NULL;
CREATE INDEX provenance_relationship_idx ON provenance (relationship_id) WHERE relationship_id IS NOT NULL;
CREATE INDEX provenance_raw_document_idx ON provenance (raw_document_id);

COMMENT ON TABLE provenance IS
    'Invariante 1: ningún hecho existe sin una fila aquí que lo enlace a su documento original.';
COMMENT ON COLUMN provenance.excerpt IS
    'Fragmento literal del crudo que sostiene el hecho, para citarlo en la UI.';

-- --------------------------------------------------------------------------
-- Resolución de entidades
-- --------------------------------------------------------------------------

CREATE TABLE review_queue (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    left_entity_id   UUID NOT NULL REFERENCES entities (id) ON DELETE CASCADE,
    right_entity_id  UUID NOT NULL REFERENCES entities (id) ON DELETE CASCADE,
    score            NUMERIC(4, 3) NOT NULL,
    features         JSONB NOT NULL DEFAULT '{}'::jsonb,
    status           TEXT NOT NULL DEFAULT 'pending',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at      TIMESTAMPTZ,
    resolved_by      TEXT,

    CONSTRAINT review_queue_score_rango CHECK (score >= 0 AND score <= 1),
    CONSTRAINT review_queue_status_valido CHECK (
        status IN ('pending', 'merged', 'rejected')
    ),
    -- Evita que (A,B) y (B,A) entren como dos candidatos distintos.
    CONSTRAINT review_queue_par_ordenado CHECK (left_entity_id < right_entity_id)
);

CREATE UNIQUE INDEX review_queue_par_key ON review_queue (left_entity_id, right_entity_id);
CREATE INDEX review_queue_pendientes_idx ON review_queue (score DESC) WHERE status = 'pending';

COMMENT ON TABLE review_queue IS
    'Invariante 4: el matching difuso propone aquí, nunca fusiona solo.';

CREATE TABLE entity_resolution_decisions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kept_entity_id    UUID NOT NULL REFERENCES entities (id) ON DELETE RESTRICT,
    merged_entity_id  UUID NOT NULL REFERENCES entities (id) ON DELETE RESTRICT,
    method            TEXT NOT NULL,
    score             NUMERIC(4, 3),
    evidence          JSONB NOT NULL DEFAULT '{}'::jsonb,
    decided_by        TEXT NOT NULL,
    decided_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Reversibilidad: deshacer una fusión rellena esto en vez de borrar la
    -- fila, para que el historial de decisiones quede intacto.
    reverted_at       TIMESTAMPTZ,
    reverted_by       TEXT,

    CONSTRAINT erd_method_valido CHECK (
        method IN ('nif_exact', 'manual_review', 'import')
    ),
    CONSTRAINT erd_no_es_self CHECK (kept_entity_id <> merged_entity_id),
    CONSTRAINT erd_score_rango CHECK (score IS NULL OR (score >= 0 AND score <= 1))
);

CREATE INDEX erd_kept_idx ON entity_resolution_decisions (kept_entity_id);
CREATE INDEX erd_merged_idx ON entity_resolution_decisions (merged_entity_id);
CREATE INDEX erd_activas_idx ON entity_resolution_decisions (decided_at DESC) WHERE reverted_at IS NULL;

COMMENT ON TABLE entity_resolution_decisions IS
    'Bitácora auditable y reversible de fusiones de entidades.';

-- --------------------------------------------------------------------------
-- updated_at automático
-- --------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION tocar_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER sources_updated_at
    BEFORE UPDATE ON sources
    FOR EACH ROW EXECUTE FUNCTION tocar_updated_at();

CREATE TRIGGER entities_updated_at
    BEFORE UPDATE ON entities
    FOR EACH ROW EXECUTE FUNCTION tocar_updated_at();

CREATE TRIGGER relationships_updated_at
    BEFORE UPDATE ON relationships
    FOR EACH ROW EXECUTE FUNCTION tocar_updated_at();

COMMIT;
