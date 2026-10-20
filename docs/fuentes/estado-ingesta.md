# Estado de la última ingesta

Generado automáticamente por el workflow «Instantánea de datos».
Dice qué fuentes respondieron y qué aportaron al mapa publicado.

- Ejecución: `39401804490` · 2026-10-20T11:12:27Z

## Fuentes que no aportaron

```
### bdns (código 1)
{"fuente": "bdns", "params": "{'fecha_desde': datetime.date(2025, 1, 1), 'fecha_hasta': datetime.date(2025, 12, 31), 'max_paginas': 30}", "event": "ingesta iniciada", "level": "info", "timestamp": "2026-10-20T09:46:04.756208Z"}
{"url": "https://www.infosubvenciones.es/bdnstrans/api/concesiones/busqueda?pageSize=1000&fechaDesde=01%2F01%2F2025&fechaHasta=31%2F12%2F2025&page=0", "event": "bdns: la respuesta no trae lista de concesiones", "level": "warning", "timestamp": "2026-10-20T09:47:05.365396Z"}
{"fuente": "bdns", "documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-10-20T09:47:05.366033Z"}
{"documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-10-20T09:47:05.366140Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-10-20T09:47:05.366180Z"}

```

## Aporte al volcado

| fuente | entidades en el mapa |
| --- | ---: |
| Base de Datos Nacional de Subvenciones | 524 |
| Boletín Oficial del Estado | 2330 |
| Comisión Nacional del Mercado de Valores | 199 |
| Congreso de los Diputados | 1477 |
| Oficina de Conflictos de Intereses | 341 |
| Plataforma de Contratación del Sector Público | 2853 |
| Senado | 28 |
| Tribunal de Cuentas | 630 |

## Territorio de los organismos

- del Estado: 374
- con comunidad: 2564
- **sin clasificar: 166**

Jerarquías más repetidas entre los sin clasificar (para afinar
`ingest/sinapsis_ingest/territorio.py`):

```
3 x NEIKER, Instituto Vasco de Investigación y Desarrollo Agrario, S.A. > NEIKER, Instituto Vasco de Investigación y Desarrollo Agrario, S.A.
3 x Sector Público > OTRAS ENTIDADES DEL SECTOR PÚBLICO > MUTUAS DE ACCIDENTES DE TRABAJO COLABORADORAS DE LA SEGURIDAD SOCIAL > ASEPEYO
2 x ETS - Euskal Trenbide Sarea > Euskal Trenbide Sarea
2 x LANTIK > LANTIK
2 x Departamento de Universidad, Innovación y Transformación Digital
2 x Servicios de La Comarca de Pamplona S.A.
2 x Bilbao Kirolak-Instituto Municipal de Deportes S.A. > Bilbao Kirolak
2 x IZFE - Sociedad Foral de Servicios Informáticos > IZFE - Sociedad Foral de Servicios Informáticos
2 x Ayuntamiento de la Anteiglesia de Erandio > Ayuntamiento de la Anteiglesia de Erandio
2 x Aguas del Añarbe-Añarbeko Urak, S.A. > AGASA
2 x Sociedad Fomento de San Sebastián > Sociedad Fomento de San Sebastián, S.A.
2 x Desarrollo Rural y Medio Ambiente
2 x Fundación Juan Crisóstomo de Arriaga-Orquesta Sinfónica de Bilbao > Fundación Juan Crisóstomo de Arriaga-Orquesta Sinfónica de Bilbao
2 x Bilbao Ekintza, E.P.E.L. > Bilbao Ekintza, E.P.E.L.
2 x Instituto Foral de Bienestar Social > Instituto Foral de Bienestar Social
```

## Cargos públicos (BOE, OCI, Congreso)

- días del BOE en caché: 5438
- personas: 2879 · actos del BOE: 6049
- actos del BOE leídos del 2011-12-17 al 2026-10-15
- personas con algo de cada fuente: {'boe': 2330, 'congreso': 435, 'oci': 166}
- autorizaciones (OCI): 643
- actividades declaradas (Congreso): 1196
- sociedades del mapa con un ex alto cargo autorizado: 13
- entidades del mapa con un diputado que declaró trabajar en ellas: 8
- órganos del mapa con quién los dirigió: 36
