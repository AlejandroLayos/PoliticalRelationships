# Estado de la última ingesta

Generado automáticamente por el workflow «Instantánea de datos».
Dice qué fuentes respondieron y qué aportaron al mapa publicado.

- Ejecución: `36226425244` · 2026-09-26T08:11:10Z

## Fuentes que no aportaron

```
### bdns (código 1)
{"fuente": "bdns", "params": "{'fecha_desde': datetime.date(2025, 1, 1), 'fecha_hasta': datetime.date(2025, 12, 31), 'max_paginas': 30}", "event": "ingesta iniciada", "level": "info", "timestamp": "2026-09-26T07:21:59.561004Z"}
{"url": "https://www.infosubvenciones.es/bdnstrans/api/concesiones/busqueda?pageSize=1000&fechaDesde=01%2F01%2F2025&fechaHasta=31%2F12%2F2025&page=0", "event": "bdns: la respuesta no trae lista de concesiones", "level": "warning", "timestamp": "2026-09-26T07:23:00.007543Z"}
{"fuente": "bdns", "documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-09-26T07:23:00.008109Z"}
{"documentos_nuevos": 1, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-09-26T07:23:00.008210Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-09-26T07:23:00.008247Z"}

```

## Aporte al volcado

| fuente | entidades en el mapa |
| --- | ---: |
| Base de Datos Nacional de Subvenciones | 524 |
| Boletín Oficial del Estado | 1841 |
| Congreso de los Diputados | 1477 |
| Oficina de Conflictos de Intereses | 341 |
| Plataforma de Contratación del Sector Público | 2853 |
| Senado | 28 |
| Tribunal de Cuentas | 630 |

## Territorio de los organismos

- del Estado: 494
- con comunidad: 3808
- **sin clasificar: 202**

Jerarquías más repetidas entre los sin clasificar (para afinar
`ingest/sinapsis_ingest/territorio.py`):

```
4 x Servicios de La Comarca de Pamplona S.A.
3 x Departamento de Cultura, Deporte y Turismo
3 x IZFE - Sociedad Foral de Servicios Informáticos > IZFE - Sociedad Foral de Servicios Informáticos
3 x Departamento de Universidad, Innovación y Transformación Digital
3 x Departamento de Economía y Hacienda
3 x Departamento de Educación
3 x Sector Público > COMUNIDADES Y CIUDADES AUTÓNOMAS > Castilla - La Mancha
2 x LANTIK > LANTIK
2 x BIDEGI, S.A. > BIDEGI Agencia Guipuzcoana de Infraestructuras
2 x Bilbao Ekintza, E.P.E.L. > Bilbao Ekintza, E.P.E.L.
2 x Ayuntamiento de Abanto Zierbena > Ayuntamiento de Abanto Zierbena
2 x ITELAZPI, S.A. > ITELAZPI, S.A.
2 x Bilbao Kirolak-Instituto Municipal de Deportes S.A. > Bilbao Kirolak
2 x Sector Público > OTRAS ENTIDADES DEL SECTOR PÚBLICO > MUTUAS DE ACCIDENTES DE TRABAJO COLABORADORAS DE LA SEGURIDAD SOCIAL > ASEPEYO
2 x Izenpe S.A. > Izenpe - Empresa de Certificación y Servicios
```

## Cargos públicos (BOE, OCI, Congreso)

- días del BOE en caché: 4900
- personas: 2390 · actos del BOE: 4901
- actos del BOE leídos del 2013-05-18 al 2026-09-16
- personas con algo de cada fuente: {'boe': 1841, 'congreso': 430, 'oci': 166}
- autorizaciones (OCI): 643
- actividades declaradas (Congreso): 1196
- sociedades del mapa con un ex alto cargo autorizado: 13
- entidades del mapa con un diputado que declaró trabajar en ellas: 11
- órganos del mapa con quién los dirigió: 48
