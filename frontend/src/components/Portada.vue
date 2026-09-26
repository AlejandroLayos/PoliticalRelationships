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
import { computed, ref } from 'vue'
import {
  construirDirectorio,
  construirDirectorioDeTerritorio,
  construirDirectorioDesdeIndice,
} from '../directorio.js'
import { contratosDeMedios } from '../medios.js'
import { delOrganoEnPalabras } from '../cargos.js'
import { cifraDeTitular, dineroCorto } from '../nucleos.js'
import { colorTipo, etiquetaEsquema } from '../esquemas.js'

const props = defineProps({
  /** El grafo YA colapsado. */
  datos: { type: Object, default: null },
  /** El grafo sin colapsar: el CPV vive en el expediente, no en la arista. */
  crudo: { type: Object, default: null },
  /** Índice de TODA la base. Si está, manda él para los rankings de dinero. */
  indice: { type: Object, default: null },
  /** El índice entero, con el reparto por comunidad. Sólo con una edición. */
  indiceCompleto: { type: Object, default: null },
  /** La edición: una comunidad, o '' para toda España. */
  territorio: { type: String, default: '' },
  /** Las comunidades del volcado, para el selector. */
  territorios: { type: Array, default: () => [] },
  /** Organismos que no se han podido situar en ninguna comunidad. */
  sinTerritorio: { type: Number, default: 0 },
  /**
   * Del cargo a la empresa: autorizaciones de la Oficina de Conflictos de
   * Intereses que nombran una sociedad del mapa. Vienen con el grafo.
   */
  cruces: { type: Array, default: () => [] },
  nCruces: { type: Number, default: 0 },
  /**
   * De la empresa al escaño: actividades que los diputados declararon al
   * Congreso en una sociedad del mapa. También vienen con el grafo.
   */
  declarados: { type: Array, default: () => [] },
  nDeclarados: { type: Number, default: 0 },
  /** {comunidad: [presidencias]} según el BOE, para la edición de cada comunidad. */
  presidenciasAutonomicas: { type: Object, default: () => ({}) },
  /** Si la edición trae cargos: sin ellos no hay red de poder que ofrecer. */
  hayRed: { type: Boolean, default: false },
  /** Cuántas cotizadas trae la edición (CNMV), para la entrada de la red. */
  nCotizadas: { type: Number, default: 0 },
  /** Cuántas personas con cargo de alta instancia judicial o fiscal. */
  nAltasInstancias: { type: Number, default: 0 },
})
const emit = defineEmits(['seleccionar', 'verMapa', 'territorio', 'verCargo', 'verClave', 'verCargos', 'verRed'])

/** Lo que cobra una sociedad, si está en el extracto del índice. Contexto, no ranking. */
function cobraDe(clave) {
  const e = (props.indice?.entidades ?? []).find((x) => x.clave === clave)
  return e?.recibido ? Number(e.recibido) : 0
}

function fechaCorta(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso ?? '')
  if (!m) return ''
  const meses = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
  return `${Number(m[3])} ${meses[Number(m[2]) - 1]} ${m[1]}`
}

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

/** La edición de una comunidad, o null si es la de toda España o aún no ha llegado. */
const deTerritorio = computed(() =>
  props.territorio ? construirDirectorioDeTerritorio(props.indiceCompleto, props.territorio) : null,
)
const cargandoTerritorio = computed(() => Boolean(props.territorio) && !deTerritorio.value)
const presidentesDe = computed(() => props.presidenciasAutonomicas?.[props.territorio] ?? [])

