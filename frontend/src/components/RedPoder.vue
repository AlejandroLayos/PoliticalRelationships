<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Graph from 'graphology'
import Sigma from 'sigma'
import EdgeCurveProgram from '@sigma/edge-curve'
import forceAtlas2 from 'graphology-layout-forceatlas2'
import { dibujarEtiquetaCentrada, dibujarEtiquetaConPlaca } from '../etiquetas.js'
import { aclarar, apagar, hexSobreFondo } from '../color.js'
import { semillaDePosicion } from '../vida.js'
import { fechaCorta, tramo } from '../cargos.js'
import {
  RELACIONES,
  buscarEnRed,
  camino,
  centroInicial,
  claseDe,
  conexionesDe,
  construirRed,
  egoRed,
  nombreDeFuente,
  redDeCamino,
  nombreDeTipo,
  capitalizar,
  puntosDeEntrada,
} from '../poder.js'

const props = defineProps({
  cargos: { type: Object, default: null },
  grafo: { type: Object, default: null },
  /** El nodo del centro, por su clave; '' para el de entrada. */
  nodo: { type: String, default: '' },
  /** El otro extremo de un camino desde el centro, o ''. */
  hasta: { type: String, default: '' },
  cargando: { type: Boolean, default: false },
})
const emit = defineEmits(['centrar', 'camino', 'ver-cargo', 'ver-entidad'])

/* --- Los datos ----------------------------------------------------------- */

const red = computed(() => (props.cargos ? construirRed(props.cargos, props.grafo) : null))
const centro = computed(() => {
  if (!red.value) return ''
  if (props.nodo && red.value.nodos.has(props.nodo)) return props.nodo
  return centroInicial(red.value, props.cargos)
})
/** Se pidió un nodo que esta edición no tiene: se dice, no se disimula. */
const perdido = computed(() => Boolean(red.value && props.nodo && !red.value.nodos.has(props.nodo)))
/** El camino hasta `hasta`, si se pidió y existe. */
const trayecto = computed(() =>
  red.value && centro.value && props.hasta && red.value.nodos.has(props.hasta)
    ? camino(red.value, centro.value, props.hasta)
    : null,
)
const ego = computed(() => {
  if (!red.value || !centro.value) return null
  if (trayecto.value) return { ...redDeCamino(red.value, trayecto.value), camino: true }
  return egoRed(red.value, centro.value)
})
/** Los pasos del camino, para leerlo: de un nodo al siguiente, con sus hechos. */
const pasos = computed(() => {
  const c = trayecto.value
  if (!c) return []
  return c.aristas.map((a, i) => {
    const de = c.nodos[i]
    const r = RELACIONES[a.relacion] ?? { ida: a.relacion, vuelta: a.relacion }
    return {
      de: red.value.nodos.get(de),
      a: red.value.nodos.get(c.nodos[i + 1]),
      como: a.source === de ? r.ida : r.vuelta,
      hechos: a.hechos,
    }
  })
})
const destino = computed(() => (props.hasta ? red.value?.nodos.get(props.hasta) ?? null : null))

const consultaCamino = ref('')
const resultadosCamino = computed(() =>
  red.value ? buscarEnRed(red.value, consultaCamino.value, 8).filter((n) => n.id !== centro.value) : [],
)
function buscarCamino(id) {
  consultaCamino.value = ''
  emit('camino', id)
}
const actual = computed(() => red.value?.nodos.get(centro.value) ?? null)
const conexiones = computed(() => (red.value && centro.value ? conexionesDe(red.value, centro.value) : []))
const entradas = computed(() => (red.value ? puntosDeEntrada(red.value) : null))

const consulta = ref('')
const resultados = computed(() => (red.value ? buscarEnRed(red.value, consulta.value, 10) : []))

/** Los grupos con muchas filas se abren a petición. */
const abiertos = ref(new Set())
const CORTE = 12
watch(centro, () => {
  abiertos.value = new Set()
})

/** El hilo que se va siguiendo: los últimos centros, para volver a ellos. */
const hilo = ref([])
watch(
  actual,
  (n) => {
    if (!n) return
    const resto = hilo.value.filter((x) => x.id !== n.id)
    hilo.value = [...resto, { id: n.id, nombre: n.nombre, tipo: n.tipo }].slice(-6)
  },
  { immediate: true },
)

function centrar(id) {
  consulta.value = ''
  emit('centrar', id)
}

function alBuscar(e) {
  if (e.key === 'Enter' && resultados.value.length) centrar(resultados.value[0].id)
  if (e.key === 'Escape') consulta.value = ''
}

