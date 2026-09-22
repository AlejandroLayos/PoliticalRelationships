<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import FlujoDinero from './components/FlujoDinero.vue'
import GrafoRed from './components/GrafoRed.vue'
import MapaNucleos from './components/MapaNucleos.vue'
import PanelEntidad from './components/PanelEntidad.vue'
import PanelInfluencia from './components/PanelInfluencia.vue'
import PanelNucleos from './components/PanelNucleos.vue'
import Portada from './components/Portada.vue'
import {
  buscarTodo,
  cargarIndiceTop,
  cargarInstantanea,
  indiceCargado,
  entidad as pedirEntidad,
  estado,
  estadoServidor,
  grafoCompleto,
  vecinos,
} from './api.js'
import { ENTIDAD_INICIAL } from './demo.js'
import { COLOR_POR_DEFECTO, COLOR_POR_ESQUEMA, NOMBRE_ESQUEMA } from './esquemas.js'
import { accionDeEstado, direccionDeVista, mismoEstado, vistaDeParametros } from './enlace.js'
import { areaDeInfluencia } from './influencia.js'
import { contratosDeMedios } from './medios.js'
import { colapsarNodosDePaso, dineroCorto } from './nucleos.js'

const consulta = ref('')
const resultados = ref([])
const buscando = ref(false)
// Cuántos resultados vienen sólo del índice: existen en la base pero no
// caben en el mapa publicado, así que de ellos sólo hay cifras.
const soloIndice = ref(0)
/** La fila del índice cuando lo seleccionado no está en el grafo publicado. */
const fueraDelMapa = ref(null)
const datos = ref({ nodes: [], edges: [], truncated: false })
const seleccionado = ref(null)
const seleccionId = ref('')
const profundidad = ref(2)
const cargando = ref(false)
const error = ref('')
const esDemo = ref(false)
const baseVacia = ref(false)
const arrancando = ref(true)
const instantanea = ref(null)
const indice = ref(null)

// --- vistas ---------------------------------------------------------------
// `portada` es lo primero que se ve con instantánea cargada. El mapa entero es
// una textura —dos mil entidades en mil píxeles son dos píxeles cada una— y
// como pantalla de entrada no da ningún asidero: quien llega no sabe qué
// buscar. Una lista ordenada por dinero sí. El mapa sigue estando, a un clic,
// para lo que sí hace bien: enseñar la forma y los grupos.
const vista = ref('portada')
const grafoEntero = ref(null)
// El mapa no se monta hasta que alguien lo pide: calcular núcleos y layout de
// dos mil nodos son varios segundos de CPU, y hacerlos al cargar la portada
// sería cobrárselos a todo el mundo para una vista que no todos abren. Una vez
// montado se queda, para que volver sea instantáneo.
const mapaPedido = ref(false)
const nucleos = ref([])
const nucleoEnfocado = ref(null)
const totalDinero = ref(0)
const visiblesEnMapa = ref(0)
const minImporte = ref(0)
const mostrarExpedientes = ref(false)
const mostrarSueltos = ref(false)
const soloExtranjero = ref(false)
const soloPartidos = ref(false)

const ESCALONES = [
  { v: 0, t: 'todo' },
  { v: 10_000, t: '10 mil €' },
  { v: 100_000, t: '100 mil €' },
  { v: 1_000_000, t: '1 M €' },
  { v: 10_000_000, t: '10 M €' },
]

function alAnalizar({ nucleos: n, totalDinero: d, visibles }) {
  nucleos.value = n
  totalDinero.value = d
  visiblesEnMapa.value = visibles
}

const hayMapa = computed(() => Boolean(grafoEntero.value?.nodes?.length))

// --- ficha de influencia --------------------------------------------------
// El grafo se colapsa ANTES de calcular la ficha, y eso no es un detalle de
// dibujo: sin colapsar, la pregunta «¿a qué empresas paga mi ayuntamiento?» se
// contesta con una lista de expedientes, porque entre el organismo y la empresa
// siempre hay un contrato de por medio. El expediente no desaparece —cada
// relación conserva el suyo y el panel lo cuenta—, pero deja de ser la
// respuesta.
const grafoColapsado = computed(() =>
  grafoEntero.value ? colapsarNodosDePaso(grafoEntero.value) : null,
)

/** Qué hay dibujado. Se consulta en cada clic, así que no puede ser un barrido. */
const idsDelMapa = computed(() => new Set((grafoEntero.value?.nodes ?? []).map((n) => n.id)))

const area = computed(() => {
  if (!seleccionId.value) return null
  // Si lo seleccionado ES un expediente —se pueden mostrar con el filtro—, en
  // el grafo colapsado ya no existe: se mira el crudo.
  const enColapsado = grafoColapsado.value
    ? areaDeInfluencia(grafoColapsado.value, seleccionId.value)
    : null
  if (enColapsado?.entidad) return enColapsado
  return grafoEntero.value ? areaDeInfluencia(grafoEntero.value, seleccionId.value) : null
})

/** Los filtros que recortan el mapa ahora mismo, dichos con palabras. */
const filtrosPuestos = computed(() => {
  const puestos = []
  if (soloExtranjero.value) puestos.push('capital extranjero')
  if (soloPartidos.value) puestos.push('partidos')
  if (minImporte.value > 0) {
    const e = ESCALONES.find((x) => x.v === minImporte.value)
    puestos.push(`importe mínimo ${e ? e.t : minImporte.value}`)
  }
  return puestos
})

