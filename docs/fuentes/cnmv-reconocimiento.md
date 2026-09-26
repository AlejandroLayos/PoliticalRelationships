# Reconocimiento: CNMV (consejos y participaciones de cotizadas)

Décima vuelta: 2026-09-26T15:25:45.701910+00:00 (`scripts/explorar_cnmv.py`).
Las anteriores siguen debajo.

## Décima vuelta: los consejeros dominicales y a quién representan

- portada → HTTP 200 (text/html; charset=utf-8); cookies: 1
- participaciones de Telefónica → HTTP 200 (text/html; charset=utf-8)

### Consejeros dominicales: a quién representan

- telefonica: IAGC 2025; páginas [15, 16, 89, 90, 129, 130]; 13 tablas
  - página 15, 11 columnas, 2 filas; primera: ['', '']
  - página 15, 1 columnas, 2 filas; primera: ['Observaciones']
  - página 16, 11 columnas, 2 filas; primera: ['', '']
  - página 89, 11 columnas, 1 filas; primera: ['', '']
  - página 89, 1 columnas, 4 filas; primera: ['Banco Bilbao Vizcaya Argentaria, S.A.']
  - página 90, 11 columnas, 1 filas; primera: ['', '']
- prisa: IAGC 2025; páginas [19, 20, 21, 22, 105, 106, 107, 108]; 10 tablas
  - página 19, 3 columnas, 3 filas; primera: ['CONSEJEROS EXTERNOS DOMINICALES', '']
  - página 20, 3 columnas, 5 filas; primera: ['CONSEJEROS EXTERNOS DOMINICALES', '']
  - página 21, 3 columnas, 3 filas; primera: ['CONSEJEROS EXTERNOS DOMINICALES', '']
  - página 21, 2 columnas, 2 filas; primera: ['Número total de consejeros dominicales', '5']
  - página 22, 2 columnas, 4 filas; primera: ['CONSEJEROS EXTERNOS INDEPENDIENTES', '']
  - página 105, 3 columnas, 3 filas; primera: ['CONSEJEROS EXTERNOS DOMINICALES', '']
- naturgy: IAGC 2025; páginas [16, 17, 93, 94, 95]; 13 tablas
  - página 16, 1 columnas, 12 filas; primera: ['Nombre o denominación del accionista significativo a quien representa o que ha propuesto su nombramiento']
  - página 17, 1 columnas, 7 filas; primera: ['Número de consejeras']
  - página 93, 6 columnas, 2 filas; primera: ['Nombre o denominación social del consejero', 'Categoría del consejero en el momento del cese']
  - página 93, 3 columnas, 3 filas; primera: ['CONSEJEROS EJECUTIVOS', '']
  - página 93, 2 columnas, 2 filas; primera: ['Número total de consejeros ejecutivos', '1']
  - página 93, 3 columnas, 4 filas; primera: ['CONSEJEROS EXTERNOS DOMINICALES', '']
- caixabank: IAGC 2025; páginas [142, 143, 144, 145]; 8 tablas
  - página 142, 3 columnas, 3 filas; primera: ['CONSEJEROS EJECUTIVOS', '']
  - página 142, 2 columnas, 2 filas; primera: ['Número total de consejeros ejecutivos', '1']
  - página 142, 3 columnas, 2 filas; primera: ['CONSEJEROS EXTERNOS DOMINICALES', '']
  - página 143, 3 columnas, 4 filas; primera: ['CONSEJEROS EXTERNOS DOMINICALES', '']
  - página 144, 3 columnas, 3 filas; primera: ['CONSEJEROS EXTERNOS DOMINICALES', '']
  - página 144, 2 columnas, 2 filas; primera: ['Número total de consejeros dominicales', '3']


---


Novena vuelta: 2026-09-26T14:05:15.752613+00:00 (`scripts/explorar_cnmv.py`).
Las anteriores siguen debajo.

## Novena vuelta: las cotizadas «sin datos»

- portada → HTTP 200 (text/html; charset=utf-8); cookies: 1
- participaciones de Telefónica → HTTP 200 (text/html; charset=utf-8)

### Las cotizadas «sin datos»: otra puerta

#### iberdrola (A48010615)

- `ee/datosgenerales.aspx?nif=A48010615` → HTTP 200: sin datos
- `ee/informaciongobcorp.aspx?nif=A48010615` → HTTP 200: sin datos
- `ee/datosgenerales.aspx?nif=A-48010615` → HTTP 200: con la ficha (sector)
- `ee/informaciongobcorp.aspx?nif=A-48010615` → HTTP 200: con la tabla del IAGC
- `ee/datosgenerales.aspx?nif=a48010615` → HTTP 200: sin datos
- `ee/informaciongobcorp.aspx?nif=a48010615` → HTTP 200: sin datos
- `ee/datosgenerales.aspx?nif=48010615` → HTTP 200: sin datos
- `ee/informaciongobcorp.aspx?nif=48010615` → HTTP 200: sin datos
- buscador «IBERDROLA» → HTTP 200; enlaces: ['../../ANCV/ConsultaISIN.aspx', '../../Advertencias.aspx', '../../AlDia/Comunicaciones-Publicas.aspx', '../../AlDia/Contacto.aspx', '../../AlDia/Discursos-Articulos.aspx', '../../AlDia/Eventos.aspx', '../../AlDia/Galeria-Multimedia.aspx', '../../AlDia/Newsletter-CNMV.aspx', '../../AlDia/Otras-Organizaciones.aspx', '../../AlDia/Premio-Periodismo.aspx', '../../Aldia/ActInternacional/ActInterCNMV.aspx', '../../Aldia/ActInternacional/ActInternacionales.aspx', '../../Aldia/ActInternacional/ComentariosOI.aspx', '../../Aldia/ActInternacional/Glosario.aspx', '../../Aldia/ActInternacional/MapaOrg.aspx', '../../Aldia/ActInternacional/NotasPrensa.aspx', '../../Aldia/ActInternacional/OrgInter.aspx', '../../Aldia/ActInternacional/Revitalizacion-Capitales.aspx', '../../Aldia/TransparenciaSupervisora.aspx', '../../Aldia/VideosCorporativos.aspx', '../../Benchmark/Indices-Referencia.aspx', '../../CSD/Depositario-Central-Valores.aspx', '../../Ciberseguridad.aspx', '../../Finanzas-Sostenibles/Indice.aspx', '../../Fintech/Innovacion.aspx']
- `ee/datosgenerales.aspx?qS={94d3176e-5928-410b-b81b-af3db8c37f26}` → HTTP 200: sin datos
- `ee/informaciongobcorp.aspx?qS={94d3176e-5928-410b-b81b-af3db8c37f26}` → HTTP 200: con la tabla del IAGC
- `DatosEntidad.aspx?qS={94d3176e-5928-410b-b81b-af3db8c37f26}` → HTTP 200: sin datos

#### atresmedia (A78839271)

- `ee/datosgenerales.aspx?nif=A78839271` → HTTP 200: sin datos
- `ee/informaciongobcorp.aspx?nif=A78839271` → HTTP 200: sin datos
- `ee/datosgenerales.aspx?nif=A-78839271` → HTTP 200: con la ficha (sector)
- `ee/informaciongobcorp.aspx?nif=A-78839271` → HTTP 200: con la tabla del IAGC
- `ee/datosgenerales.aspx?nif=a78839271` → HTTP 200: sin datos
- `ee/informaciongobcorp.aspx?nif=a78839271` → HTTP 200: sin datos
- `ee/datosgenerales.aspx?nif=78839271` → HTTP 200: sin datos
- `ee/informaciongobcorp.aspx?nif=78839271` → HTTP 200: sin datos
- buscador «ATRESMEDIA» → HTTP 200; enlaces: ['../../ANCV/ConsultaISIN.aspx', '../../Advertencias.aspx', '../../AlDia/Comunicaciones-Publicas.aspx', '../../AlDia/Contacto.aspx', '../../AlDia/Discursos-Articulos.aspx', '../../AlDia/Eventos.aspx', '../../AlDia/Galeria-Multimedia.aspx', '../../AlDia/Newsletter-CNMV.aspx', '../../AlDia/Otras-Organizaciones.aspx', '../../AlDia/Premio-Periodismo.aspx', '../../Aldia/ActInternacional/ActInterCNMV.aspx', '../../Aldia/ActInternacional/ActInternacionales.aspx', '../../Aldia/ActInternacional/ComentariosOI.aspx', '../../Aldia/ActInternacional/Glosario.aspx', '../../Aldia/ActInternacional/MapaOrg.aspx', '../../Aldia/ActInternacional/NotasPrensa.aspx', '../../Aldia/ActInternacional/OrgInter.aspx', '../../Aldia/ActInternacional/Revitalizacion-Capitales.aspx', '../../Aldia/TransparenciaSupervisora.aspx', '../../Aldia/VideosCorporativos.aspx', '../../Benchmark/Indices-Referencia.aspx', '../../CSD/Depositario-Central-Valores.aspx', '../../Ciberseguridad.aspx', '../../Finanzas-Sostenibles/Indice.aspx', '../../Fintech/Innovacion.aspx']
- `ee/datosgenerales.aspx?qS={766768ae-8126-433f-b16c-d8e79c188970}` → HTTP 200: sin datos
- `ee/informaciongobcorp.aspx?qS={766768ae-8126-433f-b16c-d8e79c188970}` → HTTP 200: con la tabla del IAGC
- `DatosEntidad.aspx?qS={766768ae-8126-433f-b16c-d8e79c188970}` → HTTP 200: sin datos

#### vocento (A48001655)

