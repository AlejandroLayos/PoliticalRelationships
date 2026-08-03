# Reconocimiento del Tribunal de Cuentas

Generado automáticamente el 2026-08-03T19:43:27.329221+00:00 por `scripts/explorar_tcu.py`.

**No es documentación de una fuente ya integrada.** Es lo que se ve
desde fuera, anotado sin interpretar, para decidir si merece la pena
escribir un conector y de qué tipo.

## portal_partidos

- URL: `https://www.tcu.es/es/partidos-politicos/`
- **No accesible:** `[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1016)`

## sanciones

- URL: `https://www.tcu.es/es/fiscalizacion/sanciones-a-partidos/`
- **No accesible:** `[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1016)`

## sede_rendicion

- URL: `https://sede.tcu.es/es/sede-electronica/GRCuentas/PartidosPoliticos/`
- HTTP 200 · `text/html;charset=UTF-8` · 37,664 bytes
- Tablas HTML en la página: **0**
- Ficheros descargables enlazados: **4**

  Primeros enlaces:
  - `http://www.tcu.es/.galleries/pdf/PLAN_CONTABILIDAD_PARTIDOS_POLITICOS.pdf`
  - `https://sede.tcu.es/.content/pdf/ens/Certificado_ENS_Medio.pdf`
  - `https://sede.tcu.es/export/sites/default/.content/pdf/PPoliticos/COMUNICADO-DEL-DEPARTAMENTO-DE-PARTIDOS-POLITICOS-final.pdf`
  - `https://sede.tcu.es/export/sites/default/.content/pdf/PPoliticos/NUEVO_PCAFP_aprobado_Pleno_20-12-2018.pdf`

  Rutas que podrían servir datos:
  - `//fonts.googleapis.com/css?family=Noto+Serif:400,400italic`
  - `/es/sede-electronica/perfil-de-contratante/procedimientos-restringidos/`

## buscador

- URL: `https://www.tcu.es/searcher/document/DocumentSearch.action?docCheckFis=true&docCheckFisSelect=FIS:+PARTIDOS+POL%C3%8DTICOS&submitSearch=true`
- **No accesible:** `[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1016)`

---

## Qué mirar en este informe

1. **¿Hay CSV, XLSX o JSON?** Si los hay, el conector es sencillo y no
   hace falta tocar un PDF.
2. **¿Hay tablas HTML?** Segunda mejor opción: se parsean sin OCR.
3. **Si sólo hay PDF**, el conector necesita extracción de tablas
   (`pdfplumber`) y, si están escaneados, OCR. Eso es trabajo de otra
   magnitud y conviene decidirlo a la vista de un fichero real, no
   antes.

Sea cual sea el caso: los datos de financiación de partidos son la zona
más delicada del proyecto en RGPD. Los donantes personas físicas se
tratan como en BDNS — el hecho se conserva, la identidad no. Ver
[spec §12](../spec.md).
