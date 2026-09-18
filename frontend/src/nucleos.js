/**
 * Detección de núcleos de financiación.
 *
 * La pregunta que el mapa tiene que contestar no es "¿quién está conectado con
 * quién?" —eso es una maraña— sino "¿qué grupos de organismos, empresas y
 * partidos se mueven juntos, y cuánto dinero circula dentro de cada uno?".
 *
 * Eso es detección de comunidades, y aquí se hace con Louvain **pesando las
 * aristas por importe**. Pesar por importe y no por número de conexiones es
 * deliberado: un organismo con mil subvenciones de 200 € pesa menos que uno con
 * tres contratos de diez millones, y para un mapa de dinero eso es lo correcto.
 *
 * Nada de esto afirma nada sobre nadie. Un núcleo es una observación sobre la
 * *forma del grafo*: estas entidades están más conectadas entre sí que con el
 * resto. No dice que haya trama, ni connivencia, ni irregularidad. La interfaz
 * tiene que decirlo con esas palabras, porque es justo el malentendido que un
 * mapa así invita a cometer (spec §12).
 */

import Graph from 'graphology'
import louvain from 'graphology-communities-louvain'

/** Los importes viajan como texto para no perder precisión. Aquí sí hace falta número. */
export function aNumero(valor) {
  if (valor === null || valor === undefined || valor === '') return 0
  const n = Number(valor)
  return Number.isFinite(n) ? n : 0
}

/**
 * Peso de una arista para el agrupamiento.
 *
 * Logarítmico porque los importes públicos abarcan de decenas de euros a
 * cientos de millones: en lineal, tres contratos enormes decidirían el mapa
 * entero y el resto sería polvo. El +1 evita log(0) y deja un peso mínimo a las
 * aristas sin importe, que siguen siendo una relación aunque no lleven cifra.
 */
export function peso(importe) {
  return 1 + Math.log10(1 + Math.max(0, aNumero(importe)))
}

/**
 * Colapsa los nodos de paso, conservando el camino.
 *
 * Un expediente de contratación no es un actor: es el papel que une al órgano
 * que adjudica con la empresa que cobra. Dibujarlo duplica la longitud de todo
 * camino —organismo → contrato → empresa— y llena el mapa de nodos que no
 * responden a ninguna pregunta.
 *
 * Pero *esconderlo* sin más rompe el grafo: los dos extremos se quedan sin
 * camino entre ellos. Se vio al estrenar el filtro de capital extranjero, que
 * devolvía cero entidades — las 19 empresas no residentes cuelgan justamente
 * de expedientes.
 *
 * Así que se puentea: se une a los vecinos del nodo de paso entre sí y luego se
 * quita. El dinero de la arista nueva es el mayor de los dos tramos, nunca la
 * suma: el órgano no pagó dos veces, es el mismo dinero visto por sus dos
 * lados, y sumarlo duplicaría el total del mapa.
 */
