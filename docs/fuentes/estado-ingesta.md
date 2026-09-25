# Estado de la última ingesta

Generado automáticamente por el workflow «Instantánea de datos».
Dice qué fuentes respondieron y qué aportaron al mapa publicado.

- Ejecución: `36192960011` · 2026-09-25T22:40:46Z

## Fuentes que no aportaron

```
### placsp-menores (código 1)
{"fuente": "placsp", "params": "{'fecha_desde': datetime.date(2025, 1, 1), 'fecha_hasta': datetime.date(2025, 12, 31), 'max_paginas': 30}", "event": "ingesta iniciada", "level": "info", "timestamp": "2026-09-25T22:23:20.355409Z"}
{"url": "https://contrataciondelestado.es/sindicacion/sindicacion_643/contratosMenoresPerfilesContratantes.atom", "content_type": "text/html; charset=UTF-8", "bytes": 521, "pista": "la ruta del feed ha cambiado o ya no existe; comprobar contra la especificaci\u00f3n de sindicaci\u00f3n", "event": "placsp: la ruta no sirve el feed, devuelve una p\u00e1gina HTML", "level": "error", "timestamp": "2026-09-25T22:23:20.952357Z"}
{"fuente": "placsp", "documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-09-25T22:23:20.952517Z"}
{"documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-09-25T22:23:20.953133Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-09-25T22:23:20.953234Z"}

```

## Aporte al volcado

| fuente | entidades en el mapa |
| --- | ---: |
| Base de Datos Nacional de Subvenciones | 526 |
| Boletín Oficial del Estado | 256 |
| Plataforma de Contratación del Sector Público | 2851 |
| Tribunal de Cuentas | 630 |

## Territorio de los organismos

- del Estado: 369
- con comunidad: 2870
- **sin clasificar: 169**

Jerarquías más repetidas entre los sin clasificar (para afinar
`ingest/sinapsis_ingest/territorio.py`):

```
4 x Servicios de La Comarca de Pamplona S.A.
3 x Departamento de Educación
3 x Departamento de Universidad, Innovación y Transformación Digital
3 x Departamento de Economía y Hacienda
2 x ETS - Euskal Trenbide Sarea > Euskal Trenbide Sarea
2 x BIDEGI, S.A. > BIDEGI Agencia Guipuzcoana de Infraestructuras
2 x IZFE - Sociedad Foral de Servicios Informáticos > IZFE - Sociedad Foral de Servicios Informáticos
2 x Bilbao Ekintza, E.P.E.L. > Bilbao Ekintza, E.P.E.L.
2 x Ayuntamiento de Abanto Zierbena > Ayuntamiento de Abanto Zierbena
2 x ITELAZPI, S.A. > ITELAZPI, S.A.
2 x Bilbao Kirolak-Instituto Municipal de Deportes S.A. > Bilbao Kirolak
2 x Sector Público > OTRAS ENTIDADES DEL SECTOR PÚBLICO > MUTUAS DE ACCIDENTES DE TRABAJO COLABORADORAS DE LA SEGURIDAD SOCIAL > ASEPEYO
2 x Sociedad Fomento de San Sebastián > Sociedad Fomento de San Sebastián, S.A.
2 x Departamento de Cultura, Deporte y Turismo
2 x Donostia Kultura > Donostia Kultura
```

## Altos cargos (BOE)

- días del BOE en caché: 500
- personas: 256 · actos: 355
- actos leídos del 2025-05-14 al 2026-09-16
