<script setup>
/*
  La radiografía del poder: la entrada de la red de poder cuando no se ha
  pedido ningún nodo. Primero las áreas y lo que las une; después los núcleos,
  los medios y sus dueños, y los puentes. Todo nombre se pulsa y lleva a la
  red, centrada en él.
*/
import { computed, ref } from 'vue'
import { AREAS, nombreCorto, nombrePropio, radiografiaCompleta } from '../radiografia.js'
import { nombreDeFuente } from '../poder.js'

const props = defineProps({
  cargos: { type: Object, default: null },
  grafo: { type: Object, default: null },
  cargando: { type: Boolean, default: false },
})
const emit = defineEmits(['centrar'])

const r = computed(() => (props.cargos ? radiografiaCompleta(props.cargos, props.grafo) : null))
const corto = (clave) => nombrePropio(nombreCorto(props.cargos?.cotizadas?.[clave]))

const numero = (n) => Number(n ?? 0).toLocaleString('es-ES')
const porcentaje = (p) => `${Number(p).toLocaleString('es-ES', { maximumFractionDigits: 1 })} %`
const millones = (x) =>
  x >= 1e9
    ? `${(x / 1e9).toLocaleString('es-ES', { maximumFractionDigits: 1 })} mil M€`
    : `${(x / 1e6).toLocaleString('es-ES', { maximumFractionDigits: 1 })} M€`
const nombre = (texto) => nombrePropio(texto)
const ir = (clave) => clave && emit('centrar', clave)

/* --- La entradilla, escrita con los datos ------------------------------- */

const entradilla = computed(() => {
  const x = r.value
  if (!x?.nucleos.length) return ''
  const estado = x.nucleos.find((n) => n.estado)
  const otros = x.nucleos.filter((n) => !n.estado).slice(0, 3)
  const partes = []
  if (estado) partes.push(`el Estado es accionista de referencia de ${estado.cotizadas.length} cotizadas`)
  for (const n of otros) partes.push(`${nombre(n.titulares[0].nombre)}, de ${n.cotizadas.length}`)
  const disputadas = [...(x.enNucleo?.entries() ?? [])].filter(([, v]) => v.length > 1).length
  return (
    `De las ${x.cifras.cotizadas} cotizadas que se siguen, ${partes.join('; ')}. ` +
    (disputadas ? `En ${disputadas} se cruzan dos núcleos o más. ` : '') +
    `Debajo, quién nombra a quién, adónde va el dinero público y qué personas unen unos núcleos con otros.`
  )
})

/* --- El diagrama de áreas ------------------------------------------------ */

const ANCHO = 210
const ALTO = 74
const POS = {
  parlamento: [20, 30],
  justicia: [375, 30],
  medios: [730, 30],
  gobierno: [20, 243],
  estado: [375, 243],
  empresas: [730, 243],
  partidos: [20, 456],
  administracion: [375, 456],
  accionistas: [730, 456],
}
// Cuánto se curva cada flujo, para que no atraviese otra caja.
const CURVA = { 'gobierno>empresas': 0.14, 'accionistas>medios': -0.3, 'estado>medios': -0.12 }
const centro = (a) => [POS[a][0] + ANCHO / 2, POS[a][1] + ALTO / 2]

