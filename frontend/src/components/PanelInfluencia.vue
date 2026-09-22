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
import { COLOR_POR_DEFECTO, COLOR_POR_ESQUEMA, etiquetaEsquema } from '../esquemas.js'
import { enumerar, fechaCorta, nombreDocumento, nombreFuente } from '../procedencia.js'

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

const fuentesDeLaFicha = computed(() =>
  enumerar(procedencia.value.map((d) => nombreFuente(props.fuentes, d.source_id))),
)

/*
  Un organismo grande sale de decenas de documentos —el Servicio Andaluz de
  Salud, de 29— y todos del mismo feed y del mismo día. Listarlos enteros es
  una pared de enlaces idénticos que además tapa el resto del panel.
  Se enseñan unos pocos y se dice cuántos quedan: lo que hace falta comprobar
  es que el documento existe y se puede abrir, no abrirlos los 29.
*/
/**
 * «Sobre todo por X, que reparte entre N entidades.»
 *
 * Se arma en JavaScript y no en la plantilla. Con `<template v-for>` y
 * `<button>` por medio, Vue colapsaba los espacios donde no tocaba —«Sobre
 * todo porD.G. DE POLÍTICA INTERIOR»— y la coma se iba sola al renglón
 * siguiente. El nombre pierde el clic, y no importa: el pagador ya está en la
 * lista de «de quién recibe», que es donde se pulsa.
 */
const fraseDelPagadorComun = computed(() => {
  const via = props.area?.compartenPor ?? []
  if (!via.length) return ''
  const trozos = via.map(
    (v) => `${v.caption}, que reparte entre ${v.alcance} ${v.alcance === 1 ? 'entidad' : 'entidades'}`,
  )
  return `Sobre todo por ${trozos.join('; y por ')}.`
})

const CUANTOS_DOCUMENTOS = 5
const documentosVisibles = computed(() => procedencia.value.slice(0, CUANTOS_DOCUMENTOS))
const documentosDeMas = computed(() =>
  Math.max(0, procedencia.value.length - CUANTOS_DOCUMENTOS),
)



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
        <button class="volver" @click="emit('volver')">← Volver a la portada</button>
        <!--
          El botón existe para que se sepa que el enlace significa algo. Ahora
          cada ficha tiene su dirección, pero nadie mira la barra del
          navegador: sin un botón que lo diga, la función está y no la usa
          nadie.
        -->
        <button class="volver copiar" @click="copiarEnlace">
          {{ copiado ? '✓ Copiado' : 'Copiar enlace' }}
        </button>
      </div>
      <header>
        <span class="punto" :style="{ background: color(fueraDelMapa.schema) }" />
        <span class="tipo">{{ etiquetaEsquema(fueraDelMapa.schema) }}</span>
      </header>
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
        <button class="volver" @click="emit('volver')">← Volver a la portada</button>
        <!--
          El botón existe para que se sepa que el enlace significa algo. Ahora
          cada ficha tiene su dirección, pero nadie mira la barra del
          navegador: sin un botón que lo diga, la función está y no la usa
          nadie.
        -->
        <button class="volver copiar" @click="copiarEnlace">
          {{ copiado ? '✓ Copiado' : 'Copiar enlace' }}
        </button>
      </div>

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
        La procedencia, en la ficha y no a dos clics.
        «Sin procedencia no se persiste» es la primera invariante del proyecto
        y la promesa que la portada hace en su primera frase, pero para ver el
        documento había que cambiar de vista. Una promesa que hay que ir a
        buscar a otra pantalla es media promesa.
        Va plegada y en una línea: quien sólo mira las cifras no la nota; quien
        duda de una tiene el documento ahí, con su huella y la fecha en que se
        descargó.
      -->
      <section v-if="procedencia.length" class="bloque procedencia">
        <details>
          <summary>
            <span class="sello">✓</span>
            {{ procedencia.length }}
            {{ procedencia.length === 1 ? 'documento' : 'documentos' }}
            {{ procedencia.length === 1 ? 'guardado' : 'guardados' }}
            de {{ fuentesDeLaFicha }}
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
          <p class="matiz">
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
          <p class="matiz">
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
          {{ pagaPublicidad ? 'Publicidad y medios que paga' : 'Publicidad institucional que cobra' }}
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
        <p class="matiz">
          Dice de qué iba el contrato, no qué es quien lo cobra: puede ser un
          medio, la agencia que compra los espacios o la productora.
        </p>
      </section>

      <!-- Ámbito de interés --------------------------------------------- -->
      <section v-if="area.comparten.length" class="bloque">
        <h3>Orbitan a sus mismos pagadores</h3>
        <p class="matiz">
          Cobran de los mismos organismos que esta entidad. Es una coincidencia
          de pagador, no una relación entre ellas.
        </p>
        <!--
          Y CUÁL es el pagador compartido, con su alcance. Sin esta frase el
          bloque insinúa: en la ficha del PSOE salían el PP, VOX, Podemos y
          once partidos más, cada uno con su cifra, bajo el título «orbitan a
          sus mismos pagadores». Es verdad y no dice nada — lo que comparten es
          quien paga la subvención electoral a todos los partidos. Con «reparte
          entre 93 entidades» al lado, se ve solo.
        -->
        <p v-if="fraseDelPagadorComun" class="matiz via">{{ fraseDelPagadorComun }}</p>
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
            <span class="barra"><i class="entra" :style="{ width: pct(c.total, tope(area.recibeDe)) }" /></span>
            <span class="meta">
              {{ c.n }} {{ c.n === 1 ? 'operación' : 'operaciones' }}
              <template v-if="c.expedientes?.length">
                · {{ c.expedientes.length }}
                {{ c.expedientes.length === 1 ? 'expediente' : 'expedientes' }}
              </template>
              <span v-if="c.inferido" class="inferido">· inferido ({{ (c.confianza * 100).toFixed(0) }} %)</span>
              <span v-if="c.extranjera" class="extranjera">· extranjera</span>
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
.acciones { display: flex; flex-wrap: wrap; gap: var(--e2); margin-bottom: var(--e2); }
.copiar { color: var(--tinta-3); }
.copiar:hover { color: var(--tinta); }

