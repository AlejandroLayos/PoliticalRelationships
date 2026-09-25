<script setup>
/**
 * La sección de cargos públicos: quién ocupó qué alto cargo del Estado, y
 * cuándo, con el Real Decreto de cada cosa a un clic.
 *
 * Es la única página de la web con nombres de personas, y lo dice arriba y
 * con la regla: salen por haber ocupado un cargo público y sólo por eso
 * (spec §12). De lo que alguien hizo antes o después, sólo lo que afirma una
 * fuente oficial en ese papel: una autorización de la Oficina de Conflictos
 * de Intereses, o lo que el diputado declaró al Congreso.
 *
 * Lo que no se sabe se enseña como no sabido: un periodo sin cese es «no
 * consta cese», no «sigue en el cargo»; uno sin nombramiento arranca en el
 * borde del eje, deshilachado, no en una fecha inventada.
 */
import { computed, nextTick, ref, watch } from 'vue'
import { dineroCorto } from '../nucleos.js'
import {
  bajoGobierno,
  buscarCargos,
  dePapel,
  delOrganoEnPalabras,
  fechaCorta,
  fechaLarga,
  gobiernos as gobiernosDe,
  huecoDelPeriodo,
  lineaDeTiempo,
  marcasDeAnios,
  movimientos,
  nombreDeGobierno,
  nombreFuente,
  organismos,
  papelDeLaFicha,
  personaDeClave,
  presidencias,
  recuento,
  sectorDeclarado,
  tramo,
} from '../cargos.js'

const props = defineProps({
  /** `cargos.json`, o null mientras llega o si la edición no lo trae. */
  datos: { type: Object, default: null },
  /** La clave de la persona abierta, o ''. */
  persona: { type: String, default: '' },
  cargando: { type: Boolean, default: false },
})
const emit = defineEmits(['persona', 'entidad'])

const filtro = ref('')
/** Todos, quien tiene un Real Decreto, o los diputados. */
const papel = ref('todos')
/** La clave del presidente bajo cuyo Gobierno se nombró, o ''. */
const gobierno = ref('')
const VISIBLES = 30
const cuantas = ref(VISIBLES)
watch([filtro, papel, gobierno], () => {
  cuantas.value = VISIBLES
})

const abierta = computed(() => personaDeClave(props.datos, props.persona))
const filtradas = computed(() =>
  bajoGobierno(dePapel(buscarCargos(props.datos, filtro.value), papel.value), gobierno.value),
)
const porGobierno = computed(() => gobiernosDe(props.datos))
const PAPELES = [
  { id: 'todos', texto: 'Todos' },
  { id: 'boe', texto: 'Altos cargos' },
  { id: 'congreso', texto: 'Diputados' },
  { id: 'autorizados', texto: 'Autorizados a ir al sector privado' },
]
const ultimos = computed(() => movimientos(props.datos, 12))
const porOrganismo = computed(() => organismos(props.datos, 6))
const gobiernos = computed(() => presidencias(props.datos))
const cuantos = computed(() => recuento(props.datos))

const eje = computed(() => {
  const p = abierta.value
  if (!p || !props.datos) return { barras: [], marcas: [] }
  return {
    barras: lineaDeTiempo(p.periodos, props.datos.actosDesde, props.datos.actosHasta),
    marcas: marcasDeAnios(props.datos.actosDesde, props.datos.actosHasta),
  }
})

function abrir(clave) {
  emit('persona', clave)
}

/*
  La ficha se abre encima de las listas, debajo del titular. Sin llevarla a
  la vista, pinchar un nombre al final de la lista —o llegar por un enlace en
  un móvil— la abría fuera de la pantalla y parecía que no había pasado nada.
  Se mira `abierta` y no la clave: en un enlace directo la clave llega antes
  que los datos, y la ficha no existe hasta que llegan.
*/
const ficha = ref(null)
watch(
  () => abierta.value?.clave,
  async (clave) => {
    if (!clave) return
    await nextTick()
    ficha.value?.scrollIntoView({ block: 'start', behavior: 'smooth' })
  },
)

const VERBOS = { nombramiento: 'Nombramiento', cese: 'Cese', autorizacion: 'Autorizada' }
const verbo = (a) => VERBOS[a.tipo] ?? a.tipo
</script>

