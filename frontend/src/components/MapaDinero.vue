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
  MINIMO_NUCLEO,
} from '../nucleos.js'
import { repartirConResto } from '../rectangulos.js'
import { mezclaDeTipos } from '../esquemas.js'

const props = defineProps({
  datos: { type: Object, required: true },
  minImporte: { type: Number, default: 0 },
  mostrarExpedientes: { type: Boolean, default: false },
  soloExtranjero: { type: Boolean, default: false },
  soloPartidos: { type: Boolean, default: false },
  /** El grupo que se está señalando desde la lista de al lado. */
  senalado: { type: Number, default: null },
})
const emit = defineEmits(['abrir', 'analizado', 'senalar'])

// Se mide el lienzo y no el componente entero: encima va el pie de gráfico.
const contenedor = ref(null)
const ancho = ref(0)
const alto = ref(0)
const encima = ref(null)
let observador = null

/*
  El bloque y su fila se señalan el uno al otro: pasar por un bloque resalta
  su fila en la lista, y pasar por la fila, su bloque. El número los ata;
  esto ahorra además buscarlo.
*/
const resaltado = computed(() => encima.value ?? props.senalado)
function senalar(id) {
  encima.value = id
  emit('senalar', typeof id === 'number' ? id : null)
}

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

const MARGEN = 2

/*
  La cola se junta en un bloque «y N más».

  Cien grupos terminan en una esquina de rectángulos de seis píxeles: no cabe
  ni el nombre ni la cifra, así que son cajas negras que no dicen nada y
  encima se pueden pulsar sin querer. Quitarlas sin más haría que el dibujo
  afirmara que ese dinero no existe, así que se juntan en una sola con su
  cuenta y su suma. El corte es por tamaño DIBUJADO y depende del lienzo: en
  una pantalla ancha se rotulan cuarenta y en un teléfono, ocho.
*/
const reparto = computed(() => {
  if (!ancho.value || !alto.value) return { cajas: [], resto: null }
  return repartirConResto(
    dibujables.value.map((n) => n.dinero),
    { x: MARGEN, y: MARGEN, ancho: ancho.value - MARGEN * 2, alto: alto.value - MARGEN * 2 },
    { minAncho: 90, minAlto: 44 },
  )
})

/** Los grupos que el reparto ha juntado al final, si ha juntado alguno. */
const juntados = computed(() => {
  const r = reparto.value.resto
  if (!r) return null
  return { cuantos: r.cuantos, dinero: r.valor }
})

/*
  Los bloques van en papel y numerados, no pintados.

  Eran ocho colores para los ocho primeros grupos y gris para el resto, y la
  lista de al lado repetía el color en un punto. Casar tonos parecidos de
  memoria —¿este naranja o aquel salmón?— es el trabajo que un número ahorra,
  y ocho colores más chocaban con los tres que dicen quién es quién en toda
  la web (docs/diseno.md §2). Ahora el bloque 03 es la fila 03.
*/
const bloques = computed(() => {
  const lista = dibujables.value
  const { cajas, resto } = reparto.value
  return cajas.map((c) => {
    const cabe = {
      cabeNombre: c.ancho > 86 && c.alto > 40,
      cabeCifra: c.ancho > 86 && c.alto > 62,
    }
    if (resto && c.i === resto.desde) {
      return { ...c, ...cabe, nucleo: null, numero: '', cabeDetalle: false, mezcla: [], juntados: resto }
    }
    const n = lista[c.i]
    return {
      ...c,
      ...cabe,
      nucleo: n,
      numero: String(c.i + 1).padStart(2, '0'),
      // Un rótulo en una caja que no lo admite es peor que ninguno: tapa el
      // bloque y no se lee.
      cabeDetalle: c.ancho > 150 && c.alto > 104,
      mezcla: mezclaDeTipos(n.tipos),
      juntados: null,
    }
  })
})

/**
 * La cifra crece con el bloque, como en una infografía de prensa: el bloque
 * más grande lleva la cifra más grande, y la jerarquía se lee antes que los
 * números. Con tope, para que no compita con el nombre.
 */
function cuerpoCifra(b) {
  return Math.round(Math.min(30, Math.max(16, Math.sqrt(b.ancho * b.alto) / 13)))
}

