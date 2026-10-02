# Estado de la última ingesta

Generado automáticamente por el workflow «Instantánea de datos».
Dice qué fuentes respondieron y qué aportaron al mapa publicado.

- Ejecución: `36996923104` · 2026-10-02T12:12:56Z

## Fuentes que no aportaron

```
### congreso (código 1)
{"fuente": "congreso", "params": "{'fecha_desde': datetime.date(2025, 1, 1), 'fecha_hasta': datetime.date(2025, 12, 31), 'max_paginas': None}", "event": "ingesta iniciada", "level": "info", "timestamp": "2026-10-02T10:44:22.087309Z"}
{"detalle": "The read operation timed out", "event": "congreso: la p\u00e1gina de datos abiertos no responde", "level": "warning", "timestamp": "2026-10-02T10:45:22.325502Z"}
{"fuente": "congreso", "documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-10-02T10:45:22.326399Z"}
{"documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-10-02T10:45:22.326560Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-10-02T10:45:22.326625Z"}

```

## Aporte al volcado

| fuente | entidades en el mapa |
| --- | ---: |
| Base de Datos Nacional de Subvenciones | 527 |
| Boletín Oficial del Estado | 2327 |
| Comisión Nacional del Mercado de Valores | 199 |
| Congreso de los Diputados | **0 — no aportó** |
| Oficina de Conflictos de Intereses | 341 |
| Plataforma de Contratación del Sector Público | 2848 |
| Senado | 28 |
| Tribunal de Cuentas | 630 |

## Territorio de los organismos

- del Estado: 222
- con comunidad: 1932
- **sin clasificar: 176**

Jerarquías más repetidas entre los sin clasificar (para afinar
`ingest/sinapsis_ingest/territorio.py`):

```
4 x Servicios de La Comarca de Pamplona S.A.
3 x DEPARTAMENTO DE COHESION TERRITORIAL
3 x Departamento de Universidad, Innovación y Transformación Digital
3 x IZFE - Sociedad Foral de Servicios Informáticos > IZFE - Sociedad Foral de Servicios Informáticos
3 x Departamento de Economía y Hacienda
2 x ETS - Euskal Trenbide Sarea > Euskal Trenbide Sarea
2 x LANTIK > LANTIK
2 x Bilbao Ekintza, E.P.E.L. > Bilbao Ekintza, E.P.E.L.
2 x OAL Viviendas Municipales de Bilbao > OAL Viviendas Municipales de Bilbao
2 x Bilbao Kirolak-Instituto Municipal de Deportes S.A. > Bilbao Kirolak
2 x Sociedad Fomento de San Sebastián > Sociedad Fomento de San Sebastián, S.A.
2 x MUBIL Fundazioa > MUBIL Fundazioa
2 x Dirección de ETB > Grupo Euskal Irrati Telebista
2 x Fundación Juan Crisóstomo de Arriaga-Orquesta Sinfónica de Bilbao > Fundación Juan Crisóstomo de Arriaga-Orquesta Sinfónica de Bilbao
2 x FUNDACION CENER
```

## Cargos públicos (BOE, OCI, Congreso)

- días del BOE en caché: 5420
- personas: 2493 · actos del BOE: 6044
- actos del BOE leídos del 2011-12-17 al 2026-09-30
- personas con algo de cada fuente: {'boe': 2327, 'oci': 166}
- autorizaciones (OCI): 643
- actividades declaradas (Congreso): 0
- sociedades del mapa con un ex alto cargo autorizado: 13
- entidades del mapa con un diputado que declaró trabajar en ellas: 0
- órganos del mapa con quién los dirigió: 19
