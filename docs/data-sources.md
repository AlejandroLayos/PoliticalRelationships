# Fuentes de datos

Cada fuente documenta: qué aporta, cómo se accede, sus límites reales y su base
legal. Antes de escribir un conector, se lee y se actualiza esta ficha.

Regla general: **si una fuente cambia de formato o devuelve error, se registra
el problema, se tolera el hueco y se sigue.** Nunca se rellena con datos
inventados.

---

## 1. BDNS — Base de Datos Nacional de Subvenciones

**Aporta:** subvenciones y ayudas públicas de toda España (AGE, comunidades
autónomas, entidades locales, universidades públicas). Convocatorias,
concesiones y beneficiarios. Es la fuente más accesible y la que valida el
pipeline entero.

**Organismo:** IGAE, Ministerio de Hacienda.

**Acceso:** API REST que devuelve JSON. Sin registro ni clave.

- Portal: <https://www.infosubvenciones.es/bdnstrans/GE/es/index>
- Documentación Swagger: <https://www.infosubvenciones.es/bdnstrans/doc/swagger>
- Base de la API: `https://www.infosubvenciones.es/bdnstrans/api/`

**Endpoint que usamos** — concesiones, no convocatorias. La *convocatoria* es
la llamada a solicitudes; la *concesión* es el dinero efectivamente otorgado, y
es lo que produce una arista.

```
GET /bdnstrans/api/concesiones/busqueda
    ?fechaDesde=01/01/2025&fechaHasta=31/01/2025&pageSize=1000&page=0
```

Las fechas van en `dd/mm/aaaa`. La respuesta es una página estilo Spring:

```json
{ "content": [ ... ], "totalPages": 12, "number": 0, "totalElements": 11543 }
```

**Campos de cada concesión**: `codConcesion`, `numeroConvocatoria`,
`convocatoria`, `nivel1`, `nivel2`, `nivel3`, `instrumento`, `urlBR`,
`fechaConcesion`, `beneficiario`, `importe`, `ayudaEquivalente`,
`tieneProyecto`.

⚠️ **`nifCif` NO existe en la respuesta.** Sólo es un parámetro de búsqueda. El
NIF viene **concatenado dentro de `beneficiario`**:

```
"A10984433 BRITISH ROBERTSON, S.A."
"***9282** DARIO SANCHEZ ESTORNELL"
```

Lo aprendimos ejecutando contra la API real: dedujimos `nifCif` del enumerado
de campos ordenables y era una suposición equivocada, así que durante la
primera ingesta el 79 % de las aristas salió sin identificador fiscal.

**Y los NIF de personas físicas llegan enmascarados** con asteriscos, mientras
que los de personas jurídicas llegan completos. Ese enmascarado es la propia
fuente señalando que el beneficiario es un particular, y lo tratamos como tal:
ver la nota de minimización más abajo.

`nivel1..3` es la jerarquía administrativa del órgano concedente; usamos el
nivel más específico que venga relleno como nombre del organismo, y la
jerarquía entera se guarda en `jerarquia_bdns` para saber de qué
administración es (fase 7, `ingest/sinapsis_ingest/territorio.py`).

⚠️ La forma real de esos tres niveles **no está verificada** —la muestra de
los tests es sintética—. Si no es la que espera `territorio.py`, esos
organismos salen «sin clasificar» y sus jerarquías aparecen en
`docs/fuentes/estado-ingesta.md`, que es de donde hay que sacar las reglas.

**Límites reales:**

- `pageSize` máximo **10.000**. Usamos 1.000: páginas mayores producen
  documentos crudos enormes y difíciles de reprocesar.
- **10 peticiones GET por segundo y por IP.** Vamos a 4/s a propósito: es un
  servicio público y no hay prisa.
- Para rangos grandes conviene trocear por fechas además de por página.

### 1.1 Subvenciones a partidos políticos

Conector `bdns-partidos`, endpoint `/partidospoliticos/busqueda`. Misma forma
de petición y respuesta que las concesiones generales.

Lo que aporta sobre el conjunto general es una afirmación que el otro no hace:
**el beneficiario es un partido político**. Por eso la entidad destino va como
`Organization` con `properties.partido_politico = true`, en vez de deducir
`Company`/`Person` a partir del NIF.

Comparte `source_id` (`bdns`) y clave de arista (`bdns:concesion:<cod>`) con el
conector general **a propósito**: es un subconjunto del mismo universo de
concesiones, y si una concesión aparece en los dos conjuntos tiene que quedar
como una sola arista. Duplicarla inflaría el dinero contabilizado. Hay un test
de integración (`test_ingerir_los_dos_conjuntos_no_duplica_aristas`) que ingiere
ambos conjuntos y comprueba que ni el número de aristas ni la suma de importes
crecen.

