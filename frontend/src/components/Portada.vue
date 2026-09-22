<script setup>
/**
 * La portada: por dónde se empieza.
 *
 * Listas ordenadas, no un grafo. Quien entra por primera vez no sabe qué
 * buscar, y una maraña de dos mil nodos no le da ningún asidero: lo primero
 * que tiene que ver es dónde está el dinero y a un clic de qué.
 *
 * Cada lista lleva escrito lo que significa Y lo que no. Una tabla ordenada
 * por euros se lee sola como una lista de sospechosos, y aquí encabezarla sólo
 * quiere decir que se compra mucho.
 */
import { computed } from 'vue'
import { construirDirectorio, construirDirectorioDesdeIndice } from '../directorio.js'
import { contratosDeMedios } from '../medios.js'
import { dineroCorto } from '../nucleos.js'
import { COLOR_POR_DEFECTO, COLOR_POR_ESQUEMA, etiquetaEsquema } from '../esquemas.js'

const props = defineProps({
  /** El grafo YA colapsado. */
  datos: { type: Object, default: null },
  /** El grafo sin colapsar: el CPV vive en el expediente, no en la arista. */
  crudo: { type: Object, default: null },
  /** Índice de TODA la base. Si está, manda él para los rankings de dinero. */
  indice: { type: Object, default: null },
})
const emit = defineEmits(['seleccionar', 'verMapa'])

/**
 * Los rankings de dinero salen del índice cuando lo hay, porque el índice
 * cubre toda la base y el grafo sólo lo que cabe en el mapa. Con rankings
 * calculados sobre el grafo, «quién reparte más dinero público» contestaba en
 * realidad «de los que caben en el mapa, quién reparte más».
 *
 * Las sanciones y el ámbito de interés siguen saliendo del grafo: son
 * relaciones, y el índice no lleva aristas.
 */
const delGrafo = computed(() => construirDirectorio(props.datos))
const delIndice = computed(() => construirDirectorioDesdeIndice(props.indice))

const dir = computed(() => {
  const g = delGrafo.value
  const i = delIndice.value
  if (!i) return g
  return {
    ...i,
    sancionados: g.sancionados,
    totales: {
      ...i.totales,
      nOperaciones: g.totales.nOperaciones,
      nSancionados: g.totales.nSancionados,
      totalSancionado: g.totales.totalSancionado,
      nSinCifra: g.totales.nSinCifra,
    },
  }
})

/** Cuántas entidades hay en la base que no caben en el mapa publicado. */
const fueraDelMapa = computed(() => {
  const t = delIndice.value?.totales
  return t ? Math.max(0, t.nActores - (t.enMapa ?? 0)) : 0
})
const medios = computed(() => contratosDeMedios(props.crudo))

function dinero(v) {
  return dineroCorto(v)
}

const LISTAS = [
  {
    clave: 'pagadores',
    titulo: 'Quién reparte más dinero público',
    que: 'Organismos y entidades por el total que sale de ellos hacia empresas y beneficiarios.',
    noEs: 'Encabezar esta lista no indica nada irregular: un servicio de salud compra para una comunidad entera.',
    unidad: (x) => `${x.n} ${x.n === 1 ? 'receptor' : 'receptores'}`,
  },
  {
    clave: 'receptores',
    titulo: 'Quién más cobra',
    que: 'Empresas y entidades por el total que reciben de administraciones públicas.',
    noEs: 'Facturar mucho es lo normal en sectores concentrados, como el farmacéutico o la obra civil.',
    unidad: (x) => `${x.n} ${x.n === 1 ? 'pagador' : 'pagadores'}`,
  },
  {
    clave: 'transversales',
    titulo: 'Cobran de más administraciones distintas',
    que: 'Ordenado por número de pagadores diferentes, no por dinero: quien aparece en muchas administraciones ha hecho un recorrido que el importe no enseña.',
    noEs: 'Puede ser simplemente un proveedor de un servicio que todas necesitan.',
    unidad: (x) => `${x.n} administraciones`,
    destacar: 'n',
  },
  {
    clave: 'extranjeras',
    titulo: 'Capital extranjero',
    que: 'Entidades con NIF de no residente (letras N y W) o NIE que cobran de administraciones españolas.',
    noEs: 'El NIF dice dónde tributan, no quién las controla. Una filial española de una matriz extranjera no aparece aquí.',
    unidad: (x) => `${x.n} ${x.n === 1 ? 'contraparte' : 'contrapartes'}`,
  },
  {
    clave: 'sancionados',
    titulo: 'Expedientes del Tribunal de Cuentas',
    que: 'Formaciones políticas con expedientes sancionadores del Tribunal de Cuentas y su cuantía.',
    noEs: 'Es una deuda con el Estado, no un pago a nadie: no es financiación en ningún sentido.',
    unidad: (x) => `${x.expedientes ?? x.n} ${(x.expedientes ?? x.n) === 1 ? 'expediente' : 'expedientes'}`,
    tono: 'sancion',
  },
]