- `ee/datosgenerales.aspx?nif=A48001655` → HTTP 200: sin datos
- `ee/informaciongobcorp.aspx?nif=A48001655` → HTTP 200: sin datos
- `ee/datosgenerales.aspx?nif=A-48001655` → HTTP 200: con la ficha (sector)
- `ee/informaciongobcorp.aspx?nif=A-48001655` → HTTP 200: con la tabla del IAGC
- `ee/datosgenerales.aspx?nif=a48001655` → HTTP 200: sin datos
- `ee/informaciongobcorp.aspx?nif=a48001655` → HTTP 200: sin datos
- `ee/datosgenerales.aspx?nif=48001655` → HTTP 200: sin datos
- `ee/informaciongobcorp.aspx?nif=48001655` → HTTP 200: sin datos
- buscador «VOCENTO» → HTTP 200; enlaces: ['../../ANCV/ConsultaISIN.aspx', '../../Advertencias.aspx', '../../AlDia/Comunicaciones-Publicas.aspx', '../../AlDia/Contacto.aspx', '../../AlDia/Discursos-Articulos.aspx', '../../AlDia/Eventos.aspx', '../../AlDia/Galeria-Multimedia.aspx', '../../AlDia/Newsletter-CNMV.aspx', '../../AlDia/Otras-Organizaciones.aspx', '../../AlDia/Premio-Periodismo.aspx', '../../Aldia/ActInternacional/ActInterCNMV.aspx', '../../Aldia/ActInternacional/ActInternacionales.aspx', '../../Aldia/ActInternacional/ComentariosOI.aspx', '../../Aldia/ActInternacional/Glosario.aspx', '../../Aldia/ActInternacional/MapaOrg.aspx', '../../Aldia/ActInternacional/NotasPrensa.aspx', '../../Aldia/ActInternacional/OrgInter.aspx', '../../Aldia/ActInternacional/Revitalizacion-Capitales.aspx', '../../Aldia/TransparenciaSupervisora.aspx', '../../Aldia/VideosCorporativos.aspx', '../../Benchmark/Indices-Referencia.aspx', '../../CSD/Depositario-Central-Valores.aspx', '../../Ciberseguridad.aspx', '../../Finanzas-Sostenibles/Indice.aspx', '../../Fintech/Innovacion.aspx']
- `ee/datosgenerales.aspx?qS={ce8acff8-8be3-4e2f-91ba-2d6cac7a0fab}` → HTTP 200: sin datos
- `ee/informaciongobcorp.aspx?qS={ce8acff8-8be3-4e2f-91ba-2d6cac7a0fab}` → HTTP 200: con la tabla del IAGC
- `DatosEntidad.aspx?qS={ce8acff8-8be3-4e2f-91ba-2d6cac7a0fab}` → HTTP 200: sin datos

#### inditex (A15075062)

- `ee/datosgenerales.aspx?nif=A15075062` → HTTP 200: sin datos
- `ee/informaciongobcorp.aspx?nif=A15075062` → HTTP 200: sin datos
- `ee/datosgenerales.aspx?nif=A-15075062` → HTTP 200: con la ficha (sector)
- `ee/informaciongobcorp.aspx?nif=A-15075062` → HTTP 200: con la tabla del IAGC
- `ee/datosgenerales.aspx?nif=a15075062` → HTTP 200: sin datos
- `ee/informaciongobcorp.aspx?nif=a15075062` → HTTP 200: sin datos
- `ee/datosgenerales.aspx?nif=15075062` → HTTP 200: sin datos
- `ee/informaciongobcorp.aspx?nif=15075062` → HTTP 200: sin datos
- buscador «INDUSTRIA DE DISEÑO TEXTIL» → HTTP 200; enlaces: ['../../ANCV/ConsultaISIN.aspx', '../../Advertencias.aspx', '../../AlDia/Comunicaciones-Publicas.aspx', '../../AlDia/Contacto.aspx', '../../AlDia/Discursos-Articulos.aspx', '../../AlDia/Eventos.aspx', '../../AlDia/Galeria-Multimedia.aspx', '../../AlDia/Newsletter-CNMV.aspx', '../../AlDia/Otras-Organizaciones.aspx', '../../AlDia/Premio-Periodismo.aspx', '../../Aldia/ActInternacional/ActInterCNMV.aspx', '../../Aldia/ActInternacional/ActInternacionales.aspx', '../../Aldia/ActInternacional/ComentariosOI.aspx', '../../Aldia/ActInternacional/Glosario.aspx', '../../Aldia/ActInternacional/MapaOrg.aspx', '../../Aldia/ActInternacional/NotasPrensa.aspx', '../../Aldia/ActInternacional/OrgInter.aspx', '../../Aldia/ActInternacional/Revitalizacion-Capitales.aspx', '../../Aldia/TransparenciaSupervisora.aspx', '../../Aldia/VideosCorporativos.aspx', '../../Benchmark/Indices-Referencia.aspx', '../../CSD/Depositario-Central-Valores.aspx', '../../Ciberseguridad.aspx', '../../Finanzas-Sostenibles/Indice.aspx', '../../Fintech/Innovacion.aspx']
- `ee/datosgenerales.aspx?qS={2d4e4466-7ada-4703-bc85-9614b46c3d28}` → HTTP 200: sin datos
- `ee/informaciongobcorp.aspx?qS={2d4e4466-7ada-4703-bc85-9614b46c3d28}` → HTTP 200: con la tabla del IAGC
- `DatosEntidad.aspx?qS={2d4e4466-7ada-4703-bc85-9614b46c3d28}` → HTTP 200: sin datos

#### Los buscadores del portal

- `busqueda.aspx?id=1` → HTTP 200: «CNMV - Datos generales»; campos: []
- `busqueda.aspx?id=2` → HTTP 200: «CNMV - Información financiera intermedia. Fondos de titulización»; campos: []
- `busqueda.aspx?id=3` → HTTP 404: «CNMV - Error»; campos: []
- `busqueda.aspx?id=4` → HTTP 400: «CNMV - Error»; campos: []
- `busqueda.aspx?id=5` → HTTP 404: «CNMV - Error»; campos: []
- `busqueda.aspx?id=6` → HTTP 200: «CNMV - Información financiera intermedia»; campos: []
- `busqueda.aspx?id=7` → HTTP 200: «CNMV - Participaciones Significativas y Autocartera en Sociedades cotizadas»; campos: []
- `busqueda.aspx?id=8` → HTTP 400: «CNMV - Error»; campos: []
- `busqueda.aspx?id=9` → HTTP 400: «CNMV - Error»; campos: []
- `busqueda.aspx?id=10` → HTTP 400: «CNMV - Error»; campos: []
- `busqueda.aspx?id=11` → HTTP 200: «CNMV - Pasaportes recibidos por la CNMV»; campos: []
- `busqueda.aspx?id=12` → HTTP 200: «CNMV - Consulta por entidades»; campos: []
- `busqueda.aspx?id=13` → HTTP 200: «CNMV - Consulta de Sociedades y Agencias de Valores, Sociedades Gestoras de Cartera y Empr»; campos: []
- `busqueda.aspx?id=14` → HTTP 200: «CNMV - Consulta de empresas de servicios de inversión extranjeras»; campos: []
- `busqueda.aspx?id=15` → HTTP 200: «CNMV - Consulta de entidades de crédito»; campos: []


---


Octava vuelta: 2026-09-26T12:23:58.828521+00:00 (`scripts/explorar_cnmv.py`).
Las anteriores siguen debajo.

## Octava vuelta: el consejo del IAGC, tabla a tabla

- portada → HTTP 200 (text/html; charset=utf-8); cookies: 1
- participaciones de Telefónica → HTTP 200 (text/html; charset=utf-8)

### El IAGC del último ejercicio, tabla a tabla

- telefonica: IAGC 2025 (registro 2026028797), 4,008,466 bytes, 167 páginas; bajada 3 s, lectura 29 s; 13 tablas con filas de consejo
  - página 7, 12 columnas, 19 filas; nacimiento en la página: False; encima: «efónica, S.A. está integrado por 15 miembros. A continuación, se detalla la actual composición del Consejo de Administración y la de cada una de sus Comisiones:»
    - primera fila: ['Consejo de Administración Comisiones del Consejo', '', '', '', '', '', '', '', '', '', '', '']
  - página 87, 5 columnas, 15 filas; nacimiento en la página: False; encima: «denominación social Repre- Categoría del Cargo en el Fecha primer nombra- Procedimiento de del consejero sentante consejero Consejo nombramiento miento elección»
    - primera fila: ['—', 'Ejecutivo', 'Presidente', '<fecha>', '<fecha>']
  - página 88, 4 columnas, 6 filas; nacimiento en la página: False; encima: «ique si el cese se denominación social consejero en el nombramiento de las que era miembro ha producido antes del consejero momento del cese del fin del mandato»
    - primera fila: ['Ejecutivo', '<fecha>', '<fecha>', 'Comisión Delegada']
  - página 91, 9 columnas, 7 filas; nacimiento en la página: False; encima: «mplete el siguiente cuadro con la información relativa al número de Consejeras al cierre de los últimos 4 ejercicios, así como la categoría de tales Consejeras:»
    - primera fila: ['', 'Número de Consejeras', '', '', '', '% sobre el total de Consejeros de cada categoría', '', '', '']
  - página 126, 7 columnas, 7 filas; nacimiento en la página: False; encima: «ximo de consejeros 20 Número mínimo de consejeros 5 Número de consejeros fijado por la junta 15 C.1.2 Complete el siguiente cuadro con los miembros del consejo:»
    - primera fila: ['Nombre o denominación social del consejero', 'Representante', 'Categoría del consejero', 'Cargo en el consejo', 'Fecha primer nombramiento', 'Fecha último nombramiento', 'Procedimiento de elección']
  - página 127, 7 columnas, 10 filas; nacimiento en la página: False; encima: «INFORME ANUAL DE GOBIERNO CORPORATIVO DE LAS SOCIEDADES ANÓNIMAS COTIZADAS»
    - primera fila: ['Nombre o denominación social del consejero', 'Representante', 'Categoría del consejero', 'Cargo en el consejo', 'Fecha primer nombramiento', 'Fecha último nombramiento', 'Procedimiento de elección']
  - página 128, 6 columnas, 7 filas; nacimiento en la página: False; encima: «os ceses que, ya sea por dimisión o por acuerdo de la junta general, se hayan producido en el consejo de administración durante el periodo sujeto a información:»
    - primera fila: ['Nombre o denominación social del consejero', 'Categoría del consejero en el momento del cese', 'Fecha del último nombramiento', 'Fecha de baja', 'Comisiones especializadas de las que era miembro', 'Indique si el cese se ha producido antes del fin del mandato']
  - página 131, 9 columnas, 6 filas; nacimiento en la página: False; encima: «mplete el siguiente cuadro con la información relativa al número de consejeras al cierre de los últimos 4 ejercicios, así como la categoría de tales consejeras:»
    - primera fila: ['', 'Número de consejeras', '', '', '', '% sobre el total de consejeros de cada categoría', '', '', '']
  - página 139, 3 columnas, 8 filas; nacimiento en la página: False; encima: « comisiones del consejo de administración, sus miembros y la proporción de consejeros ejecutivos, dominicales, independientes y otros externos que las integran:»
    - primera fila: ['COMISIÓN DELEGADA', '', '']
  - página 140, 3 columnas, 5 filas; nacimiento en la página: False; encima: «INFORME ANUAL DE GOBIERNO CORPORATIVO DE LAS SOCIEDADES ANÓNIMAS COTIZADAS»
    - primera fila: ['COMISIÓN DELEGADA', '', '']
  - página 140, 3 columnas, 6 filas; nacimiento en la página: False; encima: « VOCAL Independiente % de consejeros ejecutivos 22,22 % de consejeros dominicales 33,33 % de consejeros independientes 44,44 % de consejeros otros externos 0,00»
    - primera fila: ['COMISIÓN DE AUDITORÍA Y CONTROL', '', '']
  - página 140, 3 columnas, 7 filas; nacimiento en la página: False; encima: «ejeros BLANCO / DON PETER LÖSCHER / con experiencia DON CARLOS OCAÑA ORBIS / DON ALEJANDRO REYNAL AMPLE Fecha de nombramiento <fecha> del presidente en el cargo»
    - primera fila: ['COMISIÓN DE NOMBRAMIENTOS, RETRIBUCIONES Y BUEN GOBIERNO', '', '']
  - página 141, 3 columnas, 6 filas; nacimiento en la página: False; encima: «% de consejeros ejecutivos 0,00 % de consejeros dominicales 20,00 % de consejeros independientes 80,00 % de consejeros otros externos 0,00»
    - primera fila: ['COMISIÓN DE SOSTENIBILIDAD Y REGULACIÓN', '', '']
