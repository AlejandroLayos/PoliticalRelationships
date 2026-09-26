# Reconocimiento: CNMV (consejos y participaciones de cotizadas)

Generado el 2026-09-26T10:42:43.796753+00:00 por `scripts/explorar_cnmv.py` (segunda vuelta).

## Listados de entidades (`ListadoEntidad.aspx?id=N&tipoent=0`)

- id=0 → HTTP 404 · «CNMV - Error» · 0 NIF enlazados
- id=1 → HTTP 200 · «CNMV - Listado de Sociedades y Agencias de Valores» · 89 NIF enlazados (primeros: ['A01718576', 'A01872696', 'A02740306', 'A02969178', 'A05326467'])
- id=2 → HTTP 200 · «CNMV - Listado completo de Sociedades Gestoras de IIC» · 122 NIF enlazados (primeros: ['A06923288', 'A08188534', 'A08347684', 'A08818965', 'A13823745'])
- id=3 → HTTP 404 · «CNMV - Error» · 0 NIF enlazados
- id=4 → HTTP 200 · «CNMV - Listado completo de sociedades gestoras de entidades de inversión de tipo cerrado» · 165 NIF enlazados (primeros: ['A01621937', 'A01636133', 'A01663129', 'A01707322', 'A01876572'])
- id=5 → HTTP 404 · «CNMV - Error» · 0 NIF enlazados
- id=6 → HTTP 404 · «CNMV - Error» · 0 NIF enlazados
- id=7 → HTTP 404 · «CNMV - Error» · 0 NIF enlazados
- id=8 → HTTP 404 · «CNMV - Error» · 0 NIF enlazados
- id=9 → HTTP 404 · «CNMV - Error» · 0 NIF enlazados
- id=10 → HTTP 404 · «CNMV - Error» · 0 NIF enlazados
- id=11 → HTTP 404 · «CNMV - Error» · 0 NIF enlazados
- id=12 → HTTP 404 · «CNMV - Error» · 0 NIF enlazados
- id=13 → HTTP 404 · «CNMV - Error» · 0 NIF enlazados
- id=14 → HTTP 404 · «CNMV - Error» · 0 NIF enlazados
- id=15 → HTTP 404 · «CNMV - Error» · 0 NIF enlazados

## telefonica (A28015865)

### datosentidad

`https://www.cnmv.es/portal/Consultas/DatosEntidad.aspx?nif=A28015865` → HTTP 200 · `text/html; charset=utf-8` · 218,423 caracteres · «CNMV - Información de la Entidad - TELEFONICA, S.A.»

- rótulos: ['Información de la Entidad']
- guardado como `telefonica-datosentidad.html`

### datosgenerales

`https://www.cnmv.es/portal/Consultas/ee/datosgenerales.aspx?nif=A28015865` → HTTP 200 · `text/html; charset=utf-8` · 212,396 caracteres · «CNMV - Datos generales - TELEFONICA, S.A.»

- rótulos: ['Datos generales']
  - tabla 1 #ctl00_ContentPrincipal_gridDatos: 2 filas; primeras: [['NIF', 'LEI', 'Denominación abreviada', 'Sector', 'Capital social vigente'], ['A28015865', '549300EEJH4FEPDBBR25', 'TELEFONICA', 'TRANSPORTES Y COMUNICACIONES/COMUNICACIONES', '5.670.161.554,00 €']]
- guardado como `telefonica-datosgenerales.html`

### participaciones

`https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A28015865` → HTTP 200 · `text/html; charset=utf-8` · 212,914 caracteres · «CNMV - Participaciones Significativas y Autocartera de la entidad - TELEFONICA, S.A.»

- rótulos: ['Participaciones Significativas y Autocartera de la entidad']
- guardado como `telefonica-participaciones.html`

### gobcorp

`https://www.cnmv.es/portal/Consultas/ee/informaciongobcorp.aspx?nif=A28015865` → HTTP 200 · `text/html; charset=utf-8` · 165,316 caracteres · «CNMV - Información sobre gobierno corporativo - TELEFONICA, S.A. - Informe Anual sobre Rem»

