package httpapi

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestHealthzSiempreOK(t *testing.T) {
	// Aunque las dependencias estén caídas, /healthz debe seguir en 200:
	// es liveness, no readiness.
	s := New(Options{Checkers: []Checker{
		CheckerFunc{DepName: "postgres", Fn: func(context.Context) error {
			return errors.New("caído")
		}},
	}})

	rec := httptest.NewRecorder()
	s.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/healthz", nil))

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, quería 200", rec.Code)
	}

	var body map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("respuesta no es JSON válido: %v", err)
	}
	if body["status"] != "ok" {
		t.Errorf("status = %q, quería \"ok\"", body["status"])
	}
	if len(body) != 1 {
		t.Errorf("el cuerpo tiene %d claves, quería exactamente 1: %v", len(body), body)
	}
}

func TestReadyzTodoSano(t *testing.T) {
	s := New(Options{Checkers: []Checker{
		CheckerFunc{DepName: "postgres", Fn: func(context.Context) error { return nil }},
		CheckerFunc{DepName: "redis", Fn: func(context.Context) error { return nil }},
	}})

	rec := httptest.NewRecorder()
	s.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/readyz", nil))

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, quería 200. cuerpo: %s", rec.Code, rec.Body)
	}

	var body readyzResponse
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("respuesta no es JSON válido: %v", err)
	}
	if body.Status != "ok" {
		t.Errorf("status = %q, quería \"ok\"", body.Status)
	}
	if body.Checks["postgres"] != "ok" || body.Checks["redis"] != "ok" {
		t.Errorf("checks = %v, quería todo ok", body.Checks)
	}
}

func TestReadyzDependenciaCaida(t *testing.T) {
	s := New(Options{Checkers: []Checker{
		CheckerFunc{DepName: "postgres", Fn: func(context.Context) error { return nil }},
		CheckerFunc{DepName: "neo4j", Fn: func(context.Context) error {
			return errors.New("connection refused")
		}},
	}})

	rec := httptest.NewRecorder()
	s.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/readyz", nil))

	if rec.Code != http.StatusServiceUnavailable {
		t.Fatalf("status = %d, quería 503", rec.Code)
	}

	var body readyzResponse
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("respuesta no es JSON válido: %v", err)
	}
	if body.Status != "degraded" {
		t.Errorf("status = %q, quería \"degraded\"", body.Status)
	}
	if body.Checks["neo4j"] != "connection refused" {
		t.Errorf("checks[neo4j] = %q, quería el mensaje de error", body.Checks["neo4j"])
	}
	if body.Checks["postgres"] != "ok" {
		t.Errorf("checks[postgres] = %q, quería \"ok\"", body.Checks["postgres"])
	}
}

func TestReadyzRespetaElTimeout(t *testing.T) {
	s := New(Options{
		ReadyTimeout: 50 * time.Millisecond,
		Checkers: []Checker{
			CheckerFunc{DepName: "lento", Fn: func(ctx context.Context) error {
				select {
				case <-time.After(5 * time.Second):
					return nil
				case <-ctx.Done():
					return ctx.Err()
				}
			}},
		},
	})

	start := time.Now()
	rec := httptest.NewRecorder()
	s.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/readyz", nil))
	elapsed := time.Since(start)

	if elapsed > time.Second {
		t.Errorf("tardó %v; el timeout de 50ms no se respetó", elapsed)
	}
	if rec.Code != http.StatusServiceUnavailable {
		t.Errorf("status = %d, quería 503", rec.Code)
	}
}

func TestMetodoNoPermitido(t *testing.T) {
	s := New(Options{})
	rec := httptest.NewRecorder()
	s.ServeHTTP(rec, httptest.NewRequest(http.MethodPost, "/healthz", nil))

	if rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("status = %d, quería 405", rec.Code)
	}
}
