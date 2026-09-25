# Estado de la última ingesta

Generado automáticamente por el workflow «Instantánea de datos».
Dice qué fuentes respondieron y qué aportaron al mapa publicado.

- Ejecución: `36186851973` · 2026-09-25T21:26:01Z

## Fuentes que no aportaron

```
### placsp-menores (código 1)
{"fuente": "placsp", "params": "{'fecha_desde': datetime.date(2025, 1, 1), 'fecha_hasta': datetime.date(2025, 12, 31), 'max_paginas': 30}", "event": "ingesta iniciada", "level": "info", "timestamp": "2026-09-25T21:17:00.251624Z"}
{"url": "https://contrataciondelestado.es/sindicacion/sindicacion_643/contratosMenoresPerfilesContratantes.atom", "content_type": "text/html; charset=UTF-8", "bytes": 521, "pista": "la ruta del feed ha cambiado o ya no existe; comprobar contra la especificaci\u00f3n de sindicaci\u00f3n", "event": "placsp: la ruta no sirve el feed, devuelve una p\u00e1gina HTML", "level": "error", "timestamp": "2026-09-25T21:17:00.732127Z"}
{"fuente": "placsp", "documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-09-25T21:17:00.732312Z"}
{"documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-09-25T21:17:00.733288Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-09-25T21:17:00.733351Z"}

```

## Aporte al volcado

| fuente | entidades en el mapa |
| --- | ---: |
| Base de Datos Nacional de Subvenciones | 526 |
| Plataforma de Contratación del Sector Público | 2851 |
| Tribunal de Cuentas | 630 |

## Territorio de los organismos

- del Estado: 368
- con comunidad: 2197
- **sin clasificar: 829**

Jerarquías más repetidas entre los sin clasificar (para afinar
`ingest/sinapsis_ingest/territorio.py`):

```
379 x Entitats de l'administració local
10 x Ayuntamiento de Vitoria-Gasteiz > Ayuntamiento de Vitoria-Gasteiz
10 x Universitats
5 x Altres ens
5 x Servicio Navarro de Salud - Osasunbidea
4 x Servicios de La Comarca de Pamplona S.A.
3 x Ayuntamiento de Irun > Ayuntamiento de Irun
3 x Ayuntamiento de Pamplona
3 x Ayuntamiento de Hernani > Ayuntamiento de Hernani
3 x Ayuntamiento deLekeitio > Ayuntamiento de Lekeitio
3 x Ayuntamiento de Santurtzi > Ayuntamiento de Santurtzi
3 x Departamento de Educación
3 x Departamento de Universidad, Innovación y Transformación Digital
3 x Departamento de Economía y Hacienda
3 x Ayuntamiento de Burlada
```
