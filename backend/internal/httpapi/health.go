package httpapi

import (
	"context"
	"net/http"
	"sync"
	"time"
)

// Checker comprueba que una dependencia externa responde. Devuelve nil si la
// dependencia está sana.
type Checker interface {
	// Name identifica la dependencia en la respuesta de /readyz.
	Name() string
	// Check debe respetar la cancelación del contexto.
	Check(ctx context.Context) error
}

// CheckerFunc adapta una función al interfaz Checker.
type CheckerFunc struct {
	DepName string
	Fn      func(ctx context.Context) error
}

func (c CheckerFunc) Name() string                    { return c.DepName }
func (c CheckerFunc) Check(ctx context.Context) error { return c.Fn(ctx) }

// healthz es la sonda de liveness: responde 200 mientras el proceso esté vivo
// y sea capaz de servir HTTP. Deliberadamente NO consulta dependencias — si lo
// hiciera, una caída de Postgres provocaría que el orquestador reiniciara en
// bucle un proceso que en realidad está sano.
func (s *Server) healthz(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// readyzResponse es el cuerpo de /readyz.
type readyzResponse struct {
	Status string            `json:"status"`
	Checks map[string]string `json:"checks"`
}

// readyz es la sonda de readiness: comprueba en paralelo cada dependencia y
// devuelve 503 si alguna falla, para que el balanceador saque la instancia del
// pool sin reiniciarla.
func (s *Server) readyz(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), s.readyTimeout)
	defer cancel()

	var (
		mu      sync.Mutex
		wg      sync.WaitGroup
		checks  = make(map[string]string, len(s.checkers))
		healthy = true
	)

	for _, c := range s.checkers {
		wg.Add(1)
		go func(c Checker) {
			defer wg.Done()
			result := "ok"
			if err := c.Check(ctx); err != nil {
				result = err.Error()
			}
			mu.Lock()
			defer mu.Unlock()
			checks[c.Name()] = result
			if result != "ok" {
				healthy = false
			}
		}(c)
	}
	wg.Wait()

	body := readyzResponse{Status: "ok", Checks: checks}
	code := http.StatusOK
	if !healthy {
		body.Status = "degraded"
		code = http.StatusServiceUnavailable
	}
	writeJSON(w, code, body)
}

// pingWithTimeout envuelve un ping con un plazo propio, para que una
// dependencia colgada no consuma todo el presupuesto de /readyz.
func pingWithTimeout(ctx context.Context, d time.Duration, fn func(context.Context) error) error {
	ctx, cancel := context.WithTimeout(ctx, d)
	defer cancel()
	return fn(ctx)
}
