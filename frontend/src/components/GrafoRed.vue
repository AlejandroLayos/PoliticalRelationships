<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Graph from 'graphology'
import Sigma from 'sigma'
import EdgeCurveProgram from '@sigma/edge-curve'
import { dibujarEtiquetaConPlaca } from '../etiquetas.js'
import { aclarar, apagar, sobreFondo } from '../color.js'
import {
  cercania,
  entre,
  medidorDeFluidez,
  posicionEnDeriva,
  puntosDeReposo,
  realce,
  semillaDePosicion,
} from '../vida.js'
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

/*
  Aquí se mueve lo mismo que en el mapa: la colocación se calcula a la vista y
  después los puntos respiran. La lógica está en `vida.js`, con tests; lo de
  aquí es el bucle de fotogramas, que es Sigma y navegador.
*/
const menosMovimiento =
  typeof window !== 'undefined' &&
  Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches)

let animacion = null
let ajustesFuerza = null
let iteracionesPendientes = 0
let inicioDeriva = 0
let ultimoRefresco = 0
let ratonPintado = null
let ultimoFotograma = 0
const fluidez = medidorDeFluidez()
const reposo = new Map()
let radioRaton = 0
let raton = null
/* Mismo realce que el mapa: al apuntar un nodo, su vecindario sale de la masa
   y sus caminos se encienden. Ver `realce` en `vida.js`. */
const realzado = realce(200)
let vecindario = new Set()
let pendiente = false
let observador = null

/**
 * El tamaño del nodo crece con su grado: los nodos muy conectados son los que
 * interesan en un mapa de influencia, y así se ven sin tener que buscarlos.
 */
function tamano(grado) {
  return 5 + Math.min(14, Math.sqrt(grado) * 3.5)
}

/**
 * Los nombres de los expedientes, recortados.
 *
 * Aquí los nodos no son sólo entidades: son también contratos, y el `caption`
 * de un contrato es su objeto entero. «huelva 1º cbam-am 2204/2025 (nº siglo
 * 578/2025); c.c.a.+6.i+e9q8j-acuerdo marco con una única empresa, por lotes,
 * para el suministro…» se escribía completo, cruzaba el lienzo de lado a lado
 * y se cruzaba con los otros cuatro rótulos largos que había alrededor. La
 * pantalla era una maraña de letras de la que no se leía ninguna.
 *
 * El texto entero sigue estando: en el panel de al lado y al pasar por
 * encima.
 */
function recortar(texto, max = 44) {
  if (!texto || texto.length <= max) return texto ?? ''
  return `${texto.slice(0, max - 1).trimEnd()}…`
}

function construir() {
  grafo = new Graph({ multi: false, type: 'undirected' })

  for (const n of props.datos.nodes ?? []) {
    if (grafo.hasNode(n.id)) continue
    grafo.addNode(n.id, {
      label: recortar(n.caption),
      etiquetaReal: n.caption,
      esquema: n.schema,
      profundidad: n.depth ?? 0,
      color: COLOR_POR_ESQUEMA[n.schema] ?? COLOR_POR_DEFECTO,
      // Punto de partida estable, no aleatorio: ForceAtlas2 es determinista
      // si lo es su semilla. Ver `semillaDePosicion`.
      ...semillaDePosicion(n.id),
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
        // Opaco sobre el fondo, no `rgba`: el programa de aristas de Sigma
        // ignora el alfa y todas estas opacidades se dibujaban a 1. Ver
        // `color.js`.
        ? sobreFondo([224, 163, 58], 0.45)
        : sobreFondo([120, 150, 190], 0.3 + 0.5 * (a.confidence ?? 1)),
      size: inferida ? 0.8 : 1.2 + 2.2 * (a.confidence ?? 1),
      // Curvatura repartida para que dos aristas del mismo par no se pisen.
      curvature: 0.15 + ((a.id?.length ?? 3) % 5) * 0.035,
    })
  }

  grafo.forEachNode((id) => {
    grafo.setNodeAttribute(id, 'size', tamano(grafo.degree(id)))
  })

  // ForceAtlas2 es lo que produce el aspecto orgánico de red. Una parte de
  // las iteraciones aquí y el resto repartidas entre los primeros fotogramas:
  // así se ve el vecindario desplegarse en vez de aparecer ya colocado.
  if (grafo.order > 1) {
    const total = 220
    ajustesFuerza = {
      ...forceAtlas2.inferSettings(grafo),
      gravity: 1.4,
      scalingRatio: 12,
      barnesHutOptimize: grafo.order > 120,
    }
    const deGolpe = menosMovimiento ? total : Math.round(total * 0.25)
    forceAtlas2.assign(grafo, { iterations: deGolpe, settings: ajustesFuerza })
    iteracionesPendientes = total - deGolpe
  }
}