.procedencia > details > summary {
  cursor: pointer; font-size: 0.78rem; color: var(--texto-tenue);
  list-style-position: outside;
}
.procedencia .sello { color: #4bb47f; font-weight: 700; }
.procedencia ul { list-style: none; margin: 0.5rem 0 0; padding: 0; }
.procedencia li {
  display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.35rem;
  font-size: 0.72rem; padding: 0.3rem 0; border-top: 1px solid var(--borde-suave);
}
.procedencia a { color: var(--acento); word-break: break-word; }
.procedencia .cuando { color: var(--texto-tenue); }
.procedencia code {
  font-size: 0.66rem; color: var(--texto-tenue);
  background: var(--fondo-boton); padding: 0.05rem 0.25rem; border-radius: 3px;
}
.procedencia .y-mas { color: var(--texto-tenue); }
.procedencia blockquote {
  flex-basis: 100%; margin: 0.25rem 0 0; padding-left: 0.5rem;
  border-left: 2px solid var(--borde); color: var(--texto-tenue); font-style: italic;
}

.lista-larga > summary {
  cursor: pointer; font-size: 0.82rem; font-weight: 600; color: var(--texto);
  display: flex; align-items: baseline; gap: 0.4rem;
}
.lista-larga > summary::marker { color: var(--texto-tenue); }
.lista-larga[open] > summary { margin-bottom: 0.5rem; }

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
h2 { font-size: var(--t-xl); margin: var(--e2) 0 0.15rem; line-height: 1.25; }
.nif { font-size: var(--t-xs); color: var(--tinta-3); font-variant-numeric: tabular-nums; margin: 0; }
.resumen { font-size: var(--t-s); color: var(--tinta-2); line-height: 1.5; margin: var(--e3) 0 var(--e4); }

/*
  Dos fichas de cifra, con el contrato de siempre: rótulo, valor y qué es.
  El valor va en TINTA y el color lo lleva el filo de la izquierda. Antes el
  valor iba pintado de verde o de naranja claro: compite con el dato que el
  diagrama está dibujando al lado y, sobre fondo oscuro, se lee peor que el
  blanco.
*/
.cifras { display: grid; grid-template-columns: 1fr 1fr; gap: var(--e2); }
.cifra {
  background: var(--superficie-2); border: 1px solid var(--linea);
  border-radius: var(--radio-s); padding: var(--e3); display: flex;
  flex-direction: column; gap: 0.15rem;
}
.cifra .valor {
  font-size: var(--t-l); font-weight: 650; color: var(--tinta); line-height: 1.15;
  white-space: nowrap;
}
.cifra .que { font-size: var(--t-xs); color: var(--tinta-3); line-height: 1.35; }
.cifra.entra { border-left: 3px solid var(--entra); }
.cifra.sale { border-left: 3px solid var(--sale); }
.cifra.nada { border-left-color: var(--linea-fuerte); }
.cifra.nada .valor { color: var(--tinta-3); font-size: var(--t-m); font-weight: 600; }

.bloque { margin-top: var(--e5); }
h3 {
  font-size: var(--t-xs); text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--texto-tenue); margin: 0 0 0.5rem;
}
.cuenta { font-weight: 400; opacity: 0.7; }

.bloque.extranjero {
  background: #241d33; border: 1px solid #3c3155; border-radius: 8px; padding: 0.7rem 0.75rem;
}
.bloque.extranjero .grande { font-size: 1.05rem; font-weight: 700; color: #cbb0f0; margin: 0 0 0.5rem; }
.bloque.extranjero .pct { font-size: 0.72rem; font-weight: 400; color: var(--texto-tenue); margin-left: 0.4rem; }
.indicios { margin-top: 0.8rem; padding-top: 0.6rem; border-top: 1px dashed #3c3155; }
.indicios h4 {
  font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--texto-tenue); margin: 0 0 0.35rem; font-weight: 600;
}

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
.meta .sin-cifra { color: var(--aviso); }

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
