<script setup>
/**
 * Dónde se concentra el dinero público: un bloque por grupo.
 *
 * Esta vista sustituye al diagrama de nodos como PUERTA del mapa. El de nodos
 * no desaparece: se entra en él al pulsar un bloque, y entonces dibuja un
 * grupo de cincuenta entidades en vez de dos mil cuatrocientas, que es donde
 * un diagrama de nodos se lee.
 *
 * ## Por qué
 *
 * El mapa dibujaba los 2.428 nodos de la instantánea a la vez. Un diagrama de
 * nodos se lee hasta unos cien; con dos mil es una mancha. Se afinaron
 * tamaños, opacidades y rótulos tres veces y seguía sin leerse, porque el
 * problema no era el ajuste: era la cantidad.
 *
 * Y sobre todo: quien entra aquí no viene a ver una red. Viene a saber de
 * dónde sale el dinero de una decisión concreta, y para eso necesita
 * encontrar un sitio y meterse dentro. Cien bloques con su nombre escrito se
 * recorren con la vista en diez segundos; dos mil puntos, no.
 *
 * El área es el dato y no lleva raíz ni compresión: un bloque el doble de
 * grande es el doble de dinero. Aquí se puede, porque no hay que distinguir
 * un punto de tres píxeles de otro de dos.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  analizarNucleos,
  colapsarNodosDePaso,
  conEstructura,
  dineroCorto,
  FONDO,
  MINIMO_NUCLEO,
  paletaDeNucleos,
} from '../nucleos.js'
import { repartirRectangulo } from '../rectangulos.js'

const props = defineProps({
  datos: { type: Object, required: true },
  minImporte: { type: Number, default: 0 },
  mostrarExpedientes: { type: Boolean, default: false },
  soloExtranjero: { type: Boolean, default: false },
  soloPartidos: { type: Boolean, default: false },
})
const emit = defineEmits(['abrir', 'analizado'])

const contenedor = ref(null)
const ancho = ref(0)
const alto = ref(0)
const encima = ref(null)
let observador = null

function medir() {
  if (!contenedor.value) return
  ancho.value = contenedor.value.clientWidth
  alto.value = contenedor.value.clientHeight
}

onMounted(() => {
  medir()
  observador = new ResizeObserver(medir)
  observador.observe(contenedor.value)
})
onBeforeUnmount(() => observador?.disconnect())

/**
 * El análisis, con los mismos filtros que la vista de nodos.
 *
 * Los filtros se aplican quitando entidades ANTES de agrupar, igual que allí,
 * para que «sólo partidos» no enseñe grupos calculados sobre entidades que no
 * están en pantalla.
 */
const analisis = computed(() => {
  const fuente = props.mostrarExpedientes ? props.datos : colapsarNodosDePaso(props.datos)
  const { grafo, nucleos } = analizarNucleos(fuente)
  const porId = new Map((fuente?.nodes ?? []).map((n) => [n.id, n]))

  const fuera = new Set()
  grafo.forEachNode((id, attrs) => {
    if (props.minImporte > 0 && attrs.dinero < props.minImporte) fuera.add(id)
    const n = porId.get(id)
    if (props.soloExtranjero && !n?.properties?.entidad_extranjera) fuera.add(id)
    if (props.soloPartidos && attrs.esquema !== 'Organization') fuera.add(id)
  })

  const vivos = new Map()
  grafo.forEachNode((id, a) => {
    if (fuera.has(id)) return
    const c = a.nucleo ?? -1
    if (!vivos.has(c)) vivos.set(c, { tamano: 0, ids: new Set() })
    const v = vivos.get(c)
    v.tamano += 1
    v.ids.add(id)
  })

  const dinero = new Map()
  let total = 0
  grafo.forEachEdge((_e, attrs, s, t) => {
    if (fuera.has(s) || fuera.has(t)) return
    total += attrs.importe
    const cs = grafo.getNodeAttribute(s, 'nucleo')
    if (cs === grafo.getNodeAttribute(t, 'nucleo')) {
      dinero.set(cs, (dinero.get(cs) ?? 0) + attrs.importe)
    }
  })

  const visibles = nucleos
    .map((n) => {
      const v = vivos.get(n.id)
      if (!v) return null
      return {
        ...n,
        tamano: v.tamano,
        dinero: dinero.get(n.id) ?? 0,
        principales: n.principales.filter((m) => v.ids.has(m.id)),
        tipos: n.nodos.reduce((acc, id) => {
          if (!v.ids.has(id)) return acc
          const e = grafo.getNodeAttribute(id, 'esquema')
          acc[e] = (acc[e] ?? 0) + 1
          return acc
        }, {}),
      }
    })
    .filter((n) => n && n.tamano > 1)
    .sort((a, b) => b.dinero - a.dinero || b.tamano - a.tamano)

  const entidades = [...vivos.values()].reduce((s, v) => s + v.tamano, 0)
  return { nucleos: visibles, totalDinero: total, entidades }
})

