# Estado de la última ingesta

Generado automáticamente por el workflow «Instantánea de datos».
Dice qué fuentes respondieron y qué aportaron al mapa publicado.

- Ejecución: `36222035755` · 2026-09-26T07:05:07Z

## Fuentes que no aportaron

```
### oci (código 1)
{"fuente": "oci", "params": "{'fecha_desde': datetime.date(2025, 1, 1), 'fecha_hasta': datetime.date(2025, 12, 31), 'max_paginas': None}", "event": "ingesta iniciada", "level": "info", "timestamp": "2026-09-26T05:53:39.483678Z"}
{"detalle": "The read operation timed out", "event": "oci: el buscador no responde", "level": "warning", "timestamp": "2026-09-26T05:54:39.633601Z"}
{"fuente": "oci", "documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-09-26T05:54:39.634487Z"}
{"documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-09-26T05:54:39.634671Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-09-26T05:54:39.634741Z"}

```

## Aporte al volcado

| fuente | entidades en el mapa |
| --- | ---: |
| Base de Datos Nacional de Subvenciones | 549 |
| Boletín Oficial del Estado | 1666 |
| Congreso de los Diputados | 1477 |
| Oficina de Conflictos de Intereses | **0 — no aportó** |
| Plataforma de Contratación del Sector Público | 2830 |
| Senado | 28 |
| Tribunal de Cuentas | 630 |

## Territorio de los organismos

- del Estado: 495
- con comunidad: 3856
- **sin clasificar: 204**

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

- días del BOE en caché: 3600
- personas: 2051 · actos del BOE: 4152
- actos del BOE leídos del 2016-11-19 al 2026-09-16
- personas con algo de cada fuente: {'boe': 1666, 'congreso': 424}
- autorizaciones (OCI): 0
- actividades declaradas (Congreso): 1196
- sociedades del mapa con un ex alto cargo autorizado: 0
- entidades del mapa con un diputado que declaró trabajar en ellas: 11
- órganos del mapa con quién los dirigió: 44
