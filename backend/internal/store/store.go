// Package store es la capa de acceso a PostgreSQL, la verdad canónica de
// Sinapsis.
//
// Todas las escrituras de esta capa son idempotentes: reejecutar una ingesta
// no debe duplicar filas (invariante 3 de docs/spec.md). Neo4j se puebla por
// sincronización desde aquí y nunca al revés.
package store

import (
	"context"
	"fmt"

	"github.com/jackc/pgx/v5/pgxpool"
)

// Store envuelve el pool de conexiones a Postgres.
type Store struct {
	pool *pgxpool.Pool
}

// Open crea el pool. No abre conexiones de forma inmediata: pgx conecta de
// forma perezosa, así que un Postgres que aún no ha arrancado no impide que la
// API se levante.
func Open(ctx context.Context, dsn string) (*Store, error) {
	cfg, err := pgxpool.ParseConfig(dsn)
	if err != nil {
		return nil, fmt.Errorf("dsn inválido: %w", err)
	}

	pool, err := pgxpool.NewWithConfig(ctx, cfg)
	if err != nil {
		return nil, fmt.Errorf("creando pool: %w", err)
	}
	return &Store{pool: pool}, nil
}

// Pool expone el pool subyacente para los repositorios del paquete.
func (s *Store) Pool() *pgxpool.Pool { return s.pool }

// Ping comprueba que Postgres responde. Lo usa /readyz.
func (s *Store) Ping(ctx context.Context) error {
	if err := s.pool.Ping(ctx); err != nil {
		return fmt.Errorf("postgres no responde: %w", err)
	}
	return nil
}

// Close cierra el pool y espera a que terminen las conexiones en uso.
func (s *Store) Close() {
	if s.pool != nil {
		s.pool.Close()
	}
}
