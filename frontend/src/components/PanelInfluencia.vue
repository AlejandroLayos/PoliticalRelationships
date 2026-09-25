<script setup>
/**
 * La ficha de influencia: los hechos, en texto y en cifras.
 *
 * El diagrama enseña la forma —de dónde entra, a dónde sale— pero no se puede
 * leer una cifra exacta de una banda de colores. Aquí van los números, las
 * contrapartes completas (el dibujo recorta, la lista no) y el rastro hasta el
 * documento del que sale cada cosa.
 */
import { computed, ref } from 'vue'
import { dineroCorto } from '../nucleos.js'
import { resumenEnPalabras } from '../influencia.js'
import { administracionDe, colorTipo, etiquetaEsquema } from '../esquemas.js'
import { fechaCorta, nombreDocumento, siglaFuente } from '../procedencia.js'

const props = defineProps({
  area: { type: Object, default: null },
  /** El grafo sin colapsar, para poder nombrar los expedientes puenteados. */
  crudo: { type: Object, default: null },
  /**
   * Las fuentes con su nombre legible. Viven en la cabecera del volcado y no
   * en el grafo, así que llegan aparte: sin ellas la procedencia diría
   * «placsp» en vez de «Plataforma de Contratación del Sector Público».
   */
  fuentes: { type: Array, default: () => [] },
  /** Los contratos de publicidad y medios de todo el grafo, ya calculados. */
  medios: { type: Object, default: null },
  /**
   * La fila del índice cuando la entidad NO está en el grafo publicado.
   *
   * Existe en la base y se sabe cuánto mueve, pero no con quién: el mapa está
   * acotado y no cupo. Enseñar una ficha vacía diría que no tiene relaciones,
   * que es falso.
   */
  fueraDelMapa: { type: Object, default: null },
})
const emit = defineEmits(['seleccionar', 'volver', 'expandir'])

const resumen = computed(() => resumenEnPalabras(props.area))

/**
 * Las entidades que comparten pagador, agrupadas por ese pagador.
 *
 * El orden de los grupos es el de la lista, que ya viene ordenada por cuántos
 * pagadores se comparten y por dinero: así el grupo de arriba es el más
 * poblado, no el del organismo con el nombre más corto.
 */
const gruposComparten = computed(() => {
  const grupos = new Map()
  for (const c of props.area?.comparten ?? []) {
    const via = c.via
    if (!via) continue
    if (!grupos.has(via.id)) grupos.set(via.id, { ...via, entidades: [] })
    grupos.get(via.id).entidades.push(c)
  }
  return [...grupos.values()]
})

/**
 * ¿Las listas completas nacen abiertas?
 *
 * Plegadas cuando el diagrama ya está dibujando las contrapartes —ahí la
 * lista es el detalle, no el titular— y abiertas cuando no hay diagrama que
 * mirar: si la entidad no entró en el mapa, la lista es lo único que hay.
 */
const abiertas = computed(() => Boolean(props.fueraDelMapa))

/**
 * Copia la dirección de esta ficha.
 *
 * `navigator.clipboard` no existe fuera de un contexto seguro y puede estar
 * denegado; el respaldo es enseñar la dirección para copiarla a mano, que es
 * peor pero no es nada.
 */
const copiado = ref(false)
async function copiarEnlace() {
  try {
    await navigator.clipboard.writeText(window.location.href)
    copiado.value = true
    setTimeout(() => {
      copiado.value = false
    }, 2000)
  } catch {
    window.prompt('Copia la dirección de esta ficha:', window.location.href)
  }
}

/** Los documentos de los que sale esta ficha. */
const procedencia = computed(() => {
  const id = props.area?.entidad?.id
  if (!id) return []
  return props.crudo?.provenance?.[id] ?? []
})

/** Un sello por fuente, con su sigla. */
const fuentesDeLaFicha = computed(() => [
  ...new Set(procedencia.value.map((d) => siglaFuente(props.fuentes, d.source_id))),
])

/*
  Un organismo grande sale de decenas de documentos —el Servicio Andaluz de
  Salud, de 29— y todos del mismo feed y del mismo día. Listarlos enteros es
  una pared de enlaces idénticos que además tapa el resto del panel.
  Se enseñan unos pocos y se dice cuántos quedan: lo que hace falta comprobar
  es que el documento existe y se puede abrir, no abrirlos los 29.
*/

/** Las dos concentraciones que haya —lo que paga y lo que recibe—, con su frase. */
const reparto = computed(() => {
  const a = props.area
  if (!a) return []
  const filas = []
  if (a.concentracionPagaA) {
    filas.push({
      clave: 'paga',
      c: a.concentracionPagaA,
      verbo: 'reparte',
      preposicion: 'va a',
      plural: 'receptores',
    })
  }
  if (a.concentracionRecibeDe) {
    filas.push({
      clave: 'recibe',
      c: a.concentracionRecibeDe,
      verbo: 'recibe',
      preposicion: 'viene de',
      plural: 'pagadores',
    })
  }
  return filas
})

