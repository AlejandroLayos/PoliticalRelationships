package store

import (
	"context"
	"fmt"

	"github.com/google/uuid"
)

// ProvenanceForRelationship devuelve todos los documentos crudos que sostienen
// una arista. Es la consulta que hace auditable el proyecto: de una conexión
// mostrada en la interfaz al documento original que la respalda.
func (s *Store) ProvenanceForRelationship(ctx context.Context, relID uuid.UUID) ([]ProvenanceRef, error) {
	const q = `
		SELECT rd.id, rd.source_id, rd.url, rd.content_hash, rd.retrieved_at,
		       p.extractor_version, COALESCE(p.excerpt, '')
		FROM provenance p
		JOIN raw_documents rd ON rd.id = p.raw_document_id
		WHERE p.relationship_id = $1
		ORDER BY rd.retrieved_at DESC`
	return s.provenanceQuery(ctx, q, relID)
}

// ProvenanceForEntity devuelve los documentos crudos que sostienen una entidad.
func (s *Store) ProvenanceForEntity(ctx context.Context, entityID uuid.UUID) ([]ProvenanceRef, error) {
	const q = `
		SELECT rd.id, rd.source_id, rd.url, rd.content_hash, rd.retrieved_at,
		       p.extractor_version, COALESCE(p.excerpt, '')
		FROM provenance p
		JOIN raw_documents rd ON rd.id = p.raw_document_id
		WHERE p.entity_id = $1
		ORDER BY rd.retrieved_at DESC`
	return s.provenanceQuery(ctx, q, entityID)
}

func (s *Store) provenanceQuery(ctx context.Context, q string, id uuid.UUID) ([]ProvenanceRef, error) {
	rows, err := s.pool.Query(ctx, q, id)
	if err != nil {
		return nil, fmt.Errorf("consultando procedencia: %w", err)
	}
	defer rows.Close()

	var refs []ProvenanceRef
	for rows.Next() {
		var r ProvenanceRef
		if err := rows.Scan(&r.RawDocumentID, &r.SourceID, &r.URL, &r.ContentHash,
			&r.RetrievedAt, &r.ExtractorVersion, &r.Excerpt); err != nil {
			return nil, fmt.Errorf("leyendo procedencia: %w", err)
		}
		refs = append(refs, r)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("recorriendo procedencia: %w", err)
	}
	return refs, nil
}

// EntityByDedupeKey recupera una entidad por su clave estable.
func (s *Store) EntityByDedupeKey(ctx context.Context, key string) (Entity, error) {
	const q = `
		SELECT id, ftm_schema, caption, properties,
		       COALESCE(nif,''), COALESCE(country,''), dedupe_key,
		       COALESCE(canonical_id, '00000000-0000-0000-0000-000000000000'::uuid)
		FROM entities WHERE dedupe_key = $1`

	var e Entity
	err := s.pool.QueryRow(ctx, q, key).Scan(
		&e.ID, &e.FtmSchema, &e.Caption, &e.Properties,
		&e.NIF, &e.Country, &e.DedupeKey, &e.CanonicalID,
	)
	if err != nil {
		return Entity{}, fmt.Errorf("buscando entidad %q: %w", key, err)
	}
	return e, nil
}

// CountRawDocuments cuenta los documentos de una fuente. Lo usan los tests y
// las métricas de ingesta.
func (s *Store) CountRawDocuments(ctx context.Context, sourceID string) (int, error) {
	var n int
	err := s.pool.QueryRow(ctx,
		`SELECT count(*) FROM raw_documents WHERE source_id = $1`, sourceID).Scan(&n)
	if err != nil {
		return 0, fmt.Errorf("contando documentos de %q: %w", sourceID, err)
	}
	return n, nil
}
