<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import FlujoDinero from './components/FlujoDinero.vue'
import GrafoRed from './components/GrafoRed.vue'
import MapaDinero from './components/MapaDinero.vue'
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
import { COLOR_POR_ESQUEMA, NOMBRE_ESQUEMA, colorTipo } from './esquemas.js'
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
/** El rótulo del grupo relajado, si la búsqueda ha tenido que relajarse. */
const rotuloRelajado = ref('')
/** Dónde empieza ese grupo, para poner el rótulo una sola vez. */
const primeroRelajado = computed(() => resultados.value.findIndex((r) => r.grado === 1))
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
/** En estrecho los filtros del mapa nacen plegados; en ancho no se pliegan. */
const filtrosAbiertos = ref(false)
/** Los grupos que el mapa de bloques no dibuja por pequeños. */
const gruposPequenos = ref(null)
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

function alAnalizar({ nucleos: n, totalDinero: d, visibles, entidades, pequenos }) {
  nucleos.value = n
  totalDinero.value = d
  visiblesEnMapa.value = visibles ?? entidades ?? 0
  gruposPequenos.value = pequenos ?? null
}

const hayMapa = computed(() => Boolean(grafoEntero.value?.nodes?.length))

/**
 * Las vistas de red van en el visor oscuro (docs/diseno.md §5): los nodos se
 * iluminan al pasar, y una luz sólo se ve sobre negro. El mapa de bloques y
 * la ficha son papel: se leen, no se exploran.
 */
const enVisor = computed(
  () =>
    (vista.value === 'mapa' && nucleoEnfocado.value !== null) ||
    vista.value === 'vecindario' ||
    (!hayMapa.value && vista.value !== 'ficha'),
)

/** «25 de septiembre de 2026»: la fecha de la edición, como en un periódico. */
const fechaEdicion = computed(() =>
  instantanea.value?.generado
    ? new Date(instantanea.value.generado).toLocaleDateString('es-ES', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      })
    : '',
)

/**
 * La sigla con que se conoce cada fuente, para su sello.
 *
 * «Base de Datos Nacional de Subvenciones» no cabe en un sello; BDNS es como
 * la llama todo el que la usa, y el nombre entero está en el detalle.
 */
const SIGLAS = { bdns: 'BDNS', placsp: 'PLACSP', tcu: 'Tribunal de Cuentas' }
function siglaFuente(f) {
  return SIGLAS[f.id] ?? f.name
}

/**
 * Los tipos de entidad que hay dentro del grupo abierto, de más a menos.
 *
 * Agrupados POR COLOR, no por esquema: «Empresa» y «Persona jurídica»
 * comparten el azul a propósito —son lo mismo para quien mira un mapa de
 * dinero—, y enumerarlos por separado ponía dos entradas del mismo color en
 * la leyenda, que es justo lo que una leyenda no puede hacer.
 */
const tiposDelGrupo = computed(() => {
  const porColor = new Map()
  const tipos = Object.entries(nucleoAbierto.value?.tipos ?? {}).sort((a, b) => b[1] - a[1])
  for (const [esquema] of tipos) {
    const tono = colorTipo(esquema)
    if (!porColor.has(tono)) porColor.set(tono, [])
    porColor.get(tono).push(NOMBRE_ESQUEMA[esquema] ?? esquema)
  }
  return [...porColor.entries()].map(([color, nombres]) => ({
    color,
    nombre: nombres.join(' o ').toLowerCase().replace(/^./, (c) => c.toUpperCase()),
  }))
})

/** El grupo que se está mirando por dentro, si se ha entrado en alguno. */
const nucleoAbierto = computed(() =>
  nucleoEnfocado.value === null ? null : (nucleos.value.find((n) => n.id === nucleoEnfocado.value) ?? null),
)

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

/**
 * ¿La instantánea lleva algún vínculo que no sea dinero?
 *
 * Propiedad, cargos y participaciones vendrían del Registro Mercantil, que
 * todavía no está ingerido. Se comprueba mirando los esquemas de verdad y no
 * con una constante, para que el aviso desaparezca solo el día que entren.
 */
