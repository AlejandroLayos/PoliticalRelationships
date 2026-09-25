<script setup>
/**
 * El mapa del dinero: grupos que contienen a su gente, con cámara.
 *
 * Sustituye a dos vistas que no se hablaban —bloques estáticos y, al pulsar,
 * otra pantalla con un diagrama de nodos— por un solo dibujo que se recorre:
 *
 * - Desde fuera, cada grupo es un círculo y dentro se ven ya sus organismos y
 *   empresas, cada uno del color de su tipo. Se sabe de qué está hecho un
 *   grupo antes de entrar.
 * - Al pulsar, la cámara entra en el círculo (zoom suave de d3,
 *   `interpolateZoom`) y los de dentro se nombran. Se sabe de dónde se viene
 *   porque se ha visto el viaje.
 * - Al pasar por una entidad se dibujan sus caminos de dinero dentro del
 *   grupo, y por ellos corre el dinero del que paga al que cobra. El resto se
 *   apaga. Es la respuesta a «¿con quién se paga éste?» sin cambiar de vista.
 *
 * La cuenta vive en `mapa.js`, probada aparte. Aquí sólo se pinta.
 *
 * ## Rendimiento
 *
 * Son dos mil círculos. La cámara se mueve cambiando UN atributo —el
 * `transform` de la escena— y los grupos van con `v-memo`, así que en cada
 * fotograma del zoom Vue no vuelve a mirar los dos mil: sólo los rótulos, que
 * son unas decenas. Los eventos se escuchan una vez en el lienzo y se
 * reparten por `data-*`, no con dos mil oyentes.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { interpolateZoom } from 'd3-interpolate'
import {
  analizarMapa,
  balanceDe,
  caminosDe,
  curva,
  disponerMapa,
  gruposDelMapa,
  proyectar,
  vistaDe,
} from '../mapa.js'
import { MINIMO_NUCLEO, dineroCorto } from '../nucleos.js'
import { NOMBRE_TIPO, colorTipo, etiquetaEsquema, mezclaDeTipos } from '../esquemas.js'

const props = defineProps({
  datos: { type: Object, required: true },
  minImporte: { type: Number, default: 0 },
  mostrarExpedientes: { type: Boolean, default: false },
  mostrarSueltos: { type: Boolean, default: false },
  soloExtranjero: { type: Boolean, default: false },
  soloPartidos: { type: Boolean, default: false },
  /** La edición: sólo los organismos de esa comunidad y quien cobra de ellos. */
  territorio: { type: String, default: '' },
  /** El grupo en el que está la cámara, o null para verlos todos. */
  nucleoEnfocado: { type: Number, default: null },
  /** El grupo señalado desde la lista de al lado. */
  senalado: { type: Number, default: null },
  /** La entidad señalada desde la lista de al lado. */
  miembroSenalado: { type: String, default: null },
  /**
   * La entidad encendida desde fuera: buscada desde el mapa, o con «Ver en
   * el mapa» desde su ficha. Se enseña fijada, con su ficha a un botón.
   */
  destacado: { type: String, default: null },
})
const emit = defineEmits(['abrir', 'seleccionar', 'analizado', 'senalar', 'destacar'])

const contenedor = ref(null)
const ancho = ref(0)
const alto = ref(0)
let observador = null

const menosMovimiento =
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

// --- Los datos --------------------------------------------------------------

const analisis = computed(() =>
  analizarMapa(props.datos, {
    minImporte: props.minImporte,
    mostrarExpedientes: props.mostrarExpedientes,
    soloExtranjero: props.soloExtranjero,
    soloPartidos: props.soloPartidos,
    territorio: props.territorio,
  }),
)
const grupos = computed(() => gruposDelMapa(analisis.value, { conPequenos: props.mostrarSueltos }))
/*
  La franja de abajo es de la leyenda: los círculos se colocan por encima de
  ella. Colocados en el alto entero, el de abajo del todo quedaba debajo de
  «Administración · Empresa · Partido».
*/
const RESERVA_LEYENDA = 26
const disposicion = computed(() =>
  disponerMapa(analisis.value, grupos.value, ancho.value, Math.max(0, alto.value - RESERVA_LEYENDA)),
)
const porGrupo = computed(() => new Map(disposicion.value.grupos.map((g) => [g.id, g])))
const grupoAbierto = computed(() => porGrupo.value.get(props.nucleoEnfocado) ?? null)
const hayAgrandados = computed(() => disposicion.value.grupos.some((g) => g.agrandado))