function quitarFiltros() {
  soloExtranjero.value = false
  soloPartidos.value = false
  minImporte.value = 0
}

/** Los tipos de entidad que hay ahora mismo en el grafo del vecindario. */
const esquemasEnPantalla = computed(() => {
  const vistos = new Set((datos.value?.nodes ?? []).map((n) => n.schema))
  return Object.keys(COLOR_POR_ESQUEMA).filter((e) => vistos.has(e))
})

const hayInferidas = computed(() =>
  (datos.value?.edges ?? []).some((a) => a.status === 'inferred'),
)

/** ¿Hay alguna contraparte no residente entre las que se dibujan? */
const hayNoResidente = computed(() =>
  Boolean(
    area.value &&
      [...(area.value.recibeDe ?? []), ...(area.value.pagaA ?? [])].some((c) => c.extranjera),
  ),
)

// Se calcula una vez sobre el grafo entero y la ficha filtra lo suyo: recorrer
// cuatro mil nodos en cada selección no aporta nada y se nota al pulsar.
const medios = computed(() =>
  grafoEntero.value ? contratosDeMedios(grafoEntero.value, { limite: 1000 }) : null,
)

/** Lo que hay que advertir cuando una ficha sale sin dinero por culpa nuestra. */
const notaDeHueco = computed(() => {
  const caidas = instantanea.value?.fuentesSinDatos ?? []
  if (!caidas.length) return ''
  return `Hoy no respondió ${caidas.map((f) => f.name).join(' ni ')}, así que lo que`
    + ' cubre esa fuente no está en esta instantánea.'
})

let temporizador = null
/* --- Teclado en el buscador -------------------------------------------- */
/*
  Se escribía el nombre, salía la lista y había que soltar el teclado y coger
  el ratón para entrar. Con la lista abierta, Intro entra en la primera —que
  ahora es además la que más dinero mueve— y las flechas recorren.
*/
const resaltado = ref(-1)

function mueve(r) {
  return Number(r.recibido ?? 0) + Number(r.pagado ?? 0)
}

function mover(paso) {
  if (!resultados.value.length) return
  const n = resultados.value.length
  resaltado.value = (resaltado.value + paso + n) % n
}

function abrirResaltado() {
  const r = resultados.value[resaltado.value >= 0 ? resaltado.value : 0]
  if (r) elegir(r.id)
}

watch(consulta, (q) => {
  resaltado.value = -1
  clearTimeout(temporizador)
  if (q.trim().length < 3) {
    resultados.value = []
    return
  }
  temporizador = setTimeout(async () => {
    buscando.value = true
    try {
      const r = await buscarTodo(q.trim())
      resultados.value = r.results ?? []
      soloIndice.value = r.soloIndice ?? 0
    } finally {
      buscando.value = false
      esDemo.value = estado.esDemo
    }
  }, 250)
})

async function abrir(id) {
  cargando.value = true
  error.value = ''
  try {
    const [ficha, red] = await Promise.all([pedirEntidad(id), vecinos(id, profundidad.value)])
    seleccionado.value = ficha
    seleccionId.value = id
    datos.value = red
    resultados.value = []
    consulta.value = ''
    vista.value = 'vecindario'
  } catch (e) {
    error.value = e.message || 'no se pudo cargar la entidad'
  } finally {
    cargando.value = false
    esDemo.value = estado.esDemo
  }
}

/**
 * Qué pasa al elegir un resultado de la búsqueda.
 *
 * Con el mapa cargado se abre la ficha de influencia, no el vecindario: quien
 * busca «mi ayuntamiento» quiere saber a quién le paga, y lo que le salía era
 * una ego-red de expedientes con la que no se puede contestar eso.
 */
function elegir(id) {
  const fila = resultados.value.find((r) => r.id === id)
  resultados.value = []
  consulta.value = ''
  // Una entidad que sólo está en el índice no tiene red que dibujar. Se abre
  // su ficha igual, con lo que sí se sabe de ella, y diciéndolo.
  fueraDelMapa.value = fila?.soloIndice ? fila : null
  if (fila?.soloIndice) {
    seleccionId.value = id
    vista.value = 'ficha'
    return Promise.resolve()
  }
  return hayMapa.value ? enfocar(id) : abrir(id)
}

/**
 * Selección sin recargar el grafo: sólo cambia el foco y la ficha.
 *
 * Si la entidad no está en el grafo publicado —pasa desde que los rankings
 * salen del índice, que cubre toda la base— se abre su ficha con las cifras
 * que sí hay. Antes el clic llevaba a un panel vacío que decía «Pulsa una
 * entidad del mapa», que parece un fallo de la web.
 */