const ESQUEMAS_DE_CONTROL = new Set(['Ownership', 'Directorship', 'Membership', 'Associate'])
const hayVinculosDeControl = computed(() =>
  (grafoEntero.value?.edges ?? []).some((a) => ESQUEMAS_DE_CONTROL.has(a.schema)),
)

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
      rotuloRelajado.value = r.rotuloRelajado ?? ''
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
    <!--
      La franja de edición.

      Un periódico no dice «instantánea, no es una consulta en vivo»: dice
      «edición del 25 de septiembre». Es lo mismo —una foto de un día, no un
      grifo abierto— dicho como lo entiende cualquiera, y además fecha lo que
      se está leyendo, que es lo primero que hay que saber de un dato público.

      Lo demás —de dónde sale, qué cubre, qué NO lleva— queda a un clic, pero
      a la vista: antes era un párrafo fijo de cuatro líneas en todas las
      vistas y en un móvil se comía la primera pantalla.
    -->
    <div v-if="instantanea && !esDemo" class="franja">
      <div class="franja-linea">
        <span class="franja-edicion">
          <span class="ancho">Edición del </span>{{ fechaEdicion }}
        </span>
        <span class="franja-fuentes ancho">
          <span
            v-for="f in instantanea.fuentesConDatos ?? instantanea.fuentes"
            :key="f.id ?? f.name"
            class="sello"
          >{{ siglaFuente(f) }}</span>
        </span>
        <details class="franja-mas">
          <summary><span class="ancho">De dónde salen estos datos</span><span class="estrecho">Las fuentes</span></summary>
          <div class="franja-detalle">
            <p>
              Documentos oficiales de
              {{ (instantanea.fuentesConDatos ?? instantanea.fuentes).map((f) => f.name).join(', ') }},
              descargados y enlazados cada noche. Es una edición, no una
              consulta en vivo: lo que ves es lo que había publicado ese día.
              Cada cifra lleva el documento del que salió.
            </p>
            <!--
              Lo que cubre, con los dos números que se leen en la portada: el
              mapa y el buscador. Una versión anterior decía «la base tiene
              23.892 entidades y el buscador las cubre todas», que era falso
              —las 23.892 incluyen los expedientes, que son papeles— y
              contradecía la cifra de arriba.
            -->
            <p v-if="instantanea.truncado">
              El mapa dibuja
              {{ (indice?.enMapa ?? 0).toLocaleString('es-ES') }}
              entidades, las de más dinero, para que el navegador pueda con él.
              El buscador cubre las
              {{ (indice?.total ?? 0).toLocaleString('es-ES') }} que mueven
              dinero público en esta edición.
            </p>
            <!--
              Lo que NO hay. Un hueco que el lector no conoce se lee como un
              hecho: quien busca una empresa y no ve ningún vínculo con un
              partido puede concluir que no lo hay. Sale de mirar los esquemas
              que hay de verdad en la edición, así que desaparece solo el día
              que entre el Registro Mercantil.
            -->
            <p v-if="!hayVinculosDeControl" class="nota">
              Esta edición sólo lleva dinero público —adjudicaciones,
              subvenciones y expedientes del Tribunal de Cuentas—. No lleva
              propiedad de empresas, cargos ni consejos de administración: no
              ver un vínculo aquí no significa que no exista, sino que estas
              fuentes no lo publican.
            </p>
          </div>
        </details>
      </div>
      <p v-if="instantanea.fuentesSinDatos?.length" class="fuente-caida">
        Hoy falta {{ instantanea.fuentesSinDatos.map((f) => f.name).join(' y ') }}:
        no respondió al preparar esta edición, así que no incluye sus datos.
      </p>
    </div>

    <div v-else-if="esDemo" class="franja franja-demo">
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
      <!--
        La marca: dos nodos y un trazo. El de la izquierda con el color de
        la administración y el de la derecha con el de la empresa, así que el
        propio logotipo dice lo que la web enseña —dinero público que va de un
        sitio a otro— con los mismos colores con que lo enseña.
      -->
      <a class="marca" href="./" @click.prevent="volverAlMapa">
        <svg class="logo" viewBox="0 0 40 24" aria-hidden="true">
          <path d="M7 16 C 15 2, 25 2, 33 12" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          <circle cx="7" cy="16" r="4.2" fill="var(--adm)" />
          <circle cx="33" cy="12" r="4.2" fill="var(--emp)" />
        </svg>
        <span class="marca-texto">
          <span class="marca-nombre">Sinapsis</span>
          <!--
            Antes: «Financiación e influencia en la política española». La
            influencia no está en los datos —no hay propiedad ni cargos, ver
            la franja—, y un lema no puede prometer lo que la web no enseña.
            Esto es lo que enseña.
          -->
          <span class="marca-lema">El dinero público, de quién sale y a quién llega</span>
        </span>
      </a>

      <div class="buscador">
        <svg class="lupa" viewBox="0 0 20 20" aria-hidden="true">
          <circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" stroke-width="1.6" />
          <path d="M12.6 12.6 L17 17" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
        </svg>
        <input
          v-model="consulta"
          type="search"
          placeholder="Un ayuntamiento, una empresa, un partido…"
          aria-label="Buscar entidad"
          :aria-activedescendant="resaltado >= 0 ? `sug-${resaltado}` : undefined"
          @keydown.down.prevent="mover(1)"
          @keydown.up.prevent="mover(-1)"
          @keydown.enter.prevent="abrirResaltado"
          @keydown.esc="resultados = []"
        />
        <ul v-if="resultados.length" class="sugerencias">
          <template v-for="(r, i) in resultados" :key="r.id">
            <!--
              El grupo flojo va separado y con su rótulo. La contratación se
              publica por ÓRGANO, no por ayuntamiento, así que «ayuntamiento
              de Móstoles» encuentra una junta de gobierno y nada más; al
              relajar la búsqueda salen también el hospital de allí y las
              empresas de allí. Mezclados sin avisar, quien busca piensa que
              el buscador se ha equivocado, no que le están enseñando lo que
              hay alrededor.
            -->
            <li v-if="rotuloRelajado && r.grado === 1 && primeroRelajado === i" class="separador">
              {{ rotuloRelajado }}
            </li>
            <li :id="`sug-${i}`">
            <button :class="{ resaltada: i === resaltado }" @click="elegir(r.id)">
              <span class="punto" :style="{ background: colorTipo(r.schema) }" />
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
          </template>
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
          Nada con «{{ consulta.trim() }}» en lo publicado hasta hoy.
          <span>Prueba con una sola palabra del nombre oficial: los organismos
          salen como órgano de contratación, no por su nombre corriente.</span>
        </p>
      </div>

      <!--
        La navegación es de secciones, como en un periódico: siempre las dos,
        y la que se está leyendo, subrayada. Antes eran botones que aparecían
        y desaparecían según la vista —«← Portada» sólo fuera de la portada,
        «Mapa» sólo fuera del mapa—, así que no había manera de saber dónde
        estabas mirando la cabecera.
      -->
      <nav v-if="hayMapa" class="secciones" aria-label="Secciones">
        <a
          href="./"
          :aria-current="vista === 'portada' ? 'page' : undefined"
          @click.prevent="volverAlMapa"
        >Portada</a>
        <a
          href="?v=mapa"
          :aria-current="vista === 'mapa' ? 'page' : undefined"
          @click.prevent="verMapa"
        ><span class="ancho">Mapa del dinero</span><span class="estrecho">Mapa</span></a>
      </nav>
    </header>

    <!--
      La barra de la vista: los controles de lo que se está mirando, y sólo
      ésos, debajo del filete. Antes iban en la misma fila que la marca y la
      navegación, todos con el mismo peso, y en el mapa eran siete cosas en
      línea sin que se supiera cuáles llevaban a otra página y cuáles
      cambiaban el dibujo.
    -->
    <div v-if="hayMapa && vista !== 'portada'" class="barra-vista">
      <template v-if="vista === 'mapa'">
        <!--
          En un teléfono los filtros van plegados: son ajustes, no la puerta,
          y abiertos se comían media pantalla. En ancho siempre a la vista.
        -->
        <button
          class="boton tenue estrecho"
          :class="{ puesto: filtrosPuestos.length }"
          :aria-expanded="filtrosAbiertos"
          @click="filtrosAbiertos = !filtrosAbiertos"
        >
          Filtros<span v-if="filtrosPuestos.length"> ({{ filtrosPuestos.length }})</span>
        </button>
        <div class="filtros" :class="{ plegados: !filtrosAbiertos }">
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
        </div>
      </template>

      <template v-else-if="vista === 'ficha'">
        <span class="barra-rotulo">Ficha</span>
        <!--
          Sin red que enseñar no hay vecindario al que bajar: pulsarlo daría
          «entidad no encontrada», que parece un fallo y es lo contrario.
        -->
        <button
          v-if="!fueraDelMapa"
          class="boton tenue"
          title="La red alrededor de esta entidad, contrato a contrato, y el documento de cada dato"
          @click="verProcedencia"
        >
          Ver sus conexiones
        </button>
      </template>

      <template v-else-if="vista === 'vecindario'">
        <span class="barra-rotulo">Conexiones</span>
        <button v-if="seleccionId" class="boton tenue" @click="enfocar(seleccionId)">
          ← Volver a la ficha
        </button>
        <label class="control">
          Saltos
          <select v-model.number="profundidad">
            <option :value="1">1</option>
            <option :value="2">2</option>
            <option :value="3">3</option>
          </select>
        </label>
      </template>
    </div>

    <main>
      <div class="vista-grafo">
      <div class="lienzo-wrap" :class="{ visor: enVisor }">
        <!--
          El mapa no se desmonta al abrir una ficha: recalcular el layout de
          fuerzas de cuatro mil nodos tarda segundos, y volver atrás tiene que
          ser instantáneo o la gente deja de entrar a las fichas. Las demás
          vistas se dibujan ENCIMA.
        -->
        <!--
          Dos mapas, y el orden importa.

          La puerta es el de bloques: un bloque por grupo, el área es el
          dinero, el nombre va escrito dentro. El de nodos dibujaba las 2.428
          entidades a la vez, y un diagrama de nodos se lee hasta unos cien —
          se afinaron tamaños, opacidades y rótulos tres veces y seguía siendo
          una mancha, porque el problema no era el ajuste sino la cantidad.

          El de nodos no se va: se entra en él al pulsar un bloque, y entonces
          dibuja UN grupo —cincuenta entidades— que es donde sí se lee y donde
          la pregunta «quién está conectado con quién» tiene respuesta.
        -->
        <MapaDinero
          v-if="hayMapa && mapaPedido && nucleoEnfocado === null"
          :datos="grafoEntero"
          :min-importe="minImporte"
          :mostrar-expedientes="mostrarExpedientes"
          :solo-extranjero="soloExtranjero"
          :solo-partidos="soloPartidos"
          @abrir="(n) => (nucleoEnfocado = n)"
          @analizado="alAnalizar"
        />
        <MapaNucleos
          v-else-if="hayMapa && mapaPedido"
          :datos="grafoEntero"
          :seleccion="seleccionId"
          :nucleo-enfocado="nucleoEnfocado"
          :min-importe="minImporte"
          :mostrar-expedientes="mostrarExpedientes"
          :mostrar-sueltos="mostrarSueltos"
          :solo-extranjero="soloExtranjero"
          :solo-partidos="soloPartidos"
          :activo="vista === 'mapa'"
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
        <!--
          Dentro de un grupo, lo primero es poder salir. Un botón, con el
          nombre del grupo al lado: sin él, entrar en un bloque era un viaje
          de ida — el botón «Portada» de la cabecera saca de la vista entera,
          no del grupo.
        -->
        <div v-if="vista === 'mapa' && nucleoEnfocado !== null" class="dentro-de">
          <button class="salir" @click="nucleoEnfocado = null">← Todos los grupos</button>
          <!--
            El nombre del grupo, sólo en pantalla ancha: en un teléfono la
            barra se iba a dos renglones y tapaba la fila de arriba del
            dibujo, y ese mismo nombre con su cifra está justo debajo, en la
            cabecera de la columna.
          -->
          <span v-if="nucleoAbierto" class="nombre-grupo ancho">
            {{ nucleoAbierto.etiqueta }}
            <span class="cifra">{{ dineroCorto(nucleoAbierto.dinero) }} · {{ nucleoAbierto.tamano }} entidades</span>
          </span>
        </div>
        <!--
          El recuento se va al pie en la vista de bloques: arriba a la
          izquierda se escribía encima del nombre del bloque más grande, que
          es justo el que ocupa esa esquina.
        -->
        <p v-else-if="vista === 'mapa' && nucleos.length && filtrosPuestos.length" class="recuento">
          <span class="filtrado">
            Filtrado por {{ filtrosPuestos.join(' y ') }}.
            <button class="quitar-filtros" @click="quitarFiltros">Ver el mapa entero</button>
          </span>
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
            <i :style="{ background: colorTipo(esquema) }" />
            {{ NOMBRE_ESQUEMA[esquema] ?? esquema }}
          </span>
          <span v-if="hayInferidas" class="leyenda-inferido">
            <i class="linea-inferida" />Conexión inferida (fina y ámbar)
          </span>
        </div>
        <!--
          Dentro de un grupo manda el tipo de entidad, no el grupo: todos son
          del mismo. Los tipos salen del recuento del propio grupo, no de
          `esquemasEnPantalla`, que mira los datos del vecindario y en esta
          vista viene vacío — la leyenda no salía.
        -->
        <div v-else-if="nucleoEnfocado !== null" class="leyenda">
          <span v-for="t in tiposDelGrupo" :key="t.color">
            <i :style="{ background: t.color }" />
            {{ t.nombre }}
          </span>
          <span>El tamaño es el dinero</span>
        </div>
        <div v-else class="leyenda leyenda-texto">
          <!--
            `span` de texto corrido, no de leyenda: `.leyenda span` es un
            contenedor flex —lo necesitan las entradas con su cuadrito de
            color— y dentro de un flex cada trozo de texto suelto se convierte
            en un elemento aparte. La frase salía partida en tres columnas.
          -->
          <!--
            En un teléfono, la frase entera son seis renglones sobre una
            pantalla en la que el mapa ya sólo tiene media: la explicación
            tapaba lo explicado. Ahí se queda lo imprescindible —qué es un
            bloque y que se puede pulsar— y el detalle se lee en la columna
            de al lado, que en estrecho va justo debajo.
          -->
          <span class="corrida">
            Cada bloque es un grupo de organismos y empresas que se pagan
            entre ellos más que con el resto. El tamaño es el dinero.
            <b>Pulsa un bloque para ver quién está dentro.</b>
            <span class="ancho">
              Son {{ nucleos.length }} grupos, {{ visiblesEnMapa }} entidades y
              {{ dineroCorto(totalDinero) }} en juego.
              <template v-if="gruposPequenos?.cuantos">
                No se dibujan {{ gruposPequenos.cuantos }} grupos de menos de seis
                entidades ({{ dineroCorto(gruposPequenos.dinero) }}): con dos o tres
                no hay grupo que enseñar, y se pueden buscar por su nombre.
              </template>
            </span>
          </span>
        </div>

        <p v-if="vista !== 'mapa' || nucleoEnfocado !== null" class="ayuda">
          {{
            vista === 'mapa'
              ? 'Clic en una entidad para abrir su ficha'
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
  div suyo. En un móvil eso es media pantalla perdida —la barra de
  direcciones sólo se retrae cuando lo que se desplaza es el documento— y en
  iOS `100vh` mide más que lo visible: el final no se alcanzaba nunca. La
  barra espaciadora tampoco hacía nada, porque el foco estaba en el `body`.

  En el mapa sí hace falta alto fijo: el lienzo ocupa lo que queda.
*/
.app { display: flex; flex-direction: column; height: 100vh; height: 100dvh; }
.app.desplaza { height: auto; min-height: 100vh; min-height: 100dvh; }
.app.desplaza main { position: static; flex: none; }
.app.desplaza .vista-grafo { display: none; }
.app.desplaza .portada-encima { position: static; }
.app.desplaza :deep(.portada) { height: auto; overflow: visible; }
/* Buscador y secciones siempre a mano, aunque la página sea larga. */
.app.desplaza .cabecera { position: sticky; top: 0; z-index: 30; }

/* --- Franja de edición --------------------------------------------------- */

.franja {
  font-size: var(--t-xs); color: var(--tinta-3); line-height: 1.45;
  padding: 0.45rem var(--e5);
  border-bottom: 1px solid var(--filete-suave);
}
.franja-linea { display: flex; align-items: center; gap: var(--e3) var(--e4); flex-wrap: wrap; }
.franja-edicion {
  font-family: var(--sans); font-weight: 650; letter-spacing: 0.11em;
  text-transform: uppercase; color: var(--tinta-2);
}
.franja-fuentes { display: inline-flex; gap: var(--e1); flex-wrap: wrap; }
.franja-mas { margin-left: auto; }
.franja-mas summary {
  cursor: pointer; color: var(--tinta-2); list-style: none;
  text-decoration: underline; text-decoration-color: var(--filete-medio);
  text-underline-offset: 0.18em;
}
.franja-mas summary::-webkit-details-marker { display: none; }
.franja-mas summary::after { content: ' ↓'; }
.franja-mas[open] summary::after { content: ' ↑'; }
/*
  El detalle se despliega como una hoja sobre el papel, sin empujar la
  página: abierto en el flujo, bajaba la cabecera entera y con ella el
  buscador.
*/
.franja-mas[open] .franja-detalle {
  position: absolute; z-index: 40; right: var(--e5); margin-top: var(--e2);
  width: min(34rem, calc(100vw - 2rem));
  background: var(--hoja); border: 1px solid var(--filete-medio);
  box-shadow: 0 12px 32px rgba(28, 26, 22, 0.12);
  padding: var(--e4) var(--e5); font-size: var(--t-s); color: var(--tinta-2);
}
.franja-detalle p { margin: 0 0 var(--e3); }
.franja-detalle p:last-child { margin-bottom: 0; }
.franja-detalle .nota { font-size: var(--t-s); }
.fuente-caida {
  margin: var(--e2) 0 0; color: var(--aviso); font-weight: 600;
}
.fuente-caida::before { content: '▲ '; }

.franja-demo {
  background: #fbecc8; color: #5c3d00; border-bottom-color: #e5c47a;
  font-size: var(--t-s);
}
.franja-demo a { color: inherit; margin-left: var(--e2); }

/* --- Cabecera ------------------------------------------------------------ */

/*
  Una cabecera de periódico: la marca a la izquierda, el buscador en medio y
  las secciones a la derecha, y debajo el filete grueso que separa la
  cabecera de la página. El filete no es adorno: es lo que dice «aquí acaba
  lo que es siempre igual y empieza lo que estás leyendo».
*/
.cabecera {
  display: grid; align-items: center; gap: var(--e3) var(--e6);
  grid-template-columns: auto minmax(14rem, 34rem) 1fr;
  padding: var(--e4) var(--e5) var(--e3);
  background: var(--papel);
  border-bottom: 3px double var(--filete);
}

.marca {
  display: flex; align-items: center; gap: var(--e3);
  color: var(--tinta); text-decoration: none;
}
.logo { width: 2.5rem; height: 1.5rem; flex: none; color: var(--tinta); }
.marca-texto { display: flex; flex-direction: column; }
.marca-nombre {
  font-family: var(--serif); font-weight: 650; font-size: 1.75rem;
  letter-spacing: -0.025em; line-height: 1; font-optical-sizing: auto;
}
.marca-lema {
  font-family: var(--serif); font-style: italic; font-size: var(--t-s);
  color: var(--tinta-2); margin-top: 0.2rem; white-space: nowrap;
}

.buscador { position: relative; min-width: 0; }
.lupa {
  position: absolute; left: 0.7rem; top: 50%; width: 1rem; height: 1rem;
  transform: translateY(-50%); color: var(--tinta-3); pointer-events: none;
}
.buscador input {
  width: 100%; font: inherit; font-size: var(--t-m); color: var(--tinta);
  padding: 0.55rem 0.8rem 0.55rem 2.2rem;
  background: var(--hoja); border: 1px solid var(--filete-medio); border-radius: var(--radio);
}
.buscador input::placeholder { color: var(--tinta-3); }
.buscador input:focus { outline: none; border-color: var(--tinta); box-shadow: 0 0 0 1px var(--tinta); }

.secciones { display: flex; gap: var(--e5); justify-self: end; }
.secciones a {
  font-family: var(--sans); font-weight: 600; font-size: var(--t-s);
  color: var(--tinta-2); text-decoration: none; padding: 0.3rem 0;
  border-bottom: 2px solid transparent;
}
.secciones a:hover { color: var(--tinta); }
.secciones a[aria-current='page'] { color: var(--tinta); border-bottom-color: var(--tinta); }

/* --- Sugerencias del buscador ------------------------------------------- */

.sugerencias {
  position: absolute; z-index: 40; top: calc(100% + 6px); left: 0; right: 0;
  list-style: none; margin: 0; padding: var(--e1) 0; max-height: 380px; overflow-y: auto;
  background: var(--hoja); border: 1px solid var(--filete-medio);
  box-shadow: 0 14px 36px rgba(28, 26, 22, 0.14);
}
.sugerencias button {
  display: grid; grid-template-columns: auto 1fr auto; align-items: baseline;
  gap: 0 var(--e2); width: 100%; padding: 0.5rem 0.8rem;
  background: none; border: none; color: var(--tinta); cursor: pointer; text-align: left; font: inherit;
}
.sugerencias button:hover,
.sugerencias button.resaltada { background: var(--papel-2); }
.sugerencias button.resaltada { box-shadow: inset 3px 0 0 var(--tinta); }
.separador {
  padding: var(--e3) 0.8rem var(--e1); border-top: 1px solid var(--filete-suave); margin-top: var(--e1);
  font-size: var(--t-xs); font-weight: 650; letter-spacing: 0.1em; text-transform: uppercase;
  color: var(--tinta-3);
}
.punto { width: 0.55rem; height: 0.55rem; border-radius: 50%; flex: none; align-self: center; }
/*
  Dos renglones como mucho. «Área de Gobierno de Políticas Sociales, Familia e
  Igualdad del Ayuntamiento de Madrid» ocupaba CINCO en el desplegable, así
  que tres sugerencias llenaban la pantalla y no se podían comparar.
*/
.nombre {
  font-size: var(--t-m); min-width: 0; line-height: 1.3;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
}
.mueve {
  font-size: var(--t-s); color: var(--tinta); font-weight: 650;
  font-variant-numeric: tabular-nums; white-space: nowrap;
}
.tipo { grid-column: 2 / -1; font-size: var(--t-xs); color: var(--tinta-3); }
.sin-resultados {
  position: absolute; z-index: 40; top: calc(100% + 6px); left: 0; right: 0; margin: 0;
  padding: var(--e3) 0.9rem;
  background: var(--hoja); border: 1px solid var(--filete-medio);
  box-shadow: 0 14px 36px rgba(28, 26, 22, 0.14);
  font-family: var(--serif); font-size: var(--t-m); color: var(--tinta);
}
.sin-resultados span {
  display: block; margin-top: var(--e1);
  font-family: var(--sans); font-size: var(--t-xs); color: var(--tinta-3); line-height: 1.45;
}
.pie-sugerencias {
  font-size: var(--t-xs); color: var(--tinta-3); line-height: 1.4;
  padding: var(--e2) 0.8rem; border-top: 1px solid var(--filete-suave); margin-top: var(--e1);
}

/* --- Barra de la vista --------------------------------------------------- */

.barra-vista {
  display: flex; align-items: center; gap: var(--e3) var(--e5); flex-wrap: wrap;
  padding: var(--e2) var(--e5); min-height: 2.9rem;
  background: var(--papel); border-bottom: 1px solid var(--filete-suave);
  font-size: var(--t-s);
}
.barra-rotulo {
  font-family: var(--serif); font-weight: 650; font-size: var(--t-l); color: var(--tinta);
}
.filtros { display: contents; }
.grupo { display: flex; align-items: center; gap: var(--e3); }
.grupo + .grupo, .control + .grupo { padding-left: var(--e5); border-left: 1px solid var(--filete-suave); }
.rotulo {
  font-size: var(--t-xs); font-weight: 650; letter-spacing: 0.1em;
  text-transform: uppercase; color: var(--tinta-3);
}
.control { display: flex; align-items: center; gap: var(--e2); color: var(--tinta-2); }
.control select {
  font: inherit; color: var(--tinta); background: var(--hoja);
  border: 1px solid var(--filete-medio); border-radius: var(--radio); padding: 0.25rem 0.4rem;
}
.control.check { cursor: pointer; }
.control.check input { accent-color: var(--tinta); }
.boton.puesto { border-color: var(--tinta); color: var(--tinta); }

/* --- Cuerpo -------------------------------------------------------------- */

main { flex: 1; position: relative; min-height: 0; }
.vista-grafo { position: absolute; inset: 0; display: grid; grid-template-columns: 1fr 380px; }
.portada-encima { position: absolute; inset: 0; background: var(--papel); z-index: 5; }
.lienzo-wrap { position: relative; min-height: 0; background: var(--papel); }
.encima { position: absolute; inset: 0; background: var(--papel); }
.lienzo-wrap.visor .encima { background: var(--visor); }

.estado-flotante {
  position: absolute; inset: 0; display: grid; place-items: center; margin: 0;
  font-family: var(--serif); font-style: italic; font-size: var(--t-l);
  color: var(--tinta-3); pointer-events: none;
}
.estado-flotante.error { color: var(--aviso); }

.recorte {
  position: absolute; top: var(--e3); left: 50%; transform: translateX(-50%); margin: 0;
  background: var(--hoja); color: var(--aviso); border: 1px solid var(--filete-medio);
  padding: 0.3rem 0.7rem; font-size: var(--t-xs);
}

/* --- Leyendas y rótulos sobre el dibujo --------------------------------- */

.leyenda {
  position: absolute; bottom: var(--e3); left: var(--e4);
  display: flex; flex-wrap: wrap; gap: var(--e2) var(--e4); max-width: 72%;
  font-size: var(--t-xs); color: var(--tinta-2);
}
/*
  `>` y no descendiente: las entradas con cuadrito de color son flex, pero la
  regla alcanzaba también a los `span` de dentro del texto corrido — y un
  `display: flex` de (0,1,1) le ganaba al `display: none` de `.ancho`, que es
  (0,1,0). El detalle de pantalla ancha salía también en el teléfono.
*/
.leyenda > span { display: flex; align-items: center; gap: 0.35rem; }
.leyenda > span.corrida { display: block; }
.leyenda i { width: 0.55rem; height: 0.55rem; border-radius: 50%; display: inline-block; }
.leyenda i.linea-inferida { width: 18px; height: 2px; border-radius: 1px; background: #e0a33a; }
/*
  La explicación va sobre placa: cae encima del bloque de abajo a la
  izquierda —que es grande y lleva su nombre escrito— y sin fondo se leían
  los dos textos mezclados.
*/
.leyenda-texto {
  max-width: min(76ch, calc(100% - 2rem)); line-height: 1.5; font-size: var(--t-s);
  background: var(--hoja); border: 1px solid var(--filete-suave);
  padding: var(--e2) var(--e3);
}
.leyenda-texto b { color: var(--tinta); }
.ayuda {
  position: absolute; bottom: var(--e3); right: var(--e4); margin: 0;
  font-size: var(--t-xs); color: var(--tinta-3); font-style: italic; font-family: var(--serif);
}

.recuento {
  position: absolute; top: var(--e3); left: var(--e4); margin: 0;
  font-size: var(--t-s); color: var(--tinta-2);
  background: var(--hoja); border: 1px solid var(--filete-suave); padding: var(--e1) var(--e3);
}
.filtrado { color: var(--tinta); }
.quitar-filtros {
  margin-left: var(--e2); background: none; border: none; padding: 0; cursor: pointer;
  font: inherit; color: var(--tinta); text-decoration: underline; text-underline-offset: 0.18em;
}

/* La barra de «dentro de un grupo», en el visor. */
.dentro-de {
  position: absolute; top: var(--e3); left: var(--e4); right: var(--e4); z-index: 2;
  display: flex; align-items: center; gap: var(--e4); flex-wrap: wrap;
}
.salir {
  font: inherit; font-size: var(--t-s); font-weight: 600; cursor: pointer; white-space: nowrap;
  color: var(--tinta); background: var(--papel-2);
  border: 1px solid var(--filete-medio); border-radius: var(--radio); padding: 0.35rem 0.7rem;
}
.salir:hover { border-color: var(--tinta); }
.nombre-grupo {
  font-family: var(--serif); font-size: var(--t-h3); font-weight: 600; color: var(--tinta);
  min-width: 0;
}
.nombre-grupo .cifra {
  font-family: var(--sans); font-size: var(--t-s); color: var(--tinta-2); font-weight: 400;
  margin-left: var(--e2);
}

/* --- Pantalla ancha / estrecha ------------------------------------------ */

.estrecho { display: none; }

@media (max-width: 1100px) {
  .cabecera { grid-template-columns: auto 1fr auto; gap: var(--e3) var(--e4); }
  .marca-lema { display: none; }
}

@media (max-width: 820px) {
  .ancho { display: none; }
  .estrecho { display: inline; }

  .franja { padding: 0.4rem var(--e4); }
  .franja-linea { flex-wrap: nowrap; }
  .franja-mas[open] .franja-detalle { right: var(--e3); left: var(--e3); width: auto; }

  /*
    En estrecho: marca y secciones en un renglón, el buscador en el
    siguiente a todo lo ancho. Antes eran cuatro renglones —marca, lema,
    buscador y una fila por botón— y el primer dato caía bajo el pliegue.
  */
  .cabecera {
    grid-template-columns: 1fr auto; padding: var(--e3) var(--e4) var(--e3);
  }
  .buscador { grid-column: 1 / -1; grid-row: 2; }
  .marca-nombre { font-size: 1.45rem; }
  .logo { width: 2.1rem; height: 1.25rem; }

  .barra-vista { padding: var(--e2) var(--e4); }
  /*
    Los filtros del mapa, plegados. `display: contents` hace que en ancho los
    controles sean hijos directos de la barra; aquí se agrupan y se pliegan.
  */
  .filtros.plegados { display: none; }
  .filtros { display: flex; align-items: center; gap: var(--e3); flex-wrap: wrap; width: 100%; }
  .grupo + .grupo, .control + .grupo { padding-left: 0; border-left: none; }

  .vista-grafo { grid-template-columns: 1fr; grid-template-rows: 58vh 1fr; }
  .ayuda { display: none; }
  .leyenda { max-width: calc(100% - 1.4rem); left: var(--e3); bottom: var(--e2); }
  .leyenda:not(.leyenda-texto) { background: var(--hoja); padding: var(--e1) var(--e2); }
}
</style>
