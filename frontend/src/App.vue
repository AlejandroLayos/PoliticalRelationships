<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import GrafoRed from './components/GrafoRed.vue'
import MapaNucleos from './components/MapaNucleos.vue'
import PanelEntidad from './components/PanelEntidad.vue'
import PanelNucleos from './components/PanelNucleos.vue'
import {
  buscar,
  cargarInstantanea,
  entidad as pedirEntidad,
  estado,
  estadoServidor,
  grafoCompleto,
  vecinos,
} from './api.js'
import { ENTIDAD_INICIAL } from './demo.js'
import { COLOR_POR_ESQUEMA, NOMBRE_ESQUEMA } from './esquemas.js'
import { dineroCorto } from './nucleos.js'

const consulta = ref('')
const resultados = ref([])
const buscando = ref(false)
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

// --- mapa de núcleos ------------------------------------------------------
// `mapa` es la vista por defecto cuando hay instantánea: enseñar la estructura
// entera antes que la ego-red de un nodo cualquiera. La vista de vecindario
// sigue existiendo, pero como lo que es — un detalle al que se baja.
const vista = ref('mapa')
const grafoEntero = ref(null)
const nucleos = ref([])
const nucleoEnfocado = ref(null)
const totalDinero = ref(0)
const visiblesEnMapa = ref(0)
const minImporte = ref(0)
const mostrarExpedientes = ref(false)
const mostrarSueltos = ref(false)
const soloExtranjero = ref(false)

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