<template>
  <div class="cargos">
    <section class="primera">
      <div class="apertura">
        <p class="antetitulo">Cargos públicos · BOE, Oficina de Conflictos de Intereses y Congreso</p>
        <h1 class="titular">Quién ha ocupado los cargos del Estado, y de dónde venía</h1>
        <p v-if="datos" class="entradilla">
          {{ cuantos.boe.toLocaleString('es-ES') }} personas nombradas o
          cesadas por Real Decreto entre el {{ fechaLarga(datos.actosDesde) }} y el
          {{ fechaLarga(datos.actosHasta) }}: ministros, secretarios de Estado,
          subsecretarios, directores generales, embajadores y quien preside o
          dirige un organismo público.
          <template v-if="datos.nAutorizaciones">
            Y {{ datos.nAutorizaciones.toLocaleString('es-ES') }} autorizaciones de la
            Oficina de Conflictos de Intereses para trabajar en el sector privado
            tras el cese<template v-if="cuantos.soloOci">; de
            {{ cuantos.soloOci.toLocaleString('es-ES') }} de las personas autorizadas
            no hay nombramiento en lo leído del BOE</template>.
          </template>
          <template v-if="cuantos.diputados">
            Y {{ cuantos.diputados.toLocaleString('es-ES') }} diputados de la
            legislatura en curso con lo que declararon al Congreso de su
            actividad: para quién trabajaban antes de llegar al escaño.
          </template>
        </p>
        <p v-else-if="cargando" class="entradilla">Cargando los cargos…</p>
        <p v-else class="entradilla">Esta edición no trae cargos públicos.</p>
      </div>
      <!--
        La regla, arriba y no en la letra pequeña. En el resto de la web no
        sale ninguna persona física, y quien llega aquí desde allí tiene que
        saber por qué aquí sí.
      -->
      <aside class="por-que" aria-label="Por qué aquí hay nombres">
        <p class="antetitulo">Por qué aquí hay nombres</p>
        <p>
          En el resto de esta web no sale ninguna persona física. Aquí sí, y
          sólo con lo que publican el BOE —quién fue nombrado para qué cargo y
          cuándo cesó—, la Oficina de Conflictos de Intereses —a qué se le
          autorizó a dedicarse después— y el Congreso —quién fue diputado, por
          qué formación, y lo que cada diputado declaró de su actividad—.
          Ocupar un cargo público es un hecho público.
        </p>
        <p class="nota">
          De lo que alguien hizo antes o después del cargo, aquí sólo sale lo
          que dice una de esas fuentes, y con sus palabras.
        </p>
      </aside>
    </section>

    <!--
      Las presidencias del Gobierno que hay en lo leído: el contexto de todo
      lo demás. De los Reales Decretos del Presidente; la formación, sólo si
      su ficha está unida al Congreso por nombre y cargo en su biografía, que
      el BOE no la dice.
    -->
    <ol v-if="gobiernos.length && !abierta" class="gobiernos" aria-label="Presidencias del Gobierno">
      <li v-for="g in gobiernos" :key="g.persona + (g.desde ?? g.hasta)">
        <a href="#" @click.prevent="abrir(g.persona)">{{ g.nombre }}</a>
        <span class="tramo">
          {{ tramo(g) }}
          <abbr v-if="g.formacion" title="Formación con la que fue elegido diputado, según el Congreso">· {{ g.formacion }}</abbr>
        </span>
      </li>
    </ol>

    <!-- La ficha de una persona, encima de todo lo demás. -->
    <article v-if="abierta" ref="ficha" class="ficha" aria-live="polite">
      <header class="ficha-cabeza">
        <p class="antetitulo">{{ papelDeLaFicha(abierta) }}</p>
        <h2 class="ficha-nombre">{{ abierta.nombre }}</h2>
        <button class="boton tenue" @click="emit('persona', '')">← Todos los cargos</button>
      </header>

      <!--
        El eje va de lo primero a lo último leído del BOE, no de la vida de
        la persona. Lo que queda fuera de lo leído no se dibuja como sabido.
      -->
      <!--
        Sólo con años que marcar: un eje de tres semanas es una raya con una
        mota al final, que no enseña nada que no digan las fechas.
      -->
      <figure
        v-if="eje.barras.length && eje.marcas.length"
        class="eje"
        aria-hidden="true"
        :style="{ height: `${1.9 + eje.barras.length * 0.9}rem` }"
      >
        <span
          v-for="m in eje.marcas"
          :key="m.anio"
          class="eje-marca"
          :class="{ borde: m.x < 0.04 }"
          :style="{ left: `${m.x * 100}%` }"
        >{{ m.anio }}</span>
        <span
          v-for="(b, i) in eje.barras"
          :key="i"
          class="eje-barra"
          :class="{ izq: b.abiertoIzquierda, der: b.abiertoDerecha }"
          :style="{
            left: `${b.inicio * 100}%`,
            width: `max(3px, ${(b.fin - b.inicio) * 100}%)`,
            top: `${1.6 + i * 0.9}rem`,
          }"
          :title="b.periodo.cargo"
        />
        <!--
          El número de cada barra, el mismo que el de su periodo en la lista
          de debajo: detrás de la barra, o delante si la barra llega al final.
        -->
        <span
          v-for="(b, i) in eje.barras"
          :key="`n${i}`"
          class="eje-num"
          :class="{ delante: b.fin > 0.9 }"
          :style="{
            left: b.fin > 0.9 ? `${b.inicio * 100}%` : `${b.fin * 100}%`,
            top: `${1.6 + i * 0.9}rem`,
          }"
        >{{ String(i + 1).padStart(2, '0') }}</span>
      </figure>

      <ol class="periodos">
        <li v-for="(p, i) in abierta.periodos" :key="i" class="periodo">
          <span class="puesto-num">{{ String(i + 1).padStart(2, '0') }}</span>
          <div class="periodo-cuerpo">
            <p class="periodo-cargo">{{ p.cargo }}</p>
            <p v-if="p.organismo" class="periodo-organismo">{{ p.organismo }}</p>
            <!--
              Bajo qué Gobierno se nombró: la fecha del Real Decreto contra
              las presidencias leídas. Dice quién gobernaba, no el partido de
              la persona nombrada.
            -->
            <p v-if="p.gobierno" class="periodo-gobierno">
              Nombramiento con el
              <a href="#" @click.prevent="abrir(p.gobierno.persona)">Gobierno de {{ p.gobierno.nombre }}</a><abbr
                v-if="p.gobierno.formacion"
                title="Formación con la que el presidente fue elegido diputado, según el Congreso"
              > · {{ p.gobierno.formacion }}</abbr>
            </p>
            <p v-if="p.formacion" class="periodo-organismo">
              {{ p.formacion }}<template v-if="p.circunscripcion"> · {{ p.circunscripcion }}</template><template v-if="p.grupo"> · {{ p.grupo }}</template>
            </p>
            <!--
              El órgano que dirigía, cuando es uno del mapa del dinero: por ahí
              se llega a lo que contrató. Sólo si el nombre del órgano sale del
              puesto por construcción y es uno del Estado (exportar_cargos.py).
            -->
            <p v-if="p.organo" class="periodo-organo">
              Dirigía
              <a href="#" @click.prevent="emit('entidad', p.organo.clave)">{{ p.organo.nombre }}</a>:
              ver a quién contrató →
            </p>
            <p class="periodo-tramo">
              <span class="tramo">{{ tramo(p) }}</span>
              <span v-if="huecoDelPeriodo(p)" class="hueco">· {{ huecoDelPeriodo(p) }}</span>
            </p>
            <p class="periodo-fuentes">
              <a v-if="p.urlDesde && p.fuente === 'congreso'" :href="p.urlDesde" target="_blank" rel="noopener" class="sello">
                Congreso de los Diputados
              </a>
              <a v-else-if="p.urlDesde" :href="p.urlDesde" target="_blank" rel="noopener" class="sello">
                Nombramiento · {{ p.boeDesde }}
              </a>
              <a v-if="p.urlHasta" :href="p.urlHasta" target="_blank" rel="noopener" class="sello">
                Cese · {{ p.boeHasta || nombreFuente(p) }}
              </a>
              <span v-if="p.motivoCese" class="motivo">{{ p.motivoCese }}</span>
              <span v-if="p.cruce" class="motivo">unido a esta ficha por {{ p.cruce }}</span>
            </p>
          </div>
        </li>
      </ol>
      <!--
        Lo que vino después del cargo, cuando lo afirma la fuente que lo
        autoriza. Una autorización no dice que la persona llegara a ocupar el
        puesto, y aquí no se dice tampoco.
      -->
      <section v-if="abierta.autorizaciones?.length" class="autorizaciones">
        <h3>Autorizaciones para trabajar en el sector privado tras el cese</h3>
        <p class="nota">
          Según la Oficina de Conflictos de Intereses, que autoriza a quien deja
          un alto cargo a trabajar en una entidad privada en los dos años
          siguientes. Una autorización no dice que llegara a ocupar el puesto.
          Si el órgano que dirigía pagó a esa sociedad, se dice al lado: son dos
          hechos documentados y ninguno dice nada del otro. Las fechas son las
          de concesión o de publicación del expediente, no las del contrato.
        </p>
        <ul>
          <li v-for="(a, i) in abierta.autorizaciones" :key="i" class="autorizacion">
            <p class="actividad">{{ a.actividad }}</p>
            <p class="autorizacion-meta">
              <span v-if="a.gobierno" class="gobierno-autorizacion">nombramiento con el {{ nombreDeGobierno(a.gobierno) }} · </span>
              <span v-if="a.fecha" class="tramo">autorizada el {{ fechaCorta(a.fecha) }}</span>
              <span v-if="a.cargoAnterior"> · tras cesar como {{ a.cargoAnterior.toLowerCase() }}</span>
              <span v-if="a.fechaCese"> ({{ fechaCorta(a.fechaCese) }})</span>
            </p>
            <!--
              La sociedad del mapa del dinero, cuando el texto la nombra por
              su denominación completa, que es única en España.
            -->
            <p v-if="a.empresa" class="autorizacion-empresa">
              En el mapa del dinero:
              <a href="#" @click.prevent="emit('entidad', a.empresa.clave)">{{ a.empresa.nombre }}</a>
              — ver de quién cobra →
            </p>
            <!--
              El órgano que dirigió, cuando pagó a esa misma sociedad. Dos
              hechos documentados, uno al lado del otro; la nota de arriba
              dice lo que no significan.
            -->
            <p v-for="(d, k) in a.delOrgano ?? []" :key="k" class="del-organo">
              <a href="#" @click.prevent="emit('entidad', d.organo.clave)">{{ d.organo.nombre }}</a>,
              que dirigía, {{ delOrganoEnPalabras(d).verbo }} a esta entidad
              <strong>{{ dineroCorto(d.importe) }}</strong>
              <span class="tramo">
                · {{ delOrganoEnPalabras(d).cuantos }}<template v-if="delOrganoEnPalabras(d).cuando"> · {{ delOrganoEnPalabras(d).cuando }}</template>
              </span>
            </p>
            <p class="periodo-fuentes">
              <a v-if="a.url" :href="a.url" target="_blank" rel="noopener" class="sello">Oficina de Conflictos de Intereses</a>
              <span v-if="a.cruce" class="motivo">unida a esta ficha por {{ a.cruce }}</span>
            </p>
          </li>
        </ul>
      </section>

      <!--
        Lo que el diputado declaró al Congreso de su actividad: los años
        anteriores al escaño y lo que mantiene. Con sus palabras, sin
        interpretarlas; la sociedad del mapa, sólo si la nombra entera.
      -->
      <section v-if="abierta.declaraciones?.length" class="autorizaciones declaraciones">
        <h3>Lo que declaró al Congreso de su actividad</h3>
        <p class="nota">
          Cada diputado declara al tomar posesión para quién ha trabajado y en
          qué. Es su declaración, tal como la publica el Congreso: aquí no se
          corrige ni se completa.
        </p>
        <ul>
          <li v-for="(d, i) in abierta.declaraciones" :key="i" class="autorizacion">
            <p class="actividad">
              {{ d.empleador || d.descripcion }}
              <span v-if="sectorDeclarado(d)" class="sector" :class="sectorDeclarado(d)">{{ sectorDeclarado(d) === 'privado' ? 'sector privado' : 'sector público' }}</span>
            </p>
            <p class="autorizacion-meta">
              <span v-if="d.empleador && d.descripcion">{{ d.descripcion }}</span>
              <span v-if="d.periodo" class="tramo"><template v-if="d.empleador && d.descripcion"> · </template>{{ d.periodo }}</span>
            </p>
            <p v-if="d.empresa" class="autorizacion-empresa">
              En el mapa del dinero:
              <a href="#" @click.prevent="emit('entidad', d.empresa.clave)">{{ d.empresa.nombre }}</a>
              — ver de quién cobra →
            </p>
            <p class="periodo-fuentes">
              <a v-if="d.url" :href="d.url" target="_blank" rel="noopener" class="sello">
                Congreso<template v-if="d.fechaRegistro"> · declarada el {{ fechaCorta(d.fechaRegistro) }}</template>
              </a>
              <span v-if="d.cruce" class="motivo">unida a esta ficha por {{ d.cruce }}</span>
            </p>
          </li>
        </ul>
      </section>

      <p class="nota ficha-pie">
        Dos personas con el mismo nombre y los mismos apellidos se juntarían en
        esta ficha: ni el BOE ni el Congreso publican un identificador. Cada
        periodo lleva su fuente para comprobarlo.
      </p>
    </article>

    <div v-if="datos" class="rejilla">
      <section class="seccion">
        <header class="seccion-cabeza">
          <p class="antetitulo">Personas</p>
          <h2>{{ filtradas.length.toLocaleString('es-ES') }} con cargo</h2>
        </header>
        <div class="papeles" role="group" aria-label="Qué cargos">
          <button
            v-for="x in PAPELES"
            :key="x.id"
            class="papel"
            :aria-pressed="papel === x.id"
            @click="papel = x.id"
          >{{ x.texto }}</button>
        </div>
        <!--
          Por Gobierno: quién estaba en la Presidencia el día del Real
          Decreto. Sólo con presidencias leídas.
        -->
        <div v-if="porGobierno.length" class="papeles gobiernos-filtro" role="group" aria-label="Nombrados con el Gobierno de">
          <button class="papel" :aria-pressed="!gobierno" @click="gobierno = ''">Cualquier Gobierno</button>
          <button
            v-for="g in porGobierno"
            :key="g.persona"
            class="papel"
            :aria-pressed="gobierno === g.persona"
            :title="`${g.personas} personas nombradas con el ${nombreDeGobierno(g)}`"
            @click="gobierno = g.persona"
          >{{ g.nombre }}<template v-if="g.formacion"> · {{ g.formacion }}</template></button>
        </div>
        <label class="filtro">
          <span class="visualmente-oculto">Buscar entre los cargos</span>
          <input
            v-model="filtro"
            type="search"
            placeholder="Una persona, un cargo, un partido o una empresa"
          />
        </label>
        <ol class="personas">
          <li v-for="p in filtradas.slice(0, cuantas)" :key="p.clave">
            <button
              class="fila"
              :class="{ actual: p.clave === persona }"
              @click="abrir(p.clave)"
            >
              <span class="nombre">{{ p.nombre }}</span>
              <span class="ultimo">
                {{ p.periodos[0]?.cargo }}
                <span class="cuando">· {{ tramo(p.periodos[0] ?? {}) }}</span>
              </span>
              <span v-if="p.periodos.length > 1" class="mas-cargos">
                y {{ p.periodos.length - 1 }}
                {{ p.periodos.length - 1 === 1 ? 'cargo más' : 'cargos más' }}
              </span>
              <span v-if="p.autorizaciones?.length" class="con-autorizacion">
                {{ p.autorizaciones.length }}
                {{ p.autorizaciones.length === 1 ? 'autorización' : 'autorizaciones' }}
                para el sector privado
              </span>
              <span v-if="p.declaraciones?.length" class="con-declaracion">
                {{ p.declaraciones.length }}
                {{ p.declaraciones.length === 1 ? 'actividad declarada' : 'actividades declaradas' }}
              </span>
            </button>
          </li>
        </ol>
        <p v-if="!filtradas.length" class="nota">
          Nadie con «{{ filtro.trim() }}» en lo leído.
        </p>
        <button v-if="filtradas.length > cuantas" class="mas" @click="cuantas += VISIBLES * 2">
          Ver más ({{ (filtradas.length - cuantas).toLocaleString('es-ES') }} restantes)
        </button>
      </section>

      <aside class="lateral">
        <section class="seccion">
          <header class="seccion-cabeza">
            <p class="antetitulo">Lo último publicado</p>
            <h2>Nombramientos y ceses</h2>
          </header>
          <ol class="movimientos">
            <li v-for="(a, i) in ultimos" :key="i" class="movimiento">
              <p class="mov-linea">
                <span class="mov-fecha">{{ fechaCorta(a.fecha) }}</span>
                <span class="mov-verbo" :class="a.tipo">{{ verbo(a) }}</span>
              </p>
              <p class="mov-texto">
                <a href="#" @click.prevent="abrir(a.persona.clave)">{{ a.persona.nombre }}</a>,
                {{ a.periodo.cargo }}
              </p>
              <a v-if="a.url" :href="a.url" target="_blank" rel="noopener" class="sello">{{ a.boe }}</a>
            </li>
          </ol>
        </section>

        <section v-if="porOrganismo.length" class="seccion">
          <header class="seccion-cabeza">
            <p class="antetitulo">Dónde</p>
            <h2>Organismos con más movimientos</h2>
          </header>
          <ul class="lista">
            <li v-for="o in porOrganismo" :key="o.nombre">
              <a href="#" @click.prevent="filtro = o.nombre">{{ o.nombre }}</a>
              <span class="cifra">{{ o.actos }}</span>
            </li>
          </ul>
        </section>
      </aside>
    </div>

    <footer class="metodo">
      <h2>Cómo se hace esta sección</h2>
      <p>
        Cada noche se leen los sumarios del BOE y, de su sección II.A, los
        Reales Decretos que nombran o cesan a una persona en un alto cargo de
        la Ley 3/2015. De cada uno se guarda la disposición entera, que es la
        prueba. Fiscales, jueces y militares también se nombran por Real
        Decreto; son carreras profesionales y no salen.
      </p>
      <p>
        Los ministros se nombran todos a la vez, en un Real Decreto con los
        nombres en el cuerpo; se leen de ahí, párrafo a párrafo. Lo que no se
        lee: los nombramientos por orden ministerial y los gobiernos
        autonómicos, que publican en sus propios boletines. Por eso un periodo
        puede no tener cese: quiere decir que no consta en lo leído, no que la
        persona siga en el cargo.
      </p>
      <p>
        Del Congreso se leen los diputados de cada legislatura desde la IX
        (2008), con su formación, y la declaración de actividades de los de la
        legislatura en curso. Un diputado se une a un alto cargo sólo si tiene
        su nombre entero y su biografía del Congreso menciona ese cargo; y sale
        aquí si se une o si hizo declaración. De la declaración se leen sólo
        las actividades: las donaciones y aportaciones no.
      </p>
      <p>
        El BOE no publica ningún identificador en un nombramiento: una persona
        es su nombre. Si el BOE la escribe de dos maneras —con y sin su primer
        nombre, por ejemplo— salen dos fichas, y no se juntan a mano.
      </p>
    </footer>
  </div>
