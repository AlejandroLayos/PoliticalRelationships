/**
 * La red de poder: personas con cargo y las entidades con las que una fuente
 * oficial las une.
 *
 * Es la vista que responde a «¿con quién está conectado?» mirando a las
 * personas y no sólo al dinero. Se construye entera en el navegador a partir
 * de dos ficheros que ya se publican —`cargos.json` y `grafo.json`— y no
 * añade ningún hecho nuevo: cada arista es un hecho que ya sale en la ficha de
 * cargos o en el mapa del dinero, con la fuente que lo afirma y el enlace al
 * documento. Lo que cambia es la forma de mirarlo.
 *
 * ## Lo que NO hace, a propósito (spec §12)
 *
 * - No une personas entre sí. «Coincidieron en el mismo ministerio» no es una
 *   relación afirmada por nadie; lo es «fue nombrada en ese ministerio». Dos
 *   personas pueden aparecer cerca en el dibujo porque comparten un nodo, y
 *   la vista dice por qué: el nodo que comparten.
 * - No deduce partidos. La formación de una persona sale sólo de su escaño en
 *   el Congreso; que la nombrara un Gobierno de tal partido se dice como lo
 *   que es —«nombramiento durante el Gobierno de X»—, no como militancia.
 * - No completa nombres de organismos. El ministerio del BOE y el de la OCI
 *   se unen sólo si son el mismo nombre con «Ministerio de» delante; si no,
 *   son dos nodos.
 *
 * ## Forma
 *
 * `construirRed` devuelve `{ nodos: Map, aristas: Array, porNodo: Map }`. Cada
 * arista une DOS nodos por UNA relación y guarda todos los hechos que la
 * sostienen (`hechos`): tres cargos en el mismo ministerio son una arista con
 * tres hechos, no tres aristas encima unas de otras.
 */

import { empiezaPalabra, normaliza } from './buscador.js'
import { aNumero, colapsarNodosDePaso, dineroCorto } from './nucleos.js'

/** Cuántas contrapartes de dinero, como mucho, se traen del mapa por cada entidad de la red. */
export const DINERO_POR_NODO = 5

/** Los tipos de nodo, y cómo se dicen. */
export const TIPOS = {
  persona: { nombre: 'Persona con cargo público', plural: 'Personas' },
  gobierno: { nombre: 'Gobierno', plural: 'Gobiernos' },
  organismo: { nombre: 'Ministerio u organismo', plural: 'Ministerios y organismos' },
  partido: { nombre: 'Partido', plural: 'Partidos' },
  entidad: { nombre: 'Entidad del mapa del dinero', plural: 'Entidades' },
}

/**
 * Las relaciones. `ida` es cómo se lee desde el origen (la persona, casi
 * siempre); `vuelta`, desde el destino. Sin género: «Autorización para
 * trabajar en», no «autorizado a».
 */
export const RELACIONES = {
  preside: { ida: 'Presidió', vuelta: 'Presidencia' },
  propuesta: { ida: 'A propuesta de', vuelta: 'Propuso para el cargo' },
  nombramiento: { ida: 'Nombramientos durante el', vuelta: 'Nombramientos en el BOE' },
  cargo: { ida: 'Cargos en', vuelta: 'Personas con cargo aquí' },
  escano: { ida: 'Escaño por', vuelta: 'Escaños en el Congreso' },
  dirigio: { ida: 'Al frente de', vuelta: 'Al frente, según el BOE o la OCI' },
  autorizacion: {
    ida: 'Autorización para trabajar en',
    vuelta: 'Ex altos cargos autorizados a trabajar aquí',
  },
  declaracion: { ida: 'Actividad declarada en', vuelta: 'Diputados que declararon actividad aquí' },
  ministerio: { ida: 'Ministerios y organismos con nombramientos', vuelta: 'Gobiernos con nombramientos aquí' },
  dinero: { ida: 'Pagó o adjudicó a', vuelta: 'Cobró de' },
  accionista: { ida: 'Accionista significativo de', vuelta: 'Accionistas significativos' },
}

/** El orden en que se enseñan los grupos de conexiones en el panel. */
const ORDEN_RELACION = [
  'preside',
  'propuesta',
  'autorizacion',
  'dirigio',
  'declaracion',
  'escano',
  'cargo',
  'nombramiento',
  'ministerio',
  'accionista',
  'dinero',
]

const NOMBRE_FUENTE = {
  boe: 'BOE',
  oci: 'Oficina de Conflictos de Intereses',
  congreso: 'Congreso de los Diputados',
  cnmv: 'CNMV',
  mapa: 'Mapa del dinero',
}

export function nombreDeFuente(f) {
  return NOMBRE_FUENTE[f] ?? f ?? ''
}

