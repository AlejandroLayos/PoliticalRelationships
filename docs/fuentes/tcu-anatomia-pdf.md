# Anatomía de los PDF del Tribunal de Cuentas

Generado automáticamente el 2026-08-03T20:13:00.857509+00:00 por `scripts/anatomia_pdf_tcu.py`.

Responde a la pregunta que decide el coste del conector: si estos PDF
tienen capa de texto o son escaneos, y si `pdfplumber` reconoce sus
tablas. Medido sobre ficheros reales descargados del organismo.

**Aquí sólo hay estructura, nunca contenido.** Los expedientes
sancionadores nombran a personas; el texto extraído se sube como
artefacto del workflow y no entra en git. Ver [spec §12](../spec.md).

## `Procedimientos-sancionadores-contabilidad-electoral-2015.pdf`

- URL: `https://www.tcu.es/export/sites/portal/.galleries/Documentos-oficiales/Partidos-politicos/Procedimientos-sancionadores-contabilidad-electoral-2015.pdf`
- 1,033,150 bytes · **53 páginas**
- Páginas analizadas: 15
- ¿Capa de texto?: sí (1867 car./página de media)
- Tablas con bordes (estrategia por líneas): **207**
  - Formas (filas x columnas): 12x11, 2x1, 2x1, 2x1, 2x1, 2x1, 2x1, 2x1, 3x1, 2x1, 3x1, 2x1, 3x1, 3x1, 2x1, 13x11, 2x1, 2x1, 2x1, 2x1
- Tablas sin bordes (estrategia por texto): **15**
  - Formas (filas x columnas): 59x12, 58x13, 63x12, 55x12, 60x12, 64x11, 61x11, 60x10, 51x11, 62x13, 59x11, 58x11, 59x10, 57x11, 62x12

  **Tabla mayor** (13x11). Cabecera y patrón por
  columna. El patrón sustituye letras por `A` y cifras por `9`:
  dice el formato sin publicar el dato.

  | # | Cabecera | Patrón dominante |
  |---|----------|------------------|
  | 0 | ORIGEN | `AA.AA. 9999` |
  | 1 | FORMACIÓN POLÍTICA | `AAAAA AAAAAAAAAAA-
AAAAAAAAAA AAA AAAAA` |
  | 2 | NIF | `A99999999` |
  | 3 | FECHA RESOLUCIÓN | `99/99/9999` |
  | 4 | PRESUNTA INFRACCIÓN | `999.9 AAAAA` |
  | 5 | NO INICIAR P S / INFRACCIÓN SANCIONADA / | `AAAAAAAA 99. AAA. A) AAAAA AA
AAAAAAAA A` |
  | 6 |  | `99.999,99` |
  | 7 | CUANTÍA | `AAAAAAA` |
  | 8 |  | `` |
  | 9 | RECURSO CONTENCIOSO- ADMINISTRATIVO ANTE | `AA` |
  | 10 | RESOLUCIÓN DEL RECURSO | `AAAAAAAAAA` |

## `Procedimientos-sancionadores-contabilidad-electoral-2019.pdf`

- URL: `https://www.tcu.es/export/sites/portal/.galleries/Documentos-oficiales/Partidos-politicos/Procedimientos-sancionadores-contabilidad-electoral-2019.pdf`
- 305,637 bytes · **3 páginas**
- Páginas analizadas: 3
- ¿Capa de texto?: sí (2526 car./página de media)
- Tablas con bordes (estrategia por líneas): **36**
  - Formas (filas x columnas): 25x16, 3x1, 3x1, 2x1, 2x1, 2x1, 2x1, 2x1, 2x1, 2x1, 2x1, 22x20, 3x1, 3x1, 2x1, 2x1, 2x1, 2x1, 2x1, 2x1