const CUANTOS_DOCUMENTOS = 5
const documentosVisibles = computed(() => procedencia.value.slice(0, CUANTOS_DOCUMENTOS))
const documentosDeMas = computed(() =>
  Math.max(0, procedencia.value.length - CUANTOS_DOCUMENTOS),
)



/**
 * Los expedientes, con su nombre y con la dirección del expediente REAL.
 *
 * Y ésa es la diferencia que importa. La procedencia que se guarda de cada
 * dato es el fichero del que salió —un ATOM de sindicación de veinte megas—,
 * que sirve para reproducir la ingesta y no le sirve de nada a quien quiere
 * comprobar un contrato: se descarga un XML enorme y ahí se acaba el viaje.
 *
 * Pero el propio expediente trae en `sourceUrl` la ficha pública de la
 * plataforma, que es la página que una persona puede leer. Estaba guardada y
 * no se enseñaba en ningún sitio salvo en el bloque de publicidad de la
 * portada. «Cada cifra lleva el documento del que salió» sólo es verdad de
 * verdad si ese documento se puede abrir y entender.
 */
const expedientes = computed(() => {
  const m = new Map()
  for (const n of props.crudo?.nodes ?? []) {
    if (n.schema !== 'Contract') continue
    m.set(n.id, { nombre: n.caption, url: n.properties?.sourceUrl ?? '' })
  }
  return m
})

/** La contraparte cuyos expedientes están desplegados, si hay alguna. */
const expedientesAbiertos = ref('')

function alternarExpedientes(id) {
  expedientesAbiertos.value = expedientesAbiertos.value === id ? '' : id
}

/** Los expedientes de una contraparte, con nombre y enlace, sin repetir. */
function expedientesDe(c) {
  const vistos = new Set()
  const salida = []
  for (const id of c.expedientes ?? []) {
    if (vistos.has(id)) continue
    vistos.add(id)
    const e = expedientes.value.get(id)
    salida.push({ id, nombre: e?.nombre ?? id, url: e?.url ?? '' })
  }
  return salida
}

function tope(lista) {
  return Math.max(1, ...lista.map((x) => x.total))
}

function pct(v, max) {
  return `${Math.max(2, (v / max) * 100)}%`
}

function color(schema) {
  return colorTipo(schema)
}

/**
 * Los contratos de publicidad de ESTA entidad, la pague o la cobre.
 *
 * Es la pregunta «¿qué medios paga este ayuntamiento?» contestada desde la
 * ficha, sin tener que volver a la portada y buscar el nombre en una lista
 * general.
 */
const publicidad = computed(() => {
  const id = props.area?.entidad?.id
  if (!id || !props.medios) return []
  return props.medios.contratos.filter((c) => c.organoId === id || c.empresaId === id)
})

const publicidadTotal = computed(() =>
  publicidad.value.reduce((s, c) => s + c.importe, 0),
)

/** ¿La entidad es quien paga la publicidad, o quien la cobra? */
const pagaPublicidad = computed(
  () => publicidad.value.some((c) => c.organoId === props.area?.entidad?.id),
)

const sinDatos = computed(
  () => props.area && !props.area.recibeDe.length && !props.area.pagaA.length && !props.area.sanciones.length,
)
</script>