</template>

<style scoped>
.cargos {
  overflow-y: auto; height: 100%;
  padding: var(--e6) var(--e5) var(--e8);
}
.cargos > * { max-width: 78rem; margin-left: auto; margin-right: auto; }

.primera {
  display: grid; gap: var(--e6) var(--e7);
  grid-template-columns: minmax(0, 1fr) minmax(16rem, 22rem);
  align-items: end;
}
.titular {
  font-size: var(--t-titular); line-height: 1.04; letter-spacing: -0.022em;
  font-weight: 600; margin: 0; max-width: 20ch;
}
.entradilla {
  font-family: var(--serif); font-size: var(--t-l); line-height: 1.5;
  color: var(--tinta-2); margin: var(--e4) 0 0; max-width: 52ch;
}
.por-que { border-top: 2px solid var(--filete); padding-top: var(--e3); }
.por-que p:not(.antetitulo) {
  font-size: var(--t-s); line-height: 1.5; color: var(--tinta-2); margin: var(--e2) 0 0;
}
.por-que .nota { color: var(--tinta); }

.gobiernos {
  list-style: none; margin: var(--e6) auto 0; padding: var(--e3) 0 0;
  display: flex; flex-wrap: wrap; gap: var(--e2) var(--e5);
  border-top: 1px solid var(--filete-suave);
}
.gobiernos li { display: flex; flex-direction: column; gap: 0.1rem; }
.gobiernos a { color: var(--tinta); font-weight: 600; font-size: var(--t-s); }
.gobiernos .tramo { font-size: var(--t-xs); color: var(--tinta-3); }