/** Lo que se queda sin dibujar por pequeño, con su cifra. */
const pequenos = computed(() => {
  if (props.mostrarSueltos) return null
  const fuera = analisis.value.nucleos.filter((n) => n.tamano < MINIMO_NUCLEO)
  return fuera.length ? { cuantos: fuera.length, dinero: fuera.reduce((s, n) => s + n.dinero, 0) } : null
})

function emitirAnalisis() {
  emit('analizado', {
    nucleos: analisis.value.nucleos,
    totalDinero: analisis.value.totalDinero,
    entidades: analisis.value.entidades,
  })
}
onMounted(emitirAnalisis)
watch(analisis, emitirAnalisis)

// --- La cámara --------------------------------------------------------------

const vista = ref([0, 0, 1])
let animacion = 0

function irA(destino, inmediato = false) {
  cancelAnimationFrame(animacion)
  const desde = vista.value
  if (inmediato || menosMovimiento || !(desde[2] > 1)) {
    vista.value = destino
    return
  }
  const viaje = interpolateZoom(desde, destino)
  // La duración que propone d3 es proporcional a la distancia recorrida;
  // con topes, para que ni un salto corto sea brusco ni uno largo se haga
  // pesado.
  const dura = Math.min(1100, Math.max(480, viaje.duration * 0.75))
  const t0 = performance.now()
  const paso = (ahora) => {
    const t = Math.min(1, (ahora - t0) / dura)
    const e = t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2
    vista.value = viaje(e)
    if (t < 1) animacion = requestAnimationFrame(paso)
  }
  animacion = requestAnimationFrame(paso)
}

/*
  Con una entidad fijada, la tarjeta de abajo tapa el último tramo del
  círculo: la cámara sube un poco para que lo tapado sea el borde vacío y no
  los caminos.
*/
function vistaDelGrupo(g) {
  const v = vistaDe(g, ancho.value, alto.value)
  if (!g || !fijado.value) return v
  const k = Math.min(ancho.value, alto.value) / v[2]
  return [v[0], v[1] + 70 / k, v[2]]
}

watch(
  () => props.nucleoEnfocado,
  () => {
    fijado.value = props.destacado ?? null
    miembroEncima.value = null
    irA(vistaDelGrupo(grupoAbierto.value))
  },
)
// Si cambia el lienzo o los filtros, la cámara se recoloca sin viaje.
watch(disposicion, () => irA(vistaDelGrupo(grupoAbierto.value), true))

const escala = computed(() => Math.min(ancho.value, alto.value) / vista.value[2])
const transformacion = computed(() => {
  const k = escala.value
  const [x, y] = vista.value
  return `translate(${ancho.value / 2 - x * k},${alto.value / 2 - y * k}) scale(${k})`
})

function enPantalla(x, y) {
  return proyectar(x, y, vista.value, ancho.value, alto.value)
}

// --- Lo que se señala ------------------------------------------------------

const grupoEncima = ref(null)
const miembroEncima = ref(null)
/** En pantallas táctiles, la entidad tocada: primer toque señala, segundo abre. */
const fijado = ref(null)
watch(
  () => props.destacado,
  (id) => (fijado.value = id ?? null),
  { immediate: true },
)
/** Soltar lo fijado, y decírselo a quien lo encendió desde fuera. */
function soltar() {
  fijado.value = null
  if (props.destacado) emit('destacar', null)
}
const raton = ref(null)
let ultimoPuntero = 'mouse'

const focoMiembro = computed(() => {
  const id = miembroEncima.value ?? fijado.value ?? props.miembroSenalado
  const m = id ? disposicion.value.porMiembro.get(id) : null
  return m && m.grupo === props.nucleoEnfocado ? m : null
})
const grupoSenalado = computed(() =>
  props.nucleoEnfocado === null ? (grupoEncima.value ?? props.senalado) : null,
)

/** Cuántos caminos se dibujan como mucho, y los que tiene de verdad. */
const TOPE_CAMINOS = 60
const caminosTotales = computed(() => {
  const m = focoMiembro.value
  if (!m) return 0
  const b = balanceDe(analisis.value, m.id)
  return b.aCuantos + b.deCuantos
})