<template>
  <aside class="panel">
    <!-- Sólo en el índice: las cifras que hay, y por qué no hay más. -->
    <template v-if="fueraDelMapa">
      <div class="acciones">
        <button class="boton tenue" @click="emit('volver')">← Portada</button>
        <!--
          El botón existe para que se sepa que el enlace significa algo. Ahora
          cada ficha tiene su dirección, pero nadie mira la barra del
          navegador: sin un botón que lo diga, la función está y no la usa
          nadie.
        -->
        <button class="boton tenue" @click="copiarEnlace">
          {{ copiado ? '✓ Copiado' : 'Copiar enlace' }}
        </button>
      </div>
      <p class="antetitulo tipo">
        <span class="punto-tipo" :style="{ background: color(fueraDelMapa.schema) }" />
        {{ etiquetaEsquema(fueraDelMapa.schema) }}
      </p>
      <p v-if="administracionDe(fueraDelMapa)" class="administracion">{{ administracionDe(fueraDelMapa) }}</p>
      <h2>{{ fueraDelMapa.caption }}</h2>
      <p v-if="fueraDelMapa.nif" class="nif">NIF {{ fueraDelMapa.nif }}</p>

      <div class="cifras">
        <div class="cifra entra" :class="{ nada: !fueraDelMapa.recibido }">
          <span class="valor">
            {{ fueraDelMapa.recibido ? dineroCorto(fueraDelMapa.recibido) : 'No consta' }}
          </span>
          <span class="que">
            {{ fueraDelMapa.pagadores
              ? `recibe de ${fueraDelMapa.pagadores} ${fueraDelMapa.pagadores === 1 ? 'pagador' : 'pagadores'}`
              : 'que reciba dinero' }}
          </span>
        </div>
        <div class="cifra sale" :class="{ nada: !fueraDelMapa.pagado }">
          <span class="valor">
            {{ fueraDelMapa.pagado ? dineroCorto(fueraDelMapa.pagado) : 'No consta' }}
          </span>
          <span class="que">
            {{ fueraDelMapa.receptores
              ? `reparte entre ${fueraDelMapa.receptores} ${fueraDelMapa.receptores === 1 ? 'receptor' : 'receptores'}`
              : 'que pague a nadie' }}
          </span>
        </div>
      </div>

      <section class="bloque">
        <h3>Por qué no se ve su red</h3>
        <p class="matiz">
          Esta entidad está en la base con su procedencia, pero el mapa
          publicado se recorta a las relaciones con más dinero y ésta no entró.
          Las cifras de arriba salen del índice, que sí cubre todo lo ingerido;
          el detalle de con quién se relaciona no está en esta instantánea.
        </p>
      </section>
    </template>

    <p v-else-if="!area?.entidad" class="vacio">Pulsa una entidad del mapa.</p>

    <template v-else>
      <div class="acciones">
        <button class="boton tenue" @click="emit('volver')">← Portada</button>
        <!--
          El botón existe para que se sepa que el enlace significa algo. Ahora
          cada ficha tiene su dirección, pero nadie mira la barra del
          navegador: sin un botón que lo diga, la función está y no la usa
          nadie.
        -->
        <button class="boton tenue" @click="copiarEnlace">
          {{ copiado ? '✓ Copiado' : 'Copiar enlace' }}
        </button>
      </div>

      <p class="antetitulo tipo">
        <span class="punto-tipo" :style="{ background: color(area.entidad.schema) }" />
        {{ etiquetaEsquema(area.entidad.schema) }}
      </p>
      <!--
        De qué administración es, cuando la fuente lo dice. Es la pregunta de
        fondo de quien llega a la ficha de un organismo: ¿quién manda aquí?
      -->
      <p v-if="administracionDe(area.entidad)" class="administracion">{{ administracionDe(area.entidad) }}</p>
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
        La procedencia, en la ficha y no a dos clics.
        «Sin procedencia no se persiste» es la primera invariante del proyecto
        y la promesa que la portada hace en su primera frase, pero para ver el
        documento había que cambiar de vista. Una promesa que hay que ir a
        buscar a otra pantalla es media promesa.
        Va plegada y en una línea: quien sólo mira las cifras no la nota; quien
        duda de una tiene el documento ahí, con su huella y la fecha en que se
        descargó. Y va justo debajo de las cifras, como un sello de registro:
        es de dónde salen.
      -->
      <section v-if="procedencia.length" class="bloque procedencia">
        <details>
          <summary>
            <span v-for="f in fuentesDeLaFicha" :key="f" class="sello">{{ f }}</span>
            <span class="docs">
              {{ procedencia.length }}
              {{ procedencia.length === 1 ? 'documento guardado' : 'documentos guardados' }}
            </span>
          </summary>
          <ul>
            <li v-for="(d, i) in documentosVisibles" :key="i">
              <!--
                El texto del enlace es el NOMBRE DEL FICHERO, no el de la
                fuente: los 29 documentos de un organismo grande vienen todos
                del mismo sitio, así que repetir «Plataforma de Contratación
                del Sector Público» cinco veces seguidas no distingue nada. El
                fichero sí — lleva la fecha y el número de página del feed.
                La fuente ya está dicha una vez, arriba, en el resumen.
              -->
              <a :href="d.url" :title="d.url" target="_blank" rel="noopener noreferrer">
                {{ nombreDocumento(d.url) }}
              </a>
              <span class="cuando">leído el {{ fechaCorta(d.retrieved_at) }}</span>
              <!--
                La huella es lo que permite comprobar que el documento no ha
                cambiado desde que se leyó. Sin ella el enlace sólo dice «mira
                tú»; con ella, «esto es exactamente lo que leí».
              -->
              <code :title="d.content_hash">{{ d.content_hash.slice(0, 12) }}…</code>
              <blockquote v-if="d.excerpt">{{ d.excerpt }}</blockquote>
            </li>
            <li v-if="documentosDeMas" class="y-mas">
              y {{ documentosDeMas }} {{ documentosDeMas === 1 ? 'documento' : 'documentos' }}
              más, del mismo origen
            </li>
          </ul>
        </details>
      </section>

      <!--
        Cómo se reparte el dinero.

        La ficha decía «reparte 224 M € entre 77 receptores» y ahí se quedaba.
        Setenta y siete receptores suena a mucho reparto, y puede que los
        cinco primeros se lleven la mitad: es una diferencia grande y el
        número de receptores no la enseña. Y el panel tenía media pantalla en
        blanco justo debajo.
      -->
      <section v-if="reparto.length" class="bloque">
        <h3>Cómo se reparte</h3>
        <ul class="reparto">
          <li v-for="r in reparto" :key="r.clave">
            <p class="frase">
              El <b>{{ r.c.primero }} %</b> de lo que {{ r.verbo }} {{ r.preposicion }}
              <a href="#" class="enlace" @click.prevent="emit('seleccionar', r.c.idPrimero)">{{
                r.c.nombrePrimero
              }}</a><!--
              La razón social ya acaba muchas veces en punto —«S.A.U.»— y
              añadirle otro deja «S.A.U..».
              --><template v-if="!r.c.nombrePrimero.endsWith('.')">.</template>
              <template v-if="r.c.deCuantos > r.c.cuantos">
                Los {{ r.c.cuantos }} primeros se llevan el
                <b>{{ r.c.cabeza }} %</b>, de {{ r.c.deCuantos }}
                {{ r.plural }} con cifra.
              </template>
            </p>
            <span class="barra-reparto" aria-hidden="true">
              <i :style="{ width: `${r.c.primero}%` }" />
            </span>
          </li>
        </ul>
        <p v-if="area.periodo" class="matiz">
          Operaciones fechadas entre el {{ fechaCorta(area.periodo.desde) }} y el
          {{ fechaCorta(area.periodo.hasta) }}.
        </p>
        <!--
          Y el matiz de siempre, que aquí hace falta: una concentración alta
          no es irregular por sí misma. Hay mercados con tres proveedores en
          toda España, y una obra grande se adjudica entera a una empresa.
        -->
        <p class="nota">
          Una parte alta no indica nada irregular por sí misma: hay mercados
          con muy pocos proveedores, y una obra grande se adjudica entera.
        </p>
      </section>

      <!--
        Exposición a capital extranjero. Se dice de qué son los datos: el NIF
        de no residente prueba dónde tributa quien cobra o paga, y nada más.
        Presentarlo como «influencia extranjera» a secas sería afirmar algo
        que las fuentes no dicen.
      -->
      <section
        v-if="area.extranjero.contrapartes.length || area.extranjero.indicios.length"
        class="bloque extranjero"
      >
        <h3>Capital extranjero alrededor</h3>

        <template v-if="area.extranjero.contrapartes.length">
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
          <p class="nota">
            Lo afirma la letra del NIF: N para entidad extranjera, W para
            establecimiento permanente de no residente. Dice dónde tributan, no
            quién las controla.
          </p>
        </template>

        <!--
          Los indicios van debajo, con otro encabezado y sin sumar al
          porcentaje. Juntarlos convertiría una sospecha razonable en una
          afirmación, y la diferencia entre «lo dice su NIF» y «lo parece por
          el nombre» es justamente lo que aquí no se puede perder.
        -->
        <div v-if="area.extranjero.indicios.length" class="indicios">
          <h4>Probablemente extranjeras, sin confirmar</h4>
          <ul class="lista compacta">
            <li v-for="c in area.extranjero.indicios" :key="c.id">
              <button @click="emit('seleccionar', c.id)">{{ c.caption }}</button>
              <span class="importe">{{ dineroCorto(c.total) }}</span>
            </li>
          </ul>
          <p class="nota">
            No constan con NIF español y su nombre termina en una forma
            societaria extranjera. Es un indicio, no un dato de la Agencia
            Tributaria, y por eso no cuenta en el porcentaje de arriba.
          </p>
        </div>
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

      <!-- Publicidad institucional ---------------------------------------- -->
      <section v-if="publicidad.length" class="bloque">
        <h3>
          {{ pagaPublicidad ? 'Publicidad institucional que paga' : 'Publicidad institucional que cobra' }}
          <span class="cuenta">{{ publicidad.length }}</span>
        </h3>
        <p class="matiz">
          Contratos cuyo objeto es publicidad, edición, radio, televisión o
          relaciones públicas, por el código CPV que el órgano asignó al
          expediente. Suman {{ dineroCorto(publicidadTotal) }}.
        </p>
        <ul class="lista compacta">
          <li v-for="c in publicidad" :key="c.id">
            <button @click="emit('seleccionar', pagaPublicidad ? c.empresaId : c.organoId)">
              {{ pagaPublicidad ? c.empresa : c.organo }}
            </button>
            <span class="importe">
              {{ c.sinImporte ? 'sin cifra' : dineroCorto(c.importe) }}
            </span>
          </li>
        </ul>
        <p class="nota">
          Dice de qué iba el contrato, no qué es quien lo cobra: puede ser un
          medio, la agencia que compra los espacios o la productora.
        </p>
      </section>

      <!-- Ámbito de interés --------------------------------------------- -->
      <!--
        Cuando el único pagador que se comparte reparte entre veinte, no hay
        lista: hay una frase. En la ficha del PP salían el PSOE, VOX, ERC,
        Podemos y doce partidos más, cada uno con su cifra, bajo un título que
        decía «orbitan a sus mismos pagadores». Es verdad y no dice nada —lo
        que comparten es quien paga la subvención electoral a todos— y el
        matiz llegaba después de haber leído quince nombres de partidos
        juntos. Un falso positivo aquí es una acusación falsa (spec §12).
      -->
      <section v-if="area.compartenDeProgramaGeneral" class="bloque">
        <h3>Cobran de los mismos organismos</h3>
        <p class="matiz">
          Hay {{ area.compartenDeProgramaGeneral.entidades }} entidades que
          cobran de algún pagador de ésta, pero no se listan: el que comparten
          es
          <a href="#" class="enlace" @click.prevent="emit('seleccionar', area.compartenDeProgramaGeneral.id)">{{
            area.compartenDeProgramaGeneral.caption
          }}</a>, que reparte
          entre {{ area.compartenDeProgramaGeneral.alcance }}. Coincidir en un
          reparto general no es una relación entre ellas, y enseñarlo como una
          lista lo parecería.
        </p>
      </section>
      <section v-else-if="area.comparten.length" class="bloque">
        <h3>Cobran de los mismos organismos</h3>
        <p class="nota">
          Cobran de los mismos organismos que esta entidad. Es una coincidencia
          de pagador, no una relación entre ellas.
        </p>
        <!--
          La frase de «sobre todo por X, que reparte entre N» se ha ido: ahora
          cada grupo lleva su pagador en la cabecera, y aquella frase nombraba
          además al pagador más amplio, que es precisamente el que ya no forma
          grupo. Decía el nombre de un organismo que no aparecía debajo.
        -->
        <!--
          Agrupadas POR EL PAGADOR que comparten, no en una lista corrida.

          «PSOE · 16,4 M €» debajo de un título sobre pagadores comunes se lee
          como un vínculo. Bajo un encabezado que dice «vía Departament de
          Justícia i Qualitat Democràtica, que reparte entre 6» se lee como lo
          que es. Repetir esa coletilla en cada fila decía lo mismo y ocupaba
          cinco renglones por entidad.
        -->
        <div v-for="g in gruposComparten" :key="g.id" class="grupo-via">
          <p class="via-cabecera">
            Vía
            <a href="#" class="enlace" @click.prevent="emit('seleccionar', g.id)">{{ g.caption }}</a>,
            que reparte entre {{ g.alcance }}
          </p>
          <ul class="lista compacta">
            <li v-for="c in g.entidades" :key="c.id">
              <button @click="emit('seleccionar', c.id)">
                <span class="punto pequeno" :style="{ background: color(c.schema) }" />
                {{ c.caption }}
              </button>
              <span class="importe">{{ dineroCorto(c.total) }}</span>
            </li>
          </ul>
        </div>
      </section>

      <!--
        Las listas completas van al final y plegadas, y no por ahorrar sitio.
        Estaban arriba y repetían fila por fila lo que el diagrama de la
        izquierda ya estaba dibujando: las mismas doce contrapartes con las
        mismas cifras, dos veces en la misma pantalla. Lo que el diagrama NO
        puede enseñar —el capital extranjero, los expedientes sancionadores,
        quién orbita a los mismos pagadores— quedaba debajo de esa repetición,
        fuera de la pantalla, y no lo veía nadie.
        Aquí abajo la lista sigue estando entera, con lo suyo propio: cuántas
        operaciones, qué expedientes, qué se infirió y qué importe no se pudo
        publicar.
      -->
      <!-- De quién recibe ---------------------------------------------- -->
      <details v-if="area.recibeDe.length" class="bloque lista-larga" :open="abiertas">
        <summary>
          De quién recibe, uno a uno
          <span class="cuenta">{{ area.recibeDe.length }}</span>
        </summary>
        <ul class="lista barras">
          <li v-for="c in area.recibeDe" :key="c.id">
            <button class="fila" @click="emit('seleccionar', c.id)">
              <span class="punto pequeno" :style="{ background: color(c.schema) }" />
              <span class="nombre">{{ c.caption }}</span>
              <span class="importe">{{ dineroCorto(c.total) }}</span>
            </button>
            <span class="barra"><i :style="{ width: pct(c.total, tope(area.recibeDe)), background: color(c.schema) }" /></span>
            <span class="meta">
              {{ c.n }} {{ c.n === 1 ? 'operación' : 'operaciones' }}
              <template v-if="c.expedientes?.length">
                ·
                <button class="enlace-expedientes" @click="alternarExpedientes(c.id)">
                  {{ c.expedientes.length }}
                  {{ c.expedientes.length === 1 ? 'expediente' : 'expedientes' }}
                </button>
              </template>
              <span v-if="c.inferido" class="inferido">· inferido ({{ (c.confianza * 100).toFixed(0) }} %)</span>
              <span v-if="c.extranjera" class="extranjera">· no residente</span>
              <!--
                Un hueco sin explicar se lee como un cero. Aquí se dice que la
                cifra existe y que no se publica, y por qué.
              -->
              <span
                v-if="c.sinCifra"
                class="sin-cifra"
                :title="c.motivosSinCifra.join(' · ')"
              >
                · {{ c.sinCifra }}
                {{ c.sinCifra === 1 ? 'operación sin cifra publicada' : 'operaciones sin cifra publicada' }}
                <template v-if="c.motivosSinCifra.length">(importe no verosímil)</template>
              </span>
            </span>
            <!--
              Los expedientes, desplegables y con enlace a la ficha pública de
              la plataforma. Es el paso que faltaba para que «cada cifra lleva
              el documento del que salió» sirva de algo: la procedencia que se
              guarda es el ATOM de sindicación del que se leyó, que reproduce
              la ingesta pero no se puede leer.
            -->
            <ul v-if="expedientesAbiertos === c.id" class="expedientes-de">
              <li v-for="e in expedientesDe(c)" :key="e.id">
                <a v-if="e.url" :href="e.url" target="_blank" rel="noopener noreferrer">{{ e.nombre }}</a>
                <span v-else :title="'Este expediente no trae dirección pública'">{{ e.nombre }}</span>
              </li>
            </ul>
          </li>
        </ul>
      </details>

      <!-- A quién paga -------------------------------------------------- -->
      <details v-if="area.pagaA.length" class="bloque lista-larga" :open="abiertas">
        <summary>
          A quién paga, uno a uno
          <span class="cuenta">{{ area.pagaA.length }}</span>
        </summary>
        <ul class="lista barras">
          <li v-for="c in area.pagaA" :key="c.id">
            <button class="fila" @click="emit('seleccionar', c.id)">
              <span class="punto pequeno" :style="{ background: color(c.schema) }" />
              <span class="nombre">{{ c.caption }}</span>
              <span class="importe">{{ dineroCorto(c.total) }}</span>
            </button>
            <span class="barra"><i :style="{ width: pct(c.total, tope(area.pagaA)), background: color(c.schema) }" /></span>
            <span class="meta">
              {{ c.n }} {{ c.n === 1 ? 'operación' : 'operaciones' }}
              <template v-if="c.expedientes?.length">
                ·
                <button class="enlace-expedientes" @click="alternarExpedientes(c.id)">
                  {{ c.expedientes.length }}
                  {{ c.expedientes.length === 1 ? 'expediente' : 'expedientes' }}
                </button>
              </template>
              <span v-if="c.inferido" class="inferido">· inferido ({{ (c.confianza * 100).toFixed(0) }} %)</span>
              <span v-if="c.extranjera" class="extranjera">· no residente</span>
              <!--
                Un hueco sin explicar se lee como un cero. Aquí se dice que la
                cifra existe y que no se publica, y por qué.
              -->
              <span
                v-if="c.sinCifra"
                class="sin-cifra"
                :title="c.motivosSinCifra.join(' · ')"
              >
                · {{ c.sinCifra }}
                {{ c.sinCifra === 1 ? 'operación sin cifra publicada' : 'operaciones sin cifra publicada' }}
                <template v-if="c.motivosSinCifra.length">(importe no verosímil)</template>
              </span>
            </span>
            <!--
              Los expedientes, desplegables y con enlace a la ficha pública de
              la plataforma. Es el paso que faltaba para que «cada cifra lleva
              el documento del que salió» sirva de algo: la procedencia que se
              guarda es el ATOM de sindicación del que se leyó, que reproduce
              la ingesta pero no se puede leer.
            -->
            <ul v-if="expedientesAbiertos === c.id" class="expedientes-de">
              <li v-for="e in expedientesDe(c)" :key="e.id">
                <a v-if="e.url" :href="e.url" target="_blank" rel="noopener noreferrer">{{ e.nombre }}</a>
                <span v-else :title="'Este expediente no trae dirección pública'">{{ e.nombre }}</span>
              </li>
            </ul>
          </li>
        </ul>
      </details>

      <p v-if="sinDatos" class="matiz hueco">
        De esta entidad no consta ningún movimiento de dinero en la instantánea
        publicada. No significa que no lo haya: significa que las fuentes
        ingeridas no lo recogen.
      </p>
    </template>
  </aside>
