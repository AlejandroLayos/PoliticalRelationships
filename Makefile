.DEFAULT_GOAL := help
SHELL := /bin/bash

COMPOSE ?= docker compose
PG_DSN  ?= postgres://sinapsis:sinapsis@localhost:5432/sinapsis?sslmode=disable

.PHONY: help
help: ## Muestra esta ayuda
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# --- pila local ------------------------------------------------------------

.PHONY: up
up: ## Levanta la pila completa
	$(COMPOSE) up --build -d

.PHONY: down
down: ## Para la pila (conserva los volúmenes)
	$(COMPOSE) down

.PHONY: logs
logs: ## Sigue los logs de todos los servicios
	$(COMPOSE) logs -f

.PHONY: ps
ps: ## Estado de los servicios
	$(COMPOSE) ps

.PHONY: health
health: ## Comprueba que la API responde
	@curl -fsS http://localhost:8080/healthz && echo
	@curl -sS http://localhost:8080/readyz && echo

# --- migraciones -----------------------------------------------------------

.PHONY: migrate
migrate: ## Aplica las migraciones pendientes
	$(COMPOSE) run --rm migrate

.PHONY: migrate-down
migrate-down: ## Revierte la última migración
	$(COMPOSE) run --rm migrate -path=/migrations -database="$(PG_DSN)" down 1

# --- desarrollo ------------------------------------------------------------

.PHONY: test
test: test-backend test-ingest ## Ejecuta todos los tests

.PHONY: test-backend
test-backend: ## Tests de Go
	cd backend && go test -race ./...

.PHONY: test-ingest
test-ingest: ## Tests de Python
	cd ingest && pytest

.PHONY: lint
lint: ## Linters de ambos lenguajes
	cd backend && go vet ./... && gofmt -l .
	cd ingest && ruff check . && ruff format --check .

.PHONY: fmt
fmt: ## Formatea el código
	cd backend && gofmt -w .
	cd ingest && ruff format . && ruff check --fix .