/* Quien sale sólo por la CNMV no tiene cargos públicos: no hay ficha que abrir. */
const SIN_FICHA_DE_CARGOS = new Set(['accionista', 'consejero'])

function subtitulo(n) {
  if (!n) return ''
  if (n.tipo === 'persona') return n.cargo
  if (n.tipo === 'gobierno') return n.formacion ? `Formación del presidente: ${n.formacion}` : ''
  if (n.tipo === 'partido') return n.largo && n.largo !== n.nombre ? n.largo : ''
  if (n.tipo === 'entidad' && n.subtipo === 'organo') return 'Paga o contrata con dinero público'
  if (n.tipo === 'entidad' && n.cotizada)
    return n.sector
      ? `Sector según la CNMV: ${capitalizar(n.sector)}. Sus accionistas significativos, según la CNMV`
      : 'Sus accionistas significativos, según la CNMV'
  return ''
}

/* --- El dibujo ----------------------------------------------------------- */

/*
  Los colores son los de siempre (esquemas.js): la administración en teja, lo
  privado en azul, los partidos en verde. Las personas, en la tinta del visor:
  no son ninguno de los tres, y no gastan un cuarto color que no pasaría la
  prueba de daltonismo con los otros.
*/
const COLOR = {
  persona: '#ecebe6',
  adm: '#e5703d',
  emp: '#5d9ded',
  par: '#35b28c',
  neutro: '#7b7a80',
}
function colorDe(n) {
  return COLOR[claseDe(n)] ?? COLOR.neutro
}

const COLOR_ARISTA = {
  dinero: [233, 180, 76],
  autorizacion: [93, 157, 237],
  declaracion: [93, 157, 237],
  escano: [53, 178, 140],
  accionista: [93, 157, 237],
  preside: [229, 112, 61],
}

function recortar(t, max = 30) {
  if (!t || t.length <= max) return t ?? ''
  return `${t.slice(0, max - 1).trimEnd()}…`
}

const lienzo = ref(null)
let sigma = null
let grafo = null
let apuntado = ''
let vecinos = new Set()
let observador = null
let pendiente = false

const menosMovimiento =
  typeof window !== 'undefined' && Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches)

function construirGrafo(e) {
  const g = new Graph({ type: 'undirected', multi: false })
  if (e.camino) return grafoDeCamino(g, e)
  const directos = e.nodos.filter((n) => n.salto === 1)
  const segundos = e.nodos.filter((n) => n.salto === 2)
  for (const n of e.nodos) {
    // La semilla: el centro en medio y cada salto en su anillo. Da a
    // ForceAtlas2 un punto de partida que ya se parece a lo que es.
    let x = 0
    let y = 0
    if (n.salto > 0) {
      const lista = n.salto === 1 ? directos : segundos
      const i = lista.indexOf(n)
      const ang = (2 * Math.PI * i) / Math.max(1, lista.length) + semillaDePosicion(n.id).x * 0.02
      const radio = n.salto === 1 ? 10 : 20
      x = Math.cos(ang) * radio
      y = Math.sin(ang) * radio
    }
    const esCentro = n.salto === 0
    const base = n.tipo === 'persona' ? 5 + (n.rango ?? 1) * 0.8 : 6.5 + Math.min(8, Math.sqrt(n.grado ?? 1))
    // Con pocos nodos, todos con su nombre: una red de quince puntos sin
    // rótulos obliga a pasar el ratón por cada uno para saber quién es.
    const pocos = e.nodos.length <= 28
    g.addNode(n.id, {
      x,
      y,
      fixed: esCentro,
      size: esCentro ? 16 : n.salto === 2 ? base * 0.75 : base,
      color: n.salto === 2 ? hexSobreFondo(colorDe(n), 0.62) : colorDe(n),
      label: esCentro ? n.nombre : recortar(n.nombre),
      etiquetaReal: n.nombre,
      forceLabel: esCentro || pocos,
      zIndex: esCentro ? 2 : 1,
    })
  }
  for (const a of e.aristas) {
    if (g.hasEdge(a.source, a.target)) continue
    const rgb = COLOR_ARISTA[a.relacion] ?? [150, 160, 180]
    const fuerte = Boolean(COLOR_ARISTA[a.relacion])
    g.addEdge(a.source, a.target, {
      color: hexSobreFondo(`#${rgb.map((c) => c.toString(16).padStart(2, '0')).join('')}`, fuerte ? 0.7 : 0.28),
      size: (fuerte ? 1.6 : 0.9) + Math.min(2, Math.log2(a.hechos.length)),
      relacion: a.relacion,
      curvature: 0.12,
    })
  }
  if (g.order > 2) {
    forceAtlas2.assign(g, {
      iterations: 260,
      settings: {
        ...forceAtlas2.inferSettings(g),
        gravity: 1.2,
        scalingRatio: 9,
        adjustSizes: true,
        barnesHutOptimize: g.order > 150,
      },
    })
  }
  return g
}

