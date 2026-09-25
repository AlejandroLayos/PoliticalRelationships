# Reconocimiento del BOE y del BORME

Generado automáticamente el 2026-09-25T20:51:40.237337+00:00 por `scripts/explorar_boe.py`.

**No es documentación de una fuente integrada**: es lo que se ve desde fuera,
anotado sin interpretar, para escribir los conectores de las puertas giratorias
(spec §15, fase 7) sobre la forma real de los datos.

## BOE — sumario diario

Altos cargos por Real Decreto en los últimos días recorridos: **19**

- 20260916 · Real Decreto 734/2026, de 15 de septiembre, por el que se nombra Directora del Departamento de Comunicación Institucional de la Secretaría de Estado de Comunicación a doña María Teresa Velilla de la Rocha.
- 20260902 · Real Decreto 712/2026, de 1 de septiembre, por el que se dispone el cese de doña Rocío Báguena Rodríguez como Secretaria General de Transporte Terrestre.
- 20260902 · Real Decreto 713/2026, de 1 de septiembre, por el que se dispone el cese de doña Sara Hernández del Olmo como Secretaria General de Movilidad Sostenible.
- 20260902 · Real Decreto 714/2026, de 1 de septiembre, por el que se nombra Secretaria General de Transporte Terrestre a doña Sara Hernández del Olmo.
- 20260902 · Real Decreto 715/2026, de 1 de septiembre, por el que se dispone el cese de doña Leire Iglesias Santiago como Presidenta de CASA 47 Entidad Pública Empresarial.
- 20260902 · Real Decreto 716/2026, de 1 de septiembre, por el que se nombra Secretaria de Estado de Vivienda y Agenda Urbana a doña Leire Iglesias Santiago.
- 20260902 · Real Decreto 717/2026, de 1 de septiembre, por el que se nombra Presidenta de CASA 47 Entidad Pública Empresarial a doña María Isabel Ramos Vergeles.
- 20260827 · Real Decreto 687/2026, de 25 de agosto, por el que se dispone el cese de don José Manuel Nevado Martínez como Director del Departamento de Comunicación Institucional de la Secretaría de Estado de Comunicación.
- 20260827 · Real Decreto 693/2026, de 26 de agosto, por el que se nombra Inspectora Fiscal de la Inspección Fiscal de la Fiscalía General del Estado a doña María del Milagro Martínez-Pardo Cabrillo.
- 20260827 · Real Decreto 694/2026, de 26 de agosto, por el que se nombra Fiscal de la Fiscalía ante el Tribunal Constitucional a doña Ana Belén Alonso González.
- 20260827 · Real Decreto 695/2026, de 26 de agosto, por el que se nombra Fiscal de la Fiscalía Especial Antidroga a doña María José Martínez Rodríguez.
- 20260827 · Real Decreto 696/2026, de 26 de agosto, por el que se nombra Fiscal Jefe de la Fiscalía Provincial de Madrid a don José Luis García-Juanes Guerrero.
- 20260827 · Real Decreto 697/2026, de 26 de agosto, por el que se nombra Fiscal Jefa de la Fiscalía Provincial de Tarragona a doña María de la Cinta López Cardús.
- 20260827 · Real Decreto 698/2026, de 26 de agosto, por el que se nombra Fiscal Jefe de la Fiscalía Provincial de Málaga a don Fernando Germán Benítez Pérez-Fajardo.
- 20260827 · Real Decreto 699/2026, de 26 de agosto, por el que se nombra Fiscal Jefa de la Fiscalía Provincial de Lugo a doña María Olga Serrano Pedrós.
- 20260826 · Real Decreto 688/2026, de 25 de agosto, por el que se dispone el cese de don Antonio González-Zavala Peña como Enviado Especial para Siria.
- 20260826 · Real Decreto 689/2026, de 25 de agosto, por el que se dispone el cese de don Daniel Losada Millar como Enviado Especial para Sudán.
- 20260826 · Real Decreto 703/2026, de 25 de agosto, por el que se dispone el cese de doña Inés Carpio San Román como Directora General de Financiación Internacional.
- 20260826 · Real Decreto 704/2026, de 25 de agosto, por el que se nombra Director General de Financiación Internacional a don Luis Óscar Moreno García-Cano.

Muestra guardada en `ingest/tests/golden/boe_altos_cargos_muestra.json` (19 ítems).

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

PDF de muestra: `https://www.boe.es/borme/dias/2026/09/25/pdfs/BORME-A-2026-186-03.pdf` → HTTP 200 · `application/pdf` · 261964 bytes

Páginas: 333 renglones · asientos numerados: **73**

Actos que aparecen:

- Nombramientos: 46
- Ceses/Dimisiones: 24
- Constitución: 21
- Declaración de unipersonalidad: 10
- Reelecciones: 10
- Disolución: 7
- Extinción: 7
- Cambio de domicilio social: 4
- Reducción de capital: 3
- Revocaciones: 1
- Cambio de denominación social: 1

Etiquetas de cargo que aparecen:

- `Adm. Unico:` 34
- `Liquidador:` 14
- `Adm. Solid.:` 13
- `Auditor:` 12
- `Socio único:` 11
- `Adm. Mancom.:` 4
- `Apoderado:` 1

Muestra de texto guardada en `ingest/tests/golden/borme_seccion1_muestra.txt`, con 143 nombres de persona sustituidos.

