<script setup>
/**
 * Mapa completo, agrupado por núcleos.
 *
 * Sustituye a la vista anterior, que dibujaba la ego-red de un solo nodo: eso
 * salía siempre como una estrella con los radios pisándose las etiquetas, y de
 * una estrella no se deduce ninguna estructura. Aquí se ve el mapa entero y los
 * grupos se distinguen por color.
 *
 * Tres decisiones que son las que lo hacen legible, y todas consisten en
 * dibujar MENOS:
 *
 * - **El color dice el núcleo, no el tipo.** El tipo se lee en el panel cuando
 *   te interesa una entidad concreta; el núcleo hay que verlo de lejos.
 * - **Casi ningún nodo lleva etiqueta.** Sólo los pesos pesados de cada núcleo.
 *   Cuatro mil etiquetas no son cuatro mil datos, son una mancha gris.
 * - **Las aristas van muy translúcidas.** De cerca son relaciones; de lejos son
 *   la textura que deja ver dónde se aprieta el grafo.
 */
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import Sigma from 'sigma'
import forceAtlas2 from 'graphology-layout-forceatlas2'
import { analizarNucleos, colapsarNodosDePaso, FONDO, paletaDeNucleos } from '../nucleos.js'
import { dibujarEtiquetaCentrada } from '../etiquetas.js'
import { COLOR_POR_DEFECTO, COLOR_POR_ESQUEMA } from '../esquemas.js'

const props = defineProps({
  datos: { type: Object, required: true },
  seleccion: { type: String, default: '' },
  nucleoEnfocado: { type: Number, default: null },
  minImporte: { type: Number, default: 0 },
  mostrarExpedientes: { type: Boolean, default: false },
  mostrarSueltos: { type: Boolean, default: false },
  soloExtranjero: { type: Boolean, default: false },
  soloPartidos: { type: Boolean, default: false },
})
const emit = defineEmits(['seleccionar', 'analizado'])

const contenedor = ref(null)
const calculando = ref(true)
let sigma = null
const grafo = shallowRef(null)
const etiquetados = shallowRef(new Set())
/** El nodo bajo el ratón: es lo que destapa sus pagos a otros núcleos. */
const encima = ref('')

/**
 * Los nombres oficiales son larguísimos —"Consejería de Sanidad, Presidencia y
 * Emergencias Secretaría General Técnica"— y una etiqueta así tapa media
 * pantalla. Se recorta para el mapa; el nombre entero está en el panel y al
 * pasar por encima.
 *
 * Corto, además, porque Sigma reparte las etiquetas por una rejilla y evita
 * que dos caigan en la misma celda, pero no comprueba si se solapan de
 * verdad: dos etiquetas de treinta y cuatro caracteres en celdas vecinas se
 * pisan igual. Estrechándolas caben donde antes se superponían.
 */
function recortar(texto, max = 24) {
  if (!texto || texto.length <= max) return texto ?? ''
  return `${texto.slice(0, max - 1).trimEnd()}…`
}

/**
 * Tamaño por dinero, no por número de conexiones: esto es un mapa de dinero.
 *
 * Los puntos medían de 8 a 26 px y los núcleos salían como manchas macizas:
 * sesenta círculos de veinte píxeles dentro del sitio que ocupa un núcleo se
 * funden en una sola forma. Lo que se veía era una ameba de color, no una
 * red, y la propia ameba engañaba con el tamaño —lo que se lee es el área de
 * la unión de los círculos, no el dinero—.
 *
 * Con este rango, de 3 a 14, se ven los puntos por separado y se ve por
 * dónde se tocan, que es lo que el mapa dice: quién está conectado con quién.
 */
function tamano(dinero, grado) {
  const base = 1.6 + Math.log10(1 + Math.max(0, dinero)) * 0.85
  return Math.min(14, base + Math.min(3, Math.sqrt(grado) * 0.55))
}

