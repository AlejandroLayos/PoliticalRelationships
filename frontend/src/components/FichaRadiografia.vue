<script setup>
/*
  La ficha de la radiografía: lo que se sabe de una cotizada o de un núcleo,
  en un panel que se abre al lado (abajo, en el móvil) sin salir del mapa.
  Cada dato con su fuente; cada nombre lleva a la red de relaciones.
*/
import { onBeforeUnmount, onMounted } from 'vue'

const props = defineProps({
  // { tipo: 'empresa' | 'nucleo', datos } — ver fichaDeEmpresa y fichaDeNucleo.
  ficha: { type: Object, required: true },
})
const emit = defineEmits(['cerrar', 'ir', 'empresa', 'nucleo'])

const pct = (p) => `${Number(p).toLocaleString('es-ES', { maximumFractionDigits: 1 })} %`
const millones = (x) => `${(x / 1e6).toLocaleString('es-ES', { maximumFractionDigits: 1 })} M€`
const anio = (f) => (f ? String(f).slice(0, 4) : '')
const fecha = (f) => {
  if (!f) return ''
  const [a, m] = String(f).split('-')
  return m ? `${m}/${a}` : a
}
const legible = (t) => (t ?? '').toLowerCase().replace(/^./, (c) => c.toUpperCase())
const TIPO = { estado: 'Estado accionista', grupo: 'Grupo accionista', fortuna: 'Fortuna personal' }

function tecla(e) {
  if (e.key === 'Escape') emit('cerrar')
}
onMounted(() => window.addEventListener('keydown', tecla))
onBeforeUnmount(() => window.removeEventListener('keydown', tecla))
</script>

