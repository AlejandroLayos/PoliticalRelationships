package store

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
)

// ErrProvenanciaAusente se devuelve cuando se intenta persistir un hecho sin
// el documento crudo que lo sostiene. Es el invariante 1.
var ErrProvenanciaAusente = errors.New("store: un hecho no se persiste sin procedencia")

// UpsertSource inserta o actualiza una fuente. Idempotente por id.
func (s *Store) UpsertSource(ctx context.Context, src Source) error {
	const q = `
		INSERT INTO sources (id, name, url, license, description)
		VALUES ($1, $2, NULLIF($3,''), NULLIF($4,''), NULLIF($5,''))
		ON CONFLICT (id) DO UPDATE SET
			name        = EXCLUDED.name,
			url         = EXCLUDED.url,
			license     = EXCLUDED.license,
			description = EXCLUDED.description`

	if _, err := s.pool.Exec(ctx, q, src.ID, src.Name, src.URL, src.License, src.Description); err != nil {
		return fmt.Errorf("upsert de fuente %q: %w", src.ID, err)
	}
	return nil
}

// UpsertRawDocument guarda un documento crudo. Devuelve su id y si se creó
// ahora (false = ya existía con el mismo hash).
//
// No usa ON CONFLICT DO UPDATE a propósito: `raw_documents` tiene un trigger
// que rechaza cualquier UPDATE, así que un DO UPDATE —aunque fuera un no-op
// para obtener el RETURNING— reventaría. El crudo es inmutable, y eso incluye
// al upsert.
func (s *Store) UpsertRawDocument(ctx context.Context, doc RawDocument) (id uuid.UUID, creado bool, err error) {
	metadata, err := marshalJSON(doc.Metadata)
	if err != nil {
		return uuid.Nil, false, fmt.Errorf("serializando metadata: %w", err)
	}

	const insert = `
		INSERT INTO raw_documents
			(source_id, url, content, content_hash, media_type, retrieved_at, metadata)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		ON CONFLICT (source_id, content_hash) DO NOTHING
		RETURNING id`

	err = s.pool.QueryRow(ctx, insert,
		doc.SourceID, doc.URL, doc.Content, doc.ContentHash,
		doc.MediaType, doc.RetrievedAt, metadata,
	).Scan(&id)

	switch {
	case err == nil:
		return id, true, nil
	case !errors.Is(err, pgx.ErrNoRows):
		return uuid.Nil, false, fmt.Errorf("insertando documento crudo: %w", err)
	}

	// Sin filas devueltas: el documento ya estaba. Recuperamos su id.
	const sel = `SELECT id FROM raw_documents WHERE source_id = $1 AND content_hash = $2`
	if err := s.pool.QueryRow(ctx, sel, doc.SourceID, doc.ContentHash).Scan(&id); err != nil {
		return uuid.Nil, false, fmt.Errorf("recuperando documento crudo existente: %w", err)
	}
	return id, false, nil
}

// UpsertEntity inserta o actualiza una entidad por su DedupeKey.
//
// Sobre las propiedades: se fusionan (`||`) en vez de sustituirse, porque dos
// fuentes distintas aportan campos distintos de la misma entidad y la segunda
// ingesta no debe borrar lo que trajo la primera.
func (s *Store) UpsertEntity(ctx context.Context, e Entity) (uuid.UUID, error) {
	if e.DedupeKey == "" {
		return uuid.Nil, errors.New("store: la entidad necesita DedupeKey")
	}

	props, err := marshalJSON(e.Properties)
	if err != nil {
		return uuid.Nil, fmt.Errorf("serializando properties: %w", err)
	}

	const q = `
		INSERT INTO entities (ftm_schema, caption, properties, nif, country, dedupe_key)
		VALUES ($1, $2, $3, NULLIF($4,''), NULLIF($5,''), $6)
		ON CONFLICT (dedupe_key) DO UPDATE SET
			caption    = EXCLUDED.caption,
			properties = entities.properties || EXCLUDED.properties,
			nif        = COALESCE(entities.nif, EXCLUDED.nif),
			country    = COALESCE(entities.country, EXCLUDED.country)
		RETURNING id`

	var id uuid.UUID
	if err := s.pool.QueryRow(ctx, q,
		e.FtmSchema, e.Caption, props, e.NIF, e.Country, e.DedupeKey,
	).Scan(&id); err != nil {
		return uuid.Nil, fmt.Errorf("upsert de entidad %q: %w", e.DedupeKey, err)
	}
	return id, nil
}

