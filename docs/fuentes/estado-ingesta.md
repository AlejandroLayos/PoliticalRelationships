# Estado de la última ingesta

Generado automáticamente por el workflow «Instantánea de datos».
Dice qué fuentes respondieron y qué aportaron al mapa publicado.

- Ejecución: `35342702683` · 2026-09-18T12:13:31Z

## Fuentes que no aportaron

```
### bdns (código 1)
{"fuente": "bdns", "params": "{'fecha_desde': datetime.date(2025, 1, 1), 'fecha_hasta': datetime.date(2025, 12, 31), 'max_paginas': 12}", "event": "ingesta iniciada", "level": "info", "timestamp": "2026-09-18T12:05:26.660047Z"}
{"pagina": 0, "error": "timed out", "event": "bdns: fallo al descargar p\u00e1gina", "level": "warning", "timestamp": "2026-09-18T12:05:56.824285Z"}
{"fuente": "bdns", "documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-09-18T12:05:56.825049Z"}
{"documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-09-18T12:05:56.825227Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-09-18T12:05:56.825291Z"}

### bdns-partidos (código 1)
{"fuente": "bdns", "params": "{'fecha_desde': datetime.date(2025, 1, 1), 'fecha_hasta': datetime.date(2025, 12, 31), 'max_paginas': 12}", "event": "ingesta iniciada", "level": "info", "timestamp": "2026-09-18T12:05:57.094171Z"}
{"pagina": 0, "error": "timed out", "event": "bdns: fallo al descargar p\u00e1gina", "level": "warning", "timestamp": "2026-09-18T12:06:27.162725Z"}
{"fuente": "bdns", "documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-09-18T12:06:27.163546Z"}
{"documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-09-18T12:06:27.163713Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-09-18T12:06:27.163770Z"}

### tcu (código 1)
{"url": "https://www.tcu.es/export/sites/portal/.galleries/Documentos-oficiales/Partidos-politicos/Procedimientos-sancionadores-contabilidad-electoral-2019.pdf", "detalle": "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1016)", "event": "tcu: documento no disponible", "level": "warning", "timestamp": "2026-09-18T12:10:25.431147Z"}
{"url": "https://www.tcu.es/export/sites/portal/.galleries/Documentos-oficiales/Partidos-politicos/Procedimientos-sancionadores-contabilidad-electoral-2023.pdf", "detalle": "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1016)", "event": "tcu: documento no disponible", "level": "warning", "timestamp": "2026-09-18T12:10:26.029790Z"}
{"url": "https://www.tcu.es/export/sites/portal/.galleries/Documentos-oficiales/Partidos-politicos/Procedimientos-sancionadores-contabilidad-ordinaria.pdf", "detalle": "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1016)", "event": "tcu: documento no disponible", "level": "warning", "timestamp": "2026-09-18T12:10:26.638247Z"}
{"fuente": "tcu", "documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-09-18T12:10:26.638924Z"}
{"documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-09-18T12:10:26.639072Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-09-18T12:10:26.639165Z"}

```

## Aporte al volcado

| fuente | entidades en el mapa |
| --- | ---: |
| Base de Datos Nacional de Subvenciones | **0 — no aportó** |
| Plataforma de Contratación del Sector Público | 4000 |
| Tribunal de Cuentas | **0 — no aportó** |
