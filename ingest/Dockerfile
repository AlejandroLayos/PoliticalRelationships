# syntax=docker/dockerfile:1

# followthemoney arrastra PyICU, que se compila desde fuente y necesita las
# cabeceras de ICU y pkg-config. Los aislamos en una etapa de build para no
# cargar el compilador en la imagen final.
FROM python:3.11-slim AS build
WORKDIR /src

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        libicu-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml ./
COPY sinapsis_ingest ./sinapsis_ingest
RUN pip install --no-cache-dir .

FROM python:3.11-slim
# PyICU enlaza dinámicamente, así que libicu hace falta también en runtime.
# El número de versión del paquete (libicu72, libicu74...) depende de la
# release de Debian de la imagen base, y cambia sin avisar al actualizarla:
# lo resolvemos en tiempo de build en vez de fijarlo y que reviente luego.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        "$(apt-cache search --names-only '^libicu[0-9]+$' | cut -d' ' -f1 | sort -V | tail -1)" \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 sinapsis

COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER sinapsis
ENTRYPOINT ["sinapsis-worker"]