// UpsertRelationship inserta o actualiza una arista por su DedupeKey.
func (s *Store) UpsertRelationship(ctx context.Context, r Relationship) (uuid.UUID, error) {
	if r.DedupeKey == "" {
		return uuid.Nil, errors.New("store: la arista necesita DedupeKey")
	}
	if r.Status == "" {
		r.Status = StatusAsserted
	}

	props, err := marshalJSON(r.Properties)
	if err != nil {
		return uuid.Nil, fmt.Errorf("serializando properties: %w", err)
	}

	// $7 llega como texto y Postgres lo convierte a NUMERIC: así el importe no
	// pasa nunca por un float64.
	const q = `
		INSERT INTO relationships (
			ftm_schema, source_entity_id, target_entity_id, properties,
			start_date, end_date, amount, currency, confidence, status, dedupe_key
		)
		VALUES ($1, $2, $3, $4, $5, $6, NULLIF($7,'')::numeric, NULLIF($8,''), $9, $10, $11)
		ON CONFLICT (dedupe_key) DO UPDATE SET
			properties = relationships.properties || EXCLUDED.properties,
			start_date = COALESCE(EXCLUDED.start_date, relationships.start_date),
			end_date   = COALESCE(EXCLUDED.end_date,   relationships.end_date),
			amount     = COALESCE(EXCLUDED.amount,     relationships.amount),
			currency   = COALESCE(EXCLUDED.currency,   relationships.currency),
			confidence = EXCLUDED.confidence,
			status     = EXCLUDED.status
		RETURNING id`

	var id uuid.UUID
	if err := s.pool.QueryRow(ctx, q,
		r.FtmSchema, r.SourceEntityID, r.TargetEntityID, props,
		r.StartDate, r.EndDate, r.Amount, r.Currency,
		r.Confidence, r.Status, r.DedupeKey,
	).Scan(&id); err != nil {
		return uuid.Nil, fmt.Errorf("upsert de arista %q: %w", r.DedupeKey, err)
	}
	return id, nil
}

// AddProvenance enlaza una entidad o una arista con el documento crudo que la
// sostiene. Idempotente por (documento, sujeto, extractor_version).
func (s *Store) AddProvenance(ctx context.Context, p Provenance) error {
	if p.RawDocumentID == uuid.Nil {
		return ErrProvenanciaAusente
	}
	tieneEntidad := p.EntityID != uuid.Nil
	tieneArista := p.RelationshipID != uuid.Nil
	if tieneEntidad == tieneArista {
		return errors.New("store: la procedencia apunta a una entidad o a una arista, no a ambas ni a ninguna")
	}

	const q = `
		INSERT INTO provenance
			(raw_document_id, entity_id, relationship_id, extractor_version, excerpt)
		VALUES ($1, $2, $3, $4, NULLIF($5,''))
		ON CONFLICT DO NOTHING`

	if _, err := s.pool.Exec(ctx, q,
		p.RawDocumentID, nullUUID(p.EntityID), nullUUID(p.RelationshipID),
		p.ExtractorVersion, p.Excerpt,
	); err != nil {
		return fmt.Errorf("insertando procedencia: %w", err)
	}
	return nil
}

func marshalJSON(m map[string]any) ([]byte, error) {
	if m == nil {
		return []byte("{}"), nil
	}
	return json.Marshal(m)
}

// nullUUID convierte el UUID cero en NULL, que es lo que espera el CHECK de
// `provenance`.
func nullUUID(id uuid.UUID) *uuid.UUID {
	if id == uuid.Nil {
		return nil
	}
	return &id
}