<template>
  <aside class="ficha-r" role="dialog" :aria-label="`Ficha de ${ficha.datos.nombre}`">
    <button type="button" class="cerrar" aria-label="Cerrar la ficha" @click="emit('cerrar')">×</button>

    <!-- Una cotizada -->
    <template v-if="ficha.tipo === 'empresa'">
      <template v-for="f in [ficha.datos]" :key="f.clave">
        <p class="antes">{{ f.sector || 'Cotizada' }}<template v-if="f.medio"> · grupo de comunicación</template></p>
        <h2>{{ f.nombre }}</h2>
        <p v-if="f.nombreCompleto.toLowerCase() !== f.nombre.toLowerCase()" class="completo">{{ f.nombreCompleto }}</p>

        <section v-if="f.preside" class="bloque-f">
          <h3>Presidencia</h3>
          <p>
            <button type="button" class="enlace" @click="emit('ir', f.preside.clave)">{{ f.preside.nombre }}</button>
            <span class="dato">{{ [f.preside.categoria && `consejero ${f.preside.categoria.toLowerCase()}`, f.preside.representa && `en nombre de ${f.preside.representa}`].filter(Boolean).join(', ') }}</span>
          </p>
        </section>

        <section v-if="f.duenos.length" class="bloque-f">
          <h3>De quién es</h3>
          <ul class="duenos">
            <li v-for="d in f.duenos" :key="d.clave" :class="d.nucleo ? `k-${d.nucleo.tipo}` : d.gestora ? 'gestora' : 'suelto'">
              <span class="fila">
                <button
                  type="button"
                  class="enlace nombre-d"
                  @click="d.nucleo ? emit('nucleo', d.nucleo.id) : emit('ir', d.clave)"
                >{{ d.nombre }}</button>
                <span class="barra"><span :style="{ width: `${Math.min(100, d.porcentaje)}%` }" /></span>
                <span class="pct">{{ pct(d.porcentaje) }}</span>
              </span>
              <span v-if="d.nucleo && d.nucleo.nombre.toLowerCase() !== d.nombre.toLowerCase().replace(/,.*$/, '')" class="dato">del núcleo {{ d.nucleo.nombre }}</span>
              <span v-else-if="d.gestora" class="dato">gestora de fondos: está en casi todas</span>
              <span v-if="d.preside" class="dato estado">
                Presidencia:
                <button type="button" class="enlace" @click="emit('ir', d.preside.persona)">{{ d.preside.nombre }}</button>
                · nombramiento de {{ anio(d.preside.desde) }}{{ d.preside.gobierno ? `, Gobierno de ${d.preside.gobierno}` : '' }} (BOE)
              </span>
            </li>
          </ul>
        </section>

        <section v-if="f.dominicales.length" class="bloque-f">
          <h3>En su consejo, en nombre de sus dueños</h3>
          <ul class="lista">
            <li v-for="m in f.dominicales" :key="m.clave">
              <button type="button" class="enlace" @click="emit('ir', m.clave)">{{ m.nombre }}</button>
              <span class="dato">por {{ m.representa }}<template v-if="m.cargo && m.cargo !== 'Consejero'"> · {{ legible(m.cargo) }}</template></span>
            </li>
          </ul>
        </section>

        <section v-if="f.enOtros.length" class="bloque-f">
          <h3>De su consejo, también en otros</h3>
          <ul class="lista">
            <li v-for="m in f.enOtros" :key="m.clave">
              <button type="button" class="enlace" @click="emit('ir', m.clave)">{{ m.nombre }}</button>
              <span class="dato">
                <template v-for="(o, i) in m.otras" :key="o.clave"><template v-if="i"> y </template><button type="button" class="enlace suave" @click="emit('empresa', o.clave)">{{ o.nombre }}</button></template>
              </span>
            </li>
          </ul>
        </section>

        <section v-if="f.puertas.length" class="bloque-f puertas">
          <h3>Ex altos cargos que entraron</h3>
          <ul class="lista">
            <li v-for="p in f.puertas" :key="p.persona + p.fecha">
              <button type="button" class="enlace" @click="emit('ir', p.persona)">{{ p.nombre }}</button>
              <span class="dato">antes, {{ legible(p.cargoAnterior) }}<template v-if="p.fecha"> · autorización de {{ fecha(p.fecha) }}</template></span>
            </li>
          </ul>
          <p class="fuente">Autorizaciones de la Oficina de Conflictos de Intereses.</p>
        </section>

        <section v-if="f.dinero" class="bloque-f">
          <h3>Dinero público</h3>
          <p><b>{{ millones(f.dinero.importe) }}</b> en {{ f.dinero.n }} {{ f.dinero.n === 1 ? 'contrato o subvención' : 'contratos y subvenciones' }}, según el mapa del dinero.</p>
        </section>

        <p class="fuentes">
          Fuentes:
          <a v-if="f.url" :href="f.url" target="_blank" rel="noopener">participaciones en la CNMV</a><template v-if="f.urlGobierno"> ·
            <a :href="f.urlGobierno" target="_blank" rel="noopener">informe de gobierno corporativo{{ f.ejercicio ? ` ${f.ejercicio}` : '' }}</a></template>
        </p>
        <button type="button" class="red" @click="emit('ir', f.clave)">Ver sus relaciones en la red →</button>
      </template>
    </template>

    <!-- Un núcleo -->
    <template v-else>
      <template v-for="n in [ficha.datos]" :key="n.id">
        <p class="antes">{{ TIPO[n.tipo] }}</p>
        <h2>{{ n.nombre }}</h2>
        <ul v-if="n.tipo === 'estado' || n.titulares.length > 1" class="lista titulares">
          <li v-for="t in n.titulares" :key="t.clave">
            <button type="button" class="enlace" @click="emit('ir', t.clave)">{{ t.nombre }}</button>
            <span v-if="t.preside" class="dato">
              Presidencia: <button type="button" class="enlace" @click="emit('ir', t.preside.persona)">{{ t.preside.nombre }}</button>
              · nombramiento de {{ anio(t.preside.desde) }}{{ t.preside.gobierno ? `, Gobierno de ${t.preside.gobierno}` : '' }} (BOE)
            </span>
          </li>
        </ul>

        <section class="bloque-f">
          <h3>Lo que tiene</h3>
          <ul class="duenos" :class="`k-${n.tipo}`">
            <li v-for="c in n.cotizadas" :key="c.clave">
              <span class="fila">
                <button type="button" class="enlace nombre-d" @click="emit('empresa', c.clave)">{{ c.nombre }}</button>
                <span class="barra"><span :style="{ width: `${Math.min(100, c.porcentaje)}%` }" /></span>
                <span class="pct">{{ pct(c.porcentaje) }}</span>
              </span>
              <span v-if="n.tipo === 'estado'" class="dato">por {{ c.via }}</span>
            </li>
          </ul>
        </section>

        <section v-if="n.sienta.length" class="bloque-f">
          <h3>A quién sienta en los consejos</h3>
          <ul class="lista">
            <li v-for="x in n.sienta" :key="x.clave + x.cotizada">
              <button type="button" class="enlace" @click="emit('ir', x.clave)">{{ x.nombre }}</button>
              <span class="dato">{{ x.cotizada }}<template v-if="x.cargo && x.cargo !== 'Consejero'"> · {{ legible(x.cargo) }}</template></span>
            </li>
          </ul>
        </section>

        <section v-if="n.puertas.length" class="bloque-f puertas">
          <h3>Ex altos cargos en sus cotizadas</h3>
          <ul class="lista">
            <li v-for="p in n.puertas" :key="p.persona + p.cotizada">
              <button type="button" class="enlace" @click="emit('ir', p.persona)">{{ p.nombre }}</button>
              <span class="dato">{{ p.cotizada }} · antes, {{ legible(p.cargoAnterior) }}</span>
            </li>
          </ul>
          <p class="fuente">Autorizaciones de la Oficina de Conflictos de Intereses.</p>
        </section>

        <p class="fuentes">Fuente: participaciones significativas e informes de gobierno corporativo, CNMV; nombramientos, BOE.</p>
        <button v-if="n.tipo !== 'estado'" type="button" class="red" @click="emit('ir', n.titulares[0].clave)">Ver sus relaciones en la red →</button>
      </template>
    </template>
  </aside>
