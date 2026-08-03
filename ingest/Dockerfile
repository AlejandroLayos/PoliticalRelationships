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
# libicu se necesita también en runtime: en build sólo compilamos contra ella.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libicu74 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 sinapsis

COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER sinapsis
ENTRYPOINT ["sinapsis-worker"]