/*
  Un camino se dibuja como lo que es, una cadena: de izquierda a derecha, en
  zigzag para que los rótulos no se pisen. Sin fuerzas: el orden es el dato.
*/
function grafoDeCamino(g, e) {
  e.nodos.forEach((n, i) => {
    const extremo = i === 0 || i === e.nodos.length - 1
    g.addNode(n.id, {
      x: i * 10,
      y: i % 2 ? -3 : 3,
      size: extremo ? 14 : 9,
      color: colorDe(n),
      label: n.nombre,
      etiquetaReal: n.nombre,
      forceLabel: true,
      zIndex: 2,
    })
  })
  for (const a of e.aristas) {
    if (g.hasEdge(a.source, a.target)) continue
    const rgb = COLOR_ARISTA[a.relacion] ?? [200, 205, 215]
    g.addEdge(a.source, a.target, {
      color: hexSobreFondo(`#${rgb.map((c) => c.toString(16).padStart(2, '0')).join('')}`, 0.85),
      size: 2.4,
      relacion: a.relacion,
      curvature: 0,
    })
  }
  return g
}

function reducirNodo(id, d) {
  if (!apuntado || !grafo?.hasNode(apuntado)) return d
  if (id === apuntado) return { ...d, label: d.etiquetaReal, forceLabel: true, color: aclarar(d.color, 0.3), zIndex: 3 }
  if (vecinos.has(id)) return { ...d, label: d.etiquetaReal, forceLabel: vecinos.size <= 14, zIndex: 2 }
  return { ...d, color: apagar(d.color, 0.8), label: '', forceLabel: false, zIndex: 0 }
}

function reducirArista(id, d) {
  if (!apuntado || !grafo) return d
  const [s, t] = grafo.extremities(id)
  if (s === apuntado || t === apuntado) return { ...d, color: aclarar(d.color, 0.6), size: d.size * 1.6, zIndex: 2 }
  return { ...d, color: apagar(d.color, 0.85), zIndex: 0 }
}

function pintar() {
  if (!lienzo.value || !ego.value) return
  if (!lienzo.value.clientWidth || !lienzo.value.clientHeight) {
    pendiente = true
    return
  }
  pendiente = false
  if (sigma) {
    sigma.kill()
    sigma = null
  }
  apuntado = ''
  vecinos = new Set()
  grafo = construirGrafo(ego.value)
  sigma = new Sigma(grafo, lienzo.value, {
    defaultEdgeType: 'curva',
    edgeProgramClasses: { curva: EdgeCurveProgram },
    labelDensity: 0.9,
    labelGridCellSize: 150,
    labelRenderedSizeThreshold: 7,
    labelFont: "'Public Sans Variable', system-ui, sans-serif",
    labelColor: { color: '#ecebe6' },
    labelSize: 12,
    labelWeight: '600',
    // En un camino, el rótulo debajo del nodo: a la derecha, el del último se
    // salía del lienzo y el de cada uno pisaba al siguiente.
    defaultDrawNodeLabel: ego.value.camino ? dibujarEtiquetaCentrada : dibujarEtiquetaConPlaca,
    defaultDrawNodeHover: ego.value.camino ? dibujarEtiquetaCentrada : dibujarEtiquetaConPlaca,
    nodeReducer: reducirNodo,
    edgeReducer: reducirArista,
    // Aire alrededor: arriba va el hilo recorrido y abajo la leyenda.
    stagePadding: 56,
    minCameraRatio: 0.1,
    maxCameraRatio: 6,
    zIndex: true,
  })
  sigma.on('enterNode', ({ node }) => {
    apuntado = node
    vecinos = new Set(grafo.neighbors(node))
    lienzo.value.style.cursor = 'pointer'
    sigma.refresh({ skipIndexation: true })
  })
  sigma.on('leaveNode', () => {
    apuntado = ''
    vecinos = new Set()
    lienzo.value.style.cursor = ''
    sigma.refresh({ skipIndexation: true })
  })
  sigma.on('clickNode', ({ node }) => {
    if (node !== centro.value) centrar(node)
  })
  if (!menosMovimiento) {
    // Una entrada corta de cámara: se ve que el centro ha cambiado.
    sigma.getCamera().setState({ ratio: 1.25 })
    sigma.getCamera().animate({ ratio: 1 }, { duration: 450 })
  }
}