</template>

<style scoped>
/*
  La ficha es una columna de artículo: antetítulo con el tipo, el nombre en
  la serif como un titular, una entradilla que lo resume, dos cifras y el
  sello de dónde salen. Debajo, cada bloque bajo su filete, sin cajas: se
  separa con reglas, como en papel (docs/diseno.md §1).
*/
.panel {
  overflow-y: auto; padding: var(--e4) var(--e5) var(--e7);
  border-left: 1px solid var(--filete-suave); background: var(--papel);
}
.vacio { color: var(--tinta-3); font-size: var(--t-m); margin-top: var(--e4); }

.acciones { display: flex; flex-wrap: wrap; gap: var(--e2); margin-bottom: var(--e5); }
.acciones .boton { font-size: var(--t-xs); padding: 0.3rem 0.6rem; }

.tipo { display: flex; align-items: center; gap: 0.45em; margin-bottom: var(--e2); }
.administracion {
  margin: calc(-1 * var(--e1)) 0 var(--e2); font-size: var(--t-s); color: var(--tinta-2);
}
h2 {
  font-size: clamp(1.4rem, 1.2rem + 0.6vw, 1.75rem); line-height: 1.12;
  margin: 0 0 var(--e2); overflow-wrap: anywhere;
}
.nif {
  font-family: var(--mono); font-size: var(--t-xs); color: var(--tinta-3);
  letter-spacing: 0.02em; margin: 0;
}
.resumen {
  font-family: var(--serif); font-size: var(--t-l); color: var(--tinta-2);
  line-height: 1.45; margin: var(--e3) 0 var(--e4);
}