**Otros endpoints con valor para el proyecto**, todavía sin conector:
`/grandesbeneficiarios/busqueda`, `/sanciones/busqueda`,
`/ayudasestado/busqueda` y `/minimis/busqueda`.

**Referencia de implementación:** [`bdns-fetch`](https://github.com/cruzlorite/bdns-fetch)
(Python, GPLv3) implementa las rutas oficiales. Se usa como **referencia de
endpoints y parámetros**, no como dependencia — su licencia GPLv3 es compatible
con nuestra AGPL-3.0, pero portamos la lógica.

**Mapeo a FollowTheMoney:**

```
organismo concedente (PublicBody) --Payment--> beneficiario (Company | Person)
```

Con `amount`, `currency = 'EUR'`, `start_date` = `fechaConcesion` y
`dedupe_key = bdns:concesion:<codConcesion>`.

El tipo del beneficiario se decide por el NIF: los que empiezan por dígito o
por K, L, M, X, Y, Z son personas físicas (`Person`); el resto, `Company`. Sin
NIF no se afirma el tipo — va como `LegalEntity` y la arista baja a
`confidence = 0.7`, porque sin identificador fiscal no podemos garantizar de
quién hablamos.

**Estado de verificación:** ⚠️ el conector **no está probado contra una
respuesta real de la API**. Los golden tests existen pero se saltan hasta que
alguien capture la muestra con `scripts/capturar_muestra_bdns.py` desde una
máquina con salida a internet. Ver `ingest/tests/golden/README.md`.

**Base legal:** información de publicidad activa obligatoria (Ley 38/2003 General
de Subvenciones, art. 20).

**Minimización de datos personales.** BDNS enmascara el NIF de los particulares
pero **publica su nombre completo**. Republicar ese nombre dentro de un mapa de
influencia política sería una exposición desproporcionada: la fuente es pública,
pero el uso no es el mismo, y la propia BDNS ya señala con el enmascarado que
considera a ese beneficiario un particular.

Por eso el conector **no persiste el nombre** de las personas físicas sin NIF
visible. Conserva el hecho —qué organismo pagó cuánto y por qué convocatoria— y
sustituye la identidad por un nodo agregado por convocatoria. El dinero público
sigue trazado; el vecino que cobró una ayuda agraria no aparece con nombre y
apellidos. Ver [spec §12](spec.md).

**Retención:** se captura y conserva el crudo. La BDNS despublica registros
pasado su plazo legal, así que el crudo es la única prueba duradera.

---

## 2. PLACSP — Plataforma de Contratación del Sector Público

**Aporta:** licitaciones, adjudicaciones y contratos menores. **Es donde está
el dinero de verdad.**

**Organismo:** Dirección General del Patrimonio del Estado, Ministerio de
Hacienda.

**Acceso:** **no hay API REST.** Esto es importante y contradice la intuición.
Se publica por sindicación ATOM y descarga masiva:

- Portal de datos abiertos: <https://contrataciondelestado.es/datosabiertos/>
- Especificación de sindicación:
  <https://contrataciondelsectorpublico.gob.es/datosabiertos/especificacion-sindicacion.pdf>

**Formato:** ZIPs mensuales con ficheros `.atom`, máximo 500 entradas cada uno,
encadenados por `link rel="next"`. El contenido sigue **CODICE 2.07**, basado en
UBL (OASIS).

Hay cinco *feeds* nacionales: licitaciones, contratos menores, plataformas
agregadas, encargos a medios propios y consultas preliminares de mercado.

**De esos, la ingesta lee tres** (`ingest/sinapsis_ingest/connectors/placsp.py`,
constante `FEEDS`), cada uno como un conector aparte que comparte `source_id`:

| conector | feed | qué trae |
|---|---|---|
| `placsp` | `PlataformasAgregadasSinMenores` | lo que vuelcan las plataformas autonómicas agregadas |
| `placsp-licitaciones` | `licitacionesPerfilesContratanteCompleto3` | lo publicado directamente en la Plataforma del Estado |
| `placsp-menores` | `contratosMenoresPerfilesContratantes` | contrato menor — **la ruta no sirve** (ver abajo) |

Hasta el 18/9/2026 sólo se leía el primero. Las URL de los otros dos llevaban
en la misma constante desde el principio, sin que nada dijera que no se
usaban, así que todo lo publicado directamente en la Plataforma y todo el
contrato menor estaban fuera del mapa.

El **contrato menor** merece mención aparte: por debajo del umbral no hay
licitación pública, así que es a la vez el tramo que menos se mira y donde
vive el gasto municipal del día a día. También es donde más adjudicatarios son
personas físicas —autónomos—, y por eso pasa por dos cierres: el conector los
agrega en un nodo anónimo y el volcado no deja salir un `Person` aunque el
conector fallara. Ver [spec §12](spec.md).

Los que faltan —encargos a medios propios y consultas preliminares— son los
dos que menos dinero mueven y los que peor encajan en el modelo de
adjudicación; quedan pendientes.

**La ruta del feed de contratos menores ya no sirve.** Comprobado el
18/9/2026: `sindicacion_643/contratosMenoresPerfilesContratantes.atom`
responde **200 con una página HTML** de redirección al portal
(«Redireccionando… Se ha producido un error»), 521 bytes. No lo caza
`raise_for_status` —el código es 200— ni el parser, que sólo decía «mismatched
tag: line 1, column 200».

El conector lo diagnostica ahora explícitamente: una página HTML donde tenía
que haber un Atom se dice como tal en el log.

**La ruta buena es `sindicacion_1143`.** Reconocimiento del 25/9/2026
(`docs/fuentes/placsp-reconocimiento.md`, `scripts/explorar_placsp.py`):
`sindicacion_1143/contratosMenoresPerfilesContratantes.atom` sirve
`application/atom+xml`, actualizado a diario, con su enlace a la página
siguiente; la 643 sigue devolviendo la redirección. La página de datos
abiertos de Hacienda ya enlaza los feeds desde el dominio nuevo,
`contrataciondelsectorpublico.gob.es`; el viejo responde igual por ahora.

**Coste real:** bastante mayor que BDNS. Hay que descargar ZIPs, descomprimir,
recorrer la cadena de ATOM y parsear XML UBL. Es trabajo de fase 3, no de
arranque.

**Rutas CODICE verificadas contra una respuesta real** (namespaces
`urn:dgpe:names:draft:codice…`, estables entre versiones):

| Dato | Ruta dentro de `cac-place-ext:ContractFolderStatus` |
|---|---|
| Expediente | `cbc:ContractFolderID` |
| Estado | `cbc-place-ext:ContractFolderStatusCode` |
| Órgano | `cac-place-ext:LocatedContractingParty/cac:Party/cac:PartyName/cbc:Name` |
| Presupuesto | `cac:ProcurementProject/cac:BudgetAmount/cbc:TaxExclusiveAmount` |
| CPV | `cac:ProcurementProject/cac:RequiredCommodityClassification/cbc:ItemClassificationCode` |
| NUTS | `cac:ProcurementProject/cac:RealizedLocation/cbc:CountrySubentityCode` |
| Adjudicatario | `cac:TenderResult/cac:WinningParty/cac:PartyName/cbc:Name` |
| NIF adjudicatario | `cac:TenderResult/cac:WinningParty/cac:PartyIdentification/cbc:ID` |
| Importe adjudicado | `cac:TenderResult/cac:AwardedTenderedProject/cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount` |
| Resultado | `cac:TenderResult/cbc:ResultCode` |

El resultado se publica **en crudo, sin traducir**, en la propiedad
`resultCode` de la arista. Es un código de la lista CODICE
`TenderResultCode-2.02`, cuya URI viene en el propio elemento
(`listURI="http://contrataciondelestado.es/codice/cl/2.02/TenderResultCode-2.02.gc"`).
En la instantánea del 18/9/2026 sólo aparecen dos valores, `8` y `9`.

No se traducen a palabras porque no se ha podido comprobar la lista contra la
especificación: el entorno de desarrollo no alcanza `contrataciondelestado.es`
(ver «Estado de verificación» más abajo). Poner «adjudicado» o «formalizado»
de memoria sería inventarse el significado de un dato público.

**Tres trampas que muerden:**

1. **`ContractFolderID` no es único.** Es el número de expediente interno del
   órgano ("C. 2-2021"); dos ayuntamientos pueden tener el mismo. La clave
   estable es el `<id>` del entry ATOM, que sí es una URI global.
2. **Un contrato puede tener varios `cac:WinningParty`** — lotes o UTEs.
   Quedarse con el primero pierde adjudicatarios y, con ellos, dinero.
3. **Los `href` de `rel="next"` son relativos** al fichero que los contiene, y
   apuntan hacia atrás en el tiempo, no hacia adelante.

**Mapeo a FollowTheMoney:**

```
Contract (el expediente) --ContractAward--> adjudicatario (Company | Person)
```

El órgano de contratación va como entidad `PublicBody` y se enlaza al contrato
mediante la propiedad `authority`, **no con una arista**: en FollowTheMoney no
existe esquema de arista órgano→contrato, la autoridad es una propiedad del
contrato. La proyección a Neo4j (fase 4) es donde esa propiedad se materializa
como enlace navegable.

**Base legal:** publicidad obligatoria (Ley 9/2017 de Contratos del Sector
Público).

**Estado de verificación:** las rutas CODICE están verificadas contra una
respuesta real, pero **espejada de terceros**, no capturada por nosotros (el
entorno de desarrollo no alcanza `contrataciondelestado.es`). Ver
`ingest/tests/golden/README.md`. Falta además el camino de **descarga de los
ZIP mensuales**: el conector actual sigue el encadenado ATOM en vivo, que sirve
para lo reciente pero no para cargar el histórico.

---

## 2.bis BOE — nombramientos y ceses de altos cargos

**Aporta:** quién ocupó qué alto cargo de la Administración General del Estado
y cuándo: ministros, secretarios de Estado, subsecretarios, secretarios
generales, directores generales, delegados del Gobierno, embajadores y quien
preside o dirige un organismo o empresa pública. Es la primera pieza de las
puertas giratorias (spec §15, fase 7).

**Acceso:** API de datos abiertos del BOE, sin registro.

- Sumario diario: `https://www.boe.es/datosabiertos/api/boe/sumario/AAAAMMDD`
  (JSON). Llega al menos a 2011; los días sin BOE devuelven 404.
- Cada disposición: `https://www.boe.es/diario_boe/xml.php?id=BOE-A-…` (XML con
  `metadatos`, `analisis` y `texto`).
- Forma verificada con muestras reales: `docs/fuentes/boe-reconocimiento.md` y
  `ingest/tests/golden/boe_*`.

**Qué se lee.** De la sección II.A, los Reales Decretos cuyo título sigue la
fórmula «por el que se nombra X a don/doña Y» o «por el que se dispone el cese
de don/doña Y como X». Lo que no sigue la fórmula no se interpreta (ver
`ingest/sinapsis_ingest/cargos.py`). Sólo se descarga y se guarda lo que es
alto cargo según la Ley 3/2015: fiscales, jueces y militares también se
nombran por Real Decreto, pero son carreras y no llegan a la base.

**Base legal (spec §12).** Los nombramientos se publican en el BOE por
mandato legal para general conocimiento. Tratar el nombre de un alto cargo en
relación con su cargo es tratamiento de datos de quien ejerce funciones
públicas, con base en el interés público (art. 6.1.e RGPD) y en la Ley
19/2013 de transparencia, que obliga a publicar la información sobre altos
cargos. Se publica sólo el nombre, el cargo, las fechas y el Real Decreto: ni
el tratamiento (don/doña), ni la firma, ni nada del cuerpo de la disposición.

Los Reales Decretos que forman o disuelven un gobierno («por el que se
nombran Ministros del Gobierno», «por el que se declara el cese de los miembros
del Gobierno») llevan los nombres en el cuerpo, un párrafo por persona, y se
leen de ahí. Un párrafo con dos cargos («Vicepresidenta del Gobierno y Ministra
de la Presidencia…») son dos actos.

**Límites conocidos:**

- Una persona se identifica por su nombre: el BOE no publica ningún
  identificador en un nombramiento. Dos homónimos exactos se juntarían.
- Y al revés: el BOE no siempre escribe igual a la misma persona —«Margarita
  Robles Fernández» en 2018, «María Margarita Robles Fernández» en 2023—, y
  entonces salen dos fichas. Es un hueco, no una atribución falsa, y no se
  junta a mano sin una fuente que lo diga.
- Sólo el Estado. Los gobiernos autonómicos publican en sus boletines.

**Mapeo a FollowTheMoney:**

```
persona (Person) --Occupancy--> puesto (Position) --UnknownLink--> departamento (PublicBody)
```

Una `Occupancy` por disposición: el nombramiento lleva `start_date`, el cese
`end_date`, y el volcado los junta en periodos (`exportar_cargos.py`).

### Altas instancias judiciales y fiscales (desde el 26/9/2026)

La ampliación de §12 añade, por su nombramiento en el BOE, el Tribunal
Supremo (magistrados y presidencias de Sala), el Tribunal Constitucional, el
Consejo General del Poder Judicial, la Audiencia Nacional, las presidencias de
los TSJ, el Fiscal General del Estado y los fiscales de sala. La carrera
ordinaria —juzgados, audiencias provinciales, fiscalías provinciales— sigue
fuera. Es otra lista cerrada (`es_alta_instancia` en `cargos.py`), aparte de
la de altos cargos, que no se abre.

Se leen con el mismo conector: la caché de sumarios guarda todos los Reales
Decretos de la II.A, no sólo los que pasaban el filtro, así que el histórico
ya leído se completa sin volver a pedir ni un sumario. El reconocimiento
(`docs/fuentes/justicia-boe-reconocimiento.md`) encontró tres fórmulas
propias de la carrera judicial, que sólo se aceptan para un cargo de la lista:

- «se promueve a la categoría de Magistrado de la Sala Quinta del Tribunal
  Supremo a don …»;
- «se nombra en propiedad a don …, Magistrado de la Sala Segunda …»;
- «se nombra Presidente de la Sala Segunda del Tribunal Supremo don …», sin
  la «a».

Dos diferencias con un alto cargo:

- **La institución sale del cargo**, no del departamento: quien publica es
  el CGPJ o la Jefatura del Estado, y «Magistrado del Supremo · Consejo
  General del Poder Judicial» diría que es vocal del Consejo.
- **No se les pone Gobierno.** Los propone el CGPJ, las Cortes o el propio
  Tribunal. El cuerpo del Real Decreto lo dice —«y a propuesta del Senado,
  Vengo en nombrar…»— y se guarda (`propuestaDe`), de una lista cerrada y
  sólo si nombra a uno. Cuando es «a propuesta del Gobierno», el volcado sí
  dice de qué Gobierno. El Fiscal General lo propone siempre el Gobierno y ya
  era alto cargo: conserva su Gobierno.

---

## 2.ter Oficina de Conflictos de Intereses — actividad privada tras el cese

**Aporta:** las autorizaciones a ex altos cargos para trabajar en el sector
privado en los dos años siguientes a su cese (Ley 3/2015, art. 15). Es la
fuente que **afirma** una puerta giratoria: «X, ex ministra de Empleo, autorizada
a ser consejera de Y» lo dice un documento oficial, no una coincidencia de
nombres.

**Acceso:** Portal de Transparencia, sin registro. La portada de «Actividad
privada tras el cese» no trae la lista en el HTML; la sirve el buscador del
portal (`servicios-buscador/buscar.htm?categoria=autorizaciones_ind`), que
exporta la búsqueda entera a una hoja de cálculo —un ZIP con un XLSX dentro—
mientras sean menos de 2000 resultados. El 25/9/2026 eran 644, de 2017 a 2026.
Forma verificada en `docs/fuentes/oci-reconocimiento.md` y
`ingest/tests/golden/oci/`.

Columnas: Nombre («APELLIDOS, NOMBRE»), Alto cargo, Ministerio, Fecha de cese,
Empresa / Actividad autorizada, Fecha de autorización (`dd/mm/aaaa`; las
páginas antiguas de seguimiento usan `aaaa/mm/dd`, y se leen las dos).

**Base legal (spec §12).** Publicidad activa obligatoria (Ley 19/2013) sobre
quien ha ejercido un alto cargo, en relación con ese cargo. Se publica lo que
publica la fuente —nombre, cargo, fechas y el texto de la autorización— y nada
más. **Una autorización no dice que la persona llegara a ocupar el puesto**, y
la web lo advierte en cada una.

**Cruces:**

- Con el BOE, la misma persona sólo si coinciden el nombre entero y la fecha de
  cese (diez días de margen). Con el nombre solo, dos fichas.
- Con el mapa del dinero, la sociedad sólo si el texto de la autorización la
  nombra por su denominación completa, con forma societaria: la denominación
  social es única en España. «LOGISTA» a secas no se cruza.

**Mapeo a FollowTheMoney:**

```
ex alto cargo (Person) --Occupancy--> puesto (Position)          hasta el cese
ex alto cargo (Person) --UnknownLink--> texto de la autorización (Organization)
```

---


**Si no responde.** El 26/9/2026 el buscador no contestó en un minuto y, como la
base de la ingesta empieza vacía cada noche, la web se quedó un día sin
ninguna autorización. Ahora el conector reintenta dos veces con esperas, y si
aun así no hay respuesta publica la **última exportación descargada**, con
su fecha de descarga (caché de Actions, `/tmp/copia-oci`), y el estado de la
ingesta dice que la fuente no respondió. Sin copia, no se publica nada: no se
inventa.

## 2.quater Congreso de los Diputados — diputados por legislatura

**Aporta:** quién fue diputado en cada legislatura, por qué circunscripción,
con qué formación electoral y en qué grupo parlamentario, con fechas de alta y
baja. Es lo que da el partido —de qué formación era un ministro que fue
diputado— y, con eso, el contexto de gobierno (spec §15, fase 7, línea 4).

**Acceso:** datos abiertos del Congreso, sin registro. Un JSON por legislatura
(`odsDiputadosNN__<marca>.json`; la marca cambia a diario, así que los enlaces
se leen de <https://www.congreso.es/es/opendata/diputados>), y la legislatura
en curso en los ficheros de diputados activos y de baja. Forma verificada en
`docs/fuentes/congreso-reconocimiento.md` y `ingest/tests/golden/congreso/`.
Se leen desde la IX legislatura (2008).

**Base legal (spec §12).** Publicidad de la composición de la Cámara. Se usa
sólo en su papel de diputado.

**Minimización.** Los ficheros traen la biografía de cada diputado. No se
guarda ni se publica: de ella sólo se extraen los cargos públicos que menciona
(«Ministro de Fomento (2018-2020)»), que sirven de segunda señal para unir al
diputado con un alto cargo del BOE.

**Declaraciones de actividades.** Cada diputado declara al tomar posesión sus
actividades de los años anteriores y las que mantiene (art. 18 del Código de
Conducta de las Cortes Generales); el Congreso las publica en
`docacteco__<marca>.json`, sólo de la legislatura en curso, una fila por cosa
declarada. Se guardan **sólo las filas de ACTIVIDAD** —empleador, sector,
periodo y descripción, con las palabras del diputado—. Las donaciones, las
aportaciones a fundaciones y las observaciones no se guardan. Con la muestra
del 25/9/2026: 1.224 actividades de 403 diputados, y los 403 se unen por
nombre a su escaño de la XV.

**Cruce con el BOE.** Sólo si coinciden el nombre entero y, además, la
biografía del Congreso menciona uno de sus cargos del BOE.

**Qué se publica.** Un diputado sale en la sección de cargos si se une a un
alto cargo o si hizo declaración de actividades. De quien sólo consta el
escaño no hay nada que cruzar, y la sección no es un censo de la Cámara.

**Cruce con el mapa del dinero.** El empleador declarado se enlaza con una
sociedad del mapa con la misma regla que las autorizaciones de la OCI: la
denominación completa, con su forma societaria, entera y sin dudas
(`exportar_cargos.empresa_en`). Con el índice del 25/9/2026, 9 actividades
de 1.217; en la portada sólo salen las que nombran una sociedad mercantil
(3), y en la ficha de la persona y en el panel de la entidad, todas.

**Mapeo a FollowTheMoney:**

```
diputado (Person) --Occupancy--> escaño de la legislatura (Position)   alta → baja
diputado (Person) --UnknownLink{relacion: actividad_declarada}--> lo que declaró (Organization, texto tal cual)
```

El destino de la actividad es el texto que escribió el diputado, no una
entidad del mapa: no entra en el grafo ni en el índice, igual que la
«actividad» de una autorización de la OCI.

---

## 2.sexies Senado — los partidos y sus siglas

**Aporta:** el puente entre unas siglas y un partido. El Congreso dice que un
diputado fue elegido por «PSOE»; el mapa del dinero tiene a «PARTIDO
SOCIALISTA OBRERO ESPAÑOL» cobrando subvenciones. Unirlos con una tabla hecha
a mano sería una inferencia nuestra. El Senado publica, para cada
legislatura, los partidos de cada grupo con sus siglas y su nombre oficial:
es la fuente de esa equivalencia.

**Acceso:** datos abiertos del Senado, sin registro.
`ficopendataservlet?tipoFich=4&legis=N` (grupos y partidos de la legislatura
N), desde la IX. Forma verificada en `docs/fuentes/senado-reconocimiento.md`
y `ingest/tests/golden/senado/`.

**Cómo se usa.** Siglas del Congreso → nombre oficial del Senado → partido
del mapa con ese nombre exacto. Unas siglas con dos nombres distintos en
distintas legislaturas no se usan; un nombre con dos fichas en el mapa,
tampoco. Los partidos del Senado no entran en el grafo: el que cobra ya está,
con su NIF.

**Lo que no se lee.** Las fichas de cada senador (con estado civil, hijos y
fecha de nacimiento) no se piden. La composición desde 1977 está reconocida
(`composicion-desde-1977.xml`, 2.505 registros); ojo, sus campos de grupo
vienen corridos —`grupoCod` trae la procedencia—, y no lleva el partido.

**Mapeo a FollowTheMoney:**

```
partido (Organization) --UnknownLink{relacion: partido_en_grupo, legislatura}--> grupo parlamentario (Organization)
```

---

## 2.septies CNMV — accionistas significativos de las cotizadas

**Aporta:** quién tiene más del 3 % de los derechos de voto de cada cotizada,
y en qué otras cotizadas participa ella: la red de propiedad entre las grandes
empresas, sus fondos y sus accionistas de referencia. Es la mitad empresarial
de la red de poder (spec §12, ampliación del 26/9/2026).

**Acceso:** el portal de la CNMV, sin registro. Cinco vueltas de
reconocimiento (`docs/fuentes/cnmv-reconocimiento.md`) encontraron el camino:

- `Consultas/derechosvoto/ps_ac_ini.aspx?nif=…` da en su título el nombre que
  la CNMV tiene para ese NIF, y enlaza a las dos tablas con un identificador
  de sesión (`qS`).
- Para un tercio de las cotizadas esa página no trae enlaces (Iberdrola,
  Inditex, Indra, Endesa…). El buscador de participaciones
  (`busqueda.aspx?id=7`, un formulario ASP.NET) sí los da por denominación.
- `Notificaciones-Participaciones.aspx?qS=…` → tabla
  `gridAccionistasSignificativos`; `SociedadesParticipa.aspx?qS=…` → tabla
  `gridSociedades`. Cada celda trae su columna en `data-th`.

**Qué cotizadas.** Las de `ingest/sinapsis_ingest/datos/cotizadas.csv`: el
Ibex 35 con domicilio en España, los grupos de medios cotizados y las
sociedades con participación de la SEPI. La lista dice a quién se pregunta; el
nombre lo pone la CNMV, y un NIF que la CNMV no reconoce se salta.

**Personas.** Entre los accionistas hay personas físicas («AL THANI ,
KHALID THANI ABDULLAH»). Salen con nombre, en su papel de accionista
significativo y en ningún otro: no entran en el mapa del dinero, ni en la
lista de cargos, ni se unen a nadie. La CNMV escribe igual a una sociedad y
a una persona, así que la duda cae del lado de la persona: sólo es sociedad lo
que lleva una forma jurídica reconocible (`es_persona_fisica` en
`sinapsis_ingest/cnmv.py`).

**Límites conocidos:**

- La fecha de la tabla es la del registro de la última notificación en la
  CNMV, no la de compra. Se publica con ese nombre.
- El `qS` cambia en cada sesión: el enlace que se publica es la página estable
  de la cotizada (`ps_ac_ini.aspx?nif=`).
- Los consejos de administración están en el informe anual de gobierno
  corporativo, un PDF cuya tabla C.1.2 trae también la fecha de nacimiento de
  cada consejero. Se reconoce en unos informes y no en otros (formato libre);
  queda para una segunda fase.

**Mapeo a FollowTheMoney:**

```
titular (Company | Person) --Ownership--> cotizada (Company, nif:…)
```

### Los consejos de administración (`cnmv-consejos`)

**Qué:** los miembros del consejo de cada cotizada de la lista, con su
cargo y su categoría (ejecutivo, dominical, independiente, otro externo),
tal como los publica la cotizada en el cuadro C.1.2 de su informe anual de
gobierno corporativo (IAGC), registrado en la CNMV.

**Acceso:** `ee/informaciongobcorp.aspx?nif=…` lista los informes; se toma
el IAGC del último ejercicio de su propia tabla (`wGridIAGC_gridDatos`), no
el de remuneraciones. Es un PDF de 4 a 40 MB. Se guarda en caché por su
número de registro, que no cambia: la primera noche se bajan todos y las
demás sólo los nuevos. Sin pasar antes por la portada, la lista de informes
vuelve vacía; y la CNMV corta conexiones a ratos (octava vuelta, 26/9/2026),
así que cada petición se reintenta.

**Lectura:** sólo el cuadro del modelo de la CNMV, reconocido por su
cabecera exacta, que se repite en cada página. Ese modelo no trae fecha de
nacimiento; el cuadro propio que añaden algunas (el BBVA, «Año de
nacimiento») no se lee. De cada fila, nombre, representante (si la consejera
es una sociedad), categoría y cargo, en listas cerradas; **ninguna fecha**.
Una fila partida entre dos páginas llega sin categoría y se deja, contada:
en las cinco muestras faltan así uno de Prisa y uno del BBVA. El apartado
C.1.1 dice cuántos consejeros fijó la junta, y si se leen menos se anota.

**En la web:** en `cargos.json` (`cotizadas[x].consejo`), nunca en el grafo
ni en el índice. Una persona consejera tiene la misma clave que un
accionista de la CNMV con el mismo nombre —Oughourlian, presidente y
accionista de Prisa, es un nodo—, pero no se une con nadie de otra fuente:
un exministro en un consejo no se enlaza con su ficha del BOE sólo por el
nombre.


---

## 2.quinquies Cuentas de los partidos (Tribunal de Cuentas) — reconocida, sin conector

Para la línea 2 de la fase 7. El Tribunal de Cuentas fiscaliza cada año los
estados contables de los partidos, y la Comisión Mixta Congreso-Senado
aprueba una resolución sobre cada informe que se publica en el BOE.

**Lo que hay** (reconocimiento del 25/9/2026,
`docs/fuentes/partidos-boe-reconocimiento.md`, `scripts/explorar_partidos_boe.py`):
35 disposiciones de «Cortes Generales» desde 1990, la última de julio de
2026, localizables con el buscador del BOE por título (`campo[1]=TITULOS`;
los códigos se leen del propio formulario, no se suponen).

**Por qué no hay conector.** En el BOE sólo es texto la resolución —las
recomendaciones de la Comisión—. El informe con las cifras de cada partido va
como **imágenes de página**: 530 PNG en la de 2024
(`ingest/tests/golden/partidos_boe/BOE-A-2024-13379.xml`, `<p class="imagen">`).
Sacar cifras de ahí exigiría OCR, y un error de OCR en el dinero de un partido
es un dato inventado. El buscador del propio Tribunal va con JavaScript y no
se deja leer (`docs/fuentes/tcu-reconocimiento.md`). Queda pendiente dar con
el PDF del Tribunal con capa de texto.

Lo que sí está en el mapa: las subvenciones públicas a partidos que registra
la BDNS, y los expedientes sancionadores del Tribunal (sección 4).

---

## 3. BORME — Boletín Oficial del Registro Mercantil

**Aporta:** actos societarios inscritos — constituciones, ceses y nombramientos
de administradores, cambios de denominación, disoluciones.

**Acceso:** gratuito vía BOE, sin registro ni certificado.

- Dataset: <https://datos.gob.es/es/catalogo/ea0040819-boletin-oficial-del-registro-mercantil-borme>
- Cobertura: Sección I desde 2009; Sección II desde 2001.

**Límite crítico — léase antes de planificar nada sobre esta fuente:**

El BORME publica un **resumen del acto inscrito, no el documento completo**. En
particular **no publica estructuras accionariales**. Quién posee qué porcentaje
de una sociedad requiere una nota simple del Registro Mercantil, que es de pago.

Además, la sentencia del TJUE **C-37/20 (2022)** restringió el acceso público a
los registros de titularidad real en la UE, así que el Registro de Titularidades
Reales tampoco es una vía abierta.

**Consecuencia:** «quién controla de verdad esta empresa» tendrá **huecos
permanentes**. La interfaz debe marcarlos como tales. Un grafo que finge
completitud es peor que uno que declara sus fronteras.

Lo que sí se puede reconstruir es la red de **administradores** vía
`Directorship`, que es un proxy parcial pero útil.

**Prior art:** [LibreBORME / OpenMercantil](https://openmercantil.es/) ya
reutiliza estos datos. Conviene revisarlo antes de escribir el parser.

**Mapeo a FollowTheMoney:**

```
administrador (Person) --Directorship--> sociedad (Company)
```

---

## 4. Tribunal de Cuentas — financiación de partidos

**Aporta:** contabilidad de partidos políticos, donaciones y sus informes de
fiscalización. Junto con PLACSP, es la fuente de mayor valor del proyecto.

**Acceso:** <https://www.tcu.es> — informes en PDF. Requiere extracción de
tablas desde PDF, a veces escaneado. Fase 6.

**Mapeo a FollowTheMoney:**

```
donante (Person | Company) --Payment--> partido (Organization)
```

**Cuidado:** los donantes personas físicas son el caso más delicado del
proyecto en términos de RGPD. Aplicar §12 de la spec con el máximo rigor.

---

## 5. Registros de grupos de interés (lobbies)

**Aporta:** quién ejerce influencia declarada sobre qué organismo.

**Acceso:** fragmentado. No hay un registro estatal unificado consolidado; hay
registros sectoriales y autonómicos (CNMC, algunas comunidades) con formatos
distintos. Cada uno necesita ficha y conector propios. Fase 6.

**Mapeo a FollowTheMoney:**

```
lobby (Organization) --Representation--> cliente (LegalEntity)
```

---

## 6. Medios de comunicación

**Aporta:** estructura accionarial de los medios, para conectar propiedad con
influencia editorial.

**Acceso:** parcialmente vía BORME (con el límite accionarial de arriba) y
depósitos de cuentas. Es la fuente con más huecos estructurales.

**Lo que ya hay (26/9/2026):** los grupos de medios **cotizados**, por la
CNMV (§2.septies). Qué cotizada es un medio no lo decide una lista nuestra:
lo dice el sector que la CNMV le asigna en su ficha
(`ee/datosgenerales.aspx?nif=…`, «MEDIOS DE COMUNICACIÓN» para Prisa), y
sus dueños son sus accionistas significativos. Los medios no cotizados —la
mayoría— siguen siendo un hueco: el BORME no da accionistas, y el registro
estatal de prestadores audiovisuales está por reconocer.

**Mapeo a FollowTheMoney:**

```
accionista (Company | Person) --Ownership--> medio (Company)
```

---

## Resumen de dificultad

| Fuente | Formato | Dificultad | Fase |
|---|---|---|---|
| BDNS | JSON (API REST) | Baja | 2 |
| PLACSP | ATOM + XML CODICE en ZIP | Media-alta | 3 |
| BORME | XML/PDF diario | Media | 6 |
| Tribunal de Cuentas | PDF, a veces escaneado | Alta | 6 |
| Lobbies | Heterogéneo | Alta | 6 |
| Medios | Derivado de BORME | Alta | 6 |
