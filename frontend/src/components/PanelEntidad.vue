<script setup>
import { computed } from 'vue'
import { COLOR_POR_ESQUEMA, COLOR_POR_DEFECTO, etiquetaArista, etiquetaEsquema, NOMBRE_ESTADO } from '../esquemas.js'

const props = defineProps({
  entidad: { type: Object, default: null },
  datos: { type: Object, default: null },
})
const emit = defineEmits(['ir', 'expandir'])

const color = computed(() =>
  props.entidad ? (COLOR_POR_ESQUEMA[props.entidad.schema] ?? COLOR_POR_DEFECTO) : COLOR_POR_DEFECTO,
)

const porId = computed(() => {
  const m = new Map()
  for (const n of props.datos?.nodes ?? []) m.set(n.id, n)
  return m
})

/** Conexiones del nodo seleccionado, con la dirección y el otro extremo. */
const conexiones = computed(() => {
  if (!props.entidad || !props.datos) return []
  const yo = props.entidad.id
  return (props.datos.edges ?? [])
    .filter((a) => a.source === yo || a.target === yo)
    .map((a) => {
      const saliente = a.source === yo
      const otro = porId.value.get(saliente ? a.target : a.source)
      return { arista: a, saliente, otro }
    })
    .filter((c) => c.otro)
    .sort((x, y) => Number(y.arista.amount ?? 0) - Number(x.arista.amount ?? 0))
})

function importe(a) {
  if (!a.amount) return null
  const n = Number(a.amount)
  if (Number.isNaN(n)) return `${a.amount} ${a.currency ?? ''}`.trim()
  return n.toLocaleString('es-ES', { style: 'currency', currency: a.currency || 'EUR', maximumFractionDigits: 0 })
}
</script>

<template>
  <aside class="panel">
    <p v-if="!entidad" class="vacio">
      Busca una entidad o pulsa un nodo del grafo.
    </p>

    <template v-else>
      <header>
        <span class="punto" :style="{ background: color }" />
        <span class="tipo">{{ etiquetaEsquema(entidad.schema) }}</span>
      </header>
      <h2>{{ entidad.caption }}</h2>
      <p v-if="entidad.nif" class="nif">NIF {{ entidad.nif }}</p>

      <p v-if="entidad.merged_into" class="aviso-fusion">
        Esta ficha quedó absorbida por otra entidad en una fusión.
        <button class="enlace" @click="emit('ir', entidad.merged_into)">Ver la vigente</button>
      </p>

      <button class="expandir" @click="emit('expandir', entidad.id)">
        Expandir su red
      </button>

      <!-- Conexiones ------------------------------------------------------ -->
      <section v-if="conexiones.length">
        <h3>Conexiones <span class="cuenta">{{ conexiones.length }}</span></h3>
        <ul class="conexiones">
          <li v-for="c in conexiones" :key="c.arista.id">
            <button class="otro" @click="emit('ir', c.otro.id)">
              <span class="punto pequeno" :style="{ background: COLOR_POR_ESQUEMA[c.otro.schema] ?? COLOR_POR_DEFECTO }" />
              {{ c.otro.caption }}
            </button>
            <div class="meta">
              <span class="rel">
                {{ c.saliente ? '→' : '←' }} {{ etiquetaArista(c.arista.schema) }}
              </span>
              <span v-if="importe(c.arista)" class="importe">{{ importe(c.arista) }}</span>
            </div>
            <!--
              La confianza y el estado se muestran SIEMPRE, no sólo cuando son
              malos. Es la invariante 5: nada inferido puede presentarse igual
              que un hecho afirmado por la fuente.
            -->
            <div class="fiabilidad" :class="{ inferido: c.arista.status !== 'asserted' }">
              <span class="estado">{{ NOMBRE_ESTADO[c.arista.status] ?? c.arista.status }}</span>
              <span class="barra" :title="`Confianza ${(c.arista.confidence * 100).toFixed(0)}%`">
                <span class="relleno" :style="{ width: `${(c.arista.confidence ?? 0) * 100}%` }" />
              </span>
              <span class="pct">{{ ((c.arista.confidence ?? 0) * 100).toFixed(0) }}%</span>
            </div>
          </li>
        </ul>
      </section>

      <!-- Procedencia ----------------------------------------------------- -->
      <section v-if="entidad.provenance?.length">
        <h3>Procedencia</h3>
        <p class="explica">
          Cada dato de esta ficha sale de un documento guardado. Sin eso, no se
          publica.
        </p>
        <ul class="procedencia">
          <li v-for="(p, i) in entidad.provenance" :key="i">
            <a :href="p.url" target="_blank" rel="noopener noreferrer">{{ p.source_id }}</a>
            <code :title="p.content_hash">{{ p.content_hash.slice(0, 12) }}…</code>
            <span class="extractor">{{ p.extractor_version }}</span>
            <blockquote v-if="p.excerpt">{{ p.excerpt }}</blockquote>
          </li>
        </ul>
      </section>
    </template>
  </aside>