async function enfocar(id) {
  seleccionId.value = id
  fueraDelMapa.value = null

  if (hayMapa.value && !idsDelMapa.value.has(id)) {
    fueraDelMapa.value =
      (indice.value?.entidades ?? []).find((e) => e.id === id) ??
      indiceCargado()?.entidades?.find((e) => e.id === id) ??
      null
    if (fueraDelMapa.value) {
      vista.value = 'ficha'
      return
    }
  }
  // Con el mapa cargado, pulsar una entidad abre su ficha de influencia: es la
  // pregunta que trae a la gente («¿quién financia esto?»), y contestarla con
  // otra maraña de nodos era justo lo que no se entendía.
  if (hayMapa.value) vista.value = 'ficha'
  try {
    seleccionado.value = await pedirEntidad(id)
  } catch {
    // Si la ficha no carga, al menos se conserva lo que ya hay en el grafo.
    seleccionado.value =
      datos.value.nodes.find((n) => n.id === id) ??
      grafoEntero.value?.nodes.find((n) => n.id === id) ??
      null
  }
}

function verMapa() {
  mapaPedido.value = true
  vista.value = 'mapa'
}

function volverAlMapa() {
  vista.value = 'portada'
  seleccionId.value = ''
  seleccionado.value = null
  fueraDelMapa.value = null
}

/** De la ficha al vecindario crudo: conexiones una a una y procedencia. */
function verProcedencia() {
  if (seleccionId.value) abrir(seleccionId.value)
}

/* -------------------------------------------------------------------------
   El estado de la vista, en la URL.

   Toda la web vivía en la misma dirección: daba igual dónde estuvieras, la
   barra del navegador decía lo mismo. En un proyecto cuyo sentido es que
   alguien encuentre algo y se lo pase a otro, eso quiere decir que lo único
   que se puede mandar es una captura de pantalla. Y además el botón de atrás
   salía de la web, y recargar te devolvía a la portada.
   ------------------------------------------------------------------------- */

/** La clave estable de una entidad; el UUID sólo como último recurso. */
function claveDe(nodo) {
  return nodo?.clave || nodo?.id || ''
}

function nodoDeClave(clave) {
  if (!clave) return null
  const enGrafo = (grafoEntero.value?.nodes ?? []).find((n) => claveDe(n) === clave)
  if (enGrafo) return enGrafo
  const enIndice =
    (indice.value?.entidades ?? []).find((e) => claveDe(e) === clave) ??
    indiceCargado()?.entidades?.find((e) => claveDe(e) === clave)
  return enIndice ?? null
}

const claveSeleccionada = computed(() => {
  if (!seleccionId.value) return ''
  const n =
    (grafoEntero.value?.nodes ?? []).find((x) => x.id === seleccionId.value) ??
    fueraDelMapa.value ??
    seleccionado.value
  return claveDe(n) || seleccionId.value
})

const estadoDeVista = computed(() => ({ vista: vista.value, clave: claveSeleccionada.value }))

/** Evita apilar una entrada de historial por el estado que acabamos de leer. */
let estadoPintado = { vista: 'portada', clave: '' }
let restaurando = false

watch(estadoDeVista, (ahora) => {
  if (restaurando || arrancando.value) return
  if (mismoEstado(ahora, estadoPintado)) return
  estadoPintado = { ...ahora }
  history.pushState({ ...ahora }, '', direccionDeVista(ahora, location.pathname))
})

async function irAEstado({ vista: v, clave }) {
  restaurando = true
  try {
    const nodo = clave ? nodoDeClave(clave) : null
    // El reparto está en `enlace.js` y tiene tests: el orden de estas
    // comprobaciones ya se equivocó una vez —`?v=mapa` no lleva entidad y
    // caía en la rama de enlace roto— sin que nada lo dijera.
    switch (accionDeEstado({ vista: v, clave }, Boolean(nodo))) {
      case 'mapa':
        verMapa()
        return
      case 'portada':
        volverAlMapa()
        return
      case 'vecindario':
        await abrir(nodo.id)
        return
      default:
        await enfocar(nodo.id)
    }
  } finally {
    estadoPintado = { vista: vista.value, clave: claveSeleccionada.value }
    restaurando = false
  }
}

function alVolverAtras(e) {
  irAEstado(e.state ?? vistaDeParametros(location.search))
}

watch(profundidad, () => {
  if (seleccionId.value && vista.value === 'vecindario') abrir(seleccionId.value)
})

onMounted(async () => {
  // Cuatro situaciones que se ven igual si no preguntas: API con datos, API
  // con la base vacía, instantánea estática, o nada. Distinguirlas evita que
  // "no se ve nada" signifique cuatro cosas distintas.
  const srv = await estadoServidor()
  if (srv.conectada && !srv.vacia) {
    arrancando.value = false
    return // hay API viva: se espera una búsqueda
  }
  baseVacia.value = srv.conectada && srv.vacia

  const estatico = await cargarInstantanea()
  arrancando.value = false

  if (estatico) {
    instantanea.value = estado.instantanea
    grafoEntero.value = grafoCompleto()
    vista.value = 'portada'
    // La portada rankea sobre el EXTRACTO del índice, no sobre el índice
    // entero: las listas necesitan las cabezas, no las cuarenta mil filas. El
    // completo se pide sólo cuando alguien busca. Sin bloquear: el mapa y las
    // listas del grafo ya se ven mientras llega.
    cargarIndiceTop().then((i) => {
      indice.value = i
    })

    // Y si la dirección pedía algo concreto, se va allí. Después de tener el
    // grafo: hace falta para resolver la clave.
    const pedido = vistaDeParametros(location.search)
    if (pedido.vista !== 'portada') await irAEstado(pedido)
    estadoPintado = { vista: vista.value, clave: claveSeleccionada.value }
    history.replaceState({ ...estadoPintado }, '', direccionDeVista(estadoPintado, location.pathname))
  } else {
    await abrir(ENTIDAD_INICIAL) // demostración, y se anuncia como tal
  }
  window.addEventListener('popstate', alVolverAtras)
})