const dir = computed(() => {
  if (deTerritorio.value) return deTerritorio.value
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

/*
  El espacio entre la cifra y su unidad es duro (`\u00a0`). «368 receptores»
  es una sola cosa: partido en dos renglones deja un «receptores» huérfano
  debajo del importe y la fila parece descuadrada. Con el espacio duro el
  renglón se corta por el separador, que es donde hay que cortarlo.
*/
const LISTAS = [
  {
    clave: 'pagadores',
    ante: 'Quién paga',
    titulo: 'Quién reparte más dinero público',
    que: 'Organismos y entidades por el total que sale de ellos hacia empresas y beneficiarios.',
    noEs: 'Encabezar esta lista no indica nada irregular: un servicio de salud compra para una comunidad entera.',
    unidad: (x) => `${x.n}\u00a0${x.n === 1 ? 'receptor' : 'receptores'}`,
  },
  {
    clave: 'receptores',
    ante: 'Quién cobra',
    titulo: 'Quién más cobra',
    que: 'Empresas y entidades por el total que reciben de administraciones públicas.',
    noEs: 'Facturar mucho es lo normal en sectores concentrados, como el farmacéutico o la obra civil.',
    unidad: (x) => `${x.n}\u00a0${x.n === 1 ? 'pagador' : 'pagadores'}`,
  },
  {
    clave: 'transversales',
    ante: 'Recorrido',
    titulo: 'Cobran de más administraciones distintas',
    que: 'Ordenado por número de pagadores diferentes, no por dinero: quien aparece en muchas administraciones ha hecho un recorrido que el importe no enseña.',
    noEs: 'Puede ser simplemente un proveedor de un servicio que todas necesitan.',
    unidad: (x) => `${x.n}\u00a0administraciones`,
    destacar: 'n',
  },
  {
    clave: 'extranjeras',
    ante: 'No residentes',
    titulo: 'Capital extranjero',
    que: 'Entidades con NIF de no residente (letras N y W) o NIE que cobran de administraciones españolas.',
    noEs: 'El NIF dice dónde tributan, no quién las controla. Una filial española de una matriz extranjera no aparece aquí.',
    unidad: (x) => `${x.n}\u00a0${x.n === 1 ? 'contraparte' : 'contrapartes'}`,
  },
  {
    clave: 'sancionados',
    ante: 'Sanciones',
    titulo: 'Expedientes del Tribunal de Cuentas',
    que: 'Formaciones políticas con expedientes sancionadores del Tribunal de Cuentas y su cuantía.',
    noEs: 'Es una deuda con el Estado, no un pago a nadie: no es financiación en ningún sentido.',
    unidad: (x) => `${x.expedientes ?? x.n}\u00a0${(x.expedientes ?? x.n) === 1 ? 'expediente' : 'expedientes'}`,
    tono: 'sancion',
  },
]

/*
  En la edición de una comunidad las listas cambian de pregunta, y lo dicen:
  «quién más cobra» pasa a ser «quién más cobra de las administraciones de
  Andalucía», con lo que cobra de ellas y qué parte es de todo lo suyo. Las
  que no se pueden contestar por comunidad —cuántas administraciones distintas
  pagan a alguien, las sanciones— no salen, en vez de salir con los datos de
  toda España bajo un título que diría otra cosa.
*/
function listasDe(t) {
  if (!t) return LISTAS
  const parte = (x) =>
    x.parte == null ? '' : x.parte >= 0.995 ? 'todo lo que cobra' : `el ${Math.round(x.parte * 100)}\u00a0% de lo que cobra`
  return [
    {
      ...LISTAS[0],
      ante: `Quién paga en ${t}`,
      titulo: `Qué organismos de ${t} reparten más`,
      que: `Administraciones autonómicas y locales de ${t}, por lo que sale de ellas hacia empresas y beneficiarios.`,
    },
    {
      ...LISTAS[1],
      ante: `Quién cobra de ${t}`,
      titulo: `Quién más cobra de las administraciones de ${t}`,
      que: `Empresas y entidades por lo que reciben de organismos de ${t}. Al lado, qué parte es de todo lo que cobran.`,
      noEs: 'Cobrar mucho de una administración es lo normal para quien presta un servicio que sólo ella compra.',
      unidad: parte,
    },
    { ...LISTAS[3], que: `Entidades con NIF de no residente que cobran de organismos de ${t}.`, unidad: parte },
  ]
}

const listas = computed(() =>
  listasDe(props.territorio)
    .map((l) => ({ ...l, filas: dir.value[l.clave] ?? [] }))
    .filter((l) => l.filas.length),
)

function tope(filas, campo = 'total') {
  return Math.max(1, ...filas.map((f) => f[campo] ?? 0))
}

/**
 * Cuánto ocupa la barra de fondo de una fila, en porcentaje del primero.
 *
 * Proporcional de verdad, sin raíz ni mínimos: aquí la cifra exacta va al lado
 * en la misma línea, así que una barra corta no esconde nada — y en una lista
 * lo que se quiere ver de un vistazo es precisamente si el primero se lleva
 * casi todo o si está repartido.
 */
/** La cifra destacada: la magnitud por la que la lista está ordenada. */
function cifraCabeza(f, lista) {
  if (lista.destacar === 'n') return lista.unidad(f)
  return dineroCorto(f.total)
}

function proporcion(f, lista) {
  const campo = lista.destacar === 'n' ? 'n' : 'total'
  // Hasta el 100 %: la barra corre sobre una pista del ancho entero, así que
  // la primera fila llena la pista y se ve que es la medida, no una selección.
  // (Sin pista, una barra que llegaba al borde parecía un subrayado.)
  return Math.max(1, ((f[campo] ?? 0) / tope(lista.filas, campo)) * 100)
}

/** 01, 02… : el puesto en mono, como en una tabla de clasificación. */
function puesto(i) {
  return String(i + 1).padStart(2, '0')
}

function color(schema) {
  return colorTipo(schema)
}

/*
  Diez filas por lista, y el resto detrás de un botón.

  Cada lista traía veinticinco. Cinco listas de veinticinco son ciento
  veinticinco renglones, casi siete mil píxeles de alto: quien entra no ve
  cinco respuestas, ve un volcado. Y la cola no se lee —el puesto 23 de «quién
  más cobra» no le dice nada a nadie— pero sí empuja hacia abajo lo siguiente,
  que sí importa.

  Diez es donde deja de haber salto: en los rankings de esta instantánea, del
  1 al 10 hay un orden de magnitud y del 10 al 25 hay una meseta. Quien quiera
  la meseta la tiene a un clic, y las veinticinco siguen contando para la
  barra, así que desplegar no cambia las proporciones.
*/
const VISIBLES = 10
const desplegadas = ref(new Set())

function alternar(clave) {
  const s = new Set(desplegadas.value)
  if (s.has(clave)) s.delete(clave)
  else s.add(clave)
  desplegadas.value = s
}

function filasVisibles(l) {
  return desplegadas.value.has(l.clave) ? l.filas : l.filas.slice(0, VISIBLES)
}
</script>

<template>
  <div class="portada">
    <!--
      Primera plana: un titular con la cifra, una entradilla y dos puertas.

      La cifra ES el titular. Antes iba en un bloque aparte —«5,7 MM €» en
      grande y debajo «seguidos hasta quien los cobra»— y el título de la
      página era «Dónde está el dinero», que no decía cuánto. Un periódico
      no escribe «MM»: escribe «5736 millones de euros», que se lee en voz
      alta.
    -->
    <section class="primera">
      <div class="apertura">
        <!--
          La edición, como las regionales de un periódico: la misma portada
          con lo que pagan las administraciones de una comunidad. Sólo si el
          volcado trae comunidades.
        -->
        <p class="antetitulo edicion">
          Contratos y subvenciones públicas en
          <label v-if="territorios.length" class="selector-edicion">
            <span class="visualmente-oculto">Edición</span>
            <select :value="territorio" @change="emit('territorio', $event.target.value)">
              <option value="">España</option>
              <option v-for="t in territorios" :key="t.nombre" :value="t.nombre">{{ t.nombre }}</option>
            </select>
          </label>
          <template v-else>España</template>
        </p>
        <h1 v-if="cargandoTerritorio" class="titular">{{ territorio }}</h1>
        <h1 v-else-if="territorio" class="titular">
          Adónde van <span class="cifra-titular">{{ cifraDeTitular(dir.totales.dineroTotal) }}</span>
          de las administraciones de {{ territorio }}
        </h1>
        <h1 v-else class="titular">
          Adónde van <span class="cifra-titular">{{ cifraDeTitular(dir.totales.dineroTotal) }}</span>
          de dinero público
        </h1>
        <p class="entradilla">
          Cada contrato y cada subvención publicados: de quién sale el dinero,
          quién lo cobra y cuánto, con el documento oficial a un clic.
        </p>
        <div class="acciones">
          <button class="boton solido" @click="emit('verMapa')">Abrir el mapa del dinero →</button>
          <span class="o">o escribe un nombre en el buscador</span>
        </div>
      </div>

      <!--
        Cómo se lee, en tres renglones, al lado del titular y no al pie.
        El tercero es el que más importa y el que antes iba en letra pequeña
        al final de cada lista: que nada de esto, por sí solo, es una
        irregularidad. Una lista ordenada por euros se lee sola como una
        lista de sospechosos (spec §12), así que el aviso va ANTES.
      -->
      <aside class="como-se-lee" aria-label="Cómo se lee">
        <p class="antetitulo">Cómo se lee</p>
        <ol>
          <li>
            <span class="puesto-num">01</span>
            <span>Cada nombre abre su ficha: a quién paga, de quién cobra y cuánto.</span>
          </li>
          <li>
            <span class="puesto-num">02</span>
            <span>Cada cifra sale de un documento oficial, y la ficha lleva a él.</span>
          </li>
          <li>
            <span class="puesto-num">03</span>
            <span>Nada de esto indica por sí solo algo irregular: comprar mucho es lo
            normal en quien compra para mucha gente.</span>
          </li>
        </ol>
      </aside>
    </section>

    <p v-if="cargandoTerritorio" class="nota">Cargando la edición de {{ territorio }}…</p>
    <!--
      Lo que la edición NO cuenta, antes de las cifras: los organismos que no
      se han podido situar en ninguna comunidad no están en ninguna. Sin
      decirlo, una comunidad parecería gastar menos de lo que gasta.
    -->
    <div v-if="territorio && !cargandoTerritorio" class="aviso-edicion">
      <p class="nota">
        Cuenta lo que pagan los organismos que la propia fuente sitúa en {{ territorio }}.
        <template v-if="sinTerritorio">
          Otros {{ sinTerritorio.toLocaleString('es-ES') }} organismos no se han podido situar
          en ninguna comunidad y no están en ninguna edición.
        </template>
        Lo que paga el Estado no es de ninguna comunidad.
      </p>
    </div>

    <!--
      Quién presidía la comunidad, según el BOE: el Real Decreto que nombra
      a cada presidente autonómico tras su investidura. Sin partido: el BOE
      no lo dice, y no se completa de otra parte.
    -->
    <div v-if="territorio && !cargandoTerritorio && presidentesDe.length" class="presidencias-comunidad">
      <p class="antetitulo">Presidencia de la comunidad, según el BOE</p>
      <ol>
        <li v-for="p in presidentesDe" :key="p.persona + (p.desde ?? p.hasta ?? '')">
          <a href="#" @click.prevent="emit('verCargo', p.persona)">{{ p.nombre }}</a>
          <span v-if="p.desde" class="tramo">nombramiento del {{ fechaCorta(p.desde) }}</span>
          <span v-else-if="p.hasta" class="tramo">cese el {{ fechaCorta(p.hasta) }}</span>
        </li>
      </ol>
      <p class="nota">
        Sólo lo leído del BOE, que no dice el partido. Una presidencia sin cese
        leído dura hasta el nombramiento siguiente.
      </p>
    </div>

    <dl v-if="territorio && !cargandoTerritorio" class="apoyo">
      <div>
        <dt>organismos de {{ territorio }}</dt>
        <dd>{{ dir.totales.nOrganismos.toLocaleString('es-ES') }}</dd>
      </div>
      <div>
        <dt>cobran de ellos</dt>
        <dd>{{ dir.totales.nReceptores.toLocaleString('es-ES') }}</dd>
      </div>
      <div v-if="dir.totales.nExtranjeras">
        <dt>no residentes</dt>
        <dd>{{ dir.totales.nExtranjeras.toLocaleString('es-ES') }}</dd>
      </div>
    </dl>
    <dl v-else-if="!territorio" class="apoyo">
      <div>
        <dt>entidades en la base</dt>
        <dd>{{ dir.totales.nActores.toLocaleString('es-ES') }}</dd>
      </div>
      <div v-if="fueraDelMapa">
        <dt>caben en el mapa</dt>
        <dd>{{ (dir.totales.enMapa ?? 0).toLocaleString('es-ES') }}</dd>
      </div>
      <div v-if="dir.totales.nPartidos">
        <dt>formaciones políticas</dt>
        <dd>{{ dir.totales.nPartidos.toLocaleString('es-ES') }}</dd>
      </div>
    </dl>

    <!--
      Las listas, como tablas de clasificación de un periódico: filete grueso
      arriba, antetítulo, título, qué mide y —antes de la primera fila— lo
      que NO significa.
    -->
    <!--
      La entrada a la red de poder: personas y entidades unidas por hechos
      con fuente. Cada enlace sólo sale si la edición trae con qué.
    -->
    <section v-if="hayRed && !territorio" class="red-entrada">
      <header class="seccion-cabeza">
        <p class="antetitulo">Red de poder</p>
        <h2>Quién está unido a quién, y quién lo dice</h2>
        <p class="que">
          Gobiernos, ministerios, partidos, tribunales, empresas cotizadas y sus accionistas, con
          las personas que la fuente une a cada uno: un nombramiento, un escaño, una autorización,
          una participación. Cada línea, con su documento.
        </p>
      </header>
      <ul class="red-enlaces">
        <li><a href="?v=poder" @click.prevent="emit('verRed', '')">El Gobierno en curso y sus ministerios →</a></li>
        <li v-if="nAltasInstancias">
          <a href="?v=poder&n=organismo:tribunal-constitucional" @click.prevent="emit('verRed', 'organismo:tribunal-constitucional')">
            El Constitucional: quién propuso a cada magistrado →
          </a>
        </li>
        <li v-if="nCotizadas">
          <a href="?v=poder&n=nif:A28297059" @click.prevent="emit('verRed', 'nif:A28297059')">Los accionistas de un grupo de medios: Prisa →</a>
        </li>
        <li v-if="nCotizadas">
          <a href="?v=poder&n=nif:A28599033" @click.prevent="emit('verRed', 'nif:A28599033')">Indra: sus accionistas, sus ex altos cargos y de quién cobra →</a>
        </li>
      </ul>
    </section>

    <div class="rejilla">
      <section v-for="l in listas" :key="l.clave" class="seccion" :class="l.tono">
        <header class="seccion-cabeza">
          <p class="antetitulo">{{ l.ante }}</p>
          <h2>{{ l.titulo }}</h2>
          <p class="que">{{ l.que }}</p>
          <p class="nota">{{ l.noEs }}</p>
        </header>
        <ol class="ranking">
          <!--
            La fila ENTERA es el botón. Antes sólo lo era el nombre: el resto
            de la línea —el puesto, el tipo, la cifra— no hacía nada al
            pulsarlo, y había que explicar en un párrafo que se podía pulsar.
            Si hay que decirlo, es que no se ve.
          -->
          <li v-for="(f, i) in filasVisibles(l)" :key="f.id">
            <button class="fila" @click="emit('seleccionar', f.id)">
              <span class="puesto-num">{{ puesto(i) }}</span>
              <span class="nombre">
                <span class="punto-tipo" :style="{ background: color(f.schema) }" />
                <span class="etiqueta" :title="f.caption">{{ f.caption }}</span>
              </span>
              <!--
                La cifra grande es SIEMPRE la magnitud por la que está
                ordenada la lista. En «cobran de más administraciones» se
                enseñaba el dinero al lado de una barra que medía
                administraciones: el número 3 tenía la barra más larga que el
                7 y la cifra cinco veces menor.
              -->
              <span class="cifra">{{ cifraCabeza(f, l) }}</span>
              <span class="meta">
                {{ etiquetaEsquema(f.schema) }} ·
                <!-- La otra magnitud, la que no encabeza la fila. -->
                <template v-if="l.destacar === 'n'">{{ dineroCorto(f.total) }}</template>
                <template v-else>{{ l.unidad(f) }}</template>
                <span v-if="f.extranjera && l.clave !== 'extranjeras'">· no residente</span>
                <!--
                  Está en la base pero no en el grafo publicado: se puede
                  abrir su ficha y ver sus cifras, no su red. Decirlo aquí
                  evita que el clic parezca roto.
                -->
                <span v-if="f.enMapa === false">· sin red en el mapa</span>
              </span>
              <!--
                La barra, del color de quien es (docs/diseno.md §2): cobriza
                si es una administración, azul si es una empresa. Corre sobre
                una pista de ancho entero, que es lo que la hace leerse como
                medida y no como subrayado.
              -->
              <span class="pista" aria-hidden="true">
                <span
                  class="barra"
                  :style="{
                    width: `${proporcion(f, l)}%`,
                    background: l.tono === 'sancion' ? 'var(--sancion)' : color(f.schema),
                  }"
                />
              </span>
            </button>
          </li>
        </ol>
        <button v-if="l.filas.length > VISIBLES" class="mas" @click="alternar(l.clave)">
          {{
            desplegadas.has(l.clave)
              ? 'Ver sólo las diez primeras'
              : `Ver las ${l.filas.length} de la lista`
          }}
        </button>
      </section>

      <!--
        Publicidad institucional. Se enseña el objeto del contrato, no una
        etiqueta sobre la empresa: el dato dice para qué era el contrato, y de
        ahí no se sigue que el adjudicatario sea un medio de comunicación.

        El título decía «y medios» y prometía algo que el dato no dice. Los
        cuatro contratos de cabeza de la instantánea del 22/9 los cobran dos
        aerolíneas (promoción del turismo navarro y extremeño), un club de
        fútbol, un obrador y una agencia de medios vasca. Todos son contratos
        de publicidad y ninguno de los cuatro es un medio de comunicación.
        Por eso el título no lo afirma y el matiz va arriba, en la nota.
      -->
      <!--
        Del cargo a la empresa. Es la pregunta que trajo el proyecto hasta
        aquí —¿dónde acaban los que mandaron?—, contestada sólo con lo que
        afirma una fuente oficial: la Oficina de Conflictos de Intereses
        autorizó a esta persona a trabajar en esta sociedad. Por fecha, no
        por dinero: ordenada por euros se leería como una lista de
        sospechosos, y no lo es.
      -->

      <section v-if="cruces.length && !territorio" class="seccion puertas">
        <header class="seccion-cabeza">
          <p class="antetitulo">Puertas giratorias</p>
          <h2>Del cargo a la empresa</h2>
          <p class="que">
            Ex altos cargos a los que la Oficina de Conflictos de Intereses
            autorizó a trabajar, tras su cese, en una entidad que cobra dinero
            público en esta edición: una empresa, una fundación, una federación,
            una universidad.
          </p>
          <p class="nota">
            Una autorización no dice que la persona llegara a ocupar el puesto,
            y que la entidad cobre de una administración no dice nada de ella.
            Tampoco que la pagara el órgano que la persona dirigía, cuando se
            dice: son hechos documentados puestos uno al lado del otro.
          </p>
        </header>
        <ol class="cruces">
          <li v-for="(c, i) in cruces.slice(0, desplegadas.has('puertas') ? cruces.length : VISIBLES)" :key="i" class="cruce">
            <p class="cruce-quien">
              <a href="#" @click.prevent="emit('verCargo', c.persona)">{{ c.nombre }}</a>
              <span v-if="c.cargoAnterior" class="cruce-cargo">{{ c.cargoAnterior.toLowerCase() }}</span>
              <!-- Quién gobernaba cuando se le nombró para ese cargo, si se sabe. -->
              <span v-if="c.gobierno" class="cruce-cargo">
                · Gobierno de {{ c.gobierno.nombre }}<template v-if="c.gobierno.formacion"> ({{ c.gobierno.formacion }})</template>
              </span>
            </p>
            <p class="cruce-donde">
              <span class="flecha" aria-hidden="true">→</span>
              <a href="#" class="cruce-empresa" @click.prevent="emit('verClave', c.empresa.clave)">{{ c.empresa.nombre }}</a>
              <span v-if="cobraDe(c.empresa.clave)" class="cruce-cobra">cobra {{ dineroCorto(cobraDe(c.empresa.clave)) }} públicos</span>
            </p>
            <p class="cruce-que">{{ c.actividad }}<template v-if="c.fecha"> · autorización del {{ fechaCorta(c.fecha) }}</template></p>
            <!-- El órgano que dirigía, si pagó a esa sociedad: dos hechos, uno al lado del otro. -->
            <p v-for="(d, k) in c.delOrgano ?? []" :key="k" class="cruce-organo">
              {{ d.organo.nombre }}, que dirigía, le {{ delOrganoEnPalabras(d).verbo }}
              {{ [dineroCorto(d.importe), delOrganoEnPalabras(d).cuando].filter(Boolean).join(' ') }}
            </p>
          </li>
        </ol>
        <button v-if="cruces.length > VISIBLES" class="mas" @click="alternar('puertas')">
          {{ desplegadas.has('puertas') ? 'Ver menos' : `Ver los ${cruces.length}` }}
        </button>
        <button class="mas" @click="emit('verCargos')">
          Todos los altos cargos y sus autorizaciones →
        </button>
      </section>

      <!--
        El otro sentido: diputados que declararon al Congreso haber trabajado
        en una sociedad que cobra dinero público en esta edición. Por orden
        de sociedad, no de dinero, por lo mismo que arriba.
      -->
      <section v-if="declarados.length && !territorio" class="seccion puertas">
        <header class="seccion-cabeza">
          <p class="antetitulo">Intereses declarados</p>
          <h2>De la empresa al escaño</h2>
          <p class="que">
            Diputados que declararon al Congreso haber trabajado en una
            sociedad que cobra dinero público en esta edición.
          </p>
          <p class="nota">
            Es lo que cada diputado declaró de su actividad al tomar posesión,
            con sus palabras. Que la sociedad cobre de una administración no
            dice nada de ella ni de él.
          </p>
        </header>
        <ol class="cruces">
          <li v-for="(c, i) in declarados.slice(0, desplegadas.has('declarados') ? declarados.length : VISIBLES)" :key="i" class="cruce">
            <p class="cruce-quien">
              <a href="#" @click.prevent="emit('verCargo', c.persona)">{{ c.nombre }}</a>
              <span v-if="c.formacion" class="cruce-cargo" title="Formación con la que fue elegido, según el Congreso">{{ c.formacion }}</span>
            </p>
            <p class="cruce-donde">
              <span class="flecha" aria-hidden="true">←</span>
              <a href="#" class="cruce-empresa" @click.prevent="emit('verClave', c.empresa.clave)">{{ c.empresa.nombre }}</a>
              <span v-if="cobraDe(c.empresa.clave)" class="cruce-cobra">cobra {{ dineroCorto(cobraDe(c.empresa.clave)) }} públicos</span>
            </p>
            <p class="cruce-que">
              {{ [c.descripcion, c.periodo].filter(Boolean).join(' · ') }}
            </p>
          </li>
        </ol>
        <button v-if="declarados.length > VISIBLES" class="mas" @click="alternar('declarados')">
          {{ desplegadas.has('declarados') ? 'Ver menos' : `Ver los ${declarados.length}` }}
        </button>
      </section>

      <section v-if="medios.contratos.length && !territorio" class="seccion medios">
        <header class="seccion-cabeza">
          <p class="antetitulo">Publicidad</p>
          <h2>Gasto en publicidad institucional</h2>
          <p class="que">
            <b>{{ dinero(medios.total) }}</b> en {{ medios.contratos.length }}
            {{ medios.contratos.length === 1 ? 'adjudicación' : 'adjudicaciones' }}
            cuyo objeto es publicidad, edición, radio, televisión o relaciones
            públicas, según el código CPV que el propio órgano de contratación
            asignó al expediente.
          </p>
          <p class="nota">
            Es de qué iba el contrato, no qué es quien lo cobra: puede ser un
            medio, y puede ser la agencia que compra los espacios, la
            productora o la imprenta.
          </p>
        </header>

        <div class="dos-columnas">
          <div>
            <h3 class="subtitulo">Quién cobra</h3>
            <ul class="lista">
              <li v-for="e in medios.porEmpresa" :key="e.id">
                <button @click="emit('seleccionar', e.id)">{{ e.caption }}</button>
                <span class="cifra">{{ dinero(e.total) }}</span>
              </li>
            </ul>
          </div>
          <div>
            <h3 class="subtitulo">Quién paga</h3>
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
                <span class="sello">CPV {{ c.cpv }}</span>
                {{ c.etiqueta }}
                <a v-if="c.url" :href="c.url" target="_blank" rel="noopener noreferrer">ver el expediente</a>
              </p>
            </li>
          </ul>
        </details>
      </section>
    </div>

    <!--
      El método, al pie y con su filete doble, como la caja de «cómo se ha
      hecho» de una pieza de datos. Antes era un párrafo gris de 0,73rem y
      se leía como letra pequeña; es lo que dice qué NO está, que aquí vale
      tanto como lo que está.
    -->
    <footer class="metodo">
      <h2>Qué hay y qué no</h2>
      <p>
        <template v-if="fueraDelMapa">
          Las listas cubren las
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
      </p>
      <p v-if="dir.totales.nSinCifra">
        Otras <b>{{ dir.totales.nSinCifra.toLocaleString('es-ES') }}</b>
        operaciones constan pero sin cifra utilizable, así que no suman en
        ningún total: casi siempre porque el importe publicado es el del
        acuerdo marco entero y figura repetido en cada adjudicatario, que no es
        lo que cobra cada uno.
      </p>
    </footer>
  </div>
</template>

<style scoped>
.portada {
  overflow-y: auto; height: 100%;
  padding: var(--e6) var(--e5) var(--e8);
}
.portada > * { max-width: 78rem; margin-left: auto; margin-right: auto; }

/* --- Primera plana ------------------------------------------------------- */

.edicion { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0 0.4em; }
.selector-edicion select {
  font: inherit; letter-spacing: inherit; text-transform: inherit; color: var(--tinta);
  background: transparent; border: none; border-bottom: 1.5px solid var(--tinta);
  padding: 0 1.1em 0.05em 0; cursor: pointer; appearance: none; -webkit-appearance: none;
  background-image: linear-gradient(45deg, transparent 50%, currentColor 50%),
    linear-gradient(135deg, currentColor 50%, transparent 50%);
  background-position: calc(100% - 0.45em) 55%, calc(100% - 0.15em) 55%;
  background-size: 0.3em 0.3em;
  background-repeat: no-repeat;
}
.selector-edicion select:focus-visible { outline: 2px solid var(--tinta); outline-offset: 2px; }
.visualmente-oculto {
  position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap;
}
.aviso-edicion { margin-top: var(--e5); }
.aviso-edicion .nota { max-width: var(--medida); margin: 0; }
.presidencias-comunidad { margin-top: var(--e4); }
.presidencias-comunidad ol {
  list-style: none; margin: var(--e2) 0; padding: 0;
  display: flex; flex-wrap: wrap; gap: var(--e2) var(--e5);
}
.presidencias-comunidad li { display: flex; flex-direction: column; gap: 0.1rem; }
.presidencias-comunidad a { color: var(--tinta); font-weight: 600; font-size: var(--t-s); }
.presidencias-comunidad .tramo { font-family: var(--mono); font-size: var(--t-xs); color: var(--tinta-3); }
.presidencias-comunidad .nota { max-width: var(--medida); margin: 0; font-size: var(--t-xs); }

.primera {
  display: grid; gap: var(--e6) var(--e7);
  grid-template-columns: minmax(0, 1fr) minmax(16rem, 22rem);
  align-items: end;
}
.titular {
  font-size: var(--t-titular); line-height: 1.04; letter-spacing: -0.022em;
  font-weight: 600; margin: 0; max-width: 20ch;
}
/*
  Subrayado de rotulador en cobrizo, el color de «administración»: el
  dinero del titular es el que sale de las administraciones. No decora,
  dice de dónde es la cifra (docs/diseno.md §2).
*/
.cifra-titular {
  background: linear-gradient(transparent 64%, color-mix(in srgb, var(--adm) 24%, transparent) 64%, color-mix(in srgb, var(--adm) 24%, transparent) 92%, transparent 92%);
  box-decoration-break: clone; -webkit-box-decoration-break: clone;
}
/* La cifra no se parte en ancho; en un teléfono de 360 px no cabe entera. */
@media (min-width: 601px) {
  .cifra-titular { white-space: nowrap; }
}
.entradilla {
  font-family: var(--serif); font-size: var(--t-l); line-height: 1.5;
  color: var(--tinta-2); margin: var(--e4) 0 0; max-width: 46ch;
}
.acciones {
  display: flex; flex-wrap: wrap; align-items: center; gap: var(--e3) var(--e4);
  margin-top: var(--e5);
}
.acciones .boton { font-size: var(--t-m); padding: 0.6rem 1rem; }
.acciones .o { font-size: var(--t-s); color: var(--tinta-3); }

.como-se-lee {
  border-top: 2px solid var(--filete); padding-top: var(--e3);
}
.como-se-lee ol { list-style: none; margin: 0; padding: 0; }
.como-se-lee li {
  display: grid; grid-template-columns: 1.8rem 1fr; gap: var(--e2);
  padding: var(--e2) 0; border-bottom: 1px solid var(--filete-suave);
  font-size: var(--t-s); line-height: 1.45; color: var(--tinta-2);
}
.como-se-lee li:last-child { border-bottom: none; color: var(--tinta); }
.como-se-lee .puesto-num { padding-top: 0.1rem; }

/*
  Las cifras de apoyo, entre dos filetes y separadas por reglas finas: la
  banda de datos de debajo de un titular. Van en la serif, con las cifras
  de la fuente: a este tamaño se leen como números de prensa, no de hoja de
  cálculo.
*/
.apoyo {
  display: flex; flex-wrap: wrap; margin-top: var(--e6); margin-bottom: 0;
  border-top: 1px solid var(--filete); border-bottom: 1px solid var(--filete-suave);
}
.apoyo div {
  display: flex; flex-direction: column-reverse; gap: 0.1rem;
  padding: var(--e3) var(--e5) var(--e3) 0; margin-right: var(--e5);
  border-right: 1px solid var(--filete-suave);
}
.apoyo div:last-child { border-right: none; }
.apoyo dt { font-size: var(--t-xs); color: var(--tinta-3); }
.apoyo dd {
  margin: 0; font-family: var(--serif); font-size: var(--t-h2); font-weight: 600;
  color: var(--tinta); line-height: 1.1;
}

/* --- Las listas ---------------------------------------------------------- */

/*
  Dos columnas y no tres. Los nombres oficiales de este país son larguísimos
  —«Consejería de Presidencia, Justicia y Administración Local»— y en una
  columna estrecha se parten en tres renglones: la lista deja de leerse como
  una lista. `min(30rem, 100%)`: el mínimo de un `minmax` NO encoge, y en un
  móvil de 390 px la columna se salía por la derecha.
*/
.rejilla {
  display: grid; gap: var(--e7) var(--e7); margin-top: var(--e7);
  grid-template-columns: repeat(auto-fit, minmax(min(30rem, 100%), 1fr));
  align-items: start;
}

.seccion { border-top: 3px solid var(--filete); padding-top: var(--e3); min-width: 0; }
.seccion-cabeza h2 { font-size: var(--t-h2); margin: 0 0 var(--e2); }
.que {
  font-size: var(--t-s); color: var(--tinta-2); line-height: 1.5;
  margin: 0; max-width: 52ch;
}
.seccion-cabeza .nota { font-size: var(--t-s); margin: var(--e3) 0 var(--e4); max-width: 52ch; }

.ranking { list-style: none; margin: 0; padding: 0; }

/*
  Rejilla con áreas: la cifra cambia de renglón sin cambiar el HTML. En
  ancho va a la derecha del nombre; en móvil baja al renglón del tipo, que
  va sobrado de sitio. La barra, siempre debajo y a todo el ancho.
*/
.fila {
  width: 100%; display: grid; gap: 0 var(--e3);
  grid-template-columns: 1.6rem minmax(0, 1fr) auto;
  grid-template-areas:
    "puesto nombre cifra"
    "hueco  meta   meta"
    "hueco  pista  pista";
  align-items: baseline;
  background: none; border: none; color: inherit; font: inherit; text-align: left;
  padding: 0.65rem var(--e2) 0.7rem; margin: 0 calc(-1 * var(--e2));
  cursor: pointer; border-radius: var(--radio-s);
}
/* Con la barra en su pista, el fondo ya no significa nada: puede marcar el ratón. */
.fila:hover, .fila:focus-visible { background: var(--papel-2); outline: none; }
.fila:hover .etiqueta, .fila:focus-visible .etiqueta {
  text-decoration: underline; text-decoration-color: var(--filete-medio);
  text-underline-offset: 0.18em;
}
.fila:focus-visible { box-shadow: inset 0 0 0 2px var(--tinta); }

.fila .puesto-num { grid-area: puesto; }
.nombre {
  grid-area: nombre; display: flex; align-items: baseline; gap: var(--e2);
  color: var(--tinta); font-size: var(--t-m); line-height: 1.35; font-weight: 550;
}
/*
  Dos renglones como mucho. «UTE: OBRASCON HUARTE LAIN, S.A., AZVI, S.A.U. Y
  ROVER INFRAESTRUCTURAS…» ocupaba cuatro. El nombre entero está en el
  `title` y en la ficha, a un clic.
*/
.etiqueta {
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden; min-width: 0;
}
.cifra {
  grid-area: cifra; font-variant-numeric: tabular-nums; white-space: nowrap;
  color: var(--tinta); font-weight: 650; font-size: var(--t-m);
}
.meta {
  grid-area: meta; display: block; min-width: 0;
  font-size: var(--t-xs); color: var(--tinta-3); margin-top: 0.15rem;
}
.pista {
  grid-area: pista; display: block; height: 4px; margin-top: 0.45rem;
  background: var(--papel-3); border-radius: 1px; overflow: hidden;
}
.barra { display: block; height: 100%; }

.mas {
  display: block; width: 100%; margin: var(--e3) 0 0; padding: 0.55rem;
  background: none; border: none; border-top: 1px solid var(--filete-suave);
  color: var(--tinta); font: inherit; font-size: var(--t-s); font-weight: 600;
  cursor: pointer; text-decoration: underline; text-decoration-color: var(--filete-medio);
  text-underline-offset: 0.18em;
}
.mas:hover { text-decoration-color: currentColor; }

/* --- Puertas giratorias -------------------------------------------------- */

.cruces { list-style: none; margin: 0; padding: 0; }
.cruce { padding: 0.65rem 0; border-bottom: 1px solid var(--filete-suave); }
.cruce p { margin: 0; }
.cruce-quien { display: flex; flex-wrap: wrap; gap: 0 var(--e2); align-items: baseline; }
.cruce-quien a { color: var(--tinta); font-weight: 600; font-size: var(--t-m); }
.cruce-cargo { font-size: var(--t-xs); color: var(--tinta-3); }
.cruce-donde { display: flex; flex-wrap: wrap; gap: 0 var(--e2); align-items: baseline; margin-top: 0.15rem !important; }
.cruce-empresa { color: var(--emp); font-weight: 600; }
.cruce-cobra { font-size: var(--t-xs); color: var(--tinta-3); font-variant-numeric: tabular-nums; }
.cruce-que { font-size: var(--t-xs); color: var(--tinta-2); margin-top: 0.2rem !important; line-height: 1.45; }
.cruce-organo {
  font-size: var(--t-xs); color: var(--tinta-2); margin-top: 0.25rem !important;
  padding-left: 0.5rem; border-left: 2px solid var(--adm);
}

/* --- Publicidad ---------------------------------------------------------- */

.dos-columnas { display: grid; grid-template-columns: 1fr 1fr; gap: var(--e4) var(--e5); }
.subtitulo {
  font-family: var(--sans); font-size: var(--t-xs); font-weight: 650;
  letter-spacing: 0.1em; text-transform: uppercase; color: var(--tinta-3);
  margin: 0 0 var(--e1);
}
.lista { list-style: none; margin: 0; padding: 0; }
.lista > li {
  display: flex; justify-content: space-between; gap: var(--e3); align-items: baseline;
  padding: 0.4rem 0; border-bottom: 1px solid var(--filete-suave); font-size: var(--t-s);
}
.lista .cifra { font-size: var(--t-s); }
.lista button {
  background: none; border: none; color: var(--tinta); font: inherit; padding: 0;
  cursor: pointer; text-align: left;
}
.lista button:hover { text-decoration: underline; text-underline-offset: 0.18em; }

.expedientes { margin-top: var(--e4); }
.expedientes summary {
  cursor: pointer; font-size: var(--t-s); font-weight: 600; color: var(--tinta);
  padding: var(--e2) 0; text-decoration: underline; text-decoration-color: var(--filete-medio);
  text-underline-offset: 0.18em;
}
.detalle > li { display: block; padding: 0.6rem 0; }
.titulo-contrato {
  margin: 0 0 0.25rem; font-family: var(--serif); font-size: var(--t-m); line-height: 1.35;
  color: var(--tinta);
}
.linea { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.4rem; margin: 0; font-size: var(--t-s); }
.linea.meta { font-size: var(--t-xs); color: var(--tinta-3); margin-top: 0.25rem; align-items: center; }
.flecha { color: var(--tinta-3); }

/* --- Método -------------------------------------------------------------- */

.metodo {
  margin-top: var(--e8); padding-top: var(--e4);
  border-top: 3px double var(--filete);
}
.metodo h2 { font-size: var(--t-h3); margin: 0 0 var(--e3); }
.metodo p {
  font-size: var(--t-s); color: var(--tinta-2); line-height: 1.6;
  max-width: var(--medida); margin: 0 0 var(--e3);
}

/* --- Estrecho ------------------------------------------------------------ */

@media (max-width: 900px) {
  .primera { grid-template-columns: 1fr; align-items: start; }
}

/*
  En móvil el nombre se queda el renglón entero y la cifra baja a la punta
  de la barra, como la etiqueta de un gráfico de barras. Al lado del tipo
  —«Organismo público · 31 receptores»— partía ese renglón en dos en un
  teléfono de 360 px; con renglón propio, diez filas eran dos pantallas y
  media.
*/
@media (max-width: 600px) {
  .portada { padding: var(--e5) var(--e4) var(--e7); }
  .fila {
    grid-template-columns: 1.6rem minmax(0, 1fr) auto;
    grid-template-areas:
      "puesto nombre nombre"
      "hueco  meta   meta"
      "hueco  pista  cifra";
  }
  .pista { align-self: center; margin-top: 0.3rem; }
  .cifra { justify-self: end; margin-top: 0.3rem; }
  .etiqueta { -webkit-line-clamp: 3; }
  .dos-columnas { grid-template-columns: 1fr; }
  /* Las tres en un renglón: con `flex-wrap` la tercera caía sola debajo. */
  .apoyo { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .apoyo div { padding: var(--e3) var(--e2) var(--e3) 0; margin-right: var(--e3); }
  .apoyo dd { font-size: var(--t-h3); }
  .rejilla { gap: var(--e6); margin-top: var(--e6); }
}
/*
  La franja de la red de poder: a lo ancho, bajo la cabecera, antes de las
  listas del dinero. Texto a la izquierda, entradas a la derecha.
*/
.red-entrada {
  display: grid; gap: var(--e3) var(--e7);
  grid-template-columns: minmax(0, 1fr) minmax(16rem, 26rem);
  align-items: end;
  /* Sólo arriba y abajo: los lados los pone la maqueta de la portada. */
  margin-top: var(--e6); margin-bottom: var(--e2); padding-top: var(--e3);
  border-top: 3px solid var(--filete);
}
.red-entrada h2 { margin: 0; }
.red-enlaces { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--e2); }
.red-enlaces a { color: var(--tinta); font-weight: 600; }
@media (max-width: 60rem) {
  .red-entrada { grid-template-columns: minmax(0, 1fr); }
}
</style>