const caminos = computed(() => {
  const m = focoMiembro.value
  if (!m) return []
  const lista = caminosDe(analisis.value, m.id, TOPE_CAMINOS)
  const tope = Math.max(1, ...lista.map((p) => p.importe))
  const pos = disposicion.value.porMiembro
  return lista
    .filter((p) => pos.has(p.de) && pos.has(p.a))
    .map((p) => {
      const de = pos.get(p.de)
      return {
        clave: `${p.de}|${p.a}`,
        d: curva(de, pos.get(p.a)),
        // El camino lleva el color de quien paga: cobrizo si sale de una
        // administración, como en toda la web.
        color: colorTipo(de.esquema),
        grosor: 1.2 + 5 * Math.sqrt(p.importe / tope),
      }
    })
})
const vecinos = computed(() => {
  const m = focoMiembro.value
  if (!m) return new Set()
  const s = new Set()
  for (const p of caminosDe(analisis.value, m.id, TOPE_CAMINOS)) s.add(p.de === m.id ? p.a : p.de)
  return s
})

/** Lo que decide si un grupo tiene que volver a pintarse. */
function firmaGrupo(g) {
  const estado =
    props.nucleoEnfocado === g.id
      ? 'dentro'
      : props.nucleoEnfocado !== null
        ? 'fuera'
        : grupoSenalado.value === g.id
          ? 'encima'
          : grupoSenalado.value !== null
            ? 'apagado'
            : ''
  const foco = focoMiembro.value?.grupo === g.id ? `${focoMiembro.value.id}:${vecinos.value.size}` : ''
  return `${estado}|${foco}`
}

function clasesGrupo(g) {
  const [estado, foco] = firmaGrupo(g).split('|')
  return [estado, { 'con-foco': Boolean(foco) }]
}
function clasesMiembro(m) {
  const f = focoMiembro.value
  if (!f) return null
  if (f.id === m.id) return 'encendido'
  return vecinos.value.has(m.id) ? 'vecino' : null
}

// --- Rótulos ----------------------------------------------------------------

/*
  Los rótulos van en HTML encima del dibujo, no dentro del SVG: así no se
  escalan con la cámara —un nombre a 40 px de alto en pleno zoom no se lee—,
  se cortan a dos renglones con CSS y no tapan el ratón.
*/
const rotulos = computed(() => {
  if (!ancho.value) return []
  const salida = []
  const abierto = grupoAbierto.value
  if (!abierto) {
    for (const g of disposicion.value.grupos) {
      const p = enPantalla(g.x, g.y)
      const R = g.r * p.k
      if (R < 11) continue
      const nivel = R >= 58 ? 'entero' : R >= 30 ? 'medio' : 'numero'
      salida.push({
        clave: `g${g.id}`,
        x: p.x,
        y: p.y,
        nivel,
        numero: g.numero,
        nombre: g.etiqueta,
        cifra: dineroCorto(g.dinero),
        ancho: Math.min(R * 1.55, 230),
        encima: grupoSenalado.value === g.id,
      })
    }
    return salida
  }
  for (const m of abierto.miembros) {
    const p = enPantalla(m.x, m.y)
    const R = m.r * p.k
    if (R < 22) continue
    const f = focoMiembro.value
    salida.push({
      clave: `m${m.id}`,
      x: p.x,
      y: p.y,
      nivel: R >= 36 ? 'miembro' : 'miembro-solo',
      nombre: m.caption,
      cifra: dineroCorto(m.dentro),
      ancho: Math.min(R * 1.6, 200),
      encima: f?.id === m.id,
      // Con una entidad señalada, los rótulos de las que no tienen que ver
      // se apagan con sus círculos: si no, sobre el dibujo apagado quedaban
      // nombres a plena luz y los caminos no se leían.
      apagado: Boolean(f) && f.id !== m.id && !vecinos.value.has(m.id),
    })
  }
  return salida
})

// --- La ficha flotante ------------------------------------------------------