const listas = computed(() =>
  LISTAS.map((l) => ({ ...l, filas: dir.value[l.clave] ?? [] })).filter((l) => l.filas.length),
)

function tope(filas, campo = 'total') {
  return Math.max(1, ...filas.map((f) => f[campo] ?? 0))
}

/**
 * Cuánto ocupa la barra de fondo de una fila, en porcentaje del primero.
 *
 * Proporcional de verdad, sin raíz ni mínimos: aquí la cifra exacta va al lado
 * en la misma línea, así que una barra corta no esconde nada — y en una lista
 * lo que se quiere ver de un vistazo es precisamente si el primero se lleva
 * casi todo o si está repartido.
 */
/** La cifra destacada: la magnitud por la que la lista está ordenada. */
function cifraCabeza(f, lista) {
  if (lista.destacar === 'n') return lista.unidad(f)
  return dineroCorto(f.total)
}

function proporcion(f, lista) {
  const campo = lista.destacar === 'n' ? 'n' : 'total'
  // Tope en 92 % y no en 100: con la barra llegando al borde, la primera fila
  // de cada lista parecía seleccionada en vez de medida. Que se vea dónde
  // acaba es lo que la convierte en una barra.
  return Math.max(1.5, ((f[campo] ?? 0) / tope(lista.filas, campo)) * 92)
}

function color(schema) {
  return COLOR_POR_ESQUEMA[schema] ?? COLOR_POR_DEFECTO
}
</script>

