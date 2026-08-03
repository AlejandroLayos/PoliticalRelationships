// Package httpapi expone la API HTTP de Sinapsis.
//
// De momento sólo sirve las sondas de salud (fase 0). Los endpoints de
// entidades, aristas y grafo llegan en fases posteriores; el router está
// preparado para colgarlos sin reestructurar nada.
package httpapi

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"time"
)

// Server agrupa el router y sus dependencias.
type Server struct {
	logger       *slog.Logger
	checkers     []Checker
	readyTimeout time.Duration
	graph        Graph
	mux          *http.ServeMux
}

// Options configura la construcción del servidor.
type Options struct {
	Logger *slog.Logger
	// Checkers son las dependencias que se consultan en /readyz.
	Checkers []Checker
	// ReadyTimeout acota la duración total de /readyz.
	ReadyTimeout time.Duration
	// Graph da acceso al grafo. Si es nil, las rutas de entidades responden
	// 503: la API arranca igual y /healthz sigue sirviendo.
	Graph Graph
}

// New construye el servidor y registra las rutas.
func New(opts Options) *Server {
	if opts.Logger == nil {
		opts.Logger = slog.Default()
	}
	if opts.ReadyTimeout <= 0 {
		opts.ReadyTimeout = 3 * time.Second
	}

	s := &Server{
		logger:       opts.Logger,
		checkers:     opts.Checkers,
		readyTimeout: opts.ReadyTimeout,
		graph:        opts.Graph,
		mux:          http.NewServeMux(),
	}
	s.routes()
	return s
}

func (s *Server) routes() {
	s.mux.HandleFunc("GET /healthz", s.healthz)
	s.mux.HandleFunc("GET /readyz", s.readyz)

	s.mux.HandleFunc("GET /v1/search", s.conGrafo(s.buscar))
	s.mux.HandleFunc("GET /v1/entity/{id}", s.conGrafo(s.entidad))
	s.mux.HandleFunc("GET /v1/entity/{id}/neighbors", s.conGrafo(s.vecinos))
}

// conGrafo rechaza la petición con 503 si el servidor se construyó sin acceso
// al grafo, en vez de reventar con un nil pointer.
func (s *Server) conGrafo(h http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if s.graph == nil {
			writeError(w, http.StatusServiceUnavailable, "el grafo no está disponible")
			return
		}
		h(w, r)
	}
}

// ServeHTTP hace de Server un http.Handler, con logging de acceso alrededor.
func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
	s.mux.ServeHTTP(rec, r)

	// /healthz lo golpea el orquestador cada pocos segundos; registrarlo a
	// nivel info ahogaría el log en ruido.
	level := slog.LevelInfo
	if r.URL.Path == "/healthz" || r.URL.Path == "/readyz" {
		level = slog.LevelDebug
	}
	s.logger.Log(r.Context(), level, "http",
		slog.String("method", r.Method),
		slog.String("path", r.URL.Path),
		slog.Int("status", rec.status),
		slog.Duration("duration", time.Since(start)),
	)
}

// statusRecorder captura el código de estado para el log de acceso.
type statusRecorder struct {
	http.ResponseWriter
	status      int
	wroteHeader bool
}

func (r *statusRecorder) WriteHeader(code int) {
	if r.wroteHeader {
		return
	}
	r.status = code
	r.wroteHeader = true
	r.ResponseWriter.WriteHeader(code)
}

func writeJSON(w http.ResponseWriter, code int, body any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(code)
	if err := json.NewEncoder(w).Encode(body); err != nil {
		// La cabecera ya salió; sólo queda dejar constancia.
		slog.Default().Error("no se pudo serializar la respuesta", slog.Any("error", err))
	}
}