const ficha = computed(() => {
  const m = focoMiembro.value
  if (m && (miembroEncima.value || fijado.value)) {
    const b = balanceDe(analisis.value, m.id)
    return {
      tipo: 'miembro',
      id: m.id,
      nombre: m.caption,
      esquema: m.esquema,
      etiqueta: etiquetaEsquema(m.esquema),
      ...b,
      x: m.x,
      y: m.y,
      r: m.r,
    }
  }
  const gid = props.nucleoEnfocado === null ? grupoEncima.value : null
  const g = gid !== null ? porGrupo.value.get(gid) : null
  if (g) {
    return {
      tipo: 'grupo',
      numero: g.numero,
      nombre: g.etiqueta,
      dinero: g.dinero,
      tamano: g.tamano,
      mezcla: mezclaDeTipos(g.tipos),
      agrandado: g.agrandado,
      x: g.x,
      y: g.y,
      r: g.r,
    }
  }
  return null
})

/** Dónde va la ficha: junto al ratón, o junto a lo señalado con el teclado. */
const posicionFicha = computed(() => {
  const f = ficha.value
  if (!f) return null
  const ancla = raton.value ?? (() => {
    const p = enPantalla(f.x, f.y)
    return { x: p.x + f.r * p.k, y: p.y }
  })()
  const derecha = ancla.x > ancho.value - 300
  const abajo = ancla.y > alto.value - 170
  return {
    left: `${derecha ? ancla.x - 16 : ancla.x + 16}px`,
    top: `${abajo ? ancla.y - 12 : ancla.y + 12}px`,
    transform: `translate(${derecha ? '-100%' : '0'}, ${abajo ? '-100%' : '0'})`,
  }
})

// --- Eventos, repartidos desde el lienzo -----------------------------------

function objetivo(ev) {
  const el = ev.target?.closest?.('[data-m],[data-g]')
  if (!el) return null
  if (el.dataset.m) return { tipo: 'm', id: el.dataset.m, grupo: Number(el.dataset.g) }
  return { tipo: 'g', id: Number(el.dataset.g) }
}

function alMover(ev) {
  if (ev.pointerType === 'touch') return
  const caja = contenedor.value.getBoundingClientRect()
  raton.value = { x: ev.clientX - caja.left, y: ev.clientY - caja.top }
  const o = objetivo(ev)
  if (o?.tipo === 'm' && o.grupo === props.nucleoEnfocado) {
    miembroEncima.value = o.id
    grupoEncima.value = null
  } else if (o?.tipo === 'g' || o?.tipo === 'm') {
    miembroEncima.value = null
    const g = o.tipo === 'g' ? o.id : o.grupo
    grupoEncima.value = props.nucleoEnfocado === null ? g : null
  } else {
    miembroEncima.value = null
    grupoEncima.value = null
  }
}
watch(grupoEncima, (g) => emit('senalar', g))

function alSalir() {
  raton.value = null
  miembroEncima.value = null
  grupoEncima.value = null
}

function alPulsar(ev) {
  const o = objetivo(ev)
  const tactil = ultimoPuntero === 'touch'
  if (o?.tipo === 'm' && o.grupo === props.nucleoEnfocado) {
    // En táctil no hay «pasar por encima»: el primer toque enseña sus
    // caminos y su ficha; el segundo, o el botón de la ficha, la abre.
    if (tactil && fijado.value !== o.id) {
      fijado.value = o.id
      return
    }
    emit('seleccionar', o.id)
    return
  }
  const g = o ? (o.tipo === 'g' ? o.id : o.grupo) : null
  if (g !== null && g !== props.nucleoEnfocado) {
    emit('abrir', g)
    return
  }
  if (fijado.value) {
    soltar()
    return
  }
  // Pulsar fuera de todo, dentro de un grupo, es salir de él.
  if (g === null && props.nucleoEnfocado !== null) emit('abrir', null)
}

function alTeclear(ev) {
  if (ev.key === 'Escape' && props.nucleoEnfocado !== null) {
    emit('abrir', null)
    return
  }
  if (ev.key !== 'Enter' && ev.key !== ' ') return
  const o = objetivo(ev)
  if (!o) return
  ev.preventDefault()
  if (o.tipo === 'm' && o.grupo === props.nucleoEnfocado) emit('seleccionar', o.id)
  else emit('abrir', o.tipo === 'g' ? o.id : o.grupo)
}

/* Con el teclado, el foco hace de ratón: enseña la ficha y los caminos. */
function alEnfocar(ev) {
  raton.value = null
  const o = objetivo(ev)
  if (o?.tipo === 'm') miembroEncima.value = o.id
  else if (o?.tipo === 'g') grupoEncima.value = props.nucleoEnfocado === null ? o.id : null
}

