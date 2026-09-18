<script setup>
/**
 * La ficha de influencia: los hechos, en texto y en cifras.
 *
 * El diagrama enseña la forma —de dónde entra, a dónde sale— pero no se puede
 * leer una cifra exacta de una banda de colores. Aquí van los números, las
 * contrapartes completas (el dibujo recorta, la lista no) y el rastro hasta el
 * documento del que sale cada cosa.
 */
import { computed } from 'vue'
import { dineroCorto } from '../nucleos.js'
import { resumenEnPalabras } from '../influencia.js'
import { COLOR_POR_DEFECTO, COLOR_POR_ESQUEMA, etiquetaEsquema } from '../esquemas.js'

const props = defineProps({
  area: { type: Object, default: null },
  /** El grafo sin colapsar, para poder nombrar los expedientes puenteados. */
  crudo: { type: Object, default: null },
})
const emit = defineEmits(['seleccionar', 'volver', 'expandir'])

const resumen = computed(() => resumenEnPalabras(props.area))

const nombresExpediente = computed(() => {
  const m = new Map()
  for (const n of props.crudo?.nodes ?? []) {
    if (n.schema === 'Contract') m.set(n.id, n.caption)
  }
  return m
})

function tope(lista) {
  return Math.max(1, ...lista.map((x) => x.total))
}

function pct(v, max) {
  return `${Math.max(2, (v / max) * 100)}%`
}

function color(schema) {
  return COLOR_POR_ESQUEMA[schema] ?? COLOR_POR_DEFECTO
}

const sinDatos = computed(
  () => props.area && !props.area.recibeDe.length && !props.area.pagaA.length && !props.area.sanciones.length,
)
</script>