/*
  Sólo los grupos con cuerpo, y es el mismo corte que usa la lista de al lado:
  por debajo de seis entidades no es un grupo, es una relación con adornos. Lo
  que queda fuera se dice al pie con su cifra, que es la diferencia entre
  recortar y esconder.
*/
const dibujables = computed(() => conEstructura(analisis.value.nucleos))
const pequenos = computed(() => {
  const fuera = analisis.value.nucleos.filter((n) => n.tamano < MINIMO_NUCLEO)
  return { cuantos: fuera.length, dinero: fuera.reduce((s, n) => s + n.dinero, 0) }
})

const color = computed(() => paletaDeNucleos(analisis.value.nucleos))

const MARGEN = 10

const bloques = computed(() => {
  if (!ancho.value || !alto.value) return []
  const lista = dibujables.value
  const cajas = repartirRectangulo(
    lista.map((n) => n.dinero),
    { x: MARGEN, y: MARGEN, ancho: ancho.value - MARGEN * 2, alto: alto.value - MARGEN * 2 },
  )
  return cajas.map((c) => {
    const n = lista[c.i]
    const tono = color.value(n.id)
    return {
      ...c,
      nucleo: n,
      color: tono,
      destacado: tono !== FONDO,
      // Un rótulo en una caja que no lo admite es peor que ninguno: tapa el
      // bloque y no se lee. Los umbrales son el sitio que piden dos renglones
      // de nombre y uno de cifra con sus márgenes.
      cabeNombre: c.ancho > 86 && c.alto > 40,
      cabeCifra: c.ancho > 86 && c.alto > 58,
      cabeDetalle: c.ancho > 150 && c.alto > 86,
    }
  })
})

function emitirAnalisis() {
  emit('analizado', {
    nucleos: analisis.value.nucleos,
    totalDinero: analisis.value.totalDinero,
    entidades: analisis.value.entidades,
    // Lo que no se dibuja se dice, y lo dice la leyenda de la vista, que es
    // quien tiene el sitio: aquí abajo se cruzaba con ella.
    pequenos: pequenos.value,
  })
}
onMounted(emitirAnalisis)
// El panel de al lado tiene que hablar de lo que se está viendo, no del mapa
// sin filtros: con «sólo partidos» puesto seguía encabezado por grupos que el
// filtro había quitado de la pantalla.
watch(analisis, emitirAnalisis)

function titulo(n) {
  return `${n.etiqueta} · ${dineroCorto(n.dinero)} · ${n.tamano} entidades`
}
</script>

<template>
  <div ref="contenedor" class="mapa-dinero">
    <svg v-if="bloques.length" :width="ancho" :height="alto" role="img">
      <title>Dónde se concentra el dinero público, por grupos</title>
      <g
        v-for="b in bloques"
        :key="b.nucleo.id"
        class="bloque"
        :class="{ destacado: b.destacado, apagado: encima !== null && encima !== b.nucleo.id }"
        @mouseenter="encima = b.nucleo.id"
        @mouseleave="encima = null"
        @click="emit('abrir', b.nucleo.id)"
      >
        <title>{{ titulo(b.nucleo) }}</title>
        <rect
          :x="b.x"
          :y="b.y"
          :width="Math.max(0, b.ancho - 2)"
          :height="Math.max(0, b.alto - 2)"
          rx="4"
          :fill="b.color"
          :fill-opacity="b.destacado ? 0.4 : 0.16"
          :stroke="b.color"
          stroke-opacity="0.85"
        />
        <!--
          El canto de color, arriba: con el relleno translúcido a solas, los
          ocho de cabeza y el resto se distinguían mal en los bloques
          pequeños, y el color es lo que los ata a su fila de la lista.
        -->
        <rect
          v-if="b.destacado"
          :x="b.x"
          :y="b.y"
          :width="Math.max(0, b.ancho - 2)"
          height="3"
          :fill="b.color"
        />
        <foreignObject
          v-if="b.cabeNombre"
          :x="b.x + 7"
          :y="b.y + 8"
          :width="Math.max(0, b.ancho - 16)"
          :height="Math.max(0, b.alto - 14)"
        >
          <div class="rotulo">
            <p class="nombre">{{ b.nucleo.etiqueta }}</p>
            <p v-if="b.cabeCifra" class="cifra">{{ dineroCorto(b.nucleo.dinero) }}</p>
            <p v-if="b.cabeDetalle" class="detalle">{{ b.nucleo.tamano }} entidades</p>
          </div>
        </foreignObject>
      </g>
    </svg>
    <p v-else class="vacio">Calculando los grupos…</p>
  </div>
</template>

<style scoped>
.mapa-dinero { position: relative; width: 100%; height: 100%; overflow: hidden; }

.bloque { cursor: pointer; transition: opacity 0.12s; }
.bloque.apagado { opacity: 0.45; }
.bloque:hover rect { fill-opacity: 0.6; }

.rotulo { overflow: hidden; height: 100%; pointer-events: none; }
.nombre {
  margin: 0; font-size: 12.5px; line-height: 1.2; font-weight: 600; color: var(--tinta);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.cifra {
  margin: 3px 0 0; font-size: 13px; font-weight: 650; color: var(--tinta);
  font-variant-numeric: tabular-nums;
}
.detalle { margin: 1px 0 0; font-size: 11px; color: var(--tinta-2); }

.vacio { position: absolute; inset: 0; display: grid; place-items: center; color: var(--tinta-3); }

</style>