onBeforeUnmount(() => window.removeEventListener('popstate', alVolverAtras))
</script>

<template>
  <div class="app" :class="{ desplaza: vista === 'portada' }">
    <!--
      El aviso es permanente y no se puede cerrar mientras se estén enseñando
      datos que no vienen de una fuente real. Publicar un mapa de dinero
      público con datos inventados sin decirlo sería lo contrario de lo que
      este proyecto pretende.
    -->
    <!--
      Antes esto era un párrafo de cuatro líneas fijo en lo alto de TODAS las
      vistas. En móvil se comía la primera pantalla entera: antes de ver un
      solo dato había que leer las advertencias. Y la advertencia que de
      verdad importa —que hoy ha fallado una fuente y por eso falta media
      España— quedaba enterrada entre las que no cambian nunca.
      Ahora: una línea con lo imprescindible, el aviso de fuente caída aparte
      y siempre visible, y el resto a un clic.
    -->
    <div v-if="instantanea && !esDemo" class="banda-info">
      <div class="banda-linea">
        <span class="banda-dicho">
          <strong>Instantánea del {{ new Date(instantanea.generado).toLocaleDateString('es-ES') }}</strong>
          · no es una consulta en vivo
        </span>
        <details class="banda-mas">
          <summary>De dónde salen estos datos</summary>
          <div class="banda-detalle">
            <p>
              Datos reales de
              {{ (instantanea.fuentesConDatos ?? instantanea.fuentes).map((f) => f.name).join(', ') }},
              descargados y enlazados por la ingesta automática. Cada cifra
              lleva el documento del que salió.
            </p>
            <p v-if="instantanea.truncado">
              El mapa se recorta a la parte con más dinero para que el
              navegador pueda con él. La base entera tiene
              {{ instantanea.total }} entidades y la búsqueda las cubre todas.
            </p>
          </div>
        </details>
      </div>
      <p v-if="instantanea.fuentesSinDatos?.length" class="fuente-caida">
        ⚠ Hoy falta {{ instantanea.fuentesSinDatos.map((f) => f.name).join(' y ') }}:
        no respondió al generar esta instantánea, así que este mapa no incluye
        sus datos.
      </p>
    </div>

    <div v-else-if="esDemo" class="banda-demo">
      <strong>Datos de demostración.</strong>
      Ninguna entidad mostrada es real: los nombres son ficticios y las cifras
      inventadas.
      <span v-if="baseVacia">
        La base de datos está conectada pero todavía vacía: falta la primera
        ingesta.
      </span>
      <span v-else>Aún no hay ninguna base de datos conectada.</span>
      <a href="https://github.com/AlejandroLayos/PoliticalRelationships" target="_blank" rel="noopener">
        Cómo conectar datos reales
      </a>
    </div>

    <header class="cabecera">
      <div class="marca">
        <h1>Sinapsis</h1>
        <p>Financiación e influencia en la política española</p>
      </div>

      <div class="buscador">
        <input
          v-model="consulta"
          type="search"
          placeholder="Busca tu ayuntamiento, una empresa o un partido…"
          aria-label="Buscar entidad"
          :aria-activedescendant="resaltado >= 0 ? `sug-${resaltado}` : undefined"
          @keydown.down.prevent="mover(1)"
          @keydown.up.prevent="mover(-1)"
          @keydown.enter.prevent="abrirResaltado"
          @keydown.esc="resultados = []"
        />
        <ul v-if="resultados.length" class="sugerencias">
          <li v-for="(r, i) in resultados" :id="`sug-${i}`" :key="r.id">
            <button :class="{ resaltada: i === resaltado }" @click="elegir(r.id)">
              <span class="punto" :style="{ background: COLOR_POR_ESQUEMA[r.schema] ?? COLOR_POR_DEFECTO }" />
              <span class="nombre">{{ r.caption }}</span>
              <!--
                La cifra, aquí. Sin ella, buscar «ayuntamiento de» devuelve
                cuarenta nombres casi iguales y hay que abrirlos uno a uno
                para saber cuál es el que mueve dinero.
              -->
              <span v-if="mueve(r)" class="mueve">{{ dineroCorto(mueve(r)) }}</span>
              <span class="tipo">
                {{ NOMBRE_ESQUEMA[r.schema] ?? r.schema }}
                <!--
                  «Sin red» va aquí y en gris, no en un recuadro ámbar al lado
                  del nombre. Era lo más llamativo de cada fila y no es una
                  advertencia: es un matiz sobre lo que se puede enseñar.
                -->
                <template v-if="r.soloIndice">· sin red</template>
              </span>
            </button>
          </li>
          <!--
            El índice cubre toda la base; el mapa, sólo lo que cabe. Quien
            busca su ayuntamiento y lo encuentra marcado «sin red» tiene que
            entender por qué, o pensará que la web está rota.
          -->
          <li v-if="soloIndice" class="pie-sugerencias">
            {{ soloIndice }} {{ soloIndice === 1 ? 'consta' : 'constan' }} en la base
            pero fuera del mapa publicado: de
            {{ soloIndice === 1 ? 'ese' : 'esos' }} sólo hay cifras, no red.
          </li>
        </ul>
        <p v-if="consulta.trim().length >= 3 && !buscando && !resultados.length" class="sin-resultados">
          Sin resultados en lo ingerido hasta hoy.
        </p>
      </div>

      <div v-if="hayMapa" class="controles">
        <button v-if="vista !== 'portada'" class="volver" @click="volverAlMapa">
          ← Portada
        </button>
        <button v-if="vista !== 'mapa'" class="volver" @click="verMapa">
          <!-- En estrecho no caben las tres etiquetas largas en un renglón. -->
          <span class="ancho">Mapa de núcleos</span>
          <span class="estrecho">Núcleos</span>
        </button>

        <!--
          Sin red que enseñar no hay vecindario al que bajar: pulsarlo daría
          «entidad no encontrada», que parece un fallo de la web y es
          exactamente lo contrario de lo que pasa.
        -->
        <button
          v-if="vista === 'ficha' && !fueraDelMapa"
          class="volver"
          title="La red alrededor de esta entidad y el documento del que sale cada dato"
          @click="verProcedencia"
        >
          <!--
            «Conexiones y procedencia» no cabía junto a los otros dos botones y
            se llevaba un renglón entero de la cabecera en móvil. La vista
            lleva su propio título dentro.
          -->
          Conexiones
        </button>

        <!--
          Cinco controles en fila, todos con el mismo peso y ninguno diciendo
          qué hace. «Desde» ¿desde cuándo? —era el importe—. «Relaciones
          sueltas» no significa nada si no sabes que el mapa esconde los
          grupos de menos de tres. Y no había forma de saber si estabas
          mirando el mapa entero o uno filtrado.

          Ahora van en dos grupos con su rótulo —lo que AÑADE al mapa y lo que
          lo RECORTA—, cada uno con su explicación al pasar por encima, y con
          un aviso aparte cuando hay algo puesto.
        -->
        <template v-if="vista === 'mapa'">
          <label class="control" title="Oculta las relaciones por debajo de este importe">
            Importe mínimo
            <select v-model.number="minImporte">
              <option v-for="e in ESCALONES" :key="e.v" :value="e.v">{{ e.t }}</option>
            </select>
          </label>

          <span class="grupo">
            <span class="rotulo">Añadir</span>
            <label
              class="control check"
              title="Dibuja también el expediente de contratación entre el órgano y la empresa. Por defecto se puentea: no es un actor, es el papel que los une."
            >
              <input v-model="mostrarExpedientes" type="checkbox" />
              expedientes
            </label>
            <label
              class="control check"
              title="Dibuja también los grupos de menos de tres entidades. Son parejas y tríos sueltos: mucho punto y poca estructura."
            >
              <input v-model="mostrarSueltos" type="checkbox" />
              grupos pequeños
            </label>
          </span>

          <span class="grupo">
            <span class="rotulo">Sólo</span>
            <label class="control check" title="Entidades no residentes y quien les paga">
              <input v-model="soloExtranjero" type="checkbox" />
              capital extranjero
            </label>
            <label class="control check" title="Formaciones políticas y quien les paga">
              <input v-model="soloPartidos" type="checkbox" />
              partidos
            </label>
          </span>
        </template>

        <label v-else-if="vista === 'vecindario'" class="control">
          Saltos
          <select v-model.number="profundidad">
            <option :value="1">1</option>
            <option :value="2">2</option>
            <option :value="3">3</option>
          </select>
        </label>
      </div>
    </header>

    <main>
      <div class="vista-grafo">
      <div class="lienzo-wrap">
        <!--
          El mapa no se desmonta al abrir una ficha: recalcular el layout de
          fuerzas de cuatro mil nodos tarda segundos, y volver atrás tiene que
          ser instantáneo o la gente deja de entrar a las fichas. Las demás
          vistas se dibujan ENCIMA.
        -->
        <MapaNucleos
          v-if="hayMapa && mapaPedido"
          :datos="grafoEntero"
          :seleccion="seleccionId"
          :nucleo-enfocado="nucleoEnfocado"
          :min-importe="minImporte"
          :mostrar-expedientes="mostrarExpedientes"
          :mostrar-sueltos="mostrarSueltos"
          :solo-extranjero="soloExtranjero"
          :solo-partidos="soloPartidos"
          @seleccionar="enfocar"
          @analizado="alAnalizar"
        />
        <FlujoDinero
          v-if="vista === 'ficha'"
          class="encima"
          :area="area"
          :fuera-del-mapa="fueraDelMapa"
          :nota="notaDeHueco"
          @seleccionar="enfocar"
        />
        <div v-else-if="vista === 'vecindario' || !hayMapa" class="encima">
          <GrafoRed
            :datos="datos"
            :seleccion="seleccionId"
            @seleccionar="enfocar"
            @expandir="abrir"
          />
        </div>

        <p v-if="arrancando || cargando" class="estado-flotante">Cargando…</p>
        <p v-else-if="error" class="estado-flotante error">{{ error }}</p>
        <p v-else-if="vista === 'vecindario' && !datos.nodes.length" class="estado-flotante">
          Busca una entidad para empezar.
        </p>

        <!--
          Un mapa filtrado y uno entero se ven igual de plausibles: el
          recuento baja y ya está. Si hay filtros puestos se dice, con el
          nombre de los que están, y con un botón para quitarlos — porque
          volver al mapa completo era acordarse de cuáles habías tocado.
        -->
        <p v-if="vista === 'mapa' && nucleos.length" class="recuento">
          {{ nucleos.length }} núcleos · {{ visiblesEnMapa }} entidades ·
          {{ dineroCorto(totalDinero) }} en juego
          <template v-if="filtrosPuestos.length">
            <br />
            <span class="filtrado">
              Filtrado por {{ filtrosPuestos.join(' y ') }}.
              <button class="quitar-filtros" @click="quitarFiltros">Ver el mapa entero</button>
            </span>
          </template>
        </p>
        <p v-else-if="vista === 'vecindario' && datos.truncated" class="recorte">
          Vista recortada por tamaño: hay más conexiones de las que se muestran.
        </p>

        <!--
          Cada entrada sólo si su color está en el dibujo. El morado se
          anunciaba siempre, hubiera o no una contraparte no residente, y una
          leyenda que nombra colores que no están obliga a buscarlos.
        -->
        <div v-if="vista === 'ficha'" class="leyenda">
          <span v-if="area?.recibeDe?.length"><i style="background: #4bb47f" />Dinero que entra</span>
          <span v-if="area?.pagaA?.length"><i style="background: #e8703a" />Dinero que sale</span>
          <span v-if="hayNoResidente"><i style="background: #b08cd9" />Contraparte no residente</span>
          <span>El grosor es el importe · la cifra exacta va escrita</span>
        </div>
        <!--
          Sólo los tipos que hay en pantalla. La leyenda enumeraba los siete
          esquemas siempre, incluidos «Persona» y «Cargo público», que nunca
          aparecen —las personas físicas no se publican (§12)—. Anunciar un
          color que no está obliga a buscarlo, y en este caso además sugería
          que la web publica personas.
        -->
        <div v-else-if="vista === 'vecindario'" class="leyenda">
          <span v-for="esquema in esquemasEnPantalla" :key="esquema">
            <i :style="{ background: COLOR_POR_ESQUEMA[esquema] ?? COLOR_POR_DEFECTO }" />
            {{ NOMBRE_ESQUEMA[esquema] ?? esquema }}
          </span>
          <span v-if="hayInferidas" class="leyenda-inferido">
            <i class="linea-inferida" />Conexión inferida (fina y ámbar)
          </span>
        </div>
        <div v-else class="leyenda">
          <!--
            El orden de lectura del mapa ES información y no lo decía nadie:
            los núcleos van empaquetados por filas de más a menos dinero, así
            que el de arriba a la izquierda es el que más mueve. Sin esa frase
            la colocación parece casual, y entonces el mapa entero parece un
            adorno.
          -->
          <span>
            De más a menos dinero, empezando arriba a la izquierda.
            En color, los núcleos de cabeza —los mismos de la lista—; en gris,
            el resto. El tamaño de cada punto es dinero, y los pagos de un
            núcleo a otro salen al pasar por encima.
          </span>
        </div>

        <p class="ayuda">
          {{
            vista === 'mapa'
              ? 'Clic en un nodo para abrir su ficha de influencia'
              : vista === 'ficha'
                ? 'Clic en una contraparte para seguir el rastro'
                : 'Clic para ver · doble clic para expandir'
          }}
        </p>
      </div>

      <PanelInfluencia
        v-if="vista === 'ficha'"
        :area="area"
        :crudo="grafoEntero"
        :fuentes="instantanea?.fuentes ?? []"
        :medios="medios"
        :fuera-del-mapa="fueraDelMapa"
        @seleccionar="enfocar"
        @volver="volverAlMapa"
      />
      <PanelEntidad
        v-else-if="seleccionado"
        :entidad="seleccionado"
        :datos="vista === 'mapa' ? grafoEntero : datos"
        @ir="enfocar"
        @expandir="abrir"
      />
      <PanelNucleos
        v-else-if="vista === 'mapa'"
        :nucleos="nucleos"
        :enfocado="nucleoEnfocado"
        @enfocar="(n) => (nucleoEnfocado = n)"
        @seleccionar="enfocar"
      />
      <PanelEntidad
        v-else
        :entidad="seleccionado"
        :datos="datos"
        @ir="enfocar"
        @expandir="abrir"
      />
      </div>

      <!--
        La portada va ENCIMA en vez de sustituir al resto: así el mapa, que
        tarda segundos en calcularse, no se desmonta cada vez que se vuelve.
      -->
      <Portada
        v-if="vista === 'portada' && hayMapa"
        class="portada-encima"
        :datos="grafoColapsado"
        :crudo="grafoEntero"
        :indice="indice"
        @seleccionar="enfocar"
        @ver-mapa="verMapa"
      />
    </main>
  </div>