</template>

<style scoped>
.ficha-r {
  position: fixed; z-index: 40; top: 0; right: 0; bottom: 0; width: min(27rem, 100vw); box-sizing: border-box;
  overflow-y: auto; overscroll-behavior: contain; padding: var(--e5) var(--e5) var(--e6);
  background: var(--hoja); color: var(--tinta); border-left: 1px solid var(--filete-medio); box-shadow: -12px 0 32px rgb(0 0 0 / 0.14);
  font-family: var(--sans); font-size: var(--t-s); line-height: 1.45;
}
.cerrar { all: unset; cursor: pointer; position: sticky; top: 0; float: right; margin: calc(-1 * var(--e2)) calc(-1 * var(--e2)) 0 0; width: 2rem; height: 2rem; text-align: center; font-size: 1.5rem; line-height: 2rem; color: var(--tinta-2); border-radius: 50%; background: var(--hoja); }
.cerrar:hover, .cerrar:focus-visible { background: var(--papel-2); color: var(--tinta); }
.antes { margin: 0; font-size: 0.68rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--tinta-3); }
h2 { font-family: var(--serif); font-size: var(--t-h1); font-weight: 600; line-height: 1.1; margin: var(--e1) 0 0; }
.completo { margin: var(--e1) 0 0; color: var(--tinta-3); }
.bloque-f { margin-top: var(--e5); }
h3 { margin: 0 0 var(--e2); font-family: var(--sans); font-size: 0.7rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--tinta-3); font-weight: 600; border-bottom: 1px solid var(--filete-suave); padding-bottom: var(--e1); }
.bloque-f p { margin: 0; }
.enlace { all: unset; cursor: pointer; -webkit-tap-highlight-color: transparent; color: var(--tinta); border-bottom: 1px solid var(--filete-medio); }
.enlace:hover, .enlace:focus-visible { border-bottom-color: var(--tinta); background: var(--papel-2); }
.enlace.suave { color: var(--tinta-2); }
.dato { display: block; color: var(--tinta-3); font-size: var(--t-xs); margin-top: 1px; }
.dato.estado { color: var(--tinta-2); }
.duenos, .lista { list-style: none; margin: 0; padding: 0; }
.duenos li, .lista li { padding: var(--e2) 0; border-bottom: 1px solid var(--filete-suave); }
.duenos li:last-child, .lista li:last-child { border-bottom: 0; }
.fila { display: grid; grid-template-columns: minmax(0, 1fr) 5.5rem 3.6rem; gap: var(--e2); align-items: center; }
.nombre-d { justify-self: start; }
.barra { height: 0.5rem; background: var(--papel-3); border-radius: 1px; overflow: hidden; }
.barra span { display: block; height: 100%; background: var(--c, var(--neutro)); }
.pct { font-family: var(--mono); font-size: var(--t-xs); text-align: right; color: var(--tinta-2); }
.k-estado { --c: var(--adm); }
.k-grupo { --c: var(--emp); }
.k-fortuna { --c: var(--par); }
.gestora { --c: var(--papel-3); }
.gestora .barra span { background: var(--neutro); opacity: 0.5; }
.puertas h3 { color: var(--adm); }
.fuente { margin-top: var(--e1) !important; color: var(--tinta-3); font-size: var(--t-xs); }
.fuentes { margin: var(--e5) 0 0; color: var(--tinta-3); font-size: var(--t-xs); }
.fuentes a { color: var(--tinta-2); }
.red { all: unset; cursor: pointer; display: inline-block; margin-top: var(--e4); padding: var(--e2) var(--e4); border: 1px solid var(--tinta); border-radius: var(--radio); font-weight: 600; }
.red:hover, .red:focus-visible { background: var(--tinta); color: var(--papel); }
.titulares { margin-top: var(--e3); }

@media (max-width: 48rem) {
  /* En el móvil, una hoja que sube desde abajo. */
  .ficha-r { top: auto; left: 0; width: 100vw; max-height: 82vh; border-left: 0; border-top: 1px solid var(--filete-medio); border-radius: 10px 10px 0 0; box-shadow: 0 -12px 32px rgb(0 0 0 / 0.18); padding: var(--e4) var(--e4) var(--e6); }
}
</style>