- prisa: IAGC 2025 (registro 2026042679), 4,334,018 bytes, 191 páginas; bajada 2 s, lectura 98 s; 17 tablas con filas de consejo
  - página 15, 7 columnas, 7 filas; nacimiento en la página: False; encima: «ximo de consejeros 15 Número mínimo de consejeros 5 Número de consejeros fijado por la junta 14 C.1.2 Complete el siguiente cuadro con los miembros del consejo:»
    - primera fila: ['Nombre o denominación social del consejero', 'Representante', 'Categoría del consejero', 'Cargo en el consejo', 'Fecha primer nombramiento', 'Fecha último nombramiento', 'Procedimiento de elección']
  - página 16, 7 columnas, 9 filas; nacimiento en la página: False; encima: «INFORME ANUAL DE GOBIERNO CORPORATIVO DE LAS SOCIEDADES ANÓNIMAS COTIZADAS»
    - primera fila: ['Nombre o denominación social del consejero', 'Representante', 'Categoría del consejero', 'Cargo en el consejo', 'Fecha primer nombramiento', 'Fecha último nombramiento', 'Procedimiento de elección']
  - página 17, 6 columnas, 2 filas; nacimiento en la página: False; encima: «os ceses que, ya sea por dimisión o por acuerdo de la junta general, se hayan producido en el consejo de administración durante el periodo sujeto a información:»
    - primera fila: ['Nombre o denominación social del consejero', 'Categoría del consejero en el momento del cese', 'Fecha del último nombramiento', 'Fecha de baja', 'Comisiones especializadas de las que era miembro', 'Indique si el cese se ha producido antes del fin del mandato']
  - página 26, 9 columnas, 7 filas; nacimiento en la página: False; encima: «mplete el siguiente cuadro con la información relativa al número de consejeras al cierre de los últimos 4 ejercicios, así como la categoría de tales consejeras:»
    - primera fila: ['', 'Número de consejeras', '', '', '', '% sobre el total de consejeros de cada categoría', '', '', '']
  - página 45, 3 columnas, 6 filas; nacimiento en la página: False; encima: « comisiones del consejo de administración, sus miembros y la proporción de consejeros ejecutivos, dominicales, independientes y otros externos que las integran:»
    - primera fila: ['Comisión de Auditoría, Riesgos y Cumplimiento', '', '']
  - página 46, 3 columnas, 6 filas; nacimiento en la página: False; encima: «S ÁLVAREZ / DOÑA CARMEN con experiencia FERNÁNDEZ DE ALARCÓN ROCA / DOÑA BEATRICE DE CLERMONT- TONNERRE Fecha de nombramiento <fecha> del presidente en el cargo»
    - primera fila: ['Comisión de Nombramientos, Retribuciones y Gobierno Corporativo', '', '']
  - página 47, 3 columnas, 6 filas; nacimiento en la página: False; encima: « que ha emitido (y que se publicará al tiempo de publicarse el anuncio de convocatoria de la Junta Ordinaria de Accionistas 2026, en la página web corporativa).»
    - primera fila: ['Comisión de Sostenibilidad', '', '']
  - página 48, 3 columnas, 7 filas; nacimiento en la página: False; encima: «ión (que se publicará al tiempo de publicarse el anuncio de convocatoria de la Junta Ordinaria de Accionistas 2026, en la página web corporativa www.prisa.com).»
    - primera fila: ['Comisión Delegada', '', '']
  - página 101, 7 columnas, 7 filas; nacimiento en la página: False; encima: «ximo de consejeros 15 Número mínimo de consejeros 5 Número de consejeros fijado por la junta 14 C.1.2 Complete el siguiente cuadro con los miembros del consejo:»
    - primera fila: ['Nombre o denominación social del consejero', 'Representante', 'Categoría del consejero', 'Cargo en el consejo', 'Fecha primer nombramiento', 'Fecha último nombramiento', 'Procedimiento de elección']
  - página 102, 7 columnas, 9 filas; nacimiento en la página: False; encima: «INFORME ANUAL DE GOBIERNO CORPORATIVO DE LAS SOCIEDADES ANÓNIMAS COTIZADAS»
    - primera fila: ['Nombre o denominación social del consejero', 'Representante', 'Categoría del consejero', 'Cargo en el consejo', 'Fecha primer nombramiento', 'Fecha último nombramiento', 'Procedimiento de elección']
  - página 103, 6 columnas, 2 filas; nacimiento en la página: False; encima: «os ceses que, ya sea por dimisión o por acuerdo de la junta general, se hayan producido en el consejo de administración durante el periodo sujeto a información:»
    - primera fila: ['Nombre o denominación social del consejero', 'Categoría del consejero en el momento del cese', 'Fecha del último nombramiento', 'Fecha de baja', 'Comisiones especializadas de las que era miembro', 'Indique si el cese se ha producido antes del fin del mandato']
  - página 112, 9 columnas, 7 filas; nacimiento en la página: False; encima: «mplete el siguiente cuadro con la información relativa al número de consejeras al cierre de los últimos 4 ejercicios, así como la categoría de tales consejeras:»
    - primera fila: ['', 'Número de consejeras', '', '', '', '% sobre el total de consejeros de cada categoría', '', '', '']
  - página 131, 3 columnas, 6 filas; nacimiento en la página: False; encima: « comisiones del consejo de administración, sus miembros y la proporción de consejeros ejecutivos, dominicales, independientes y otros externos que las integran:»
    - primera fila: ['Comisión de Auditoría, Riesgos y Cumplimiento', '', '']
  - página 132, 3 columnas, 6 filas; nacimiento en la página: False; encima: «S ÁLVAREZ / DOÑA CARMEN con experiencia FERNÁNDEZ DE ALARCÓN ROCA / DOÑA BEATRICE DE CLERMONT- TONNERRE Fecha de nombramiento <fecha> del presidente en el cargo»
    - primera fila: ['Comisión de Nombramientos, Retribuciones y Gobierno Corporativo', '', '']
  - página 133, 3 columnas, 6 filas; nacimiento en la página: False; encima: « que ha emitido (y que se publicará al tiempo de publicarse el anuncio de convocatoria de la Junta Ordinaria de Accionistas 2026, en la página web corporativa).»
    - primera fila: ['Comisión de Sostenibilidad', '', '']
  - página 134, 3 columnas, 5 filas; nacimiento en la página: False; encima: «ión (que se publicará al tiempo de publicarse el anuncio de convocatoria de la Junta Ordinaria de Accionistas 2026, en la página web corporativa www.prisa.com).»
    - primera fila: ['Comisión Delegada', '', '']
  - página 135, 3 columnas, 4 filas; nacimiento en la página: False; encima: «INFORME ANUAL DE GOBIERNO CORPORATIVO DE LAS SOCIEDADES ANÓNIMAS COTIZADAS»
    - primera fila: ['Comisión Delegada', '', '']