/*
  Las dos cifras, entre filetes y sin recuadro: lo que recibe y lo que paga.
  Antes eran dos cajas con un filo verde y otro naranja —los colores de
  «entra» y «sale», que en el resto de la web no significaban eso—.
*/
.cifras {
  display: grid; grid-template-columns: 1fr 1fr;
  border-top: 1px solid var(--filete); border-bottom: 1px solid var(--filete-suave);
}
.cifra { display: flex; flex-direction: column; gap: 0.1rem; padding: var(--e3) var(--e3) var(--e3) 0; }
.cifra + .cifra { border-left: 1px solid var(--filete-suave); padding-left: var(--e3); }
.cifra .valor {
  font-family: var(--serif); font-size: var(--t-h2); font-weight: 600; color: var(--tinta);
  line-height: 1.1; white-space: nowrap;
}
.cifra .que { font-size: var(--t-xs); color: var(--tinta-3); line-height: 1.35; }
.cifra.nada .valor { font-family: var(--sans); font-size: var(--t-m); color: var(--tinta-3); font-weight: 600; }

/* El sello de procedencia, pegado a las cifras: es de dónde salen. */
.bloque.procedencia { margin-top: var(--e3); padding-top: 0; border-top: none; }
.procedencia > details > summary {
  cursor: pointer; font-size: var(--t-xs); color: var(--tinta-2);
  display: flex; flex-wrap: wrap; align-items: center; gap: var(--e1) var(--e2); list-style: none;
}
.procedencia .docs { text-decoration: underline; text-decoration-color: var(--filete-medio); text-underline-offset: 0.18em; }
.procedencia > details > summary::-webkit-details-marker { display: none; }
.procedencia > details > summary::after { content: '↓'; color: var(--tinta-3); }
.procedencia > details[open] > summary::after { content: '↑'; }
.procedencia ul { list-style: none; margin: var(--e2) 0 0; padding: 0; }
.procedencia li {
  display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.35rem;
  font-size: var(--t-xs); padding: 0.35rem 0; border-top: 1px solid var(--filete-suave);
}
.procedencia a { word-break: break-word; }
.procedencia .cuando { color: var(--tinta-3); }
.procedencia code { font-family: var(--mono); font-size: 0.6875rem; color: var(--tinta-3); }
.procedencia .y-mas { color: var(--tinta-3); }
.procedencia blockquote {
  flex-basis: 100%; margin: 0.25rem 0 0; padding-left: var(--e2);
  border-left: 2px solid var(--filete-medio); color: var(--tinta-2);
  font-family: var(--serif); font-style: italic;
}

