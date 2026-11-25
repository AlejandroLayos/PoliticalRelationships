# Estado de la última ingesta

Generado automáticamente por el workflow «Instantánea de datos».
Dice qué fuentes respondieron y qué aportaron al mapa publicado.

- Ejecución: `45638774635` · 2026-11-25T16:11:01Z

## Fuentes que no aportaron

```
### cnmv (código 1)
{"url": "https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A20001020", "detalle": "Server disconnected without sending a response.", "event": "cnmv: p\u00e1gina no disponible", "level": "warning", "timestamp": "2026-11-25T15:29:02.131202Z"}
{"url": "https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A28092583", "detalle": "Server disconnected without sending a response.", "event": "cnmv: p\u00e1gina no disponible", "level": "warning", "timestamp": "2026-11-25T15:30:02.282761Z"}
{"url": "https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A28212264", "detalle": "Server disconnected without sending a response.", "event": "cnmv: p\u00e1gina no disponible", "level": "warning", "timestamp": "2026-11-25T15:31:02.115774Z"}
{"fuente": "cnmv", "documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-11-25T15:31:02.116498Z"}
{"documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-11-25T15:31:02.116635Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-11-25T15:31:02.116703Z"}

### placsp (código 1)
{"fuente": "placsp", "params": "{'fecha_desde': datetime.date(2025, 1, 1), 'fecha_hasta': datetime.date(2025, 12, 31), 'max_paginas': 30}", "event": "ingesta iniciada", "level": "info", "timestamp": "2026-11-25T15:49:12.664262Z"}
{"url": "https://contrataciondelestado.es/sindicacion/sindicacion_1044/PlataformasAgregadasSinMenores.atom", "content_type": "text/html", "bytes": 244, "pista": "la ruta del feed ha cambiado o ya no existe; comprobar contra la especificaci\u00f3n de sindicaci\u00f3n", "event": "placsp: la ruta no sirve el feed, devuelve una p\u00e1gina HTML", "level": "error", "timestamp": "2026-11-25T15:49:13.297517Z"}
{"fuente": "placsp", "documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-11-25T15:49:13.298226Z"}
{"documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-11-25T15:49:13.298340Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-11-25T15:49:13.298374Z"}

### placsp-licitaciones (código 1)
{"fuente": "placsp", "params": "{'fecha_desde': datetime.date(2025, 1, 1), 'fecha_hasta': datetime.date(2025, 12, 31), 'max_paginas': 30}", "event": "ingesta iniciada", "level": "info", "timestamp": "2026-11-25T15:49:13.601020Z"}
{"url": "https://contrataciondelestado.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom", "content_type": "text/html", "bytes": 244, "pista": "la ruta del feed ha cambiado o ya no existe; comprobar contra la especificaci\u00f3n de sindicaci\u00f3n", "event": "placsp: la ruta no sirve el feed, devuelve una p\u00e1gina HTML", "level": "error", "timestamp": "2026-11-25T15:49:14.225232Z"}
{"fuente": "placsp", "documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-11-25T15:49:14.226143Z"}
{"documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-11-25T15:49:14.226293Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-11-25T15:49:14.226330Z"}

### placsp-menores (código 1)
{"fuente": "placsp", "params": "{'fecha_desde': datetime.date(2025, 1, 1), 'fecha_hasta': datetime.date(2025, 12, 31), 'max_paginas': 30}", "event": "ingesta iniciada", "level": "info", "timestamp": "2026-11-25T15:49:14.523548Z"}
{"url": "https://contrataciondelestado.es/sindicacion/sindicacion_1143/contratosMenoresPerfilesContratantes.atom", "content_type": "text/html", "bytes": 244, "pista": "la ruta del feed ha cambiado o ya no existe; comprobar contra la especificaci\u00f3n de sindicaci\u00f3n", "event": "placsp: la ruta no sirve el feed, devuelve una p\u00e1gina HTML", "level": "error", "timestamp": "2026-11-25T15:49:15.139537Z"}
{"fuente": "placsp", "documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-11-25T15:49:15.140258Z"}
{"documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-11-25T15:49:15.140366Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-11-25T15:49:15.140400Z"}

### cnmv-consejos (código 1)
{"url": "https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A84236934", "detalle": "Server disconnected without sending a response.", "event": "cnmv: p\u00e1gina no disponible", "level": "warning", "timestamp": "2026-11-25T16:10:24.706500Z"}
{"nif": "A84236934", "event": "cnmv: la CNMV no reconoce el NIF", "level": "warning", "timestamp": "2026-11-25T16:10:24.706740Z"}
{"desde": "A08000143", "event": "cnmv: tope de tiempo; quedan cotizadas sin leer", "level": "warning", "timestamp": "2026-11-25T16:10:24.706776Z"}
{"fuente": "cnmv", "documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-11-25T16:10:24.707492Z"}
{"documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-11-25T16:10:24.707622Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-11-25T16:10:24.707669Z"}

```

## Aporte al volcado

| fuente | entidades en el mapa |
| --- | ---: |
| Base de Datos Nacional de Subvenciones | 2398 |
| Boletín Oficial del Estado | 2342 |
| Comisión Nacional del Mercado de Valores | **0 — no aportó** |
| Congreso de los Diputados | 1477 |
| Oficina de Conflictos de Intereses | 341 |
| Plataforma de Contratación del Sector Público | **0 — no aportó** |
| Senado | 28 |
| Tribunal de Cuentas | 630 |

## Territorio de los organismos

- del Estado: 8
- con comunidad: 206
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

- días del BOE en caché: 5474
- personas: 2891 · actos del BOE: 6084
- actos del BOE leídos del 2011-12-17 al 2026-11-18
- personas con algo de cada fuente: {'boe': 2342, 'congreso': 435, 'oci': 166}
- autorizaciones (OCI): 643
- actividades declaradas (Congreso): 1196
- sociedades del mapa con un ex alto cargo autorizado: 0
- entidades del mapa con un diputado que declaró trabajar en ellas: 0
- órganos del mapa con quién los dirigió: 4