let temporizador = null
watch(consulta, (q) => {
  clearTimeout(temporizador)
  if (q.trim().length < 3) {
    resultados.value = []
    return
  }
  temporizador = setTimeout(async () => {
    buscando.value = true
    try {
      resultados.value = (await buscar(q.trim())).results ?? []
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

/** Selección sin recargar el grafo: sólo cambia el foco y la ficha. */
async function enfocar(id) {
  seleccionId.value = id
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

function volverAlMapa() {
  vista.value = 'mapa'
  seleccionId.value = ''
  seleccionado.value = null
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
    vista.value = 'mapa'
  } else {
    await abrir(ENTIDAD_INICIAL) // demostración, y se anuncia como tal
  }
})
</script>

<template>
  <div class="app">
    <!--
      El aviso es permanente y no se puede cerrar mientras se estén enseñando
      datos que no vienen de una fuente real. Publicar un mapa de dinero
      público con datos inventados sin decirlo sería lo contrario de lo que
      este proyecto pretende.
    -->
    <div v-if="instantanea && !esDemo" class="banda-info">
      <strong>Instantánea del {{ new Date(instantanea.generado).toLocaleDateString('es-ES') }}.</strong>
      Datos reales de
      {{ (instantanea.fuentesConDatos ?? instantanea.fuentes).map((f) => f.name).join(', ') }},
      generados por la ingesta automática. No es una consulta en vivo.
      <span v-if="instantanea.fuentesSinDatos?.length" class="fuente-caida">
        ⚠ Hoy falta {{ instantanea.fuentesSinDatos.map((f) => f.name).join(' y ') }}:
        no respondió al generar esta instantánea, así que este mapa no incluye
        sus datos.
      </span>
      <span v-if="instantanea.truncado">
        Se publica la parte del grafo con más dinero, no la base entera
        ({{ instantanea.total }} entidades).
      </span>
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
          placeholder="Buscar empresa, organismo, partido o persona…"
          aria-label="Buscar entidad"
        />
        <ul v-if="resultados.length" class="sugerencias">
          <li v-for="r in resultados" :key="r.id">
            <button @click="abrir(r.id)">
              <span class="punto" :style="{ background: COLOR_POR_ESQUEMA[r.schema] ?? '#8b93a7' }" />
              <span class="nombre">{{ r.caption }}</span>
              <span class="tipo">{{ NOMBRE_ESQUEMA[r.schema] ?? r.schema }}</span>
            </button>
          </li>
        </ul>
        <p v-else-if="consulta.trim().length >= 3 && !buscando" class="sin-resultados">
          Sin resultados.
        </p>
      </div>

      <div v-if="hayMapa" class="controles">
        <button
          v-if="vista === 'vecindario'"
          class="volver"
          @click="volverAlMapa"
        >
          ← Ver el mapa completo
        </button>

        <template v-if="vista === 'mapa'">
          <label class="control">
            Desde
            <select v-model.number="minImporte">
              <option v-for="e in ESCALONES" :key="e.v" :value="e.v">{{ e.t }}</option>
            </select>
          </label>
          <label class="control check">
            <input v-model="mostrarExpedientes" type="checkbox" />
            Ver expedientes
          </label>
          <label class="control check">
            <input v-model="mostrarSueltos" type="checkbox" />
            Relaciones sueltas
          </label>
          <label class="control check" title="Entidades con NIF de no residente (letras N y W) y quien les paga">
            <input v-model="soloExtranjero" type="checkbox" />
            Capital extranjero
          </label>
        </template>

        <label v-else class="control">
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
      <div class="lienzo-wrap">
        <MapaNucleos
          v-if="vista === 'mapa' && hayMapa"
          :datos="grafoEntero"
          :seleccion="seleccionId"
          :nucleo-enfocado="nucleoEnfocado"
          :min-importe="minImporte"
          :mostrar-expedientes="mostrarExpedientes"
          :mostrar-sueltos="mostrarSueltos"
          :solo-extranjero="soloExtranjero"
          @seleccionar="enfocar"
          @analizado="alAnalizar"
        />
        <GrafoRed
          v-else
          :datos="datos"
          :seleccion="seleccionId"
          @seleccionar="enfocar"
          @expandir="abrir"
        />

        <p v-if="arrancando || cargando" class="estado-flotante">Cargando…</p>
        <p v-else-if="error" class="estado-flotante error">{{ error }}</p>
        <p v-else-if="vista === 'vecindario' && !datos.nodes.length" class="estado-flotante">
          Busca una entidad para empezar.
        </p>

        <p v-if="vista === 'mapa' && nucleos.length" class="recuento">
          {{ nucleos.length }} núcleos · {{ visiblesEnMapa }} entidades ·
          {{ dineroCorto(totalDinero) }} en juego
        </p>
        <p v-else-if="vista === 'vecindario' && datos.truncated" class="recorte">
          Vista recortada por tamaño: hay más conexiones de las que se muestran.
        </p>

        <div v-if="vista === 'vecindario'" class="leyenda">
          <span v-for="(color, esquema) in COLOR_POR_ESQUEMA" :key="esquema">
            <i :style="{ background: color }" />{{ NOMBRE_ESQUEMA[esquema] ?? esquema }}
          </span>
          <span class="leyenda-inferido"><i class="linea-inferida" />Conexión inferida (fina y ámbar)</span>
        </div>
        <div v-else class="leyenda">
          <span>Cada color es un núcleo · el tamaño es dinero</span>
        </div>

        <p class="ayuda">
          {{ vista === 'mapa' ? 'Clic en un nodo para ver su ficha' : 'Clic para ver · doble clic para expandir' }}
        </p>
      </div>

      <PanelEntidad
        v-if="seleccionado"
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
    </main>
  </div>
</template>

<style scoped>
.app { display: flex; flex-direction: column; height: 100vh; }

.banda-demo {
  background: var(--aviso-fondo); color: var(--aviso-texto);
  padding: 0.55rem 1rem; font-size: 0.82rem; line-height: 1.4;
  border-bottom: 1px solid var(--aviso-borde);
}
.banda-demo a { color: inherit; margin-left: 0.4rem; }

.banda-info {
  background: #16232e; color: #a9cbe4;
  padding: 0.5rem 1rem; font-size: 0.8rem; line-height: 1.4;
  border-bottom: 1px solid #23384a;
}

.cabecera {
  display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap;
  padding: 0.7rem 1rem; border-bottom: 1px solid var(--borde); background: var(--fondo-panel);
}
.marca h1 { font-size: 1.05rem; margin: 0; letter-spacing: -0.01em; }
.marca p { font-size: 0.74rem; color: var(--texto-tenue); margin: 0.1rem 0 0; }

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
.sugerencias button:hover { background: var(--fondo-boton); }
.punto { width: 8px; height: 8px; border-radius: 50%; flex: none; }
.nombre { flex: 1; font-size: 0.86rem; }
.tipo { font-size: 0.7rem; color: var(--texto-tenue); white-space: nowrap; }
.sin-resultados { position: absolute; top: calc(100% + 6px); font-size: 0.8rem; color: var(--texto-tenue); }

.profundidad { font-size: 0.78rem; color: var(--texto-tenue); display: flex; align-items: center; gap: 0.4rem; }
.profundidad select {
  background: var(--fondo-boton); color: var(--texto);
  border: 1px solid var(--borde); border-radius: 5px; padding: 0.3rem 0.4rem;
}

main { flex: 1; display: grid; grid-template-columns: 1fr 340px; min-height: 0; }
.lienzo-wrap { position: relative; min-height: 0; }

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
  main { grid-template-columns: 1fr; grid-template-rows: 55vh 1fr; }
  .leyenda { max-width: 100%; }
}

.controles { display: flex; align-items: center; gap: 0.9rem; flex-wrap: wrap; }
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
.recuento {
  position: absolute; top: 0.6rem; left: 0.9rem; margin: 0;
  font-size: 0.75rem; color: var(--texto-tenue);
  background: rgba(10, 14, 20, 0.72); padding: 0.25rem 0.55rem; border-radius: 6px;
}
</style>
