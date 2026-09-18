<script setup>
/**
 * Lista de núcleos, ordenada por dinero.
 *
 * Es la puerta de entrada al mapa. Un grafo grande sin índice no se explora: se
 * mira un rato y se cierra. Aquí se ve de golpe dónde hay más dinero y quién
 * está dentro de cada grupo, y desde ahí se salta al mapa.
 *
 * El aviso de qué NO significa un núcleo va arriba y no en letra pequeña. Un
 * mapa de dinero público invita justo al malentendido de leer proximidad como
 * connivencia, y ese malentendido es el riesgo principal del proyecto
 * (spec §12).
 */
import { computed } from 'vue'
import { colorNucleo, dineroCorto } from '../nucleos.js'
import { etiquetaEsquema } from '../esquemas.js'

const props = defineProps({
  nucleos: { type: Array, default: () => [] },
  enfocado: { type: Number, default: null },
})
const emit = defineEmits(['enfocar', 'seleccionar'])

// Un puñado de entidades alrededor de una empresa y sus contratos no es un
// núcleo: es una relación con adornos, y ordenando por dinero se cuelan
// arriba y tapan lo que sí tiene estructura. Se pide cuerpo de verdad.
const MINIMO = 6
defineExpose({ MINIMO })
const conEstructura = computed(() => props.nucleos.filter((n) => n.tamano >= MINIMO).slice(0, 40))
const pequenos = computed(() => props.nucleos.filter((n) => n.tamano < MINIMO).length)

function resumenTipos(tipos) {
  return Object.entries(tipos)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([k, v]) => `${v} ${etiquetaEsquema(k).toLowerCase()}`)
    .join(' · ')
}
</script>

<template>
  <aside class="panel">
    <div class="cabecera">
      <h2>Núcleos de financiación</h2>
      <p class="que-es">
        Grupos de organismos, empresas y partidos <strong>más conectados entre sí
        que con el resto</strong> del mapa. Es una observación sobre la forma de
        la red, no una acusación: no implica irregularidad ni connivencia.
      </p>
    </div>

    <p v-if="!conEstructura.length" class="vacio">
      Todavía no se ha encontrado ningún núcleo con estructura.
    </p>

    <ul v-else class="lista">
      <li v-for="n in conEstructura" :key="n.id">
        <button
          class="nucleo"
          :class="{ activo: enfocado === n.id }"
          @click="emit('enfocar', enfocado === n.id ? null : n.id)"
        >
          <span class="marca" :style="{ background: colorNucleo(n.id) }" />
          <span class="cuerpo">
            <span class="titulo">{{ n.etiqueta }}</span>
            <span class="cifras">
              <strong>{{ dineroCorto(n.dinero) }}</strong>
              <span class="sep">·</span>
              {{ n.tamano }} entidades
            </span>
            <span class="tipos">{{ resumenTipos(n.tipos) }}</span>
          </span>
        </button>

        <ul v-if="enfocado === n.id" class="miembros">
          <li v-for="m in n.principales" :key="m.id">
            <button class="miembro" @click="emit('seleccionar', m.id)">
              <span class="nombre">{{ m.caption }}</span>
              <span class="dinero">{{ dineroCorto(m.dinero) }}</span>
            </button>
          </li>
        </ul>
      </li>
    </ul>

    <p v-if="pequenos" class="nota-pequenos">
      Hay además {{ pequenos }} grupos de menos de {{ MINIMO }} entidades. No se
      listan porque casi siempre son una empresa con sus contratos, no un
      núcleo; se ven en el mapa activando «relaciones sueltas».
    </p>
  </aside>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  background: var(--fondo-panel);
  border-left: 1px solid var(--borde);
}
.cabecera {
  padding: 1rem 1rem 0.75rem;
  border-bottom: 1px solid var(--borde);
  position: sticky;
  top: 0;
  background: var(--fondo-panel);
  z-index: 1;
}
h2 {
  margin: 0 0 0.35rem;
  font-size: 0.95rem;
  letter-spacing: 0.02em;
}
.que-es {
  margin: 0;
  font-size: 0.72rem;
  line-height: 1.45;
  color: var(--texto-tenue);
}
.vacio {
  padding: 1rem;
  color: var(--texto-tenue);
  font-size: 0.8rem;
}
.lista,
.miembros {
  list-style: none;
  margin: 0;
  padding: 0;
}
.nucleo {
  display: flex;
  gap: 0.6rem;
  width: 100%;
  padding: 0.65rem 1rem;
  background: none;
  border: 0;
  border-bottom: 1px solid var(--borde);
  color: inherit;
  text-align: left;
  cursor: pointer;
  align-items: flex-start;
}
.nucleo:hover {
  background: var(--fondo-hover);
}
.nucleo.activo {
  background: var(--fondo-hover);
}
.marca {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 0.3rem;
  flex: none;
}
.cuerpo {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}
.titulo {
  font-size: 0.83rem;
  font-weight: 600;
  overflow-wrap: anywhere;
}
.cifras {
  font-size: 0.76rem;
  color: var(--texto-tenue);
}
.cifras strong {
  color: var(--texto);
}
.sep {
  margin: 0 0.3rem;
}
.tipos {
  font-size: 0.7rem;
  color: var(--texto-tenue);
}
.miembros {
  background: rgba(0, 0, 0, 0.18);
  border-bottom: 1px solid var(--borde);
}
.miembro {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  width: 100%;
  padding: 0.4rem 1rem 0.4rem 2.1rem;
  background: none;
  border: 0;
  color: inherit;
  font-size: 0.76rem;
  text-align: left;
  cursor: pointer;
}
.miembro:hover {
  background: var(--fondo-hover);
}
.nombre {
  overflow-wrap: anywhere;
}
.dinero {
  color: var(--texto-tenue);
  white-space: nowrap;
}
.nota-pequenos {
  padding: 0.85rem 1rem;
  margin: 0;
  font-size: 0.72rem;
  line-height: 1.45;
  color: var(--texto-tenue);
  border-top: 1px solid var(--borde);
}
</style>