/* --- La ficha ------------------------------------------------------------ */

.ficha {
  margin-top: var(--e7); padding: var(--e5) 0 var(--e4);
  /* La cabecera es fija: sin margen, el nombre quedaría debajo de ella. */
  scroll-margin-top: 8rem;
  border-top: 3px solid var(--filete); border-bottom: 1px solid var(--filete-suave);
}
.ficha-cabeza {
  display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: end;
  gap: var(--e2) var(--e4);
}
.ficha-cabeza .antetitulo { grid-column: 1 / -1; color: var(--adm); }
.ficha-nombre {
  font-family: var(--serif); font-size: var(--t-h1); line-height: 1.1;
  font-weight: 600; margin: 0;
}

/*
  El eje: una pista con los años y una barra por periodo. Lo que no se sabe
  se deshilacha: un periodo sin nombramiento entra desde el borde con un
  degradado, uno sin cese se sale por el otro lado con el trazo punteado.
*/
.eje {
  position: relative; margin: var(--e5) 0 var(--e3);
  border-top: 1px solid var(--filete-suave);
}
.eje-marca {
  position: absolute; top: 0.2rem; transform: translateX(-50%);
  font-family: var(--mono); font-size: var(--t-xs); color: var(--tinta-3);
}
.eje-marca.borde { transform: none; }
.eje-marca.borde::before { left: 0; }
.eje-marca::before {
  content: ''; position: absolute; left: 50%; top: -0.45rem; height: 0.35rem;
  border-left: 1px solid var(--filete-medio);
}
.eje-barra {
  position: absolute; height: 0.5rem; background: var(--adm); border-radius: 1px;
}
.eje-num {
  position: absolute; margin-top: -0.28rem; padding: 0 0.35rem;
  font-family: var(--mono); font-size: 0.6875rem; line-height: 1; color: var(--tinta-3);
}
.eje-num.delante { transform: translateX(-100%); }
.eje-barra.izq {
  background: linear-gradient(to right, transparent, var(--adm) 2.5rem);
}
.eje-barra.der {
  background:
    repeating-linear-gradient(to right, var(--adm) 0 6px, transparent 6px 9px) right / 2.5rem 100% no-repeat,
    linear-gradient(to right, var(--adm), var(--adm)) left / calc(100% - 2.5rem) 100% no-repeat;
}
/*
  Abierto por los dos lados: se funde por la izquierda y se deshilacha por la
  derecha, con el tramo sabido entero en medio. Todo a rayas se leía como
  «no se sabe nada», y un escaño de 2023 a hoy se sabe entero.
*/
.eje-barra.izq.der {
  background:
    repeating-linear-gradient(to right, var(--adm) 0 6px, transparent 6px 9px) right / 2.5rem 100% no-repeat,
    linear-gradient(to right, transparent, var(--adm) 2.5rem) left / calc(100% - 2.5rem) 100% no-repeat;
}