function construir() {
  calculando.value = true
  // Se puentean los expedientes ANTES de agrupar: si se quitaran después, los
  // núcleos se habrían calculado sobre un grafo con nodos de paso y saldrían
  // artificialmente troceados.
  const fuente = props.mostrarExpedientes ? props.datos : colapsarNodosDePaso(props.datos)
  const { grafo: g, nucleos, porNodo, totalDinero } = analizarNucleos(fuente)
  const nodosPorId = new Map((fuente?.nodes ?? []).map((n) => [n.id, n]))

  // Filtros: se aplican quitando nodos del grafo, no ocultándolos, para que el
  // layout no reserve sitio a lo que no se ve.
  // Set y no lista: un nodo puede caer por dos filtros a la vez y dropNode
  // revienta la segunda.
  const fuera = new Set()
  g.forEachNode((id, attrs) => {
    if (props.minImporte > 0 && attrs.dinero < props.minImporte) fuera.add(id)
  })

  /*
    Dentro de un grupo se dibuja SÓLO ese grupo.

    Antes el grupo enfocado se atenuaba y el resto seguía ahí, así que el
    dibujo era el mismo mapa de dos mil puntos con una mancha algo más viva en
    alguna esquina: no se veía mejor, se veía igual con menos luz. Quitando lo
    demás, el layout se calcula sobre cincuenta entidades, la cámara las
    encuadra y se leen los nombres. Que es lo que un diagrama de nodos sabe
    hacer, y sólo a ese tamaño.
  */
  const soloUnNucleo = props.nucleoEnfocado !== null
  if (soloUnNucleo) {
    g.forEachNode((id, attrs) => {
      if (attrs.nucleo !== props.nucleoEnfocado) fuera.add(id)
    })
  }

  /**
   * Filtros de «esto y su entorno inmediato».
   *
   * Se conserva la entidad marcada Y sus vecinos, que es la relación que
   * interesa: quedarse sólo con las marcadas deja nodos sueltos sin decir de
   * dónde les viene el dinero, y un nodo suelto no cuenta nada.
   */
  function soloEstasYSuEntorno(marca) {
    const marcadas = new Set(
      (fuente?.nodes ?? [])
        .filter(marca)
        .map((n) => n.id)
        .filter((id) => g.hasNode(id)),
    )
    const aSalvo = new Set(marcadas)
    for (const id of marcadas) for (const v of g.neighbors(id)) aSalvo.add(v)
    g.forEachNode((id) => {
      if (!aSalvo.has(id)) fuera.add(id)
    })
  }

  if (props.soloExtranjero) {
    soloEstasYSuEntorno(
      (n) => n.properties?.entidad_extranjera || n.properties?.entidad_extranjera_indicio,
    )
  }

  // Partidos y quien les paga: el mapa entero es una textura, pero recortado a
  // las formaciones políticas y sus pagadores se vuelve legible y contesta
  // directamente de dónde sale el dinero de los partidos.
  if (props.soloPartidos) {
    soloEstasYSuEntorno((n) => n.properties?.partido_politico)
  }
  for (const id of fuera) g.dropNode(id)
  // Un nodo que se queda sin aristas tras filtrar ya no cuenta nada.
  const sinAristas = g.filterNodes((id) => g.degree(id) === 0)
  for (const id of sinAristas) g.dropNode(id)

  // Los grupos de dos nodos no son núcleos: son una relación suelta, y hay
  // cientos. Amontonados llenan la pantalla de confeti y, peor, al repartir el
  // sitio empujan a los núcleos de verdad hacia el borde y dejan el centro
  // vacío. Se pueden volver a encender, pero no de entrada.
  if (!props.mostrarSueltos) {
    const cuenta = new Map()
    g.forEachNode((id, a) => cuenta.set(a.nucleo, (cuenta.get(a.nucleo) ?? 0) + 1))
    const fragmentos = g.filterNodes((id, a) => (cuenta.get(a.nucleo) ?? 0) < 3)
    for (const id of fragmentos) g.dropNode(id)
  }

  // El color sólo lo llevan los núcleos de cabeza, y es el mismo que su fila
  // en la lista de al lado. Ver `paletaDeNucleos`.
  //
  // Se reparte sobre la lista VISIBLE y no sobre la del análisis, y ése es el
  // detalle que importa: `recalcularVisible` reordena por el dinero que queda
  // después de los filtros, así que con las dos listas en órdenes distintos la
  // fila decía un color y su mancha en el mapa otro.
  const visible = recalcularVisible(g, nucleos)
  const color = paletaDeNucleos(visible.nucleos)

  // Etiqueta EXACTAMENTE los que llevan color, y en el mismo orden.
  //
  // Antes eran dieciocho, elegidas de otra lista: seis manchas grises salían
  // rotuladas y el ojo las leía como importantes, mientras que alguna de las
  // de color se quedaba muda. Color, etiqueta y fila de la lista señalan ahora
  // al mismo núcleo, que es lo que permite pasar del mapa a la lista y al
  // revés sin tener que adivinar nada.
  // `continue` y no `break`: la paleta salta los núcleos sin cuerpo —los de
  // menos de seis entidades, que la lista tampoco enseña—, así que en medio
  // de la lista hay grises. Cortando en el primero, los de color que venían
  // detrás se quedaban sin nombre.
  const conEtiqueta = new Set()
  if (soloUnNucleo) {
    /*
      Dentro de un grupo pequeño o mediano caben todos los nombres, y es el
      caso en el que un diagrama de nodos contesta algo —quién está conectado
      con quién—: sin nombres no contesta nada.

      Pero hay grupos de casi doscientas entidades, y ahí forzar los nombres
      devuelve el problema de antes a menor escala: ciento noventa y cinco
      rótulos pisándose. A partir del tope se fuerzan sólo las cabezas —las
      que salen listadas en el panel— y del resto se encarga el reparto por
      rejilla de Sigma, que enseña las que caben mientras se hace zoom.
    */
    const TOPE_TODOS = 45
    if (g.order <= TOPE_TODOS) {
      g.forEachNode((id) => conEtiqueta.add(id))
    } else {
      const suyo = visible.nucleos.find((n) => n.id === props.nucleoEnfocado)
      for (const m of suyo?.principales ?? []) if (g.hasNode(m.id)) conEtiqueta.add(m.id)
    }
  } else {
    for (const n of visible.nucleos) {
      if (color(n.id) === FONDO) continue
      const cabeza = n.principales.find((m) => g.hasNode(m.id))
      if (cabeza) conEtiqueta.add(cabeza.id)
    }
  }
  etiquetados.value = conEtiqueta

  g.forEachNode((id, attrs) => {
    g.mergeNodeAttributes(id, {
      label: conEtiqueta.has(id) ? recortar(attrs.label) : '',
      // Forzada: si el núcleo lleva color, lleva nombre, y no depende de que
      // su cabeza gane la celda de la rejilla de rótulos de Sigma. Con el
      // reparto automático salían con nombre cuatro de los siete de color y
      // los otros tres eran manchas mudas — y el color está precisamente
      // para poder ir de la mancha a su fila en la lista de al lado.
      forceLabel: conEtiqueta.has(id),
      etiquetaReal: attrs.label,
      // Dentro de un grupo, el color del grupo lo llevan todos y no distingue
      // nada; ahí vuelve a decir el tipo de entidad, que es lo que separa al
      // organismo que paga de las empresas que cobran.
      color: soloUnNucleo ? (COLOR_POR_ESQUEMA[attrs.esquema] ?? COLOR_POR_DEFECTO) : color(attrs.nucleo),
      extranjera: Boolean(nodosPorId.get(id)?.properties?.entidad_extranjera),
      size: tamano(attrs.dinero, attrs.grado),
      x: Math.random(),
      y: Math.random(),
    })
  })

  // Las aristas ENTRE núcleos, mucho más tenues que las de dentro.
  //
  // Los núcleos se colocan empaquetados por dinero, no por quién toca con
  // quién, así que una arista que cruza el lienzo entero no dice «estos dos
  // grupos están cerca»: sólo dice que existe un pago entre ellos. Pintadas
  // igual que las de dentro, esas líneas largas eran lo primero que se veía
  // —una maraña blanca por encima de todo— y tapaban justo lo que el mapa
  // quiere enseñar, que es la forma de cada grupo.
  //
  // No se esconden: un pago entre dos núcleos es un dato, y esconderlo diría
  // que no lo hay. Se dejan como textura de fondo.
  g.forEachEdge((e, attrs, _a, _b, orig, dest) => {
    const inferida = attrs.estado === 'inferred'
    const dentro = orig.nucleo === dest.nucleo
    const color = inferida
      ? `rgba(224,163,58,${dentro ? 0.26 : 0.1})`
      // Más tenues que antes porque ahora se ven. Con los puntos pequeños,
      // un organismo que paga a sesenta empresas dibuja un abanico de sesenta
      // rectas que salen del mismo sitio: apiladas a 0,18 se suman hasta el
      // blanco y el abanico tapa el núcleo entero. A 0,11 la forma se sigue
      // leyendo y no se come lo que hay debajo.
      // Dentro de un grupo la cámara acerca, así que la misma opacidad cubre
      // muchos más píxeles y la telaraña se come los puntos. Más tenue ahí.
      : `rgba(150,170,200,${dentro ? (soloUnNucleo ? 0.07 : 0.11) : 0.045})`
    const grosor = 0.35 + Math.min(2.2, Math.log10(1 + attrs.importe) * 0.4)
    g.mergeEdgeAttributes(e, { color, size: dentro ? grosor : Math.min(grosor, 0.6) })
  })

  if (g.order > 1) {
    forceAtlas2.assign(g, {
      iterations: g.order > 1500 ? 120 : 260,
      settings: {
        ...forceAtlas2.inferSettings(g),
        gravity: 0.8,
        scalingRatio: 18,
        outboundAttractionDistribution: true,
        barnesHutOptimize: g.order > 300,
      },
    })
    separarNucleos(g, aspectoDelLienzo())
  }

  grafo.value = g
  // El panel tiene que hablar del mapa que se está viendo, no del que habría
  // sin filtros. Con «Sólo partidos» puesto, la lista seguía encabezada por
  // núcleos enteros que el filtro había quitado de la pantalla: se leían
  // nombres y cifras que no estaban en ninguna parte del dibujo.
  emit('analizado', visible)
  calculando.value = false
}