<template>
  <div class="portada">
    <!--
      La entradilla era un párrafo de cuatro líneas explicando cómo usar la
      página («pulsa cualquier nombre para ver…») y cinco recuadros de cifras
      del mismo tamaño. En móvil eso son dos pantallas de scroll antes del
      primer dato.
      Si hay que explicar que se puede pulsar un nombre, lo que falla es que
      no lo parezca; se arregla en la lista, no con un párrafo. Y de las cinco
      cifras, tres tienen su propia sección más abajo.
    -->
    <section class="intro">
      <h2>Dónde está el dinero</h2>
      <p class="lema">
        Quién paga a quién en la contratación y las subvenciones públicas
        españolas, sacado de los documentos oficiales y con el documento
        siempre a mano.
      </p>

      <!--
        Una cifra grande y tres de apoyo, y no cinco recuadros iguales.
        La página tiene UNA cosa que decir al entrar —cuánto dinero hay
        seguido— y antes la decía en el mismo cuerpo de letra que el resto,
        así que no la decía. La cifra va con las cifras proporcionales de la
        fuente: a este tamaño, las tabulares dejan huecos entre dígitos.
      -->
      <div class="cabecera-cifras">
        <p class="hero">
          <span class="valor">{{ dineroCorto(dir.totales.dineroTotal) }}</span>
          <span class="que">seguidos hasta quien los cobra</span>
        </p>
        <dl class="apoyo">
          <div>
            <dt>Entidades</dt>
            <dd class="tabular">{{ dir.totales.nActores.toLocaleString('es-ES') }}</dd>
          </div>
          <div v-if="fueraDelMapa">
            <dt>Caben en el mapa</dt>
            <dd class="tabular">{{ (dir.totales.enMapa ?? 0).toLocaleString('es-ES') }}</dd>
          </div>
          <div v-if="dir.totales.nPartidos">
            <dt>Formaciones políticas</dt>
            <dd class="tabular">{{ dir.totales.nPartidos.toLocaleString('es-ES') }}</dd>
          </div>
        </dl>
      </div>
    </section>

    <div class="rejilla">
      <section v-for="l in listas" :key="l.clave" class="tarjeta" :class="l.tono">
        <h3>{{ l.titulo }}</h3>
        <p class="que">{{ l.que }}</p>
        <ol class="ranking">
          <!--
            La fila ENTERA es el botón. Antes sólo lo era el nombre: el resto
            de la línea —el puesto, el tipo, la cifra— no hacía nada al
            pulsarlo, y había que explicar en un párrafo de la entradilla que
            se podía pulsar. Si hay que decirlo, es que no se ve.
          -->
          <li v-for="(f, i) in l.filas" :key="f.id">
            <button class="fila" @click="emit('seleccionar', f.id)">
              <span
                class="fondo"
                :style="{ width: `max(6px, calc(${proporcion(f, l)}% - 1rem))` }"
                aria-hidden="true"
              />
              <span class="puesto">{{ i + 1 }}</span>
              <span class="cuerpo">
                <span class="nombre">
                  <span class="punto" :style="{ background: color(f.schema) }" />
                  <span class="etiqueta" :title="f.caption">{{ f.caption }}</span>
                </span>
                <span class="meta">
                  {{ etiquetaEsquema(f.schema) }} ·
                  <!-- La otra magnitud, la que no encabeza la fila. -->
                  <template v-if="l.destacar === 'n'">{{ dineroCorto(f.total) }}</template>
                  <template v-else>{{ l.unidad(f) }}</template>
                  <span v-if="f.extranjera && l.clave !== 'extranjeras'" class="marca">· no residente</span>
                  <!--
                    Está en la base pero no en el grafo publicado: se puede
                    abrir su ficha y ver sus cifras, no su red. Decirlo aquí
                    evita que el clic parezca roto.
                  -->
                  <span v-if="f.enMapa === false" class="sin-red">· sin red en el mapa</span>
                </span>
              </span>
              <!--
                La cifra grande es SIEMPRE la magnitud por la que está
                ordenada la lista. En «cobran de más administraciones» se
                enseñaba el dinero al lado de una barra que medía
                administraciones: el número 3 tenía la barra más larga que el
                7 y la cifra cinco veces menor. Parecía un fallo de cálculo y
                era una comparación de dos cosas distintas.
              -->
              <span class="cifra">{{ cifraCabeza(f, l) }}</span>
            </button>
          </li>
        </ol>
        <p class="no-es">{{ l.noEs }}</p>
      </section>
    </div>

    <!--
      Publicidad institucional. Se enseña el objeto del contrato, no una
      etiqueta sobre la empresa: el dato dice para qué era el contrato, y de
      ahí no se sigue que el adjudicatario sea un medio de comunicación.

      El título decía «y medios» y prometía algo que el dato no dice. Los
      cuatro contratos de cabeza de la instantánea del 22/9 los cobran dos
      aerolíneas (promoción del turismo navarro y extremeño), un club de
      fútbol (patrocinio para publicitar una marca de ciudad), un obrador y
      una agencia de medios vasca. El filtro CPV es correcto —todos son
      contratos de publicidad— pero ninguno de los cuatro primeros es un
      medio de comunicación. El desmentido estaba al pie, después de la
      lista: llegaba tarde. Ahora el título no lo afirma y el matiz va en la
      entradilla.
    -->
    <section v-if="medios.contratos.length" class="tarjeta medios">
      <h3>Gasto en publicidad institucional</h3>
      <p class="que">
        <b>{{ dinero(medios.total) }}</b> en {{ medios.contratos.length }}
        {{ medios.contratos.length === 1 ? 'adjudicación' : 'adjudicaciones' }}
        cuyo objeto es publicidad, edición, radio, televisión o relaciones
        públicas, según el código CPV que el propio órgano de contratación
        asignó al expediente. Es de qué iba el contrato, no qué es quien lo
        cobra: puede ser un medio, y puede ser la agencia que compra los
        espacios, la productora o la imprenta.
      </p>

      <div class="dos-columnas">
        <div>
          <h4>Quién cobra</h4>
          <ul class="lista">
            <li v-for="e in medios.porEmpresa" :key="e.id">
              <button @click="emit('seleccionar', e.id)">{{ e.caption }}</button>
              <span class="cifra">{{ dinero(e.total) }}</span>
            </li>
          </ul>
        </div>
        <div>
          <h4>Quién paga</h4>
          <ul class="lista">
            <li v-for="o in medios.porOrganismo" :key="o.id">
              <button @click="emit('seleccionar', o.id)">{{ o.caption }}</button>
              <span class="cifra">{{ dinero(o.total) }}</span>
            </li>
          </ul>
        </div>
      </div>

      <details class="expedientes">
        <summary>Ver los {{ medios.contratos.length }} contratos uno a uno</summary>
        <ul class="lista detalle">
          <li v-for="c in medios.contratos" :key="c.id">
            <p class="titulo-contrato">{{ c.titulo }}</p>
            <p class="linea">
              <button @click="emit('seleccionar', c.organoId)">{{ c.organo }}</button>
              <span class="flecha">→</span>
              <button @click="emit('seleccionar', c.empresaId)">{{ c.empresa }}</button>
              <span class="cifra">{{ c.sinImporte ? 'importe no publicado' : dinero(c.importe) }}</span>
            </p>
            <p class="linea meta">
              {{ c.etiqueta }} (CPV {{ c.cpv }})
              <a v-if="c.url" :href="c.url" target="_blank" rel="noopener noreferrer">ver el expediente</a>
            </p>
          </li>
        </ul>
      </details>

    </section>

    <p class="pie">
      <template v-if="fueraDelMapa">
        Los rankings cubren las
        {{ dir.totales.nActores.toLocaleString('es-ES') }} entidades ingeridas;
        el mapa dibuja las {{ (dir.totales.enMapa ?? 0).toLocaleString('es-ES') }}
        con más dinero, así que
        {{ fueraDelMapa.toLocaleString('es-ES') }} se pueden buscar y consultar
        pero no se ven en el grafo.
      </template>
      <template v-else>
        Las listas se calculan sobre la instantánea publicada, que es una parte
        del total.
      </template>
      Lo que falta por ingerir no aparece, y la ausencia de una entidad aquí no
      dice nada sobre ella.
      <template v-if="dir.totales.nSinCifra">
        Otras <b>{{ dir.totales.nSinCifra.toLocaleString('es-ES') }}</b>
        operaciones constan pero sin cifra utilizable, así que no suman en
        ningún total: casi siempre porque el importe publicado es el del
        acuerdo marco entero y figura repetido en cada adjudicatario, que no es
        lo que cobra cada uno.
      </template>
    </p>
  </div>