- Tablas sin bordes (estrategia por texto): **3**
  - Formas (filas x columnas): 81x13, 81x13, 87x16

  **Tabla mayor** (22x20). Cabecera y patrón por
  columna. El patrón sustituye letras por `A` y cifras por `9`:
  dice el formato sin publicar el dato.

  | # | Cabecera | Patrón dominante |
  |---|----------|------------------|
  | 0 | ORIGEN | `AA.AA. 9999` |
  | 1 | FORMACIÓN POLÍTICA | `AAAAAAAA AAAAA-
AAAAAAAA
AAAAAAAAAAA:AAA` |
  | 2 |  | `AAAAAAAAA AAAAA- AAAA-` |
  | 3 |  | `` |
  | 4 | NIF | `A99999999` |
  | 5 | FECHA RESOLUCIÓN | `99/99/9999` |
  | 6 | LEY APLICABLE | `AAAAA` |
  | 7 | PRESUNTA INFRACCIÓN | `999.9 AAAAA` |
  | 8 | NO INICIAR PS / INFRACCIÓN SANCIONADA /  | `AAAAAAAA 99. AAA A) AAAAA AA
AAAAAAAA AA` |
  | 9 |  | `AAAAAAAA 99. AAA A) AAAAA AA` |
  | 10 |  | `` |
  | 11 | CUANTÍA SANCIÓN (€) | `99.999,99` |
  | 12 |  | `9.999,99` |
  | 13 |  | `` |
  | 14 |  | `AA` |
  | 15 | RECURSO | `AAAAAAAAAAA-` |
  | 16 |  | `` |
  | 17 | RESOLUCIÓN DEL RECURSO | `AAAAAAAA,
AAAAAAA
AAAAAAA*` |
  | 18 |  | `AAAAAAAA,` |
  | 19 |  | `` |

## `Procedimientos-sancionadores-contabilidad-electoral-2023.pdf`

- URL: `https://www.tcu.es/export/sites/portal/.galleries/Documentos-oficiales/Partidos-politicos/Procedimientos-sancionadores-contabilidad-electoral-2023.pdf`
- 411,676 bytes · **4 páginas**
- Páginas analizadas: 4
- ¿Capa de texto?: sí (1647 car./página de media)
- Tablas con bordes (estrategia por líneas): **33**
  - Formas (filas x columnas): 25x17, 3x1, 2x1, 2x1, 2x1, 2x1, 2x1, 2x1, 2x1, 25x15, 3x1, 2x1, 2x1, 2x1, 2x1, 3x1, 2x1, 25x19, 3x1, 2x1
- Tablas sin bordes (estrategia por texto): **4**
  - Formas (filas x columnas): 58x11, 54x13, 52x15, 37x13

  **Tabla mayor** (25x19). Cabecera y patrón por
  columna. El patrón sustituye letras por `A` y cifras por `9`:
  dice el formato sin publicar el dato.

  | # | Cabecera | Patrón dominante |
  |---|----------|------------------|
  | 0 | ORIGEN | `AA.AA. 9999` |
  | 1 | FORMACIÓN POLÍTICA | `AAAAAAAAAA
AAAAAAAAA` |
  | 2 |  | `AAAAAAAAAA` |
  | 3 |  | `` |
  | 4 | NIF | `A99999999` |
  | 5 | FECHA RESOLUCIÓN | `99/99/9999` |
  | 6 | PRESUNTA INFRACCIÓN | `999.9 AAAAA` |
  | 7 |  | `99.9 AAAAA` |
  | 8 |  | `` |
  | 9 | NO INICIAR PS / INFRACCIÓN SANCIONADA /  | `AAAAAAAA 99. AAA A) AAAAA AA
AAAAAAAA AA` |
  | 10 |  | `AAAAAAAA 99. AAA A) AAAAA AA` |
  | 11 |  | `` |
  | 12 | CUANTÍA SANCIÓN (€) | `9.999,99*` |
  | 13 |  | `99.999,99*` |
  | 14 |  | `` |
  | 15 |  | `` |
  | 16 | RECURSO | `AAAAAAAAAAA-` |
  | 17 |  | `` |
  | 18 | RESOLUCIÓN DEL RECURSO | `` |

