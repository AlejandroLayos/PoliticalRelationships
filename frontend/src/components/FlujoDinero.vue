<script setup>
/**
 * El flujo de dinero de una entidad, en tres columnas.
 *
 * De quién le entra · quién es · a quién le sale. Es la vista que contesta la
 * pregunta con la que la gente llega: «este ayuntamiento, ¿a qué empresas
 * paga?», «este partido, ¿quién lo financia?».
 *
 * La geometría vive en `flujo.js` y está probada aparte; aquí sólo se pinta.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { disponerFlujo, recortarAAncho } from '../flujo.js'
import { dineroCorto } from '../nucleos.js'
import { COLOR_POR_DEFECTO, COLOR_POR_ESQUEMA, etiquetaEsquema } from '../esquemas.js'

const props = defineProps({
  area: { type: Object, default: null },
  /** Aviso de por qué puede faltar dinero: una fuente caída, por ejemplo. */
  nota: { type: String, default: '' },
  /** Fila del índice cuando la entidad no está en el grafo publicado. */
  fueraDelMapa: { type: Object, default: null },
})
const emit = defineEmits(['seleccionar'])

// Los mismos de la hoja de estilos, medidos: entra/sale pasan las seis
// comprobaciones con todos los pares (peor ΔE 9,4 con deuteranopia, 24,6 en
// visión normal). Aquí el color dice DIRECCIÓN y no tipo, y puede hacerlo
// porque en este dibujo no hay ninguna marca de tipo con la que confundirse y
// las cabeceras de columna lo dicen además con palabras.
const ENTRA = '#199e70'
const SALE = '#d95926'
const EXTRANJERO = '#9085e9'

const caja = ref(null)
const ancho = ref(0)
const alto = ref(0)
const encima = ref('')
let observador = null

onMounted(() => {
  observador = new ResizeObserver(([e]) => {
    ancho.value = e.contentRect.width
    alto.value = e.contentRect.height
  })
  observador.observe(caja.value)
})
onBeforeUnmount(() => observador?.disconnect())

const disposicion = computed(() =>
  disponerFlujo(props.area, {
    ancho: ancho.value,
    alto: alto.value,
    // El pie guarda sitio para dos cosas que se pintan por debajo de la
    // última ficha: el «+N más, en la lista» y la leyenda. En escritorio, con
    // 22 px el «+N» caía encima de la ayuda de la esquina; en móvil la
    // leyenda pasa a dos renglones sobre una placa opaca y con 50 px se
    // tragaba el «+N», que salía apagado debajo del recuadro.
    pie: ancho.value < 700 ? 78 : 36,
    // Doce contrapartes dejaban media pantalla en negro: con el tope de alto
    // de la ficha puesto, doce cajas de 68 px ocupan 890 px de los 900 que
    // hay, pero como las de abajo son pequeñas el dibujo se queda corto por
    // arriba y sobra sitio. A dieciocho cabe todo y cada caja sigue teniendo
    // sitio de sobra para el nombre y el importe.
    maxPorLado: ancho.value < 700 ? 9 : 18,
  }),
)

/**
 * Los nombres oficiales son interminables. Se recortan al ancho de la ficha y
 * el nombre entero queda en el `title` y en el panel.
 *
 * `reservado` es el sitio que ocupa otra cosa en la misma línea. En las fichas
 * bajas el nombre y la cifra comparten renglón, y sin reservarlo se pisaban:
 * "CONSEJERÍA DE DESREGULACIÓN, FAMILIA Y…" con "11 mil €" encima.
 */
/*
  Se mide con un lienzo en vez de contar caracteres.

  La cuenta era «6,4 px por carácter», y los nombres de empresa van casi todos
  en mayúsculas, que son más anchas: el recorte se quedaba corto y en las
  fichas de un solo renglón el nombre acababa pegado al importe, sin espacio
  —«VERTEX PHARMACEUTICALS (SPAI…4,3 M €»—.
*/
let medidor = null
function anchoDe(texto, fuente) {
  if (medidor === null) {
    const lienzo = typeof document === 'undefined' ? null : document.createElement('canvas')
    medidor = lienzo?.getContext('2d') ?? false
  }
  if (!medidor) return texto.length * 7
  medidor.font = fuente
  return medidor.measureText(texto).width
}

const FUENTE_NOMBRE = '11.5px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
const FUENTE_CIFRA = '650 12px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
/** Aire entre el nombre y la cifra cuando comparten renglón. */
const AIRE = 12

function recortar(texto, w, reservado = 0) {
  return recortarAAncho(texto, w - 18 - reservado, (t) => anchoDe(t, FUENTE_NOMBRE))
}

/** Lo que ocupa la cifra, para no escribir el nombre debajo. */
function anchoCifra(total) {
  return anchoDe(dineroCorto(total), FUENTE_CIFRA) + AIRE
}