</template>

<style scoped>
.portada { overflow-y: auto; padding: 1.2rem 1.4rem 3rem; height: 100%; }

.intro { max-width: 64rem; }
.intro h2 {
  font-size: clamp(1.75rem, 4vw, 2.5rem); margin: 0 0 var(--e2);
  letter-spacing: -0.03em; font-weight: 680;
}
.intro p { line-height: 1.6; margin: 0; max-width: 46rem; }

.lema { max-width: 46rem; font-size: var(--t-m); color: var(--tinta-2); }

.cabecera-cifras {
  display: flex; flex-wrap: wrap; align-items: flex-end;
  gap: var(--e5) var(--e7); margin-top: var(--e5);
}
.hero { margin: 0; display: flex; flex-direction: column; gap: 0.1rem; }
.hero .valor {
  font-size: var(--t-hero); font-weight: 680; color: var(--tinta);
  line-height: 1; letter-spacing: -0.03em;
}
.hero .que { font-size: var(--t-s); color: var(--tinta-3); }

.apoyo { display: flex; flex-wrap: wrap; gap: var(--e5); margin: 0 0 0.3rem; }
.apoyo div { display: flex; flex-direction: column; gap: 0.1rem; }
.apoyo dt {
  font-size: var(--t-xs); color: var(--tinta-3);
  text-transform: uppercase; letter-spacing: 0.07em;
}
.apoyo dd { margin: 0; font-size: var(--t-xl); font-weight: 620; color: var(--tinta); line-height: 1.1; }