.periodos { list-style: none; margin: var(--e4) 0 0; padding: 0; }
.periodo {
  display: grid; grid-template-columns: 1.8rem minmax(0, 1fr); gap: var(--e2);
  padding: var(--e3) 0; border-top: 1px solid var(--filete-suave);
}
.periodo .puesto-num { padding-top: 0.25rem; }
.periodo-cuerpo p { margin: 0; }
.periodo-cargo { font-family: var(--serif); font-size: var(--t-l); line-height: 1.3; color: var(--tinta); }
.periodo-organismo { font-size: var(--t-s); color: var(--tinta-2); margin-top: 0.15rem !important; }
.periodo-tramo { font-size: var(--t-s); margin-top: 0.3rem !important; }
.periodo-organo { font-size: var(--t-s); color: var(--tinta-2); margin-top: 0.3rem !important; }
.periodo-organo a { color: var(--adm); font-weight: 600; }
.tramo { font-family: var(--mono); font-size: var(--t-xs); color: var(--tinta); }
.hueco { font-style: italic; color: var(--tinta-3); margin-left: 0.3em; }
.periodo-fuentes {
  display: flex; flex-wrap: wrap; gap: var(--e2); align-items: center; margin-top: var(--e2) !important;
}
.periodo-fuentes a.sello, .movimiento a.sello { text-decoration: none; }
.periodo-fuentes a.sello:hover, .movimiento a.sello:hover { text-decoration: underline; }
.motivo { font-size: var(--t-xs); color: var(--tinta-3); font-style: italic; }
.ficha-pie { font-size: var(--t-s); margin: var(--e4) 0 0; max-width: var(--medida); }

