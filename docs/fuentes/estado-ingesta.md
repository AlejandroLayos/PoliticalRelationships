# Estado de la última ingesta

Generado automáticamente por el workflow «Instantánea de datos».
Dice qué fuentes respondieron y qué aportaron al mapa publicado.

- Ejecución: `40674759279` · 2026-10-28T11:22:06Z

## Fuentes que no aportaron

```
### placsp-menores (código 1)
{"fuente": "placsp", "params": "{'fecha_desde': datetime.date(2025, 1, 1), 'fecha_hasta': datetime.date(2025, 12, 31), 'max_paginas': 30}", "event": "ingesta iniciada", "level": "info", "timestamp": "2026-10-28T11:06:01.018830Z"}
{"url": "https://contrataciondelestado.es/sindicacion/sindicacion_1143/contratosMenoresPerfilesContratantes.atom", "error": "The read operation timed out", "event": "placsp: fallo al descargar", "level": "warning", "timestamp": "2026-10-28T11:08:28.886416Z"}
{"fuente": "placsp", "documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta terminada", "level": "info", "timestamp": "2026-10-28T11:08:28.886663Z"}
{"documentos_nuevos": 0, "documentos_repetidos": 0, "entidades": 0, "aristas": 0, "registros_descartados": 0, "errores": 0, "event": "ingesta completada", "level": "info", "timestamp": "2026-10-28T11:08:28.886787Z"}
{"errores": 0, "event": "la ingesta no produjo nada", "level": "error", "timestamp": "2026-10-28T11:08:28.886826Z"}

```

## Aporte al volcado

| fuente | entidades en el mapa |
| --- | ---: |
| Base de Datos Nacional de Subvenciones | 2891 |
| Boletín Oficial del Estado | 2339 |
| Comisión Nacional del Mercado de Valores | 198 |
| Congreso de los Diputados | 1477 |
| Oficina de Conflictos de Intereses | 341 |
| Plataforma de Contratación del Sector Público | 486 |
| Senado | 28 |
| Tribunal de Cuentas | 630 |

## Territorio de los organismos

- del Estado: 26
- con comunidad: 330
- **sin clasificar: 20**

Jerarquías más repetidas entre los sin clasificar (para afinar
`ingest/sinapsis_ingest/territorio.py`):

```
1 x OTROS > CÁMARA DE COMERCIO DE VALENCIA
1 x AUKERAK > AUKERAK - Agencia Vasca de Reinserción Social
1 x Sector Público > OTRAS ENTIDADES DEL SECTOR PÚBLICO > MUTUAS DE ACCIDENTES DE TRABAJO COLABORADORAS DE LA SEGURIDAD SOCIAL > UMIVALE
1 x Sector Público > ENTIDADES LOCALES
1 x LOCAL > CONSEJO INSULAR DE MALLORCA > CONSELL INSULAR DE MALLORCA
1 x LOCAL > CABILDO INSULAR DE TENERIFE > CABILDO INSULAR DE TENERIFE
1 x LOCAL > CABILDO INSULAR DE LANZAROTE > CABILDO INSULAR DE LANZAROTE
1 x LOCAL > CABILDO INSULAR DE FUERTEVENTURA > CABILDO INSULAR DE FUERTEVENTURA
1 x Sociedad Fomento de San Sebastián > Sociedad Fomento de San Sebastián, S.A.
1 x BILBAOTIK, S.A. > BILBAOTIK, S.A.
1 x Ayuntamiento de la Anteiglesia de Abadiño > Ayuntamiento de la Anteiglesia de Abadiño
1 x Asociación Centro de Investigación Cooperativa en Biomateriales-CIC biomaGUNE > Asociación Centro de Investigación Cooperativa en Biomateriales-CIC biomaGUNE
1 x Sector Público > OTRAS ENTIDADES DEL SECTOR PÚBLICO > MUTUAS DE ACCIDENTES DE TRABAJO COLABORADORAS DE LA SEGURIDAD SOCIAL > ASEPEYO
1 x Sector Público > OTRAS ENTIDADES DEL SECTOR PÚBLICO > INSTITUCIONES INDEPENDIENTES > Banco de España
1 x LOCAL > ALCOY/ALCOI > AYUNTAMIENTO DE ALCOY/ALCOI
```

## Cargos públicos (BOE, OCI, Congreso)

- días del BOE en caché: 5446
- personas: 2888 · actos del BOE: 6074
- actos del BOE leídos del 2011-12-17 al 2026-10-28
- personas con algo de cada fuente: {'boe': 2339, 'congreso': 435, 'oci': 166}
- autorizaciones (OCI): 643
- actividades declaradas (Congreso): 1196
- sociedades del mapa con un ex alto cargo autorizado: 10
- entidades del mapa con un diputado que declaró trabajar en ellas: 1
- órganos del mapa con quién los dirigió: 7