- santander: IAGC 2025 (registro 2026029544), 6,644,367 bytes, 216 páginas; bajada 4 s, lectura 39 s; 11 tablas con filas de consejo
  - página 142, 2 columnas, 2 filas; nacimiento en la página: False; encima: «externos que las integran: Comisión ejecutiva Nombre Cargo Categoría Ana Botín-Sanz de Sautuola y O’Shea Presidente Ejecutivo Héctor Grisi Checa Vocal Ejecutivo»
    - primera fila: ['', 'Otro externo']
  - página 175, 7 columnas, 7 filas; nacimiento en la página: False; encima: «imo de consejeros 17 Número mínimo de consejeros 12 Número de consejeros fijado por la junta 15 C.1.2 Complete el siguiente cuadro con los miembros del consejo:»
    - primera fila: ['Nombre o denominación social del consejero', 'Representante', 'Categoría del consejero', 'Cargo en el consejo', 'Fecha primer nombramiento', 'Fecha último nombramiento', 'Procedimiento de elección']
  - página 176, 7 columnas, 10 filas; nacimiento en la página: False; encima: «INFORME ANUAL DE GOBIERNO CORPORATIVO DE LAS SOCIEDADES ANÓNIMAS COTIZADAS»
    - primera fila: ['Nombre o denominación social del consejero', 'Representante', 'Categoría del consejero', 'Cargo en el consejo', 'Fecha primer nombramiento', 'Fecha último nombramiento', 'Procedimiento de elección']
  - página 183, 9 columnas, 7 filas; nacimiento en la página: False; encima: «mplete el siguiente cuadro con la información relativa al número de consejeras al cierre de los últimos 4 ejercicios, así como la categoría de tales consejeras:»
    - primera fila: ['', 'Número de consejeras', '', '', '', '% sobre el total de consejeros de cada categoría', '', '', '']
  - página 190, 3 columnas, 7 filas; nacimiento en la página: False; encima: « comisiones del consejo de administración, sus miembros y la proporción de consejeros ejecutivos, dominicales, independientes y otros externos que las integran:»
    - primera fila: ['COMISIÓN DE AUDITORÍA', '', '']
  - página 191, 3 columnas, 7 filas; nacimiento en la página: False; encima: «nsejeros ESCAMILLA / DOÑA HOMAIRA con experiencia AKBARI / DON HENRIQUE DE CASTRO / DOÑA PAMELA WALKDEN Fecha de nombramiento <fecha> del presidente en el cargo»
    - primera fila: ['COMISIÓN DE BANCA RESPONSABLE, SOSTENIBILIDAD Y CULTURA', '', '']
  - página 191, 3 columnas, 10 filas; nacimiento en la página: False; encima: «N VOCAL Independiente % de consejeros ejecutivos 0,00 % de consejeros dominicales 0,00 % de consejeros independientes 100,00 % de consejeros otros externos 0,00»
    - primera fila: ['COMISIÓN DE INNOVACIÓN Y TECNOLOGÍA', '', '']
  - página 192, 3 columnas, 7 filas; nacimiento en la página: False; encima: «% de consejeros dominicales 0,00 % de consejeros independientes 62,50 % de consejeros otros externos 12,50»
    - primera fila: ['COMISIÓN DE NOMBRAMIENTOS', '', '']
  - página 192, 3 columnas, 7 filas; nacimiento en la página: False; encima: «S VOCAL Independiente % de consejeros ejecutivos 0,00 % de consejeros dominicales 0,00 % de consejeros independientes 100,00 % de consejeros otros externos 0,00»
    - primera fila: ['COMISIÓN DE RETRIBUCIONES', '', '']
  - página 192, 3 columnas, 7 filas; nacimiento en la página: False; encima: «S VOCAL Independiente % de consejeros ejecutivos 0,00 % de consejeros dominicales 0,00 % de consejeros independientes 80,00 % de consejeros otros externos 20,00»
    - primera fila: ['COMISIÓN DE SUPERVISIÓN DE RIESGOS, REGULACIÓN Y CUMPLIMIENTO', '', '']
  - página 193, 3 columnas, 7 filas; nacimiento en la página: False; encima: «% de consejeros dominicales 0,00 % de consejeros independientes 60,00 % de consejeros otros externos 40,00»
    - primera fila: ['COMISIÓN EJECUTIVA', '', '']
- bbva: IAGC 2025 (registro 2026023386), 12,593,738 bytes, 180 páginas; bajada 4 s, lectura 39 s; 18 tablas con filas de consejo
  - página 26, 6 columnas, 16 filas; nacimiento en la página: True; encima: «Consejo (C.1.2) A 31 de diciembre de 2025, los miembros del Consejo de Administración son los siguientes, todos ellos nombrados por acuerdo de la Junta General:»
    - primera fila: ['Nombre', 'Cargo en el Consejo', 'Año de nacimiento', 'Categoría', 'Fecha primer nombramiento', 'Fecha último nombramiento']
  - página 55, 3 columnas, 6 filas; nacimiento en la página: False; encima: «te del Consejo de Administración será miembro nato de la Comisión. A 31 de diciembre de 2025, la composición de la Comisión Delegada Permanente es la siguiente:»
    - primera fila: ['Nombre', 'Cargo', 'Categoría']
  - página 58, 3 columnas, 7 filas; nacimiento en la página: False; encima: «o años, pudiendo ser reelegido una vez transcurrido un año desde su cese. A 31 de diciembre de 2025, la composición de la Comisión de Auditoría es la siguiente:»
    - primera fila: ['Nombre', 'Cargo', 'Categoría']
  - página 65, 3 columnas, 6 filas; nacimiento en la página: False; encima: «de independientes, al igual que su presidente. A 31 de diciembre de 2025, la composición de la Comisión de Nombramientos y Gobierno Corporativo es la siguiente:»
    - primera fila: ['Nombre', 'Cargo', 'Categoría']
  - página 69, 3 columnas, 6 filas; nacimiento en la página: False; encima: «yoría de ellos consejeros independientes, al igual que su presidente. A 31 de diciembre de 2025, la composición de la Comisión de Retribuciones es la siguiente:»
    - primera fila: ['Nombre', 'Cargo', 'Categoría']
  - página 74, 3 columnas, 6 filas; nacimiento en la página: False; encima: «llos, consejeros independientes, al igual que su presidente. A 31 de diciembre de 2025, la composición de la Comisión de Riesgos y Cumplimiento es la siguiente:»
    - primera fila: ['Nombre', 'Cargo', 'Categoría']
  - página 79, 3 columnas, 6 filas; nacimiento en la página: False; encima: «ría de los cuales deberán ser consejeros no ejecutivos. A 31 de diciembre de 2025, la composición de la Comisión de Tecnología y Ciberseguridad es la siguiente:»
    - primera fila: ['Nombre', 'Cargo', 'Categoría']
  - página 140, 7 columnas, 7 filas; nacimiento en la página: False; encima: «ximo de consejeros 15 Número mínimo de consejeros 5 Número de consejeros fijado por la junta 15 C.1.2 Complete el siguiente cuadro con los miembros del consejo:»
    - primera fila: ['Nombre o denominación social del consejero', 'Representante', 'Categoría del consejero', 'Cargo en el consejo', 'Fecha primer nombramiento', 'Fecha último nombramiento', 'Procedimiento de elección']
  - página 141, 7 columnas, 10 filas; nacimiento en la página: False; encima: «INFORME ANUAL DE GOBIERNO CORPORATIVO DE LAS SOCIEDADES ANÓNIMAS COTIZADAS»
    - primera fila: ['Nombre o denominación social del consejero', 'Representante', 'Categoría del consejero', 'Cargo en el consejo', 'Fecha primer nombramiento', 'Fecha último nombramiento', 'Procedimiento de elección']
  - página 149, 9 columnas, 7 filas; nacimiento en la página: False; encima: «mplete el siguiente cuadro con la información relativa al número de consejeras al cierre de los últimos 4 ejercicios, así como la categoría de tales consejeras:»
    - primera fila: ['', 'Número de consejeras', '', '', '', '% sobre el total de consejeros de cada categoría', '', '', '']
  - página 155, 3 columnas, 6 filas; nacimiento en la página: False; encima: « comisiones del consejo de administración, sus miembros y la proporción de consejeros ejecutivos, dominicales, independientes y otros externos que las integran:»
    - primera fila: ['COMISIÓN DE NOMBRAMIENTOS Y GOBIERNO CORPORATIVO', '', '']
  - página 156, 3 columnas, 3 filas; nacimiento en la página: False; encima: «INFORME ANUAL DE GOBIERNO CORPORATIVO DE LAS SOCIEDADES ANÓNIMAS COTIZADAS»
    - primera fila: ['COMISIÓN DE NOMBRAMIENTOS Y GOBIERNO CORPORATIVO', '', '']
  - página 156, 3 columnas, 7 filas; nacimiento en la página: False; encima: «A VOCAL Independiente % de consejeros ejecutivos 0,00 % de consejeros dominicales 0,00 % de consejeros independientes 60,00 % de consejeros otros externos 40,00»
    - primera fila: ['COMISIÓN DE RETRIBUCIONES', '', '']
  - página 156, 3 columnas, 7 filas; nacimiento en la página: False; encima: «ÍN VOCAL Otro Externo % de consejeros ejecutivos 0,00 % de consejeros dominicales 0,00 % de consejeros independientes 80,00 % de consejeros otros externos 20,00»
    - primera fila: ['COMISIÓN DE RIESGOS Y CUMPLIMIENTO', '', '']
  - página 156, 3 columnas, 4 filas; nacimiento en la página: False; encima: «A VOCAL Independiente % de consejeros ejecutivos 0,00 % de consejeros dominicales 0,00 % de consejeros independientes 100,00 % de consejeros otros externos 0,00»
    - primera fila: ['COMISIÓN DELEGADA PERMANENTE', '', '']
  - página 157, 3 columnas, 5 filas; nacimiento en la página: False; encima: «INFORME ANUAL DE GOBIERNO CORPORATIVO DE LAS SOCIEDADES ANÓNIMAS COTIZADAS»
    - primera fila: ['COMISIÓN DELEGADA PERMANENTE', '', '']
  - página 157, 3 columnas, 7 filas; nacimiento en la página: False; encima: «GENÇ VOCAL Ejecutivo % de consejeros ejecutivos 40,00 % de consejeros dominicales 0,00 % de consejeros independientes 40,00 % de consejeros otros externos 20,00»
    - primera fila: ['COMISIÓN DE TECNOLOGÍA Y CIBERSEGURIDAD', '', '']
  - página 157, 3 columnas, 8 filas; nacimiento en la página: False; encima: « VOCAL Independiente % de consejeros ejecutivos 20,00 % de consejeros dominicales 0,00 % de consejeros independientes 60,00 % de consejeros otros externos 20,00»
    - primera fila: ['COMISIÓN DE AUDITORÍA', '', '']
