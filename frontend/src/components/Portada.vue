<script setup>
/**
 * La portada: por dónde se empieza.
 *
 * Listas ordenadas, no un grafo. Quien entra por primera vez no sabe qué
 * buscar, y una maraña de dos mil nodos no le da ningún asidero: lo primero
 * que tiene que ver es dónde está el dinero y a un clic de qué.
 *
 * Cada lista lleva escrito lo que significa Y lo que no. Una tabla ordenada
 * por euros se lee sola como una lista de sospechosos, y aquí encabezarla sólo
 * quiere decir que se compra mucho.
 */
import { computed } from 'vue'
import { construirDirectorio, construirDirectorioDesdeIndice } from '../directorio.js'
import { contratosDeMedios } from '../medios.js'
import { dineroCorto } from '../nucleos.js'
import { COLOR_POR_DEFECTO, COLOR_POR_ESQUEMA, etiquetaEsquema } from '../esquemas.js'

const props = defineProps({
  /** El grafo YA colapsado. */
  datos: { type: Object, default: null },
  /** El grafo sin colapsar: el CPV vive en el expediente, no en la arista. */
  crudo: { type: Object, default: null },
  /** Índice de TODA la base. Si está, manda él para los rankings de dinero. */
  indice: { type: Object, default: null },
})
const emit = defineEmits(['seleccionar', 'verMapa'])

/**
 * Los rankings de dinero salen del índice cuando lo hay, porque el índice
 * cubre toda la base y el grafo sólo lo que cabe en el mapa. Con rankings
 * calculados sobre el grafo, «quién reparte más dinero público» contestaba en
 * realidad «de los que caben en el mapa, quién reparte más».
 *
 * Las sanciones y el ámbito de interés siguen saliendo del grafo: son
 * relaciones, y el índice no lleva aristas.
 */
const delGrafo = computed(() => construirDirectorio(props.datos))
const delIndice = computed(() => construirDirectorioDesdeIndice(props.indice))

const dir = computed(() => {
  const g = delGrafo.value
  const i = delIndice.value
  if (!i) return g
  return {
    ...i,
    sancionados: g.sancionados,
    totales: {
      ...i.totales,
      nOperaciones: g.totales.nOperaciones,
      nSancionados: g.totales.nSancionados,
      totalSancionado: g.totales.totalSancionado,
      nSinCifra: g.totales.nSinCifra,
    },
  }
})

/** Cuántas entidades hay en la base que no caben en el mapa publicado. */
const fueraDelMapa = computed(() => {
  const t = delIndice.value?.totales
  return t ? Math.max(0, t.nActores - (t.enMapa ?? 0)) : 0
})
const medios = computed(() => contratosDeMedios(props.crudo))

function dinero(v) {
  return dineroCorto(v)
}

const LISTAS = [
  {
    clave: 'pagadores',
    titulo: 'Quién reparte más dinero público',
    que: 'Organismos y entidades por el total que sale de ellos hacia empresas y beneficiarios.',
    noEs: 'Encabezar esta lista no indica nada irregular: un servicio de salud compra para una comunidad entera.',
    unidad: (x) => `${x.n} ${x.n === 1 ? 'receptor' : 'receptores'}`,
  },
  {
    clave: 'receptores',
    titulo: 'Quién más cobra',
    que: 'Empresas y entidades por el total que reciben de administraciones públicas.',
    noEs: 'Facturar mucho es lo normal en sectores concentrados, como el farmacéutico o la obra civil.',
    unidad: (x) => `${x.n} ${x.n === 1 ? 'pagador' : 'pagadores'}`,
  },
  {
    clave: 'transversales',
    titulo: 'Cobran de más administraciones distintas',
    que: 'Ordenado por número de pagadores diferentes, no por dinero: quien aparece en muchas administraciones ha hecho un recorrido que el importe no enseña.',
    noEs: 'Puede ser simplemente un proveedor de un servicio que todas necesitan.',
    unidad: (x) => `${x.n} administraciones`,
    destacar: 'n',
  },
  {
    clave: 'extranjeras',
    titulo: 'Capital extranjero',
    que: 'Entidades con NIF de no residente (letras N y W) o NIE que cobran de administraciones españolas.',
    noEs: 'El NIF dice dónde tributan, no quién las controla. Una filial española de una matriz extranjera no aparece aquí.',
    unidad: (x) => `${x.n} ${x.n === 1 ? 'contraparte' : 'contrapartes'}`,
  },
  {
    clave: 'sancionados',
    titulo: 'Expedientes del Tribunal de Cuentas',
    que: 'Formaciones políticas con expedientes sancionadores del Tribunal de Cuentas y su cuantía.',
    noEs: 'Es una deuda con el Estado, no un pago a nadie: no es financiación en ningún sentido.',
    unidad: (x) => `${x.expedientes ?? x.n} ${(x.expedientes ?? x.n) === 1 ? 'expediente' : 'expedientes'}`,
    tono: 'sancion',
  },
]

