package store

import (
	"context"
	"errors"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
)

// ErrEntidadNoEncontrada se devuelve cuando el id no existe.
var ErrEntidadNoEncontrada = errors.New("store: entidad no encontrada")

// EntityDetail es una entidad con lo necesario para mostrarla y auditarla.
type EntityDetail struct {
	ID          uuid.UUID
	FtmSchema   string
	Caption     string
	NIF         string
	Country     string
	Properties  map[string]any
	CanonicalID *uuid.UUID
}

// GraphNode es un nodo del vecindario.
type GraphNode struct {
	ID        uuid.UUID
	FtmSchema string
	Caption   string
	NIF       string
	// Depth es el número de saltos desde la entidad raíz.
	Depth int
}

// GraphEdge es una arista del vecindario.
//
// Confidence y Status no son opcionales ni en el struct ni en el JSON: la
// invariante 5 dice que nada inferido se presenta como probado, y eso hay que
// imponerlo en la API, no sólo en la interfaz. Quien consuma la API en crudo
// tiene que recibir la distinción.
type GraphEdge struct {
	ID             uuid.UUID
	FtmSchema      string
	SourceEntityID uuid.UUID
	TargetEntityID uuid.UUID
	Amount         string
	Currency       string
	Confidence     float64
	Status         string
	StartDate      string
	EndDate        string
}

// Neighborhood es la ego-red de una entidad.
type Neighborhood struct {
	RootID uuid.UUID
	Depth  int
	Nodes  []GraphNode
	Edges  []GraphEdge
	// Truncated indica que se alcanzó el límite de nodos y el vecindario
	// mostrado está incompleto. La interfaz debe decirlo: un grafo recortado
	// que finge estar completo miente.
	Truncated bool
}

// EntityByID recupera una entidad. Si fue absorbida en una fusión devuelve la
// fila tal cual, con CanonicalID relleno, para que quien llame decida si
// redirigir.
func (s *Store) EntityByID(ctx context.Context, id uuid.UUID) (EntityDetail, error) {
	const q = `
		SELECT id, ftm_schema, caption, COALESCE(nif,''), COALESCE(country,''),
		       properties, canonical_id
		FROM entities WHERE id = $1`

	var e EntityDetail
	err := s.pool.QueryRow(ctx, q, id).Scan(
		&e.ID, &e.FtmSchema, &e.Caption, &e.NIF, &e.Country, &e.Properties, &e.CanonicalID,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return EntityDetail{}, ErrEntidadNoEncontrada
	}
	if err != nil {
		return EntityDetail{}, fmt.Errorf("consultando entidad %s: %w", id, err)
	}
	return e, nil
}

// ResolverCanonica sigue la cadena de fusiones hasta la entidad viva.
func (s *Store) ResolverCanonica(ctx context.Context, id uuid.UUID) (uuid.UUID, error) {
	actual := id
	// Cota dura: una cadena más larga es un bug o un ciclo, y en cualquier
	// caso no queremos un bucle infinito sirviendo una petición HTTP.
	for range 16 {
		e, err := s.EntityByID(ctx, actual)
		if err != nil {
			return uuid.Nil, err
		}
		if e.CanonicalID == nil {
			return actual, nil
		}
		actual = *e.CanonicalID
	}
	return uuid.Nil, fmt.Errorf("cadena de fusiones demasiado larga desde %s", id)
}

// Neighborhood devuelve la ego-red de una entidad hasta `depth` saltos.
//
// Se expande nivel a nivel en vez de con una CTE recursiva: el grafo tiene
// ciclos, y una CTE recursiva sobre un grafo cíclico o explota o necesita
// detección de ciclos que oscurece la consulta. Con profundidades pequeñas
// —que son las únicas útiles para navegar— son dos o tres consultas acotadas.
//
// El patrón es expansión de ego-red, no volcado del grafo entero: un
// ForceAtlas2 con cien mil nodos es espectacular en una captura e inútil para
// investigar.
func (s *Store) Neighborhood(
	ctx context.Context, root uuid.UUID, depth, maxNodes int,
) (Neighborhood, error) {
	if depth < 1 {
		depth = 1
	}
	if depth > 3 {
		depth = 3
	}
	if maxNodes <= 0 {
		maxNodes = 300
	}

	raiz, err := s.EntityByID(ctx, root)
	if err != nil {
		return Neighborhood{}, err
	}

	vecindario := Neighborhood{RootID: root, Depth: depth}
	visitados := map[uuid.UUID]int{root: 0}
	vecindario.Nodes = append(vecindario.Nodes, GraphNode{
		ID: raiz.ID, FtmSchema: raiz.FtmSchema, Caption: raiz.Caption,
		NIF: raiz.NIF, Depth: 0,
	})

	aristasVistas := map[uuid.UUID]bool{}
	frontera := []uuid.UUID{root}

	for nivel := 1; nivel <= depth && len(frontera) > 0; nivel++ {
		aristas, err := s.aristasDe(ctx, frontera)
		if err != nil {
			return Neighborhood{}, err
		}

		var siguiente []uuid.UUID
		for _, a := range aristas {
			if !aristasVistas[a.ID] {
				aristasVistas[a.ID] = true
				vecindario.Edges = append(vecindario.Edges, a)
			}
			for _, extremo := range []uuid.UUID{a.SourceEntityID, a.TargetEntityID} {
				if _, visto := visitados[extremo]; visto {
					continue
				}
				if len(visitados) >= maxNodes {
					vecindario.Truncated = true
					continue
				}
				visitados[extremo] = nivel
				siguiente = append(siguiente, extremo)
			}
		}
		if len(siguiente) == 0 {
			break
		}

		nodos, err := s.nodos(ctx, siguiente, nivel)
		if err != nil {
			return Neighborhood{}, err
		}
		vecindario.Nodes = append(vecindario.Nodes, nodos...)
		frontera = siguiente
	}

	// Una arista cuyo otro extremo se quedó fuera por el límite colgaría en el
	// vacío al dibujarla; se descarta y se marca el recorte.
	if vecindario.Truncated {
		filtradas := vecindario.Edges[:0]
		for _, a := range vecindario.Edges {
			_, ok1 := visitados[a.SourceEntityID]
			_, ok2 := visitados[a.TargetEntityID]
			if ok1 && ok2 {
				filtradas = append(filtradas, a)
			}
		}
		vecindario.Edges = filtradas
	}

	return vecindario, nil
}