const FUENTE_TIPO = '9.5px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
/** `measureText` no sabe del `letter-spacing` del CSS; se suma aparte. */
const ESPACIADO_TIPO = 0.95

/**
 * El tipo de la entidad, o nada si no cabe en el recuadro.
 *
 * Va centrado sobre la caja y no se recorta solo: en un móvil, «ORGANISMO
 * PÚBLICO» es más ancho que el recuadro y se salía por los dos lados, encima
 * de las cintas. Antes que un rótulo pisando el dibujo, ninguno — el tipo
 * está también en el panel de al lado, en su cabecera.
 */
const tipoCentro = computed(() => {
  const caja = disposicion.value.centro
  const texto = etiquetaEsquema(props.area?.entidad?.schema ?? '').toUpperCase()
  if (!caja || !texto) return ''
  const mide = anchoDe(texto, FUENTE_TIPO) + texto.length * ESPACIADO_TIPO
  return mide <= caja.w - 12 ? texto : ''
})

/** Dos renglones si la ficha da de sí; si no, nombre y cifra en el mismo. */
function esAlta(c) {
  return c.h > 34
}

function colorDe(c) {
  if (c.extranjera) return EXTRANJERO
  return c.lado === 'izquierda' ? ENTRA : SALE
}

function rellenoCinta(c) {
  const sufijo = c.extranjera ? '-ext' : ''
  return `url(#cinta-${c.lado === 'izquierda' ? 'entra' : 'sale'}${sufijo})`
}

function ultima(columna) {
  return columna[columna.length - 1]
}

/** Justo debajo de la última ficha, sin salirse del lienzo. */
function piePara(columna) {
  const c = ultima(columna)
  return Math.min(alto.value - 4, c.y + c.h + 14)
}

/** Resaltado: al pasar por una ficha se apaga todo lo demás. */
function apagada(id) {
  return encima.value && encima.value !== id
}

const colorCentro = computed(
  () => COLOR_POR_ESQUEMA[props.area?.entidad?.schema] ?? COLOR_POR_DEFECTO,
)

/**
 * Una ficha sin dinero puede ser un hecho o puede ser un hueco nuestro. No es
 * lo mismo «este partido no recibe nada» que «hoy no respondió la fuente que
 * recoge las subvenciones», y presentarlos igual haría que la ausencia de dato
 * pareciera un dato.
 */
const sinFlujo = computed(
  () => Boolean(props.area?.entidad) && !props.area.recibeDe.length && !props.area.pagaA.length,
)
</script>