/* --- Listas -------------------------------------------------------------- */

.rejilla {
  display: grid; gap: var(--e7); margin-top: var(--e7);
  grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr);
  align-items: start;
}
.lateral { display: grid; gap: var(--e7); }
.seccion { border-top: 3px solid var(--filete); padding-top: var(--e3); min-width: 0; }
.seccion-cabeza h2 { font-size: var(--t-h2); margin: 0 0 var(--e3); }

.filtro input {
  width: 100%; font: inherit; font-size: var(--t-m); color: var(--tinta);
  background: var(--hoja); border: 1px solid var(--filete-medio); border-radius: var(--radio);
  padding: 0.55rem 0.7rem; margin-bottom: var(--e3);
}
.filtro input:focus-visible { outline: 2px solid var(--tinta); outline-offset: 1px; }
.visualmente-oculto {
  position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap;
}

.personas { list-style: none; margin: 0; padding: 0; }
.fila {
  width: 100%; display: flex; flex-direction: column; gap: 0.15rem;
  background: none; border: none; border-bottom: 1px solid var(--filete-suave);
  color: inherit; font: inherit; text-align: left;
  padding: 0.6rem var(--e2); margin: 0 calc(-1 * var(--e2)); cursor: pointer;
  border-radius: var(--radio-s);
}
.fila:hover, .fila:focus-visible { background: var(--papel-2); outline: none; }
.fila:focus-visible { box-shadow: inset 0 0 0 2px var(--tinta); }
.fila.actual { background: var(--papel-2); box-shadow: inset 3px 0 0 var(--adm); }
.nombre { font-size: var(--t-m); font-weight: 600; color: var(--tinta); }
.fila:hover .nombre { text-decoration: underline; text-underline-offset: 0.18em; text-decoration-color: var(--filete-medio); }
.ultimo { font-size: var(--t-s); color: var(--tinta-2); line-height: 1.4; }
.cuando { font-family: var(--mono); font-size: var(--t-xs); color: var(--tinta-3); }
.mas-cargos { font-size: var(--t-xs); color: var(--tinta-3); }