/** Los tramos de la barra de mezcla de un bloque, en píxeles. */
function tramos(b) {
  const x0 = b.x + 9
  const w = Math.max(0, b.ancho - 20)
  let x = x0
  return b.mezcla.map((m) => {
    const t = { tipo: m.tipo, x, w: Math.max(0, m.parte * w - 1) }
    x += m.parte * w
    return t
  })
}

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
  <div class="mapa-dinero">
    <!--
      El pie de gráfico va ARRIBA y fuera del dibujo. Era una placa encima de
      la esquina de abajo, y tapaba justo los bloques que caían ahí: el de la
      Diputación de Gipuzkoa se leía a medias debajo de la frase que
      explicaba qué eran los bloques.
    -->
    <p class="pie-grafico">
      <b>El área de cada bloque es el dinero</b> que se pagan entre sí los
      organismos y empresas de un grupo. Pulsa uno para ver quién está dentro.
      <span class="ancho">
        {{ dibujables.length }} grupos, {{ analisis.entidades.toLocaleString('es-ES') }}
        entidades, {{ dineroCorto(analisis.totalDinero) }} en juego.
        <!-- Lo que se recorta se dice, con su cifra: es la diferencia entre recortar y esconder. -->
        <template v-if="pequenos.cuantos">
          No se dibujan {{ pequenos.cuantos }} grupos de menos de {{ MINIMO_NUCLEO }}
          entidades ({{ dineroCorto(pequenos.dinero) }}): se pueden buscar por su nombre.
        </template>
      </span>
    </p>

    <div ref="contenedor" class="lienzo">
      <svg v-if="bloques.length" :width="ancho" :height="alto" role="img">
        <title>Dónde se concentra el dinero público, por grupos</title>
        <defs>
          <!-- El rayado del resto: lo que no se dibuja por separado. -->
          <pattern id="rayado-resto" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="7" height="7" class="rayado-fondo" />
            <line x1="0" y1="0" x2="0" y2="7" class="rayado-linea" />
          </pattern>
        </defs>
        <g
          v-for="b in bloques"
          :key="b.juntados ? 'resto' : b.nucleo.id"
          class="bloque"
          :class="{
            resto: Boolean(b.juntados),
            apagado: resaltado !== null && resaltado !== (b.nucleo?.id ?? 'resto'),
          }"
          @mouseenter="senalar(b.nucleo?.id ?? 'resto')"
          @mouseleave="senalar(null)"
          @click="b.nucleo && emit('abrir', b.nucleo.id)"
        >
          <title v-if="b.juntados">
            {{ b.juntados.cuantos }} grupos más pequeños · {{ dineroCorto(b.juntados.valor) }}
          </title>
          <title v-else>{{ titulo(b.nucleo) }}</title>
          <rect
            :x="b.x"
            :y="b.y"
            :width="Math.max(0, b.ancho - 3)"
            :height="Math.max(0, b.alto - 3)"
            rx="2"
            class="caja"
            :style="b.juntados ? { fill: 'url(#rayado-resto)' } : null"
          />
          <foreignObject
            v-if="b.cabeNombre"
            :x="b.x + 9"
            :y="b.y + 7"
            :width="Math.max(0, b.ancho - 20)"
            :height="Math.max(0, b.alto - (b.cabeDetalle ? 26 : 12))"
          >
            <div v-if="b.juntados" class="rotulo">
              <p class="nombre tenue">y {{ b.juntados.cuantos }} grupos más</p>
              <p v-if="b.cabeCifra" class="cifra tenue">{{ dineroCorto(b.juntados.valor) }}</p>
            </div>
            <div v-else class="rotulo">
              <p class="numero">{{ b.numero }}</p>
              <p class="nombre">{{ b.nucleo.etiqueta }}</p>
              <p v-if="b.cabeCifra" class="cifra" :style="{ fontSize: `${cuerpoCifra(b)}px` }">
                {{ dineroCorto(b.nucleo.dinero) }}
              </p>
              <p v-if="b.cabeDetalle" class="detalle">{{ b.nucleo.tamano }} entidades</p>
            </div>
          </foreignObject>
          <!--
            La mezcla del grupo: cuántas administraciones, empresas y
            organizaciones tiene, en los tres colores de tipo. Dice de un
            vistazo si un bloque es un organismo con sus proveedores o una
            red de administraciones que se pagan entre sí.
          -->
          <g v-if="b.cabeDetalle" aria-hidden="true">
            <rect
              v-for="t in tramos(b)"
              :key="t.tipo"
              :x="t.x"
              :y="b.y + b.alto - 15"
              :width="t.w"
              height="4"
              :style="{ fill: `var(--${t.tipo})` }"
            />
          </g>
        </g>
      </svg>
      <p v-else class="vacio">Calculando los grupos…</p>
    </div>
  </div>
</template>

<style scoped>
.mapa-dinero {
  position: relative; width: 100%; height: 100%; overflow: hidden;
  display: flex; flex-direction: column; background: var(--papel);
}
.pie-grafico {
  margin: 0; padding: var(--e3) var(--e4) var(--e2);
  font-size: var(--t-s); color: var(--tinta-2); line-height: 1.45;
  max-width: 90ch;
}
.pie-grafico b { color: var(--tinta); font-weight: 650; }
.lienzo { position: relative; flex: 1; min-height: 0; margin: 0 var(--e3) var(--e3); }

.bloque { cursor: pointer; transition: opacity 0.12s; }
.caja { fill: var(--papel-2); stroke: none; transition: fill 0.12s; }
.bloque:hover .caja { fill: var(--papel-3); }
.bloque.apagado { opacity: 0.5; }
/* El bloque del resto no lleva a ninguna parte: no se puede pulsar. */
.bloque.resto { cursor: default; }
.rayado-fondo { fill: var(--papel); }
.rayado-linea { stroke: var(--filete-suave); stroke-width: 2.5; }
.tenue { color: var(--tinta-3) !important; }

.rotulo { overflow: hidden; height: 100%; pointer-events: none; }
.numero {
  margin: 0 0 2px; font-family: var(--mono); font-size: 10.5px; color: var(--tinta-3);
  line-height: 1.2;
}
.nombre {
  margin: 0; font-size: 12.5px; line-height: 1.22; font-weight: 600; color: var(--tinta);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.cifra {
  margin: 3px 0 0; font-family: var(--serif); font-size: 17px; font-weight: 600;
  color: var(--tinta); line-height: 1.15;
}
.detalle { margin: 1px 0 0; font-size: 11px; color: var(--tinta-3); }

.vacio { position: absolute; inset: 0; display: grid; place-items: center; color: var(--tinta-3); }

@media (max-width: 820px) {
  .ancho { display: none; }
}
</style>
