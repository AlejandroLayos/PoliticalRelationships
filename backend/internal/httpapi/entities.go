package httpapi

import (
	"context"
	"errors"
	"net/http"
	"strconv"

	"github.com/AlejandroLayos/PoliticalRelationships/backend/internal/store"
	"github.com/google/uuid"
)

// Graph es lo que la API necesita del almacén. Interfaz y no struct concreto
// para poder probar los handlers sin base de datos.
type Graph interface {
	EntityByID(ctx context.Context, id uuid.UUID) (store.EntityDetail, error)
	ResolverCanonica(ctx context.Context, id uuid.UUID) (uuid.UUID, error)
	Neighborhood(ctx context.Context, root uuid.UUID, depth, maxNodes int) (store.Neighborhood, error)
	SearchEntities(ctx context.Context, q string, limite int) ([]store.GraphNode, error)
	ProvenanceForEntity(ctx context.Context, id uuid.UUID) ([]store.ProvenanceRef, error)
}

// --- representaciones JSON -------------------------------------------------

type nodoJSON struct {
	ID      string `json:"id"`
	Schema  string `json:"schema"`
	Caption string `json:"caption"`
	NIF     string `json:"nif,omitempty"`
	Depth   int    `json:"depth"`
}

type aristaJSON struct {
	ID     string `json:"id"`
	Schema string `json:"schema"`
	Source string `json:"source"`
	Target string `json:"target"`
	Amount string `json:"amount,omitempty"`
	// Currency acompaña siempre a Amount: un importe sin moneda no es un importe.
	Currency string `json:"currency,omitempty"`
	// Confidence y Status NUNCA se omiten, ni siquiera cuando valen lo
	// "normal". Es la invariante 5 impuesta en la capa API: quien consuma esto
	// en crudo debe poder distinguir lo afirmado de lo inferido.
	Confidence float64 `json:"confidence"`
	Status     string  `json:"status"`
	StartDate  string  `json:"start_date,omitempty"`
	EndDate    string  `json:"end_date,omitempty"`
}

type procedenciaJSON struct {
	SourceID         string `json:"source_id"`
	URL              string `json:"url"`
	ContentHash      string `json:"content_hash"`
	RetrievedAt      string `json:"retrieved_at"`
	ExtractorVersion string `json:"extractor_version"`
	Excerpt          string `json:"excerpt,omitempty"`
}

type vecindarioJSON struct {
	Root      string       `json:"root"`
	Depth     int          `json:"depth"`
	Nodes     []nodoJSON   `json:"nodes"`
	Edges     []aristaJSON `json:"edges"`
	Truncated bool         `json:"truncated"`
}

func aNodoJSON(n store.GraphNode) nodoJSON {
	return nodoJSON{
		ID: n.ID.String(), Schema: n.FtmSchema, Caption: n.Caption,
		NIF: n.NIF, Depth: n.Depth,
	}
}

func aAristaJSON(a store.GraphEdge) aristaJSON {
	return aristaJSON{
		ID: a.ID.String(), Schema: a.FtmSchema,
		Source: a.SourceEntityID.String(), Target: a.TargetEntityID.String(),
		Amount: a.Amount, Currency: a.Currency,
		Confidence: a.Confidence, Status: a.Status,
		StartDate: a.StartDate, EndDate: a.EndDate,
	}
}

// --- handlers --------------------------------------------------------------

func (s *Server) entidad(w http.ResponseWriter, r *http.Request) {
	id, ok := s.idDeRuta(w, r)
	if !ok {
		return
	}

	e, err := s.graph.EntityByID(r.Context(), id)
	if errors.Is(err, store.ErrEntidadNoEncontrada) {
		writeError(w, http.StatusNotFound, "entidad no encontrada")
		return
	}
	if err != nil {
		s.logger.Error("consultando entidad", "error", err)
		writeError(w, http.StatusInternalServerError, "error consultando la entidad")
		return
	}

	proc, err := s.graph.ProvenanceForEntity(r.Context(), id)
	if err != nil {
		s.logger.Error("consultando procedencia", "error", err)
		writeError(w, http.StatusInternalServerError, "error consultando la procedencia")
		return
	}

	cuerpo := map[string]any{
		"id":         e.ID.String(),
		"schema":     e.FtmSchema,
		"caption":    e.Caption,
		"properties": e.Properties,
	}
	if e.NIF != "" {
		cuerpo["nif"] = e.NIF
	}
	if e.Country != "" {
		cuerpo["country"] = e.Country
	}
	// Si la entidad fue absorbida se dice explícitamente y se apunta a la
	// canónica: ocultarlo haría que la interfaz mostrara un duplicado sin
	// avisar de que lo es.
	if e.CanonicalID != nil {
		cuerpo["merged_into"] = e.CanonicalID.String()
	}

	refs := make([]procedenciaJSON, 0, len(proc))
	for _, p := range proc {
		refs = append(refs, procedenciaJSON{
			SourceID: p.SourceID, URL: p.URL, ContentHash: p.ContentHash,
			RetrievedAt:      p.RetrievedAt.Format("2006-01-02T15:04:05Z07:00"),
			ExtractorVersion: p.ExtractorVersion, Excerpt: p.Excerpt,
		})
	}
	cuerpo["provenance"] = refs

	writeJSON(w, http.StatusOK, cuerpo)
}

