package config

import (
	"testing"
	"time"
)

func TestLoadDefaults(t *testing.T) {
	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() error inesperado: %v", err)
	}
	if cfg.HTTPAddr != ":8080" {
		t.Errorf("HTTPAddr = %q, quería \":8080\"", cfg.HTTPAddr)
	}
	if cfg.ShutdownTimeout != 15*time.Second {
		t.Errorf("ShutdownTimeout = %v, quería 15s", cfg.ShutdownTimeout)
	}
}

func TestLoadOverridesFromEnv(t *testing.T) {
	t.Setenv("SINAPSIS_HTTP_ADDR", ":9999")
	t.Setenv("SINAPSIS_POSTGRES_DSN", "postgres://x/y")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() error inesperado: %v", err)
	}
	if cfg.HTTPAddr != ":9999" {
		t.Errorf("HTTPAddr = %q, quería \":9999\"", cfg.HTTPAddr)
	}
	if cfg.PostgresDSN != "postgres://x/y" {
		t.Errorf("PostgresDSN = %q, quería \"postgres://x/y\"", cfg.PostgresDSN)
	}
}

func TestEnvDuration(t *testing.T) {
	tests := []struct {
		name    string
		value   string
		want    time.Duration
		wantErr bool
	}{
		{name: "vacío usa el defecto", value: "", want: 5 * time.Second},
		{name: "formato Go", value: "45s", want: 45 * time.Second},
		{name: "segundos enteros", value: "90", want: 90 * time.Second},
		{name: "basura da error", value: "mañana", wantErr: true},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			t.Setenv("SINAPSIS_TEST_DURATION", tc.value)
			got, err := envDuration("SINAPSIS_TEST_DURATION", 5*time.Second)
			if tc.wantErr {
				if err == nil {
					t.Fatalf("envDuration(%q) no dio error, quería uno", tc.value)
				}
				return
			}
			if err != nil {
				t.Fatalf("envDuration(%q) error inesperado: %v", tc.value, err)
			}
			if got != tc.want {
				t.Errorf("envDuration(%q) = %v, quería %v", tc.value, got, tc.want)
			}
		})
	}
}
