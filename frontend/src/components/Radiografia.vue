<script setup>
/*
  La radiografía del poder: la entrada de la red de poder cuando no se ha
  pedido ningún nodo. Primero las islas del poder económico —un núcleo, una
  isla, con sus cotizadas dentro—; después las áreas y lo que las une, los
  núcleos en detalle, los medios y sus dueños, y los puentes. Todo nombre se
  pulsa y lleva a la red, centrada en él.
*/
import { computed, ref } from 'vue'
import { AREAS, PROPONENTES, TIPOS_DE_INSTITUCION, nombreCorto, nombrePropio, radiografiaCompleta, sigla, buscar, indiceDeBusqueda, fichaDeEmpresa, fichaDeNucleo } from '../radiografia.js'
import FichaRadiografia from './FichaRadiografia.vue'
import { nombreDeFuente } from '../poder.js'

const props = defineProps({
  cargos: { type: Object, default: null },
  grafo: { type: Object, default: null },
  cargando: { type: Boolean, default: false },
  // La ficha abierta: la clave de una cotizada o el id de un núcleo.
  ficha: { type: String, default: '' },
})
const emit = defineEmits(['centrar', 'ficha'])

const r = computed(() => (props.cargos ? radiografiaCompleta(props.cargos, props.grafo) : null))
const indice = computed(() => (props.cargos ? indiceDeBusqueda(props.cargos) : []))
const consulta = ref('')
const resultados = computed(() => buscar(indice.value, consulta.value))
const corto = (clave) => nombrePropio(nombreCorto(props.cargos?.cotizadas?.[clave]))

const numero = (n) => Number(n ?? 0).toLocaleString('es-ES')
const porcentaje = (p) => `${Number(p).toLocaleString('es-ES', { maximumFractionDigits: 1 })} %`
const millones = (x) =>
  x >= 1e9
    ? `${(x / 1e9).toLocaleString('es-ES', { maximumFractionDigits: 1 })} mil M€`
    : `${(x / 1e6).toLocaleString('es-ES', { maximumFractionDigits: 1 })} M€`