<template>
  <aside class="panel">
    <p v-if="!area?.entidad" class="vacio">Pulsa una entidad del mapa.</p>

    <template v-else>
      <button class="volver" @click="emit('volver')">← Volver al mapa</button>

      <header>
        <span class="punto" :style="{ background: color(area.entidad.schema) }" />
        <span class="tipo">{{ etiquetaEsquema(area.entidad.schema) }}</span>
      </header>
      <h2>{{ area.entidad.caption }}</h2>
      <p v-if="area.entidad.nif" class="nif">NIF {{ area.entidad.nif }}</p>
      <p class="resumen">{{ resumen }}</p>

      <!-- Cifras grandes: lo primero que se mira. ----------------------- -->
      <!--
        Un «0 €» grande afirma que no entró dinero. Lo que sabemos es más
        flojo: que no consta en lo ingerido. La cifra sólo se pone cuando hay
        algo que contar.
      -->
      <div class="cifras">
        <div class="cifra entra" :class="{ nada: !area.recibeDe.length }">
          <span class="valor">{{ area.recibeDe.length ? dineroCorto(area.totalRecibido) : 'No consta' }}</span>
          <span class="que">
            {{ area.recibeDe.length
              ? `recibe de ${area.recibeDe.length} ${area.recibeDe.length === 1 ? 'pagador' : 'pagadores'}`
              : 'que reciba dinero' }}
          </span>
        </div>
        <div class="cifra sale" :class="{ nada: !area.pagaA.length }">
          <span class="valor">{{ area.pagaA.length ? dineroCorto(area.totalPagado) : 'No consta' }}</span>
          <span class="que">
            {{ area.pagaA.length
              ? `reparte entre ${area.pagaA.length} ${area.pagaA.length === 1 ? 'receptor' : 'receptores'}`
              : 'que pague a nadie' }}
          </span>
        </div>
      </div>

      <!--
        Exposición a capital extranjero. Se dice de qué son los datos: el NIF
        de no residente prueba dónde tributa quien cobra o paga, y nada más.
        Presentarlo como «influencia extranjera» a secas sería afirmar algo
        que las fuentes no dicen.
      -->
      <section v-if="area.extranjero.contrapartes.length" class="bloque extranjero">
        <h3>Capital extranjero alrededor</h3>
        <p class="grande">
          {{ dineroCorto(area.extranjero.total) }}
          <span class="pct">{{ area.extranjero.porcentaje.toFixed(1) }} % de lo que mueve</span>
        </p>
        <ul class="lista compacta">
          <li v-for="c in area.extranjero.contrapartes" :key="c.id">
            <button @click="emit('seleccionar', c.id)">{{ c.caption }}</button>
            <span class="importe">{{ dineroCorto(c.total) }}</span>
          </li>
        </ul>
        <p class="matiz">
          Son entidades con NIF de no residente (letras N y W) o NIE. Dice dónde
          tributan, no quién las controla.
        </p>
      </section>

      <!-- De quién recibe ---------------------------------------------- -->
      <section v-if="area.recibeDe.length" class="bloque">
        <h3>De quién recibe <span class="cuenta">{{ area.recibeDe.length }}</span></h3>
        <ul class="lista barras">
          <li v-for="c in area.recibeDe" :key="c.id">
            <button class="fila" @click="emit('seleccionar', c.id)">
              <span class="punto pequeno" :style="{ background: color(c.schema) }" />
              <span class="nombre">{{ c.caption }}</span>
              <span class="importe">{{ dineroCorto(c.total) }}</span>
            </button>
            <span class="barra"><i class="entra" :style="{ width: pct(c.total, tope(area.recibeDe)) }" /></span>
            <span class="meta">
              {{ c.n }} {{ c.n === 1 ? 'operación' : 'operaciones' }}
              <template v-if="c.expedientes?.length">
                · {{ c.expedientes.length }}
                {{ c.expedientes.length === 1 ? 'expediente' : 'expedientes' }}
              </template>
              <span v-if="c.inferido" class="inferido">· inferido ({{ (c.confianza * 100).toFixed(0) }} %)</span>
              <span v-if="c.extranjera" class="extranjera">· extranjera</span>
            </span>
          </li>
        </ul>
      </section>

      <!-- A quién paga -------------------------------------------------- -->
      <section v-if="area.pagaA.length" class="bloque">
        <h3>A quién paga <span class="cuenta">{{ area.pagaA.length }}</span></h3>
        <ul class="lista barras">
          <li v-for="c in area.pagaA" :key="c.id">
            <button class="fila" @click="emit('seleccionar', c.id)">
              <span class="punto pequeno" :style="{ background: color(c.schema) }" />
              <span class="nombre">{{ c.caption }}</span>
              <span class="importe">{{ dineroCorto(c.total) }}</span>
            </button>
            <span class="barra"><i class="sale" :style="{ width: pct(c.total, tope(area.pagaA)) }" /></span>
            <span class="meta">
              {{ c.n }} {{ c.n === 1 ? 'operación' : 'operaciones' }}
              <template v-if="c.expedientes?.length">
                ·
                <span :title="c.expedientes.map((e) => nombresExpediente.get(e) ?? e).join(' · ')">
                  {{ c.expedientes.length }}
                  {{ c.expedientes.length === 1 ? 'expediente' : 'expedientes' }}
                </span>
              </template>
              <span v-if="c.inferido" class="inferido">· inferido ({{ (c.confianza * 100).toFixed(0) }} %)</span>
              <span v-if="c.extranjera" class="extranjera">· extranjera</span>
            </span>
          </li>
        </ul>
      </section>

      <!--
        Las sanciones van aparte de los pagos a propósito: una multa del
        Tribunal de Cuentas es una deuda, no una compra. Mezclarlas diría que
        el sancionado «financia» a la Administración.
      -->
      <section v-if="area.sanciones.length" class="bloque sanciones">
        <h3>Expedientes sancionadores <span class="cuenta">{{ area.sanciones.length }}</span></h3>
        <ul class="lista compacta">
          <li v-for="s in area.sanciones" :key="s.id">
            <span class="nombre">{{ s.acreedor }}</span>
            <span class="importe">
              {{ s.sinImporte ? 'sin cuantía única' : dineroCorto(s.importe) }}
            </span>
            <span v-if="s.fecha" class="meta">{{ s.fecha }}</span>
          </li>
        </ul>
      </section>

      <!-- Ámbito de interés --------------------------------------------- -->
      <section v-if="area.comparten.length" class="bloque">
        <h3>Orbitan a sus mismos pagadores</h3>
        <p class="matiz">
          Cobran de los mismos organismos que esta entidad. Es una coincidencia
          de pagador, no una relación entre ellas.
        </p>
        <ul class="lista compacta">
          <li v-for="c in area.comparten" :key="c.id">
            <button @click="emit('seleccionar', c.id)">
              <span class="punto pequeno" :style="{ background: color(c.schema) }" />
              {{ c.caption }}
            </button>
            <span class="importe">{{ dineroCorto(c.total) }}</span>
          </li>
        </ul>
      </section>

      <p v-if="sinDatos" class="matiz hueco">
        De esta entidad no consta ningún movimiento de dinero en la instantánea
        publicada. No significa que no lo haya: significa que las fuentes
        ingeridas no lo recogen.
      </p>
    </template>
  </aside>
