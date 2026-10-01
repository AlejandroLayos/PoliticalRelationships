# Estado de la última ingesta

Generado automáticamente por el workflow «Instantánea de datos».
Dice qué fuentes respondieron y qué aportaron al mapa publicado.

- Ejecución: `36853485775` · 2026-10-01T12:51:17Z

## Fuentes que no aportaron

```
### cnmv (código 1)
{"url": "https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A20001020", "detalle": "The read operation timed out", "event": "cnmv: p\u00e1gina no disponible", "level": "warning", "timestamp": "2026-10-01T11:45:25.724759Z"}
{"url": "https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A28092583", "detalle": "The read operation timed out", "event": "cnmv: p\u00e1gina no disponible", "level": "warning", "timestamp": "2026-10-01T11:46:26.296460Z"}
{"url": "https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A28212264", "detalle": "Server disconnected without sending a response.", "event": "cnmv: p\u00e1gina no disponible", "level": "warning", "timestamp": "2026-10-01T11:47:26.078385Z"}
{"fuente": "cnmv", "documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-10-01T11:47:26.079173Z"}
{"documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-10-01T11:47:26.079306Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-10-01T11:47:26.079368Z"}

### cnmv-consejos (código 1)
{"url": "https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A84236934", "detalle": "Server disconnected without sending a response.", "event": "cnmv: p\u00e1gina no disponible", "level": "warning", "timestamp": "2026-10-01T12:47:06.142500Z"}
{"nif": "A84236934", "event": "cnmv: la CNMV no reconoce el NIF", "level": "warning", "timestamp": "2026-10-01T12:47:06.142679Z"}
{"desde": "A08000143", "event": "cnmv: tope de tiempo; quedan cotizadas sin leer", "level": "warning", "timestamp": "2026-10-01T12:47:06.142722Z"}
{"fuente": "cnmv", "documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-10-01T12:47:06.142780Z"}
{"documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-10-01T12:47:06.142919Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-10-01T12:47:06.142964Z"}

```

## Aporte al volcado

| fuente | entidades en el mapa |
| --- | ---: |
| Base de Datos Nacional de Subvenciones | 530 |
| Boletín Oficial del Estado | 2327 |
| Comisión Nacional del Mercado de Valores | **0 — no aportó** |
| Congreso de los Diputados | 1477 |
| Oficina de Conflictos de Intereses | 341 |
| Plataforma de Contratación del Sector Público | 2845 |
| Senado | 28 |
| Tribunal de Cuentas | 630 |

## Territorio de los organismos

- del Estado: 9
- con comunidad: 1292
- **sin clasificar: 150**

Jerarquías más repetidas entre los sin clasificar (para afinar
`ingest/sinapsis_ingest/territorio.py`):

```
5 x Servicios de La Comarca de Pamplona S.A.
3 x DEPARTAMENTO DE COHESION TERRITORIAL
3 x Departamento de Universidad, Innovación y Transformación Digital
3 x IZFE - Sociedad Foral de Servicios Informáticos > IZFE - Sociedad Foral de Servicios Informáticos
3 x Departamento de Economía y Hacienda
2 x ETS - Euskal Trenbide Sarea > Euskal Trenbide Sarea
2 x LANTIK > LANTIK
2 x Bilbao Ekintza, E.P.E.L. > Bilbao Ekintza, E.P.E.L.
2 x Bilbao Kirolak-Instituto Municipal de Deportes S.A. > Bilbao Kirolak
2 x OAL Viviendas Municipales de Bilbao > OAL Viviendas Municipales de Bilbao
2 x Sociedad Fomento de San Sebastián > Sociedad Fomento de San Sebastián, S.A.
2 x MUBIL Fundazioa > MUBIL Fundazioa
2 x Dirección de ETB > Grupo Euskal Irrati Telebista
2 x FUNDACION CENER
2 x Departamento de Educación
```

## Cargos públicos (BOE, OCI, Congreso)

- días del BOE en caché: 5419
- personas: 2876 · actos del BOE: 6044
- actos del BOE leídos del 2011-12-17 al 2026-09-30
- personas con algo de cada fuente: {'boe': 2327, 'congreso': 435, 'oci': 166}
- autorizaciones (OCI): 643
- actividades declaradas (Congreso): 1196
- sociedades del mapa con un ex alto cargo autorizado: 6
- entidades del mapa con un diputado que declaró trabajar en ellas: 3
- órganos del mapa con quién los dirigió: 5
