# Estado de la última ingesta

Generado automáticamente por el workflow «Instantánea de datos».
Dice qué fuentes respondieron y qué aportaron al mapa publicado.

- Ejecución: `40307528994` · 2026-10-26T12:07:19Z

## Fuentes que no aportaron

```
### bdns (código 1)
{"fuente": "bdns", "params": "{'fecha_desde': datetime.date(2025, 1, 1), 'fecha_hasta': datetime.date(2025, 12, 31), 'max_paginas': 30}", "event": "ingesta iniciada", "level": "info", "timestamp": "2026-10-26T10:40:47.725750Z"}
{"url": "https://www.infosubvenciones.es/bdnstrans/api/concesiones/busqueda?pageSize=1000&fechaDesde=01%2F01%2F2025&fechaHasta=31%2F12%2F2025&page=0", "event": "bdns: la respuesta no trae lista de concesiones", "level": "warning", "timestamp": "2026-10-26T10:41:48.190215Z"}
{"fuente": "bdns", "documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-10-26T10:41:48.190909Z"}
{"documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-10-26T10:41:48.191033Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-10-26T10:41:48.191077Z"}

```

## Aporte al volcado

| fuente | entidades en el mapa |
| --- | ---: |
| Base de Datos Nacional de Subvenciones | 524 |
| Boletín Oficial del Estado | 2336 |
| Comisión Nacional del Mercado de Valores | 198 |
| Congreso de los Diputados | 1477 |
| Oficina de Conflictos de Intereses | 341 |
| Plataforma de Contratación del Sector Público | 2852 |
| Senado | 28 |
| Tribunal de Cuentas | 630 |

## Territorio de los organismos

- del Estado: 347
- con comunidad: 2438
- **sin clasificar: 145**

Jerarquías más repetidas entre los sin clasificar (para afinar
`ingest/sinapsis_ingest/territorio.py`):

```
3 x IZFE - Sociedad Foral de Servicios Informáticos > IZFE - Sociedad Foral de Servicios Informáticos
2 x ETS - Euskal Trenbide Sarea > Euskal Trenbide Sarea
2 x LANTIK > LANTIK
2 x Sector Público > OTRAS ENTIDADES DEL SECTOR PÚBLICO > MUTUAS DE ACCIDENTES DE TRABAJO COLABORADORAS DE LA SEGURIDAD SOCIAL > ASEPEYO
2 x Departamento de Universidad, Innovación y Transformación Digital
2 x Ayuntamiento de la Anteiglesia de Erandio > Ayuntamiento de la Anteiglesia de Erandio
2 x Desarrollo Rural y Medio Ambiente
2 x NEIKER, Instituto Vasco de Investigación y Desarrollo Agrario, S.A. > NEIKER, Instituto Vasco de Investigación y Desarrollo Agrario, S.A.
2 x Sociedad Fomento de San Sebastián > Sociedad Fomento de San Sebastián, S.A.
2 x Bilbao Kirolak-Instituto Municipal de Deportes S.A. > Bilbao Kirolak
2 x Departamento de Economía y Hacienda
1 x EuskoTrenbideak FFCC Vascos, S.A.U. > Eusko Trenbideak Ferrocarriles Vascos, S.A.
1 x Aguas Municipales de Vitoria-Gasteiz, S.A.U. > Aguas Municipales de Vitoria-Gasteiz, S.A.U.
1 x ZUGAZTEL, M. P., S. A. > ZUGAZTEL, M. P., S. A.
1 x Sector Público > OTRAS ENTIDADES DEL SECTOR PÚBLICO > INSTITUCIONES INDEPENDIENTES > Sociedad de Gestión de Activos procedentes de la Reestructuración Bancaria, S.A
```

## Cargos públicos (BOE, OCI, Congreso)

- días del BOE en caché: 5444
- personas: 2885 · actos del BOE: 6062
- actos del BOE leídos del 2011-12-17 al 2026-10-21
- personas con algo de cada fuente: {'boe': 2336, 'congreso': 435, 'oci': 166}
- autorizaciones (OCI): 643
- actividades declaradas (Congreso): 1196
- sociedades del mapa con un ex alto cargo autorizado: 17
- entidades del mapa con un diputado que declaró trabajar en ellas: 5
- órganos del mapa con quién los dirigió: 29