const seleccionado = ref('')
const flujos = computed(() => {
  const lista = r.value?.flujos ?? []
  return lista.map((f) => {
    const clave = `${f.de}>${f.a}`
    const grosor = 1.5 + 2.6 * Math.log10(f.n + 1)
    let d
    let pos
    if (f.de === f.a) {
      // Un lazo sobre la propia caja.
      const [x, y] = POS[f.de]
      const x1 = x + ANCHO * 0.3
      const x2 = x + ANCHO * 0.7
      d = `M ${x1} ${y} C ${x1 - 10} ${y - 44}, ${x2 + 10} ${y - 44}, ${x2} ${y}`
      pos = [x + ANCHO / 2, y - 36]
      if (f.de === 'empresas') {
        // A la derecha: abajo llega la flecha de los accionistas.
        const xd = x + ANCHO
        const y1 = y + ALTO * 0.25
        const y2 = y + ALTO * 0.75
        d = `M ${xd} ${y1} C ${xd + 48} ${y1 - 12}, ${xd + 48} ${y2 + 12}, ${xd} ${y2}`
        pos = [xd + 38, y + ALTO / 2]
      }
    } else {
      const [x1, y1] = centro(f.de)
      const [x2, y2] = centro(f.a)
      const dx = x2 - x1
      const dy = y2 - y1
      const largo = Math.hypot(dx, dy)
      const k = CURVA[clave] ?? 0
      const cx = (x1 + x2) / 2 + (-dy / largo) * k * largo
      const cy = (y1 + y2) / 2 + (dx / largo) * k * largo
      // La curva, muestreada, entre donde sale de su caja y donde llega a la
      // otra: así la punta queda a la vista.
      const punto = (t) => [(1 - t) ** 2 * x1 + 2 * (1 - t) * t * cx + t ** 2 * x2, (1 - t) ** 2 * y1 + 2 * (1 - t) * t * cy + t ** 2 * y2]
      const dentro = ([x, y], a, m) => x > POS[a][0] - m && x < POS[a][0] + ANCHO + m && y > POS[a][1] - m && y < POS[a][1] + ALTO + m
      const puntos = []
      for (let i = 0; i <= 60; i++) {
        const q = punto(i / 60)
        if (!dentro(q, f.de, 2) && !dentro(q, f.a, 7)) puntos.push(q)
      }
      d = puntos.map(([x, y], i) => `${i ? 'L' : 'M'} ${x.toFixed(1)} ${y.toFixed(1)}`).join(' ')
      pos = [0.25 * x1 + 0.5 * cx + 0.25 * x2, 0.25 * y1 + 0.5 * cy + 0.25 * y2]
    }
    return { ...f, clave, d, grosor, pos, clase: AREAS[f.de]?.clase ?? 'neutro' }
  })
})
const flujoActual = computed(() => flujos.value.find((f) => f.clave === seleccionado.value) ?? null)
function elegir(clave) {
  seleccionado.value = seleccionado.value === clave ? '' : clave
}
const frase = (f) => `${f.frase}: ${numero(f.n)} ${f.unidad[f.n === 1 ? 0 : 1]}${f.importe ? `, ${millones(f.importe)}` : ''}`
const areasPresentes = computed(() => {
  const s = new Set(flujos.value.flatMap((f) => [f.de, f.a]))
  return Object.keys(POS).filter((a) => s.has(a))
})
const claveDeHecho = (h) => h.persona ?? h.cotizada ?? h.titular ?? h.entidad ?? ''

/* --- Núcleos, medios, referencias y puentes ------------------------------ */

const otrosNucleos = (n, cotizada) =>
  (r.value?.enNucleo?.get(cotizada) ?? [])
    .filter((id) => id !== n.id)
    .map((id) => r.value.nucleos.find((x) => x.id === id))
    .filter(Boolean)
const presidenciasDelEstado = computed(() =>
  [...(r.value?.estado?.entries() ?? [])]
    .filter(([, e]) => e.cargos.length)
    .map(([clave, e]) => ({ clave, ultimo: e.cargos[0], n: e.cargos.length })),
)
const medios = computed(() =>
  Object.values(props.cargos?.cotizadas ?? {})
    .filter((c) => c.medio)
    .map((c) => ({ ...c, accionistas: [...(c.accionistas ?? [])].sort((a, b) => b.porcentaje - a.porcentaje) })),
)
const GRUPOS_DE_PUENTES = {
  consejos: 'En más de un consejo de administración',
  accionista: 'Personas con participación significativa en más de una cotizada',
  puerta: 'De un alto cargo a una cotizada, con autorización de la OCI',
  estado: 'Quienes presiden el Estado accionista, nombrados por el Gobierno',
}
const puentesPorTipo = computed(() => {
  const g = {}
  for (const p of r.value?.puentes ?? []) (g[p.tipo] ??= []).push(p)
  return g
})
const anio = (f) => (f ? f.slice(0, 4) : '')
const recortar = (t, n) => (t.length > n ? `${t.slice(0, n - 1)}…` : t)
</script>

