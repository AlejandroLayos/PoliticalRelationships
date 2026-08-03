# syntax=docker/dockerfile:1

FROM golang:1.25-alpine AS build
WORKDIR /src

# Capa de dependencias aparte: cambiar código no invalida la caché de módulos.
COPY go.mod go.sum ./
RUN go mod download

COPY . .
# CGO desactivado para obtener un binario estático que corra en `scratch`.
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/api ./cmd/api

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/api /api
EXPOSE 8080
USER nonroot:nonroot
ENTRYPOINT ["/api"]
