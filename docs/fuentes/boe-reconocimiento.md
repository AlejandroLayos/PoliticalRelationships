# Reconocimiento del BOE y del BORME

Generado automáticamente el 2026-09-25T20:40:06.695863+00:00 por `scripts/explorar_boe.py`.

**No es documentación de una fuente integrada**: es lo que se ve desde fuera,
anotado sin interpretar, para escribir los conectores de las puertas giratorias
(spec §15, fase 7) sobre la forma real de los datos.

## BOE — sumario diario

- `https://www.boe.es/datosabiertos/api/boe/sumario/20260925` → HTTP 200 · `application/json`

Forma de la respuesta (claves reales, sin contenido):

```json
{
  "status": {
    "code": "str[3]",
    "text": "str[2]"
  },
  "data": {
    "sumario": {
      "metadatos": {
        "publicacion": "str[3]",
        "fecha_publicacion": "str[8]"
      },
      "diario": [
        {
          "numero": "str[3]",
          "sumario_diario": {
            "identificador": "str[14]",
            "url_pdf": {
              "szBytes": "str[6]",
              "szKBytes": "str[3]",
              "texto": "str[62]"
            }
          },
          "seccion": [
            {
              "codigo": "str[1]",
              "nombre": "str[26]",
              "departamento": [
                "…"
              ]
            }
          ]
        }
      ]
    }
  }
}
```

Secciones del día:

- `1` I. Disposiciones generales — 5 disposiciones
- `2A` II. Autoridades y personal. - A. Nombramientos, situaciones e incidencias — 15 disposiciones
- `2B` II. Autoridades y personal. - B. Oposiciones y concursos — 39 disposiciones
- `3` III. Otras disposiciones — 38 disposiciones
- `5A` V. Anuncios. - A. Contratación del Sector Público — 45 disposiciones
- `5B` V. Anuncios. - B. Otros anuncios oficiales — 45 disposiciones

Epígrafes de la II.A:

- 'Nombramientos': 9
- 'Destinos': 3
- 'Adscripciones': 2
- 'Situaciones': 1

Disposiciones por Real Decreto de nombramiento o cese (altos cargos): **0**

Claves de un `item`:

```json
{
  "identificador": "str[16]",
  "control": "str[10]",
  "titulo": "str[200]",
  "url_pdf": {
    "szBytes": "str[6]",
    "szKBytes": "str[3]",
    "pagina_inicial": "str[6]",
    "pagina_final": "str[6]",
    "texto": "str[64]"
  },
  "url_html": "str[57]",
  "url_xml": "str[57]",
  "_departamento": "str[34]",
  "_epigrafe": "str[13]"
}
```

Títulos de altos cargos (son publicables: §12):


## BORME — sumario diario y sección primera

- `https://www.boe.es/datosabiertos/api/borme/sumario/20260925` → HTTP 200 · `application/json`

Forma de la respuesta (claves reales, sin contenido):

```json
{
  "status": {
    "code": "str[3]",
    "text": "str[2]"
  },
  "data": {
    "sumario": {
      "metadatos": {
        "publicacion": "str[5]",
        "fecha_publicacion": "str[8]"
      },
      "diario": [
        {
          "numero": "str[3]",
          "sumario_diario": {
            "identificador": "str[16]",
            "url_pdf": {
              "szBytes": "str[6]",
              "szKBytes": "str[3]",
              "texto": "str[66]"
            }
          },
          "seccion": [
            {
              "codigo": "str[1]",
              "nombre": "str[45]",
              "item": [
                "…"
              ]
            }
          ]
        }
      ]
    }
  }
}
```

- sección `A` SECCIÓN PRIMERA. Empresarios. Actos inscritos
- sección `B` SECCIÓN PRIMERA. Empresarios. Otros actos publicados en el Registro Mercantil
- sección `C` SECCIÓN SEGUNDA. Anuncios y avisos legales

Ítems de la sección primera: **23**

Claves de un `item`:

```json
{
  "identificador": "str[19]",
  "titulo": "str[8]",
  "url_pdf": {
    "szBytes": "str[6]",
    "szKBytes": "str[3]",
    "pagina_inicial": "str[5]",
    "pagina_final": "str[5]",
    "texto": "str[69]"
  },
  "url_html": "str[62]",
  "url_xml": "str[62]"
}
```

- ALBACETE
- ALICANTE/ALACANT
- ALMERÍA
- BADAJOZ
- ILLES BALEARS
- BARCELONA
- CÁCERES
- CIUDAD REAL
- A CORUÑA
- GIRONA
- GRANADA
- LEÓN

PDF de muestra: `https://www.boe.es/borme/dias/2026/09/25/pdfs/BORME-A-2026-186-24.pdf` → HTTP 200 · `application/pdf` · 154851 bytes

Páginas: 16 renglones · asientos numerados: **1**

Actos que aparecen:

- Constitución: 1
- Nombramientos: 1

Etiquetas de cargo que aparecen:

- `Adm. Unico:` 1

Muestra de texto guardada en `ingest/tests/golden/borme_seccion1_muestra.txt`, con 7 nombres de persona sustituidos.