- repsol: IAGC 2025 (registro 2026025989), 39,982,065 bytes, 143 páginas; bajada 8 s, lectura 24 s; 9 tablas con filas de consejo
  - página 97, 7 columnas, 7 filas; nacimiento en la página: False; encima: «ximo de consejeros 16 Número mínimo de consejeros 9 Número de consejeros fijado por la junta 15 C.1.2 Complete el siguiente cuadro con los miembros del consejo:»
    - primera fila: ['Nombre o denominación social del consejero', 'Representante', 'Categoría del consejero', 'Cargo en el consejo', 'Fecha primer nombramiento', 'Fecha último nombramiento', 'Procedimiento de elección']
  - página 98, 7 columnas, 10 filas; nacimiento en la página: False; encima: «INFORME ANUAL DE GOBIERNO CORPORATIVO DE LAS SOCIEDADES ANÓNIMAS COTIZADAS»
    - primera fila: ['Nombre o denominación social del consejero', 'Representante', 'Categoría del consejero', 'Cargo en el consejo', 'Fecha primer nombramiento', 'Fecha último nombramiento', 'Procedimiento de elección']
  - página 113, 4 columnas, 2 filas; nacimiento en la página: False; encima: « externos 4 % sobre el total del consejo 26,67 Indique las variaciones que, en su caso, se hayan producido durante el periodo en la categoría de cada consejero:»
    - primera fila: ['Nombre o denominación social del consejero', 'Fecha del cambio', 'Categoría anterior', 'Categoría actual']
  - página 113, 9 columnas, 7 filas; nacimiento en la página: False; encima: «mplete el siguiente cuadro con la información relativa al número de consejeras al cierre de los últimos 4 ejercicios, así como la categoría de tales consejeras:»
    - primera fila: ['', 'Número de consejeras', '', '', '', '% sobre el total de consejeros de cada categoría', '', '', '']
  - página 120, 3 columnas, 7 filas; nacimiento en la página: False; encima: « comisiones del consejo de administración, sus miembros y la proporción de consejeros ejecutivos, dominicales, independientes y otros externos que las integran:»
    - primera fila: ['Comisión de Auditoría y Control', '', '']
  - página 121, 3 columnas, 5 filas; nacimiento en la página: False; encima: «de los consejeros FERREZUELO / DOÑA TERESA con experiencia GARCÍA-MILÁ LLOVERAS / DOÑA AURORA CATÁ SALA Fecha de nombramiento <fecha> del presidente en el cargo»
    - primera fila: ['Comisión de Nombramientos', '', '']
  - página 121, 3 columnas, 5 filas; nacimiento en la página: False; encima: «SIDENTE Independiente % de consejeros ejecutivos 0,00 % de consejeros dominicales 0,00 % de consejeros independientes 66,67 % de consejeros otros externos 33,33»
    - primera fila: ['Comisión de Retribuciones', '', '']
  - página 121, 3 columnas, 6 filas; nacimiento en la página: False; encima: «xterno DOÑA AURORA CATÁ SALA PRESIDENTE Independiente % de consejeros dominicales 0,00 % de consejeros independientes 66,67 % de consejeros otros externos 33,33»
    - primera fila: ['Comisión de Sostenibilidad', '', '']
  - página 122, 3 columnas, 10 filas; nacimiento en la página: False; encima: «% de consejeros ejecutivos 0,00 % de consejeros dominicales 0,00 % de consejeros independientes 75,00 % de consejeros otros externos 25,00»
    - primera fila: ['Comisión Delegada', '', '']


---


Octava vuelta: 2026-09-26T12:15:52.306386+00:00 (`scripts/explorar_cnmv.py`).
Las anteriores siguen debajo.

## Octava vuelta: el consejo del IAGC, tabla a tabla

- portada → HTTP 0 (error: Server disconnected without sending a response.); cookies: 0
- participaciones de Telefónica → HTTP 0 (error: Server disconnected without sending a response.)

### El IAGC del último ejercicio, tabla a tabla

- telefonica: sin IAGC en su tabla (HTTP 0, error: The read operation timed out)
- prisa: sin IAGC en su tabla (HTTP 0, error: Server disconnected without sending a response.)
- santander: sin IAGC en su tabla (HTTP 0, error: Server disconnected without sending a response.)
- bbva: sin IAGC en su tabla (HTTP 0, error: The read operation timed out)
- repsol: sin IAGC en su tabla (HTTP 0, error: The read operation timed out)


---


Séptima vuelta: 2026-09-26T12:02:48.741256+00:00 (`scripts/explorar_cnmv.py`).
Las anteriores siguen debajo.

## Séptima vuelta: consejos y directivos, con la sesión hecha

- portada → HTTP 200 (text/html; charset=utf-8); cookies: 1
- participaciones de Telefónica → HTTP 200 (text/html; charset=utf-8)

### El consejo en el informe de gobierno corporativo, por filas

- telefonica: 167 páginas, 42 filas de consejo; categorías {'ejecutivo': 8, 'dominical': 8, 'independiente': 24, 'otro externo': 2}; forma de la primera: [4]
- prisa: 191 páginas, 28 filas de consejo; categorías {'dominical': 8, 'independiente': 14, 'ejecutivo': 6}; forma de la primera: [5]
- santander: 216 páginas, 15 filas de consejo; categorías {'independiente': 10, 'otro externo': 3, 'ejecutivo': 2}; forma de la primera: [5]
- bbva: 180 páginas, 26 filas de consejo; categorías {'ejecutivo': 4, 'independiente': 20, 'otro externo': 2}; forma de la primera: [5]
- repsol: 143 páginas, 16 filas de consejo; categorías {'independiente': 11, 'otro externo': 4, 'ejecutivo': 1}; forma de la primera: [5]

### Notificaciones de directivos: sólo la forma

- telefonica: HTTP 200, 0 tablas (text/html; charset=utf-8)
- prisa: HTTP 200, 0 tablas (text/html; charset=utf-8)
- santander: HTTP 200, 0 tablas (text/html; charset=utf-8)


---


Sexta vuelta: 2026-09-26T11:39:45.204368+00:00 (`scripts/explorar_cnmv.py`).
Las anteriores siguen debajo.

## Sexta vuelta: consejos y directivos

### El consejo en el informe de gobierno corporativo, por filas

- telefonica: sin informes por NIF
- prisa: sin informes por NIF
- santander: sin informes por NIF
- bbva: sin informes por NIF
- repsol: sin informes por NIF

### Notificaciones de directivos: sólo la forma

- telefonica: HTTP 0, 0 tablas
- prisa: HTTP 0, 0 tablas
- santander: HTTP 0, 0 tablas


---


Quinta vuelta: 2026-09-26T11:05:11.962821+00:00 (`scripts/explorar_cnmv.py`).
Las anteriores siguen debajo.

## Quinta vuelta: el buscador por denominación

### El buscador de participaciones significativas

- `https://www.cnmv.es/portal/Consultas/busqueda.aspx?id=7` → HTTP 200 · «CNMV - Participaciones Significativas y Autocartera en Sociedades cotizadas» · final `https://www.cnmv.es/portal/Consultas/busqueda?id=7`
- ocultos: ['__EVENTVALIDATION', '__VIEWSTATE', '__VIEWSTATEGENERATOR']
- de texto: []
- botones: [('ctl00$WucCookiesPolicy$btnCookiesConfirmTech', 'Aceptar solo las imprescindibles'), ('ctl00$WucCookiesPolicy$btnCookiesConfirmAll', 'Aceptar todas'), ('ctl00$WucCookiesPolicy$btnCookiesConfirmSelected', 'Confirmar selección'), ('ctl00$WucCookiesPolicy$btnCookiesConfirmAll2', 'Aceptar todas'), ('ctl00$ContentPrincipal$btnOk', 'Buscar'), ('ctl00$ContentPrincipal$btnLimpiar', 'Limpiar')]
- desplegables: []
- contenido: 'ContentPrincipal_wNombreEntidad_txtDenominacion" id="ctl00_ContentPrincipal_wNombreEntidad_lblDenominacion" class="enlinea3">Por denominación de la entidad: Por intervalo de fechas de registro (dd/mm/aaaa): Fecha desde: Fecha hasta: Por los registros de los últimos días <'
- campo de denominación: ctl00$ContentPrincipal$wNombreEntidad$txtDenominacion
- «IBERDROLA» → HTTP 200 · 213,167 caracteres · enlaces: ['Autocartera.aspx?qS={f113e1f8-aae6-44fb-ad50-c7e7a3320512}', 'Notificaciones-Participaciones.aspx?qS={f113e1f8-aae6-44fb-ad50-c7e7a3320512}', 'SociedadesParticipa.aspx?qS={f113e1f8-aae6-44fb-ad50-c7e7a3320512}', 'https://www.cnmv.es/portal/consultas/derechosvoto/ps_ac_ini?qS={32a67081-f3a5-448a-9375-4137c10b17bf}&lang=ca', 'https://www.cnmv.es/portal/consultas/derechosvoto/ps_ac_ini?qS={32a67081-f3a5-448a-9375-4137c10b17bf}&lang=en', 'https://www.cnmv.es/portal/consultas/derechosvoto/ps_ac_ini?qS={32a67081-f3a5-448a-9375-4137c10b17bf}&lang=es', 'https://www.cnmv.es/portal/consultas/derechosvoto/ps_ac_ini?qS={32a67081-f3a5-448a-9375-4137c10b17bf}&lang=eu', 'https://www.cnmv.es/portal/consultas/derechosvoto/ps_ac_ini?qS={32a67081-f3a5-448a-9375-4137c10b17bf}&lang=gl']
  - contenido: 'ContentPrincipal_titulo_wuc_Noscript1"> Notificaciones de derechos de voto e instrumentos financieros Sociedades cotizadas donde participa Notificaciones sobre acciones propias (Autocartera) <'