watch(ego, () => nextTick(pintar))

onMounted(() => {
  observador = new ResizeObserver(() => {
    if (pendiente && lienzo.value?.clientWidth) pintar()
  })
  if (lienzo.value) observador.observe(lienzo.value)
  pintar()
})

onBeforeUnmount(() => {
  observador?.disconnect()
  sigma?.kill()
})

/* --- El panel ------------------------------------------------------------ */

function visibles(g) {
  const k = `${g.relacion}|${g.sentido}`
  return abiertos.value.has(k) ? g.items : g.items.slice(0, CORTE)
}
function abrirGrupo(g) {
  const s = new Set(abiertos.value)
  s.add(`${g.relacion}|${g.sentido}`)
  abiertos.value = s
}
const totalConexiones = computed(() => conexiones.value.reduce((n, g) => n + g.items.length, 0))
</script>

<template>
  <section class="poder">
    <header class="poder-cabeza">
      <div class="que-es">
        <p class="antetitulo">
          <button type="button" class="volver-radiografia" @click="emit('centrar', '')">← Radiografía del poder</button>
          · Red de poder
        </p>
        <h1 class="titulo">Quién está unido a quién, y quién lo dice</h1>
        <p class="entradilla">
          Cada línea es un hecho de una fuente oficial: un nombramiento en el BOE, un escaño, una
          autorización de la Oficina de Conflictos de Intereses, una actividad declarada al Congreso,
          una participación significativa registrada en la CNMV.
          Pulsa un nodo para ponerlo en el centro.
        </p>
      </div>
      <div class="buscar">
        <label class="antetitulo" for="buscar-red">Buscar en la red</label>
        <input
          id="buscar-red"
          v-model="consulta"
          type="search"
          autocomplete="off"
          placeholder="Una persona, un ministerio, un partido, una empresa…"
          :disabled="!red"
          @keydown="alBuscar"
        />
        <ul v-if="consulta.trim().length >= 2" class="resultados" role="listbox">
          <li v-for="r in resultados" :key="r.id">
            <button type="button" @click="centrar(r.id)">
              <span class="punto" :class="`k-${claseDe(r)}`" />
              <span class="r-nombre">{{ r.nombre }}</span>
              <span class="r-tipo">{{ nombreDeTipo(r) }}</span>
            </button>
          </li>
          <li v-if="!resultados.length" class="sin">Nada con ese nombre en la red.</li>
        </ul>
      </div>
    </header>

    <nav v-if="entradas" class="entradas" aria-label="Por dónde empezar">
      <div class="fila">
        <span class="rotulo">Gobiernos</span>
        <button v-for="g in entradas.gobiernos" :key="g.id" type="button" class="chip k-adm" @click="centrar(g.id)">
          {{ g.nombre.replace('Gobierno de ', '') }}
        </button>
      </div>
      <div v-if="entradas.cotizadas.length" class="fila">
        <span class="rotulo">Cotizadas</span>
        <button v-for="c in entradas.cotizadas" :key="c.id" type="button" class="chip" :class="`k-${claseDe(c)}`" @click="centrar(c.id)">
          {{ c.nombre }} <span class="n">{{ c.accionistas }}</span>
        </button>
      </div>
      <div v-if="entradas.medios.length" class="fila">
        <span class="rotulo">Medios</span>
        <button v-for="m in entradas.medios" :key="m.id" type="button" class="chip" :class="`k-${claseDe(m)}`" @click="centrar(m.id)">
          {{ m.nombre }} <span class="n">{{ m.accionistas }}</span>
        </button>
      </div>
      <div v-if="entradas.justicia.length" class="fila">
        <span class="rotulo">Justicia</span>
        <button v-for="j in entradas.justicia" :key="j.id" type="button" class="chip k-adm" @click="centrar(j.id)">
          {{ j.nombre }}
        </button>
      </div>
      <div class="fila">
        <span class="rotulo">Partidos</span>
        <button v-for="p in entradas.partidos" :key="p.id" type="button" class="chip k-par" @click="centrar(p.id)">
          {{ p.nombre }}
        </button>
      </div>
      <div v-if="entradas.entidades.length" class="fila">
        <span class="rotulo">Con más cargos unidos</span>
        <button v-for="e in entradas.entidades" :key="e.id" type="button" class="chip" :class="`k-${claseDe(e)}`" @click="centrar(e.id)">
          {{ e.nombre }} <span class="n">{{ e.personas }}</span>
        </button>
      </div>
    </nav>

    <p v-if="!red" class="estado">{{ cargando ? 'Cargando la red…' : 'Esta edición no trae cargos públicos.' }}</p>

    <div v-else class="cuerpo">
      <div class="visor lienzo-caja">
        <div ref="lienzo" class="lienzo" />
        <ol v-if="hilo.length > 1" class="hilo" aria-label="Lo que has recorrido">
          <li v-for="h in hilo" :key="h.id">
            <button type="button" :aria-current="h.id === centro ? 'true' : undefined" @click="centrar(h.id)">
              {{ recortar(h.nombre, 26) }}
            </button>
          </li>
        </ol>
        <ul class="leyenda" aria-label="Leyenda">
          <li><span class="punto k-persona" />Persona</li>
          <li><span class="punto k-adm" />Administración</li>
          <li><span class="punto k-emp" />Empresa</li>
          <li><span class="punto k-par" />Partido, asociación o fundación</li>
          <li><span class="raya dinero" />Dinero</li>
        </ul>
        <p v-if="ego?.ocultos" class="caben">
          En el dibujo caben {{ ego.nodos.length - 1 }}; las {{ ego.ocultos.toLocaleString('es-ES') }} conexiones
          restantes están en la lista.
        </p>
      </div>

      <aside v-if="actual" class="panel" aria-live="polite">
        <p v-if="perdido" class="aviso">Lo que pedía el enlace no está en esta edición; se abre la red por el principio.</p>
        <p class="antetitulo" :class="`c-${claseDe(actual)}`">{{ nombreDeTipo(actual) }}</p>
        <h2 class="nombre">{{ actual.nombre }}</h2>
        <p v-if="subtitulo(actual)" class="sub">{{ subtitulo(actual) }}</p>
        <div class="acciones">
          <button v-if="actual.tipo === 'persona' && !SIN_FICHA_DE_CARGOS.has(actual.papel)" type="button" @click="emit('ver-cargo', actual.id)">Ficha de sus cargos →</button>
          <button v-if="actual.entidad" type="button" @click="emit('ver-entidad', actual.entidad)">Su dinero en el mapa →</button>
          <button
            v-if="actual.tipo === 'gobierno' && red.nodos.has(actual.presidente)"
            type="button"
            @click="centrar(actual.presidente)"
          >Presidencia →</button>
        </div>
        <p class="nota">
          Cada línea es un hecho publicado por la fuente que se cita. Dos personas cerca en el dibujo no
          tienen por eso relación entre sí: comparten el nodo que las une, y nada más.
        </p>

        <!-- El camino hasta otro nodo: una cadena de hechos, no una relación. -->
        <section class="camino">
          <label class="antetitulo" for="buscar-camino">¿Cómo se une con…?</label>
          <input
            id="buscar-camino"
            v-model="consultaCamino"
            type="search"
            autocomplete="off"
            placeholder="Otra persona, entidad, partido…"
            @keydown.enter="resultadosCamino.length && buscarCamino(resultadosCamino[0].id)"
          />
          <ul v-if="consultaCamino.trim().length >= 2" class="resultados-camino">
            <li v-for="r in resultadosCamino" :key="r.id">
              <button type="button" @click="buscarCamino(r.id)">
                <span class="punto" :class="`k-${claseDe(r)}`" /> {{ r.nombre }}
              </button>
            </li>
            <li v-if="!resultadosCamino.length" class="sin">Nada con ese nombre en la red.</li>
          </ul>
          <template v-if="hasta && destino">
            <p v-if="!trayecto" class="aviso">
              No hay camino de menos de seis pasos entre {{ actual.nombre }} y {{ destino.nombre }}.
            </p>
            <template v-else>
              <p class="nota">
                Un camino es una cadena de hechos, cada uno con su fuente. Que exista no dice que
                {{ actual.nombre }} y {{ destino.nombre }} tengan relación entre sí.
              </p>
              <ol class="pasos">
                <li v-for="(p, i) in pasos" :key="i">
                  <button type="button" class="otro" @click="centrar(p.de.id)">
                    <span class="punto" :class="`k-${claseDe(p.de)}`" /> {{ p.de.nombre }}
                  </button>
                  <p class="como">{{ p.como }}</p>
                  <ul class="hechos">
                    <li v-for="(h, j) in p.hechos.slice(0, 2)" :key="j">
                      <span class="texto">{{ h.texto }}</span>
                      <span v-if="tramo(h)" class="cuando">{{ tramo(h) }}</span>
                      <a v-if="h.url" :href="h.url" target="_blank" rel="noopener" class="fuente">{{ nombreDeFuente(h.fuente) }}</a>
                      <span v-else class="fuente">{{ nombreDeFuente(h.fuente) }}</span>
                    </li>
                  </ul>
                  <button v-if="i === pasos.length - 1" type="button" class="otro" @click="centrar(p.a.id)">
                    <span class="punto" :class="`k-${claseDe(p.a)}`" /> {{ p.a.nombre }}
                  </button>
                </li>
              </ol>
            </template>
            <button type="button" class="ver-todos" @click="emit('camino', '')">Quitar el camino</button>
          </template>
        </section>

        <p class="recuento">{{ totalConexiones.toLocaleString('es-ES') }} conexiones</p>
        <section v-for="g in conexiones" :key="`${g.relacion}|${g.sentido}`" class="grupo">
          <h3>
            {{ g.titulo }}<template v-if="g.relacion === 'nombramiento' && g.sentido === 'ida'"> Gobierno de…</template>
            <span class="n">{{ g.items.length.toLocaleString('es-ES') }}</span>
          </h3>
          <ul>
            <li v-for="it in visibles(g)" :key="it.nodo.id">
              <button type="button" class="otro" @click="centrar(it.nodo.id)">
                <span class="punto" :class="`k-${claseDe(it.nodo)}`" />
                {{ g.relacion === 'nombramiento' && g.sentido === 'ida' ? it.nodo.nombre.replace('Gobierno de ', '') : it.nodo.nombre }}
              </button>
              <ul class="hechos">
                <li v-for="(h, i) in it.hechos.slice(0, 3)" :key="i">
                  <span class="texto">{{ h.texto }}</span>
                  <span v-if="tramo(h)" class="cuando">{{ tramo(h) }}</span>
                  <span v-if="h.registro" class="cuando" title="Fecha en que la CNMV registró la última notificación; no es la de compra">registro {{ fechaCorta(h.registro) }}</span>
                  <span v-if="h.cruce" class="cuando" title="Por qué se da por la misma persona">unido por {{ h.cruce }}</span>
                  <a v-if="h.url" :href="h.url" target="_blank" rel="noopener" class="fuente">{{ nombreDeFuente(h.fuente) }}</a>
                  <span v-else class="fuente">{{ nombreDeFuente(h.fuente) }}</span>
                </li>
                <li v-if="it.hechos.length > 3" class="mas">y {{ it.hechos.length - 3 }} más</li>
              </ul>
            </li>
          </ul>
          <button v-if="g.items.length > CORTE && visibles(g).length < g.items.length" type="button" class="ver-todos" @click="abrirGrupo(g)">
            Ver los {{ g.items.length.toLocaleString('es-ES') }}
          </button>
        </section>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.volver-radiografia { all: unset; cursor: pointer; text-decoration: underline; text-underline-offset: 2px; }