<template>
  <div class="fondo">
  <article class="radiografia">
    <p v-if="!r" class="estado">{{ cargando ? 'Cargando la radiografía…' : 'Esta edición no trae los datos de la red de poder.' }}</p>
    <template v-else>
      <header class="cabeza">
        <p class="antetitulo">Radiografía</p>
        <h1 class="titular">Quién tiene el poder en España</h1>
        <p class="entradilla">{{ entradilla }}</p>
        <ul class="cifras" aria-label="Lo que cubre esta edición">
          <li><b>{{ numero(r.cifras.cotizadas) }}</b> cotizadas</li>
          <li><b>{{ numero(r.cifras.accionistas) }}</b> accionistas significativos</li>
          <li><b>{{ numero(r.cifras.consejeros) }}</b> consejeros</li>
          <li><b>{{ numero(r.cifras.altosCargos) }}</b> altos cargos del BOE</li>
          <li><b>{{ numero(r.cifras.justicia) }}</b> cargos de las altas instancias judiciales</li>
        </ul>
      </header>

      <!-- 1. Las áreas y lo que las une -->
      <section class="bloque" aria-labelledby="t-areas">
        <h2 id="t-areas" class="seccion">Cómo se enlazan los poderes</h2>
        <p class="nota">
          Cada flecha es un recuento de hechos publicados: nombramientos en el BOE, participaciones en la CNMV,
          autorizaciones de la Oficina de Conflictos de Intereses, contratos y subvenciones. Cuanto más gruesa, más
          hechos. Pulsa una para verlos.
        </p>
        <div class="diagrama">
          <svg viewBox="0 -56 1010 620" role="img" aria-labelledby="t-areas">
            <defs>
              <marker v-for="c in ['adm', 'emp', 'par']" :id="`punta-${c}`" :key="c" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" :class="`relleno-${c}`" />
              </marker>
            </defs>
            <g v-for="f in flujos" :key="f.clave" class="flujo" :class="[`k-${f.clase}`, { activo: f.clave === seleccionado, apagado: seleccionado && f.clave !== seleccionado }]" @click="elegir(f.clave)">
              <path :d="f.d" class="trazo-ancho" />
              <path :d="f.d" class="trazo" :stroke-width="f.grosor" :marker-end="`url(#punta-${f.clase})`" />
              <g :transform="`translate(${f.pos[0]}, ${f.pos[1]})`" class="cifra">
                <rect x="-22" y="-11" width="44" height="22" rx="11" />
                <text text-anchor="middle" dy="4">{{ numero(f.n) }}</text>
              </g>
              <title>{{ frase(f) }}</title>
            </g>
            <g v-for="a in areasPresentes" :key="a" class="area" :class="`k-${AREAS[a].clase}`" :transform="`translate(${POS[a][0]}, ${POS[a][1]})`">
              <rect :width="ANCHO" :height="ALTO" rx="4" />
              <text :x="ANCHO / 2" :y="r.rotulos[a] ? ALTO / 2 - 3 : ALTO / 2 + 6" text-anchor="middle">{{ AREAS[a].nombre }}</text>
              <text v-if="r.rotulos[a]" :x="ANCHO / 2" :y="ALTO / 2 + 18" text-anchor="middle" class="rotulo">{{ recortar(r.rotulos[a], 30) }}</text>
            </g>
          </svg>
        </div>
        <ol class="flujos">
          <li v-for="f in flujos" :key="f.clave">
            <button type="button" :class="[`k-${f.clase}`, { activo: f.clave === seleccionado }]" :aria-expanded="f.clave === seleccionado" @click="elegir(f.clave)">
              {{ frase(f) }}
            </button>
          </li>
        </ol>
        <div v-if="flujoActual" class="hechos" aria-live="polite">
          <h3>{{ frase(flujoActual) }}</h3>
          <ul>
            <li v-for="(h, i) in flujoActual.hechos.slice(0, 14)" :key="i">
              <button v-if="claveDeHecho(h)" type="button" class="enlace" @click="ir(claveDeHecho(h))">{{ h.texto }}</button>
              <span v-else>{{ h.texto }}</span>
              <span v-if="h.importe" class="dato">{{ millones(h.importe) }}</span>
              <span v-if="h.desde" class="dato">{{ anio(h.desde) }}</span>
              <a v-if="h.url" :href="h.url" target="_blank" rel="noopener" class="fuente">{{ nombreDeFuente(h.fuente) }}</a>
              <span v-else class="fuente">{{ nombreDeFuente(h.fuente) }}</span>
            </li>
            <li v-if="flujoActual.hechos.length > 14" class="mas">y {{ numero(flujoActual.hechos.length - 14) }} más</li>
          </ul>
        </div>
      </section>

      <!-- 2. Los núcleos -->
      <section class="bloque" aria-labelledby="t-nucleos">
        <h2 id="t-nucleos" class="seccion">Los núcleos del poder económico</h2>
        <p class="nota">
          El núcleo de un accionista son las cotizadas en las que tiene al menos un 5 % de los derechos de voto, si son
          dos o más, según la CNMV. Una misma cotizada puede estar en varios: ahí se disputa su control.
          <template v-if="r.omnipresentes.length">
            Se apartan las gestoras que están en casi todas —{{ r.omnipresentes.map((o) => `${nombre(o.nombre)}, en ${o.en.length}`).join('; ') }}—:
            una cartera repartida por todo el mercado no es un núcleo.
          </template>
        </p>
        <div class="nucleos">
          <section v-for="n in r.nucleos" :key="n.id" class="nucleo" :class="{ 'es-estado': n.estado }">
            <p class="antetitulo">{{ n.estado ? 'El Estado accionista' : n.titulares.some((t) => t.persona) ? 'Una fortuna personal' : 'Un grupo accionista' }}</p>
            <h3>
              <template v-if="n.estado">El Estado</template>
              <template v-else>
                <template v-for="(t, i) in n.titulares" :key="t.clave">
                  <span v-if="i" class="sep"> · </span>
                  <button type="button" class="enlace" @click="ir(t.clave)">{{ nombre(t.nombre) }}</button>
                </template>
              </template>
            </h3>
            <p v-if="n.estado" class="sub">
              <template v-for="(t, i) in n.titulares" :key="t.clave">
                <span v-if="i"> · </span>
                <button type="button" class="enlace" @click="ir(t.clave)">{{ nombre(t.nombre) }}</button>
              </template>
            </p>
            <ul class="barras">
              <li v-for="p in n.participaciones" :key="`${p.titular}|${p.cotizada}`">
                <button type="button" class="enlace cot" @click="ir(p.cotizada)">{{ corto(p.cotizada) }}</button>
                <span class="barra" :title="`${nombre(p.nombre)}: ${porcentaje(p.porcentaje)}`"><span :style="{ width: `${Math.min(100, p.porcentaje)}%` }" /></span>
                <span class="pct">{{ porcentaje(p.porcentaje) }}</span>
                <span v-if="n.estado" class="quien">{{ nombre(p.nombre) }}</span>
                <span v-for="o in otrosNucleos(n, p.cotizada)" :key="o.id" class="cruce" :title="`También en el núcleo de ${o.nombre}`">+ {{ o.estado ? 'Estado' : nombre(o.titulares[0].nombre) }}</span>
              </li>
            </ul>
            <p v-if="n.estado && presidenciasDelEstado.length" class="cadena">
              <b>Quién lo preside:</b>{{ ' ' }}
              <template v-for="(pr, i) in presidenciasDelEstado" :key="pr.clave">
                <span v-if="i">; </span>
                <button type="button" class="enlace" @click="ir(pr.ultimo.persona)">{{ pr.ultimo.nombre }}</button>
                ({{ pr.ultimo.cargo.replace(/^President[ae] del? /, '') }}, desde {{ anio(pr.ultimo.desde) }}{{ pr.ultimo.gobierno ? `, ${pr.ultimo.gobierno.nombre.replace(/^/, 'Gobierno de ')}` : '' }})
              </template>
              — nombramientos por Real Decreto del Consejo de Ministros.
            </p>
            <p v-if="n.consejeros?.length" class="puentes-nucleo">
              <b>Consejeros que comparte:</b>{{ ' ' }}
              <template v-for="(c, i) in n.consejeros" :key="c.clave">
                <span v-if="i">; </span>
                <button type="button" class="enlace" @click="ir(c.clave)">{{ nombre(c.nombre) }}</button>
                ({{ c.en.map((e) => nombre(e.nombre)).join(' y ') }})
              </template>
            </p>
          </section>
        </div>
      </section>

      <!-- 3. Los medios y sus dueños -->
      <section v-if="medios.length" class="bloque" aria-labelledby="t-medios">
        <h2 id="t-medios" class="seccion">Quién es dueño de los medios</h2>
        <p class="nota">Los grupos de comunicación cotizados —así los clasifica la CNMV— y sus accionistas significativos.</p>
        <div class="medios">
          <section v-for="m in medios" :key="m.clave" class="medio">
            <h3><button type="button" class="enlace" @click="ir(m.clave)">{{ nombre(m.nombre) }}</button></h3>
            <ul class="barras">
              <li v-for="a in m.accionistas" :key="a.clave">
                <button type="button" class="enlace cot" @click="ir(a.clave)">{{ nombre(a.nombre) }}</button>
                <span class="barra"><span :style="{ width: `${Math.min(100, a.porcentaje)}%` }" /></span>
                <span class="pct">{{ porcentaje(a.porcentaje) }}</span>
              </li>
            </ul>
          </section>
        </div>
      </section>

      <!-- 4. Cotizadas con un dueño de referencia -->
      <section v-if="r.referencias.length" class="bloque" aria-labelledby="t-referencias">
        <h2 id="t-referencias" class="seccion">Cotizadas con un dueño de referencia</h2>
        <p class="nota">Las que no están en ningún núcleo, con su mayor accionista significativo.</p>
        <table class="referencias">
          <tbody>
            <tr v-for="c in r.referencias" :key="c.clave">
              <th scope="row"><button type="button" class="enlace" @click="ir(c.clave)">{{ nombre(c.nombre) }}</button></th>
              <td>
                <button v-if="c.principal" type="button" class="enlace" @click="ir(c.principal.titular)">{{ nombre(c.principal.nombre) }}</button>
                <span v-else class="apagado">sin accionista significativo fuera de las gestoras</span>
              </td>
              <td class="pct">{{ c.principal ? porcentaje(c.principal.porcentaje) : '' }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- 5. Los puentes -->
      <section class="bloque" aria-labelledby="t-puentes">
        <h2 id="t-puentes" class="seccion">Los puentes</h2>
        <p class="nota">
          Quién está en más de un sitio. Cada persona sale sólo en el papel en que la publica su fuente; dos que se llaman
          igual en dos fuentes no se dan por la misma sin una segunda señal.
        </p>
        <div class="puentes">
          <section v-for="(titulo, tipo) in GRUPOS_DE_PUENTES" v-show="puentesPorTipo[tipo]?.length" :key="tipo" class="grupo-puentes">
            <h3>{{ titulo }}</h3>
            <ul>
              <li v-for="p in puentesPorTipo[tipo] ?? []" :key="`${tipo}|${p.clave}|${p.detalle[0]}`">
                <button type="button" class="enlace" @click="ir(p.clave)">{{ nombre(p.nombre) }}</button>
                <span class="detalle">{{ p.detalle.map(nombre).join(' · ') }}{{ p.gobierno ? ` · Gobierno de ${p.gobierno}` : '' }}</span>
              </li>
            </ul>
          </section>
        </div>
      </section>

      <footer class="pie">
        <button type="button" class="explorar" @click="ir(r.nucleos[0]?.titulares[0]?.clave)">Explorar la red completa →</button>
        <p class="nota">
          Fuentes: BOE (altos cargos y altas instancias judiciales), CNMV (accionistas significativos, consejos y sector),
          Oficina de Conflictos de Intereses (autorizaciones tras el cese), Congreso (declaraciones de actividades) y el mapa
          del dinero público. Lo que no publican, no está.
        </p>
      </footer>
    </template>
  </article>
  </div>
</template>

<style scoped>
.fondo { background: var(--papel); width: 100%; min-height: 100%; }
.radiografia { max-width: 72rem; margin: 0 auto; padding: var(--e6) var(--e5) var(--e8); color: var(--tinta); }
.estado { font-family: var(--sans); color: var(--tinta-3); }
.antetitulo { font-family: var(--sans); font-size: var(--t-xs); letter-spacing: 0.08em; text-transform: uppercase; color: var(--tinta-3); margin: 0 0 var(--e1); }
.titular { font-family: var(--serif); font-size: var(--t-titular); line-height: 1.05; margin: 0 0 var(--e4); font-weight: 600; }
.entradilla { font-family: var(--serif); font-size: var(--t-l); line-height: 1.5; max-width: var(--medida); color: var(--tinta-2); margin: 0 0 var(--e5); }
.cifras { list-style: none; display: flex; flex-wrap: wrap; gap: var(--e2) var(--e5); padding: var(--e3) 0; margin: 0; border-top: 2px solid var(--filete); border-bottom: 1px solid var(--filete-suave); font-family: var(--sans); font-size: var(--t-s); color: var(--tinta-2); }
.cifras b { font-family: var(--mono); font-weight: 500; color: var(--tinta); }
.bloque { margin-top: var(--e7); }
.seccion { font-family: var(--serif); font-size: var(--t-h1); margin: 0 0 var(--e2); padding-top: var(--e3); border-top: 2px solid var(--filete); }
.nota { font-family: var(--sans); font-size: var(--t-s); color: var(--tinta-3); max-width: var(--medida); line-height: 1.5; margin: 0 0 var(--e4); }

/* El diagrama */
.diagrama { background: var(--hoja); border: 1px solid var(--filete-suave); border-radius: var(--radio); padding: var(--e3); }
.diagrama svg { width: 100%; height: auto; display: block; font-family: var(--sans); }
.area rect { fill: var(--papel); stroke-width: 2; }
.area.k-adm rect { stroke: var(--adm); }
.area.k-emp rect { stroke: var(--emp); }
.area.k-par rect { stroke: var(--par); }
.area text { font-size: 17px; font-weight: 600; fill: var(--tinta); }
.area text.rotulo { font-size: 12.5px; font-weight: 400; fill: var(--tinta-3); }
.flujo { cursor: pointer; }
.flujo .trazo { fill: none; opacity: 0.75; transition: opacity 0.15s; }
.flujo .trazo-ancho { fill: none; stroke: transparent; stroke-width: 18; }
.flujo.k-adm .trazo { stroke: var(--adm); }
.flujo.k-emp .trazo { stroke: var(--emp); }
.flujo.k-par .trazo { stroke: var(--par); }
.relleno-adm { fill: var(--adm); }
.relleno-emp { fill: var(--emp); }
.relleno-par { fill: var(--par); }
.flujo.apagado .trazo { opacity: 0.15; }
.flujo.apagado .cifra { opacity: 0.3; }
.flujo.activo .trazo, .flujo:hover .trazo { opacity: 1; }
.cifra rect { fill: var(--hoja); stroke: var(--filete-medio); }
.cifra text { font-family: var(--mono); font-size: 13px; fill: var(--tinta); }
.flujos { list-style: none; padding: 0; margin: var(--e4) 0 0; columns: 2 22rem; column-gap: var(--e5); }
.flujos li { break-inside: avoid; margin-bottom: var(--e1); }
.flujos button { all: unset; cursor: pointer; font-family: var(--sans); font-size: var(--t-s); line-height: 1.45; border-left: 3px solid var(--neutro); padding-left: var(--e2); display: block; color: var(--tinta-2); }
.flujos button.k-adm { border-color: var(--adm); }
.flujos button.k-emp { border-color: var(--emp); }
.flujos button.k-par { border-color: var(--par); }
.flujos button.activo, .flujos button:hover, .flujos button:focus-visible { color: var(--tinta); background: var(--papel-2); }
.hechos { margin-top: var(--e4); background: var(--hoja); border: 1px solid var(--filete-suave); border-radius: var(--radio); padding: var(--e3) var(--e4); }
.hechos h3 { font-family: var(--serif); font-size: var(--t-h3); margin: 0 0 var(--e2); }
.hechos ul { list-style: none; margin: 0; padding: 0; font-family: var(--sans); font-size: var(--t-s); }
.hechos li { padding: var(--e1) 0; border-bottom: 1px solid var(--filete-suave); display: flex; flex-wrap: wrap; gap: var(--e2); align-items: baseline; }
.hechos .mas { color: var(--tinta-3); border: 0; }
.dato, .fuente { font-family: var(--mono); font-size: var(--t-xs); color: var(--tinta-3); }
a.fuente { color: var(--tinta-2); }

.enlace { all: unset; cursor: pointer; text-decoration: underline; text-decoration-color: var(--filete-medio); text-underline-offset: 2px; }
.enlace:hover, .enlace:focus-visible { text-decoration-color: var(--tinta); background: var(--papel-2); }

/* Núcleos */
.nucleos { display: grid; grid-template-columns: repeat(auto-fill, minmax(21rem, 1fr)); gap: var(--e4); }
.nucleo, .medio { border: 1px solid var(--filete-suave); border-top: 3px solid var(--emp); border-radius: var(--radio); padding: var(--e3) var(--e4); background: var(--hoja); }
.nucleo.es-estado { border-top-color: var(--adm); grid-column: 1 / -1; }
.nucleo h3, .medio h3 { font-family: var(--serif); font-size: var(--t-h3); margin: 0 0 var(--e2); line-height: 1.25; }
.nucleo .sub { font-family: var(--sans); font-size: var(--t-s); color: var(--tinta-2); margin: 0 0 var(--e2); }
.sep { color: var(--tinta-3); }
.barras { list-style: none; margin: 0; padding: 0; font-family: var(--sans); font-size: var(--t-s); }
.barras li { display: grid; grid-template-columns: minmax(8rem, 1.3fr) minmax(4rem, 1fr) 4.2rem; gap: var(--e1) var(--e2); align-items: center; padding: 3px 0; }
.es-estado .barras { columns: 2 22rem; column-gap: var(--e6); }
.es-estado .barras li { break-inside: avoid; }
.barras .cot { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.barra { height: 0.55rem; background: var(--papel-3); border-radius: 1px; position: relative; }
.barra span { position: absolute; inset: 0 auto 0 0; background: var(--emp); border-radius: 1px; }
.es-estado .barra span { background: var(--adm); }
.pct { font-family: var(--mono); font-size: var(--t-xs); text-align: right; }
.quien, .cruce { grid-column: 1 / -1; font-size: var(--t-xs); color: var(--tinta-3); margin-top: -2px; }
.cruce { color: var(--emp); }
.cadena, .puentes-nucleo { font-family: var(--sans); font-size: var(--t-s); line-height: 1.5; color: var(--tinta-2); margin: var(--e3) 0 0; }
.medios { display: grid; grid-template-columns: repeat(auto-fill, minmax(21rem, 1fr)); gap: var(--e4); }

/* Referencias y puentes */
.referencias { width: 100%; border-collapse: collapse; font-family: var(--sans); font-size: var(--t-s); }
.referencias th, .referencias td { text-align: left; padding: var(--e1) var(--e2) var(--e1) 0; border-bottom: 1px solid var(--filete-suave); font-weight: 400; }
.referencias th { width: 42%; }
.apagado { color: var(--tinta-3); }
.puentes { display: grid; grid-template-columns: repeat(auto-fill, minmax(22rem, 1fr)); gap: var(--e5); }
.grupo-puentes h3 { font-family: var(--sans); font-size: var(--t-s); font-weight: 600; margin: 0 0 var(--e2); text-transform: uppercase; letter-spacing: 0.05em; color: var(--tinta-2); }
.grupo-puentes ul { list-style: none; margin: 0; padding: 0; font-family: var(--sans); font-size: var(--t-s); }
.grupo-puentes li { padding: var(--e1) 0; border-bottom: 1px solid var(--filete-suave); }
.detalle { display: block; color: var(--tinta-3); font-size: var(--t-xs); }
.pie { margin-top: var(--e7); border-top: 2px solid var(--filete); padding-top: var(--e4); }
.explorar { all: unset; cursor: pointer; font-family: var(--sans); font-weight: 600; padding: var(--e2) var(--e4); border: 1px solid var(--tinta); border-radius: var(--radio); margin-bottom: var(--e3); display: inline-block; }
.explorar:hover, .explorar:focus-visible { background: var(--tinta); color: var(--papel); }

@media (max-width: 40rem) {
  .radiografia { padding: var(--e4) var(--e4) var(--e7); }
  .nucleos, .medios, .puentes { grid-template-columns: 1fr; }
  .barras li { grid-template-columns: minmax(7rem, 1.4fr) minmax(3rem, 1fr) 3.8rem; }
}
</style>