</template>

<style scoped>
.panel {
  overflow-y: auto;
  padding: 1.1rem 1.15rem 3rem;
  border-left: 1px solid var(--borde);
  background: var(--fondo-panel);
}
.vacio { color: var(--texto-tenue); font-size: 0.9rem; margin-top: 1rem; }
header { display: flex; align-items: center; gap: 0.5rem; }
.punto { width: 10px; height: 10px; border-radius: 50%; flex: none; }
.punto.pequeno { width: 7px; height: 7px; }
.tipo { font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--texto-tenue); }
h2 { font-size: 1.1rem; margin: 0.35rem 0 0.2rem; line-height: 1.3; }
.nif { font-size: 0.8rem; color: var(--texto-tenue); font-variant-numeric: tabular-nums; margin: 0 0 0.6rem; }

.aviso-fusion {
  font-size: 0.8rem; background: var(--aviso-suave); border-radius: 6px;
  padding: 0.5rem 0.6rem; margin: 0.5rem 0;
}
.enlace { background: none; border: none; color: var(--acento); cursor: pointer; padding: 0; text-decoration: underline; font: inherit; }

.expandir {
  width: 100%; margin: 0.6rem 0 0.9rem; padding: 0.5rem;
  border: 1px solid var(--borde); border-radius: 6px;
  background: var(--fondo-boton); color: var(--texto); cursor: pointer; font-size: 0.85rem;
}
.expandir:hover { border-color: var(--acento); color: var(--acento); }

h3 { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--texto-tenue); margin: 1.2rem 0 0.5rem; }
.cuenta { color: var(--texto-tenue); font-weight: 400; }

.conexiones, .procedencia { list-style: none; padding: 0; margin: 0; }
.conexiones li { padding: 0.55rem 0; border-bottom: 1px solid var(--borde-suave); }
.otro {
  display: flex; align-items: center; gap: 0.45rem; background: none; border: none;
  color: var(--texto); cursor: pointer; padding: 0; font: inherit; font-size: 0.88rem;
  text-align: left; line-height: 1.3;
}
.otro:hover { color: var(--acento); }
.meta { display: flex; justify-content: space-between; gap: 0.5rem; font-size: 0.76rem; color: var(--texto-tenue); margin-top: 0.2rem; }
.importe { font-variant-numeric: tabular-nums; white-space: nowrap; }

.fiabilidad { display: flex; align-items: center; gap: 0.4rem; margin-top: 0.3rem; font-size: 0.7rem; color: var(--texto-tenue); }
.fiabilidad.inferido .estado { color: var(--aviso); font-weight: 600; }
.barra { flex: 1; height: 3px; background: var(--borde); border-radius: 2px; overflow: hidden; }
.relleno { display: block; height: 100%; background: var(--acento); }
.fiabilidad.inferido .relleno { background: var(--aviso); }
.pct { font-variant-numeric: tabular-nums; }

.explica { font-size: 0.76rem; color: var(--texto-tenue); margin: 0 0 0.5rem; line-height: 1.4; }
.procedencia li { font-size: 0.76rem; padding: 0.4rem 0; border-bottom: 1px solid var(--borde-suave); display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; }
.procedencia code { font-size: 0.7rem; color: var(--texto-tenue); }
.extractor { color: var(--texto-tenue); }
.procedencia blockquote { flex-basis: 100%; margin: 0.3rem 0 0; padding-left: 0.55rem; border-left: 2px solid var(--borde); color: var(--texto-tenue); font-style: italic; }
</style>
