// Command api sirve la API HTTP de Sinapsis.
package main

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/AlejandroLayos/PoliticalRelationships/backend/internal/config"
	"github.com/AlejandroLayos/PoliticalRelationships/backend/internal/httpapi"
	"github.com/AlejandroLayos/PoliticalRelationships/backend/internal/store"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))
	slog.SetDefault(logger)

	if err := run(logger); err != nil {
		logger.Error("la api terminó con error", slog.Any("error", err))
		os.Exit(1)
	}
}

func run(logger *slog.Logger) error {
	cfg, err := config.Load()
	if err != nil {
		return fmt.Errorf("cargando configuración: %w", err)
	}

	// Escuchamos SIGINT/SIGTERM desde el principio para que un Ctrl+C durante
	// el arranque no deje conexiones a medias.
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	// La API arranca aunque Postgres todavía no acepte conexiones: el pool de
	// pgx conecta de forma perezosa y /readyz reflejará el estado real. Así
	// `docker compose up` no depende del orden de arranque.
	pg, err := store.Open(ctx, cfg.PostgresDSN)
	if err != nil {
		return fmt.Errorf("abriendo postgres: %w", err)
	}
	defer pg.Close()

	srv := &http.Server{
		Addr: cfg.HTTPAddr,
		Handler: httpapi.New(httpapi.Options{
			Logger:       logger,
			ReadyTimeout: cfg.ReadyTimeout,
			Graph:        pg,
			Checkers: []httpapi.Checker{
				httpapi.CheckerFunc{DepName: "postgres", Fn: pg.Ping},
			},
		}),
		ReadHeaderTimeout: 10 * time.Second,
		ReadTimeout:       30 * time.Second,
		WriteTimeout:      60 * time.Second,
		IdleTimeout:       120 * time.Second,
	}

	errCh := make(chan error, 1)
	go func() {
		logger.Info("api escuchando", slog.String("addr", cfg.HTTPAddr))
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			errCh <- err
		}
	}()

	select {
	case err := <-errCh:
		return fmt.Errorf("servidor http: %w", err)
	case <-ctx.Done():
		logger.Info("señal de parada recibida, cerrando ordenadamente")
	}

	shutdownCtx, cancel := context.WithTimeout(context.Background(), cfg.ShutdownTimeout)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		return fmt.Errorf("cierre ordenado: %w", err)
	}
	logger.Info("api detenida")
	return nil
}
