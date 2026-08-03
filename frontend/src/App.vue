<script setup>
import { onMounted, ref, watch } from 'vue'
import GrafoRed from './components/GrafoRed.vue'
import PanelEntidad from './components/PanelEntidad.vue'
import { buscar, cargarInstantanea, entidad as pedirEntidad, estado, estadoServidor, vecinos } from './api.js'
import { ENTIDAD_INICIAL } from './demo.js'
import { COLOR_POR_ESQUEMA, NOMBRE_ESQUEMA } from './esquemas.js'

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
    seleccionado.value = datos.value.nodes.find((n) => n.id === id) ?? null
  }
}

watch(profundidad, () => {
  if (seleccionId.value) abrir(seleccionId.value)
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
    await abrir(estatico.entidadDestacada())
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
      Datos reales de {{ instantanea.fuentes.map((f) => f.name).join(', ') }}, generados por la
      ingesta automática. No es una consulta en vivo.
      <span v-if="instantanea.truncado">
        Se muestran las {{ datos.nodes.length ? instantanea.total : 0 }} entidades más conectadas.
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

      <label class="profundidad">
        Saltos
        <select v-model.number="profundidad">
          <option :value="1">1</option>
          <option :value="2">2</option>
          <option :value="3">3</option>
        </select>
      </label>
    </header>

    <main>
      <div class="lienzo-wrap">
        <GrafoRed
          :datos="datos"
          :seleccion="seleccionId"
          @seleccionar="enfocar"
          @expandir="abrir"
        />

        <p v-if="arrancando || cargando" class="estado-flotante">Cargando…</p>
        <p v-else-if="error" class="estado-flotante error">{{ error }}</p>
        <p v-else-if="!datos.nodes.length" class="estado-flotante">
          Busca una entidad para empezar.
        </p>

        <p v-if="datos.truncated" class="recorte">
          Vista recortada por tamaño: hay más conexiones de las que se muestran.
        </p>

        <div class="leyenda">
          <span v-for="(color, esquema) in COLOR_POR_ESQUEMA" :key="esquema">
            <i :style="{ background: color }" />{{ NOMBRE_ESQUEMA[esquema] ?? esquema }}
          </span>
          <span class="leyenda-inferido"><i class="linea-inferida" />Conexión inferida (fina y ámbar)</span>
        </div>

        <p class="ayuda">Clic para ver · doble clic para expandir</p>
      </div>

      <PanelEntidad :entidad="seleccionado" :datos="datos" @ir="enfocar" @expandir="abrir" />
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
</style>