function prepararDeriva() {
  const nodos = grafo.mapNodes((id, a) => ({ id, x: a.x, y: a.y, size: a.size }))
  const calculado = puntosDeReposo(nodos)
  reposo.clear()
  for (const [id, base] of calculado.reposo) reposo.set(id, base)
  radioRaton = calculado.radio
  inicioDeriva = performance.now()
}

function unFotograma(ahora) {
  animacion = requestAnimationFrame(unFotograma)
  if (!sigma || !grafo || document.hidden) return

  if (iteracionesPendientes > 0) {
    const paso = Math.min(4, iteracionesPendientes)
    forceAtlas2.assign(grafo, { iterations: paso, settings: ajustesFuerza })
    iteracionesPendientes -= paso
    if (iteracionesPendientes <= 0) prepararDeriva()
    sigma.refresh()
    return
  }

  // El realce va siempre, incluso con «reducir movimiento»: es respuesta a un
  // gesto. Lo que se le quita a quien lo pide es el fundido y la respiración.
  const dt = ahora - (ultimoFotograma || ahora)
  ultimoFotograma = ahora
  const fundiendo = realzado.avanza(menosMovimiento ? 1e4 : dt)

  if (menosMovimiento) {
    if (!fundiendo && raton === ratonPintado) return
    ratonPintado = raton
    sigma.refresh({ skipIndexation: true })
    return
  }

  if (!reposo.size) prepararDeriva()

  // Mismo trato que en el mapa: la respiración se apaga sola donde repintar
  // salga caro; el foco del cursor se repinta siempre que el ratón se mueva.
  // Ver `medidorDeFluidez` en `vida.js`.
  const ratonMovido = raton !== ratonPintado
  if (!fluidez.viable && !ratonMovido && !fundiendo) return
  if (!fundiendo && ahora - ultimoRefresco < 33) return
  ultimoRefresco = ahora
  ratonPintado = raton

  if (fluidez.viable) {
    const t = (ahora - inicioDeriva) / 1000
    grafo.forEachNode((id) => {
      const b = reposo.get(id)
      if (!b) return
      const pos = posicionEnDeriva(b, t)
      grafo.setNodeAttribute(id, 'x', pos.x)
      grafo.setNodeAttribute(id, 'y', pos.y)
    })
  }
  if (!fundiendo) fluidez.anota(ahora)
  sigma.refresh({ skipIndexation: true })
}

function seguirAlRaton(e) {
  if (!sigma || !contenedor.value) return
  const caja = contenedor.value.getBoundingClientRect()
  raton = sigma.viewportToGraph({ x: e.clientX - caja.left, y: e.clientY - caja.top })
}

function soltarElRaton() {
  raton = null
}

