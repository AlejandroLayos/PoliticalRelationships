package store

import (
	"time"

	"github.com/google/uuid"
)

// Source es una fuente pública de datos.
type Source struct {
	ID          string
	Name        string
	URL         string
	License     string
	Description string
}

// RawDocument es la respuesta literal de una fuente. Una vez insertado no se
// modifica nunca: hay un trigger en la base de datos que rechaza el UPDATE.
type RawDocument struct {
	ID          uuid.UUID
	SourceID    string
	URL         string
	Content     []byte
	ContentHash string
	MediaType   string
	RetrievedAt time.Time
	Metadata    map[string]any
}

// Entity es un nodo del grafo: una empresa, una persona, un organismo.
type Entity struct {
	ID         uuid.UUID
	FtmSchema  string
	Caption    string
	Properties map[string]any

	// NIF normalizado. Vacío si la fuente no lo da.
	NIF     string
	Country string

	// DedupeKey identifica la entidad de forma estable entre ejecuciones.
	// Con NIF conocido debe ser "nif:<NIF>", de forma que dos fuentes que ven
	// el mismo NIF converjan en la misma fila.
	DedupeKey string

	// CanonicalID apunta a la entidad que absorbió a ésta en una fusión.
	// uuid.Nil si es canónica.
	CanonicalID uuid.UUID
}

// Relationship es una arista del grafo.
type Relationship struct {
	ID             uuid.UUID
	FtmSchema      string
	SourceEntityID uuid.UUID
	TargetEntityID uuid.UUID
	Properties     map[string]any

	StartDate *time.Time
	EndDate   *time.Time

	// Amount va como cadena decimal ("50000.00") y no como float: el importe
	// es el dato que da sentido al proyecto y un redondeo binario lo
	// corrompería en silencio. Postgres lo guarda en NUMERIC(18,2).
	Amount   string
	Currency string

	// Confidence entre 0 y 1. Nunca se omite.
	Confidence float64

	// Status: asserted, inferred, disputed o retracted.
	Status string

	// DedupeKey hace idempotente la ingesta de la arista.
	DedupeKey string
}

// Estados admitidos para una arista.
const (
	StatusAsserted  = "asserted"
	StatusInferred  = "inferred"
	StatusDisputed  = "disputed"
	StatusRetracted = "retracted"
)

// Provenance enlaza un hecho con el documento crudo que lo sostiene.
// Exactamente uno de EntityID / RelationshipID debe estar relleno.
type Provenance struct {
	ID               uuid.UUID
	RawDocumentID    uuid.UUID
	EntityID         uuid.UUID
	RelationshipID   uuid.UUID
	ExtractorVersion string
	Excerpt          string
	ExtractedAt      time.Time
}

// ProvenanceRef es lo que se devuelve al preguntar de dónde salió un hecho:
// suficiente para citar la fuente sin cargar el crudo entero.
type ProvenanceRef struct {
	RawDocumentID    uuid.UUID
	SourceID         string
	URL              string
	ContentHash      string
	RetrievedAt      time.Time
	ExtractorVersion string
	Excerpt          string
}