/**
 * Reduce el análisis a lo que ha sobrevivido a los filtros.
 *
 * Los núcleos se calculan sobre el grafo entero a propósito —agrupar después
 * de filtrar daría grupos distintos cada vez que se toca una casilla, y la
 * estructura dejaría de ser comparable—, pero lo que se cuenta tiene que ser
 * lo que se ve.
 */
function recalcularVisible(g, nucleos) {
  const vivos = new Map()
  g.forEachNode((id, a) => {
    const c = a.nucleo ?? -1
    if (!vivos.has(c)) vivos.set(c, { tamano: 0, ids: new Set() })
    const v = vivos.get(c)
    v.tamano += 1
    v.ids.add(id)
  })

  const dinero = new Map()
  g.forEachEdge((_e, attrs, s, t) => {
    const cs = g.getNodeAttribute(s, 'nucleo')
    if (cs === g.getNodeAttribute(t, 'nucleo')) {
      dinero.set(cs, (dinero.get(cs) ?? 0) + attrs.importe)
    }
  })

  let totalDinero = 0
  g.forEachEdge((_e, attrs) => {
    totalDinero += attrs.importe
  })

  const visibles = nucleos
    .filter((n) => (vivos.get(n.id)?.tamano ?? 0) > 1)
    .map((n) => {
      const v = vivos.get(n.id)
      return {
        ...n,
        tamano: v.tamano,
        dinero: dinero.get(n.id) ?? 0,
        principales: n.principales.filter((m) => v.ids.has(m.id)),
        // Los recuentos por tipo también son del recorte.
        tipos: n.nodos.reduce((acc, id) => {
          if (!v.ids.has(id)) return acc
          const e = g.getNodeAttribute(id, 'esquema')
          acc[e] = (acc[e] ?? 0) + 1
          return acc
        }, {}),
      }
    })
    .sort((a, b) => b.dinero - a.dinero || b.tamano - a.tamano)

  const porNodo = new Map()
  g.forEachNode((id, attrs) => porNodo.set(id, attrs))

  return { nucleos: visibles, porNodo, totalDinero, visibles: g.order }
}