.volver-radiografia:hover, .volver-radiografia:focus-visible { color: var(--tinta); }
.poder {
  height: 100%;
  overflow-y: auto;
  padding: var(--e5) var(--e5) var(--e7);
}
.poder > * { max-width: 90rem; margin-left: auto; margin-right: auto; }

.poder-cabeza {
  display: grid;
  gap: var(--e4) var(--e7);
  grid-template-columns: minmax(0, 1fr) minmax(16rem, 26rem);
  align-items: end;
}
.titulo {
  font-size: var(--t-h2); line-height: 1.15; letter-spacing: -0.012em;
  font-weight: 600; margin: 0;
}
.entradilla {
  font-family: var(--serif); font-size: var(--t-m); line-height: 1.5;
  color: var(--tinta-2); margin: var(--e3) 0 0; max-width: 60ch;
}

.buscar { position: relative; }
.buscar input {
  width: 100%; box-sizing: border-box;
  font: inherit; font-size: var(--t-m);
  padding: var(--e2) var(--e3);
  background: var(--hoja); color: var(--tinta);
  border: 1px solid var(--filete-medio); border-radius: var(--radio);
}
.resultados {
  position: absolute; z-index: 10; left: 0; right: 0; top: 100%;
  list-style: none; margin: 2px 0 0; padding: var(--e1) 0;
  background: var(--hoja); border: 1px solid var(--filete-medio); border-radius: var(--radio);
  box-shadow: 0 6px 24px rgb(0 0 0 / 0.12);
  max-height: 22rem; overflow-y: auto;
}
.resultados button {
  display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: var(--e2);
  align-items: center; width: 100%; text-align: left;
  padding: var(--e2) var(--e3); border: 0; background: none; color: var(--tinta);
  font: inherit; font-size: var(--t-s); cursor: pointer;
}
.resultados button:hover, .resultados button:focus-visible { background: var(--papel-2); }
.r-nombre { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.r-tipo { font-size: var(--t-xs); color: var(--tinta-3); }
.resultados .sin { padding: var(--e2) var(--e3); font-size: var(--t-s); color: var(--tinta-3); }

.entradas {
  margin-top: var(--e4); padding-top: var(--e3);
  border-top: 2px solid var(--filete);
  display: flex; flex-direction: column; gap: var(--e2);
}
.fila {
  display: flex; align-items: baseline; gap: var(--e2);
  /* Una línea por fila, que se desliza de lado: tres filas que se parten en
     seis dejaban el lienzo debajo del pliegue. */
  overflow-x: auto; white-space: nowrap; scrollbar-width: thin;
  padding-bottom: 2px;
}
.fila > * { flex: none; }
.rotulo {
  font-size: var(--t-xs); font-weight: 650; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--tinta-3); min-width: 12rem;
}
.chip {
  font: inherit; font-size: var(--t-s); color: var(--tinta);
  padding: 0.15rem var(--e2); cursor: pointer;
  background: var(--papel); border: 1px solid var(--filete-suave); border-left: 3px solid var(--neutro);
  border-radius: var(--radio-s);
}
.chip:hover, .chip:focus-visible { background: var(--papel-2); }
.chip.k-adm { border-left-color: var(--adm); }
.chip.k-par { border-left-color: var(--par); }
.chip.k-emp { border-left-color: var(--emp); }
.chip .n { font-family: var(--mono); font-size: var(--t-xs); color: var(--tinta-3); margin-left: 0.2rem; }