- «INDRA SISTEMAS» → HTTP 200 · 213,202 caracteres · enlaces: ['Autocartera.aspx?qS={d69f4887-b880-452b-ad60-631c30d9b330}', 'Notificaciones-Participaciones.aspx?qS={d69f4887-b880-452b-ad60-631c30d9b330}', 'SociedadesParticipa.aspx?qS={d69f4887-b880-452b-ad60-631c30d9b330}', 'https://www.cnmv.es/portal/consultas/derechosvoto/ps_ac_ini?qS={d8cffa67-ed46-4f34-adcd-6d6f97efb70b}&lang=ca', 'https://www.cnmv.es/portal/consultas/derechosvoto/ps_ac_ini?qS={d8cffa67-ed46-4f34-adcd-6d6f97efb70b}&lang=en', 'https://www.cnmv.es/portal/consultas/derechosvoto/ps_ac_ini?qS={d8cffa67-ed46-4f34-adcd-6d6f97efb70b}&lang=es', 'https://www.cnmv.es/portal/consultas/derechosvoto/ps_ac_ini?qS={d8cffa67-ed46-4f34-adcd-6d6f97efb70b}&lang=eu', 'https://www.cnmv.es/portal/consultas/derechosvoto/ps_ac_ini?qS={d8cffa67-ed46-4f34-adcd-6d6f97efb70b}&lang=gl']
  - contenido: 'ContentPrincipal_titulo_wuc_Noscript1"> Notificaciones de derechos de voto e instrumentos financieros Sociedades cotizadas donde participa Notificaciones sobre acciones propias (Autocartera) <'
- «INDUSTRIA DE DISEÑO TEXTIL» → HTTP 200 · 213,303 caracteres · enlaces: ['Autocartera.aspx?qS={f14109e7-2300-4e20-aff2-51eea38685b4}', 'Notificaciones-Participaciones.aspx?qS={f14109e7-2300-4e20-aff2-51eea38685b4}', 'SociedadesParticipa.aspx?qS={f14109e7-2300-4e20-aff2-51eea38685b4}', 'https://www.cnmv.es/portal/consultas/derechosvoto/ps_ac_ini?qS={788b190b-afa7-44bc-abcb-013e5f4942ee}&lang=ca', 'https://www.cnmv.es/portal/consultas/derechosvoto/ps_ac_ini?qS={788b190b-afa7-44bc-abcb-013e5f4942ee}&lang=en', 'https://www.cnmv.es/portal/consultas/derechosvoto/ps_ac_ini?qS={788b190b-afa7-44bc-abcb-013e5f4942ee}&lang=es', 'https://www.cnmv.es/portal/consultas/derechosvoto/ps_ac_ini?qS={788b190b-afa7-44bc-abcb-013e5f4942ee}&lang=eu', 'https://www.cnmv.es/portal/consultas/derechosvoto/ps_ac_ini?qS={788b190b-afa7-44bc-abcb-013e5f4942ee}&lang=gl']
  - contenido: 'ContentPrincipal_titulo_wuc_Noscript1"> Notificaciones de derechos de voto e instrumentos financieros Sociedades cotizadas donde participa Notificaciones sobre acciones propias (Autocartera) <'
- «ATRESMEDIA» → HTTP 200 · 213,736 caracteres · enlaces: ['../../HR/HSPactosParasociales.aspx?qS={ba0de6e4-195c-4a67-ae91-af8e586a21bd}', 'Autocartera.aspx?qS={ba0de6e4-195c-4a67-ae91-af8e586a21bd}', 'Notificaciones-Participaciones.aspx?qS={ba0de6e4-195c-4a67-ae91-af8e586a21bd}', 'SociedadesParticipa.aspx?qS={ba0de6e4-195c-4a67-ae91-af8e586a21bd}', 'https://www.cnmv.es/portal/consultas/derechosvoto/ps_ac_ini?qS={7ea16c6c-8e4e-4f68-96d0-7a2e09b4c7a1}&lang=ca', 'https://www.cnmv.es/portal/consultas/derechosvoto/ps_ac_ini?qS={7ea16c6c-8e4e-4f68-96d0-7a2e09b4c7a1}&lang=en', 'https://www.cnmv.es/portal/consultas/derechosvoto/ps_ac_ini?qS={7ea16c6c-8e4e-4f68-96d0-7a2e09b4c7a1}&lang=es', 'https://www.cnmv.es/portal/consultas/derechosvoto/ps_ac_ini?qS={7ea16c6c-8e4e-4f68-96d0-7a2e09b4c7a1}&lang=eu']
  - contenido: 'ContentPrincipal_titulo_wuc_Noscript1"> Notificaciones de derechos de voto e instrumentos financieros Sociedades cotizadas donde participa Notificaciones sobre acciones propias (Autocartera) Comunicación de Pactos parasociales <'


---


Cuarta vuelta: 2026-09-26T11:03:09.318976+00:00 (`scripts/explorar_cnmv.py`).
Las anteriores siguen debajo.

## Cuarta vuelta

### DatosEntidad por NIF en una muestra amplia

- repsol (A78374725) → HTTP 200 · «REPSOL, S.A.»
- bbva (A48265169) → HTTP 200 · «BANCO BILBAO VIZCAYA ARGENTARIA, S.A.»
- inditex (A15075062) → HTTP 200 · «sin datos»
- aena (A86212420) → HTTP 200 · «AENA, S.M.E., S.A.»
- endesa (A81948077) → HTTP 200 · «sin datos»
- naturgy (A08015497) → HTTP 200 · «NATURGY ENERGY GROUP, S.A.»
- caixabank (A08663619) → HTTP 200 · «CAIXABANK, S.A.»
- sabadell (A08000143) → HTTP 200 · «BANCO DE SABADELL, S.A.»
- mapfre (A08055741) → HTTP 200 · «MAPFRE, S.A.»
- acciona (A08001851) → HTTP 200 · «ACCIONA, S.A.»
- grifols (A58389123) → HTTP 200 · «GRIFOLS, S.A.»
- cellnex (A64907306) → HTTP 200 · «CELLNEX TELECOM, S.A.»
- colonial (A28027399) → HTTP 200 · «sin datos»
- merlin (A86977790) → HTTP 200 · «MERLIN PROPERTIES, SOCIMI, S.A.»
- sacyr (A28013811) → HTTP 200 · «sin datos»
- bankinter (A28157360) → HTTP 200 · «BANKINTER, S.A.»
- enagas (A28294726) → HTTP 200 · «sin datos»
- amadeus (A84236934) → HTTP 200 · «sin datos»
- acerinox (A28250777) → HTTP 200 · «sin datos»
- unicaja (A93139053) → HTTP 200 · «UNICAJA BANCO, S.A.»
- vocento (A48001655) → HTTP 200 · «sin datos»
- logista (A87008579) → HTTP 200 · «LOGISTA INTEGRAL, S.A.»

Con datos: 14; sin datos: 8 (['inditex', 'endesa', 'colonial', 'sacyr', 'enagas', 'amadeus', 'acerinox', 'vocento'])

### El buscador de participaciones significativas

- `https://www.cnmv.es/portal/Consultas/busqueda.aspx?id=7` → HTTP 200 · «CNMV - Participaciones Significativas y Autocartera en Sociedades cotizadas» · final `https://www.cnmv.es/portal/Consultas/busqueda?id=7`
- ocultos: ['__EVENTVALIDATION', '__VIEWSTATE', '__VIEWSTATEGENERATOR']
- de texto: []
- botones: [('ctl00$WucCookiesPolicy$btnCookiesConfirmTech', 'Aceptar solo las imprescindibles'), ('ctl00$WucCookiesPolicy$btnCookiesConfirmAll', 'Aceptar todas'), ('ctl00$WucCookiesPolicy$btnCookiesConfirmSelected', 'Confirmar selección'), ('ctl00$WucCookiesPolicy$btnCookiesConfirmAll2', 'Aceptar todas'), ('ctl00$ContentPrincipal$btnOk', 'Buscar'), ('ctl00$ContentPrincipal$btnLimpiar', 'Limpiar')]
- desplegables: []
- contenido: 'ContentPrincipal_wNombreEntidad_txtDenominacion" id="ctl00_ContentPrincipal_wNombreEntidad_lblDenominacion" class="enlinea3">Por denominación de la entidad: Por intervalo de fechas de registro (dd/mm/aaaa): Fecha desde: Fecha hasta: Por los registros de los últimos días <'
- no hay campo de texto reconocible


---


Tercera vuelta: 2026-09-26T10:57:43.367136+00:00 (`scripts/explorar_cnmv.py`).
La segunda vuelta sigue debajo.

## Tercera vuelta

### Participaciones de telefonica

- `ps_ac_ini` → HTTP 200; enlaces con qS: ['https://www.cnmv.es/portal/Consultas/derechosvoto/Notificaciones-Participaciones.aspx?qS={2e0da3d2-af21-4f16-8dd2-31cdd5160df2}', 'https://www.cnmv.es/portal/Consultas/derechosvoto/SociedadesParticipa.aspx?qS={2e0da3d2-af21-4f16-8dd2-31cdd5160df2}', 'https://www.cnmv.es/portal/Consultas/derechosvoto/Autocartera.aspx?qS={2e0da3d2-af21-4f16-8dd2-31cdd5160df2}', 'https://www.cnmv.es/portal/HR/HSPactosParasociales.aspx?qS={2e0da3d2-af21-4f16-8dd2-31cdd5160df2}']

