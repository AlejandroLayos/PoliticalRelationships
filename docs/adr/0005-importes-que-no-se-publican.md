# ADR 0005 — Cuándo NO se publica un importe

- **Estado:** aceptado
- **Fecha:** 2026-09-18

## Contexto

El 18/9/2026, al estrenar la portada con los rankings de «quién más cobra del
Estado», los primeros puestos eran estos:

| entidad | importe publicado |
| --- | ---: |
| CRISOSTOMO FINE ART SERVICES SL | 2.000 M € |
| INDRA SOLUCIONES TECNOLOGÍAS DE LA INFORMACIÓN S.L | 908 M € |
| AYESA ADVANCED TECHNOLOGIES SA | 906 M € |
| SOLTEL IT SOLUTIONS SL | 903 M € |
| INETUM ESPAÑA S.A. | 902 M € |

Ocho empresas rondando los 900 millones, todas con la misma cifra, es lo que
hizo mirar. Resultaron ser **dos problemas distintos**, y los dos convertían la
web en una máquina de publicar cifras falsas con nombre y apellidos.

### Problema 1: erratas del formulario de origen

CRISOSTOMO FINE ART SERVICES SL cobró un servicio de transporte para una
exposición temporal. El expediente declara un presupuesto base de licitación de
**22.000 €** y un importe adjudicado de **1.954.023.643,40 €**: 88.819 veces
más. Otras dos adjudicaciones del mismo tipo de servicio, en el mismo
organismo, van a 11.965 € y 6.670 €.

Es una errata de quien rellenó el formulario. El conector la leía bien: estaba
así en la fuente.

Esa sola cifra era el **8 %** de todo el dinero del mapa.

### Problema 2: el valor del acuerdo marco, repetido en cada adjudicatario

En un acuerdo marco o un sistema dinámico de adquisición, PLACSP publica el
valor del acuerdo —o del lote— en el resultado de **cada** adjudicatario
admitido. No es lo que va a cobrar cada uno: es el techo de gasto del marco,
dentro del cual después compiten por los pedidos concretos.

Un acuerdo marco de servicios informáticos con 20 adjudicatarios a
900.000.000 € cada uno aportaba **18.000 millones de euros**: el 85 % del
dinero del mapa entero.

Sumado todo, el **90,5 %** del dinero de las adjudicaciones venía de importes
repetidos así. El mapa decía 23.000 millones donde hay del orden de 2.000.

## Decisión

**Cuando un importe no es atribuible a quien aparece al otro lado de la arista,
no se publica la cifra — pero sí la relación.**

Se aplica en dos casos:

1. **Importe inverosímil.** El importe adjudicado supera en más de **diez
   veces** el presupuesto base de licitación del propio contrato.
2. **Importe compartido.** El mismo importe figura en **dos o más**
   adjudicaciones del mismo contrato.

En los dos, la arista `ContractAward` se conserva con `amount` vacío, y:

- el valor original va a `importeSinInterpretar` o a `importeCompartido`;
- `motivoImporteDudoso` explica por qué, en castellano y con las cifras dentro;
- `confidence` baja a 0,5.

El volcado lleva las propiedades de la arista, y la interfaz cuenta esas
operaciones aparte: «3 operaciones sin cifra publicada (importe no verosímil)».

## Razones

**Lo que se descarta es la atribución, no el hecho.** Esas empresas cobraron
ese servicio, o entraron en ese acuerdo marco. Eso es un dato y se publica. Lo
que no se puede afirmar es *cuánto* le corresponde a cada una.

**Un falso positivo aquí es una acusación falsa.** Publicar «INDRA recibió 908
millones de euros de este organismo» no es un error de redondeo: es una
afirmación sobre una empresa concreta, falsa, en una web cuyo propósito es que
se la crean. Un falso negativo es sólo un hueco ([spec §12](../spec.md)).

**Que el número venga de la fuente no lo hace cierto.** «Sin procedencia no se
persiste» no significa «con procedencia se publica cualquier cosa». La
procedencia dice de dónde sale un dato, no que sea correcto.

**El hueco se explica.** Una relación sin importe y sin motivo se lee como un
cero, y entonces la ausencia de dato pasa por dato. Por eso el motivo viaja
con la arista hasta la pantalla, incluso cuando el expediente se colapsa para
unir al organismo con la empresa.

## Umbrales, y por qué esos

**Diez veces el presupuesto**, deliberadamente flojo. Un importe puede superar
al presupuesto por IVA, por lotes contados de otra manera, por una prórroga o
por un presupuesto anualizado frente a un importe de todo el plazo. En las
1.901 adjudicaciones ingeridas con presupuesto publicado, el **99,5 % está en
1,07 veces o por debajo** y sólo dos pasan de cinco. A diez veces ya no queda
ninguna explicación posible.

**Dos repeticiones**, deliberadamente estricto. Podrían ser dos lotes de
idéntico valor adjudicados a empresas distintas, pero desde fuera no hay manera
de distinguir ese caso del acuerdo marco. Exigir tres repeticiones en vez de
dos sólo rescata un 0,3 % del dinero: no vale el precio de publicar cifras
falsas.

La asimetría entre los dos umbrales es intencionada y sale de los datos, no de
la simetría: en un caso la distribución deja un hueco enorme entre lo normal y
lo imposible, y en el otro no hay hueco ninguno.

## Consecuencias

- **El dinero publicado baja un 90 %.** Es la corrección, no una pérdida: lo
  anterior era en su mayoría la misma cifra contada muchas veces.
- **Las UTE pierden su importe.** Dos empresas en un mismo `TenderResult`
  comparten importe, así que la regla las alcanza. Es correcto: el dinero fue a
  la UTE y no sabemos cómo se reparte. La UTE, cuando figura como
  adjudicataria con nombre propio, sí conserva el suyo.
- **Un test que ya existía se rompió y tenía razón.** Los dos adjudicatarios de
  la muestra golden de PLACSP van en el mismo `TenderResult` —es una UTE— y la
  regla les bajaba la confianza a los dos, tapando lo que ese test miraba.
- **No se corrige ninguna cifra, ni se reparte ninguna.** Dividir el acuerdo
  marco entre sus adjudicatarios sería inventar datos.

## Alternativas consideradas

**Repartir el importe compartido entre los adjudicatarios.** Daría un total
correcto y cifras individuales inventadas. El total no es lo que se publica al
lado del nombre de una empresa.

**Publicar la cifra con un aviso.** El aviso no viaja: la cifra se cita, se
captura de pantalla y se comparte sola.

**Filtrar sólo los acuerdos marco por su tipo de procedimiento.** El campo
existe (`ProcedureCode`) pero no distingue de forma fiable los casos en que el
importe se repite, y deja fuera los lotes. La repetición del importe es el
síntoma directo del problema; el tipo de procedimiento es un proxy.