/* --- Bloques ------------------------------------------------------------- */

.bloque { margin-top: var(--e6); padding-top: var(--e3); border-top: 2px solid var(--filete); }
h3 {
  font-family: var(--serif); font-size: var(--t-h3); font-weight: 600;
  color: var(--tinta); margin: 0 0 var(--e3); display: flex; align-items: baseline; gap: var(--e2);
}
.cuenta { font-family: var(--mono); font-size: var(--t-xs); font-weight: 400; color: var(--tinta-3); }

.matiz { font-size: var(--t-xs); color: var(--tinta-3); line-height: 1.5; margin: var(--e2) 0 0; }
.panel .nota { font-size: var(--t-s); margin-top: var(--e3); }
.hueco { margin-top: var(--e5); }

/*
  Dentro de una frase, un enlace de verdad y no un `button`: un botón es una
  caja aunque se le ponga `display: inline`, así que un nombre largo ocupaba
  el renglón entero y el punto de detrás caía solo al principio del
  siguiente. Tinta subrayada, como todo enlace.
*/
.enlace,
.enlace-expedientes {
  display: inline; background: none; border: none; padding: 0; font: inherit;
  color: var(--tinta); cursor: pointer; text-align: left;
  text-decoration: underline; text-decoration-color: var(--filete-medio);
  text-underline-offset: 0.18em;
}
.enlace:hover, .enlace-expedientes:hover { text-decoration-color: currentColor; }