</template>

<style scoped>
/*
  La portada desplaza el DOCUMENTO; el mapa no.

  Todo iba dentro de un `height: 100vh` con la portada haciendo scroll en un
  div suyo. En un ordenador se nota poco; en un móvil es media pantalla
  perdida. La barra de direcciones del navegador sólo se retrae cuando lo que
  se desplaza es el documento, así que se quedaba fija arriba todo el rato, y
  además `100vh` en iOS mide MÁS que lo visible: el final del div no se podía
  alcanzar ni desplazándolo del todo. Los últimos párrafos —de dónde salen los
  datos, qué no dice esta lista— quedaban bajo la barra, sin manera de leerlos.

  Tampoco funcionaba la barra espaciadora: el foco está en el `body`, que no
  tiene nada que desplazar, y la página no se movía.

  En el mapa sí hace falta alto fijo: el lienzo ocupa lo que queda y no debe
  crecer. Por eso la altura fija se quita sólo en la portada.
*/
.app { display: flex; flex-direction: column; height: 100vh; height: 100dvh; }
.app.desplaza { height: auto; min-height: 100vh; min-height: 100dvh; }
.app.desplaza main { position: static; flex: none; }
.app.desplaza .vista-grafo { display: none; }
.app.desplaza .portada-encima { position: static; }
.app.desplaza :deep(.portada) { height: auto; overflow: visible; }
/* Buscador y vuelta al mapa siempre a mano, aunque la página sea larga. */
.app.desplaza .cabecera { position: sticky; top: 0; z-index: 30; }