function pintar() {
  if (!contenedor.value) return
  /*
    Un contenedor sin ancho no se puede dibujar.

    Sigma lo dice por la consola —«Container has no width»— y se queda con un
    lienzo de cero. Pasa porque la vista del grafo se esconde con
    `display: none` cuando la portada está delante: si algo manda repintar en
    ese momento, se pinta contra la nada y al volver el dibujo está vacío sin
    que nadie haya fallado. Se apunta y se pinta cuando el contenedor tenga
    tamaño, que es lo que avisa el observador.
  */
  if (!contenedor.value.clientWidth || !contenedor.value.clientHeight) {
    pendiente = true
    return
  }
  pendiente = false
  if (animacion !== null) {
    cancelAnimationFrame(animacion)
    animacion = null
  }
  if (sigma) {
    contenedor.value.removeEventListener('mousemove', seguirAlRaton)
    contenedor.value.removeEventListener('mouseleave', soltarElRaton)
    sigma.kill()
    sigma = null
  }
  construir()

  sigma = new Sigma(grafo, contenedor.value, {
    renderEdgeLabels: false,
    // Curvas: con rectas, el vecindario de un organismo sale como un abanico
    // de agujas que se cortan en ángulo. Ver el mismo ajuste en `MapaNucleos`.
    defaultEdgeType: 'curva',
    edgeProgramClasses: { curva: EdgeCurveProgram },
    // Rotular tiene presupuesto. Con celdas de 70 px y umbral 7, un organismo
    // con treinta vecinos dejaba treinta nombres largos apiñados unos encima
    // de otros: una mancha de letras de la que no se leía ninguna. La rejilla
    // más grande deja pasar menos, y la placa hace legibles las que pasan.
    labelDensity: 0.5,
    labelGridCellSize: 180,
    labelRenderedSizeThreshold: 9,
    labelFont: 'system-ui, sans-serif',
    labelColor: { color: '#f2f5fa' },
    labelSize: 12,
    labelWeight: '600',
    defaultDrawNodeLabel: dibujarEtiquetaConPlaca,
    // El nodo resaltado usa OTRO pintor, el de hover, que por defecto dibuja
    // una placa blanca con texto oscuro. Al cambiar sólo el de la etiqueta,
    // encima de esa placa blanca se escribía el texto claro del nuestro y el
    // nombre del nodo seleccionado desaparecía: un rectángulo blanco vacío en
    // el centro del grafo. Los dos pintan igual.
    defaultDrawNodeHover: dibujarEtiquetaConPlaca,
    minCameraRatio: 0.08,
    maxCameraRatio: 8,
  })

  sigma.on('enterNode', ({ node }) => {
    vecindario = new Set(grafo.neighbors(node))
    realzado.apunta(node)
  })
  sigma.on('leaveNode', () => realzado.apunta(''))
  sigma.on('clickNode', ({ node }) => emit('seleccionar', node))
  sigma.on('doubleClickNode', ({ node, event }) => {
    // Doble clic expande el vecindario desde ese nodo: es el gesto natural
    // para "sigue tirando del hilo".
    event.preventSigmaDefault()
    emit('expandir', node)
  })

  contenedor.value.addEventListener('mousemove', seguirAlRaton)
  contenedor.value.addEventListener('mouseleave', soltarElRaton)

  resaltar()
  reposo.clear()
  raton = null
  animacion = requestAnimationFrame(unFotograma)
}