// --- Montaje ----------------------------------------------------------------

/** Los grupos aparecen uno tras otro al llegar, no de golpe. */
const naciendo = ref(!menosMovimiento)

onMounted(() => {
  observador = new ResizeObserver(() => {
    ancho.value = contenedor.value?.clientWidth ?? 0
    alto.value = contenedor.value?.clientHeight ?? 0
  })
  observador.observe(contenedor.value)
  setTimeout(() => (naciendo.value = false), 2200)
})
onBeforeUnmount(() => {
  observador?.disconnect()
  cancelAnimationFrame(animacion)
})

function etiquetaAria(g) {
  return `Grupo ${g.numero}: ${g.etiqueta}, ${dineroCorto(g.dinero)}, ${g.tamano} entidades`
}
</script>

<template>
  <div class="mapa-circulos" :class="{ dentro: grupoAbierto !== null }">
    <!--
      El pie de gráfico, arriba y fuera del dibujo. Dentro de un grupo lo tapa
      la banda con el nombre del grupo y la salida, que ocupa el mismo sitio.
    -->
    <div class="cabeza">
      <p class="pie-grafico ancho">
        <b>Cada círculo es un grupo</b> de organismos y empresas que se pagan
        entre sí; cada punto, uno de ellos. El área es el dinero. Pulsa un
        grupo para entrar; dentro, pasa por una entidad para ver con quién se
        paga.
      </p>
      <p class="pie-grafico estrecho">
        <b>Cada círculo, un grupo</b>; cada punto, un organismo o empresa. El
        área es el dinero. Toca uno para entrar.
      </p>
    </div>

    <div
      ref="contenedor"
      class="lienzo"
      @pointerdown="ultimoPuntero = $event.pointerType"
      @pointermove="alMover"
      @pointerleave="alSalir"
      @click="alPulsar"
      @keydown="alTeclear"
      @focusin="alEnfocar"
    >
      <svg
        v-if="ancho && alto"
        :width="ancho"
        :height="alto"
        role="group"
        aria-label="Grupos de dinero público. Cada círculo es un grupo; pulsa uno para entrar."
        :class="{ naciendo, 'hay-senal': grupoSenalado !== null }"
      >
        <g class="escena" :transform="transformacion">
          <g
            v-for="(g, i) in disposicion.grupos"
            :key="g.id"
            v-memo="[g, firmaGrupo(g), naciendo]"
            class="grupo"
            :class="clasesGrupo(g)"
            :style="{ '--i': Math.min(i, 40) }"
            :data-g="g.id"
            :tabindex="nucleoEnfocado === null ? 0 : -1"
            role="button"
            :aria-label="etiquetaAria(g)"
          >
            <circle class="contorno" :class="{ agrandado: g.agrandado }" :cx="g.x" :cy="g.y" :r="g.r" :data-g="g.id" />
            <circle
              v-for="m in g.miembros"
              :key="m.id"
              class="miembro"
              :class="clasesMiembro(m)"
              :cx="m.x"
              :cy="m.y"
              :r="m.r"
              :style="{ '--c': colorTipo(m.esquema) }"
              :data-m="m.id"
              :data-g="g.id"
              :tabindex="nucleoEnfocado === g.id ? 0 : -1"
              :aria-label="nucleoEnfocado === g.id ? `${m.caption}, ${etiquetaEsquema(m.esquema)}, ${dineroCorto(m.dentro)}` : undefined"
            />
          </g>

          <!--
            Los caminos de la entidad señalada. Se dibujan desde quien paga
            hasta quien cobra y, dibujados, por encima corre el dinero en ese
            sentido: puntos que avanzan del que paga al que cobra.
          -->
          <g v-if="caminos.length" :key="focoMiembro?.id" class="caminos" aria-hidden="true">
            <g v-for="c in caminos" :key="c.clave">
              <path class="camino" :d="c.d" pathLength="1" :style="{ stroke: c.color, strokeWidth: c.grosor }" />
              <path class="flujo" :d="c.d" pathLength="1" :style="{ strokeWidth: Math.max(1.6, c.grosor * 0.7) }" />
            </g>
          </g>
        </g>
      </svg>

      <div class="rotulos" aria-hidden="true">
        <div
          v-for="r in rotulos"
          :key="r.clave"
          class="rotulo"
          :class="[r.nivel, { encima: r.encima, apagado: r.apagado }]"
          :style="{ transform: `translate(${r.x}px, ${r.y}px) translate(-50%, -50%)`, width: `${r.ancho}px` }"
        >
          <span v-if="r.numero" class="numero">{{ r.numero }}</span>
          <span v-if="r.nivel === 'entero' || r.nivel.startsWith('miembro')" class="nombre">{{ r.nombre }}</span>
          <span v-if="r.nivel !== 'numero' && r.nivel !== 'miembro-solo'" class="cifra">{{ r.cifra }}</span>
        </div>
      </div>

      <!-- La ficha flotante: al pasar, junto al ratón; en táctil, abajo y con botón. -->
      <div
        v-if="ficha"
        class="ficha-flotante"
        :class="{ tactil: Boolean(fijado) }"
        :style="fijado ? null : posicionFicha"
        role="status"
      >
        <template v-if="ficha.tipo === 'miembro'">
          <p class="f-tipo">
            <span class="punto-tipo" :style="{ background: colorTipo(ficha.esquema) }" />
            {{ ficha.etiqueta }}
          </p>
          <p class="f-nombre">{{ ficha.nombre }}</p>
          <p v-if="ficha.cobra" class="f-linea">
            Cobra <b>{{ dineroCorto(ficha.cobra) }}</b> de {{ ficha.deCuantos }}
            {{ ficha.deCuantos === 1 ? 'pagador' : 'pagadores' }} del grupo
          </p>
          <p v-if="ficha.paga" class="f-linea">
            Paga <b>{{ dineroCorto(ficha.paga) }}</b> a {{ ficha.aCuantos }}
            {{ ficha.aCuantos === 1 ? 'receptor' : 'receptores' }} del grupo
          </p>
          <p v-if="!ficha.cobra && !ficha.paga" class="f-linea">
            Sus relaciones en el grupo no llevan cifra publicada.
          </p>
          <!-- Lo que no se dibuja se dice: un camino que falta se lee como que no existe. -->
          <p v-if="caminosTotales > TOPE_CAMINOS" class="f-nota">
            Se dibujan los {{ TOPE_CAMINOS }} caminos con más dinero, de {{ caminosTotales }}.
          </p>
          <p v-if="!fijado" class="f-pista">Clic para abrir su ficha</p>
          <div v-else class="f-acciones">
            <button class="boton solido" @click.stop="emit('seleccionar', ficha.id)">Abrir su ficha</button>
            <button class="boton tenue" @click.stop="soltar">Cerrar</button>
          </div>
        </template>
        <template v-else>
          <p class="f-tipo"><span class="puesto-num">{{ ficha.numero }}</span> Grupo</p>
          <p class="f-nombre">{{ ficha.nombre }}</p>
          <p class="f-cifra">{{ dineroCorto(ficha.dinero) }} <span>· {{ ficha.tamano }} entidades</span></p>
          <span class="f-mezcla" aria-hidden="true">
            <i
              v-for="t in ficha.mezcla"
              :key="t.tipo"
              :style="{ width: `${t.parte * 100}%`, background: `var(--${t.tipo})` }"
            />
          </span>
          <p v-if="ficha.agrandado" class="f-linea">
            Dibujado más grande de lo que es, para poder pulsarlo.
          </p>
          <p class="f-pista">Pulsa para entrar</p>
        </template>
      </div>

      <!-- La leyenda: los colores que hay, y cómo leer el tamaño. -->
      <div class="leyenda-mapa">
        <span v-for="t in ['adm', 'emp', 'par']" :key="t">
          <i :style="{ background: `var(--${t})` }" />{{ NOMBRE_TIPO[t] }}
        </span>
        <span v-if="hayAgrandados && !grupoAbierto" class="ancho">
          <i class="trazos" />agrandado para poder verlo
        </span>
        <span v-if="pequenos && !grupoAbierto" class="ancho">
          sin dibujar: {{ pequenos.cuantos }} grupos de menos de {{ MINIMO_NUCLEO }}
          ({{ dineroCorto(pequenos.dinero) }})
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
/*
  `isolation`: los z-index de dentro —leyenda, ficha flotante— se quedan
  dentro. Sin esto, con una ficha abierta encima del mapa, la leyenda del
  mapa se transparentaba por encima de la de la ficha.
*/
.mapa-circulos {
  position: relative; width: 100%; height: 100%; overflow: hidden; isolation: isolate;
  display: flex; flex-direction: column; background: var(--papel);
}
.cabeza { flex: none; height: var(--banda, 3.4rem); display: flex; align-items: center; padding: 0 var(--e4); }
.pie-grafico { margin: 0; font-size: var(--t-s); color: var(--tinta-2); line-height: 1.45; max-width: 100ch; }
.pie-grafico b { color: var(--tinta); font-weight: 650; }
.lienzo { position: relative; flex: 1; min-height: 0; touch-action: manipulation; }
svg { display: block; }
svg:focus { outline: none; }