const nombre = (texto) => nombrePropio(texto)
const ir = (clave) => clave && emit('centrar', clave)
/* --- La ficha ------------------------------------------------------------ */
// Una cotizada o un núcleo se abren aquí mismo, sin salir del mapa; la red,
// desde la ficha. Abrir y cerrar pasa por la dirección: atrás la cierra.
const abrirFicha = (id) => emit('ficha', id ?? '')
const fichaActual = computed(() => {
  const id = props.ficha
  if (!id || !r.value) return null
  if (id.startsWith('nucleo:')) {
    const datos = fichaDeNucleo(id, props.cargos, r.value)
    return datos && { tipo: 'nucleo', datos }
  }
  const datos = fichaDeEmpresa(id, props.cargos, r.value)
  return datos && { tipo: 'empresa', datos }
})
/** Del buscador: una cotizada, a su ficha; lo demás, a la red. */
const elegirResultado = (clave) => (props.cargos?.cotizadas?.[clave] ? abrirFicha(clave) : ir(clave))
/** Lleva a una sección de la página, sin tocar la dirección. */
function irA(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

/* --- La entradilla, escrita con los datos ------------------------------- */

const entradilla = computed(() =>
  r.value?.cifras.cotizadas
    ? `Quién es dueño de las grandes empresas y de los medios, quién nombra a los árbitros y a los jueces, y quién pasa de un sitio a otro. Sólo con lo que publican el BOE, la CNMV, la Oficina de Conflictos de Intereses y el Congreso: cada línea lleva a su documento.`
    : '',
)

/* --- Las islas del poder económico -------------------------------------- */

const islas = computed(() => r.value?.islas ?? [])
/**
 * Todas las cotizadas, de la A a la Z, cada una con el color del núcleo que
 * más tiene en ella (o sin color, si no está en ninguno): para encontrar
 * también las que no salen en el mapa, como Repsol.
 */
const todasLasCotizadas = computed(() => {
  const mayor = new Map()
  for (const isla of islas.value) {
    for (const b of isla.burbujas) {
      const x = mayor.get(b.clave)
      if (!x || b.porcentaje > x.porcentaje) mayor.set(b.clave, { tipo: isla.tipo, porcentaje: b.porcentaje })
    }
  }
  return Object.values(props.cargos?.cotizadas ?? {})
    .map((c) => ({ clave: c.clave, nombre: nombrePropio(nombreCorto(c)), tipo: mayor.get(c.clave)?.tipo ?? '' }))
    .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'))
})
const TIPO_DE_ISLA = { estado: 'Estado accionista', grupo: 'Grupo accionista', fortuna: 'Fortuna personal' }
// La cotizada señalada: se ilumina en todas las islas en que está. Con la
// ficha abierta, la suya.
const senaladaAlPasar = ref('')
const senalada = computed({
  get: () => senaladaAlPasar.value || (fichaActual.value?.tipo === 'empresa' ? props.ficha : ''),
  set: (v) => (senaladaAlPasar.value = v),
})
// Con ratón, pasar por encima señala; pulsar (o tocar) abre su ficha.
function pasar(e, b) {
  if (e.pointerType === 'mouse') senalada.value = b.clave
}
// El foco sólo señala si llega con el teclado: un toque también enfoca, y
// entonces el primer toque ya llevaba a la red.
function enfocar(e, b) {
  if (e.target.matches?.(':focus-visible')) senalada.value = b.clave
}
/**
 * El rótulo de una burbuja, tan grande como quepa: en una línea o, si así
 * cabe más grande, en dos. Debajo, el porcentaje, si hay sitio.
 */
function rotuloBurbuja(b) {
  const ancho = 2 * b.r * 0.86
  const cuerpo = (l) => Math.min(15, ancho / (0.56 * l))
  const palabras = b.corto.split(/\s+/)
  let lineas = [b.corto]
  let tam = cuerpo(b.corto.length)
  if (palabras.length > 1) {
    let mejor = null
    for (let k = 1; k < palabras.length; k++) {
      const dos = [palabras.slice(0, k).join(' '), palabras.slice(k).join(' ')]
      const t = Math.min(cuerpo(Math.max(...dos.map((x) => x.length))), b.r / 2.1)
      if (!mejor || t > mejor.t) mejor = { t, dos }
    }
    if (mejor.t > tam * 1.15) {
      lineas = mejor.dos
      tam = mejor.t
    }
  }
  if (tam < 8) {
    tam = 8
    const cabe = Math.max(3, Math.floor(ancho / (0.56 * tam)))
    lineas = lineas.length > 1 ? lineas.map((l) => recortar(l, cabe)) : [recortar(b.corto, cabe)]
  }
  const conPct = b.r >= 24
  const pct = Math.min(tam * 0.85, 12)
  // Centrado el bloque entero: líneas del nombre y, debajo, el porcentaje.
  const alto = lineas.length * tam * 1.05 + (conPct ? pct * 1.15 : 0)
  return { lineas, tam, conPct, pct, y0: -alto / 2 + tam * 0.8 }
}

/* --- El diagrama de áreas ------------------------------------------------ */

const ANCHO = 210
const ALTO = 74
const POS = {
  parlamento: [20, 30],
  justicia: [375, 30],
  medios: [730, 30],
  gobierno: [20, 243],
  estado: [375, 243],
  empresas: [730, 243],
  partidos: [20, 456],
  administracion: [375, 456],
  accionistas: [730, 456],
}
// Cuánto se curva cada flujo, para que no atraviese otra caja.
const CURVA = { 'gobierno>empresas': 0.14, 'accionistas>medios': -0.3, 'estado>medios': -0.12 }
const centro = (a) => [POS[a][0] + ANCHO / 2, POS[a][1] + ALTO / 2]

const seleccionado = ref('')
const flujos = computed(() => {
  const lista = r.value?.flujos ?? []
  return lista.map((f) => {
    const clave = `${f.de}>${f.a}`
    const grosor = 1.5 + 2.6 * Math.log10(f.n + 1)
    let d
    let pos
    if (f.de === f.a) {
      // Un lazo sobre la propia caja.
      const [x, y] = POS[f.de]
      const x1 = x + ANCHO * 0.3
      const x2 = x + ANCHO * 0.7
      d = `M ${x1} ${y} C ${x1 - 10} ${y - 44}, ${x2 + 10} ${y - 44}, ${x2} ${y}`
      pos = [x + ANCHO / 2, y - 36]
      if (f.de === 'empresas') {
        // A la derecha: abajo llega la flecha de los accionistas.
        const xd = x + ANCHO
        const y1 = y + ALTO * 0.25
        const y2 = y + ALTO * 0.75
        d = `M ${xd} ${y1} C ${xd + 48} ${y1 - 12}, ${xd + 48} ${y2 + 12}, ${xd} ${y2}`
        pos = [xd + 38, y + ALTO / 2]
      }
    } else {
      const [x1, y1] = centro(f.de)
      const [x2, y2] = centro(f.a)
      const dx = x2 - x1
      const dy = y2 - y1
      const largo = Math.hypot(dx, dy)
      const k = CURVA[clave] ?? 0
      const cx = (x1 + x2) / 2 + (-dy / largo) * k * largo
      const cy = (y1 + y2) / 2 + (dx / largo) * k * largo
      // La curva, muestreada, entre donde sale de su caja y donde llega a la
      // otra: así la punta queda a la vista.
      const punto = (t) => [(1 - t) ** 2 * x1 + 2 * (1 - t) * t * cx + t ** 2 * x2, (1 - t) ** 2 * y1 + 2 * (1 - t) * t * cy + t ** 2 * y2]
      const dentro = ([x, y], a, m) => x > POS[a][0] - m && x < POS[a][0] + ANCHO + m && y > POS[a][1] - m && y < POS[a][1] + ALTO + m
      const puntos = []
      for (let i = 0; i <= 60; i++) {
        const q = punto(i / 60)
        if (!dentro(q, f.de, 2) && !dentro(q, f.a, 7)) puntos.push(q)
      }
      d = puntos.map(([x, y], i) => `${i ? 'L' : 'M'} ${x.toFixed(1)} ${y.toFixed(1)}`).join(' ')
      pos = [0.25 * x1 + 0.5 * cx + 0.25 * x2, 0.25 * y1 + 0.5 * cy + 0.25 * y2]
    }
    return { ...f, clave, d, grosor, pos, clase: AREAS[f.de]?.clase ?? 'neutro' }
  })
})
const flujoActual = computed(() => flujos.value.find((f) => f.clave === seleccionado.value) ?? null)
function elegir(clave) {
  seleccionado.value = seleccionado.value === clave ? '' : clave
}
const frase = (f) => `${f.frase}: ${numero(f.n)} ${f.unidad[f.n === 1 ? 0 : 1]}${f.importe ? `, ${millones(f.importe)}` : ''}`
const areasPresentes = computed(() => {
  const s = new Set(flujos.value.flatMap((f) => [f.de, f.a]))
  return Object.keys(POS).filter((a) => s.has(a))
})
const claveDeHecho = (h) => h.persona ?? h.cotizada ?? h.titular ?? h.entidad ?? ''

/* --- Núcleos, medios, referencias y puentes ------------------------------ */

const otrosNucleos = (n, cotizada) =>
  (r.value?.enNucleo?.get(cotizada) ?? [])
    .filter((id) => id !== n.id)
    .map((id) => r.value.nucleos.find((x) => x.id === id))
    .filter(Boolean)
const presidenciasDelEstado = computed(() =>
  [...(r.value?.estado?.entries() ?? [])]
    .filter(([, e]) => e.cargos.length)
    .map(([clave, e]) => ({ clave, ultimo: e.cargos[0], n: e.cargos.length })),
)
const medios = computed(() =>
  Object.values(props.cargos?.cotizadas ?? {})
    .filter((c) => c.medio)
    .map((c) => ({ ...c, accionistas: [...(c.accionistas ?? [])].sort((a, b) => b.porcentaje - a.porcentaje) })),
)
/** Quien preside el consejo de una cotizada, según su informe de gobierno. */
/** El nombre de un titular por su clave, del registro de la CNMV. */
const nombreTitular = (clave) => {
  for (const c of Object.values(props.cargos?.cotizadas ?? {})) for (const a of c.accionistas ?? []) if (a.clave === clave) return a.nombre
  return ''
}
const presidenteDe = (c) => (c.consejo ?? []).find((m) => /^presidente\b/i.test(m.cargo ?? '')) ?? null
const GRUPOS_DE_PUENTES = {
  consejos: 'En más de un consejo de administración',
  accionista: 'Personas con participación significativa en más de una cotizada',
  puerta: 'De un alto cargo a una cotizada, con autorización de la OCI',
  estado: 'Quienes presiden el Estado accionista, nombrados por el Gobierno',
}
const puentesPorTipo = computed(() => {
  const g = {}
  for (const p of r.value?.puentes ?? []) (g[p.tipo] ??= []).push(p)
  return g
})
const anio = (f) => (f ? f.slice(0, 4) : '')
const CORTO_PROPONENTE = {
  'Congreso de los Diputados': 'Propone el Congreso',
  Senado: 'Propone el Senado',
  Gobierno: 'Propone el Gobierno',
  'Consejo General del Poder Judicial': 'Propone el CGPJ',
}
const hayJusticia = computed(() => Object.keys(r.value?.justicia?.recuento ?? {}).length > 0)
/** Quién se sienta dónde, una vez por persona: «Isidro Fainé (ACS y Telefónica)». */
function porPersona(lista) {
  const m = new Map()
  for (const x of lista ?? []) {
    const g = m.get(x.persona) ?? { persona: x.persona, nombre: x.nombre, en: [] }
    g.en.push(x)
    m.set(x.persona, g)
  }
  return [...m.values()]
}
const abiertos = ref(new Set())
const abrir = (k) => (abiertos.value = new Set([...abiertos.value, k]))
const recortar = (t, n) => (t.length > n ? `${t.slice(0, n - 1)}…` : t)
</script>

<template>
  <div class="fondo">
  <article class="radiografia">
    <p v-if="!r" class="estado">{{ cargando ? 'Cargando la radiografía…' : 'Esta edición no trae los datos de la red de poder.' }}</p>
    <template v-else>
      <header class="cabeza">
        <p class="antetitulo">Radiografía</p>
        <h1 class="titular">Quién tiene el poder en España</h1>
        <p class="entradilla">{{ entradilla }}</p>
        <div class="buscar-radio" role="search">
          <label for="buscar-radio" class="antetitulo">Buscar a alguien</label>
          <input
            id="buscar-radio"
            v-model="consulta"
            type="search"
            autocomplete="off"
            placeholder="Una persona, una empresa, un accionista…"
            @keydown.enter="resultados.length && elegirResultado(resultados[0].clave)"
          />
          <ul v-if="consulta.trim().length >= 2" class="resultados-radio">
            <li v-for="x in resultados" :key="x.clave">
              <button type="button" @click="elegirResultado(x.clave)">
                <span class="nombre-r">{{ x.nombre }}</span>
                <span class="que-r">{{ x.que }}</span>
              </button>
            </li>
            <li v-if="!resultados.length" class="nada">No está en esta edición.</li>
          </ul>
        </div>
      </header>

      <FichaRadiografia
        v-if="fichaActual"
        :ficha="fichaActual"
        @cerrar="abrirFicha('')"
        @ir="ir"
        @empresa="abrirFicha"
        @nucleo="abrirFicha"
      />

      <!-- 0. Las islas del poder económico -->
      <section v-if="islas.length" class="bloque" aria-labelledby="t-mapa">
        <h2 id="t-mapa" class="seccion">Quién manda en las grandes empresas</h2>
        <p class="nota">
          Cada isla es un núcleo de poder: el Estado, un grupo accionista o una fortuna personal. Dentro, las cotizadas en
          las que tiene al menos un 5 % de los votos, según la CNMV; cuanto mayor la burbuja, más tiene. La que lleva un
          anillo de trazos está en más de una isla: se la disputan. El punto rojo cuenta los ex altos cargos que la Oficina
          de Conflictos de Intereses autorizó a trabajar en ella. Pulsa una cotizada o el nombre de un núcleo para ver su
          ficha: de quién es, quién la preside, quién se sienta en nombre de quién.
        </p>
        <ul class="leyenda-islas">
          <li><span class="muestra k-estado" />El Estado</li>
          <li><span class="muestra k-grupo" />Un grupo accionista</li>
          <li><span class="muestra k-fortuna" />Una fortuna personal</li>
          <li><span class="muestra disputada" />En más de una isla</li>
          <li><span class="muestra puerta">1</span>Ex altos cargos autorizados a trabajar en ella</li>
        </ul>
        <div class="islas" :class="{ todas: abiertos.has('islas') }" @mouseleave="senalada = ''">
          <figure v-for="isla in islas" :key="isla.id" class="isla" :class="`k-${isla.tipo}`">
            <figcaption>
              <span class="tipo-isla">{{ TIPO_DE_ISLA[isla.tipo] }}</span>
              <button type="button" class="nombre-isla" :title="nombre(isla.nombreCompleto)" @click="abrirFicha(isla.id)">{{ isla.nombre }}</button>
              <span v-if="isla.tipo === 'estado' && r.rotulos?.estado" class="sub-isla">{{ r.rotulos.estado }}</span>
            </figcaption>
            <svg
              :viewBox="`${-isla.radio} ${-isla.radio} ${2 * isla.radio} ${2 * isla.radio}`"
              :style="{ width: `${2 * isla.radio}px` }"
              role="group"
              :aria-label="`Las cotizadas de ${isla.nombre}`"
            >
              <circle class="mar" :r="isla.radio" />
              <g
                v-for="b in isla.burbujas"
                :key="b.clave"
                class="burbuja"
                :class="{ disputada: b.tambien.length, senalada: senalada === b.clave, apagada: senalada && senalada !== b.clave }"
                :transform="`translate(${b.x} ${b.y})`"
                tabindex="0"
                role="button"
                :aria-label="`${nombre(b.nombre)}: ${porcentaje(b.porcentaje)}${b.tambien.length ? `; también ${b.tambien.map((t) => t.nombre).join(', ')}` : ''}`"
                @pointerenter="pasar($event, b)"
                @focus="enfocar($event, b)"
                @click="abrirFicha(b.clave)"
                @keydown.enter="abrirFicha(b.clave)"
              >
                <circle v-if="b.tambien.length" class="anillo" :r="b.r + 2.2" />
                <circle class="cuerpo" :r="b.r" />
                <text :y="rotuloBurbuja(b).y0" :font-size="rotuloBurbuja(b).tam">
                  <tspan v-for="(l, k) in rotuloBurbuja(b).lineas" :key="k" x="0" :dy="k ? rotuloBurbuja(b).tam * 1.05 : 0">{{ l }}</tspan>
                  <tspan v-if="rotuloBurbuja(b).conPct" class="pct-b" x="0" :dy="rotuloBurbuja(b).pct * 1.2" :font-size="rotuloBurbuja(b).pct">{{ porcentaje(b.porcentaje) }}</tspan>
                </text>
                <g v-if="b.puertas" class="puerta" :transform="`translate(${b.r * 0.72} ${-b.r * 0.72})`">
                  <circle r="8.5" />
                  <text dy="3.6">{{ b.puertas }}</text>
                </g>
              </g>
            </svg>
          </figure>
        </div>
        <button v-if="islas.length > 6 && !abiertos.has('islas')" type="button" class="mas-boton mas-islas" @click="abrir('islas')">
          Ver los otros {{ islas.length - 6 }} núcleos
        </button>
        <h3 class="antetitulo todas-t">Las {{ todasLasCotizadas.length }} cotizadas, una a una</h3>
        <ul class="todas-cot">
          <li v-for="c in todasLasCotizadas" :key="c.clave">
            <button type="button" :class="c.tipo ? `k-${c.tipo}` : 'sin-nucleo'" @click="abrirFicha(c.clave)">{{ c.nombre }}</button>
          </li>
        </ul>
      </section>

      <section class="bloque resumen">
        <section v-if="r.esencial.length" class="esencial" aria-labelledby="t-esencial">
          <h2 id="t-esencial" class="antetitulo">Lo esencial</h2>
          <ol>
            <li v-for="(e, i) in r.esencial" :key="i">
              <a :href="`#${e.seccion}`" @click.prevent="irA(e.seccion)">{{ e.texto }}</a>
            </li>
          </ol>
        </section>
        <ul class="cifras" aria-label="Lo que cubre esta edición">
          <li><b>{{ numero(r.cifras.cotizadas) }}</b> cotizadas</li>
          <li><b>{{ numero(r.cifras.accionistas) }}</b> accionistas significativos</li>
          <li><b>{{ numero(r.cifras.consejeros) }}</b> consejeros</li>
          <li><b>{{ numero(r.cifras.altosCargos) }}</b> altos cargos del BOE</li>
          <li><b>{{ numero(r.cifras.justicia) }}</b> cargos de las altas instancias judiciales</li>
        </ul>
      </section>

      <!-- 1. Las áreas y lo que las une -->
      <section class="bloque" aria-labelledby="t-areas">
        <h2 id="t-areas" class="seccion">Cómo se enlazan los poderes</h2>
        <p class="nota">
          Cada flecha es un recuento de hechos publicados: nombramientos en el BOE, participaciones en la CNMV,
          autorizaciones de la Oficina de Conflictos de Intereses, contratos y subvenciones. Cuanto más gruesa, más
          hechos. Pulsa una para verlos.
        </p>
        <div class="diagrama">
          <svg viewBox="0 -56 1010 620" role="img" aria-labelledby="t-areas">
            <defs>
              <marker v-for="c in ['adm', 'emp', 'par']" :id="`punta-${c}`" :key="c" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" :class="`relleno-${c}`" />
              </marker>
            </defs>
            <g v-for="f in flujos" :key="f.clave" class="flujo" :class="[`k-${f.clase}`, { activo: f.clave === seleccionado, apagado: seleccionado && f.clave !== seleccionado }]" @click="elegir(f.clave)">
              <path :d="f.d" class="trazo-ancho" />
              <path :d="f.d" class="trazo" :stroke-width="f.grosor" :marker-end="`url(#punta-${f.clase})`" />
              <g :transform="`translate(${f.pos[0]}, ${f.pos[1]})`" class="cifra">
                <rect x="-22" y="-11" width="44" height="22" rx="11" />
                <text text-anchor="middle" dy="4">{{ numero(f.n) }}</text>
              </g>
              <title>{{ frase(f) }}</title>
            </g>
            <g v-for="a in areasPresentes" :key="a" class="area" :class="`k-${AREAS[a].clase}`" :transform="`translate(${POS[a][0]}, ${POS[a][1]})`">
              <rect :width="ANCHO" :height="ALTO" rx="4" />
              <text :x="ANCHO / 2" :y="r.rotulos[a] ? ALTO / 2 - 3 : ALTO / 2 + 6" text-anchor="middle">{{ AREAS[a].nombre }}</text>
              <text v-if="r.rotulos[a]" :x="ANCHO / 2" :y="ALTO / 2 + 18" text-anchor="middle" class="rotulo">{{ recortar(r.rotulos[a], 30) }}</text>
            </g>
          </svg>
        </div>
        <p class="desliza">Desliza de lado para ver el diagrama entero.</p>
        <ol class="flujos">
          <li v-for="f in flujos" :key="f.clave">
            <button type="button" :class="[`k-${f.clase}`, { activo: f.clave === seleccionado }]" :aria-expanded="f.clave === seleccionado" @click="elegir(f.clave)">
              {{ frase(f) }}
            </button>
          </li>
        </ol>
        <div v-if="flujoActual" class="hechos" aria-live="polite">
          <h3>{{ frase(flujoActual) }}</h3>
          <ul>
            <li v-for="(h, i) in flujoActual.hechos.slice(0, 14)" :key="i">
              <button v-if="claveDeHecho(h)" type="button" class="enlace" @click="ir(claveDeHecho(h))">{{ h.texto }}</button>
              <span v-else>{{ h.texto }}</span>
              <span v-if="h.importe" class="dato">{{ millones(h.importe) }}</span>
              <span v-if="h.desde" class="dato">{{ anio(h.desde) }}</span>
              <a v-if="h.url" :href="h.url" target="_blank" rel="noopener" class="fuente">{{ nombreDeFuente(h.fuente) }}</a>
              <span v-else class="fuente">{{ nombreDeFuente(h.fuente) }}</span>
            </li>
            <li v-if="flujoActual.hechos.length > 14" class="mas">y {{ numero(flujoActual.hechos.length - 14) }} más</li>
          </ul>
        </div>
      </section>

      <!-- 1b. Lo que nombra cada Gobierno -->
      <section v-if="r.gobiernos?.some((g) => Object.keys(g.grupos).length)" class="bloque" aria-labelledby="t-gobiernos">
        <h2 id="t-gobiernos" class="seccion">Quién nombra a los árbitros</h2>
        <p class="nota">
          Quien preside los reguladores, las empresas públicas y los órganos consultivos se nombra por Real Decreto del
          Consejo de Ministros; en algunos casos —la CNMC, la CNMV, el Consejo de Seguridad Nuclear, Protección de
          Datos— el Congreso tiene que dar antes su visto bueno. Estos son los que el BOE atribuye a cada Gobierno.
          Donde pone «antes», esa misma persona había estado en el Gobierno, según el mismo BOE. La presidencia del
          Tribunal de Cuentas no se cuenta: la elige su propio Pleno.
        </p>
        <div class="gobiernos">
          <section v-for="g in r.gobiernos.filter((x) => Object.keys(x.grupos).length)" :key="g.persona" class="gobierno">
            <h3>
              <button type="button" class="enlace" @click="ir(`gobierno:${g.persona}`)">Gobierno de {{ g.nombre }}</button>
              <span v-if="g.formacion" class="formacion">{{ g.formacion }}</span>
            </h3>
            <p class="sub">{{ numero(g.altosCargos) }} altos cargos en el BOE · {{ numero(g.ministros) }} ministros</p>
            <div v-for="(titulo, tipo) in TIPOS_DE_INSTITUCION" v-show="g.grupos[tipo]?.length" :key="tipo" class="grupo-nombramientos">
              <h4>{{ titulo }} <span class="n">{{ g.grupos[tipo]?.length }}</span></h4>
              <ul>
                <li v-for="x in (g.grupos[tipo] ?? []).slice(0, abiertos.has(`${g.persona}|${tipo}`) ? 99 : 6)" :key="`${x.persona}|${x.cargo}|${x.desde}`">
                  <button type="button" class="enlace" @click="ir(x.persona)">{{ x.nombre }}</button>
                  <span class="cargo">{{ x.cargo.replace(/^(President[ae]|Gobernador[a]?) del? (la )?/, '') }}</span>
                  <span v-if="x.desde" class="dato">{{ anio(x.desde) }}</span>
                  <span v-if="x.antes" class="antes">antes: {{ x.antes }}</span>
                </li>
              </ul>
              <button
                v-if="(g.grupos[tipo]?.length ?? 0) > 6 && !abiertos.has(`${g.persona}|${tipo}`)"
                type="button"
                class="mas-boton"
                @click="abrir(`${g.persona}|${tipo}`)"
              >y {{ g.grupos[tipo].length - 6 }} más</button>
            </div>
          </section>
        </div>
      </section>

      <!-- 1c. Quién elige a los jueces -->
      <section v-if="hayJusticia" class="bloque" aria-labelledby="t-jueces">
        <h2 id="t-jueces" class="seccion">Quién elige a los jueces</h2>
        <p class="nota">
          Los magistrados del Tribunal Constitucional, por quién los propuso, y cuántos nombramientos de la cúpula
          judicial propuso cada institución, según el BOE. Son nombramientos leídos, no la composición de hoy: quien fue
          nombrado hace años puede no seguir.
        </p>
        <div class="proponentes">
          <section v-for="pr in PROPONENTES" :key="pr" class="proponente">
            <h3>{{ CORTO_PROPONENTE[pr] }}</h3>
            <p class="recuento-just">
              <template v-for="(n, inst) in r.justicia.recuento[pr] ?? {}" :key="inst">
                <span v-if="inst"><b>{{ numero(n) }}</b> {{ inst.replace(/^Tribunal /, 'T. ') }}</span>
              </template>
            </p>
            <h4 v-if="r.justicia.constitucional[pr].length">Al Constitucional</h4>
            <ul>
              <li v-for="m in r.justicia.constitucional[pr]" :key="m.persona + m.desde">
                <button type="button" class="enlace" @click="ir(m.persona)">{{ m.nombre }}</button>
                <span v-if="m.desde" class="dato">{{ anio(m.desde) }}</span>
                <span v-if="m.antes" class="antes">antes: {{ m.antes }}</span>
              </li>
            </ul>
          </section>
        </div>
      </section>

      <!-- 2. Los núcleos -->
      <section class="bloque" aria-labelledby="t-nucleos">
        <h2 id="t-nucleos" class="seccion">Los núcleos del poder económico</h2>
        <p class="nota">
          El núcleo de un accionista son las cotizadas en las que tiene al menos un 5 % de los derechos de voto, si son
          dos o más, según la CNMV. Una misma cotizada puede estar en varios: ahí se disputa su control.
          <template v-if="r.omnipresentes.length">
            Se apartan las gestoras que están en casi todas —{{ r.omnipresentes.map((o) => `${nombre(o.nombre)}, en ${o.en.length}`).join('; ') }}—:
            una cartera repartida por todo el mercado no es un núcleo.
          </template>
        </p>
        <div class="nucleos">
          <section v-for="n in r.nucleos.slice(0, abiertos.has('nucleos') ? 999 : 6)" :key="n.id" class="nucleo" :class="{ 'es-estado': n.estado }">
            <p class="antetitulo">{{ n.estado ? 'El Estado accionista' : n.titulares.some((t) => t.persona) ? 'Una fortuna personal' : 'Un grupo accionista' }}</p>
            <h3>
              <template v-if="n.estado">El Estado</template>
              <template v-else>
                <template v-for="(t, i) in n.titulares" :key="t.clave">
                  <span v-if="i" class="sep"> · </span>
                  <button type="button" class="enlace" @click="ir(t.clave)">{{ nombre(t.nombre) }}</button>
                </template>
              </template>
            </h3>
            <p v-if="n.estado" class="sub">
              <template v-for="(t, i) in n.titulares" :key="t.clave">
                <span v-if="i"> · </span>
                <button type="button" class="enlace" @click="ir(t.clave)">{{ nombre(t.nombre) }}</button>
              </template>
            </p>
            <ul class="barras">
              <li v-for="p in n.participaciones" :key="`${p.titular}|${p.cotizada}`">
                <button type="button" class="enlace cot" @click="abrirFicha(p.cotizada)">{{ corto(p.cotizada) }}</button>
                <span class="barra" :title="`${nombre(p.nombre)}: ${porcentaje(p.porcentaje)}`"><span :style="{ width: `${Math.min(100, p.porcentaje)}%` }" /></span>
                <span class="pct">{{ porcentaje(p.porcentaje) }}</span>
                <span v-if="n.estado" class="quien">{{ nombre(p.nombre) }}</span>
                <span v-for="o in otrosNucleos(n, p.cotizada)" :key="o.id" class="cruce" :title="`También en el núcleo de ${o.nombre}`">+ {{ o.estado ? 'Estado' : nombre(o.titulares[0].nombre) }}</span>
              </li>
            </ul>
            <p v-if="n.estado && presidenciasDelEstado.length" class="cadena">
              <b>Quién lo preside:</b>{{ ' ' }}
              <template v-for="(pr, i) in presidenciasDelEstado" :key="pr.clave">
                <span v-if="i">; </span>
                <button type="button" class="enlace" @click="ir(pr.ultimo.persona)">{{ pr.ultimo.nombre }}</button>
                ({{ pr.ultimo.cargo.replace(/^President[ae] del? /, '') }}, desde {{ anio(pr.ultimo.desde) }}{{ pr.ultimo.gobierno ? `, ${pr.ultimo.gobierno.nombre.replace(/^/, 'Gobierno de ')}` : '' }})
              </template>
              — nombramientos por Real Decreto del Consejo de Ministros.
            </p>
            <p v-if="n.sienta?.length" class="sienta">
              <b>Sienta en los consejos:</b>{{ ' ' }}
              <template v-for="(x, i) in porPersona(n.sienta)" :key="x.persona">
                <span v-if="i">; </span>
                <button type="button" class="enlace" @click="ir(x.persona)">{{ nombre(x.nombre) }}</button>
                ({{ x.en.map((e) => corto(e.cotizada) + (n.estado ? `, por ${sigla(nombre(nombreTitular(e.titular)))}` : '')).join(' y ') }})
              </template>
            </p>
            <details v-if="n.consejeros?.length" class="puentes-nucleo">
              <summary>
                {{ n.consejeros.length === 1 ? 'Una persona se sienta' : `${n.consejeros.length} personas se sientan` }} en uno de sus
                consejos y en el de otra cotizada
              </summary>
              <p>
                <template v-for="(c, i) in n.consejeros" :key="c.clave">
                  <span v-if="i">; </span>
                  <button type="button" class="enlace" @click="ir(c.clave)">{{ nombre(c.nombre) }}</button>
                  ({{ c.en.map((e) => nombre(e.nombre)).join(' y ') }})
                </template>
              </p>
            </details>
          </section>
        </div>
        <button v-if="r.nucleos.length > 6 && !abiertos.has('nucleos')" type="button" class="mas-boton" @click="abrir('nucleos')">
          Ver los otros {{ r.nucleos.length - 6 }} núcleos
        </button>
      </section>

      <!-- 3. Los medios y sus dueños -->
      <section v-if="medios.length" class="bloque" aria-labelledby="t-medios">
        <h2 id="t-medios" class="seccion">Quién es dueño de los medios</h2>
        <p class="nota">Los grupos de comunicación cotizados —así los clasifica la CNMV— y sus accionistas significativos.</p>
        <div class="medios">
          <section v-for="m in medios" :key="m.clave" class="medio">
            <h3><button type="button" class="enlace" @click="abrirFicha(m.clave)">{{ nombre(m.nombre) }}</button></h3>
            <p v-if="presidenteDe(m)" class="preside">
              Lo preside
              <button type="button" class="enlace" @click="ir(presidenteDe(m).clave)">{{ nombre(presidenteDe(m).nombre) }}</button>
              <span v-if="presidenteDe(m).categoria" class="dato">consejero {{ presidenteDe(m).categoria.toLowerCase() }}</span>
            </p>
            <ul class="barras">
              <li v-for="a in m.accionistas" :key="a.clave">
                <button type="button" class="enlace cot" @click="ir(a.clave)">{{ nombre(a.nombre) }}</button>
                <span class="barra"><span :style="{ width: `${Math.min(100, a.porcentaje)}%` }" /></span>
                <span class="pct">{{ porcentaje(a.porcentaje) }}</span>
              </li>
            </ul>
          </section>
        </div>
      </section>

      <!-- 4. Cotizadas con un dueño de referencia -->
      <section v-if="r.referencias.length" class="bloque" aria-labelledby="t-referencias">
        <h2 id="t-referencias" class="seccion">Cotizadas con un dueño de referencia</h2>
        <p class="nota">Las que no están en ningún núcleo, con su mayor accionista significativo.</p>
        <table class="referencias">
          <tbody>
            <tr v-for="c in r.referencias" :key="c.clave">
              <th scope="row"><button type="button" class="enlace" @click="abrirFicha(c.clave)">{{ nombre(c.nombre) }}</button></th>
              <td>
                <button v-if="c.principal" type="button" class="enlace" @click="ir(c.principal.titular)">{{ nombre(c.principal.nombre) }}</button>
                <span v-else class="apagado">sin accionista significativo fuera de las gestoras</span>
              </td>
              <td class="pct">{{ c.principal ? porcentaje(c.principal.porcentaje) : '' }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- 5. Los puentes -->
      <section class="bloque" aria-labelledby="t-puentes">
        <h2 id="t-puentes" class="seccion">Los puentes</h2>
        <p class="nota">
          Quién está en más de un sitio. Cada persona sale sólo en el papel en que la publica su fuente; dos que se llaman
          igual en dos fuentes no se dan por la misma sin una segunda señal.
        </p>
        <div class="puentes">
          <section v-for="(titulo, tipo) in GRUPOS_DE_PUENTES" v-show="puentesPorTipo[tipo]?.length" :key="tipo" class="grupo-puentes">
            <h3>{{ titulo }}</h3>
            <ul>
              <li v-for="p in (puentesPorTipo[tipo] ?? []).slice(0, abiertos.has(`puentes|${tipo}`) ? 999 : 8)" :key="`${tipo}|${p.clave}|${p.detalle[0]}`">
                <button type="button" class="enlace" @click="ir(p.clave)">{{ nombre(p.nombre) }}</button>
                <span class="detalle">{{ p.detalle.map(nombre).join(' · ') }}{{ p.gobierno ? ` · Gobierno de ${p.gobierno}` : '' }}</span>
              </li>
            </ul>
            <button
              v-if="(puentesPorTipo[tipo]?.length ?? 0) > 8 && !abiertos.has(`puentes|${tipo}`)"
              type="button"
              class="mas-boton"
              @click="abrir(`puentes|${tipo}`)"
            >y {{ puentesPorTipo[tipo].length - 8 }} más</button>
          </section>
        </div>
      </section>

      <footer class="pie">
        <button type="button" class="explorar" @click="ir(r.nucleos[0]?.titulares[0]?.clave)">Explorar la red completa →</button>
        <p class="nota">
          Fuentes: BOE (altos cargos y altas instancias judiciales), CNMV (accionistas significativos, consejos y sector),
          Oficina de Conflictos de Intereses (autorizaciones tras el cese), Congreso (declaraciones de actividades) y el mapa
          del dinero público. Lo que no publican, no está.
        </p>
      </footer>
    </template>
  </article>
  </div>
</template>

<style scoped>
.fondo { background: var(--papel); width: 100%; min-height: 100%; }
.radiografia { max-width: 72rem; margin: 0 auto; padding: var(--e6) var(--e5) var(--e8); color: var(--tinta); }
.estado { font-family: var(--sans); color: var(--tinta-3); }
.antetitulo { font-family: var(--sans); font-size: var(--t-xs); letter-spacing: 0.08em; text-transform: uppercase; color: var(--tinta-3); margin: 0 0 var(--e1); }
.titular { font-family: var(--serif); font-size: var(--t-titular); line-height: 1.05; margin: 0 0 var(--e4); font-weight: 600; }
.entradilla { font-family: var(--serif); font-size: var(--t-l); line-height: 1.5; max-width: var(--medida); color: var(--tinta-2); margin: 0 0 var(--e5); }
.buscar-radio { position: relative; max-width: 34rem; margin: 0 0 var(--e4); }
.buscar-radio input { width: 100%; box-sizing: border-box; font: inherit; font-family: var(--sans); font-size: var(--t-m); padding: var(--e2) var(--e3); border: 1px solid var(--filete-medio); border-radius: var(--radio); background: var(--hoja); color: var(--tinta); }
.resultados-radio { position: absolute; z-index: 3; left: 0; right: 0; list-style: none; margin: 2px 0 0; padding: var(--e1) 0; background: var(--hoja); border: 1px solid var(--filete-medio); border-radius: var(--radio); box-shadow: 0 6px 18px rgb(0 0 0 / 0.12); }
.resultados-radio button { all: unset; cursor: pointer; display: flex; flex-direction: column; width: 100%; box-sizing: border-box; padding: var(--e1) var(--e3); font-family: var(--sans); }
.resultados-radio button:hover, .resultados-radio button:focus-visible { background: var(--papel-2); }
.nombre-r { font-size: var(--t-s); color: var(--tinta); }
.que-r { font-size: var(--t-xs); color: var(--tinta-3); }
.resultados-radio .nada { padding: var(--e1) var(--e3); font-family: var(--sans); font-size: var(--t-s); color: var(--tinta-3); }
.esencial { margin: 0 0 var(--e5); max-width: 52rem; }
.esencial ol { margin: var(--e2) 0 0; padding-left: 1.4rem; font-family: var(--serif); font-size: var(--t-l); line-height: 1.45; }
.esencial li { margin-bottom: var(--e2); padding-left: var(--e1); }
.esencial li::marker { font-family: var(--mono); font-size: var(--t-s); color: var(--tinta-3); }
.esencial a { color: var(--tinta); text-decoration: none; border-bottom: 1px solid var(--filete-medio); }
.esencial a:hover, .esencial a:focus-visible { border-bottom-color: var(--tinta); background: var(--papel-2); }
.cifras { list-style: none; display: flex; flex-wrap: wrap; gap: var(--e2) var(--e5); padding: var(--e3) 0; margin: 0; border-top: 2px solid var(--filete); border-bottom: 1px solid var(--filete-suave); font-family: var(--sans); font-size: var(--t-s); color: var(--tinta-2); }
.cifras b { font-family: var(--mono); font-weight: 500; color: var(--tinta); }
.bloque { margin-top: var(--e7); }
.seccion { font-family: var(--serif); font-size: var(--t-h1); margin: 0 0 var(--e2); padding-top: var(--e3); border-top: 2px solid var(--filete); }
.nota { font-family: var(--sans); font-size: var(--t-s); color: var(--tinta-3); max-width: var(--medida); line-height: 1.5; margin: 0 0 var(--e4); }

/* El diagrama */
.diagrama { background: var(--hoja); border: 1px solid var(--filete-suave); border-radius: var(--radio); padding: var(--e3); }
.diagrama svg { width: 100%; height: auto; display: block; font-family: var(--sans); }
.area rect { fill: var(--papel); stroke-width: 2; }
.area.k-adm rect { stroke: var(--adm); }
.area.k-emp rect { stroke: var(--emp); }
.area.k-par rect { stroke: var(--par); }
.area text { font-size: 17px; font-weight: 600; fill: var(--tinta); }
.area text.rotulo { font-size: 12.5px; font-weight: 400; fill: var(--tinta-3); }
.flujo { cursor: pointer; }
.flujo .trazo { fill: none; opacity: 0.75; transition: opacity 0.15s; }
.flujo .trazo-ancho { fill: none; stroke: transparent; stroke-width: 18; }
.flujo.k-adm .trazo { stroke: var(--adm); }
.flujo.k-emp .trazo { stroke: var(--emp); }
.flujo.k-par .trazo { stroke: var(--par); }
.relleno-adm { fill: var(--adm); }
.relleno-emp { fill: var(--emp); }
.relleno-par { fill: var(--par); }
.flujo.apagado .trazo { opacity: 0.15; }
.flujo.apagado .cifra { opacity: 0.3; }
.flujo.activo .trazo, .flujo:hover .trazo { opacity: 1; }
.cifra rect { fill: var(--hoja); stroke: var(--filete-medio); }
.cifra text { font-family: var(--mono); font-size: 13px; fill: var(--tinta); }
.flujos { list-style: none; padding: 0; margin: var(--e4) 0 0; columns: 2 22rem; column-gap: var(--e5); }
.flujos li { break-inside: avoid; margin-bottom: var(--e1); }
.flujos button { all: unset; cursor: pointer; font-family: var(--sans); font-size: var(--t-s); line-height: 1.45; border-left: 3px solid var(--neutro); padding-left: var(--e2); display: block; color: var(--tinta-2); }
.flujos button.k-adm { border-color: var(--adm); }
.flujos button.k-emp { border-color: var(--emp); }
.flujos button.k-par { border-color: var(--par); }
.flujos button.activo, .flujos button:hover, .flujos button:focus-visible { color: var(--tinta); background: var(--papel-2); }
.hechos { margin-top: var(--e4); background: var(--hoja); border: 1px solid var(--filete-suave); border-radius: var(--radio); padding: var(--e3) var(--e4); }
.hechos h3 { font-family: var(--serif); font-size: var(--t-h3); margin: 0 0 var(--e2); }
.hechos ul { list-style: none; margin: 0; padding: 0; font-family: var(--sans); font-size: var(--t-s); }
.hechos li { padding: var(--e1) 0; border-bottom: 1px solid var(--filete-suave); display: flex; flex-wrap: wrap; gap: var(--e2); align-items: baseline; }
.hechos .mas { color: var(--tinta-3); border: 0; }
.dato, .fuente { font-family: var(--mono); font-size: var(--t-xs); color: var(--tinta-3); }
a.fuente { color: var(--tinta-2); }

.enlace { all: unset; cursor: pointer; text-decoration: underline; text-decoration-color: var(--filete-medio); text-underline-offset: 2px; }
.enlace:hover, .enlace:focus-visible { text-decoration-color: var(--tinta); background: var(--papel-2); }

/* El mapa de los núcleos */
.mas-boton.mas-islas { display: none; }
.desliza { display: none; font-family: var(--sans); font-size: var(--t-xs); color: var(--tinta-3); margin: var(--e1) 0 0; }
.leyenda-islas { list-style: none; display: flex; flex-wrap: wrap; gap: var(--e1) var(--e4); padding: 0; margin: 0 0 var(--e4); font-family: var(--sans); font-size: var(--t-xs); color: var(--tinta-3); }
.leyenda-islas li { display: flex; align-items: center; gap: var(--e1); }
.muestra { display: inline-block; width: 0.85rem; height: 0.85rem; border-radius: 50%; }
.muestra.k-estado { background: var(--adm); }
.muestra.k-grupo { background: var(--emp); }
.muestra.k-fortuna { background: var(--par); }
.muestra.disputada { background: var(--tinta-3); box-shadow: 0 0 0 1.5px var(--papel), 0 0 0 3px var(--tinta); outline: none; }
.muestra.puerta { width: 1rem; height: 1rem; background: var(--adm); color: var(--hoja); font-size: 0.6rem; font-weight: 700; text-align: center; line-height: 1rem; }
.islas { display: flex; flex-wrap: wrap; justify-content: center; align-items: flex-end; gap: var(--e5) var(--e5); }
.isla { margin: 0; display: flex; flex-direction: column; align-items: center; max-width: 100%; }
.isla figcaption { display: flex; flex-direction: column; align-items: center; text-align: center; max-width: 18rem; margin-bottom: var(--e1); font-family: var(--sans); }
.tipo-isla { font-size: 0.66rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--tinta-3); }
.nombre-isla { all: unset; font-family: var(--serif); font-size: var(--t-h3); font-weight: 600; line-height: 1.15; color: var(--tinta); }
button.nombre-isla { cursor: pointer; border-bottom: 1px solid transparent; }
button.nombre-isla:hover, button.nombre-isla:focus-visible { border-bottom-color: var(--tinta); }
.sub-isla { font-size: var(--t-xs); color: var(--tinta-3); }
.isla svg { max-width: 100%; height: auto; display: block; overflow: visible; font-family: var(--sans); }
.mar { fill: var(--hoja); stroke: var(--c); stroke-opacity: 0.45; stroke-width: 1.2; }
.k-estado { --c: var(--adm); }
.k-grupo { --c: var(--emp); }
.k-fortuna { --c: var(--par); }
.todas-t { margin: var(--e6) 0 var(--e2); }
.todas-cot { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: var(--e2); }
.todas-cot button { all: unset; cursor: pointer; display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.3rem 0.65rem; border: 1px solid var(--filete-suave); border-radius: 999px; background: var(--hoja); font-family: var(--sans); font-size: var(--t-s); color: var(--tinta); -webkit-tap-highlight-color: transparent; }
.todas-cot button::before { content: ''; width: 0.55rem; height: 0.55rem; border-radius: 50%; background: var(--c, transparent); border: 1px solid var(--c, var(--filete-medio)); }
.todas-cot button:hover, .todas-cot button:focus-visible { border-color: var(--tinta); background: var(--papel-2); }
.burbuja { cursor: pointer; transition: opacity 0.15s; outline: none; }
.burbuja .cuerpo { fill: var(--c); }
.burbuja .anillo { fill: none; stroke: var(--tinta); stroke-width: 1.4; stroke-dasharray: 3 2.4; }
.burbuja text { fill: var(--hoja); text-anchor: middle; font-weight: 600; pointer-events: none; }
.burbuja .pct-b { font-weight: 400; font-family: var(--mono); opacity: 0.9; }
.burbuja.apagada { opacity: 0.22; }
.burbuja.senalada .cuerpo, .burbuja:focus-visible .cuerpo { stroke: var(--tinta); stroke-width: 2.5; }
.burbuja .puerta circle { fill: var(--adm); stroke: var(--hoja); stroke-width: 1.5; }
.burbuja .puerta text { fill: var(--hoja); font-size: 10px; font-weight: 700; }

/* Lo que nombra cada Gobierno */
.gobiernos { display: grid; grid-template-columns: repeat(auto-fit, minmax(22rem, 1fr)); gap: var(--e5); }
.gobierno { border-top: 3px solid var(--adm); padding-top: var(--e3); }
.gobierno h3 { font-family: var(--serif); font-size: var(--t-h3); margin: 0; }
.gobierno .formacion { font-family: var(--mono); font-size: var(--t-xs); color: var(--tinta-3); margin-left: var(--e2); }
.gobierno .sub { font-family: var(--sans); font-size: var(--t-xs); color: var(--tinta-3); margin: var(--e1) 0 var(--e3); }
.grupo-nombramientos h4 { font-family: var(--sans); font-size: var(--t-xs); text-transform: uppercase; letter-spacing: 0.06em; color: var(--tinta-2); margin: var(--e3) 0 var(--e1); }
.grupo-nombramientos h4 .n { font-family: var(--mono); color: var(--tinta-3); }
.grupo-nombramientos ul { list-style: none; margin: 0; padding: 0; font-family: var(--sans); font-size: var(--t-s); }
.grupo-nombramientos li { padding: 3px 0; border-bottom: 1px solid var(--filete-suave); display: flex; flex-wrap: wrap; gap: 0 var(--e2); align-items: baseline; }
.grupo-nombramientos .cargo { color: var(--tinta-2); flex: 1 1 12rem; }
.grupo-nombramientos .antes { flex-basis: 100%; font-size: var(--t-xs); color: var(--adm); }
.mas-boton { all: unset; cursor: pointer; font-family: var(--sans); font-size: var(--t-xs); color: var(--tinta-2); text-decoration: underline; margin-top: var(--e1); }

/* Quién elige a los jueces */
.proponentes { display: grid; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); gap: var(--e4); }
.proponente { border-top: 3px solid var(--par); padding-top: var(--e2); font-family: var(--sans); font-size: var(--t-s); }
.proponente:nth-child(3) { border-top-color: var(--adm); }
.proponente:nth-child(4) { border-top-color: var(--tinta-2); }
.proponente h3 { font-family: var(--serif); font-size: var(--t-h3); margin: 0 0 var(--e2); }
.proponente h4 { font-size: var(--t-xs); text-transform: uppercase; letter-spacing: 0.06em; color: var(--tinta-2); margin: var(--e3) 0 var(--e1); }
.recuento-just { display: flex; flex-direction: column; gap: 2px; margin: 0; color: var(--tinta-2); }
.recuento-just b { font-family: var(--mono); font-weight: 500; color: var(--tinta); }
.proponente ul { list-style: none; margin: 0; padding: 0; }
.proponente li { padding: 3px 0; border-bottom: 1px solid var(--filete-suave); display: flex; flex-wrap: wrap; justify-content: space-between; gap: 0 var(--e2); }
.proponente .antes { flex-basis: 100%; font-size: var(--t-xs); color: var(--adm); }

