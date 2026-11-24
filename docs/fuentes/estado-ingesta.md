# Estado de la última ingesta

Generado automáticamente por el workflow «Instantánea de datos».
Dice qué fuentes respondieron y qué aportaron al mapa publicado.

- Ejecución: `45422687472` · 2026-11-24T15:37:56Z

## Fuentes que no aportaron

```
### cnmv (código 1)
{"url": "https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A20001020", "detalle": "Server error '504 Gateway Timeout' for url 'https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A20001020'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/504", "event": "cnmv: p\u00e1gina no disponible", "level": "warning", "timestamp": "2026-11-24T15:15:08.158835Z"}
{"url": "https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A28092583", "detalle": "Server error '504 Gateway Timeout' for url 'https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A28092583'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/504", "event": "cnmv: p\u00e1gina no disponible", "level": "warning", "timestamp": "2026-11-24T15:15:08.361487Z"}
{"url": "https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A28212264", "detalle": "Server error '504 Gateway Timeout' for url 'https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A28212264'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/504", "event": "cnmv: p\u00e1gina no disponible", "level": "warning", "timestamp": "2026-11-24T15:15:08.564857Z"}
{"fuente": "cnmv", "documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-11-24T15:15:08.565090Z"}
{"documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-11-24T15:15:08.565209Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-11-24T15:15:08.565228Z"}

### placsp (código 1)
{"fuente": "placsp", "params": "{'fecha_desde': datetime.date(2025, 1, 1), 'fecha_hasta': datetime.date(2025, 12, 31), 'max_paginas': 30}", "event": "ingesta iniciada", "level": "info", "timestamp": "2026-11-24T15:20:50.281552Z"}
{"url": "https://contrataciondelestado.es/sindicacion/sindicacion_1044/PlataformasAgregadasSinMenores.atom", "content_type": "text/html", "bytes": 244, "pista": "la ruta del feed ha cambiado o ya no existe; comprobar contra la especificaci\u00f3n de sindicaci\u00f3n", "event": "placsp: la ruta no sirve el feed, devuelve una p\u00e1gina HTML", "level": "error", "timestamp": "2026-11-24T15:20:51.222523Z"}
{"fuente": "placsp", "documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-11-24T15:20:51.222935Z"}
{"documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-11-24T15:20:51.223016Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-11-24T15:20:51.223037Z"}

### placsp-licitaciones (código 1)
{"fuente": "placsp", "params": "{'fecha_desde': datetime.date(2025, 1, 1), 'fecha_hasta': datetime.date(2025, 12, 31), 'max_paginas': 30}", "event": "ingesta iniciada", "level": "info", "timestamp": "2026-11-24T15:20:51.447414Z"}
{"url": "https://contrataciondelestado.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom", "content_type": "text/html", "bytes": 244, "pista": "la ruta del feed ha cambiado o ya no existe; comprobar contra la especificaci\u00f3n de sindicaci\u00f3n", "event": "placsp: la ruta no sirve el feed, devuelve una p\u00e1gina HTML", "level": "error", "timestamp": "2026-11-24T15:20:52.186195Z"}
{"fuente": "placsp", "documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-11-24T15:20:52.186594Z"}
{"documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-11-24T15:20:52.186680Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-11-24T15:20:52.186702Z"}

### placsp-menores (código 1)
{"fuente": "placsp", "params": "{'fecha_desde': datetime.date(2025, 1, 1), 'fecha_hasta': datetime.date(2025, 12, 31), 'max_paginas': 30}", "event": "ingesta iniciada", "level": "info", "timestamp": "2026-11-24T15:20:52.409419Z"}
{"url": "https://contrataciondelestado.es/sindicacion/sindicacion_1143/contratosMenoresPerfilesContratantes.atom", "content_type": "text/html", "bytes": 244, "pista": "la ruta del feed ha cambiado o ya no existe; comprobar contra la especificaci\u00f3n de sindicaci\u00f3n", "event": "placsp: la ruta no sirve el feed, devuelve una p\u00e1gina HTML", "level": "error", "timestamp": "2026-11-24T15:20:53.176637Z"}
{"fuente": "placsp", "documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-11-24T15:20:53.177086Z"}
{"documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-11-24T15:20:53.177178Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-11-24T15:20:53.177201Z"}

```

## Aporte al volcado

| fuente | entidades en el mapa |
| --- | ---: |
| Base de Datos Nacional de Subvenciones | 3377 |
| Boletín Oficial del Estado | 2342 |
| Comisión Nacional del Mercado de Valores | **0 — no aportó** |
| Congreso de los Diputados | 1477 |
| Oficina de Conflictos de Intereses | 341 |
| Plataforma de Contratación del Sector Público | **0 — no aportó** |
| Senado | 28 |
| Tribunal de Cuentas | 630 |

## Territorio de los organismos

- del Estado: 9
- con comunidad: 218
- **sin clasificar: 11**

Jerarquías más repetidas entre los sin clasificar (para afinar
`ingest/sinapsis_ingest/territorio.py`):

```
1 x OTROS > CÁMARA DE COMERCIO DE VALENCIA
1 x LOCAL > CONSEJO INSULAR DE MALLORCA > CONSELL INSULAR DE MALLORCA
1 x LOCAL > CABILDO INSULAR DE TENERIFE > CABILDO INSULAR DE TENERIFE
1 x LOCAL > CABILDO INSULAR DE LANZAROTE > CABILDO INSULAR DE LANZAROTE
1 x LOCAL > CABILDO INSULAR DE FUERTEVENTURA > CABILDO INSULAR DE FUERTEVENTURA
1 x LOCAL > ALCOY/ALCOI > AYUNTAMIENTO DE ALCOY/ALCOI
1 x LOCAL > CONSELL COMARCAL DE ALT PENEDÈS > CONSELL COMARCAL DE ALT PENEDÈS
1 x LOCAL > CONSELL COMARCAL DE ALT URGELL > CONSELL COMARCAL DE ALT URGELL
1 x LOCAL > ENTIDAD METROPOLITANA DE SERVICIOS HIDRÁULICOS > ENTIDAD METROPOLITANA DE SERVICIOS HIDRÁULICOS
1 x OTROS > UNIVERSIDAD JAUME I DE CASTELLÓN
1 x (ninguna)
```

## Cargos públicos (BOE, OCI, Congreso)

- días del BOE en caché: 5473
- personas: 2891 · actos del BOE: 6084
- actos del BOE leídos del 2011-12-17 al 2026-11-18
- personas con algo de cada fuente: {'boe': 2342, 'congreso': 435, 'oci': 166}
- autorizaciones (OCI): 643
- actividades declaradas (Congreso): 1196
- sociedades del mapa con un ex alto cargo autorizado: 1
- entidades del mapa con un diputado que declaró trabajar en ellas: 1
- órganos del mapa con quién los dirigió: 5