<template>
  <div ref="caja" class="lienzo">
    <svg v-if="disposicion.centro && !fueraDelMapa" :width="ancho" :height="alto" class="flujo">
      <!--
        Las cintas se degradan hacia la entidad. Planas y translúcidas salían
        marrones —naranja al 30 % sobre fondo oscuro— y las de un lado y otro
        se distinguían mal; con el degradado el color se reconoce donde está la
        etiqueta, que es donde se mira.
      -->
      <defs>
        <linearGradient id="cinta-entra" x1="0" x2="1">
          <stop offset="0" :stop-color="ENTRA" stop-opacity="0.22" />
          <stop offset="1" :stop-color="ENTRA" stop-opacity="0.05" />
        </linearGradient>
        <linearGradient id="cinta-sale" x1="0" x2="1">
          <stop offset="0" :stop-color="SALE" stop-opacity="0.05" />
          <stop offset="1" :stop-color="SALE" stop-opacity="0.22" />
        </linearGradient>
        <linearGradient id="cinta-entra-ext" x1="0" x2="1">
          <stop offset="0" :stop-color="EXTRANJERO" stop-opacity="0.26" />
          <stop offset="1" :stop-color="EXTRANJERO" stop-opacity="0.06" />
        </linearGradient>
        <linearGradient id="cinta-sale-ext" x1="0" x2="1">
          <stop offset="0" :stop-color="EXTRANJERO" stop-opacity="0.06" />
          <stop offset="1" :stop-color="EXTRANJERO" stop-opacity="0.26" />
        </linearGradient>
      </defs>
      <!-- Cabeceras de columna: el papel de cada lado, dicho con palabras. -->
      <!--
        El texto de la cabecera va en TINTA, no del color de la serie, y la
        identidad la lleva el cuadrito de color de al lado. Un rótulo pintado
        del color del dato compite con el dato y encima se lee peor: un verde
        o un naranja sobre fondo oscuro no dan el contraste que da el blanco.
      -->
      <template v-if="disposicion.izquierda.length">
        <rect :x="disposicion.izquierda[0].x" y="9" width="9" height="9" rx="2" :fill="ENTRA" />
        <text :x="disposicion.izquierda[0].x + 14" y="18" class="cabecera">
          DE QUIÉN RECIBE · {{ dineroCorto(area.totalRecibido) }}
        </text>
      </template>
      <template v-if="disposicion.derecha.length">
        <text
          :x="disposicion.derecha[0].x + disposicion.derecha[0].w - 14"
          y="18"
          text-anchor="end"
          class="cabecera"
        >
          A QUIÉN PAGA · {{ dineroCorto(area.totalPagado) }}
        </text>
        <rect
          :x="disposicion.derecha[0].x + disposicion.derecha[0].w - 9"
          y="9"
          width="9"
          height="9"
          rx="2"
          :fill="SALE"
        />
      </template>

      <!-- Cintas primero, para que las fichas queden encima. -->
      <g>
        <path
          v-for="c in disposicion.cintas"
          :key="c.id"
          :d="c.d"
          :fill="rellenoCinta(c)"
          :stroke="colorDe(c)"
          :class="['cinta', { apagada: apagada(c.nodoId), inferida: c.inferido }]"
        />
      </g>

      <!-- Contrapartes -->
      <g
        v-for="c in [...disposicion.izquierda, ...disposicion.derecha]"
        :key="c.id"
        :class="['ficha', { apagada: apagada(c.id) }]"
        @mouseenter="encima = c.id"
        @mouseleave="encima = ''"
        @click="emit('seleccionar', c.id)"
      >
        <title>{{ c.caption }} · {{ dineroCorto(c.total) }} · {{ c.n }} {{ c.n === 1 ? 'relación' : 'relaciones' }}</title>
        <rect :x="c.x" :y="c.y" :width="c.w" :height="c.h" rx="6" class="caja-ficha" />
        <!--
          La banda de color va por la BANDA, no por la ficha: es lo que deja
          ver el grosor real cuando la etiqueta es más baja que el flujo.
        -->
        <rect
          :x="c.lado === 'izquierda' ? c.x + c.w - 3 : c.x"
          :y="c.bandaY"
          width="3"
          :height="c.bandaH"
          :fill="colorDe(c)"
        />
        <text :x="c.x + 9" :y="c.y + (esAlta(c) ? 17 : c.h / 2 + 4)" class="nombre">
          {{ recortar(c.caption, c.w, esAlta(c) ? 0 : anchoCifra(c.total)) }}
        </text>
        <text v-if="esAlta(c)" :x="c.x + 9" :y="c.y + 33" class="cifra">
          {{ dineroCorto(c.total) }}
          <tspan v-if="c.extranjera" class="marca">· extranjera</tspan>
          <tspan v-if="c.inferido" class="marca inferida">· inferido</tspan>
        </text>
        <text v-else :x="c.x + c.w - 9" :y="c.y + c.h / 2 + 4" text-anchor="end" class="cifra">
          {{ dineroCorto(c.total) }}
        </text>
      </g>

      <!-- La entidad -->
      <g class="centro">
        <rect
          :x="disposicion.centro.x"
          :y="disposicion.centro.y"
          :width="disposicion.centro.w"
          :height="disposicion.centro.h"
          rx="10"
          class="caja-centro"
          :style="{ stroke: colorCentro }"
        />
        <text
          :x="disposicion.centro.x + disposicion.centro.w / 2"
          :y="disposicion.centro.y + 22"
          text-anchor="middle"
          class="tipo-centro"
        >
          {{ tipoCentro }}
        </text>
        <foreignObject
          :x="disposicion.centro.x + 8"
          :y="disposicion.centro.y + 30"
          :width="disposicion.centro.w - 16"
          :height="disposicion.centro.h - 38"
        >
          <div class="cuerpo-centro">
            <p class="titulo">{{ area.entidad.caption }}</p>
            <!--
              Un expediente sin cuantía sigue siendo un expediente. Condicionar
              esto al importe escondía sanciones sólo porque el Tribunal de
              Cuentas publicó la cifra de un modo que no se pudo interpretar.
            -->
            <p v-if="area.sanciones.length" class="sancion">
              {{ area.sanciones.length }}
              {{ area.sanciones.length === 1 ? 'expediente sancionador' : 'expedientes sancionadores' }}
              <template v-if="area.totalSancionado > 0">· {{ dineroCorto(area.totalSancionado) }}</template>
              <template v-else>· sin cuantía interpretable</template>
            </p>
          </div>
        </foreignObject>
      </g>

      <!-- Sin flujo: decir por qué, no dejar el hueco mudo. -->
      <foreignObject
        v-if="sinFlujo"
        :x="Math.max(8, disposicion.centro.x - 60)"
        :y="disposicion.centro.y + disposicion.centro.h + 14"
        :width="Math.min(ancho - 16, disposicion.centro.w + 120)"
        height="110"
      >
        <p class="sin-flujo">
          No consta que esta entidad pague ni cobre en la instantánea
          publicada.<template v-if="nota"> {{ nota }}</template>
          <template v-else> Puede que sólo aparezca como estructura, sin
            operaciones económicas en las fuentes ingeridas.</template>
        </p>
      </foreignObject>

      <!--
        Lo que no cupo se dice, no se esconde. Va pegado debajo de la última
        ficha de su columna y no al pie del lienzo: ahí se cruzaba con la ayuda
        de la esquina —«+85 receptores más» encima de «Clic en una contraparte
        para seguir el rastro»— y no se leía ninguna de las dos.
      -->
      <text
        v-if="disposicion.recortado.izquierda"
        :x="ultima(disposicion.izquierda).x"
        :y="piePara(disposicion.izquierda)"
        class="recorte"
      >
        +{{ disposicion.recortado.izquierda }} pagadores más, en la lista
      </text>
      <!--
        Anclado por la derecha: escrito desde el borde izquierdo de la
        columna, en un móvil se salía del lienzo y el texto acababa cortado
        («+68 receptores más, en la lis»).
      -->
      <text
        v-if="disposicion.recortado.derecha"
        :x="ultima(disposicion.derecha).x + ultima(disposicion.derecha).w"
        :y="piePara(disposicion.derecha)"
        text-anchor="end"
        class="recorte"
      >
        +{{ disposicion.recortado.derecha }} receptores más, en la lista
      </text>
    </svg>

    <div v-if="fueraDelMapa" class="vacio">
      <p>
        De <strong>{{ fueraDelMapa.caption }}</strong> consta cuánto mueve,
        pero no con quién: el mapa publicado se recorta a las relaciones con
        más dinero y ésta no entró. Las cifras están en el panel.
      </p>
    </div>

  </div>