/** «ECONOMÍA Y COMPETITIVIDAD» → «Economía y competitividad». No añade palabras. */
export function capitalizar(texto) {
  const t = (texto ?? '').trim()
  if (!t) return ''
  if (t !== t.toUpperCase()) return t
  const bajo = t.toLocaleLowerCase('es')
  return bajo.charAt(0).toLocaleUpperCase('es') + bajo.slice(1)
}

/*
  La forma jurídica por la letra del NIF.

  Es una regla oficial (Orden EHA/451/2008), no una suposición sobre el nombre:
  la A es una sociedad anónima, la Q un organismo público. Sirve para decir qué
  es cada entidad y pintarla con el color de su clase —lo público en teja, lo
  privado en azul, asociaciones y partidos en verde— sin tener que buscarla en
  el mapa del dinero, que en la instantánea va recortado.
*/
const FORMA_POR_LETRA = {
  A: ['Sociedad anónima', 'emp'],
  B: ['Sociedad limitada', 'emp'],
  C: ['Sociedad colectiva', 'emp'],
  D: ['Sociedad comanditaria', 'emp'],
  E: ['Comunidad de bienes', 'emp'],
  F: ['Cooperativa', 'emp'],
  G: ['Asociación o fundación', 'par'],
  H: ['Comunidad de propietarios', 'emp'],
  J: ['Sociedad civil', 'emp'],
  N: ['Entidad extranjera', 'emp'],
  P: ['Corporación local', 'adm'],
  Q: ['Organismo público', 'adm'],
  R: ['Congregación o institución religiosa', 'par'],
  S: ['Órgano de la Administración', 'adm'],
  U: ['Unión temporal de empresas', 'emp'],
  V: ['Otra entidad', 'neutro'],
  W: ['Establecimiento de entidad no residente', 'emp'],
}

/** `{forma, clase}` de una clave `nif:…`, o null si no es un NIF de entidad. */
export function formaDeNif(clave) {
  const m = /^nif:([A-Z])/.exec(clave ?? '')
  const f = m ? FORMA_POR_LETRA[m[1]] : null
  return f ? { forma: f[0], clase: f[1] } : null
}

const PARTICULAS = new Set(['de', 'del', 'la', 'las', 'los', 'y', 'i', 'e', 'da', 'do', 'dos', 'van', 'von', 'al'])

/**
 * «KHALID THANI ABDULLAH AL THANI» → «Khalid Thani Abdullah al Thani». Sólo
 * para mostrar el nombre de una persona que la fuente escribe en mayúsculas;
 * lo que ya trae minúsculas se deja como viene.
 */