.mas {
  display: block; width: 100%; margin: var(--e3) 0 0; padding: 0.55rem;
  background: none; border: none; color: var(--tinta); font: inherit; font-size: var(--t-s);
  font-weight: 600; cursor: pointer; text-decoration: underline;
  text-decoration-color: var(--filete-medio); text-underline-offset: 0.18em;
}

.movimientos { list-style: none; margin: 0; padding: 0; }
.movimiento { padding: 0.6rem 0; border-bottom: 1px solid var(--filete-suave); }
.movimiento p { margin: 0; }
.mov-linea { display: flex; gap: var(--e2); align-items: baseline; }
.mov-fecha { font-family: var(--mono); font-size: var(--t-xs); color: var(--tinta-3); }
.mov-verbo {
  font-size: var(--t-xs); font-weight: 650; letter-spacing: 0.08em; text-transform: uppercase;
}
.mov-verbo.nombramiento { color: var(--adm); }
.mov-verbo.cese { color: var(--tinta-3); }
.mov-verbo.autorizacion { color: var(--emp); }

.autorizaciones { margin-top: var(--e5); padding-top: var(--e3); border-top: 2px solid var(--filete); }
.autorizaciones h3 { font-size: var(--t-h3); margin: 0 0 var(--e2); }
.autorizaciones .nota { font-size: var(--t-s); margin: 0 0 var(--e3); max-width: var(--medida); }
.autorizaciones ul { list-style: none; margin: 0; padding: 0; }
.autorizacion { padding: var(--e3) 0; border-top: 1px solid var(--filete-suave); }
.autorizacion p { margin: 0; }
.actividad { font-family: var(--serif); font-size: var(--t-l); line-height: 1.35; color: var(--tinta); }
.autorizacion-meta { font-size: var(--t-s); color: var(--tinta-2); margin-top: 0.25rem !important; }
.autorizacion-empresa { font-size: var(--t-s); color: var(--tinta-2); margin-top: 0.3rem !important; }
.autorizacion-empresa a { color: var(--emp); font-weight: 600; }
.autorizacion .periodo-fuentes { margin-top: var(--e2) !important; }
.con-autorizacion { font-size: var(--t-xs); color: var(--emp); font-weight: 600; }
.con-declaracion { font-size: var(--t-xs); color: var(--tinta-2); font-weight: 600; }
.sector {
  display: inline-block; vertical-align: middle; margin-left: 0.4rem;
  font-family: var(--sans); font-size: var(--t-xs); font-weight: 600;
  letter-spacing: 0.02em; padding: 0 0.35rem; border-radius: 2px;
  border: 1px solid currentColor;
}
.sector.privado { color: var(--emp); }
.sector.publico { color: var(--adm); }
.papeles { display: flex; flex-wrap: wrap; gap: 0; margin: 0 0 var(--e2); }
.papel {
  font: inherit; font-size: var(--t-s); cursor: pointer;
  background: none; color: var(--tinta-2);
  border: 1px solid var(--filete); padding: 0.25rem 0.7rem;
}
.papel + .papel { margin-left: -1px; }
.papel[aria-pressed='true'] { background: var(--tinta); color: var(--papel); border-color: var(--tinta); position: relative; }
.papel:focus-visible { outline: 2px solid var(--tinta); outline-offset: 1px; }
.gobiernos-filtro { flex-wrap: wrap; }
.gobiernos-filtro .papel { font-size: var(--t-xs); }
.periodo-gobierno { font-size: var(--t-s); color: var(--tinta-2); margin-top: 0.2rem !important; }
.periodo-gobierno a { color: var(--tinta); }
.periodo-gobierno abbr { text-decoration: none; }
.gobierno-autorizacion { color: var(--tinta-2); }
.del-organo {
  font-size: var(--t-s); color: var(--tinta-2); margin-top: 0.35rem !important;
  padding-left: 0.6rem; border-left: 2px solid var(--adm);
}
.del-organo a { color: var(--adm); font-weight: 600; }
.del-organo strong { color: var(--tinta); font-variant-numeric: tabular-nums; }
.mov-texto { font-size: var(--t-s); line-height: 1.45; color: var(--tinta-2); margin: 0.2rem 0 0.35rem !important; }
.mov-texto a { color: var(--tinta); font-weight: 600; }

.lista { list-style: none; margin: 0; padding: 0; }
.lista li {
  display: flex; justify-content: space-between; gap: var(--e3); align-items: baseline;
  padding: 0.4rem 0; border-bottom: 1px solid var(--filete-suave); font-size: var(--t-s);
}
.lista a { color: var(--tinta); }
.cifra { font-variant-numeric: tabular-nums; font-weight: 650; }

.metodo { margin-top: var(--e8); padding-top: var(--e4); border-top: 3px double var(--filete); }
.metodo h2 { font-size: var(--t-h3); margin: 0 0 var(--e3); }
.metodo p {
  font-size: var(--t-s); color: var(--tinta-2); line-height: 1.6;
  max-width: var(--medida); margin: 0 0 var(--e3);
}

@media (max-width: 900px) {
  .primera, .rejilla { grid-template-columns: 1fr; }
}
@media (max-width: 600px) {
  .cargos { padding: var(--e5) var(--e4) var(--e7); }
  .ficha-cabeza { grid-template-columns: 1fr; }
  .ficha-cabeza .boton { justify-self: start; }
}
</style>
