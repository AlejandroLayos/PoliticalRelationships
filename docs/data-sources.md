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

**Endpoint de ejemplo** (convocatorias por rango de fechas):

```
GET /bdnstrans/api/convocatorias/busqueda
    ?fechaDesde=01/01/2025&fechaHasta=31/12/2025&pageSize=50&page=0
```

**Límites:**

- `pageSize` máximo **10.000 registros por consulta**. Hay que paginar, y para
  rangos grandes conviene trocear por fechas además de por página.
- Sin límite de tasa documentado. Se aplica *backoff* por prudencia y para no
  cargar un servicio público.

**Referencia de implementación:** [`bdns-fetch`](https://github.com/cruzlorite/bdns-fetch)
(Python, GPLv3) implementa las rutas oficiales. Se usa como **referencia de
endpoints y parámetros**, no como dependencia — su licencia GPLv3 es compatible
con nuestra AGPL-3.0, pero portamos la lógica.

**Mapeo a FollowTheMoney:**

```
organismo convocante (PublicBody) --Payment--> beneficiario (Company | Person)
```

Con `amount`, `currency = 'EUR'`, `start_date` de la concesión, y
`dedupe_key` derivada del identificador de concesión de BDNS.

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

**Mapeo a FollowTheMoney:**

```
Contract (el expediente) --ContractAward--> adjudicatario (Company)
órgano de contratación (PublicBody) relacionado con el Contract
```

**Base legal:** publicidad obligatoria (Ley 9/2017 de Contratos del Sector
Público).

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
