# Estado de la última ingesta

Generado automáticamente por el workflow «Instantánea de datos».
Dice qué fuentes respondieron y qué aportaron al mapa publicado.

- Ejecución: `45838061297` · 2026-11-26T15:08:57Z

## Fuentes que no aportaron

```
### placsp-licitaciones (código 1)
{"fuente": "placsp", "params": "{'fecha_desde': datetime.date(2025, 1, 1), 'fecha_hasta': datetime.date(2025, 12, 31), 'max_paginas': 30}", "event": "ingesta iniciada", "level": "info", "timestamp": "2026-11-26T14:55:30.020333Z"}
{"url": "https://contrataciondelestado.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom", "content_type": "text/html", "bytes": 244, "pista": "la ruta del feed ha cambiado o ya no existe; comprobar contra la especificaci\u00f3n de sindicaci\u00f3n", "event": "placsp: la ruta no sirve el feed, devuelve una p\u00e1gina HTML", "level": "error", "timestamp": "2026-11-26T14:55:30.582387Z"}
{"fuente": "placsp", "documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-11-26T14:55:30.582889Z"}
{"documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-11-26T14:55:30.583016Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-11-26T14:55:30.583081Z"}

### placsp-menores (código 1)
{"fuente": "placsp", "params": "{'fecha_desde': datetime.date(2025, 1, 1), 'fecha_hasta': datetime.date(2025, 12, 31), 'max_paginas': 30}", "event": "ingesta iniciada", "level": "info", "timestamp": "2026-11-26T14:55:30.892889Z"}
{"url": "https://contrataciondelestado.es/sindicacion/sindicacion_1143/contratosMenoresPerfilesContratantes.atom", "content_type": "text/html", "bytes": 244, "pista": "la ruta del feed ha cambiado o ya no existe; comprobar contra la especificaci\u00f3n de sindicaci\u00f3n", "event": "placsp: la ruta no sirve el feed, devuelve una p\u00e1gina HTML", "level": "error", "timestamp": "2026-11-26T14:55:31.553648Z"}
{"fuente": "placsp", "documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-11-26T14:55:31.554134Z"}
{"documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-11-26T14:55:31.554284Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-11-26T14:55:31.554333Z"}

```

## Aporte al volcado

| fuente | entidades en el mapa |
| --- | ---: |
| Base de Datos Nacional de Subvenciones | 783 |
| Boletín Oficial del Estado | 2342 |
| Comisión Nacional del Mercado de Valores | 204 |
| Congreso de los Diputados | 1477 |
| Oficina de Conflictos de Intereses | 341 |
| Plataforma de Contratación del Sector Público | 2594 |
| Senado | 28 |
| Tribunal de Cuentas | 630 |

## Territorio de los organismos

- del Estado: 9
- con comunidad: 1236
- **sin clasificar: 132**

Jerarquías más repetidas entre los sin clasificar (para afinar
`ingest/sinapsis_ingest/territorio.py`):

```
4 x Servicios de La Comarca de Pamplona S.A.
4 x FUNDACION PUBLICA MIGUEL SERVET
4 x Departamento de Educación
2 x ETS - Euskal Trenbide Sarea > Euskal Trenbide Sarea
2 x Departamento de Universidad, Innovación y Transformación Digital
2 x LANTIK > LANTIK
2 x IZFE - Sociedad Foral de Servicios Informáticos > IZFE - Sociedad Foral de Servicios Informáticos
2 x Sociedad Fomento de San Sebastián > Sociedad Fomento de San Sebastián, S.A.
2 x BSTK FUNDAZIOA > BSTK FUNDAZIOA
2 x Bilbao Ekintza, E.P.E.L. > Bilbao Ekintza, E.P.E.L.
2 x Instituto Foral de Bienestar Social > Instituto Foral de Bienestar Social
1 x AZPIEGITURAK, S.A.M.P. > AZPIEGITURAK, S.A.M.P.
1 x Mancomunidad de Montejurra
1 x Departamento de Presidencia e Igualdad
1 x EuskoTrenbideak FFCC Vascos, S.A.U. > Eusko Trenbideak Ferrocarriles Vascos, S.A.
```

## Cargos públicos (BOE, OCI, Congreso)

- días del BOE en caché: 5475
- personas: 2891 · actos del BOE: 6084
- actos del BOE leídos del 2011-12-17 al 2026-11-18
- personas con algo de cada fuente: {'boe': 2342, 'congreso': 435, 'oci': 166}
- autorizaciones (OCI): 643
- actividades declaradas (Congreso): 1196
- sociedades del mapa con un ex alto cargo autorizado: 14
- entidades del mapa con un diputado que declaró trabajar en ellas: 3
- órganos del mapa con quién los dirigió: 5
