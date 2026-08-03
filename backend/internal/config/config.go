// Package config carga la configuración del proceso desde variables de entorno.
//
// No hay fichero de configuración: todo entra por entorno, de forma que el
// mismo binario sirve en local (docker compose) y en producción (VPS) sin
// recompilar. Los valores por defecto apuntan a los servicios del compose.
package config

import (
	"fmt"
	"os"
	"strconv"
	"time"
)

// Config es la configuración completa del proceso api.
type Config struct {
	// HTTPAddr es la dirección de escucha del servidor HTTP, formato ":8080".
	HTTPAddr string

	// PostgresDSN es la cadena de conexión a la verdad canónica.
	PostgresDSN string

	// RedisAddr es la dirección host:puerto de Redis (cola y caché).
	RedisAddr string

	// Neo4jURI, Neo4jUser y Neo4jPassword configuran la proyección de grafo.
	Neo4jURI      string
	Neo4jUser     string
	Neo4jPassword string

	// ShutdownTimeout es lo que esperamos a que terminen las peticiones en
	// vuelo antes de matar el servidor.
	ShutdownTimeout time.Duration

	// ReadyTimeout acota cuánto puede tardar la comprobación de dependencias
	// de /readyz. Un chequeo lento debe fallar, no colgarse.
	ReadyTimeout time.Duration
}

// Load lee la configuración del entorno, aplicando valores por defecto
// pensados para el docker compose de desarrollo.
func Load() (Config, error) {
	cfg := Config{
		HTTPAddr:      env("SINAPSIS_HTTP_ADDR", ":8080"),
		PostgresDSN:   env("SINAPSIS_POSTGRES_DSN", "postgres://sinapsis:sinapsis@postgres:5432/sinapsis?sslmode=disable"),
		RedisAddr:     env("SINAPSIS_REDIS_ADDR", "redis:6379"),
		Neo4jURI:      env("SINAPSIS_NEO4J_URI", "bolt://neo4j:7687"),
		Neo4jUser:     env("SINAPSIS_NEO4J_USER", "neo4j"),
		Neo4jPassword: env("SINAPSIS_NEO4J_PASSWORD", "sinapsis-dev"),
	}

	var err error
	if cfg.ShutdownTimeout, err = envDuration("SINAPSIS_SHUTDOWN_TIMEOUT", 15*time.Second); err != nil {
		return Config{}, err
	}
	if cfg.ReadyTimeout, err = envDuration("SINAPSIS_READY_TIMEOUT", 3*time.Second); err != nil {
		return Config{}, err
	}
	return cfg, nil
}

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func envDuration(key string, fallback time.Duration) (time.Duration, error) {
	raw := os.Getenv(key)
	if raw == "" {
		return fallback, nil
	}
	// Aceptamos tanto "30s" como un número entero de segundos, porque los
	// ficheros de entorno suelen traer lo segundo.
	if d, err := time.ParseDuration(raw); err == nil {
		return d, nil
	}
	secs, err := strconv.Atoi(raw)
	if err != nil {
		return 0, fmt.Errorf("config: %s=%q no es una duración válida", key, raw)
	}
	return time.Duration(secs) * time.Second, nil
}