.estado { margin-top: var(--e6); color: var(--tinta-3); }

.cuerpo {
  margin-top: var(--e4);
  display: grid; gap: var(--e4);
  grid-template-columns: minmax(0, 1fr) minmax(20rem, 30rem);
  align-items: start;
}
.lienzo-caja {
  position: sticky; top: var(--e4);
  height: min(78vh, 52rem); min-height: 26rem;
  border-radius: var(--radio); overflow: hidden;
}
.lienzo { position: absolute; inset: 0; }

.hilo {
  position: absolute; left: var(--e3); top: var(--e3); right: var(--e3);
  display: flex; flex-wrap: wrap; gap: 0.1rem 0; list-style: none; margin: 0; padding: 0;
  font-size: var(--t-xs);
}
.hilo li + li::before { content: '›'; color: var(--tinta-3); margin: 0 0.35rem; }
.hilo button {
  font: inherit; border: 0; background: rgb(18 19 21 / 0.8); color: var(--tinta-2);
  padding: 0.1rem 0.3rem; border-radius: var(--radio-s); cursor: pointer;
}
.hilo button[aria-current='true'] { color: var(--tinta); font-weight: 650; }

.leyenda {
  position: absolute; left: var(--e3); bottom: var(--e3);
  display: flex; flex-wrap: wrap; gap: var(--e1) var(--e3);
  list-style: none; margin: 0; padding: var(--e1) var(--e2);
  background: rgb(18 19 21 / 0.8); border-radius: var(--radio-s);
  font-size: var(--t-xs); color: var(--tinta-2);
}
.leyenda li { display: flex; align-items: center; gap: 0.35rem; }
.caben {
  position: absolute; right: var(--e3); bottom: var(--e3); margin: 0; max-width: 18rem;
  font-size: var(--t-xs); color: var(--tinta-3); text-align: right;
  background: rgb(18 19 21 / 0.8); padding: var(--e1) var(--e2); border-radius: var(--radio-s);
}