## `Procedimientos-sancionadores-contabilidad-ordinaria.pdf`

- URL: `https://www.tcu.es/export/sites/portal/.galleries/Documentos-oficiales/Partidos-politicos/Procedimientos-sancionadores-contabilidad-ordinaria.pdf`
- 536,139 bytes · **9 páginas**
- Páginas analizadas: 9
- ¿Capa de texto?: sí (1663 car./página de media)
- Tablas con bordes (estrategia por líneas): **92**
  - Formas (filas x columnas): 24x17, 3x1, 2x1, 2x1, 2x1, 2x1, 2x1, 2x1, 3x1, 3x1, 3x1, 3x1, 4x1, 3x1, 26x17, 3x1, 2x1, 2x1, 2x1, 2x1
- Tablas sin bordes (estrategia por texto): **9**
  - Formas (filas x columnas): 76x12, 63x14, 67x8, 58x8, 60x8, 62x8, 60x8, 66x10, 72x12

  **Tabla mayor** (25x19). Cabecera y patrón por
  columna. El patrón sustituye letras por `A` y cifras por `9`:
  dice el formato sin publicar el dato.

  | # | Cabecera | Patrón dominante |
  |---|----------|------------------|
  | 0 | ORIGEN | `AAAAAAAAAAAA
AAAAA 9999` |
  | 1 |  | `AAAAAAAAAAAA` |
  | 2 |  | `` |
  | 3 | FORMACIÓN POLÍTICA | `AAA` |
  | 4 | NIF | `A99999999` |
  | 5 | FECHA RESOLUCIÓN | `99/99/9999` |
  | 6 | PRESUNTA INFRACCIÓN | `AAAAAA AA AAAAA AA
AAAAAAAAAAAA AAA
AAAA` |
  | 7 |  | `AAAAAAAAAA` |
  | 8 |  | `` |
  | 9 | NO INICIAR PS / INFRACCIÓN SANCIONADA /  | `AAAAAAAA 99. AAA A) AAAAA AA
AAAAAAAA AA` |
  | 10 |  | `AAAAAAAA 99. AAA A) AAAAA AA` |
  | 11 |  | `` |
  | 12 | CUANTÍA SANCIÓN (€) | `9.999,99` |
  | 13 |  | `AA
99/99/9999` |
  | 14 | RECURSO | `AAAAAAAAAAA-` |
  | 15 |  | `` |
  | 16 | RESOLUCIÓN DEL RECURSO | `AAAAAAAAAAA
99/99/9999` |
  | 17 |  | `AAAAAAAA,` |
  | 18 |  | `` |

---

## Veredicto

- Con capa de texto: **4 de 4**
- Con tablas con bordes: **4 de 4**
- Con tablas sin bordes: **4 de 4**

Lectura, de más barato a más caro:

1. **Capa de texto + tablas con bordes** → conector medio:
   `pdfplumber` con la estrategia por líneas, golden test con una
   muestra real guardada, y a funcionar.
2. **Capa de texto + tablas sólo por alineación** → el cuadro no
   lleva bordes; se reconstruye por posiciones. Funciona, pero es
   frágil: cualquier rediseño del PDF lo rompe. Exige golden tests y
   tolerar el hueco cuando cambien el formato.
3. **Capa de texto sin ninguna tabla** → es prosa, no un cuadro. Hay
   que extraer con expresiones regulares sobre el texto corrido, que
   es lo más frágil de todo.
4. **Sin capa de texto** → OCR. Sobre cifras de financiación un error
   de OCR es un dato falso con aspecto de dato bueno. Antes de ir por
   ahí conviene agotar la vía de pedir los datos al organismo.

La distinción 1 vs 2 importa y por eso se miden las dos estrategias:
la de por defecto se apoya en las líneas dibujadas y devuelve cero
tablas en un cuadro sin bordes aunque el cuadro esté ahí. Quedarse
sólo con ella haría parecer caro algo que no lo es.

Nada de esto se decide por lo que «suele pasar» con los PDF de la
administración: se decide por los números de arriba.