export function colapsarNodosDePaso(datos, esquema = 'Contract') {
  const nodes = datos?.nodes ?? []
  const edges = datos?.edges ?? []
  const dePaso = new Set(nodes.filter((n) => n.schema === esquema).map((n) => n.id))
  if (!dePaso.size) return { ...datos, nodes, edges }

  // La DIRECCIÓN importa, y la primera versión la ignoraba: unía entre sí a
  // todos los vecinos del expediente, así que un contrato con tres
  // adjudicatarios generaba tres aristas repitiendo el importe y el dinero del
  // mapa se disparó de 17 a 119 millones. Dos adjudicatarios del mismo
  // contrato no se pagan el uno al otro.
  //
  // Lo correcto es unir quien ENTRA al expediente —el órgano que adjudica—
  // con quien SALE de él —cada adjudicatario—, y nada más.
  const entrantes = new Map()
  const salientes = new Map()
  for (const a of edges) {
    if (dePaso.has(a.target) && !dePaso.has(a.source)) {
      if (!entrantes.has(a.target)) entrantes.set(a.target, [])
      entrantes.get(a.target).push(a)
    }
    if (dePaso.has(a.source) && !dePaso.has(a.target)) {
      if (!salientes.has(a.source)) salientes.set(a.source, [])
      salientes.get(a.source).push(a)
    }
  }

  const salida = edges.filter((a) => !dePaso.has(a.source) && !dePaso.has(a.target))
  for (const paso of dePaso) {
    for (const dentro of entrantes.get(paso) ?? []) {
      for (const fuera of salientes.get(paso) ?? []) {
        salida.push({
          id: `puente:${paso}:${dentro.source}:${fuera.target}`,
          source: dentro.source,
          target: fuera.target,
          // El importe es el del tramo que lleva el dinero de verdad: lo que
          // cobró el adjudicatario. El tramo de entrada no lleva cifra
          // justamente para no contarlo dos veces.
          amount: fuera.amount ?? dentro.amount ?? '',
          schema: fuera.schema ?? dentro.schema,
          // La confianza de un camino no puede ser mayor que la del tramo más
          // flojo por el que pasa.
          confidence: Math.min(dentro.confidence ?? 1, fuera.confidence ?? 1),
          status:
            dentro.status === 'inferred' || fuera.status === 'inferred' ? 'inferred' : 'asserted',
          viaDePaso: paso,
        })
      }
    }
  }

  return { ...datos, nodes: nodes.filter((n) => !dePaso.has(n.id)), edges: salida }
}

const TIPOS_CABECERA = ['PublicBody', 'Organization', 'Company', 'LegalEntity']

/**
 * Construye el grafo, detecta núcleos y resume cada uno.
 *
 * Devuelve `{ grafo, nucleos, porNodo, totalDinero }`. `nucleos` va ordenado
 * por dinero descendente: lo primero que se ve es donde más dinero hay.
 */