/*
  Dos columnas y no tres. Los nombres oficiales de este país son larguísimos
  —«Consejería de Presidencia, Justicia y Administración Local»— y en una
  columna de 28rem se parten en tres renglones cada uno: la lista deja de
  leerse como una lista y pasa a ser un párrafo con cifras.
*/
.rejilla {
  display: grid; gap: var(--e4); margin-top: var(--e6);
  /*
    `min(31rem, 100%)` y no `31rem` a secas: el mínimo de un `minmax` NO
    encoge, así que en un móvil de 390 px la columna se quedaba en 496 px y la
    tarjeta se salía de la pantalla por la derecha, cortando el texto.
  */
  grid-template-columns: repeat(auto-fit, minmax(min(31rem, 100%), 1fr));
}

.tarjeta {
  background: var(--superficie); border: 1px solid var(--linea);
  border-radius: var(--radio); padding: var(--e5) var(--e5) var(--e4);
}
.tarjeta h3 { font-size: var(--t-l); margin: 0 0 var(--e2); }
.que {
  font-size: var(--t-s); color: var(--tinta-3); line-height: 1.5;
  margin: 0 0 var(--e4); max-width: 42ch;
}

.ranking { list-style: none; margin: 0; padding: 0; }
/*
  Sin línea entre filas: la barra de cada una y el aire de debajo ya las
  separan, y una línea más a 6 px de la barra se confunde con ella.
*/
.ranking li { border-bottom: none; }

.fila {
  position: relative; width: 100%; display: grid; gap: var(--e3) var(--e3);
  grid-template-columns: 1.5rem 1fr auto; align-items: baseline;
  background: none; border: none; color: inherit; font: inherit;
  padding: 0.6rem 0.5rem 0.85rem; margin: 0 -0.5rem; text-align: left;
  cursor: pointer; border-radius: var(--radio-s);
}
/*
  El ratón NO pinta fondo, y es a propósito: el fondo ya significa otra cosa
  —la barra proporcional— y con las dos cosas pintadas igual la fila bajo el
  cursor parecía la más grande de la lista.
*/
.fila:hover, .fila:focus-visible { outline: none; box-shadow: inset 0 0 0 1px var(--acento); }
.fila:hover .nombre, .fila:focus-visible .nombre { color: var(--acento); }

/*
  Una barra, no un bloque de fondo.
  Ha pasado por las tres formas y las dos primeras fallaban por lo mismo:
  - Línea de 3 px entre el nombre y el tipo: se leía como un subrayado.
  - Tinte detrás de la fila entera: con las filas altas —los nombres oficiales
    ocupan dos renglones— el tinte es un bloque del tamaño de un botón, y la
    fila más larga parecía seleccionada, no medida.
  Abajo del todo, a 6 px de alto y separada del texto, se lee como lo que es.
  Extremo del dato redondeado y base cuadrada: nace del borde izquierdo.
*/
.fondo {
  position: absolute; left: 0.5rem; bottom: 0.3rem; height: 6px;
  background: var(--serie-1); pointer-events: none;
  border-radius: 1px 4px 4px 1px;
}
.tarjeta.sancion .fondo { background: var(--grave); }
.fila:hover .fondo { filter: brightness(1.25); }