/* --- Grupos ------------------------------------------------------------- */

.grupo { transition: opacity 0.25s ease; transform-box: fill-box; transform-origin: center; outline: none; }
.contorno {
  fill: var(--papel-2); fill-opacity: 0.55; stroke: var(--filete-medio); stroke-width: 1;
  vector-effect: non-scaling-stroke; cursor: pointer; transition: stroke 0.2s, fill-opacity 0.2s;
}
.contorno.agrandado { stroke-dasharray: 3 3; }
.grupo.encima .contorno, .grupo:focus-visible .contorno { stroke: var(--tinta); fill-opacity: 0.9; }
.grupo:focus-visible .contorno { stroke-width: 2; }
.grupo.apagado { opacity: 0.4; }
.grupo.fuera { opacity: 0.16; }
.grupo.dentro .contorno { cursor: default; fill-opacity: 0.35; }

/* Entran uno tras otro, desde el centro de cada uno. */
.naciendo .grupo { animation: nacer 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) backwards; animation-delay: calc(var(--i) * 22ms); }
@keyframes nacer {
  from { opacity: 0; transform: scale(0.35); }
}

/* --- Entidades ---------------------------------------------------------- */

.miembro {
  fill: var(--c); fill-opacity: 0.32; stroke: var(--c); stroke-width: 1; stroke-opacity: 0.9;
  vector-effect: non-scaling-stroke; pointer-events: none;
  transition: opacity 0.2s ease, fill-opacity 0.2s ease;
}
.grupo.dentro .miembro { pointer-events: all; cursor: pointer; outline: none; }
.grupo.dentro .miembro:hover, .grupo.dentro .miembro:focus-visible { fill-opacity: 0.6; }
.grupo.con-foco .miembro { opacity: 0.14; }
.grupo.con-foco .miembro.vecino { opacity: 1; fill-opacity: 0.5; }
.grupo.con-foco .miembro.encendido {
  opacity: 1; fill-opacity: 0.8; stroke-width: 2;
  filter: drop-shadow(0 0 8px var(--c));
}