`https://www.cnmv.es/portal/Consultas/derechosvoto/Notificaciones-Participaciones.aspx?qS={2e0da3d2-af21-4f16-8dd2-31cdd5160df2}` → HTTP 200 · `text/html; charset=utf-8` · 234,667 caracteres · «CNMV - Notificaciones de derechos de voto e instrumentos financieros - TELEFONICA, S.A.»
- contenido: 'ContentPrincipal_titulo_wuc_Noscript1"> Número total de derechos de voto (incluidos los adicionales otorgados por acciones por lealtad): 5.670.161.554 De los cuales: - atribuibles a las acciones: 5.670.161.554 - adicionales otorgados por acciones por lealtad: 0 Fecha de última modificación del número de derechos de voto: 13/05/2024 Fecha de publicación en la pagina web CNMV: 13/05/2024 Accionistas Significativos % de derechos de voto atribuidos a las acciones % de derechos de voto a través de instrumentos financieros % de derechos de voto total Histórico de notificaciones Denominación % Total '
  - tabla 1 #ctl00_ContentPrincipal_gridAccionistasSignificativos: 9 filas; primeras: [[''], ['% de derechos de voto atribuidos a las acciones', '% de derechos de voto a través de instrumentos fin', '% de derechos de voto total', '', 'Histórico de notificaciones'], ['Denominación', '% Total (A)', '% Directo', '% Indirecto', '% (B)', '(A+B)', 'F.Registro Entrada CNMV', 'Información adicional', 'Detalle/anulaciones'], ['BLACKROCK INC.', '5,033', '0,000', '5,033', '1,208', '6,241', '23/06/2026', '', '']]
- guardado como `telefonica-notificaciones-participaciones-aspx.html`

`https://www.cnmv.es/portal/Consultas/derechosvoto/SociedadesParticipa.aspx?qS={2e0da3d2-af21-4f16-8dd2-31cdd5160df2}` → HTTP 200 · `text/html; charset=utf-8` · 213,784 caracteres · «CNMV - Sociedades cotizadas donde participa - TELEFONICA, S.A.»
- contenido: 'ContentPrincipal_Noscript1"> NoScript No tiene participaciones en ninguna sociedad cotizada ADVERTENCIA: La información se obtiene de las notificaciones de derechos de voto remitidas por cada sujeto obligado. En la medida en que un accionista significativo no presente una notificación, acogiéndose a lo establecido en el Real Decreto 1362/2007, de 19 de octubre, sobre información regulada, en el artículo 24.1a) relativo a acuerdos para el ejercicio concertado de los derechos de voto o en el 25.1 relativo a la notificación en caso de grupos, el nombre del titular de la participación significativ'

### Participaciones de prisa

- `ps_ac_ini` → HTTP 200; enlaces con qS: ['https://www.cnmv.es/portal/Consultas/derechosvoto/Notificaciones-Participaciones.aspx?qS={92e04394-8ab4-4c37-b862-5870635979c1}', 'https://www.cnmv.es/portal/Consultas/derechosvoto/SociedadesParticipa.aspx?qS={92e04394-8ab4-4c37-b862-5870635979c1}', 'https://www.cnmv.es/portal/Consultas/derechosvoto/Autocartera.aspx?qS={92e04394-8ab4-4c37-b862-5870635979c1}', 'https://www.cnmv.es/portal/HR/HSPactosParasociales.aspx?qS={92e04394-8ab4-4c37-b862-5870635979c1}']

`https://www.cnmv.es/portal/Consultas/derechosvoto/Notificaciones-Participaciones.aspx?qS={92e04394-8ab4-4c37-b862-5870635979c1}` → HTTP 200 · `text/html; charset=utf-8` · 248,131 caracteres · «CNMV - Notificaciones de derechos de voto e instrumentos financieros - PROMOTORA DE INFORM»
- contenido: 'ContentPrincipal_titulo_wuc_Noscript1"> Número total de derechos de voto (incluidos los adicionales otorgados por acciones por lealtad): 134.914.212 De los cuales: - atribuibles a las acciones: 134.914.212 - adicionales otorgados por acciones por lealtad: 0 Fecha de última modificación del número de derechos de voto: 02/07/2026 Fecha de publicación en la pagina web CNMV: 02/07/2026 Accionistas Significativos % de derechos de voto atribuidos a las acciones % de derechos de voto a través de instrumentos financieros % de derechos de voto total Histórico de notificaciones Denominación % Total (A) '
  - tabla 1 #ctl00_ContentPrincipal_gridAccionistasSignificativos: 14 filas; primeras: [[''], ['% de derechos de voto atribuidos a las acciones', '% de derechos de voto a través de instrumentos fin', '% de derechos de voto total', '', 'Histórico de notificaciones'], ['Denominación', '% Total (A)', '% Directo', '% Indirecto', '% (B)', '(A+B)', 'F.Registro Entrada CNMV', 'Información adicional', 'Detalle/anulaciones'], ['AL THANI , KHALID THANI ABDULLAH', '3,353', '3,353', '0,000', '0,000', '3,353', '19/12/2024', '', '']]
- guardado como `prisa-notificaciones-participaciones-aspx.html`

`https://www.cnmv.es/portal/Consultas/derechosvoto/SociedadesParticipa.aspx?qS={92e04394-8ab4-4c37-b862-5870635979c1}` → HTTP 200 · `text/html; charset=utf-8` · 213,896 caracteres · «CNMV - Sociedades cotizadas donde participa - PROMOTORA DE INFORMACIONES, S.A.»
- contenido: 'ContentPrincipal_Noscript1"> NoScript No tiene participaciones en ninguna sociedad cotizada ADVERTENCIA: La información se obtiene de las notificaciones de derechos de voto remitidas por cada sujeto obligado. En la medida en que un accionista significativo no presente una notificación, acogiéndose a lo establecido en el Real Decreto 1362/2007, de 19 de octubre, sobre información regulada, en el artículo 24.1a) relativo a acuerdos para el ejercicio concertado de los derechos de voto o en el 25.1 relativo a la notificación en caso de grupos, el nombre del titular de la participación significativ'

### Participaciones de santander

- `ps_ac_ini` → HTTP 200; enlaces con qS: ['https://www.cnmv.es/portal/Consultas/derechosvoto/Notificaciones-Participaciones.aspx?qS={0be368f4-a293-438e-8459-ecb9cba4aa25}', 'https://www.cnmv.es/portal/Consultas/derechosvoto/SociedadesParticipa.aspx?qS={0be368f4-a293-438e-8459-ecb9cba4aa25}', 'https://www.cnmv.es/portal/Consultas/derechosvoto/Autocartera.aspx?qS={0be368f4-a293-438e-8459-ecb9cba4aa25}', 'https://www.cnmv.es/portal/HR/HSPactosParasociales.aspx?qS={0be368f4-a293-438e-8459-ecb9cba4aa25}']

`https://www.cnmv.es/portal/Consultas/derechosvoto/Notificaciones-Participaciones.aspx?qS={0be368f4-a293-438e-8459-ecb9cba4aa25}` → HTTP 200 · `text/html; charset=utf-8` · 220,289 caracteres · «CNMV - Notificaciones de derechos de voto e instrumentos financieros - BANCO SANTANDER, S.»
- contenido: 'ContentPrincipal_titulo_wuc_Noscript1"> Número total de derechos de voto (incluidos los adicionales otorgados por acciones por lealtad): 14.556.482.801 De los cuales: - atribuibles a las acciones: 14.556.482.801 - adicionales otorgados por acciones por lealtad: 0 Fecha de última modificación del número de derechos de voto: 09/09/2026 Fecha de publicación en la pagina web CNMV: 09/09/2026 Accionistas Significativos % de derechos de voto atribuidos a las acciones % de derechos de voto a través de instrumentos financieros % de derechos de voto total Histórico de notificaciones Denominación % Tota'
  - tabla 1 #ctl00_ContentPrincipal_gridAccionistasSignificativos: 4 filas; primeras: [[''], ['% de derechos de voto atribuidos a las acciones', '% de derechos de voto a través de instrumentos fin', '% de derechos de voto total', '', 'Histórico de notificaciones'], ['Denominación', '% Total (A)', '% Directo', '% Indirecto', '% (B)', '(A+B)', 'F.Registro Entrada CNMV', 'Información adicional', 'Detalle/anulaciones'], ['BLACKROCK INC.', '6,851', '0,000', '6,851', '0,010', '6,861', '04/07/2025', '', '']]
- guardado como `santander-notificaciones-participaciones-aspx.html`

`https://www.cnmv.es/portal/Consultas/derechosvoto/SociedadesParticipa.aspx?qS={0be368f4-a293-438e-8459-ecb9cba4aa25}` → HTTP 200 · `text/html; charset=utf-8` · 217,198 caracteres · «CNMV - Sociedades cotizadas donde participa - BANCO SANTANDER, S.A.»
- contenido: 'ContentPrincipal_Noscript1"> NoScript Sociedad Participada % derechos de voto atribuidos a las acciones % derechos de voto a través de instrumentos financieros Total % F. Registro entrada CNMV PROMOTORA DE INFORMACIONES, S.A. 4,145 0,000 4,145 07/02/2017 GENERAL DE ALQUILER DE MAQUINARIA, S.A. 4,477 0,000 4,477 03/12/2019 MERLIN PROPERTIES, SOCIMI, S.A. 22,268 0,000 22,268 02/11/2016 COMPAÑIA ESPAÑOLA DE VIVIENDAS EN ALQUILER, S.A. 24,068 0,000 24,068 04/10/2018 METROVACESA, S.A. 49,362 0,000 49,362 04/10/2018 ADVERTENCIA: La información se obtiene de las notificaciones de derechos de voto rem'
  - tabla 1 #ctl00_ContentPrincipal_gridSociedades: 6 filas; primeras: [['Sociedad Participada', '% derechos de voto atribuidos a las acciones', '% derechos de voto a través de instrumentos financ', 'Total %', 'F. Registro entrada CNMV'], ['PROMOTORA DE INFORMACIONES, S.A.', '4,145', '0,000', '4,145', '07/02/2017'], ['GENERAL DE ALQUILER DE MAQUINARIA, S.A.', '4,477', '0,000', '4,477', '03/12/2019'], ['MERLIN PROPERTIES, SOCIMI, S.A.', '22,268', '0,000', '22,268', '02/11/2016']]
