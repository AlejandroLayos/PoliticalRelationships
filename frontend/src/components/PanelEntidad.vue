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


/** La fecha en corto; si no se puede leer, nada. */
function dia(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('es-ES')
}

/**
 * El concepto de la operación: la convocatoria en BDNS, el objeto en PLACSP.
 * Recortado, con el entero en el `title`.
 */
function conceptoEntero(arista) {
  const p = arista?.properties ?? {}
  return p.convocatoria ?? p.objeto ?? ''
}

/**
 * ¿Es el caso normal? Afirmado por la fuente y sin ninguna duda.
 *
 * Se dice igualmente, pero en una línea y sin barra: la barra está para
 * marcar lo que NO es rutina.
 */
function esRutina(arista) {
  return arista.status === 'asserted' && (arista.confidence ?? 1) >= 1
}

function concepto(arista) {
  const t = conceptoEntero(arista).trim()
  return t.length > 64 ? `${t.slice(0, 63)}…` : t
}

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
            <!--
              El nombre, a tres renglones como mucho. Aquí los vecinos no son
              sólo entidades: son también contratos, y el nombre de un
              contrato es su objeto entero. Una fila ocupaba siete renglones
              —«pa 82/2024 (sevilla) servicio de limpieza, logística de
              gestión interna de residuos, suministro y reposición del
              material de higiene consumible y otros servicios
              complementarios…»— y setenta y cinco filas así son un muro. El
              texto entero está en el `title` y en la procedencia.
            -->
            <button class="otro" :title="c.otro.caption" @click="emit('ir', c.otro.id)">
              <span class="punto pequeno" :style="{ background: COLOR_POR_ESQUEMA[c.otro.schema] ?? COLOR_POR_DEFECTO }" />
              <span class="nombre-otro">{{ c.otro.caption }}</span>
            </button>
            <div class="meta">
              <span class="rel">
                {{ c.saliente ? '→' : '←' }} {{ etiquetaArista(c.arista.schema) }}
              </span>
              <span v-if="importe(c.arista)" class="importe">{{ importe(c.arista) }}</span>
            </div>
            <!--
              La fecha y el concepto, que es lo único que distingue una fila de
              otra cuando se repiten.

              En la ficha del PSOE salían DOCE renglones idénticos —«AYUNTAMIENTO
              DE BASAURI · pago/subvención · 1.092,50 € · 100%»— y once más de
              Amurrio y once de Santander. Parecen datos duplicados y no lo son:
              son las transferencias MENSUALES al grupo municipal, cada una con
              su fecha y su convocatoria («…GRUPOS POLÍTICOS MARZO 2025»). Sin
              enseñar eso, el lector sólo puede concluir que la web repite
              filas.
            -->
            <div v-if="c.arista.start_date || concepto(c.arista)" class="cuando-que">
              <span v-if="c.arista.start_date" class="fecha">{{ dia(c.arista.start_date) }}</span>
              <span v-if="concepto(c.arista)" class="concepto" :title="conceptoEntero(c.arista)">
                {{ concepto(c.arista) }}
              </span>
            </div>
            <!--
              La confianza y el estado se muestran SIEMPRE, no sólo cuando son
              malos. Es la invariante 5: nada inferido puede presentarse igual
              que un hecho afirmado por la fuente.

              Pero el caso normal —afirmado por la fuente, 100 %— no necesita
              una barra: era lo más llamativo de cada fila, repetido setenta y
              cinco veces, y justo lo que menos dice. En una línea pequeña y
              sin barra, el contraste con lo inferido es MAYOR que antes, que
              es lo que la invariante pide: la barra ámbar de una conexión
              inferida ahora salta a la vista en medio de una lista sobria.
            -->
            <div
              class="fiabilidad"
              :class="{ inferido: c.arista.status !== 'asserted', rutina: esRutina(c.arista) }"
            >
              <span class="estado">{{ NOMBRE_ESTADO[c.arista.status] ?? c.arista.status }}</span>
              <template v-if="!esRutina(c.arista)">
                <span class="barra" :title="`Confianza ${(c.arista.confidence * 100).toFixed(0)}%`">
                  <span class="relleno" :style="{ width: `${(c.arista.confidence ?? 0) * 100}%` }" />
                </span>
                <span class="pct">{{ ((c.arista.confidence ?? 0) * 100).toFixed(0) }}%</span>
              </template>
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
.nombre-otro {
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
  overflow: hidden; min-width: 0;
}
.fiabilidad.rutina { color: var(--tinta-3); font-size: var(--t-xs); }
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
.cuando-que {
  display: flex; flex-wrap: wrap; gap: 0.35rem; align-items: baseline;
  font-size: 0.7rem; color: var(--texto-tenue); margin-top: 0.1rem;
}
.cuando-que .fecha { font-variant-numeric: tabular-nums; white-space: nowrap; }
.cuando-que .concepto { min-width: 0; }
.procedencia blockquote { flex-basis: 100%; margin: 0.3rem 0 0; padding-left: 0.55rem; border-left: 2px solid var(--borde); color: var(--texto-tenue); font-style: italic; }
</style>
