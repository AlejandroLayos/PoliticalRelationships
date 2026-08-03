<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Graph from 'graphology'
import Sigma from 'sigma'
import forceAtlas2 from 'graphology-layout-forceatlas2'
import { COLOR_POR_ESQUEMA, COLOR_POR_DEFECTO } from '../esquemas.js'

const props = defineProps({
  datos: { type: Object, required: true },
  seleccion: { type: String, default: '' },
})
const emit = defineEmits(['seleccionar', 'expandir'])

const contenedor = ref(null)
let sigma = null
let grafo = null

/**
 * El tamaño del nodo crece con su grado: los nodos muy conectados son los que
 * interesan en un mapa de influencia, y así se ven sin tener que buscarlos.
 */
function tamano(grado) {
  return 5 + Math.min(14, Math.sqrt(grado) * 3.5)
}

function construir() {
  grafo = new Graph({ multi: false, type: 'undirected' })

  for (const n of props.datos.nodes ?? []) {
    if (grafo.hasNode(n.id)) continue
    grafo.addNode(n.id, {
      label: n.caption,
      esquema: n.schema,
      profundidad: n.depth ?? 0,
      color: COLOR_POR_ESQUEMA[n.schema] ?? COLOR_POR_DEFECTO,
      // Posición inicial aleatoria: ForceAtlas2 la reordena.
      x: Math.random(),
      y: Math.random(),
      size: 6,
    })
  }

  for (const a of props.datos.edges ?? []) {
    if (!grafo.hasNode(a.source) || !grafo.hasNode(a.target)) continue
    if (grafo.hasEdge(a.source, a.target)) continue
    const inferida = a.status === 'inferred'
    grafo.addEdge(a.source, a.target, {
      esquema: a.schema,
      confianza: a.confidence,
      estado: a.status,
      importe: a.amount,
      moneda: a.currency,
      // Lo inferido se dibuja fino y en un gris apagado; lo afirmado, más
      // grueso y azulado según su confianza. Nunca puede parecer lo mismo que
      // un hecho afirmado por la fuente.
      // (Sigma v3 no trae programa de línea discontinua, así que la distinción
      // va por color y grosor, no por trazo.)
      color: inferida
        ? 'rgba(224,163,58,0.45)'
        : `rgba(120,150,190,${0.3 + 0.5 * (a.confidence ?? 1)})`,
      size: inferida ? 0.8 : 1.2 + 2.2 * (a.confidence ?? 1),
    })
  }

  grafo.forEachNode((id) => {
    grafo.setNodeAttribute(id, 'size', tamano(grafo.degree(id)))
  })

  // ForceAtlas2 es lo que produce el aspecto orgánico de red neuronal. Se
  // ejecuta un número fijo de iteraciones en vez de en bucle: es una vista de
  // vecindario pequeña, no hace falta animación continua.
  if (grafo.order > 1) {
    forceAtlas2.assign(grafo, {
      iterations: 220,
      settings: {
        ...forceAtlas2.inferSettings(grafo),
        gravity: 1.4,
        scalingRatio: 12,
        barnesHutOptimize: grafo.order > 120,
      },
    })
  }
}

function pintar() {
  if (!contenedor.value) return
  if (sigma) {
    sigma.kill()
    sigma = null
  }
  construir()

  sigma = new Sigma(grafo, contenedor.value, {
    renderEdgeLabels: false,
    defaultEdgeType: 'line',
    labelDensity: 0.6,
    labelGridCellSize: 70,
    labelRenderedSizeThreshold: 7,
    minCameraRatio: 0.08,
    maxCameraRatio: 8,
  })

  sigma.on('clickNode', ({ node }) => emit('seleccionar', node))
  sigma.on('doubleClickNode', ({ node, event }) => {
    // Doble clic expande el vecindario desde ese nodo: es el gesto natural
    // para "sigue tirando del hilo".
    event.preventSigmaDefault()
    emit('expandir', node)
  })

  resaltar()
}

/** Atenúa lo que no toca al nodo seleccionado, para poder leer el vecindario. */
function resaltar() {
  if (!sigma || !grafo) return
  const foco = props.seleccion
  sigma.setSetting('nodeReducer', (id, datos) => {
    if (!foco || !grafo.hasNode(foco)) return datos
    if (id === foco) return { ...datos, highlighted: true, zIndex: 2 }
    if (grafo.areNeighbors(foco, id)) return { ...datos, zIndex: 1 }
    return { ...datos, color: 'rgba(160,165,180,0.28)', label: '', zIndex: 0 }
  })
  sigma.setSetting('edgeReducer', (id, datos) => {
    if (!foco || !grafo.hasNode(foco)) return datos
    const extremos = grafo.extremities(id)
    if (extremos.includes(foco)) return { ...datos, zIndex: 1 }
    return { ...datos, color: 'rgba(190,193,203,0.16)', zIndex: 0 }
  })
  sigma.refresh()
}

onMounted(pintar)
watch(() => props.datos, pintar, { deep: false })
watch(() => props.seleccion, resaltar)

onBeforeUnmount(() => {
  if (sigma) sigma.kill()
})
</script>

<template>
  <div ref="contenedor" class="lienzo" />
</template>

<style scoped>
.lienzo {
  width: 100%;
  height: 100%;
  background: var(--fondo-grafo);
}
</style>