/* Núcleos */
.nucleos { display: grid; grid-template-columns: repeat(auto-fill, minmax(21rem, 1fr)); gap: var(--e4); }
.nucleo, .medio { border: 1px solid var(--filete-suave); border-top: 3px solid var(--emp); border-radius: var(--radio); padding: var(--e3) var(--e4); background: var(--hoja); }
.nucleo.es-estado { border-top-color: var(--adm); grid-column: 1 / -1; }
.nucleo h3, .medio h3 { font-family: var(--serif); font-size: var(--t-h3); margin: 0 0 var(--e2); line-height: 1.25; }
.nucleo .sub { font-family: var(--sans); font-size: var(--t-s); color: var(--tinta-2); margin: 0 0 var(--e2); }
.sep { color: var(--tinta-3); }
.barras { list-style: none; margin: 0; padding: 0; font-family: var(--sans); font-size: var(--t-s); }
.barras li { display: grid; grid-template-columns: minmax(8rem, 1.3fr) minmax(4rem, 1fr) 4.2rem; gap: var(--e1) var(--e2); align-items: center; padding: 3px 0; }
.es-estado .barras { columns: 2 22rem; column-gap: var(--e6); }
.es-estado .barras li { break-inside: avoid; }
.barras .cot { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.barra { height: 0.55rem; background: var(--papel-3); border-radius: 1px; position: relative; }
.barra span { position: absolute; inset: 0 auto 0 0; background: var(--emp); border-radius: 1px; }
.es-estado .barra span { background: var(--adm); }
.pct { font-family: var(--mono); font-size: var(--t-xs); text-align: right; }
.quien, .cruce { grid-column: 1 / -1; font-size: var(--t-xs); color: var(--tinta-3); margin-top: -2px; }
.cruce { color: var(--emp); }
.cadena, .puentes-nucleo, .sienta { font-family: var(--sans); font-size: var(--t-s); line-height: 1.5; color: var(--tinta-2); margin: var(--e3) 0 0; }
.puentes-nucleo summary { cursor: pointer; font-weight: 600; color: var(--tinta); }
.puentes-nucleo p { margin: var(--e1) 0 0; }
.medio .barras li { grid-template-columns: minmax(11rem, 2fr) minmax(3rem, 1fr) 3.8rem; }
.preside { font-family: var(--sans); font-size: var(--t-s); color: var(--tinta-2); margin: 0 0 var(--e2); display: flex; flex-wrap: wrap; gap: 0 var(--e2); align-items: baseline; }
.medios { display: grid; grid-template-columns: repeat(auto-fill, minmax(21rem, 1fr)); gap: var(--e4); }

/* Referencias y puentes */
.referencias { width: 100%; border-collapse: collapse; font-family: var(--sans); font-size: var(--t-s); }
.referencias th, .referencias td { text-align: left; padding: var(--e1) var(--e2) var(--e1) 0; border-bottom: 1px solid var(--filete-suave); font-weight: 400; }
.referencias th { width: 42%; }
.apagado { color: var(--tinta-3); }
.puentes { display: grid; grid-template-columns: repeat(auto-fill, minmax(22rem, 1fr)); gap: var(--e5); }
.grupo-puentes h3 { font-family: var(--sans); font-size: var(--t-s); font-weight: 600; margin: 0 0 var(--e2); text-transform: uppercase; letter-spacing: 0.05em; color: var(--tinta-2); }
.grupo-puentes ul { list-style: none; margin: 0; padding: 0; font-family: var(--sans); font-size: var(--t-s); }
.grupo-puentes li { padding: var(--e1) 0; border-bottom: 1px solid var(--filete-suave); }
.detalle { display: block; color: var(--tinta-3); font-size: var(--t-xs); }
.pie { margin-top: var(--e7); border-top: 2px solid var(--filete); padding-top: var(--e4); }
.explorar { all: unset; cursor: pointer; font-family: var(--sans); font-weight: 600; padding: var(--e2) var(--e4); border: 1px solid var(--tinta); border-radius: var(--radio); margin-bottom: var(--e3); display: inline-block; }
.explorar:hover, .explorar:focus-visible { background: var(--tinta); color: var(--papel); }

@media (max-width: 48rem) {
  /* En el móvil, el mapa y el diagrama conservan un ancho legible y se
     desplazan de lado: encogidos, sus rótulos no se leen. */
  .diagrama { overflow-x: auto; -webkit-overflow-scrolling: touch; }
  /* En el móvil, las seis islas que más pesan; el resto, a un toque. */
  .islas:not(.todas) .isla:nth-child(n + 7) { display: none; }
  .mas-boton.mas-islas { display: block; margin: var(--e3) auto 0; font-size: var(--t-s); }
  .diagrama svg { min-width: 640px; }
  .desliza { display: block; }
}
@media (max-width: 40rem) {
  .radiografia { padding: var(--e4) var(--e4) var(--e7); }
  .nucleos, .medios, .puentes { grid-template-columns: 1fr; }
  .barras li { grid-template-columns: minmax(7rem, 1.4fr) minmax(3rem, 1fr) 3.8rem; }
}
</style>
