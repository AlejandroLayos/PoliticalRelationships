# Reconocimiento: CNMV (consejos y participaciones de cotizadas)

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