.banda-demo {
  background: var(--aviso-fondo); color: var(--aviso-texto);
  padding: 0.55rem 1rem; font-size: 0.82rem; line-height: 1.4;
  border-bottom: 1px solid var(--aviso-borde);
}
.banda-demo a { color: inherit; margin-left: 0.4rem; }

/*
  La banda ya no es azul marino. Con las superficies neutras del sistema, un
  azul saturado arriba del todo era lo más llamativo de la página y lo que
  dice es «esto es una instantánea»: información de contexto que no debe
  competir con el dato.
*/
.banda-info {
  background: var(--superficie); color: var(--tinta-3);
  padding: 0.4rem 1.25rem; font-size: var(--t-xs); line-height: 1.45;
  border-bottom: 1px solid var(--linea);
}
.banda-dicho strong { color: var(--tinta-2); }
.banda-mas summary { color: var(--tinta-2); }
.banda-linea {
  display: flex; align-items: baseline; gap: 0.75rem; flex-wrap: wrap;
}
.banda-dicho strong { font-weight: 600; }
.banda-mas summary {
  cursor: pointer; color: #8fb6d4; text-decoration: underline;
  text-underline-offset: 2px; font-size: 0.74rem;
}
.banda-mas summary::marker { color: #6d8ba4; }
.banda-detalle { padding: 0.4rem 0 0.2rem; max-width: 62ch; }
.banda-detalle p { margin: 0 0 0.35rem; }
.banda-detalle p:last-child { margin-bottom: 0; }

.cabecera {
  display: flex; align-items: center; gap: var(--e5); flex-wrap: wrap;
  padding: var(--e3) var(--e5); border-bottom: 1px solid var(--linea);
  background: var(--superficie);
}
.marca h1 { font-size: var(--t-l); margin: 0; letter-spacing: -0.02em; }
.marca p { font-size: var(--t-xs); color: var(--tinta-3); margin: 0.1rem 0 0; }

.buscador { position: relative; flex: 1; min-width: 240px; max-width: 480px; }
.buscador input {
  width: 100%; padding: 0.5rem 0.7rem; border-radius: 7px;
  border: 1px solid var(--borde); background: var(--fondo-boton); color: var(--texto); font-size: 0.9rem;
}
.buscador input:focus { outline: 2px solid var(--acento); outline-offset: -1px; }

.sugerencias {
  position: absolute; z-index: 20; top: calc(100% + 4px); left: 0; right: 0;
  list-style: none; margin: 0; padding: 0.25rem; max-height: 340px; overflow-y: auto;
  background: var(--fondo-panel); border: 1px solid var(--borde); border-radius: 8px;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.28);
}
.sugerencias button {
  display: flex; align-items: center; gap: 0.5rem; width: 100%; padding: 0.45rem 0.5rem;
  background: none; border: none; color: var(--texto); cursor: pointer; text-align: left; font: inherit;
  border-radius: 5px;
}
.sugerencias button:hover,
.sugerencias button.resaltada { background: var(--superficie-2); }
.sugerencias button.resaltada { box-shadow: inset 0 0 0 1px var(--serie-1); }
.punto { width: 8px; height: 8px; border-radius: 50%; flex: none; }
/*
  Dos renglones como mucho. «Área de Gobierno de Políticas Sociales, Familia e
  Igualdad del Ayuntamiento de Madrid» ocupaba CINCO en el desplegable, así
  que tres sugerencias llenaban la pantalla y no se podían comparar.
*/
.nombre {
  flex: 1; font-size: var(--t-m); min-width: 0; line-height: 1.3;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
}
.mueve {
  font-size: var(--t-s); color: var(--tinta); font-weight: 620;
  font-variant-numeric: tabular-nums; white-space: nowrap;
}
.tipo { font-size: var(--t-xs); color: var(--tinta-3); white-space: nowrap; }
.sin-resultados { position: absolute; top: calc(100% + 6px); font-size: 0.8rem; color: var(--texto-tenue); }
.pie-sugerencias {
  font-size: 0.7rem; color: var(--texto-tenue); line-height: 1.35;
  padding: 0.4rem 0.5rem; border-top: 1px solid var(--borde-suave); margin-top: 0.2rem;
}
.fuera {
  font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.05em;
  color: var(--aviso); border: 1px solid var(--aviso-borde); border-radius: 4px;
  padding: 0.05rem 0.28rem; white-space: nowrap;
}