/** Atenúa lo que no toca al nodo seleccionado, para poder leer el vecindario. */
function resaltar() {
  if (!sigma || !grafo) return
  const foco = props.seleccion
  sigma.setSetting('nodeReducer', (id, datos) => {
    if (foco && grafo.hasNode(foco)) {
      // El del foco, con su nombre entero: es UNO, no se cruza con nada y es
      // justo el que se está mirando.
      if (id === foco) {
        return { ...datos, label: datos.etiquetaReal ?? datos.label, highlighted: true, zIndex: 2 }
      }
      if (grafo.areNeighbors(foco, id)) return { ...datos, zIndex: 1 }
      return { ...datos, color: sobreFondo([160, 165, 180], 0.28), label: '', zIndex: 0 }
    }
    // Apuntar un nodo enciende su vecindario y apaga el resto, con fundido.
    const i = realzado.intensidad
    if (i > 0.001 && realzado.id && grafo.hasNode(realzado.id)) {
      if (id === realzado.id) {
        return {
          ...datos,
          label: datos.etiquetaReal ?? datos.label,
          forceLabel: true,
          color: aclarar(datos.color, entre(0, 0.45, i)),
          size: datos.size * entre(1, 1.7, i),
          zIndex: 3,
        }
      }
      if (vecindario.has(id)) {
        return {
          ...datos,
          label: datos.etiquetaReal ?? datos.label,
          forceLabel: vecindario.size <= 12 && i > 0.55,
          color: aclarar(datos.color, entre(0, 0.34, i)),
          size: datos.size * entre(1, 1.3, i),
          zIndex: 2,
        }
      }
      return { ...datos, color: apagar(datos.color, entre(0, 0.88, i)), label: '', zIndex: 0 }
    }

    // Y si no, el foco del cursor: lo de alrededor se aclara, el resto se aleja.
    if (!raton) return datos
    const cerca = cercania(datos.x, datos.y, raton, radioRaton)
    if (cerca <= 0.02) return { ...datos, color: apagar(datos.color, 0.55), zIndex: 0 }
    return {
      ...datos,
      color: aclarar(datos.color, cerca * 0.5),
      size: datos.size * (1 + cerca * 0.55),
      zIndex: 1,
    }
  })
  sigma.setSetting('edgeReducer', (id, datos) => {
    const extremos = grafo.extremities(id)
    if (foco && grafo.hasNode(foco)) {
      if (extremos.includes(foco)) return { ...datos, zIndex: 1 }
      return { ...datos, color: sobreFondo([190, 193, 203], 0.16), zIndex: 0 }
    }
    // Los caminos del nodo apuntado: los suyos se encienden y engordan, los
    // de vecino a vecino quedan a media luz y el resto casi al fondo.
    const i = realzado.intensidad
    if (i > 0.001 && realzado.id) {
      if (extremos.includes(realzado.id)) {
        const grueso = vecindario.size > 24 ? 1.5 : vecindario.size > 8 ? 2 : 2.6
        return {
          ...datos,
          color: aclarar(datos.color, entre(0, 0.85, i)),
          size: datos.size * entre(1, grueso, i),
          zIndex: 3,
        }
      }
      const entreVecinos = vecindario.has(extremos[0]) && vecindario.has(extremos[1])
      return {
        ...datos,
        color: apagar(datos.color, entre(0, entreVecinos ? 0.55 : 0.92, i)),
        zIndex: 0,
      }
    }

    if (!raton) return datos
    const cerca = Math.max(
      cercania(grafo.getNodeAttribute(extremos[0], 'x'), grafo.getNodeAttribute(extremos[0], 'y'), raton, radioRaton),
      cercania(grafo.getNodeAttribute(extremos[1], 'x'), grafo.getNodeAttribute(extremos[1], 'y'), raton, radioRaton),
    )
    if (cerca <= 0.02) return { ...datos, color: sobreFondo([150, 170, 200], 0.1), zIndex: 0 }
    return { ...datos, color: sobreFondo([200, 222, 250], 0.15 + cerca * 0.75), zIndex: 1 }
  })
  sigma.refresh()
}

onMounted(() => {
  observador = new ResizeObserver(() => {
    if (pendiente && contenedor.value?.clientWidth) pintar()
  })
  observador.observe(contenedor.value)
  pintar()
})
watch(() => props.datos, pintar, { deep: false })
watch(() => props.seleccion, resaltar)

onBeforeUnmount(() => {
  observador?.disconnect()
  if (animacion !== null) cancelAnimationFrame(animacion)
  contenedor.value?.removeEventListener('mousemove', seguirAlRaton)
  contenedor.value?.removeEventListener('mouseleave', soltarElRaton)
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
