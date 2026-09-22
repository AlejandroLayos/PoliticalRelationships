# Estado de la última ingesta

Generado automáticamente por el workflow «Instantánea de datos».
Dice qué fuentes respondieron y qué aportaron al mapa publicado.

- Ejecución: `35726332414` · 2026-09-22T13:47:23Z

## Fuentes que no aportaron

```
### placsp-menores (código 1)
{"fuente": "placsp", "params": "{'fecha_desde': datetime.date(2025, 1, 1), 'fecha_hasta': datetime.date(2025, 12, 31), 'max_paginas': 30}", "event": "ingesta iniciada", "level": "info", "timestamp": "2026-09-22T13:43:06.709586Z"}
{"url": "https://contrataciondelestado.es/sindicacion/sindicacion_643/contratosMenoresPerfilesContratantes.atom", "content_type": "text/html; charset=UTF-8", "bytes": 521, "pista": "la ruta del feed ha cambiado o ya no existe; comprobar contra la especificaci\u00f3n de sindicaci\u00f3n", "event": "placsp: la ruta no sirve el feed, devuelve una p\u00e1gina HTML", "level": "error", "timestamp": "2026-09-22T13:43:07.368274Z"}
{"fuente": "placsp", "documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-09-22T13:43:07.368398Z"}
{"documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-09-22T13:43:07.368743Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-09-22T13:43:07.368770Z"}

```

## Aporte al volcado

| fuente | entidades en el mapa |
| --- | ---: |
| Base de Datos Nacional de Subvenciones | 558 |
| Plataforma de Contratación del Sector Público | 2821 |
| Tribunal de Cuentas | 630 |