// aristasDe devuelve todas las aristas incidentes en un conjunto de nodos, en
// los dos sentidos.
func (s *Store) aristasDe(ctx context.Context, ids []uuid.UUID) ([]GraphEdge, error) {
	const q = `
		SELECT id, ftm_schema, source_entity_id, target_entity_id,
		       COALESCE(amount::text,''), COALESCE(currency,''),
		       confidence, status,
		       COALESCE(start_date::text,''), COALESCE(end_date::text,'')
		FROM relationships
		WHERE (source_entity_id = ANY($1) OR target_entity_id = ANY($1))
		  -- Una arista retractada no se muestra: se conserva por trazabilidad,
		  -- no para seguir publicándola.
		  AND status <> 'retracted'`

	rows, err := s.pool.Query(ctx, q, ids)
	if err != nil {
		return nil, fmt.Errorf("consultando aristas: %w", err)
	}
	defer rows.Close()

	var aristas []GraphEdge
	for rows.Next() {
		var a GraphEdge
		if err := rows.Scan(&a.ID, &a.FtmSchema, &a.SourceEntityID, &a.TargetEntityID,
			&a.Amount, &a.Currency, &a.Confidence, &a.Status,
			&a.StartDate, &a.EndDate); err != nil {
			return nil, fmt.Errorf("leyendo arista: %w", err)
		}
		aristas = append(aristas, a)
	}
	return aristas, rows.Err()
}

func (s *Store) nodos(ctx context.Context, ids []uuid.UUID, depth int) ([]GraphNode, error) {
	const q = `
		SELECT id, ftm_schema, caption, COALESCE(nif,'')
		FROM entities WHERE id = ANY($1)`

	rows, err := s.pool.Query(ctx, q, ids)
	if err != nil {
		return nil, fmt.Errorf("consultando nodos: %w", err)
	}
	defer rows.Close()

	var nodos []GraphNode
	for rows.Next() {
		n := GraphNode{Depth: depth}
		if err := rows.Scan(&n.ID, &n.FtmSchema, &n.Caption, &n.NIF); err != nil {
			return nil, fmt.Errorf("leyendo nodo: %w", err)
		}
		nodos = append(nodos, n)
	}
	return nodos, rows.Err()
}

// SearchEntities busca entidades por nombre. Es la puerta de entrada de la
// interfaz: se busca una entidad y desde ahí se expande el vecindario.
func (s *Store) SearchEntities(ctx context.Context, q string, limite int) ([]GraphNode, error) {
	if limite <= 0 || limite > 100 {
		limite = 25
	}
	const sql = `
		SELECT id, ftm_schema, caption, COALESCE(nif,'')
		FROM entities
		WHERE canonical_id IS NULL
		  AND caption_normalizado LIKE '%' || sinapsis_normalizar_nombre($1) || '%'
		ORDER BY length(caption)
		LIMIT $2`

	rows, err := s.pool.Query(ctx, sql, q, limite)
	if err != nil {
		return nil, fmt.Errorf("buscando entidades: %w", err)
	}
	defer rows.Close()

	var nodos []GraphNode
	for rows.Next() {
		var n GraphNode
		if err := rows.Scan(&n.ID, &n.FtmSchema, &n.Caption, &n.NIF); err != nil {
			return nil, fmt.Errorf("leyendo resultado: %w", err)
		}
		nodos = append(nodos, n)
	}
	return nodos, rows.Err()
}