const listas = computed(() =>
  LISTAS.map((l) => ({ ...l, filas: dir.value[l.clave] ?? [] })).filter((l) => l.filas.length),
)

function tope(filas, campo = 'total') {
  return Math.max(1, ...filas.map((f) => f[campo] ?? 0))
}

function color(schema) {
  return COLOR_POR_ESQUEMA[schema] ?? COLOR_POR_DEFECTO
}
</script>

<template>
  <div class="portada">
    <section class="intro">
      <h2>Dónde está el dinero</h2>
      <p>
        Todo lo que sigue sale de los documentos públicos que la ingesta guarda
        con su procedencia. Pulsa cualquier nombre para ver su área de
        influencia: de quién recibe, a quién paga y con quién comparte
        pagadores.
      </p>
      <div class="totales">
        <div><b>{{ dineroCorto(dir.totales.dineroTotal) }}</b><span>en operaciones publicadas</span></div>
        <div><b>{{ dir.totales.nOperaciones.toLocaleString('es-ES') }}</b><span>operaciones</span></div>
        <div>
          <b>{{ dir.totales.nActores.toLocaleString('es-ES') }}</b>
          <span>entidades{{ fueraDelMapa ? ', el mapa enseña parte' : '' }}</span>
        </div>
        <div><b>{{ dir.totales.nPartidos.toLocaleString('es-ES') }}</b><span>formaciones políticas</span></div>
        <div><b>{{ dir.totales.nExtranjeras }}</b><span>entidades no residentes</span></div>
      </div>
      <button class="ir-mapa" @click="emit('verMapa')">Ver el mapa de núcleos →</button>
    </section>

    <div class="rejilla">
      <section v-for="l in listas" :key="l.clave" class="tarjeta" :class="l.tono">
        <h3>{{ l.titulo }}</h3>
        <p class="que">{{ l.que }}</p>
        <ol class="ranking">
          <li v-for="(f, i) in l.filas" :key="f.id">
            <span class="puesto">{{ i + 1 }}</span>
            <div class="cuerpo">
              <button class="nombre" @click="emit('seleccionar', f.id)">
                <span class="punto" :style="{ background: color(f.schema) }" />
                {{ f.caption }}
              </button>
              <span class="barra">
                <i :style="{ width: `${Math.max(2, ((l.destacar === 'n' ? f.n : f.total) / tope(l.filas, l.destacar === 'n' ? 'n' : 'total')) * 100)}%` }" />
              </span>
              <span class="meta">
                {{ etiquetaEsquema(f.schema) }} · {{ l.unidad(f) }}
                <span v-if="f.extranjera && l.clave !== 'extranjeras'" class="marca">· no residente</span>
                <!--
                  Está en la base pero no en el grafo publicado: se puede
                  abrir su ficha y ver sus cifras, no su red. Decirlo aquí
                  evita que el clic parezca roto.
                -->
                <span v-if="f.enMapa === false" class="sin-red">· sin red en el mapa</span>
              </span>
            </div>
            <span class="cifra">{{ dineroCorto(f.total) }}</span>
          </li>
        </ol>
        <p class="no-es">{{ l.noEs }}</p>
      </section>
    </div>

    <!--
      Publicidad institucional. Se enseña el objeto del contrato, no una
      etiqueta sobre la empresa: el dato dice para qué era el contrato, y de
      ahí no se sigue que el adjudicatario sea un medio de comunicación.
    -->
    <section v-if="medios.contratos.length" class="tarjeta medios">
      <h3>Publicidad institucional y medios</h3>
      <p class="que">
        Contratos cuyo objeto es publicidad, edición, radio, televisión o
        relaciones públicas, según el código CPV que el propio órgano de
        contratación asignó al expediente.
        <b>{{ dinero(medios.total) }}</b> en {{ medios.contratos.length }}
        {{ medios.contratos.length === 1 ? 'adjudicación' : 'adjudicaciones' }}.
      </p>

      <div class="dos-columnas">
        <div>
          <h4>Quién cobra</h4>
          <ul class="lista">
            <li v-for="e in medios.porEmpresa" :key="e.id">
              <button @click="emit('seleccionar', e.id)">{{ e.caption }}</button>
              <span class="cifra">{{ dinero(e.total) }}</span>
            </li>
          </ul>
        </div>
        <div>
          <h4>Quién paga</h4>
          <ul class="lista">
            <li v-for="o in medios.porOrganismo" :key="o.id">
              <button @click="emit('seleccionar', o.id)">{{ o.caption }}</button>
              <span class="cifra">{{ dinero(o.total) }}</span>
            </li>
          </ul>
        </div>
      </div>

      <details class="expedientes">
        <summary>Ver los {{ medios.contratos.length }} contratos uno a uno</summary>
        <ul class="lista detalle">
          <li v-for="c in medios.contratos" :key="c.id">
            <p class="titulo-contrato">{{ c.titulo }}</p>
            <p class="linea">
              <button @click="emit('seleccionar', c.organoId)">{{ c.organo }}</button>
              <span class="flecha">→</span>
              <button @click="emit('seleccionar', c.empresaId)">{{ c.empresa }}</button>
              <span class="cifra">{{ c.sinImporte ? 'importe no publicado' : dinero(c.importe) }}</span>
            </p>
            <p class="linea meta">
              {{ c.etiqueta }} (CPV {{ c.cpv }})
              <a v-if="c.url" :href="c.url" target="_blank" rel="noopener noreferrer">ver el expediente</a>
            </p>
          </li>
        </ul>
      </details>

      <p class="no-es">
        Aparecer aquí no convierte a una empresa en un medio de comunicación:
        puede ser la agencia que compra los espacios, la productora o la
        imprenta. El dato dice de qué iba el contrato, no qué es quien lo cobra.
      </p>
    </section>

    <p class="pie">
      <template v-if="fueraDelMapa">
        Los rankings cubren las
        {{ dir.totales.nActores.toLocaleString('es-ES') }} entidades ingeridas;
        el mapa dibuja las {{ (dir.totales.enMapa ?? 0).toLocaleString('es-ES') }}
        con más dinero, así que
        {{ fueraDelMapa.toLocaleString('es-ES') }} se pueden buscar y consultar
        pero no se ven en el grafo.
      </template>
      <template v-else>
        Las listas se calculan sobre la instantánea publicada, que es una parte
        del total.
      </template>
      Lo que falta por ingerir no aparece, y la ausencia de una entidad aquí no
      dice nada sobre ella.
      <template v-if="dir.totales.nSinCifra">
        Otras <b>{{ dir.totales.nSinCifra.toLocaleString('es-ES') }}</b>
        operaciones constan pero sin cifra utilizable, así que no suman en
        ningún total: casi siempre porque el importe publicado es el del
        acuerdo marco entero y figura repetido en cada adjudicatario, que no es
        lo que cobra cada uno.
      </template>
    </p>
  </div>
