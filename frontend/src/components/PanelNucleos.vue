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
import { MINIMO_NUCLEO, conEstructura, dineroCorto } from '../nucleos.js'
import { etiquetaEsquemaPlural } from '../esquemas.js'

const props = defineProps({
  nucleos: { type: Array, default: () => [] },
  enfocado: { type: Number, default: null },
  /** El grupo señalado en el mapa, para resaltar su fila. */
  senalado: { type: Number, default: null },
})
const emit = defineEmits(['enfocar', 'seleccionar', 'senalar'])

/*
  El mismo número que el bloque del mapa, y por el mismo orden: el de esta
  lista, que es el del dinero. Antes era un color —ocho, y gris el resto—, y
  casar tonos de memoria era un trabajo que un número ahorra.
*/
function numero(i) {
  return String(i + 1).padStart(2, '0')
}

// El corte vive en `nucleos.js` porque el mapa tiene que aplicar el mismo:
// si aquí se esconde un grupo por pequeño y allí se le da color, la leyenda
// promete una fila que no existe.
const MINIMO = MINIMO_NUCLEO
const conCuerpo = computed(() => conEstructura(props.nucleos).slice(0, 40))
const pequenos = computed(() => props.nucleos.length - conEstructura(props.nucleos).length)

function resumenTipos(tipos) {
  return Object.entries(tipos)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([k, v]) => `${v} ${etiquetaEsquemaPlural(k, v)}`)
    .join(' · ')
}
</script>

<template>
  <aside class="panel">
    <div class="cabecera">
      <!--
        «Núcleo de financiación» era jerga nuestra. Quien entra a saber de
        dónde sale el dinero de una decisión no tiene por qué traducirla, y si
        el título de la columna hay que traducirlo, la columna no se lee.
      -->
      <p class="antetitulo">Los grupos, por dinero</p>
      <h2>Grupos de dinero público</h2>
      <p class="que-es">
        Organismos y empresas que <strong>se pagan entre ellos mucho más que
        con el resto</strong>.
      </p>
      <p class="nota">
        Sale de mirar la forma de la red, no de ninguna investigación: estar
        en el mismo grupo no implica irregularidad ni connivencia.
      </p>
    </div>

    <p v-if="!conCuerpo.length" class="vacio">
      Todavía no se ha encontrado ningún grupo con estructura.
    </p>

    <ul v-else class="lista">
      <li v-for="(n, i) in conCuerpo" :key="n.id">
        <button
          class="nucleo"
          :class="{ activo: enfocado === n.id, senalado: senalado === n.id }"
          @click="emit('enfocar', enfocado === n.id ? null : n.id)"
          @mouseenter="emit('senalar', n.id)"
          @mouseleave="emit('senalar', null)"
        >
          <span class="puesto-num">{{ numero(i) }}</span>
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
      grupo; se pueden buscar por su nombre.
    </p>
  </aside>
</template>

<style scoped>
.panel {
  display: flex; flex-direction: column; height: 100%; overflow-y: auto;
  background: var(--papel); border-left: 1px solid var(--filete-suave);
}
.cabecera {
  padding: var(--e4) var(--e4) var(--e3);
  border-bottom: 2px solid var(--filete);
  position: sticky; top: 0; background: var(--papel); z-index: 1;
}
h2 { margin: 0 0 var(--e2); font-size: var(--t-h3); }
.que-es { margin: 0; font-size: var(--t-s); line-height: 1.45; color: var(--tinta-2); }
.que-es strong { color: var(--tinta); font-weight: 650; }
.cabecera .nota { font-size: var(--t-s); margin-top: var(--e2); }
.vacio { padding: var(--e4); color: var(--tinta-3); font-size: var(--t-s); }

.lista, .miembros { list-style: none; margin: 0; padding: 0; }
.nucleo {
  display: grid; grid-template-columns: 1.7rem 1fr; gap: var(--e2);
  width: 100%; padding: var(--e3) var(--e4);
  background: none; border: 0; border-bottom: 1px solid var(--filete-suave);
  color: inherit; font: inherit; text-align: left; cursor: pointer; align-items: baseline;
}
.nucleo:hover, .nucleo.activo, .nucleo.senalado { background: var(--papel-2); }
.nucleo.activo { box-shadow: inset 3px 0 0 var(--tinta); }
.cuerpo { display: flex; flex-direction: column; gap: 0.15rem; min-width: 0; }
.titulo { font-size: var(--t-m); font-weight: 600; color: var(--tinta); line-height: 1.3; overflow-wrap: anywhere; }
.cifras { font-size: var(--t-s); color: var(--tinta-3); }
.cifras strong { color: var(--tinta); font-weight: 650; }
.sep { margin: 0 0.3rem; }
.tipos { font-size: var(--t-xs); color: var(--tinta-3); }

.miembros { background: var(--hoja); border-bottom: 1px solid var(--filete-suave); }
.miembro {
  display: flex; justify-content: space-between; gap: var(--e3);
  width: 100%; padding: 0.45rem var(--e4) 0.45rem calc(var(--e4) + 1.7rem + var(--e2));
  background: none; border: 0; color: var(--tinta); font: inherit; font-size: var(--t-s);
  text-align: left; cursor: pointer;
}
.miembro:hover { background: var(--papel-2); }
.miembro:hover .nombre { text-decoration: underline; text-decoration-color: var(--filete-medio); text-underline-offset: 0.18em; }
.nombre { overflow-wrap: anywhere; }
.dinero { color: var(--tinta-2); white-space: nowrap; font-variant-numeric: tabular-nums; }
.nota-pequenos {
  padding: var(--e3) var(--e4); margin: 0;
  font-size: var(--t-xs); line-height: 1.5; color: var(--tinta-3);
}
</style>