export function analizarNucleos(datos, { resolucion = 1 } = {}) {
  const grafo = new Graph({ multi: false, type: 'undirected' })

  const nodosPorId = new Map()
  for (const n of datos?.nodes ?? []) {
    if (grafo.hasNode(n.id)) continue
    nodosPorId.set(n.id, n)
    grafo.addNode(n.id, {
      label: n.caption,
      esquema: n.schema,
      dinero: 0,
      grado: 0,
    })
  }

  for (const a of datos?.edges ?? []) {
    if (!grafo.hasNode(a.source) || !grafo.hasNode(a.target)) continue
    if (a.source === a.target) continue
    const importe = aNumero(a.amount)
    if (grafo.hasEdge(a.source, a.target)) {
      // Dos relaciones entre los mismos dos nodos suman dinero; el grafo se
      // mantiene simple para que el agrupamiento no cuente la misma pareja dos
      // veces.
      const e = grafo.edge(a.source, a.target)
      grafo.setEdgeAttribute(e, 'importe', grafo.getEdgeAttribute(e, 'importe') + importe)
      grafo.setEdgeAttribute(e, 'weight', peso(grafo.getEdgeAttribute(e, 'importe')))
      grafo.setEdgeAttribute(e, 'n', grafo.getEdgeAttribute(e, 'n') + 1)
    } else {
      grafo.addEdge(a.source, a.target, {
        importe,
        weight: peso(importe),
        n: 1,
        esquema: a.schema,
        confianza: a.confidence ?? 1,
        estado: a.status ?? 'asserted',
      })
    }
    for (const extremo of [a.source, a.target]) {
      grafo.setNodeAttribute(extremo, 'dinero', grafo.getNodeAttribute(extremo, 'dinero') + importe)
    }
  }

  grafo.forEachNode((id) => grafo.setNodeAttribute(id, 'grado', grafo.degree(id)))

  // Louvain necesita al menos una arista; con un grafo sin aristas devuelve
  // cada nodo en su propia comunidad, que es lo correcto pero conviene no
  // llamarlo siquiera.
  if (grafo.size > 0) {
    louvain.assign(grafo, { nodeCommunityAttribute: 'nucleo', resolution: resolucion, weighted: true })
  } else {
    grafo.forEachNode((id, attrs) => grafo.setNodeAttribute(id, 'nucleo', attrs.grado === 0 ? -1 : 0))
  }

  const porNucleo = new Map()
  grafo.forEachNode((id, attrs) => {
    const c = attrs.nucleo ?? -1
    if (!porNucleo.has(c)) porNucleo.set(c, { id: c, nodos: [], dinero: 0, tipos: {} })
    const n = porNucleo.get(c)
    n.nodos.push(id)
    n.tipos[attrs.esquema] = (n.tipos[attrs.esquema] ?? 0) + 1
  })

  // El dinero de un núcleo es el de sus aristas internas. Las que salen fuera
  // pertenecen a la frontera y contarlas aquí inflaría los dos lados.
  grafo.forEachEdge((e, attrs, s, t) => {
    const cs = grafo.getNodeAttribute(s, 'nucleo')
    const ct = grafo.getNodeAttribute(t, 'nucleo')
    if (cs === ct && porNucleo.has(cs)) porNucleo.get(cs).dinero += attrs.importe
  })

  const nucleos = [...porNucleo.values()]
    .map((n) => {
      const miembros = n.nodos
        .map((id) => ({ id, ...grafo.getNodeAttributes(id), caption: nodosPorId.get(id)?.caption }))
        .sort((a, b) => b.dinero - a.dinero || b.grado - a.grado)
      return {
        ...n,
        tamano: n.nodos.length,
        principales: miembros.slice(0, 8),
        etiqueta: etiquetaDe(miembros),
      }
    })
    // Un solo nodo no es un núcleo, es un nodo.
    .filter((n) => n.tamano > 1)
    .sort((a, b) => b.dinero - a.dinero || b.tamano - a.tamano)

  const porNodo = new Map()
  grafo.forEachNode((id, attrs) => porNodo.set(id, attrs))

  let totalDinero = 0
  grafo.forEachEdge((_e, attrs) => {
    totalDinero += attrs.importe
  })

  return { grafo, nucleos, porNodo, totalDinero }
}

/**
 * Nombra el núcleo por su actor más pesado, prefiriendo quien reparte el
 * dinero: un núcleo se entiende antes por "Ayuntamiento de X" que por la
 * empresa que más cobró.
 */
export function etiquetaDe(miembros) {
  if (!miembros.length) return 'Núcleo'
  for (const tipo of TIPOS_CABECERA) {
    const c = miembros.find((m) => m.esquema === tipo)
    if (c?.caption) return c.caption
  }
  return miembros[0].caption ?? 'Núcleo'
}

/** Paleta estable: el mismo núcleo mantiene su color entre repintados. */
const PALETA = [
  '#e8703a', '#3d8bd4', '#c94f7c', '#4bb47f', '#d9b04b',
  '#b08cd9', '#5ec8c0', '#e0685f', '#7f9bd1', '#9fc45a',
  '#d98cb0', '#69a5a0',
]

export function colorNucleo(idNucleo) {
  if (idNucleo === undefined || idNucleo === null || idNucleo < 0) return '#6b7280'
  return PALETA[idNucleo % PALETA.length]
}

/** Formato de dinero legible: 12.400.000 € se lee peor que 12,4 M €. */
export function dineroCorto(v) {
  const n = aNumero(v)
  if (n >= 1e9) return `${(n / 1e9).toFixed(1).replace('.', ',')} MM €`
  if (n >= 1e6) return `${(n / 1e6).toFixed(1).replace('.', ',')} M €`
  if (n >= 1e3) return `${Math.round(n / 1e3)} mil €`
  return `${Math.round(n)} €`
}