/**
 * Aparta los núcleos unos de otros sin deshacer su forma interna.
 *
 * ForceAtlas2 coloca bien *dentro* de cada grupo pero los amontona todos en un
 * disco, y entonces el color es lo único que distingue un núcleo de su vecino:
 * el ojo no ve grupos, ve confeti. La primera versión salió exactamente así.
 *
 * El apaño es el de siempre para esto: se deja que FA2 haga su trabajo, se
 * calcula el centro de cada núcleo, se reparten esos centros en una espiral y
 * se traslada cada núcleo en bloque. Como es una traslación, las posiciones
 * relativas dentro del núcleo se conservan intactas — se mueve el grupo, no se
 * recoloca a sus miembros.
 *
 * El radio de cada núcleo crece con su tamaño para que los grandes no se coman
 * a los pequeños, y la espiral (en vez de un círculo) evita que los muchos
 * núcleos diminutos se aplasten en el borde.
 */
/**
 * Cuánto más ancho que alto es el lienzo, acotado.
 *
 * El empaquetado hacía una región cuadrada y Sigma la encaja respetando la
 * proporción: en una pantalla de 16:9 eso deja casi la mitad del lienzo en
 * negro a izquierda y derecha. Dándole la proporción real, lo mismo se dibuja
 * con un 40 % más de píxeles.
 */