</template>

<style scoped>
.panel {
  overflow-y: auto; padding: 0.9rem 1.15rem 3rem;
  border-left: 1px solid var(--borde); background: var(--fondo-panel);
}
.vacio { color: var(--texto-tenue); font-size: 0.9rem; margin-top: 1rem; }

.volver {
  background: var(--fondo-boton); color: var(--texto); border: 1px solid var(--borde);
  border-radius: 6px; padding: 0.35rem 0.7rem; font: inherit; font-size: 0.78rem;
  cursor: pointer; margin-bottom: 0.8rem;
}
.volver:hover { border-color: var(--acento); }

header { display: flex; align-items: center; gap: 0.5rem; }
.punto { width: 10px; height: 10px; border-radius: 50%; flex: none; }
.punto.pequeno { width: 7px; height: 7px; display: inline-block; }
.tipo { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--texto-tenue); }
h2 { font-size: 1.12rem; margin: 0.3rem 0 0.15rem; line-height: 1.3; }
.nif { font-size: 0.78rem; color: var(--texto-tenue); font-variant-numeric: tabular-nums; margin: 0; }
.resumen { font-size: 0.83rem; color: var(--texto-tenue); line-height: 1.45; margin: 0.5rem 0 0.9rem; }

.cifras { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }
.cifra {
  background: var(--fondo-boton); border: 1px solid var(--borde);
  border-radius: 8px; padding: 0.55rem 0.6rem; display: flex; flex-direction: column; gap: 0.1rem;
}
.cifra .valor { font-size: 1.02rem; font-weight: 700; font-variant-numeric: tabular-nums; }
.cifra .que { font-size: 0.7rem; color: var(--texto-tenue); }
.cifra.entra { border-left: 3px solid #4bb47f; }
.cifra.entra .valor { color: #7fd0a5; }
.cifra.sale { border-left: 3px solid #e8703a; }
.cifra.sale .valor { color: #f0956b; }
.cifra.nada { border-left-color: var(--borde); opacity: 0.6; }
.cifra.nada .valor { color: var(--texto-tenue); font-size: 0.85rem; font-weight: 600; }

.bloque { margin-top: 1.3rem; }
h3 {
  font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--texto-tenue); margin: 0 0 0.5rem;
}
.cuenta { font-weight: 400; opacity: 0.7; }

.bloque.extranjero {
  background: #241d33; border: 1px solid #3c3155; border-radius: 8px; padding: 0.7rem 0.75rem;
}
.bloque.extranjero .grande { font-size: 1.05rem; font-weight: 700; color: #cbb0f0; margin: 0 0 0.5rem; }
.bloque.extranjero .pct { font-size: 0.72rem; font-weight: 400; color: var(--texto-tenue); margin-left: 0.4rem; }

.lista { list-style: none; margin: 0; padding: 0; }
.lista button {
  background: none; border: none; color: var(--texto); font: inherit; cursor: pointer;
  padding: 0; text-align: left;
}
.lista button:hover { color: var(--acento); }

.barras li { padding: 0.5rem 0; border-bottom: 1px solid var(--borde-suave); }
.fila { display: flex; align-items: baseline; gap: 0.4rem; width: 100%; font-size: 0.85rem; }
.fila .nombre { flex: 1; line-height: 1.3; }
.importe { font-variant-numeric: tabular-nums; font-size: 0.8rem; white-space: nowrap; color: var(--texto-tenue); }
.barra { display: block; height: 3px; background: var(--borde-suave); border-radius: 2px; margin: 0.3rem 0 0.25rem; overflow: hidden; }
.barra i { display: block; height: 100%; }
.barra i.entra { background: #4bb47f; }
.barra i.sale { background: #e8703a; }
.meta { font-size: 0.7rem; color: var(--texto-tenue); }
.meta .inferido { color: var(--aviso); }
.meta .extranjera { color: #b08cd9; }

.compacta li {
  display: flex; align-items: baseline; gap: 0.5rem; justify-content: space-between;
  padding: 0.32rem 0; border-bottom: 1px solid var(--borde-suave); font-size: 0.83rem;
}
.compacta .nombre { flex: 1; }

.sanciones h3 { color: #e8877f; }
.sanciones .importe { color: #e8877f; }

.matiz { font-size: 0.72rem; color: var(--texto-tenue); line-height: 1.45; margin: 0.4rem 0 0; }
.hueco { margin-top: 1.2rem; }
</style>
