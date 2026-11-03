# Estado de la última ingesta

Generado automáticamente por el workflow «Instantánea de datos».
Dice qué fuentes respondieron y qué aportaron al mapa publicado.

- Ejecución: `41634381212` · 2026-11-03T14:02:13Z

## Fuentes que no aportaron

```
### cnmv (código 1)
{"url": "https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A20001020", "detalle": "The read operation timed out", "event": "cnmv: p\u00e1gina no disponible", "level": "warning", "timestamp": "2026-11-03T12:53:32.149202Z"}
{"url": "https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A28092583", "detalle": "Server disconnected without sending a response.", "event": "cnmv: p\u00e1gina no disponible", "level": "warning", "timestamp": "2026-11-03T12:54:32.113685Z"}
{"url": "https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A28212264", "detalle": "The read operation timed out", "event": "cnmv: p\u00e1gina no disponible", "level": "warning", "timestamp": "2026-11-03T12:55:32.470321Z"}
{"fuente": "cnmv", "documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-11-03T12:55:32.471104Z"}
{"documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-11-03T12:55:32.471255Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-11-03T12:55:32.471292Z"}

### cnmv-consejos (código 1)
{"url": "https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A84236934", "detalle": "Server disconnected without sending a response.", "event": "cnmv: p\u00e1gina no disponible", "level": "warning", "timestamp": "2026-11-03T13:54:49.095936Z"}
{"nif": "A84236934", "event": "cnmv: la CNMV no reconoce el NIF", "level": "warning", "timestamp": "2026-11-03T13:54:49.096112Z"}
{"desde": "A08000143", "event": "cnmv: tope de tiempo; quedan cotizadas sin leer", "level": "warning", "timestamp": "2026-11-03T13:54:49.096141Z"}
{"fuente": "cnmv", "documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-11-03T13:54:49.096737Z"}
{"documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-11-03T13:54:49.096859Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-11-03T13:54:49.096898Z"}

```

## Aporte al volcado

| fuente | entidades en el mapa |
| --- | ---: |
| Base de Datos Nacional de Subvenciones | 734 |
| Boletín Oficial del Estado | 2339 |
| Comisión Nacional del Mercado de Valores | **0 — no aportó** |
| Congreso de los Diputados | 1477 |
| Oficina de Conflictos de Intereses | 341 |
| Plataforma de Contratación del Sector Público | 2645 |
| Senado | 28 |
| Tribunal de Cuentas | 630 |

## Territorio de los organismos

- del Estado: 336
- con comunidad: 2436
- **sin clasificar: 143**

Jerarquías más repetidas entre los sin clasificar (para afinar
`ingest/sinapsis_ingest/territorio.py`):

```
3 x IZFE - Sociedad Foral de Servicios Informáticos > IZFE - Sociedad Foral de Servicios Informáticos
3 x Sector Público > OTRAS ENTIDADES DEL SECTOR PÚBLICO > MUTUAS DE ACCIDENTES DE TRABAJO COLABORADORAS DE LA SEGURIDAD SOCIAL > ASEPEYO
3 x Departamento de Universidad, Innovación y Transformación Digital
3 x Departamento de Interior, Función Pública y Justicia
2 x ETS - Euskal Trenbide Sarea > Euskal Trenbide Sarea
2 x ZUGAZTEL, M. P., S. A. > ZUGAZTEL, M. P., S. A.
2 x LANTIK > LANTIK
2 x BIDEGI, S.A. > BIDEGI Agencia Guipuzcoana de Infraestructuras
2 x Sociedad Fomento de San Sebastián > Sociedad Fomento de San Sebastián, S.A.
2 x Bilbao Kirolak-Instituto Municipal de Deportes S.A. > Bilbao Kirolak
2 x Desarrollo Rural y Medio Ambiente
2 x Bilbao Ekintza, E.P.E.L. > Bilbao Ekintza, E.P.E.L.
2 x Departamento de Economía y Hacienda
2 x NEIKER, Instituto Vasco de Investigación y Desarrollo Agrario, S.A. > NEIKER, Instituto Vasco de Investigación y Desarrollo Agrario, S.A.
2 x Instituto Foral de Bienestar Social > Instituto Foral de Bienestar Social
```

## Cargos públicos (BOE, OCI, Congreso)

- días del BOE en caché: 5452
- personas: 2888 · actos del BOE: 6074
- actos del BOE leídos del 2011-12-17 al 2026-10-28
- personas con algo de cada fuente: {'boe': 2339, 'congreso': 435, 'oci': 166}
- autorizaciones (OCI): 643
- actividades declaradas (Congreso): 1196
- sociedades del mapa con un ex alto cargo autorizado: 7
- entidades del mapa con un diputado que declaró trabajar en ellas: 4
- órganos del mapa con quién los dirigió: 35
