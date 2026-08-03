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

**Campos de cada concesión** (verificados en el enumerado de campos ordenables
de la API): `codConcesion`, `numeroConvocatoria`, `convocatoria`, `nivel1`,
`nivel2`, `nivel3`, `instrumento`, `urlBR`, `fechaConcesion`, `beneficiario`,
`nifCif`, `importe`, `ayudaEquivalente`, `tieneProyecto`.

`nivel1..3` es la jerarquía administrativa del órgano concedente; usamos el
nivel más específico que venga relleno.

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
de Subvenciones, art. 20). Los beneficiarios personas físicas se tratan según
§12 de la spec.

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