export function nombreLegible(nombre) {
  const t = (nombre ?? '').trim()
  if (!t || t !== t.toUpperCase()) return t
  return t
    .toLocaleLowerCase('es')
    .split(/\s+/)
    .map((palabra, i) =>
      i > 0 && PARTICULAS.has(palabra)
        ? palabra
        : palabra.replace(/(^|[-'’])(\p{L})/gu, (_, sep, letra) => sep + letra.toLocaleUpperCase('es')),
    )
    .join(' ')
}

/** La clave de un organismo del BOE por su nombre. */
function claveOrganismo(nombre) {
  return `organismo:${normaliza(nombre).replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')}`
}

/**
 * Cuánto pesa un cargo para decidir qué personas se dibujan cuando no caben
 * todas. No es un juicio sobre nadie: es el orden del BOE (ministro,
 * secretario de Estado, subsecretario, director general).
 */
export function rangoDeCargo(cargo) {
  const c = normaliza(cargo)
  if (/^president[ae] del gobierno/.test(c)) return 8
  if (/^vicepresident[ae]/.test(c)) return 7
  if (/^ministr[ao]/.test(c)) return 6
  if (/^secretari[ao] de estado/.test(c)) return 4
  if (/^(subsecretari[ao]|secretari[ao] general)/.test(c)) return 3
  if (/^director[a]? general/.test(c) || /^d\. gral/.test(c)) return 2
  return 1
}

/**
 * Construye la red a partir de `cargos.json` y, si está, del grafo del dinero.
 *
 * @param {object} cargos el fichero de cargos públicos.
 * @param {{nodes: Array, edges: Array}|null} grafo el de la instantánea.
 */
export function construirRed(cargos, grafo = null) {
  const nodos = new Map()
  const aristas = new Map()
  const formaciones = cargos?.formaciones ?? {}

  function nodo(id, datos) {
    if (!nodos.has(id)) nodos.set(id, { id, ...datos })
    return nodos.get(id)
  }

  function unir(origen, destino, relacion, hecho) {
    if (!origen || !destino || origen === destino) return
    const id = `${relacion}|${origen}|${destino}`
    if (!aristas.has(id)) aristas.set(id, { id, source: origen, target: destino, relacion, hechos: [] })
    const a = aristas.get(id)
    // El mismo hecho dos veces —un periodo que llega por dos fuentes unidas—
    // se cuenta una.
    const firma = `${hecho.texto}|${hecho.desde ?? ''}|${hecho.hasta ?? ''}|${hecho.url ?? ''}`
    if (!a.hechos.some((h) => h.firma === firma)) a.hechos.push({ ...hecho, firma })
  }

  /** El nodo de un partido: la entidad del mapa si el puente la da, o sus siglas. */
  function nodoPartido(sigla) {
    const f = formaciones[sigla]
    const entidad = f?.entidad
    const id = entidad?.clave ?? `partido:${sigla}`
    const n = nodo(id, { tipo: 'partido', nombre: sigla, largo: f?.nombre ?? '', siglas: [] })
    if (!n.siglas.includes(sigla)) n.siglas.push(sigla)
    if (entidad?.clave) n.entidad = entidad.clave
    return n
  }

  function nodoEntidad(e) {
    if (!e?.clave) return null
    const f = formaDeNif(e.clave)
    return nodo(e.clave, {
      tipo: 'entidad',
      nombre: e.nombre ?? e.clave,
      entidad: e.clave,
      ...(f ? { forma: f.forma, clase: f.clase } : {}),
    })
  }

  // Los gobiernos: uno por presidente, con sus periodos.
  const presidentes = new Map()
  for (const p of cargos?.presidencias ?? []) {
    if (!p?.persona) continue
    const x = presidentes.get(p.persona) ?? { nombre: p.nombre, formacion: p.formacion, periodos: [] }
    x.periodos.push({ desde: p.desde ?? null, hasta: p.hasta ?? null })
    if (p.formacion) x.formacion = p.formacion
    presidentes.set(p.persona, x)
  }
  function nodoGobierno(g) {
    const id = `gobierno:${g.persona}`
    return nodo(id, {
      tipo: 'gobierno',
      nombre: `Gobierno de ${g.nombre}`,
      presidente: g.persona,
      formacion: g.formacion ?? presidentes.get(g.persona)?.formacion ?? '',
    })
  }

  // Los ministerios del BOE, por nombre normalizado, para que la OCI se una
  // a ellos sólo cuando es el mismo nombre.
  const organismosBoe = new Map()
  for (const persona of cargos?.personas ?? []) {
    for (const p of persona.periodos ?? []) {
      if ((p.fuente ?? 'boe') === 'boe' && p.organismo) organismosBoe.set(normaliza(p.organismo), p.organismo)
    }
  }
  function nodoOrganismo(nombre, fuente) {
    let oficial = nombre
    if (fuente === 'oci') {
      oficial = organismosBoe.get(normaliza(`Ministerio de ${nombre}`)) ?? organismosBoe.get(normaliza(nombre)) ?? null
      if (!oficial) return nodo(claveOrganismo(`oci ${nombre}`), { tipo: 'organismo', nombre: capitalizar(nombre) })
    }
    return nodo(claveOrganismo(oficial), { tipo: 'organismo', nombre: oficial })
  }

  // Cuántos nombramientos hizo cada Gobierno en cada organismo.
  const gobiernoOrganismo = new Map()

  for (const persona of cargos?.personas ?? []) {
    if (!persona?.clave) continue
    const periodos = persona.periodos ?? []
    const mejor = periodos.reduce((m, p) => Math.max(m, rangoDeCargo(p.cargo ?? p.puesto)), 0)
    const ultimo = [...periodos].sort((a, b) =>
      (b.desde ?? b.hasta ?? '').localeCompare(a.desde ?? a.hasta ?? ''),
    )[0]
    nodo(persona.clave, {
      tipo: 'persona',
      nombre: persona.nombre,
      rango: mejor,
      cargo: ultimo?.cargo ?? ultimo?.puesto ?? '',
    })

    for (const p of periodos) {
      const fuente = p.fuente ?? 'boe'
      const url = p.urlDesde || p.urlHasta || ''
      const base = { desde: p.desde ?? null, hasta: p.hasta ?? null, fuente, url }
      if (fuente === 'congreso') {
        if (!p.formacion) continue
        const partido = nodoPartido(p.formacion)
        const donde = [p.grupo, p.circunscripcion].filter(Boolean).join(' · ')
        unir(persona.clave, partido.id, 'escano', {
          ...base,
          texto: `${p.cargo ?? p.puesto}${donde ? ` (${donde})` : ''}`,
        })
        continue
      }
      const cargo = p.cargo ?? p.puesto ?? ''
      if (p.organismo) {
        const org = nodoOrganismo(p.organismo, fuente)
        unir(persona.clave, org.id, 'cargo', { ...base, texto: cargo })
        if (p.gobierno?.persona && p.desde) {
          const g = nodoGobierno(p.gobierno)
          const k = `${g.id}|${org.id}`
          gobiernoOrganismo.set(k, (gobiernoOrganismo.get(k) ?? 0) + 1)
        }
      }
      // Quién propuso a una alta instancia judicial, según el Real Decreto.
      // Si fue el Gobierno, la arista va a ese Gobierno y no es un
      // «nombramiento durante»: es una propuesta suya.
      const propuestaDelGobierno = p.propuesta === 'Gobierno' && p.gobierno?.persona
      if (p.propuesta && !propuestaDelGobierno && p.propuesta !== 'Gobierno') {
        const quien = nodo(claveOrganismo(p.propuesta), { tipo: 'organismo', nombre: p.propuesta })
        unir(persona.clave, quien.id, 'propuesta', { ...base, texto: cargo })
      }
      if (p.gobierno?.persona) {
        const g = nodoGobierno(p.gobierno)
        unir(persona.clave, g.id, propuestaDelGobierno ? 'propuesta' : 'nombramiento', { ...base, texto: cargo })
      }
      if (p.organo?.clave) {
        const o = nodoEntidad(p.organo)
        o.subtipo = 'organo'
        o.clase = 'adm'
        unir(persona.clave, o.id, 'dirigio', { ...base, texto: cargo })
      }
    }

    for (const a of persona.autorizaciones ?? []) {
      if (!a.empresa?.clave) continue
      const e = nodoEntidad(a.empresa)
      unir(persona.clave, e.id, 'autorizacion', {
        texto: `${a.actividad}${a.cargoAnterior ? `, tras dejar ${a.cargoAnterior}` : ''}`,
        desde: a.fecha ?? null,
        hasta: null,
        fuente: 'oci',
        url: a.url ?? '',
      })
      // El dinero entre el órgano que dirigió y la sociedad, si el volcado lo
      // encontró (`delOrgano`): es la pregunta de la puerta giratoria.
      for (const d of a.delOrgano ?? []) {
        if (!d?.organo?.clave) continue
        const o = nodoEntidad(d.organo)
        o.subtipo = 'organo'
        o.clase = 'adm'
        unir(o.id, e.id, 'dinero', {
          texto: dineroCorto(aNumero(d.importe)),
          importe: aNumero(d.importe),
          desde: d.desde ?? null,
          hasta: d.hasta ?? null,
          fuente: 'mapa',
          url: '',
        })
      }
    }

    for (const d of persona.declaraciones ?? []) {
      if (!d.empresa?.clave) continue
      const e = nodoEntidad(d.empresa)
      unir(persona.clave, e.id, 'declaracion', {
        texto: [d.descripcion, d.periodo].filter(Boolean).join(' · ') || d.empleador,
        desde: d.fechaRegistro ?? null,
        hasta: null,
        fuente: 'congreso',
        url: d.url ?? '',
      })
    }
  }

  // Las cotizadas y sus accionistas significativos, según la CNMV. Una
  // cotizada con NIF es el mismo nodo que esa empresa en el resto de la red:
  // la Indra de las autorizaciones de la OCI es la Indra de la CNMV.
  for (const c of Object.values(cargos?.cotizadas ?? {})) {
    if (!c?.clave) continue
    const f = formaDeNif(c.clave)
    const cotizada = nodo(c.clave, {
      tipo: 'entidad',
      nombre: c.nombre,
      ...(c.clave.startsWith('nif:') ? { entidad: c.clave } : {}),
      ...(f ? { forma: f.forma, clase: f.clase } : {}),
    })
    cotizada.cotizada = true
    // El sector es el de la ficha de la CNMV; «medio», si ese sector es el de
    // los medios de comunicación. Lo dice la fuente, no una lista nuestra.
    if (c.sector) cotizada.sector = c.sector
    if (c.medio) cotizada.medio = true
    for (const a of c.accionistas ?? []) {
      if (!a?.clave) continue
      const titular = a.persona
        ? nodo(a.clave, { tipo: 'persona', papel: 'accionista', nombre: nombreLegible(a.nombre), rango: 1, cargo: 'Accionista significativo' })
        : nodo(a.clave, {
            tipo: 'entidad',
            nombre: a.nombre,
            ...(a.clave.startsWith('nif:') ? { entidad: a.clave } : {}),
            ...(formaDeNif(a.clave) ? { forma: formaDeNif(a.clave).forma, clase: formaDeNif(a.clave).clase } : {}),
          })
      const pct = a.porcentaje ? `${String(a.porcentaje).replace('.', ',')} % de los derechos de voto` : 'Participación significativa'
      unir(titular.id, cotizada.id, 'accionista', {
        texto: pct,
        porcentaje: Number(a.porcentaje) || 0,
        desde: null,
        hasta: null,
        registro: a.fechaRegistroCNMV ?? null,
        fuente: 'cnmv',
        url: c.url ?? '',
      })
    }
  }

  // Presidentes → su Gobierno.
  for (const [clave, x] of presidentes) {
    if (!nodos.has(clave)) continue
    const g = nodoGobierno({ persona: clave, nombre: x.nombre, formacion: x.formacion })
    for (const per of x.periodos) {
      unir(clave, g.id, 'preside', {
        texto: 'Presidencia del Gobierno',
        desde: per.desde,
        hasta: per.hasta,
        fuente: 'boe',
        url: '',
      })
    }
  }

  // Gobierno → organismo, con cuántos nombramientos.
  for (const [k, n] of gobiernoOrganismo) {
    const [g, o] = k.split('|')
    unir(g, o, 'ministerio', {
      texto: `${n} ${n === 1 ? 'nombramiento' : 'nombramientos'} en el BOE`,
      n,
      fuente: 'boe',
      url: '',
    })
  }

  // El dinero, del mapa publicado. Dos cosas:
  //
  // - Entre entidades que ya están en la red, todo.
  // - Alrededor de cada entidad de la red, sus principales contrapartes —de
  //   quién cobra, a quién paga—, hasta `DINERO_POR_NODO`. Es lo que une la
  //   red de poder con el mapa del dinero: Indra, además de a quién se
  //   autorizó a trabajar allí, cobra de estos órganos.
  //
  // No todo el mapa: la red no se convierte en él, que ya existe.
  if (grafo?.nodes?.length) {
    const colapsado = colapsarNodosDePaso(grafo)
    const porId = new Map(colapsado.nodes.map((n) => [n.id, n]))
    const suma = new Map()
    for (const a of colapsado.edges) {
      if (a.status === 'retracted') continue
      const s = porId.get(a.source)
      const t = porId.get(a.target)
      if (!s?.clave || !t?.clave || s.clave === t.clave) continue
      const k = `${s.clave}|${t.clave}`
      const x = suma.get(k) ?? { s, t, importe: 0, veces: 0, desde: null, hasta: null }
      x.importe += aNumero(a.amount)
      x.veces += 1
      const f = a.start_date ?? null
      if (f && (!x.desde || f < x.desde)) x.desde = f
      if (f && (!x.hasta || f > x.hasta)) x.hasta = f
      suma.set(k, x)
    }
    const enLaRed = (clave) => nodos.has(clave) && nodos.get(clave).tipo !== 'persona'
    const alrededor = new Map()
    for (const x of suma.values()) {
      for (const [propio, ajeno] of [
        [x.s.clave, x.t],
        [x.t.clave, x.s],
      ]) {
        if (!enLaRed(propio) || enLaRed(ajeno.clave)) continue
        if (!alrededor.has(propio)) alrededor.set(propio, [])
        alrededor.get(propio).push({ x, ajeno })
      }
    }
    const elegidas = [...suma.values()].filter((x) => enLaRed(x.s.clave) && enLaRed(x.t.clave))
    for (const lista of alrededor.values()) {
      lista.sort((a, b) => b.x.importe - a.x.importe)
      for (const { x, ajeno } of lista.slice(0, DINERO_POR_NODO)) {
        if (!x.importe) continue
        const clase = ajeno.schema === 'PublicBody' ? 'adm' : ajeno.schema === 'Organization' ? 'par' : 'emp'
        nodo(ajeno.clave, { tipo: 'entidad', nombre: ajeno.caption, entidad: ajeno.clave, clase, ...(ajeno.schema === 'PublicBody' ? { subtipo: 'organo' } : {}) })
        elegidas.push(x)
      }
    }
    for (const x of elegidas) {
      const s = x.s.clave
      const t = x.t.clave
      // Si el volcado ya lo dio por `delOrgano`, no se duplica.
      if (aristas.has(`dinero|${s}|${t}`)) continue
      unir(s, t, 'dinero', {
        texto: `${dineroCorto(x.importe)} en ${x.veces} ${x.veces === 1 ? 'pago o adjudicación' : 'pagos o adjudicaciones'}`,
        importe: x.importe,
        desde: x.desde,
        hasta: x.hasta,
        fuente: 'mapa',
        url: '',
      })
    }
  }

  const lista = [...aristas.values()]
  const porNodo = new Map()
  for (const a of lista) {
    for (const extremo of [a.source, a.target]) {
      if (!porNodo.has(extremo)) porNodo.set(extremo, [])
      porNodo.get(extremo).push(a)
    }
  }
  for (const [id, n] of nodos) n.grado = porNodo.get(id)?.length ?? 0
  // Un nodo sin aristas no dice nada en una red: fuera.
  for (const [id, n] of nodos) if (!n.grado) nodos.delete(id)
  return { nodos, aristas: lista, porNodo }
}

/**
 * Cuánto interesa dibujar un nodo cuando no caben todos. Primero lo que une
 * a la persona con el dinero o con un partido; después el rango del cargo.
 */
export function relevancia(red, id) {
  const n = red.nodos.get(id)
  if (!n) return 0
  if (n.tipo !== 'persona') return 100 + (n.grado ?? 0)
  let fuertes = 0
  for (const a of red.porNodo.get(id) ?? []) {
    if (['autorizacion', 'declaracion', 'dirigio', 'escano', 'preside', 'propuesta', 'accionista'].includes(a.relacion)) fuertes += 1
  }
  return fuertes * 10 + (n.rango ?? 1) * 3 + Math.min(5, n.grado ?? 0)
}

function otro(a, id) {
  return a.source === id ? a.target : a.source
}

/**
 * El vecindario de un nodo, para dibujar.
 *
 * Los vecinos directos, por relevancia, hasta `limite`; si son pocos, un
 * segundo salto a través de los vecinos que no son un eje (un Gobierno, un
 * partido con doscientos escaños): así, desde una persona se ve quién más
 * pasó por la misma empresa, pero no los mil nombramientos del Gobierno.
 * Y las aristas entre todos los que se dibujan.
 *
 * @returns {{nodos: Array, aristas: Array, ocultos: number, centro: string}}
 */
export function egoRed(red, centro, { limite = 70, eje = 40, porPaso = 8 } = {}) {
  if (!red?.nodos?.has(centro)) return { nodos: [], aristas: [], ocultos: 0, centro }
  const orden = (a, b) => relevancia(red, b) - relevancia(red, a) || a.localeCompare(b)

  const directos = [...new Set((red.porNodo.get(centro) ?? []).map((a) => otro(a, centro)))].sort(orden)
  const dentro = new Map([[centro, 0]])
  for (const v of directos.slice(0, limite)) dentro.set(v, 1)
  const ocultos = Math.max(0, directos.length - limite)

  if (dentro.size < 16) {
    for (const v of directos) {
      if (dentro.size >= limite) break
      const nv = red.nodos.get(v)
      if (!nv || (nv.grado ?? 0) > eje) continue
      const segundos = [...new Set((red.porNodo.get(v) ?? []).map((a) => otro(a, v)))]
        .filter((w) => !dentro.has(w))
        .sort(orden)
        .slice(0, porPaso)
      for (const w of segundos) {
        if (dentro.size >= limite) break
        dentro.set(w, 2)
      }
    }
  }

  const aristas = []
  const vistas = new Set()
  for (const id of dentro.keys()) {
    for (const a of red.porNodo.get(id) ?? []) {
      if (vistas.has(a.id) || !dentro.has(a.source) || !dentro.has(a.target)) continue
      vistas.add(a.id)
      aristas.push(a)
    }
  }
  return {
    centro,
    ocultos,
    nodos: [...dentro.entries()].map(([id, salto]) => ({ ...red.nodos.get(id), salto })),
    aristas,
  }
}

/**
 * Las conexiones de un nodo para el panel, agrupadas por relación y en el
 * sentido en que se leen desde él.
 */
export function conexionesDe(red, id) {
  const grupos = new Map()
  for (const a of red?.porNodo?.get(id) ?? []) {
    const ida = a.source === id
    const clave = `${a.relacion}|${ida ? 'ida' : 'vuelta'}`
    if (!grupos.has(clave)) {
      const r = RELACIONES[a.relacion] ?? { ida: a.relacion, vuelta: a.relacion }
      grupos.set(clave, { relacion: a.relacion, sentido: ida ? 'ida' : 'vuelta', titulo: ida ? r.ida : r.vuelta, items: [] })
    }
    const o = red.nodos.get(otro(a, id))
    if (!o) continue
    grupos.get(clave).items.push({ nodo: o, hechos: a.hechos })
  }
  const salida = [...grupos.values()]
  for (const g of salida) {
    g.items.sort((x, y) => {
      if (g.relacion === 'dinero') return (y.hechos[0]?.importe ?? 0) - (x.hechos[0]?.importe ?? 0)
      if (g.relacion === 'ministerio') return (y.hechos[0]?.n ?? 0) - (x.hechos[0]?.n ?? 0)
      if (g.relacion === 'accionista') return (y.hechos[0]?.porcentaje ?? 0) - (x.hechos[0]?.porcentaje ?? 0)
      return relevancia(red, y.nodo.id) - relevancia(red, x.nodo.id) || x.nodo.nombre.localeCompare(y.nodo.nombre, 'es')
    })
  }
  return salida.sort(
    (a, b) =>
      ORDEN_RELACION.indexOf(a.relacion) - ORDEN_RELACION.indexOf(b.relacion) ||
      (a.sentido === 'ida' ? -1 : 1),
  )
}

/** Buscar en la red por nombre, desde el principio de palabra. */
export function buscarEnRed(red, consulta, limite = 12) {
  const aguja = normaliza(consulta).trim().replace(/\s+/g, ' ')
  if (aguja.length < 2) return []
  const salida = []
  for (const n of red?.nodos?.values() ?? []) {
    const nombres = [n.nombre, n.largo, ...(n.siglas ?? [])].filter(Boolean)
    if (nombres.some((x) => empiezaPalabra(normaliza(x), aguja))) salida.push(n)
  }
  return salida
    .sort((a, b) => relevancia(red, b.id) - relevancia(red, a.id) || a.nombre.localeCompare(b.nombre, 'es'))
    .slice(0, limite)
}

/**
 * La clase de color de un nodo: 'persona', 'adm', 'emp', 'par' o 'neutro'.
 * Los Gobiernos y ministerios son administración; los partidos, partido.
 */
export function claseDe(n) {
  if (!n) return 'neutro'
  if (n.tipo === 'persona') return 'persona'
  if (n.tipo === 'gobierno' || n.tipo === 'organismo') return 'adm'
  if (n.tipo === 'partido') return 'par'
  return n.clase ?? 'emp'
}

/** Cómo se dice qué es un nodo, lo más concreto que se sepa. */
export function nombreDeTipo(n) {
  if (!n) return ''
  // Un accionista de la CNMV no tiene cargo público: se dice lo que es.
  if (n.tipo === 'persona' && n.papel === 'accionista') return 'Accionista significativo, según la CNMV'
  if (n.tipo === 'entidad' && n.medio) return 'Grupo de medios de comunicación cotizado'
  if (n.tipo === 'entidad' && n.cotizada && n.forma) return `${n.forma} cotizada`
  if (n.tipo === 'entidad' && n.subtipo === 'organo') return 'Órgano de la administración'
  if (n.tipo === 'entidad' && n.forma) return n.forma
  return TIPOS[n.tipo]?.nombre ?? ''
}

/**
 * Por dónde empezar: los gobiernos, los partidos, y las entidades a las que
 * más personas con cargo están unidas.
 */
export function puntosDeEntrada(red, cuantos = 6) {
  const todos = [...(red?.nodos?.values() ?? [])]
  const porTipo = (tipo) => todos.filter((n) => n.tipo === tipo)
  const personasUnidas = (n) =>
    new Set(
      (red.porNodo.get(n.id) ?? [])
        .filter((a) => ['autorizacion', 'declaracion', 'dirigio'].includes(a.relacion))
        .map((a) => otro(a, n.id)),
    ).size
  const accionistas = (n) =>
    (red.porNodo.get(n.id) ?? []).filter((a) => a.relacion === 'accionista' && a.target === n.id).length
  const conAccionistas = (n) => ({ ...n, accionistas: accionistas(n) })
  const porAccionistas = (a, b) => b.accionistas - a.accionistas || a.nombre.localeCompare(b.nombre, 'es')
  return {
    // Los grupos de medios van en su fila, no repetidos en la de cotizadas.
    cotizadas: todos
      .filter((n) => n.cotizada && !n.medio)
      .map(conAccionistas)
      .filter((n) => n.accionistas > 0)
      .sort(porAccionistas)
      .slice(0, cuantos + 4),
    medios: todos.filter((n) => n.medio).map(conAccionistas).sort(porAccionistas),
    gobiernos: porTipo('gobierno').sort((a, b) => (b.grado ?? 0) - (a.grado ?? 0)),
    // Las instituciones de las altas instancias judiciales y fiscales, por su
    // nombre, que es el que pone el conector a partir del cargo.
    justicia: porTipo('organismo')
      .filter((n) => INSTITUCIONES_DE_JUSTICIA.test(n.nombre))
      .sort((a, b) => (b.grado ?? 0) - (a.grado ?? 0))
      .slice(0, cuantos + 4),
    partidos: porTipo('partido')
      .sort((a, b) => (b.grado ?? 0) - (a.grado ?? 0))
      .slice(0, cuantos + 2),
    entidades: porTipo('entidad')
      .map((n) => ({ ...n, personas: personasUnidas(n) }))
      .filter((n) => n.personas > 0)
      .sort((a, b) => b.personas - a.personas || a.nombre.localeCompare(b.nombre, 'es'))
      .slice(0, cuantos),
  }
}

const INSTITUCIONES_DE_JUSTICIA =
  /^(Tribunal Supremo|Tribunal Constitucional|Consejo General del Poder Judicial|Audiencia Nacional|Fiscalía General del Estado|Tribunal Superior de Justicia)/

/** El nodo con el que abrir la vista si no se pide ninguno: el Gobierno en curso. */
export function centroInicial(red, cargos) {
  const pres = [...(cargos?.presidencias ?? [])].sort((a, b) =>
    (b.desde ?? '').localeCompare(a.desde ?? ''),
  )
  for (const p of pres) {
    const id = `gobierno:${p.persona}`
    if (red.nodos.has(id)) return id
  }
  const primero = [...red.nodos.values()].sort((a, b) => (b.grado ?? 0) - (a.grado ?? 0))[0]
  return primero?.id ?? ''
}

/** Un montículo binario de [coste, …]: saca siempre el de menor coste. */
function monticulo() {
  const h = []
  const sube = (i) => {
    while (i > 0) {
      const p = (i - 1) >> 1
      if (h[p][0] <= h[i][0]) break
      ;[h[p], h[i]] = [h[i], h[p]]
      i = p
    }
  }
  const baja = (i) => {
    for (;;) {
      const l = 2 * i + 1
      const r = l + 1
      let m = i
      if (l < h.length && h[l][0] < h[m][0]) m = l
      if (r < h.length && h[r][0] < h[m][0]) m = r
      if (m === i) break
      ;[h[m], h[i]] = [h[i], h[m]]
      i = m
    }
  }
  return {
    tamano: () => h.length,
    mete(x) {
      h.push(x)
      sube(h.length - 1)
    },
    saca() {
      const cima = h[0]
      const ultimo = h.pop()
      if (h.length) {
        h[0] = ultimo
        baja(0)
      }
      return cima
    },
  }
}

/**
 * El camino más corto entre dos nodos, con los hechos de cada paso.
 *
 * «¿Cómo se une esta persona con esta empresa?». Pasar por un nodo cuesta
 * más cuanto más conectado está: un Gobierno une a mil quinientas personas,
 * y un camino por él es cierto pero no dice nada. Así que se prefiere el que
 * va por vínculos concretos —una empresa, un órgano, un partido— y sólo si
 * no hay otro se pasa por un eje.
 *
 * Un camino es una cadena de hechos, no una relación entre sus extremos: la
 * vista lo dice con esas palabras.
 *
 * @returns {{nodos: string[], aristas: object[]} | null} null si no hay.
 */
export function camino(red, desde, hasta, { maxPasos = 6 } = {}) {
  if (!red?.nodos?.has(desde) || !red.nodos.has(hasta)) return null
  if (desde === hasta) return { nodos: [desde], aristas: [] }
  // Con la raíz y no con el logaritmo: un Gobierno de 1.200 nombramientos
  // cuesta doce pasos, un ministerio de sesenta, tres y medio, y una empresa
  // con cinco vínculos, poco más de uno. Con el logaritmo el camino cruzaba
  // dos Gobiernos antes que dar un rodeo por una empresa.
  const coste = (id) => 1 + Math.sqrt(red.nodos.get(id)?.grado ?? 0) / 3
  // El estado es (nodo, pasos dados): con el límite de pasos, llegar a un
  // nodo barato pero por un camino largo no puede impedir llegar a él por
  // uno más caro y más corto. Con el estado sólo por nodo, pasaba.
  const k = (id, n) => `${n}|${id}`
  const dist = new Map([[k(desde, 0), 0]])
  const previo = new Map()
  const cola = monticulo()
  cola.mete([0, desde, 0])
  let final = null
  while (cola.tamano()) {
    const [d, actual, n] = cola.saca()
    if (actual === hasta) {
      final = k(actual, n)
      break
    }
    if (d > (dist.get(k(actual, n)) ?? Infinity) || n >= maxPasos) continue
    for (const a of red.porNodo.get(actual) ?? []) {
      const siguiente = otro(a, actual)
      if (siguiente === desde) continue
      // El coste es el del nodo al que se entra; el destino no penaliza.
      const nd = d + (siguiente === hasta ? 1 : coste(siguiente))
      const clave = k(siguiente, n + 1)
      if (nd < (dist.get(clave) ?? Infinity)) {
        dist.set(clave, nd)
        previo.set(clave, { estado: k(actual, n), nodo: actual, arista: a })
        cola.mete([nd, siguiente, n + 1])
      }
    }
  }
  if (!final) return null
  const nodos = [hasta]
  const aristas = []
  let x = final
  while (previo.has(x)) {
    const p = previo.get(x)
    aristas.unshift(p.arista)
    nodos.unshift(p.nodo)
    x = p.estado
  }
  return { nodos, aristas }
}

/** Un camino como red para dibujar: sus nodos, en orden, y sus aristas. */
export function redDeCamino(red, c) {
  if (!c) return { nodos: [], aristas: [], ocultos: 0, centro: '' }
  return {
    centro: c.nodos[0],
    ocultos: 0,
    nodos: c.nodos.map((id, i) => ({ ...red.nodos.get(id), salto: i === 0 || i === c.nodos.length - 1 ? 0 : 1 })),
    aristas: c.aristas,
  }
}