.profundidad { font-size: 0.78rem; color: var(--texto-tenue); display: flex; align-items: center; gap: 0.4rem; }
.profundidad select {
  background: var(--fondo-boton); color: var(--texto);
  border: 1px solid var(--borde); border-radius: 5px; padding: 0.3rem 0.4rem;
}

main { flex: 1; position: relative; min-height: 0; }
.vista-grafo { position: absolute; inset: 0; display: grid; grid-template-columns: 1fr 340px; }
.portada-encima { position: absolute; inset: 0; background: var(--fondo); z-index: 5; }
.lienzo-wrap { position: relative; min-height: 0; }
.encima { position: absolute; inset: 0; background: var(--fondo-grafo); }

.estado-flotante {
  position: absolute; inset: 0; display: grid; place-items: center;
  color: var(--texto-tenue); font-size: 0.9rem; pointer-events: none; margin: 0;
}
.estado-flotante.error { color: var(--aviso); }

.recorte {
  position: absolute; top: 0.6rem; left: 50%; transform: translateX(-50%);
  background: var(--aviso-fondo); color: var(--aviso-texto);
  padding: 0.3rem 0.7rem; border-radius: 999px; font-size: 0.74rem; margin: 0;
}

.leyenda {
  position: absolute; bottom: 0.6rem; left: 0.7rem;
  display: flex; flex-wrap: wrap; gap: 0.55rem 0.9rem; max-width: 70%;
  font-size: 0.7rem; color: var(--texto-tenue);
}
.leyenda span { display: flex; align-items: center; gap: 0.3rem; }
.leyenda i { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.leyenda i.linea-inferida {
  width: 18px; height: 2px; border-radius: 1px;
  background: rgba(224, 163, 58, 0.75);
}

.ayuda { position: absolute; bottom: 0.6rem; right: 0.8rem; font-size: 0.7rem; color: var(--texto-tenue); margin: 0; }

@media (max-width: 820px) {
  .vista-grafo { grid-template-columns: 1fr; grid-template-rows: 55vh 1fr; }
  /*
    En estrecho la leyenda envolvía a tres líneas y se cruzaba con la ayuda de
    la esquina: dos textos superpuestos e ilegibles los dos. La ayuda sobra en
    táctil —no hay ratón que pasar por encima— y la leyenda se pone sobre
    fondo para no leerse encima del diagrama.
  */
  .ayuda { display: none; }
  .leyenda {
    max-width: calc(100% - 1.4rem);
    background: rgba(10, 14, 20, 0.85);
    padding: 0.3rem 0.45rem;
    border-radius: 6px;
  }
  .banda-info, .banda-demo { font-size: 0.72rem; padding: 0.35rem 0.7rem; }

  /*
    En estrecho la cabecera ocupaba cuatro renglones —marca, lema, buscador y
    una fila por cada botón— y empujaba el primer dato por debajo del pliegue.
    La marca y los botones comparten renglón, y el lema sobra: el buscador que
    hay justo debajo dice lo mismo con un ejemplo.
  */
  .cabecera { gap: 0.6rem 0.9rem; padding: 0.55rem 0.8rem; }
  .cabecera .marca { flex: 1; min-width: 0; }
  .marca p { display: none; }
  .buscador { order: 3; flex-basis: 100%; max-width: none; }
  .controles { gap: 0.5rem; }
  .volver, .controles .volver { padding: 0.3rem 0.6rem; font-size: 0.74rem; }
  .marca h1 { font-size: 0.98rem; }
}

.estrecho { display: none; }
@media (max-width: 820px) {
  .ancho { display: none; }
  .estrecho { display: inline; }
}

.controles { display: flex; align-items: center; gap: 0.9rem; flex-wrap: wrap; }
.grupo {
  display: flex; align-items: center; gap: 0.55rem;
  padding-left: 0.6rem; border-left: 1px solid var(--borde);
}
.rotulo {
  font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.07em;
  color: var(--texto-tenue);
}
.control { font-size: 0.78rem; color: var(--texto-tenue); display: flex; align-items: center; gap: 0.4rem; }
.control select {
  background: var(--fondo-boton); color: var(--texto);
  border: 1px solid var(--borde); border-radius: 6px; padding: 0.25rem 0.4rem; font: inherit;
}
.control.check { cursor: pointer; }
.volver {
  background: var(--fondo-boton); color: var(--texto); border: 1px solid var(--borde);
  border-radius: 6px; padding: 0.35rem 0.7rem; font: inherit; font-size: 0.78rem; cursor: pointer;
}
.volver:hover { border-color: var(--acento); }
.fuente-caida {
  display: block;
  margin-top: 0.3rem;
  color: #e8c37a;
}
.filtrado { color: var(--aviso); }
.quitar-filtros {
  background: none; border: none; padding: 0; margin-left: 0.3rem;
  color: var(--acento); font: inherit; cursor: pointer; text-decoration: underline;
  text-underline-offset: 2px;
}
.recuento {
  position: absolute; top: 0.6rem; left: 0.9rem; margin: 0;
  font-size: 0.75rem; color: var(--texto-tenue);
  background: rgba(10, 14, 20, 0.72); padding: 0.25rem 0.55rem; border-radius: 6px;
}
</style>