- rótulos: ['Información sobre gobierno corporativo', 'Informe Anual de Gobierno Corporativo']
  - tabla 1 #ctl00_ContentPrincipal_wGridIAGC_gridDatos: 16 filas; primeras: [['Nombre del emisor', 'Nº registro oficial', 'Fecha registro oficial', 'Ejercicio', 'Fecha modificación', 'Apartados modificados', 'Ampliación (1)', 'Documento'], ['TELEFONICA, S.A.', '2026028797', '24/02/2026', '2025', '', '', '', ''], ['TELEFONICA, S.A.', '2025030786', '27/02/2025', '2024', '', '', '', ''], ['TELEFONICA, S.A.', '2024027945', '23/02/2024', '2023', '', '', '', '']]
- guardado como `telefonica-gobcorp.html`
    - documento 'Código de conducta' → `https://www.cnmv.es/DocPortal/quees/Conducta.pdf`
    - documento 'CNMV 2030' → `https://www.cnmv.es/DocPortal/OtrosDocumentos/CNMV2030.pdf`
    - documento 'Política de comunicación pública' → `https://www.cnmv.es/DocPortal/AlDia/PoliticaComunicacionCNMV.pdf`
    - documento 'Plan de sostenibilidad ambiental' → `https://www.cnmv.es/DocPortal/OtrosDocumentos/Plan-Sostenibilidad-CNMV.pdf`
    - documento 'Política de comunicación pública' → `https://www.cnmv.es/DocPortal/AlDia/PoliticaComunicacionCNMV.pdf`
    - documento 'Documentos a consulta' → `https://www.cnmv.es/portal/Publicaciones/DocumentosConsulta.aspx`
    - documento 'De la Comisión Nacional del Mercado de V' → `https://www.cnmv.es/portal/publicaciones/documentos-fase-consulta.aspx?tDoc=1`
    - documento 'De la Comisión Europea' → `https://www.cnmv.es/portal/publicaciones/listadodocumentos.aspx?tDoc=4`
- el primero → HTTP 200 · `application/pdf` · 20,260,205 bytes

### directivos