- guardado como `santander-sociedadesparticipa-aspx.html`

### IAGC de telefonica

- página → HTTP 200; documentos: 15
- el más reciente → HTTP 200 · `application/pdf` · 4,008,466 bytes · PDF: True
- páginas: 167
- páginas que citan C.1.2: [87, 94, 117, 118, 126, 135, 136]
  - página 87, tabla 1: 1 filas; cabecera: ['', '', '', '', '', '', '4', '', '', '', '']
  - página 87, tabla 2: 15 filas; cabecera: ['—', 'Ejecutivo', 'Presidente', '18/01/2025', '10/04/2025']
  - página 94, tabla 1: 1 filas; cabecera: ['', '', '', '', '', '', '4', '', '', '', '']
  - página 94, tabla 2: 4 filas; cabecera: ['C.1.21 Explique si existen requisitos específicos,']
  - página 94, tabla 3: 4 filas; cabecera: ['C.1.26 Indique el número de reuniones que ha']
  - página 94, tabla 4: 2 filas; cabecera: ['17']
  - página 94, tabla 5: 7 filas; cabecera: ['C.1.25 Indique el número de reuniones que ha']
  - página 94, tabla 6: 1 filas; cabecera: ['Número de reuniones', '0']
  - página 117, tabla 1: 1 filas; cabecera: ['', '', '', '', '', '4', '', '', '', '']
  - página 117, tabla 2: 6 filas; cabecera: ['titularidad de miembros del Consejo de Administració']
  - página 117, tabla 3: 8 filas; cabecera: ['por motivos profesionales y personales,']
  - página 117, tabla 4: 9 filas; cabecera: ['Finalmente, D. Francisco Javier de Paz Mancho presentó']
  - página 117, tabla 5: 3 filas; cabecera: ['Bilbao Vizcaya Argentaria, S.A. (5,01%), representado e']
  - página 117, tabla 6: 4 filas; cabecera: ['dimisiones de miembros del Consejo de Administració']
  - página 117, tabla 7: 5 filas; cabecera: ['acordar el Consejo de Administración, previo informe']
  - página 117, tabla 8: 3 filas; cabecera: ['nueva etapa en la presidencia ejecutiva de la Socieda']
  - página 117, tabla 9: 5 filas; cabecera: ['Riberas Mera presentó su renuncia voluntaria al cargo']
  - página 117, tabla 10: 10 filas; cabecera: ['Administración, previo informe favorable de la Comisió']
  - página 117, tabla 11: 6 filas; cabecera: ['D. Peter Löscher es Miembro Emérito del Consejo', '', '']
  - página 118, tabla 1: 1 filas; cabecera: ['', '', '', '', '', '', '4', '', '', '', '']
  - página 118, tabla 2: 3 filas; cabecera: ['de cinco Consejos de Administración de otras']
  - página 118, tabla 3: 8 filas; cabecera: ['A estos efectos, a) se computarán como un solo Consej']
  - página 118, tabla 4: 3 filas; cabecera: ['Excepcionalmente, y por razones debidamente']
  - página 118, tabla 5: 2 filas; cabecera: ['-Nota 8 al Apartado C.1.21 del anexo estadístico de']
  - página 118, tabla 6: 9 filas; cabecera: ['De conformidad con lo establecido en el artículo 31.4 de']
  - página 118, tabla 7: 2 filas; cabecera: ['- Nota 6 al Apartado C.1.12 del anexo estadístico']
  - página 118, tabla 8: 9 filas; cabecera: ['De conformidad con lo establecido en el artículo 27.2 del']
  - página 118, tabla 9: 2 filas; cabecera: ['Se indica N/A en los supuestos en los que no se ha']
  - página 118, tabla 10: 6 filas; cabecera: ['El importe de las operaciones se ha determinado']
  - página 118, tabla 11: 2 filas; cabecera: ['conforme a los criterios establecidos por CNMV a los']
- filas del consejo reconocidas: 0

### IAGC de prisa

- página → HTTP 200; documentos: 15
- el más reciente → HTTP 200 · `application/pdf` · 4,334,018 bytes · PDF: True
- páginas: 191
- páginas que citan C.1.2: [15, 37, 38, 39, 40, 101, 123, 124, 125, 126]
  - página 15, tabla 1: 3 filas; cabecera: ['Número máximo de consejeros', '15']
  - página 15, tabla 2: 7 filas; cabecera: ['Nombre o denominación social del consejero', 'Representante', 'Categoría del consejero', 'Cargo en el consejo', 'Fecha primer nombramiento', 'Fecha último nombramiento', 'Procedimiento de elección']
    - columnas reconocidas: {'nombre': 0, 'representante': 1, 'categoria': 2, 'cargo': 3, 'primer_nombramiento': 4, 'ultimo_nombramiento': 5}
  - página 38, tabla 1: 2 filas; cabecera: ['Número de reuniones del consejo', '16']
  - página 38, tabla 2: 1 filas; cabecera: ['Número de reuniones', '1']
  - página 38, tabla 3: 4 filas; cabecera: ['Número de reuniones de Comisión de Auditoría, Riesgos y Cumplimiento', '8']
  - página 39, tabla 1: 4 filas; cabecera: ['Número de reuniones con la asistencia presencial de al menos el 80% de los consejeros', '16']
  - página 39, tabla 2: 4 filas; cabecera: ['Nombre', 'Cargo']
    - columnas reconocidas: {'nombre': 0, 'cargo': 1}
- filas del consejo reconocidas: 9
- guardado como `prisa-iagc-consejo.json` (sin fecha de nacimiento; el PDF no se guarda)

### iberdrola (A48010615), con sesión nueva

- portada → HTTP 200; cookies: ['IdiomaCNMV_']
- `DatosEntidad.aspx?nif=A48010615` → HTTP 200 · «CNMV - Información de la Entidad» · 'ContentPrincipal_wuc_SinDatos_divAviso" class="msgAviso"> No se han encontrado datos disponibles <'
- `DatosEntidad.aspx?nif=A48010615&lang=es` → HTTP 200 · «CNMV - Información de la Entidad» · 'ContentPrincipal_wuc_SinDatos_divAviso" class="msgAviso"> No se han encontrado datos disponibles <'
- `ee/datosgenerales.aspx?nif=A48010615` → HTTP 200 · «CNMV - Datos generales» · 'ContentPrincipal_lblSubtitulo"> No se han encontrado datos disponibles <'

### acs (A28004885), con sesión nueva

- portada → HTTP 200; cookies: ['IdiomaCNMV_']
- `DatosEntidad.aspx?nif=A28004885` → HTTP 200 · «CNMV - Información de la Entidad» · 'ContentPrincipal_wuc_SinDatos_divAviso" class="msgAviso"> No se han encontrado datos disponibles <'
- `DatosEntidad.aspx?nif=A28004885&lang=es` → HTTP 200 · «CNMV - Información de la Entidad» · 'ContentPrincipal_wuc_SinDatos_divAviso" class="msgAviso"> No se han encontrado datos disponibles <'
- `ee/datosgenerales.aspx?nif=A28004885` → HTTP 200 · «CNMV - Datos generales» · 'ContentPrincipal_lblSubtitulo"> No se han encontrado datos disponibles <'

### atresmedia (A78839271), con sesión nueva

- portada → HTTP 200; cookies: ['IdiomaCNMV_']
- `DatosEntidad.aspx?nif=A78839271` → HTTP 200 · «CNMV - Información de la Entidad» · 'ContentPrincipal_wuc_SinDatos_divAviso" class="msgAviso"> No se han encontrado datos disponibles <'
- `DatosEntidad.aspx?nif=A78839271&lang=es` → HTTP 200 · «CNMV - Información de la Entidad» · 'ContentPrincipal_wuc_SinDatos_divAviso" class="msgAviso"> No se han encontrado datos disponibles <'
- `ee/datosgenerales.aspx?nif=A78839271` → HTTP 200 · «CNMV - Datos generales» · 'ContentPrincipal_lblSubtitulo"> No se han encontrado datos disponibles <'

### indra (A28599033), con sesión nueva

- portada → HTTP 200; cookies: ['IdiomaCNMV_']
- `DatosEntidad.aspx?nif=A28599033` → HTTP 200 · «CNMV - Información de la Entidad» · 'ContentPrincipal_wuc_SinDatos_divAviso" class="msgAviso"> No se han encontrado datos disponibles <'
- `DatosEntidad.aspx?nif=A28599033&lang=es` → HTTP 200 · «CNMV - Información de la Entidad» · 'ContentPrincipal_wuc_SinDatos_divAviso" class="msgAviso"> No se han encontrado datos disponibles <'
- `ee/datosgenerales.aspx?nif=A28599033` → HTTP 200 · «CNMV - Datos generales» · 'ContentPrincipal_lblSubtitulo"> No se han encontrado datos disponibles <'

### redeia (A78003662), con sesión nueva

- portada → HTTP 200; cookies: ['IdiomaCNMV_']
- `DatosEntidad.aspx?nif=A78003662` → HTTP 200 · «CNMV - Información de la Entidad» · 'ContentPrincipal_wuc_SinDatos_divAviso" class="msgAviso"> No se han encontrado datos disponibles <'
- `DatosEntidad.aspx?nif=A78003662&lang=es` → HTTP 200 · «CNMV - Información de la Entidad» · 'ContentPrincipal_wuc_SinDatos_divAviso" class="msgAviso"> No se han encontrado datos disponibles <'
- `ee/datosgenerales.aspx?nif=A78003662` → HTTP 200 · «CNMV - Datos generales» · 'ContentPrincipal_lblSubtitulo"> No se han encontrado datos disponibles <'


---

## Segunda vuelta: CNMV (consejos y participaciones de cotizadas)

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