function aspectoDelLienzo() {
  const el = contenedor.value
  if (!el || !el.clientHeight) return 1
  return Math.min(2.6, Math.max(0.5, el.clientWidth / el.clientHeight))
}

function separarNucleos(g, aspecto = 1) {
  const acc = new Map()
  g.forEachNode((id, a) => {
    const c = a.nucleo ?? -1
    if (!acc.has(c)) acc.set(c, { x: 0, y: 0, n: 0, nodos: [], dinero: 0 })
    const v = acc.get(c)
    v.x += a.x
    v.y += a.y
    v.n += 1
    v.dinero += a.dinero
    v.nodos.push(id)
  })
  for (const v of acc.values()) {
    v.x /= v.n
    v.y /= v.n
  }
  for (const v of acc.values()) {
    let max = 0
    for (const id of v.nodos) {
      const a = g.getNodeAttributes(id)
      max = Math.max(max, Math.hypot(a.x - v.x, a.y - v.y))
    }
    v.radio = Math.max(max, 3)
  }

  // Empaquetado por filas, de más dinero a menos.
  //
  // Antes iba en espiral y salía un anillo con el centro vacío: el radio de
  // una espiral sólo puede crecer, así que con mil núcleos el primero queda
  // solo en el medio y los demás se van al borde. Se veía peor que sin
  // separar nada.
  //
  // Por filas no pasa: es dense, no deja huecos, y además ordena. El de
  // arriba a la izquierda es el que más dinero mueve, y eso ya es información
  // antes de tocar nada.
  const orden = [...acc.entries()].sort((a, b) => b[1].dinero - a[1].dinero || b[1].n - a[1].n)
  // Más aire entre núcleos del que pide el dibujo, porque el rótulo también
  // ocupa: los nombres se escriben centrados sobre la cabeza del grupo y se
  // salen de su mancha por los dos lados. Con 1,35 «Aena. Consejo de
  // Administración» se metía dentro del núcleo de al lado.
  const HUECO = 1.55
  const area = orden.reduce((s, [, v]) => s + (v.radio * 2 * HUECO) ** 2, 0)
  const anchoFila = Math.sqrt(area * aspecto) * 1.1

  const destino = new Map()
  let x = 0
  let y = 0
  let altoFila = 0
  for (const [c, v] of orden) {
    const d = v.radio * 2 * HUECO
    if (x > 0 && x + d > anchoFila) {
      x = 0
      y -= altoFila
      altoFila = 0
    }
    destino.set(c, { x: x + d / 2, y: y - d / 2 })
    x += d
    altoFila = Math.max(altoFila, d)
  }

  g.forEachNode((id, a) => {
    const c = a.nucleo ?? -1
    const origen = acc.get(c)
    const fin = destino.get(c)
    if (!origen || !fin) return
    g.mergeNodeAttributes(id, { x: a.x - origen.x + fin.x, y: a.y - origen.y + fin.y })
  })
}

