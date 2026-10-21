# Estado de la última ingesta

Generado automáticamente por el workflow «Instantánea de datos».
Dice qué fuentes respondieron y qué aportaron al mapa publicado.

- Ejecución: `39577956943` · 2026-10-21T11:18:56Z

## Fuentes que no aportaron

```
### cnmv (código 1)
{"url": "https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A20001020", "detalle": "Server disconnected without sending a response.", "event": "cnmv: p\u00e1gina no disponible", "level": "warning", "timestamp": "2026-10-21T10:11:04.804421Z"}
{"url": "https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A28092583", "detalle": "The read operation timed out", "event": "cnmv: p\u00e1gina no disponible", "level": "warning", "timestamp": "2026-10-21T10:12:05.331881Z"}
{"url": "https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A28212264", "detalle": "Server disconnected without sending a response.", "event": "cnmv: p\u00e1gina no disponible", "level": "warning", "timestamp": "2026-10-21T10:13:05.731411Z"}
{"fuente": "cnmv", "documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-10-21T10:13:05.732079Z"}
{"documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-10-21T10:13:05.732224Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-10-21T10:13:05.732264Z"}

### cnmv-consejos (código 1)
{"url": "https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A84236934", "detalle": "Server disconnected without sending a response.", "event": "cnmv: p\u00e1gina no disponible", "level": "warning", "timestamp": "2026-10-21T11:12:17.277223Z"}
{"nif": "A84236934", "event": "cnmv: la CNMV no reconoce el NIF", "level": "warning", "timestamp": "2026-10-21T11:12:17.277396Z"}
{"desde": "A08000143", "event": "cnmv: tope de tiempo; quedan cotizadas sin leer", "level": "warning", "timestamp": "2026-10-21T11:12:17.277423Z"}
{"fuente": "cnmv", "documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-10-21T11:12:17.277954Z"}
{"documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-10-21T11:12:17.278090Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-10-21T11:12:17.278125Z"}

```

## Aporte al volcado

| fuente | entidades en el mapa |
| --- | ---: |
| Base de Datos Nacional de Subvenciones | 693 |
| Boletín Oficial del Estado | 2336 |
| Comisión Nacional del Mercado de Valores | **0 — no aportó** |
| Congreso de los Diputados | 1477 |
| Oficina de Conflictos de Intereses | 341 |
| Plataforma de Contratación del Sector Público | 2685 |
| Senado | 28 |
| Tribunal de Cuentas | 630 |

## Territorio de los organismos

- del Estado: 299
- con comunidad: 2239
- **sin clasificar: 158**

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

- días del BOE en caché: 5439
- personas: 2885 · actos del BOE: 6062
- actos del BOE leídos del 2011-12-17 al 2026-10-21
- personas con algo de cada fuente: {'boe': 2336, 'congreso': 435, 'oci': 166}
- autorizaciones (OCI): 643
- actividades declaradas (Congreso): 1196
- sociedades del mapa con un ex alto cargo autorizado: 8
- entidades del mapa con un diputado que declaró trabajar en ellas: 10
- órganos del mapa con quién los dirigió: 29