.reparto { list-style: none; margin: 0 0 var(--e3); padding: 0; }
.reparto li + li { margin-top: var(--e4); }
.frase { margin: 0 0 var(--e2); font-size: var(--t-m); color: var(--tinta-2); line-height: 1.5; }
.frase b { color: var(--tinta); font-weight: 700; }
/* Barra de una sola parte: lo del primero sobre el total. */
.barra-reparto {
  display: block; height: 4px; background: var(--papel-3); border-radius: 1px; overflow: hidden;
}
.barra-reparto i { display: block; height: 100%; background: var(--tinta-2); }

.grupo-via + .grupo-via { margin-top: var(--e4); }
.via-cabecera { margin: 0 0 var(--e1); font-size: var(--t-xs); color: var(--tinta-3); line-height: 1.45; }

.expedientes-de {
  list-style: none; margin: 0.35rem 0 0; padding: 0 0 0 var(--e3);
  border-left: 2px solid var(--filete-medio);
}
.expedientes-de li { font-family: var(--mono); font-size: 0.6875rem; line-height: 1.45; margin-bottom: 0.25rem; }

/* Capital extranjero: sin caja morada. Lo que es un dato va como dato. */
.extranjero .grande {
  font-family: var(--serif); font-size: var(--t-h2); font-weight: 600; color: var(--tinta);
  margin: 0 0 var(--e2); line-height: 1.1;
}
.extranjero .pct { font-family: var(--sans); font-size: var(--t-xs); font-weight: 400; color: var(--tinta-3); margin-left: var(--e2); }
.indicios { margin-top: var(--e4); padding-top: var(--e3); border-top: 1px dashed var(--filete-medio); }
.indicios h4 {
  font-size: var(--t-xs); text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--tinta-3); margin: 0 0 var(--e1); font-weight: 650;
}