function pintar() {
  if (!contenedor.value) return
  if (sigma) {
    sigma.kill()
    sigma = null
  }
  construir()
  if (!grafo.value || grafo.value.order === 0) return

  sigma = new Sigma(grafo.value, contenedor.value, {
    renderEdgeLabels: false,
    defaultEdgeType: 'line',
    // Sin la maraña de rectas cruzando el lienzo, los núcleos quedan
    // separados de verdad y caben más rótulos: con celdas de 220 px sólo
    // salían tres de los doce con color, y una mancha de color sin nombre no
    // sirve para llegar a la lista de al lado.
    labelDensity: 0.6,
    labelGridCellSize: 155,
    // El umbral es de tamaño DIBUJADO, así que va atado al rango de `tamano`.
    // Al bajar los puntos de 8-26 px a 3-14, un umbral de 11 dejaba mudos la
    // mitad de los núcleos de color: el de Aena, el de Metro de Madrid y dos
    // más salían pintados y sin nombre, que es justo lo que no puede pasar
    // —el color existe para poder saltar del mapa a la lista de al lado—.
    labelRenderedSizeThreshold: 8,
    labelFont: 'system-ui, sans-serif',
    labelColor: { color: '#f2f5fa' },
    labelSize: 12,
    labelWeight: '600',
    // Sigma dibuja el texto a pelo. Encima de una mancha de color claro
    // —verde, amarillo, turquesa— el blanco no se lee, y encima de dos manchas
    // que se tocan, menos. Con una placa oscura detrás se lee siempre, sobre
    // lo que sea, que es lo que tiene que pasar con el nombre de un organismo.
    defaultDrawNodeLabel: dibujarEtiquetaCentrada,
    // El nodo resaltado usa OTRO pintor, el de hover, que por defecto dibuja
    // una placa blanca con texto oscuro. Al cambiar sólo el de la etiqueta,
    // encima de esa placa blanca se escribía el texto claro del nuestro y el
    // nombre del nodo seleccionado desaparecía: un rectángulo blanco vacío en
    // el centro del grafo. Los dos pintan igual.
    defaultDrawNodeHover: dibujarEtiquetaCentrada,
    minCameraRatio: 0.03,
    maxCameraRatio: 12,
    zIndex: true,
  })

  sigma.on('clickNode', ({ node }) => emit('seleccionar', node))
  sigma.on('enterNode', ({ node }) => {
    encima.value = node
    // La etiqueta aparece al pasar por encima aunque el nodo no sea de los
    // rotulados: así se puede explorar sin llenar la pantalla de texto.
    sigma.setSetting('nodeReducer', (id, d) =>
      id === node ? { ...d, label: d.etiquetaReal, highlighted: true, zIndex: 3 } : reducirNodo(id, d),
    )
    sigma.setSetting('edgeReducer', reducirArista)
    sigma.refresh()
  })
  sigma.on('leaveNode', () => {
    encima.value = ''
    aplicarReductores()
  })

  aplicarReductores()
}

function reducirNodo(id, d) {
  const g = grafo.value
  const foco = props.seleccion
  const nuc = props.nucleoEnfocado

  if (nuc !== null && g.getNodeAttribute(id, 'nucleo') !== nuc) {
    return { ...d, color: 'rgba(120,126,140,0.18)', label: '', zIndex: 0 }
  }
  if (foco && g.hasNode(foco)) {
    if (id === foco) return { ...d, label: d.etiquetaReal, highlighted: true, zIndex: 3 }
    if (g.areNeighbors(foco, id)) return { ...d, label: d.etiquetaReal, zIndex: 2 }
    return { ...d, color: 'rgba(120,126,140,0.15)', label: '', zIndex: 0 }
  }
  return d
}