</template>

<style scoped>
.portada { overflow-y: auto; padding: 1.2rem 1.4rem 3rem; height: 100%; }

.intro { max-width: 58rem; }
.intro h2 { font-size: 1.35rem; margin: 0 0 0.4rem; letter-spacing: -0.015em; }
.intro p { font-size: 0.88rem; color: var(--texto-tenue); line-height: 1.55; margin: 0 0 0.9rem; max-width: 44rem; }

.totales { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.totales div {
  background: var(--fondo-panel); border: 1px solid var(--borde); border-radius: 8px;
  padding: 0.5rem 0.8rem; display: flex; flex-direction: column; min-width: 8.5rem;
}
.totales b { font-size: 1.05rem; font-variant-numeric: tabular-nums; }
.totales span { font-size: 0.7rem; color: var(--texto-tenue); margin-top: 0.1rem; }

.ir-mapa {
  margin-top: 0.9rem; background: var(--fondo-boton); color: var(--texto);
  border: 1px solid var(--borde); border-radius: 7px; padding: 0.45rem 0.85rem;
  font: inherit; font-size: 0.82rem; cursor: pointer;
}
.ir-mapa:hover { border-color: var(--acento); color: var(--acento); }

.rejilla {
  display: grid; gap: 1rem; margin-top: 1.5rem;
  grid-template-columns: repeat(auto-fit, minmax(23rem, 1fr));
}

.tarjeta {
  background: var(--fondo-panel); border: 1px solid var(--borde);
  border-radius: 10px; padding: 0.9rem 1rem 0.8rem;
}
.tarjeta h3 { font-size: 0.95rem; margin: 0 0 0.3rem; letter-spacing: -0.01em; }
.que { font-size: 0.75rem; color: var(--texto-tenue); line-height: 1.45; margin: 0 0 0.7rem; }

.ranking { list-style: none; margin: 0; padding: 0; counter-reset: n; }
.ranking li {
  display: grid; grid-template-columns: 1.4rem 1fr auto; gap: 0.5rem; align-items: baseline;
  padding: 0.4rem 0; border-bottom: 1px solid var(--borde-suave);
}
.puesto { font-size: 0.72rem; color: var(--texto-tenue); font-variant-numeric: tabular-nums; text-align: right; }
.cuerpo { min-width: 0; }
.nombre {
  background: none; border: none; color: var(--texto); font: inherit; font-size: 0.84rem;
  padding: 0; cursor: pointer; text-align: left; line-height: 1.3; display: flex;
  align-items: baseline; gap: 0.35rem;
}
.nombre:hover { color: var(--acento); }
.punto { width: 7px; height: 7px; border-radius: 50%; flex: none; }
.barra { display: block; height: 3px; background: var(--borde-suave); border-radius: 2px; margin: 0.28rem 0 0.22rem; overflow: hidden; }
.barra i { display: block; height: 100%; background: var(--acento); }
.tarjeta.sancion .barra i { background: #d9635c; }
.meta { font-size: 0.68rem; color: var(--texto-tenue); }
.meta .marca { color: #b08cd9; }
.meta .sin-red { color: var(--aviso); }
.cifra { font-size: 0.8rem; font-variant-numeric: tabular-nums; white-space: nowrap; color: var(--texto-tenue); }
.tarjeta.sancion .cifra { color: #e8877f; }

.no-es {
  font-size: 0.7rem; color: var(--texto-tenue); line-height: 1.45;
  margin: 0.7rem 0 0; padding-top: 0.55rem; border-top: 1px solid var(--borde-suave);
  font-style: italic;
}

.medios { margin-top: 1rem; }
.dos-columnas { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem 1.5rem; }
.medios h4 {
  font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--texto-tenue); margin: 0 0 0.35rem;
}
.lista { list-style: none; margin: 0; padding: 0; }
.lista > li {
  display: flex; justify-content: space-between; gap: 0.6rem; align-items: baseline;
  padding: 0.3rem 0; border-bottom: 1px solid var(--borde-suave); font-size: 0.82rem;
}
.lista button {
  background: none; border: none; color: var(--texto); font: inherit; padding: 0;
  cursor: pointer; text-align: left;
}
.lista button:hover { color: var(--acento); }

.expedientes { margin-top: 0.9rem; }
.expedientes summary {
  cursor: pointer; font-size: 0.78rem; color: var(--acento); padding: 0.3rem 0;
}
.detalle > li { display: block; padding: 0.55rem 0; }
.titulo-contrato { margin: 0 0 0.2rem; font-size: 0.8rem; line-height: 1.35; }
.linea { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.4rem; margin: 0; font-size: 0.8rem; }
.linea.meta { font-size: 0.7rem; color: var(--texto-tenue); margin-top: 0.15rem; }
.flecha { color: var(--texto-tenue); }

@media (max-width: 640px) {
  .dos-columnas { grid-template-columns: 1fr; }
}

.pie {
  margin: 1.6rem 0 0; font-size: 0.73rem; color: var(--texto-tenue);
  line-height: 1.5; max-width: 44rem;
}
</style>