.lista { list-style: none; margin: 0; padding: 0; }
.lista button {
  background: none; border: none; color: var(--tinta); font: inherit; cursor: pointer;
  padding: 0; text-align: left;
}
.lista button:hover { text-decoration: underline; text-decoration-color: var(--filete-medio); text-underline-offset: 0.18em; }

.compacta li {
  display: flex; align-items: baseline; gap: var(--e3); justify-content: space-between;
  padding: 0.4rem 0; border-bottom: 1px solid var(--filete-suave); font-size: var(--t-s);
}
.compacta .nombre { flex: 1; }
.importe {
  font-variant-numeric: tabular-nums; font-size: var(--t-s); font-weight: 650;
  white-space: nowrap; color: var(--tinta);
}
.punto.pequeno {
  display: inline-block; width: 0.5em; height: 0.5em; border-radius: 50%;
  margin-right: 0.3em; vertical-align: 0.1em;
}

/* Sanciones: lacre, y siempre con su palabra al lado. */
.sanciones { border-top-color: var(--sancion); }
.sanciones h3 { color: var(--sancion); }
.sanciones .importe { color: var(--sancion); }
.sanciones li { flex-wrap: wrap; }
.sanciones .meta { flex-basis: 100%; font-family: var(--mono); }

/* --- Listas completas ---------------------------------------------------- */

.lista-larga > summary {
  cursor: pointer; font-family: var(--serif); font-size: var(--t-h3); font-weight: 600;
  color: var(--tinta); display: flex; align-items: baseline; gap: var(--e2);
}
.lista-larga > summary::marker { color: var(--tinta-3); }
.lista-larga[open] > summary { margin-bottom: var(--e2); }

.barras li { padding: 0.55rem 0; border-bottom: 1px solid var(--filete-suave); }
.fila { display: flex; align-items: baseline; gap: var(--e2); width: 100%; font-size: var(--t-s); }
.fila .nombre { flex: 1; line-height: 1.35; }
.barra {
  display: block; height: 3px; background: var(--papel-3); border-radius: 1px;
  margin: 0.35rem 0 0.25rem; overflow: hidden;
}
.barra i { display: block; height: 100%; }
.meta { font-size: var(--t-xs); color: var(--tinta-3); }
.meta .inferido, .meta .sin-cifra { color: var(--aviso); }
.meta .extranjera { color: var(--tinta-2); }
</style>