/**
 * Las aristas ENTRE núcleos no se dibujan en la vista general.
 *
 * Los núcleos se empaquetan por dinero, no por quién toca con quién, así que
 * una arista entre dos de ellos sale como una recta que cruza el lienzo
 * entero: es larga porque la colocación no refleja la conexión, no porque los
 * dos grupos estén lejos en ningún sentido. Mil rectas así son lo primero que
 * se ve —una maraña blanca por encima de todo— y tapan lo único que este mapa
 * sabe enseñar, que es la forma de cada grupo.
 *
 * No se esconde el dato: aparece al pasar por encima de cualquiera de sus dos
 * extremos, y la leyenda lo dice. Lo que se quita es pintar mil a la vez
 * cuando no se ha preguntado por ninguna.
 */
function reducirArista(id, d) {
  const g = grafo.value
  const foco = props.seleccion
  const nuc = props.nucleoEnfocado
  const [s, t] = g.extremities(id)
  const entreNucleos = g.getNodeAttribute(s, 'nucleo') !== g.getNodeAttribute(t, 'nucleo')
  const tocaAlDeEncima = encima.value && (s === encima.value || t === encima.value)

  if (tocaAlDeEncima) {
    return { ...d, color: 'rgba(210,225,245,0.55)', size: Math.max(d.size, 1), zIndex: 2 }
  }
  if (entreNucleos && !foco && nuc === null) return { ...d, hidden: true }

  if (nuc !== null) {
    const dentro = g.getNodeAttribute(s, 'nucleo') === nuc && g.getNodeAttribute(t, 'nucleo') === nuc
    if (!dentro) return { ...d, color: 'rgba(120,126,140,0.05)', zIndex: 0 }
  }
  if (foco && g.hasNode(foco)) {
    if (s === foco || t === foco) return { ...d, color: 'rgba(210,225,245,0.55)', size: d.size * 1.6, zIndex: 2 }
    return { ...d, color: 'rgba(120,126,140,0.05)', zIndex: 0 }
  }
  return d
}

function aplicarReductores() {
  if (!sigma || !grafo.value) return
  sigma.setSetting('nodeReducer', reducirNodo)
  sigma.setSetting('edgeReducer', reducirArista)
  sigma.refresh()
}

/** Centra la cámara en un núcleo concreto. */
function enfocarNucleo(idNucleo) {
  if (!sigma || !grafo.value || idNucleo === null) return
  const g = grafo.value
  const puntos = g.filterNodes((id) => g.getNodeAttribute(id, 'nucleo') === idNucleo)
  if (!puntos.length) return
  const xs = puntos.map((p) => g.getNodeAttribute(p, 'x'))
  const ys = puntos.map((p) => g.getNodeAttribute(p, 'y'))
  const cx = xs.reduce((a, b) => a + b, 0) / xs.length
  const cy = ys.reduce((a, b) => a + b, 0) / ys.length
  const pos = sigma.graphToViewport({ x: cx, y: cy })
  const { x, y } = sigma.viewportToFramedGraph(pos)
  sigma.getCamera().animate({ x, y, ratio: 0.35 }, { duration: 500 })
}

const hayAlgo = computed(() => (props.datos?.nodes?.length ?? 0) > 0)

onMounted(pintar)
watch(() => props.datos, pintar)
watch(
  () => [
    props.minImporte,
    props.mostrarExpedientes,
    props.mostrarSueltos,
    props.soloExtranjero,
    props.soloPartidos,
  ],
  pintar,
)
watch(() => props.seleccion, aplicarReductores)
watch(
  () => props.nucleoEnfocado,
  (n) => {
    aplicarReductores()
    enfocarNucleo(n)
  },
)

onBeforeUnmount(() => {
  if (sigma) sigma.kill()
})

defineExpose({ enfocarNucleo })
</script>

<template>
  <div class="mapa">
    <div ref="contenedor" class="lienzo" />
    <p v-if="calculando" class="aviso">Buscando núcleos…</p>
    <p v-else-if="!hayAlgo" class="aviso">No hay datos que dibujar.</p>
  </div>
</template>

<style scoped>
.mapa {
  position: relative;
  width: 100%;
  height: 100%;
}
.lienzo {
  width: 100%;
  height: 100%;
  background: var(--fondo-grafo);
}
.aviso {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  margin: 0;
  color: var(--texto-tenue);
  pointer-events: none;
}
</style>