.puesto {
  font-size: var(--t-xs); color: var(--tinta-3);
  font-variant-numeric: tabular-nums; text-align: right;
}
.cuerpo { min-width: 0; display: block; }
.nombre {
  color: var(--tinta); font-size: var(--t-m); line-height: 1.35; font-weight: 500;
  display: flex; align-items: baseline; gap: var(--e2);
}
/*
  Dos renglones como mucho. «UTE: OBRASCON HUARTE LAIN, S.A., AZVI, S.A.U. Y
  ROVER INFRAESTRUCTURAS, S.A. (CIUDAD DE LA JUSTICIA LOTE 1)» ocupaba cuatro
  y empujaba la fila siguiente fuera de la tarjeta. El nombre entero está en
  el `title` y en la ficha, a un clic.
*/
.nombre .etiqueta {
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden; min-width: 0;
}
.punto { width: 8px; height: 8px; border-radius: 50%; flex: none; }
.meta {
  display: block; font-size: var(--t-xs); color: var(--tinta-3); margin-top: 0.2rem;
}
.meta .marca { color: var(--tinta-2); }
.meta .sin-red { color: var(--aviso); }
/*
  La cifra en tinta, no en el color de la serie. El punto de color de al lado
  es el que lleva la identidad; una cifra pintada del color del dato compite
  con el dato y encima se lee peor —un verde o un ámbar sobre fondo oscuro no
  dan el contraste que da el blanco—.
*/
.cifra {
  font-size: var(--t-m); font-variant-numeric: tabular-nums; white-space: nowrap;
  color: var(--tinta); font-weight: 620;
}

/*
  En móvil la cifra baja a su propio renglón. Compartiendo renglón con el
  nombre le dejaba una columna de dos palabras: «Consejería de
  Presidencia,…» y el resto cortado, en una lista cuyo trabajo es que se lea
  quién es quién.
*/
@media (max-width: 600px) {
  .fila { grid-template-columns: 1.5rem 1fr; }
  .cifra { grid-column: 2; justify-self: start; font-size: var(--t-l); }
  .tarjeta { padding: var(--e4) var(--e4) var(--e3); }
  .nombre .etiqueta { -webkit-line-clamp: 3; }
}

.no-es {
  font-size: var(--t-xs); color: var(--tinta-3); line-height: 1.5;
  margin: var(--e4) 0 0; padding-top: var(--e3); border-top: 1px solid var(--linea);
}

.medios { margin-top: 1rem; }
.dos-columnas { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem 1.5rem; }
.medios h4 {
  font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--texto-tenue); margin: 0 0 0.35rem;
}
.lista { list-style: none; margin: 0; padding: 0; }
.lista > li {
  display: flex; justify-content: space-between; gap: 0.6rem; align-items: baseline;
  padding: 0.3rem 0; border-bottom: 1px solid var(--borde-suave); font-size: 0.82rem;
}
.lista button {
  background: none; border: none; color: var(--texto); font: inherit; padding: 0;
  cursor: pointer; text-align: left;
}
.lista button:hover { color: var(--acento); }

.expedientes { margin-top: 0.9rem; }
.expedientes summary {
  cursor: pointer; font-size: 0.78rem; color: var(--acento); padding: 0.3rem 0;
}
.detalle > li { display: block; padding: 0.55rem 0; }
.titulo-contrato { margin: 0 0 0.2rem; font-size: 0.8rem; line-height: 1.35; }
.linea { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.4rem; margin: 0; font-size: 0.8rem; }
.linea.meta { font-size: 0.7rem; color: var(--texto-tenue); margin-top: 0.15rem; }
.flecha { color: var(--texto-tenue); }

@media (max-width: 640px) {
  .dos-columnas { grid-template-columns: 1fr; }
}

.pie {
  margin: 1.6rem 0 0; font-size: 0.73rem; color: var(--texto-tenue);
  line-height: 1.5; max-width: 44rem;
}
</style>
