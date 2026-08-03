# Instantáneas del grafo

`grafo.json` **no está en el repositorio a propósito**: lo genera el workflow
`.github/workflows/datos.yml` a partir de las fuentes públicas reales, y lo
commitea él.

No lo generes a mano desde una base de pruebas. Los fixtures de
`ingest/tests/golden/` incluyen una muestra **sintética** de BDNS, y un volcado
que la mezclara con datos reales se publicaría bajo el cartel «datos reales de
BDNS, PLACSP». Eso es precisamente la confusión que el proyecto existe para
evitar.

Mientras este fichero no exista, la web muestra el conjunto de demostración con
su aviso, que es honesto: no hay datos reales que enseñar todavía.

Para generarlo: **Actions → Instantánea de datos → Run workflow**.