</template>

<style scoped>
.lienzo { position: absolute; inset: 0; background: var(--fondo-grafo); overflow: hidden; }
.flujo { display: block; }

.cabecera {
  font-size: 10.5px; letter-spacing: 0.09em; font-weight: 700;
  fill: var(--tinta-3);
}

/* El filo marca dónde acaba cada cinta cuando dos van pegadas. */
/*
  El relleno es un lavado y el FILO es quien lleva la forma. Con el relleno
  cargado, doce cintas juntas se funden en un bloque marrón que ocupa media
  pantalla y no deja ver ninguna; con el filo marcado se distinguen las doce y
  el dibujo respira.
*/
.cinta { transition: opacity 0.15s; stroke-width: 1.25; stroke-opacity: 0.5; }
.cinta.apagada { opacity: 0.12; }
.cinta.inferida { opacity: 0.45; }

.ficha { cursor: pointer; transition: opacity 0.15s; }
.ficha.apagada { opacity: 0.3; }
.caja-ficha { fill: var(--superficie); stroke: var(--linea); }
.ficha:hover .caja-ficha { stroke: var(--acento); }

.nombre { font-size: 11.5px; fill: var(--tinta-2); }
.cifra {
  font-size: 12px; font-variant-numeric: tabular-nums; font-weight: 650;
  fill: var(--tinta);
}
.marca { font-size: 9.5px; font-weight: 400; fill: var(--texto-tenue); }
.marca.inferida { fill: var(--aviso); }

.caja-centro { fill: var(--superficie); stroke-width: 2; }
.tipo-centro { font-size: 9.5px; letter-spacing: 0.1em; fill: var(--texto-tenue); }
.cuerpo-centro { display: flex; flex-direction: column; justify-content: center; height: 100%; text-align: center; }
.titulo {
  margin: 0; font-size: 14px; line-height: 1.3; font-weight: 650; color: var(--tinta);
  font-family: system-ui, sans-serif;
}
.sancion {
  margin: 0.35rem 0 0; font-size: 10.5px; color: #e8877f; line-height: 1.3;
  font-family: system-ui, sans-serif;
}

.recorte { font-size: 10px; fill: var(--texto-tenue); }

.sin-flujo {
  margin: 0; text-align: center; font-size: 11.5px; line-height: 1.45;
  color: var(--texto-tenue); font-family: system-ui, sans-serif;
}

/*
  Era un <p> con `display: grid`, y eso convierte en celda cada hijo: los
  trozos de texto por un lado y el <strong> por otro, cada uno centrado
  aparte. En la ficha de un organismo salía la palabra «De» suelta arriba del
  todo, el nombre en negrita pisando el diagrama por el medio y el resto de la
  frase abajo. Parecía un fallo de render porque lo era.
*/
.vacio {
  position: absolute; inset: 0; margin: 0;
  display: flex; align-items: center; justify-content: center;
  padding: 2rem; text-align: center;
  color: var(--texto-tenue); font-size: 0.88rem; line-height: 1.5;
}
.vacio > * { max-width: 34rem; margin: 0; }
</style>