.punto {
  display: inline-block; width: 0.6rem; height: 0.6rem; border-radius: 50%; flex: none;
  background: var(--neutro);
}
.punto.k-persona { background: var(--tinta); box-shadow: 0 0 0 1px var(--filete-medio); }
.punto.k-adm { background: var(--adm); }
.punto.k-par { background: var(--par); }
.punto.k-emp { background: var(--emp); }
.raya { display: inline-block; width: 1rem; height: 2px; background: #e9b44c; }

.panel {
  border-top: 3px solid var(--filete);
  padding-top: var(--e3);
}
.aviso { color: var(--aviso); font-size: var(--t-s); margin: 0 0 var(--e3); }
.c-persona { color: var(--tinta-2); }
.c-adm { color: var(--adm); }
.c-par { color: var(--par); }
.c-emp { color: var(--emp); }
.nombre {
  font-family: var(--serif); font-size: var(--t-h2); line-height: 1.15;
  font-weight: 600; margin: 0; color: var(--tinta);
}
.sub { margin: var(--e1) 0 0; color: var(--tinta-2); font-size: var(--t-s); }
.acciones { display: flex; flex-wrap: wrap; gap: var(--e2) var(--e4); margin-top: var(--e3); }
.acciones button {
  font: inherit; font-size: var(--t-s); font-weight: 600; color: var(--tinta);
  background: none; border: 0; border-bottom: 1px solid var(--filete-medio);
  padding: 0; cursor: pointer;
}
.panel .nota { margin-top: var(--e4); font-size: var(--t-s); }
.recuento {
  margin: var(--e4) 0 0; font-size: var(--t-xs); font-weight: 650;
  letter-spacing: 0.08em; text-transform: uppercase; color: var(--tinta-3);
}

.grupo { margin-top: var(--e4); border-top: 1px solid var(--filete-suave); padding-top: var(--e2); }
.grupo h3 {
  display: flex; justify-content: space-between; gap: var(--e3);
  font-size: var(--t-s); font-weight: 650; margin: 0 0 var(--e2); color: var(--tinta);
}
.grupo h3 .n { font-family: var(--mono); font-weight: 400; color: var(--tinta-3); }
.grupo > ul { list-style: none; margin: 0; padding: 0; }
.grupo > ul > li { padding: var(--e2) 0; border-bottom: 1px solid var(--filete-suave); }
.grupo > ul > li:last-child { border-bottom: 0; }
.otro {
  display: flex; align-items: center; gap: var(--e2);
  font: inherit; font-size: var(--t-m); font-weight: 600; text-align: left;
  color: var(--tinta); background: none; border: 0; padding: 0; cursor: pointer;
}
.otro:hover, .otro:focus-visible { text-decoration: underline; text-underline-offset: 0.18em; }
.hechos { list-style: none; margin: var(--e1) 0 0 1.1rem; padding: 0; }
.hechos li {
  font-size: var(--t-s); line-height: 1.45; color: var(--tinta-2);
  display: flex; flex-wrap: wrap; gap: 0 var(--e2);
}
.hechos .cuando { font-family: var(--mono); font-size: var(--t-xs); color: var(--tinta-3); }
.hechos .fuente { font-size: var(--t-xs); color: var(--tinta-3); }
.hechos a.fuente { color: var(--tinta-2); text-decoration: underline; text-underline-offset: 0.15em; }
.hechos .mas { color: var(--tinta-3); font-style: italic; }
.ver-todos {
  margin-top: var(--e2); font: inherit; font-size: var(--t-s); color: var(--tinta);
  background: var(--papel-2); border: 1px solid var(--filete-suave); border-radius: var(--radio-s);
  padding: var(--e1) var(--e3); cursor: pointer;
}

.camino { margin-top: var(--e4); border-top: 1px solid var(--filete-suave); padding-top: var(--e3); position: relative; }
.camino input {
  width: 100%; box-sizing: border-box; font: inherit; font-size: var(--t-s);
  padding: var(--e1) var(--e2); background: var(--hoja); color: var(--tinta);
  border: 1px solid var(--filete-medio); border-radius: var(--radio);
}
.resultados-camino { list-style: none; margin: var(--e1) 0 0; padding: 0; }
.resultados-camino button {
  display: flex; align-items: center; gap: var(--e2); width: 100%; text-align: left;
  font: inherit; font-size: var(--t-s); color: var(--tinta); background: none; border: 0;
  padding: var(--e1) 0; cursor: pointer;
}
.resultados-camino .sin { font-size: var(--t-s); color: var(--tinta-3); }
.pasos { list-style: none; margin: var(--e3) 0 0; padding: 0; border-left: 2px solid var(--filete-medio); }
.pasos > li { padding: 0 0 var(--e3) var(--e3); }
.como { margin: var(--e1) 0 0 1.1rem; font-size: var(--t-xs); font-weight: 650; letter-spacing: 0.06em; text-transform: uppercase; color: var(--tinta-3); }

@media (max-width: 60rem) {
  .poder { padding: var(--e4) var(--e4) var(--e7); }
  .poder-cabeza { grid-template-columns: minmax(0, 1fr); }
  .cuerpo { grid-template-columns: minmax(0, 1fr); }
  .lienzo-caja { position: relative; top: 0; height: 60vh; min-height: 20rem; }
  .rotulo { min-width: 0; }
  .caben { display: none; }
}
</style>