/* --- Caminos ------------------------------------------------------------ */

.caminos { pointer-events: none; }
.camino {
  fill: none; stroke-linecap: round; vector-effect: non-scaling-stroke; opacity: 0.85;
  stroke-dasharray: 1; stroke-dashoffset: 1;
  animation: dibujar 0.55s cubic-bezier(0.3, 0.7, 0.3, 1) forwards;
}
/* El dinero corriendo del que paga al que cobra, una vez dibujado el camino. */
.flujo {
  fill: none; stroke: var(--tinta); stroke-linecap: round; vector-effect: non-scaling-stroke;
  stroke-dasharray: 0.004 0.05; opacity: 0;
  animation: aparecer 0.3s 0.45s forwards, fluir 1.6s 0.45s linear infinite;
}
@keyframes dibujar { to { stroke-dashoffset: 0; } }
@keyframes aparecer { to { opacity: 0.9; } }
@keyframes fluir {
  from { stroke-dashoffset: 0.054; }
  to { stroke-dashoffset: 0; }
}

/* --- Rótulos ------------------------------------------------------------ */

.rotulos { position: absolute; inset: 0; pointer-events: none; overflow: hidden; }
.rotulo {
  position: absolute; left: 0; top: 0; display: flex; flex-direction: column; align-items: center;
  text-align: center; gap: 1px; will-change: transform;
}
.rotulo .numero {
  font-family: var(--mono); font-size: 10.5px; color: var(--tinta-2);
  background: color-mix(in srgb, var(--papel) 78%, transparent); padding: 0 4px; border-radius: 2px;
}
.rotulo .nombre {
  font-size: 12px; font-weight: 600; line-height: 1.2; color: var(--tinta);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  text-shadow: 0 0 4px var(--papel), 0 0 2px var(--papel), 0 1px 2px var(--papel);
}
.rotulo .cifra {
  font-family: var(--serif); font-size: 15px; font-weight: 600; color: var(--tinta); line-height: 1.1;
  text-shadow: 0 0 4px var(--papel), 0 0 2px var(--papel);
}
.rotulo.medio .cifra { font-size: 13px; }
.rotulo.miembro .nombre, .rotulo.miembro-solo .nombre { font-size: 11px; }
.rotulo.miembro .cifra { font-size: 13px; }
.rotulo.encima .numero { background: var(--tinta); color: var(--papel); }
.rotulo.apagado { opacity: 0.18; }
.rotulo { transition: opacity 0.2s ease; }
.rotulo .cifra { white-space: nowrap; }