`https://www.cnmv.es/portal/Consultas/directivos-resultado.aspx?nif=A28015865` → HTTP 200 · `text/html; charset=utf-8` · 248,876 caracteres · «CNMV - Notificaciones de los directivos y personas vinculadas (Reglamento de Ejecución (UE»

- rótulos: ['Notificaciones de los directivos y personas vinculadas (Reglamento de Ejecución (UE) 2016/']
- no se guarda: trae personas vinculadas

## iberdrola (A48010615)

### datosentidad

`https://www.cnmv.es/portal/Consultas/DatosEntidad.aspx?nif=A48010615` → HTTP 200 · `text/html; charset=utf-8` · 209,774 caracteres · «CNMV - Información de la Entidad»

- rótulos: ['Información de la Entidad']
- guardado como `iberdrola-datosentidad.html`

### datosgenerales

`https://www.cnmv.es/portal/Consultas/ee/datosgenerales.aspx?nif=A48010615` → HTTP 200 · `text/html; charset=utf-8` · 211,037 caracteres · «CNMV - Datos generales»

- rótulos: ['Datos generales']
- guardado como `iberdrola-datosgenerales.html`

### participaciones

`https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A48010615` → HTTP 200 · `text/html; charset=utf-8` · 211,531 caracteres · «CNMV - Participaciones Significativas y Autocartera de la entidad - IBERDROLA, S.A.»

- rótulos: ['Participaciones Significativas y Autocartera de la entidad']
- guardado como `iberdrola-participaciones.html`

### gobcorp

`https://www.cnmv.es/portal/Consultas/ee/informaciongobcorp.aspx?nif=A48010615` → HTTP 200 · `text/html; charset=utf-8` · 150,054 caracteres · «CNMV - Información sobre gobierno corporativo - Informe Anual sobre Remuneraciones de los »

- rótulos: ['Información sobre gobierno corporativo']
- guardado como `iberdrola-gobcorp.html`
    - documento 'Código de conducta' → `https://www.cnmv.es/DocPortal/quees/Conducta.pdf`
    - documento 'CNMV 2030' → `https://www.cnmv.es/DocPortal/OtrosDocumentos/CNMV2030.pdf`
    - documento 'Política de comunicación pública' → `https://www.cnmv.es/DocPortal/AlDia/PoliticaComunicacionCNMV.pdf`
    - documento 'Plan de sostenibilidad ambiental' → `https://www.cnmv.es/DocPortal/OtrosDocumentos/Plan-Sostenibilidad-CNMV.pdf`
    - documento 'Política de comunicación pública' → `https://www.cnmv.es/DocPortal/AlDia/PoliticaComunicacionCNMV.pdf`
    - documento 'Documentos a consulta' → `https://www.cnmv.es/portal/Publicaciones/DocumentosConsulta.aspx`
    - documento 'De la Comisión Nacional del Mercado de V' → `https://www.cnmv.es/portal/publicaciones/documentos-fase-consulta.aspx?tDoc=1`
    - documento 'De la Comisión Europea' → `https://www.cnmv.es/portal/publicaciones/listadodocumentos.aspx?tDoc=4`
- el primero → HTTP 200 · `application/pdf` · 20,260,205 bytes

### directivos

`https://www.cnmv.es/portal/Consultas/directivos-resultado.aspx?nif=A48010615` → HTTP 200 · `text/html; charset=utf-8` · 211,523 caracteres · «CNMV - Notificaciones de los directivos y personas vinculadas (Reglamento de Ejecución (UE»

- rótulos: ['Notificaciones de los directivos y personas vinculadas (Reglamento de Ejecución (UE) 2016/']
- no se guarda: trae personas vinculadas

## acs (A28004885)

### datosentidad

`https://www.cnmv.es/portal/Consultas/DatosEntidad.aspx?nif=A28004885` → HTTP 200 · `text/html; charset=utf-8` · 209,774 caracteres · «CNMV - Información de la Entidad»

- rótulos: ['Información de la Entidad']
- guardado como `acs-datosentidad.html`

### datosgenerales

`https://www.cnmv.es/portal/Consultas/ee/datosgenerales.aspx?nif=A28004885` → HTTP 200 · `text/html; charset=utf-8` · 211,037 caracteres · «CNMV - Datos generales»

- rótulos: ['Datos generales']
- guardado como `acs-datosgenerales.html`

### participaciones

`https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A28004885` → HTTP 200 · `text/html; charset=utf-8` · 211,776 caracteres · «CNMV - Participaciones Significativas y Autocartera de la entidad - ACS, ACTIVIDADES DE CO»

- rótulos: ['Participaciones Significativas y Autocartera de la entidad']
- guardado como `acs-participaciones.html`

### gobcorp

`https://www.cnmv.es/portal/Consultas/ee/informaciongobcorp.aspx?nif=A28004885` → HTTP 200 · `text/html; charset=utf-8` · 150,054 caracteres · «CNMV - Información sobre gobierno corporativo - Informe Anual sobre Remuneraciones de los »

- rótulos: ['Información sobre gobierno corporativo']
- guardado como `acs-gobcorp.html`
    - documento 'Código de conducta' → `https://www.cnmv.es/DocPortal/quees/Conducta.pdf`
    - documento 'CNMV 2030' → `https://www.cnmv.es/DocPortal/OtrosDocumentos/CNMV2030.pdf`
    - documento 'Política de comunicación pública' → `https://www.cnmv.es/DocPortal/AlDia/PoliticaComunicacionCNMV.pdf`
    - documento 'Plan de sostenibilidad ambiental' → `https://www.cnmv.es/DocPortal/OtrosDocumentos/Plan-Sostenibilidad-CNMV.pdf`
    - documento 'Política de comunicación pública' → `https://www.cnmv.es/DocPortal/AlDia/PoliticaComunicacionCNMV.pdf`
    - documento 'Documentos a consulta' → `https://www.cnmv.es/portal/Publicaciones/DocumentosConsulta.aspx`
    - documento 'De la Comisión Nacional del Mercado de V' → `https://www.cnmv.es/portal/publicaciones/documentos-fase-consulta.aspx?tDoc=1`
    - documento 'De la Comisión Europea' → `https://www.cnmv.es/portal/publicaciones/listadodocumentos.aspx?tDoc=4`
- el primero → HTTP 200 · `application/pdf` · 20,260,205 bytes

### directivos

`https://www.cnmv.es/portal/Consultas/directivos-resultado.aspx?nif=A28004885` → HTTP 200 · `text/html; charset=utf-8` · 211,523 caracteres · «CNMV - Notificaciones de los directivos y personas vinculadas (Reglamento de Ejecución (UE»

- rótulos: ['Notificaciones de los directivos y personas vinculadas (Reglamento de Ejecución (UE) 2016/']
- no se guarda: trae personas vinculadas

## atresmedia (A78839271)

### datosentidad

`https://www.cnmv.es/portal/Consultas/DatosEntidad.aspx?nif=A78839271` → HTTP 200 · `text/html; charset=utf-8` · 209,774 caracteres · «CNMV - Información de la Entidad»

- rótulos: ['Información de la Entidad']
- guardado como `atresmedia-datosentidad.html`

### datosgenerales

`https://www.cnmv.es/portal/Consultas/ee/datosgenerales.aspx?nif=A78839271` → HTTP 200 · `text/html; charset=utf-8` · 211,037 caracteres · «CNMV - Datos generales»

- rótulos: ['Datos generales']
- guardado como `atresmedia-datosgenerales.html`

### participaciones

`https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A78839271` → HTTP 200 · `text/html; charset=utf-8` · 211,804 caracteres · «CNMV - Participaciones Significativas y Autocartera de la entidad - ATRESMEDIA CORPORACION»

- rótulos: ['Participaciones Significativas y Autocartera de la entidad']
- guardado como `atresmedia-participaciones.html`

### gobcorp

`https://www.cnmv.es/portal/Consultas/ee/informaciongobcorp.aspx?nif=A78839271` → HTTP 200 · `text/html; charset=utf-8` · 150,054 caracteres · «CNMV - Información sobre gobierno corporativo - Informe Anual sobre Remuneraciones de los »

- rótulos: ['Información sobre gobierno corporativo']
- guardado como `atresmedia-gobcorp.html`
    - documento 'Código de conducta' → `https://www.cnmv.es/DocPortal/quees/Conducta.pdf`
    - documento 'CNMV 2030' → `https://www.cnmv.es/DocPortal/OtrosDocumentos/CNMV2030.pdf`
    - documento 'Política de comunicación pública' → `https://www.cnmv.es/DocPortal/AlDia/PoliticaComunicacionCNMV.pdf`
    - documento 'Plan de sostenibilidad ambiental' → `https://www.cnmv.es/DocPortal/OtrosDocumentos/Plan-Sostenibilidad-CNMV.pdf`
    - documento 'Política de comunicación pública' → `https://www.cnmv.es/DocPortal/AlDia/PoliticaComunicacionCNMV.pdf`
    - documento 'Documentos a consulta' → `https://www.cnmv.es/portal/Publicaciones/DocumentosConsulta.aspx`
    - documento 'De la Comisión Nacional del Mercado de V' → `https://www.cnmv.es/portal/publicaciones/documentos-fase-consulta.aspx?tDoc=1`
    - documento 'De la Comisión Europea' → `https://www.cnmv.es/portal/publicaciones/listadodocumentos.aspx?tDoc=4`
- el primero → HTTP 200 · `application/pdf` · 20,260,205 bytes

### directivos

`https://www.cnmv.es/portal/Consultas/directivos-resultado.aspx?nif=A78839271` → HTTP 200 · `text/html; charset=utf-8` · 211,523 caracteres · «CNMV - Notificaciones de los directivos y personas vinculadas (Reglamento de Ejecución (UE»

- rótulos: ['Notificaciones de los directivos y personas vinculadas (Reglamento de Ejecución (UE) 2016/']
- no se guarda: trae personas vinculadas

## prisa (A28297059)

### datosentidad

`https://www.cnmv.es/portal/Consultas/DatosEntidad.aspx?nif=A28297059` → HTTP 200 · `text/html; charset=utf-8` · 218,996 caracteres · «CNMV - Información de la Entidad - PROMOTORA DE INFORMACIONES, S.A.»

- rótulos: ['Información de la Entidad']
- guardado como `prisa-datosentidad.html`

### datosgenerales

`https://www.cnmv.es/portal/Consultas/ee/datosgenerales.aspx?nif=A28297059` → HTTP 200 · `text/html; charset=utf-8` · 212,469 caracteres · «CNMV - Datos generales - PROMOTORA DE INFORMACIONES, S.A.»

- rótulos: ['Datos generales']
  - tabla 1 #ctl00_ContentPrincipal_gridDatos: 2 filas; primeras: [['NIF', 'LEI', 'Denominación abreviada', 'Sector', 'Capital social vigente'], ['A28297059', '959800U3NGPXSCQHQW54', 'PRISA', 'MEDIOS DE COMUNICACIÓN', '134.914.212,00 €']]
- guardado como `prisa-datosgenerales.html`

### participaciones

`https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A28297059` → HTTP 200 · `text/html; charset=utf-8` · 213,026 caracteres · «CNMV - Participaciones Significativas y Autocartera de la entidad - PROMOTORA DE INFORMACI»

- rótulos: ['Participaciones Significativas y Autocartera de la entidad']
- guardado como `prisa-participaciones.html`

### gobcorp

`https://www.cnmv.es/portal/Consultas/ee/informaciongobcorp.aspx?nif=A28297059` → HTTP 200 · `text/html; charset=utf-8` · 166,109 caracteres · «CNMV - Información sobre gobierno corporativo - PROMOTORA DE INFORMACIONES, S.A. - Informe»

- rótulos: ['Información sobre gobierno corporativo', 'Informe Anual de Gobierno Corporativo']
  - tabla 1 #ctl00_ContentPrincipal_wGridIAGC_gridDatos: 16 filas; primeras: [['Nombre del emisor', 'Nº registro oficial', 'Fecha registro oficial', 'Ejercicio', 'Fecha modificación', 'Apartados modificados', 'Ampliación (1)', 'Documento'], ['PROMOTORA DE INFORMACIONES, S.A.', '2026042679', '24/03/2026', '2025', '', '', '', ''], ['PROMOTORA DE INFORMACIONES, S.A.', '2025039653', '19/03/2025', '2024', '', '', '', ''], ['PROMOTORA DE INFORMACIONES, S.A.', '2024037652', '12/03/2024', '2023', '', '', '', '']]
- guardado como `prisa-gobcorp.html`
    - documento 'Código de conducta' → `https://www.cnmv.es/DocPortal/quees/Conducta.pdf`
    - documento 'CNMV 2030' → `https://www.cnmv.es/DocPortal/OtrosDocumentos/CNMV2030.pdf`
    - documento 'Política de comunicación pública' → `https://www.cnmv.es/DocPortal/AlDia/PoliticaComunicacionCNMV.pdf`
    - documento 'Plan de sostenibilidad ambiental' → `https://www.cnmv.es/DocPortal/OtrosDocumentos/Plan-Sostenibilidad-CNMV.pdf`
    - documento 'Política de comunicación pública' → `https://www.cnmv.es/DocPortal/AlDia/PoliticaComunicacionCNMV.pdf`
    - documento 'Documentos a consulta' → `https://www.cnmv.es/portal/Publicaciones/DocumentosConsulta.aspx`
    - documento 'De la Comisión Nacional del Mercado de V' → `https://www.cnmv.es/portal/publicaciones/documentos-fase-consulta.aspx?tDoc=1`
    - documento 'De la Comisión Europea' → `https://www.cnmv.es/portal/publicaciones/listadodocumentos.aspx?tDoc=4`
- el primero → HTTP 200 · `application/pdf` · 20,260,205 bytes

### directivos

`https://www.cnmv.es/portal/Consultas/directivos-resultado.aspx?nif=A28297059` → HTTP 200 · `text/html; charset=utf-8` · 249,400 caracteres · «CNMV - Notificaciones de los directivos y personas vinculadas (Reglamento de Ejecución (UE»

- rótulos: ['Notificaciones de los directivos y personas vinculadas (Reglamento de Ejecución (UE) 2016/']
- no se guarda: trae personas vinculadas

## indra (A28599033)

### datosentidad

`https://www.cnmv.es/portal/Consultas/DatosEntidad.aspx?nif=A28599033` → HTTP 200 · `text/html; charset=utf-8` · 209,774 caracteres · «CNMV - Información de la Entidad»

- rótulos: ['Información de la Entidad']
- guardado como `indra-datosentidad.html`

### datosgenerales

`https://www.cnmv.es/portal/Consultas/ee/datosgenerales.aspx?nif=A28599033` → HTTP 200 · `text/html; charset=utf-8` · 211,037 caracteres · «CNMV - Datos generales»

- rótulos: ['Datos generales']
- guardado como `indra-datosgenerales.html`

### participaciones

`https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A28599033` → HTTP 200 · `text/html; charset=utf-8` · 211,566 caracteres · «CNMV - Participaciones Significativas y Autocartera de la entidad - INDRA SISTEMAS, S.A.»

- rótulos: ['Participaciones Significativas y Autocartera de la entidad']
- guardado como `indra-participaciones.html`

### gobcorp

`https://www.cnmv.es/portal/Consultas/ee/informaciongobcorp.aspx?nif=A28599033` → HTTP 200 · `text/html; charset=utf-8` · 150,054 caracteres · «CNMV - Información sobre gobierno corporativo - Informe Anual sobre Remuneraciones de los »

- rótulos: ['Información sobre gobierno corporativo']
- guardado como `indra-gobcorp.html`
    - documento 'Código de conducta' → `https://www.cnmv.es/DocPortal/quees/Conducta.pdf`
    - documento 'CNMV 2030' → `https://www.cnmv.es/DocPortal/OtrosDocumentos/CNMV2030.pdf`
    - documento 'Política de comunicación pública' → `https://www.cnmv.es/DocPortal/AlDia/PoliticaComunicacionCNMV.pdf`
    - documento 'Plan de sostenibilidad ambiental' → `https://www.cnmv.es/DocPortal/OtrosDocumentos/Plan-Sostenibilidad-CNMV.pdf`
    - documento 'Política de comunicación pública' → `https://www.cnmv.es/DocPortal/AlDia/PoliticaComunicacionCNMV.pdf`
    - documento 'Documentos a consulta' → `https://www.cnmv.es/portal/Publicaciones/DocumentosConsulta.aspx`
    - documento 'De la Comisión Nacional del Mercado de V' → `https://www.cnmv.es/portal/publicaciones/documentos-fase-consulta.aspx?tDoc=1`
    - documento 'De la Comisión Europea' → `https://www.cnmv.es/portal/publicaciones/listadodocumentos.aspx?tDoc=4`
- el primero → HTTP 200 · `application/pdf` · 20,260,205 bytes

### directivos

`https://www.cnmv.es/portal/Consultas/directivos-resultado.aspx?nif=A28599033` → HTTP 200 · `text/html; charset=utf-8` · 211,523 caracteres · «CNMV - Notificaciones de los directivos y personas vinculadas (Reglamento de Ejecución (UE»

- rótulos: ['Notificaciones de los directivos y personas vinculadas (Reglamento de Ejecución (UE) 2016/']
- no se guarda: trae personas vinculadas

## santander (A39000013)

### datosentidad

`https://www.cnmv.es/portal/Consultas/DatosEntidad.aspx?nif=A39000013` → HTTP 200 · `text/html; charset=utf-8` · 220,620 caracteres · «CNMV - Información de la Entidad - BANCO SANTANDER, S.A.»

- rótulos: ['Información de la Entidad']
- guardado como `santander-datosentidad.html`

### datosgenerales

`https://www.cnmv.es/portal/Consultas/ee/datosgenerales.aspx?nif=A39000013` → HTTP 200 · `text/html; charset=utf-8` · 212,436 caracteres · «CNMV - Datos generales - BANCO SANTANDER, S.A.»

- rótulos: ['Datos generales']
  - tabla 1 #ctl00_ContentPrincipal_gridDatos: 2 filas; primeras: [['NIF', 'LEI', 'Denominación abreviada', 'Sector', 'Capital social vigente'], ['A39000013', '5493006QMFDDMYWIAM13', 'BANCO SANTANDER', 'FINANCIACIÓN Y SEGUROS/BANCOS', '7.278.241.400,50 €']]
- guardado como `santander-datosgenerales.html`

### participaciones

`https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A39000013` → HTTP 200 · `text/html; charset=utf-8` · 212,949 caracteres · «CNMV - Participaciones Significativas y Autocartera de la entidad - BANCO SANTANDER, S.A.»

- rótulos: ['Participaciones Significativas y Autocartera de la entidad']
- guardado como `santander-participaciones.html`

### gobcorp

`https://www.cnmv.es/portal/Consultas/ee/informaciongobcorp.aspx?nif=A39000013` → HTTP 200 · `text/html; charset=utf-8` · 165,709 caracteres · «CNMV - Información sobre gobierno corporativo - BANCO SANTANDER, S.A. - Informe Anual sobr»

- rótulos: ['Información sobre gobierno corporativo', 'Informe Anual de Gobierno Corporativo']
  - tabla 1 #ctl00_ContentPrincipal_wGridIAGC_gridDatos: 16 filas; primeras: [['Nombre del emisor', 'Nº registro oficial', 'Fecha registro oficial', 'Ejercicio', 'Fecha modificación', 'Apartados modificados', 'Ampliación (1)', 'Documento'], ['BANCO SANTANDER, S.A.', '2026029544', '25/02/2026', '2025', '', '', '', ''], ['BANCO SANTANDER, S.A.', '2025031198', '28/02/2025', '2024', '', '', '', ''], ['BANCO SANTANDER, S.A.', '2024024847', '19/02/2024', '2023', '', '', '', '']]
- guardado como `santander-gobcorp.html`
    - documento 'Código de conducta' → `https://www.cnmv.es/DocPortal/quees/Conducta.pdf`
    - documento 'CNMV 2030' → `https://www.cnmv.es/DocPortal/OtrosDocumentos/CNMV2030.pdf`
    - documento 'Política de comunicación pública' → `https://www.cnmv.es/DocPortal/AlDia/PoliticaComunicacionCNMV.pdf`
    - documento 'Plan de sostenibilidad ambiental' → `https://www.cnmv.es/DocPortal/OtrosDocumentos/Plan-Sostenibilidad-CNMV.pdf`
    - documento 'Política de comunicación pública' → `https://www.cnmv.es/DocPortal/AlDia/PoliticaComunicacionCNMV.pdf`
    - documento 'Documentos a consulta' → `https://www.cnmv.es/portal/Publicaciones/DocumentosConsulta.aspx`
    - documento 'De la Comisión Nacional del Mercado de V' → `https://www.cnmv.es/portal/publicaciones/documentos-fase-consulta.aspx?tDoc=1`
    - documento 'De la Comisión Europea' → `https://www.cnmv.es/portal/publicaciones/listadodocumentos.aspx?tDoc=4`
- el primero → HTTP 200 · `application/pdf` · 20,260,205 bytes

### directivos

`https://www.cnmv.es/portal/Consultas/directivos-resultado.aspx?nif=A39000013` → HTTP 200 · `text/html; charset=utf-8` · 249,894 caracteres · «CNMV - Notificaciones de los directivos y personas vinculadas (Reglamento de Ejecución (UE»

- rótulos: ['Notificaciones de los directivos y personas vinculadas (Reglamento de Ejecución (UE) 2016/']
- no se guarda: trae personas vinculadas

## redeia (A78003662)

### datosentidad

`https://www.cnmv.es/portal/Consultas/DatosEntidad.aspx?nif=A78003662` → HTTP 200 · `text/html; charset=utf-8` · 209,774 caracteres · «CNMV - Información de la Entidad»

- rótulos: ['Información de la Entidad']
- guardado como `redeia-datosentidad.html`

### datosgenerales

`https://www.cnmv.es/portal/Consultas/ee/datosgenerales.aspx?nif=A78003662` → HTTP 200 · `text/html; charset=utf-8` · 211,037 caracteres · «CNMV - Datos generales»

- rótulos: ['Datos generales']
- guardado como `redeia-datosgenerales.html`

### participaciones

`https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A78003662` → HTTP 200 · `text/html; charset=utf-8` · 211,594 caracteres · «CNMV - Participaciones Significativas y Autocartera de la entidad - REDEIA CORPORACION, S.»

- rótulos: ['Participaciones Significativas y Autocartera de la entidad']
- guardado como `redeia-participaciones.html`

### gobcorp

`https://www.cnmv.es/portal/Consultas/ee/informaciongobcorp.aspx?nif=A78003662` → HTTP 200 · `text/html; charset=utf-8` · 150,054 caracteres · «CNMV - Información sobre gobierno corporativo - Informe Anual sobre Remuneraciones de los »

- rótulos: ['Información sobre gobierno corporativo']
- guardado como `redeia-gobcorp.html`
    - documento 'Código de conducta' → `https://www.cnmv.es/DocPortal/quees/Conducta.pdf`
    - documento 'CNMV 2030' → `https://www.cnmv.es/DocPortal/OtrosDocumentos/CNMV2030.pdf`
    - documento 'Política de comunicación pública' → `https://www.cnmv.es/DocPortal/AlDia/PoliticaComunicacionCNMV.pdf`
    - documento 'Plan de sostenibilidad ambiental' → `https://www.cnmv.es/DocPortal/OtrosDocumentos/Plan-Sostenibilidad-CNMV.pdf`
    - documento 'Política de comunicación pública' → `https://www.cnmv.es/DocPortal/AlDia/PoliticaComunicacionCNMV.pdf`
    - documento 'Documentos a consulta' → `https://www.cnmv.es/portal/Publicaciones/DocumentosConsulta.aspx`
    - documento 'De la Comisión Nacional del Mercado de V' → `https://www.cnmv.es/portal/publicaciones/documentos-fase-consulta.aspx?tDoc=1`
    - documento 'De la Comisión Europea' → `https://www.cnmv.es/portal/publicaciones/listadodocumentos.aspx?tDoc=4`
- el primero → HTTP 200 · `application/pdf` · 20,260,205 bytes

### directivos

`https://www.cnmv.es/portal/Consultas/directivos-resultado.aspx?nif=A78003662` → HTTP 200 · `text/html; charset=utf-8` · 211,523 caracteres · «CNMV - Notificaciones de los directivos y personas vinculadas (Reglamento de Ejecución (UE»

- rótulos: ['Notificaciones de los directivos y personas vinculadas (Reglamento de Ejecución (UE) 2016/']
- no se guarda: trae personas vinculadas