func (s *Server) vecinos(w http.ResponseWriter, r *http.Request) {
	id, ok := s.idDeRuta(w, r)
	if !ok {
		return
	}

	depth := 1
	if raw := r.URL.Query().Get("depth"); raw != "" {
		n, err := strconv.Atoi(raw)
		if err != nil || n < 1 || n > 3 {
			writeError(w, http.StatusBadRequest, "depth debe ser un entero entre 1 y 3")
			return
		}
		depth = n
	}

	limite := 300
	if raw := r.URL.Query().Get("limit"); raw != "" {
		n, err := strconv.Atoi(raw)
		if err != nil || n < 1 || n > 1000 {
			writeError(w, http.StatusBadRequest, "limit debe ser un entero entre 1 y 1000")
			return
		}
		limite = n
	}

	// Una entidad absorbida no tiene vecindario propio: el grafo real cuelga
	// de su canónica.
	canonica, err := s.graph.ResolverCanonica(r.Context(), id)
	if errors.Is(err, store.ErrEntidadNoEncontrada) {
		writeError(w, http.StatusNotFound, "entidad no encontrada")
		return
	}
	if err != nil {
		s.logger.Error("resolviendo canónica", "error", err)
		writeError(w, http.StatusInternalServerError, "error resolviendo la entidad")
		return
	}

	v, err := s.graph.Neighborhood(r.Context(), canonica, depth, limite)
	if errors.Is(err, store.ErrEntidadNoEncontrada) {
		writeError(w, http.StatusNotFound, "entidad no encontrada")
		return
	}
	if err != nil {
		s.logger.Error("consultando vecindario", "error", err)
		writeError(w, http.StatusInternalServerError, "error consultando el vecindario")
		return
	}

	cuerpo := vecindarioJSON{
		Root:      v.RootID.String(),
		Depth:     v.Depth,
		Nodes:     make([]nodoJSON, 0, len(v.Nodes)),
		Edges:     make([]aristaJSON, 0, len(v.Edges)),
		Truncated: v.Truncated,
	}
	for _, n := range v.Nodes {
		cuerpo.Nodes = append(cuerpo.Nodes, aNodoJSON(n))
	}
	for _, a := range v.Edges {
		cuerpo.Edges = append(cuerpo.Edges, aAristaJSON(a))
	}
	writeJSON(w, http.StatusOK, cuerpo)
}

func (s *Server) buscar(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query().Get("q")
	if len(q) < 3 {
		writeError(w, http.StatusBadRequest, "q debe tener al menos 3 caracteres")
		return
	}

	limite := 25
	if raw := r.URL.Query().Get("limit"); raw != "" {
		if n, err := strconv.Atoi(raw); err == nil && n > 0 && n <= 100 {
			limite = n
		}
	}

	nodos, err := s.graph.SearchEntities(r.Context(), q, limite)
	if err != nil {
		s.logger.Error("buscando entidades", "error", err)
		writeError(w, http.StatusInternalServerError, "error en la búsqueda")
		return
	}

	res := make([]nodoJSON, 0, len(nodos))
	for _, n := range nodos {
		res = append(res, aNodoJSON(n))
	}
	writeJSON(w, http.StatusOK, map[string]any{"results": res})
}

func (s *Server) idDeRuta(w http.ResponseWriter, r *http.Request) (uuid.UUID, bool) {
	id, err := uuid.Parse(r.PathValue("id"))
	if err != nil {
		writeError(w, http.StatusBadRequest, "id no es un UUID válido")
		return uuid.Nil, false
	}
	return id, true
}

func writeError(w http.ResponseWriter, code int, msg string) {
	writeJSON(w, code, map[string]string{"error": msg})
}