/* --- Ficha flotante ----------------------------------------------------- */

.ficha-flotante {
  position: absolute; z-index: 5; width: max-content; max-width: 280px; pointer-events: none;
  background: color-mix(in srgb, var(--hoja) 94%, transparent);
  backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px);
  border: 1px solid var(--filete-medio); border-radius: var(--radio);
  padding: var(--e3) var(--e3) var(--e2); box-shadow: 0 12px 30px rgba(0, 0, 0, 0.35);
}
.ficha-flotante.tactil {
  left: var(--e3); right: var(--e3); bottom: var(--e3); max-width: none; width: auto;
  pointer-events: auto;
}
.ficha-flotante p { margin: 0; }
.f-tipo {
  display: flex; align-items: center; gap: 0.45em; font-size: var(--t-xs); font-weight: 650;
  letter-spacing: 0.1em; text-transform: uppercase; color: var(--tinta-3);
}
.f-nombre {
  font-family: var(--serif); font-size: var(--t-l); font-weight: 600; color: var(--tinta);
  line-height: 1.2; margin: var(--e1) 0 var(--e2) !important;
}
.f-cifra { font-family: var(--serif); font-size: var(--t-h3); font-weight: 600; color: var(--tinta); }
.f-cifra span { font-family: var(--sans); font-size: var(--t-xs); font-weight: 400; color: var(--tinta-3); }
.f-linea { font-size: var(--t-s); color: var(--tinta-2); line-height: 1.45; }
.f-linea b { color: var(--tinta); font-weight: 650; }
.f-nota { margin-top: var(--e1) !important; font-size: var(--t-xs); color: var(--tinta-3); }
.f-pista { margin-top: var(--e2) !important; font-size: var(--t-xs); color: var(--tinta-3); font-style: italic; font-family: var(--serif); }
.f-mezcla { display: flex; height: 4px; gap: 1px; margin: var(--e2) 0; }
.f-mezcla i { display: block; height: 100%; }
.f-acciones { display: flex; gap: var(--e2); margin-top: var(--e3); }

/* --- Leyenda ------------------------------------------------------------ */

.leyenda-mapa {
  position: absolute; left: var(--e4); bottom: var(--e3); z-index: 2;
  display: flex; flex-wrap: wrap; gap: var(--e1) var(--e4);
  font-size: var(--t-xs); color: var(--tinta-2); pointer-events: none;
}
.leyenda-mapa span { display: inline-flex; align-items: center; gap: 0.4em; }
.leyenda-mapa i { width: 0.6rem; height: 0.6rem; border-radius: 50%; display: inline-block; }
.leyenda-mapa i.trazos { background: none; border: 1px dashed var(--tinta-2); }

.estrecho { display: none; }
@media (max-width: 820px) {
  .ancho, .leyenda-mapa .ancho { display: none; }
  .estrecho { display: block; }
  .leyenda-mapa { left: var(--e3); bottom: var(--e2); gap: var(--e1) var(--e3); }
}

@media (prefers-reduced-motion: reduce) {
  .naciendo .grupo, .camino, .flujo { animation: none; }
  .camino { stroke-dashoffset: 0; }
  .flujo { display: none; }
}
</style>
