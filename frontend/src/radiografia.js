import { nombreLegible } from './poder.js'

/**
 * La radiografía del poder: dónde se concentra y cómo se enlazan sus áreas.
 *
 * La red de poder (poder.js) responde a «¿con quién está unido X?». Esto
 * responde a la pregunta anterior, la de quien abre la página sin un nombre en
 * la cabeza: ¿cuáles son los núcleos, y qué los une?
 *
 * Todo sale de los dos ficheros publicados —`cargos.json` y `grafo.json`— y de
 * lo que dicen sus fuentes. Nada se clasifica por una lista nuestra:
 *
 * - **Núcleos**: el de un accionista son las cotizadas en las que tiene al
 *   menos un 5 %, si son dos o más (ver `nucleosEconomicos`). Las gestoras que
 *   están en casi todas (BlackRock) se apartan: una cartera repartida por todo
 *   el mercado no es un núcleo de poder.
 * - **Estado accionista**: un titular es del Estado si el BOE nombra a quien lo
 *   preside —el Gobierno nombra por Real Decreto la presidencia de la SEPI y
 *   la del FROB— o si tiene la mayoría de una sociedad cuyo nombre lleva
 *   «S.M.E.», la marca legal de las sociedades mercantiles estatales (ENAIRE en
 *   Aena). Las dos cosas son de la fuente, no una lista.
 * - **Flujos entre áreas**: cada uno es un recuento de hechos documentados —un
 *   nombramiento, una participación, una autorización, un contrato—, con los
 *   hechos detrás.
 *
 * Una persona sólo aparece en el papel en que la publica su fuente (spec §12):
 * consejero o accionista, según la CNMV; cargo público, según el BOE o la OCI.
 */

const FORMAS = new Set(['sa', 'sl', 'sau', 'slu', 'sme', 'socimi', 'sfl', 'inc', 'plc', 'llc', 'llp', 'lp', 'ag', 'icav', 'sgiic', 'srl', 'se', 'nv', 'bv', 'fi', 'frob', 'sepi', 'bbva', 'caf', 'acs', 'gic', 'fmr', 'tci', 'disa', 'enaire', 'mfe'])

/**
 * Un nombre de la CNMV o del BOE, legible: «CRITERIA CAIXA, S.A.U.» →
 * «Criteria Caixa, S.A.U.». Las formas jurídicas y las siglas, en mayúscula.
 */
export function nombrePropio(texto) {
  const t = nombreLegible((texto ?? '').trim())
  return t.replace(/[\p{L}.]+/gu, (palabra) => {
    const letras = palabra.replace(/\./g, '').toLowerCase()
    const conPuntos = /\p{L}\.\p{L}/u.test(palabra) && letras.length <= 5
    return FORMAS.has(letras) || conPuntos ? palabra.toUpperCase() : palabra
  })
}

/** Normalización para comparar nombres: sin acentos, sin signos, en minúscula. */
export function plano(texto) {
  return (texto ?? '')
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
}

/** ¿El nombre de la sociedad lleva la marca de las mercantiles estatales? */
export function esMercantilEstatal(nombre) {
  return /\bs\s?m\s?e\b/.test(plano(nombre))
}

/** Las gestoras presentes en casi todo: a partir de cuántas cotizadas. */
export function umbralOmnipresente(nCotizadas) {
  return Math.max(8, Math.ceil(nCotizadas * 0.2))
}

const pct = (x) => Number(x) || 0

/**
 * Los titulares que son el Estado, con el porqué.
 *
 * @returns {Map<string, {motivo: string, cargos: Array}>} por clave de titular.
 */
export function estadoAccionista(cargos) {
  const cotizadas = Object.values(cargos?.cotizadas ?? {})
  const titulares = new Map()
  for (const c of cotizadas) for (const a of c.accionistas ?? []) if (!a.persona) titulares.set(a.clave, a.nombre)

  const estado = new Map()
  // 1. El BOE nombra a quien lo preside o lo dirige: su nombre oficial, o su
  //    sigla entre paréntesis, está en el cargo.
  for (const [clave, nombre] of titulares) {
    const n = plano(nombre)
    if (n.length < 4) continue
    const cargosDelBoe = []
    for (const p of cargos?.personas ?? []) {
      for (const x of p.periodos ?? []) {
        if (x.ambito === 'justicia') continue
        const cargo = x.cargo ?? ''
        if (!/^(presidente|presidenta|director|directora)\b/i.test(cargo)) continue
        const sigla = cargo.match(/\(([^)]+)\)/)?.[1] ?? ''
        const cuerpo = plano(cargo.replace(/\([^)]*\)/g, ''))
        if (cuerpo.endsWith(n) || (sigla && plano(sigla) === n)) {
          cargosDelBoe.push({
            persona: p.clave,
            nombre: p.nombre,
            cargo,
            desde: x.desde ?? null,
            hasta: x.hasta ?? null,
            gobierno: x.gobierno ?? null,
            url: x.urlDesde ?? '',
          })
        }
      }
    }
    if (cargosDelBoe.length) {
      cargosDelBoe.sort((a, b) => (b.desde ?? '').localeCompare(a.desde ?? ''))
      estado.set(clave, { motivo: 'El Gobierno nombra a quien lo preside (BOE)', cargos: cargosDelBoe })
    }
  }
  // 2. Mayoría de una sociedad mercantil estatal.
  for (const c of cotizadas) {
    if (!esMercantilEstatal(c.nombre)) continue
    for (const a of c.accionistas ?? []) {
      if (!a.persona && pct(a.porcentaje) > 50 && !estado.has(a.clave)) {
        estado.set(a.clave, { motivo: `Tiene la mayoría de ${c.nombre}, sociedad mercantil estatal`, cargos: [] })
      }
    }
  }
  return estado
}

/** Desde qué porcentaje una participación cuenta para un núcleo. */
export const UMBRAL_DE_NUCLEO = 5

/**
 * Los núcleos del poder económico.
 *
 * El núcleo de un accionista son las cotizadas en las que tiene al menos un
 * 5 %, si son dos o más. Una cotizada puede estar en varios núcleos, y eso es
 * parte de lo que se ve: en Telefónica están la SEPI, Criteria y el fondo
 * saudí a la vez. Dos titulares con exactamente las mismas participaciones son
 * un solo grupo —la CNMV atribuye la misma participación indirecta a la
 * Fundación la Caixa y a Criteria, o a Joseph Oughourlian y a su Amber
 * Capital—, y los titulares del Estado (ver `estadoAccionista`) forman uno.
 * Los consejeros compartidos no hacen núcleos: son puentes entre ellos.
 * Una cotizada que no está en ningún núcleo sale en `referencias`, con su
 * accionista principal.
 */
export function nucleosEconomicos(cargos) {
  const cotizadas = cargos?.cotizadas ?? {}
  const n = Object.keys(cotizadas).length
  const presencia = new Map()
  for (const c of Object.values(cotizadas)) {
    for (const a of c.accionistas ?? []) {
      const x = presencia.get(a.clave) ?? { clave: a.clave, nombre: a.nombre, persona: !!a.persona, en: [] }
      x.en.push({ clave: c.clave, nombre: c.nombre, porcentaje: pct(a.porcentaje) })
      presencia.set(a.clave, x)
    }
  }
  const umbral = umbralOmnipresente(n)
  const omnipresentes = [...presencia.values()]
    .filter((x) => x.en.length >= umbral)
    .sort((a, b) => b.en.length - a.en.length)
  const apartados = new Set(omnipresentes.map((x) => x.clave))
  const estado = estadoAccionista(cargos)

  const asientos = new Map()
  for (const c of Object.values(cotizadas)) {
    for (const m of c.consejo ?? []) {
      const x = asientos.get(m.clave) ?? { clave: m.clave, nombre: m.nombre, persona: !!m.persona, en: [] }
      x.en.push({ clave: c.clave, nombre: c.nombre, cargo: m.cargo ?? '', categoria: m.categoria ?? '' })
      asientos.set(m.clave, x)
    }
  }
  const compartidos = [...asientos.values()].filter((x) => x.en.length >= 2)

  // Los grupos de titulares: por sus participaciones de referencia idénticas,
  // y el Estado, junto.
  const grupos = new Map()
  for (const x of presencia.values()) {
    if (apartados.has(x.clave)) continue
    const fuertes = x.en.filter((e) => e.porcentaje >= UMBRAL_DE_NUCLEO && e.clave !== x.clave)
    if (!fuertes.length) continue
    const firma = estado.has(x.clave)
      ? 'estado'
      : fuertes
          .map((e) => `${e.clave}:${e.porcentaje}`)
          .sort()
          .join('|')
    const gr = grupos.get(firma) ?? { titulares: [], participaciones: [] }
    gr.titulares.push({ clave: x.clave, nombre: x.nombre, persona: x.persona })
    for (const e of fuertes) {
      if (!gr.participaciones.some((p) => p.cotizada === e.clave && p.porcentaje === e.porcentaje && (firma !== 'estado' || p.titular === x.clave))) {
        gr.participaciones.push({ titular: x.clave, nombre: x.nombre, persona: x.persona, cotizada: e.clave, porcentaje: e.porcentaje })
      }
    }
    grupos.set(firma, gr)
  }

  const ficha = (k) => ({ clave: k, nombre: cotizadas[k]?.nombre ?? k, sector: cotizadas[k]?.sector ?? '', medio: !!cotizadas[k]?.medio })
  const nucleos = []
  for (const [firma, gr] of grupos) {
    const cots = [...new Set(gr.participaciones.map((p) => p.cotizada))]
    if (cots.length < 2) continue
    gr.participaciones.sort((a, b) => b.porcentaje - a.porcentaje)
    // Primero las sociedades que las personas: la persona que está detrás de
    // una sociedad se nombra, pero después.
    const titulares = [...gr.titulares].sort((a, b) => a.persona - b.persona || a.nombre.localeCompare(b.nombre, 'es'))
    nucleos.push({
      id: firma === 'estado' ? 'nucleo:estado' : `nucleo:${titulares[0].clave}`,
      estado: firma === 'estado',
      titulares,
      nombre: firma === 'estado' ? 'El Estado' : titulares.map((t) => t.nombre).join(' · '),
      cotizadas: cots.map(ficha).sort((a, b) => a.nombre.localeCompare(b.nombre, 'es')),
      participaciones: gr.participaciones,
      peso: gr.participaciones.reduce((s, p) => s + p.porcentaje, 0),
    })
  }
  nucleos.sort((a, b) => b.estado - a.estado || b.cotizadas.length - a.cotizadas.length || b.peso - a.peso)

  const enNucleo = new Map()
  for (const nu of nucleos) for (const c of nu.cotizadas) enNucleo.set(c.clave, [...(enNucleo.get(c.clave) ?? []), nu.id])
  for (const nu of nucleos) {
    nu.consejeros = compartidos.filter((x) => x.en.some((e) => enNucleo.get(e.clave)?.includes(nu.id)))
  }
  const referencias = Object.values(cotizadas)
    .filter((c) => !enNucleo.has(c.clave))
    .map((c) => {
      const ps = (c.accionistas ?? [])
        .filter((a) => !apartados.has(a.clave))
        .map((a) => ({ titular: a.clave, nombre: a.nombre, persona: !!a.persona, porcentaje: pct(a.porcentaje) }))
        .sort((a, b) => b.porcentaje - a.porcentaje)
      return { ...ficha(c.clave), principal: ps[0] ?? null, participaciones: ps }
    })
    .sort((a, b) => (b.principal?.porcentaje ?? 0) - (a.principal?.porcentaje ?? 0))

  return { nucleos, referencias, omnipresentes, compartidos, presencia, enNucleo }
}

/** Las áreas del poder y el orden en que se dibujan. */
export const AREAS = {
  parlamento: { nombre: 'Parlamento', clase: 'par' },
  partidos: { nombre: 'Partidos', clase: 'par' },
  gobierno: { nombre: 'Gobierno', clase: 'adm' },
  administracion: { nombre: 'Administración', clase: 'adm' },
  estado: { nombre: 'Estado accionista', clase: 'adm' },
  justicia: { nombre: 'Justicia', clase: 'adm' },
  accionistas: { nombre: 'Grandes accionistas', clase: 'emp' },
  empresas: { nombre: 'Grandes empresas', clase: 'emp' },
  medios: { nombre: 'Medios', clase: 'emp' },
}

/**
 * Cómo se enlazan las áreas: cada flujo, un recuento de hechos con fuente.
 */
export function flujosEntreAreas(cargos, grafo = null) {
  const flujos = []
  const cotizadas = cargos?.cotizadas ?? {}
  const estado = estadoAccionista(cargos)
  // Cada flujo con su frase y su unidad: «9 nombramientos», no «9 hechos».
  const add = (de, a, frase, unidad, hechos, extra = {}) => {
    if (hechos.length) flujos.push({ de, a, frase, unidad, n: hechos.length, hechos, ...extra })
  }

  // Gobierno → Estado accionista: los nombramientos de quien lo preside.
  add(
    'gobierno',
    'estado',
    'El Gobierno nombra a quien preside el Estado accionista',
    ['nombramiento', 'nombramientos'],
    [...estado.values()].flatMap((e) => e.cargos.map((c) => ({ texto: `${c.nombre}: ${c.cargo}`, desde: c.desde, fuente: 'boe', url: c.url, persona: c.persona }))),
  )
  // Estado accionista → empresas.
  const deEstado = []
  const deGrandes = []
  const aMedios = []
  for (const c of Object.values(cotizadas)) {
    for (const a of c.accionistas ?? []) {
      const h = { texto: `${a.nombre} → ${c.nombre}: ${String(a.porcentaje).replace('.', ',')} %`, porcentaje: pct(a.porcentaje), titular: a.clave, cotizada: c.clave, fuente: 'cnmv', url: c.url ?? '' }
      if (estado.has(a.clave)) deEstado.push(h)
      else if (c.medio) aMedios.push(h)
      else deGrandes.push(h)
    }
  }
  const porPct = (a, b) => b.porcentaje - a.porcentaje
  add('estado', 'empresas', 'El Estado es accionista de grandes empresas', ['participación', 'participaciones'], deEstado.filter((h) => !cotizadas[h.cotizada]?.medio).sort(porPct))
  add('estado', 'medios', 'El Estado es accionista de medios', ['participación', 'participaciones'], deEstado.filter((h) => cotizadas[h.cotizada]?.medio).sort(porPct))
  add('accionistas', 'empresas', 'Los grandes accionistas, en las cotizadas', ['participación significativa', 'participaciones significativas'], deGrandes.sort(porPct))
  add('accionistas', 'medios', 'Quién es dueño de los medios', ['participación significativa', 'participaciones significativas'], aMedios.sort(porPct))

  // Empresas ↔ empresas: consejeros compartidos.
  const { compartidos } = nucleosEconomicos(cargos)
  add(
    'empresas',
    'empresas',
    'Las grandes empresas comparten consejeros',
    ['consejero en dos consejos o más', 'consejeros en dos consejos o más'],
    compartidos.filter((x) => x.persona).map((x) => ({ texto: `${x.nombre}: ${x.en.map((e) => e.nombre).join(' · ')}`, persona: x.clave, fuente: 'cnmv' })),
  )

  // Gobierno → empresas: ex altos cargos autorizados a trabajar en ellas.
  const puertas = []
  for (const [clave, lista] of Object.entries(cargos?.empresas ?? {})) {
    for (const a of lista) {
      puertas.push({ texto: `${a.nombre} (${a.cargoAnterior ?? 'alto cargo'}) → ${a.actividad}`, persona: a.persona, entidad: clave, cotizada: !!cotizadas[clave], desde: a.fecha ?? null, fuente: 'oci' })
    }
  }
  // Sólo las autorizaciones para una cotizada: la flecha va a «grandes
  // empresas», y la mayoría son para otras sociedades o entidades.
  add(
    'gobierno',
    'empresas',
    'Ex altos cargos autorizados a trabajar en una cotizada',
    ['autorización de la OCI', 'autorizaciones de la OCI'],
    puertas.filter((h) => h.cotizada),
  )

  // Parlamento → empresas: lo que declararon los diputados.
  const declarados = []
  for (const [clave, lista] of Object.entries(cargos?.declarantes ?? {})) {
    for (const d of lista) declarados.push({ texto: `${d.nombre} (${d.formacion ?? ''}) → ${d.empleador ?? ''}`, persona: d.persona, entidad: clave, fuente: 'congreso' })
  }
  add(
    'parlamento',
    'empresas',
    'Diputados que declararon actividad en una cotizada',
    ['declaración', 'declaraciones'],
    declarados.filter((h) => cotizadas[h.entidad]),
  )

  // Justicia: quién propone a las altas instancias.
  const propuestas = { Gobierno: [], 'Congreso de los Diputados': [], Senado: [], 'Consejo General del Poder Judicial': [] }
  for (const p of cargos?.personas ?? []) {
    for (const x of p.periodos ?? []) {
      if (x.ambito !== 'justicia' || !propuestas[x.propuesta]) continue
      propuestas[x.propuesta].push({ texto: `${p.nombre}: ${x.cargo}`, persona: p.clave, desde: x.desde ?? null, fuente: 'boe', url: x.urlDesde ?? '' })
    }
  }
  add('parlamento', 'justicia', 'Congreso y Senado proponen vocales del CGPJ y magistrados del Constitucional', ['nombramiento', 'nombramientos'], [...propuestas['Congreso de los Diputados'], ...propuestas.Senado])
  add('justicia', 'justicia', 'El CGPJ propone la cúpula judicial', ['nombramiento', 'nombramientos'], propuestas['Consejo General del Poder Judicial'])
  add('gobierno', 'justicia', 'El Gobierno propone cargos de la cúpula judicial y fiscal', ['nombramiento', 'nombramientos'], propuestas.Gobierno)

  // Dinero público, del grafo: a las grandes empresas y a los partidos.
  if (grafo?.nodes?.length) {
    const claveDe = new Map(grafo.nodes.map((n) => [n.id, n]))
    const partidos = new Set(Object.values(cargos?.formaciones ?? {}).map((f) => f?.entidad?.clave).filter(Boolean))
    const aEmpresas = []
    const aPartidos = []
    for (const e of grafo.edges ?? []) {
      const s = claveDe.get(e.source)
      const t = claveDe.get(e.target)
      const importe = Number(e.amount) || 0
      if (!s || !t || !importe || e.schema === 'Debt') continue
      const h = { texto: `${s.caption} → ${t.caption}`, importe, desde: e.start_date ?? null, fuente: 'mapa', entidad: t.clave }
      if (cotizadas[t.clave]) aEmpresas.push(h)
      else if (partidos.has(t.clave)) aPartidos.push(h)
    }
    const porImporte = (a, b) => b.importe - a.importe
    const suma = (l) => l.reduce((s, h) => s + h.importe, 0)
    add('administracion', 'empresas', 'Dinero público a las cotizadas', ['contrato o subvención', 'contratos y subvenciones'], aEmpresas.sort(porImporte), { importe: suma(aEmpresas) })
    add('administracion', 'partidos', 'Dinero público a los partidos', ['subvención', 'subvenciones'], aPartidos.sort(porImporte), { importe: suma(aPartidos) })
  }
  return flujos
}

/**
 * Los puentes: quien está en más de un sitio.
 */
export function puentes(cargos) {
  const salida = []
  const { compartidos, presencia } = nucleosEconomicos(cargos)
  const cotizadas = cargos?.cotizadas ?? {}
  for (const x of compartidos) {
    if (!x.persona) continue
    salida.push({ clave: x.clave, nombre: x.nombre, tipo: 'consejos', n: x.en.length, detalle: x.en.map((e) => e.nombre) })
  }
  for (const x of presencia.values()) {
    if (x.persona && x.en.length >= 2) {
      salida.push({ clave: x.clave, nombre: x.nombre, tipo: 'accionista', n: x.en.length, detalle: x.en.map((e) => `${e.nombre} (${String(e.porcentaje).replace('.', ',')} %)`) })
    }
  }
  for (const [clave, lista] of Object.entries(cargos?.empresas ?? {})) {
    if (!cotizadas[clave]) continue
    for (const a of lista) {
      salida.push({ clave: a.persona, nombre: a.nombre, tipo: 'puerta', n: 1, detalle: [`${a.cargoAnterior ?? 'Alto cargo'} → ${cotizadas[clave].nombre}`] })
    }
  }
  for (const [, e] of estadoAccionista(cargos)) {
    for (const c of e.cargos.slice(0, 3)) {
      salida.push({ clave: c.persona, nombre: c.nombre, tipo: 'estado', n: 1, detalle: [c.cargo], gobierno: c.gobierno?.nombre ?? '' })
    }
  }
  const orden = { consejos: 0, accionista: 1, puerta: 2, estado: 3 }
  return salida.sort((a, b) => orden[a.tipo] - orden[b.tipo] || b.n - a.n || a.nombre.localeCompare(b.nombre, 'es'))
}

/**
 * Qué tipo de institución preside un cargo, por su nombre oficial. No se
 * clasifica a nadie: se clasifica la institución, y sólo con nombres que no
 * admiten duda. Lo que no casa no sale en este bloque (sí en la red).
 */
const INSTITUCIONES = [
  {
    tipo: 'reguladores',
    patron:
      /banco de espana|comision nacional del mercado de valores|comision nacional de los mercados y la competencia|comision nacional de energia|comision nacional de la competencia|comision del mercado de las telecomunicaciones|consejo de seguridad nuclear|agencia espanola de proteccion de datos|autoridad independiente de responsabilidad fiscal|consejo de transparencia|comision nacional del sector postal/,
  },
  {
    tipo: 'empresas',
    patron:
      /sociedad estatal de participaciones industriales|fondo de reestructuracion ordenada bancaria|instituto de credito oficial|administrador de infraestructuras ferroviarias|renfe|puertos del estado|enaire|aena|compania espanola de seguros de credito|correos|paradores|patrimonio nacional|entidad publica empresarial|sociedad mercantil estatal/,
  },
  // Sin el Tribunal de Cuentas: su presidencia la elige su propio Pleno, y el
  // Real Decreto sólo la formaliza. Contarla como «la nombra el Gobierno»
  // sería falso.
  { tipo: 'control', patron: /^presidente del consejo de estado$|instituto nacional de estadistica/ },
]
export const TIPOS_DE_INSTITUCION = {
  reguladores: 'Reguladores y supervisores',
  empresas: 'Empresas y entidades públicas',
  control: 'Órganos consultivos y estadística',
}

/**
 * Lo que nombra cada Gobierno: las presidencias de reguladores, empresas
 * públicas y órganos de control, del BOE, con el Gobierno que las nombró.
 */
export function nombramientosClave(cargos) {
  const gobiernos = new Map()
  for (const p of cargos?.presidencias ?? []) {
    if (!gobiernos.has(p.persona)) gobiernos.set(p.persona, { persona: p.persona, nombre: p.nombre, formacion: p.formacion ?? '', desde: p.desde ?? null, grupos: {}, altosCargos: new Set(), ministros: new Set() })
  }
  for (const p of cargos?.personas ?? []) {
    for (const x of p.periodos ?? []) {
      if (x.ambito === 'justicia' || (x.fuente ?? 'boe') !== 'boe') continue
      const g = gobiernos.get(x.gobierno?.persona)
      if (!g) continue
      g.altosCargos.add(p.clave)
      const cargo = x.cargo ?? ''
      const plano_ = plano(cargo.replace(/^president[ae]/i, 'presidente'))
      if (/^ministr[oa]\b/.test(plano_)) g.ministros.add(p.clave)
      if (!/^(presidente|gobernador|gobernadora)\b/.test(plano_) || /\bseccion\b/.test(plano_)) continue
      const inst = INSTITUCIONES.find((i) => i.patron.test(plano_))
      if (!inst) continue
      // Si antes estuvo en el Gobierno —ministro, vicepresidente, secretario
      // de Estado—, según el mismo BOE y la misma persona: del Gobierno al
      // árbitro. Sólo cargos anteriores a este nombramiento.
      const antes = (p.periodos ?? [])
        .filter((y) => y !== x && (y.fuente ?? 'boe') === 'boe' && y.desde && x.desde && y.desde < x.desde)
        .filter((y) => /^(ministr[oa]|vicepresident[ae] (primer|segund|tercer|cuart)[oa]? del gobierno|vicepresident[ae] del gobierno|secretari[oa] de estado)/i.test(y.cargo ?? ''))
        .sort((a, b) => (b.desde ?? '').localeCompare(a.desde ?? ''))[0]
      ;(g.grupos[inst.tipo] ??= []).push({
        persona: p.clave,
        nombre: p.nombre,
        cargo,
        desde: x.desde ?? null,
        url: x.urlDesde ?? '',
        ...(antes ? { antes: antes.cargo } : {}),
      })
    }
  }
  return [...gobiernos.values()]
    .map((g) => {
      for (const l of Object.values(g.grupos)) l.sort((a, b) => (b.desde ?? '').localeCompare(a.desde ?? ''))
      return { ...g, altosCargos: g.altosCargos.size, ministros: g.ministros.size }
    })
    .sort((a, b) => (b.desde ?? '').localeCompare(a.desde ?? ''))
}

/** Las cifras de cabecera. */
export function cifras(cargos) {
  const cot = Object.values(cargos?.cotizadas ?? {})
  const personas = cargos?.personas ?? []
  return {
    cotizadas: cot.length,
    consejeros: new Set(cot.flatMap((c) => (c.consejo ?? []).map((m) => m.clave))).size,
    accionistas: new Set(cot.flatMap((c) => (c.accionistas ?? []).map((a) => a.clave))).size,
    altosCargos: personas.filter((p) => (p.periodos ?? []).some((x) => x.ambito !== 'justicia' && (x.fuente ?? 'boe') === 'boe')).length,
    justicia: personas.filter((p) => (p.periodos ?? []).some((x) => x.ambito === 'justicia')).length,
    gobiernos: new Set((cargos?.presidencias ?? []).map((p) => p.persona)).size,
  }
}

/** El nombre corto de una cotizada: el que le da la CNMV, si está. */
export function nombreCorto(c) {
  return c?.abreviada || (c?.nombre ?? '').replace(/,.*$/, '')
}

/** Una sigla para un nombre largo: «Sociedad Estatal de Participaciones Industriales» → SEPI. */
export function sigla(nombre) {
  const t = (nombre ?? '').trim()
  if (t.length <= 14) return t
  const letras = t
    .split(/\s+/)
    .filter((p) => p.length > 2 && /^\p{Lu}/u.test(p))
    .map((p) => p[0])
    .join('')
  return letras.length >= 3 ? letras.toUpperCase() : t
}

/**
 * Lo que va dentro de cada caja del diagrama: quiénes son, con nombres. Sale
 * de los mismos datos; un área sin nada que nombrar se queda sin rótulo.
 */
export function rotulos(cargos, grafo, r) {
  const salida = {}
  const cot = cargos?.cotizadas ?? {}
  // El primer apellido: con dos apellidos, el penúltimo; con uno, el último.
  const apellido = (n) => {
    const t = (n ?? '').split(/\s+/)
    return t.length >= 3 ? t[t.length - 2] : t[t.length - 1]
  }
  const presidentes = [...new Map((cargos?.presidencias ?? []).map((p) => [p.persona, p.nombre])).values()]
  if (presidentes.length) salida.gobierno = `Gobiernos de ${presidentes.map(apellido).join(' y ')}`
  if (r.cifras.justicia) salida.justicia = 'Supremo · TC · CGPJ · AN…'
  const estado = [...(r.estado?.keys() ?? [])].map((k) => {
    for (const c of Object.values(cot)) for (const a of c.accionistas ?? []) if (a.clave === k) return sigla(nombrePropio(a.nombre))
    return ''
  })
  if (estado.length) salida.estado = estado.filter(Boolean).join(' · ')
  // Una palabra por titular: «Banco Santander» → Santander, «Amancio Ortega
  // Gaona» → Ortega.
  const corto = (t) => {
    if (t.persona) return apellido(nombrePropio(t.nombre))
    const palabras = nombrePropio(t.nombre).replace(/,.*$/, '').split(/\s+/)
    return palabras.find((w) => !/^(banco|grupo|corporaci[oó]n|sociedad|fundaci[oó]n|compañ[ií]a|the|de|la|el)$/i.test(w)) ?? palabras[0]
  }
  const grandes = r.nucleos.filter((n) => !n.estado).slice(0, 3).map((n) => corto(n.titulares[0]))
  if (grandes.length) salida.accionistas = grandes.join(' · ') + '…'
  salida.empresas = `${Object.keys(cot).length} cotizadas`
  const medios = Object.values(cot).filter((c) => c.medio).map((c) => nombrePropio(nombreCorto(c)))
  if (medios.length) salida.medios = medios.join(' · ')
  const partidos = r.flujos.find((f) => f.de === 'administracion' && f.a === 'partidos')
  if (partidos) {
    const porPartido = new Map()
    for (const h of partidos.hechos) porPartido.set(h.entidad, (porPartido.get(h.entidad) ?? 0) + h.importe)
    const siglas = Object.entries(cargos?.formaciones ?? {})
    const top = [...porPartido.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3)
      .map(([clave]) => siglas.find(([, f]) => f?.entidad?.clave === clave)?.[0]).filter(Boolean)
    if (top.length) salida.partidos = top.join(' · ') + '…'
  }
  const dinero = r.flujos.filter((f) => f.de === 'administracion')
  if (dinero.length) salida.administracion = 'Ministerios y organismos'
  const diputados = (cargos?.personas ?? []).filter((p) => (p.periodos ?? []).some((x) => x.fuente === 'congreso')).length
  if (diputados) salida.parlamento = `Congreso · ${diputados.toLocaleString('es-ES')} diputados`
  return salida
}

/**
 * El mapa de los núcleos, en una colocación que se puede explicar en una
 * frase: los núcleos en un anillo, ordenados para que los que comparten
 * cotizadas queden juntos; la cotizada de un solo núcleo, por fuera de él; la
 * que está en varios, dentro del anillo, entre ellos y más cerca de quien más
 * tiene. «Entre dos» es literal: se la disputan. Los consejeros compartidos,
 * entre las dos cotizadas que unen. Sin simulación: el mismo dato da siempre
 * el mismo dibujo.
 *
 * @returns {{nodos: Array, aristas: Array, caja: [number, number, number, number]}}
 */
export function mapaDeNucleos(r, cargos, { ancho = 1000, alto = 660 } = {}) {
  const cot = cargos?.cotizadas ?? {}
  const nucleos = r.nucleos
  if (!nucleos.length) return { nodos: [], aristas: [], caja: [0, 0, ancho, alto] }
  const cx = ancho / 2
  const cy = alto / 2
  const rx = ancho * 0.31
  const ry = alto * 0.34

  // El orden del anillo: cada núcleo se inserta donde menos lejos queda de
  // los núcleos con los que comparte cotizadas (lejanía en el anillo, por
  // cotizadas compartidas). Primero los que más comparten; el Estado, arriba.
  const cotsDe = new Map(nucleos.map((n) => [n.id, new Set(n.cotizadas.map((c) => c.clave))]))
  const comunes = (a, b) => [...cotsDe.get(a)].filter((c) => cotsDe.get(b).has(c)).length
  const total = (a) => nucleos.reduce((s, n) => s + (n.id === a ? 0 : comunes(a, n.id)), 0)
  const coste = (o) => {
    let c = 0
    for (let i = 0; i < o.length; i++) {
      for (let j = i + 1; j < o.length; j++) {
        const k = comunes(o[i], o[j])
        if (k) c += k * Math.min(j - i, o.length - (j - i))
      }
    }
    return c
  }
  const orden = [nucleos[0].id]
  const resto = nucleos.slice(1).map((n) => n.id).sort((a, b) => total(b) - total(a))
  for (const id of resto) {
    let mejor = null
    for (let i = 1; i <= orden.length; i++) {
      const prueba = [...orden.slice(0, i), id, ...orden.slice(i)]
      const c = coste(prueba)
      if (!mejor || c < mejor.c) mejor = { c, o: prueba }
    }
    orden.splice(0, orden.length, ...mejor.o)
  }
  const pos = new Map()
  const angulo = new Map()
  orden.forEach((id, i) => {
    const a = -Math.PI / 2 + (2 * Math.PI * i) / orden.length
    angulo.set(id, a)
    pos.set(id, [cx + rx * Math.cos(a), cy + ry * Math.sin(a)])
  })

  const nodos = []
  const porId = new Map(nucleos.map((n) => [n.id, n]))
  for (const id of orden) {
    const n = porId.get(id)
    nodos.push({
      id,
      tipo: 'nucleo',
      estado: n.estado,
      clave: n.estado ? '' : n.titulares[0].clave,
      nombre: n.estado ? 'El Estado' : n.titulares.map((t) => t.nombre).join(' · '),
      corto: n.estado ? 'El Estado' : nombrePropio(n.titulares[0].nombre).replace(/,.*$/, ''),
      persona: !n.estado && n.titulares.every((t) => t.persona),
      peso: n.cotizadas.length,
      x: pos.get(id)[0],
      y: pos.get(id)[1],
      // El rótulo: a un lado en los costados; arriba y abajo, hacia dentro
      // del anillo, que por fuera van sus cotizadas.
      lado:
        Math.cos(angulo.get(id)) > 0.55 ? 'der' : Math.cos(angulo.get(id)) < -0.55 ? 'izq' : Math.sin(angulo.get(id)) > 0 ? 'arriba' : 'abajo',
    })
  }

  // Cada cotizada, con sus núcleos y lo que cada uno tiene.
  const de = new Map()
  for (const n of nucleos) {
    for (const p of n.participaciones) {
      const x = de.get(p.cotizada) ?? new Map()
      x.set(n.id, Math.max(x.get(n.id) ?? 0, p.porcentaje))
      de.set(p.cotizada, x)
    }
  }
  const solas = new Map()
  const cotizadas = []
  for (const [clave, nus] of de) {
    const base = {
      id: clave,
      tipo: 'cotizada',
      clave,
      nombre: cot[clave]?.nombre ?? clave,
      corto: nombrePropio(nombreCorto(cot[clave])),
      medio: !!cot[clave]?.medio,
      compartida: nus.size > 1,
    }
    if (nus.size === 1) {
      const [id] = nus.keys()
      solas.set(id, [...(solas.get(id) ?? []), base])
    } else {
      // Entre sus núcleos, pesando por participación, y hacia dentro.
      let sx = 0
      let sy = 0
      let sw = 0
      for (const [id, pc] of nus) {
        const w = 0.5 + pc
        sx += pos.get(id)[0] * w
        sy += pos.get(id)[1] * w
        sw += w
      }
      const mx = sx / sw
      const my = sy / sw
      cotizadas.push({ ...base, x: cx + (mx - cx) * 0.62, y: cy + (my - cy) * 0.62, lado: 'arriba' })
    }
  }
  // Las de un solo núcleo, en abanico por fuera de él.
  for (const [id, lista] of solas) {
    const a = angulo.get(id)
    const [nx, ny] = pos.get(id)
    lista.sort((p, q) => p.nombre.localeCompare(q.nombre, 'es'))
    lista.forEach((c, i) => {
      const abre = (i - (lista.length - 1) / 2) * 0.55
      const x = nx + Math.cos(a + abre) * 74
      const y = ny + Math.sin(a + abre) * 60
      // El rótulo, por el lado que se aleja de su núcleo.
      const dx = x - nx
      const dy = y - ny
      const lado = Math.abs(dx) > Math.abs(dy) * 1.2 ? (dx > 0 ? 'der' : 'izq') : dy < 0 ? 'arriba' : 'abajo'
      // En abanico, los rótulos alternan de altura para no pisarse.
      cotizadas.push({ ...c, x, y, lado, escalon: i % 2, abanico: id })
    })
    // Un abanico vertical de varias: los rótulos se abren a los lados, el de
    // más a la izquierda hacia la izquierda y el resto hacia la derecha.
    if (lista.length > 1 && Math.abs(Math.sin(a)) > 0.7) {
      const suyas = cotizadas.filter((c) => c.abanico === id).sort((p, q) => p.x - q.x)
      suyas.forEach((c, i) => {
        const vertical = Math.sin(a) > 0 ? 'abajo' : 'arriba'
        c.lado = `${vertical}-${i < suyas.length / 2 ? 'izq' : 'der'}`
        c.escalon = i % 2
      })
    }
  }
  // Las de dentro, separadas por la caja de su rótulo (unos 6,5 px por letra,
  // encima del punto), no sólo por el punto: dos rótulos no se pisan.
  const dentro = cotizadas.filter((c) => c.compartida)
  const caja = (c) => {
    const w = Math.min(20, c.corto.length) * 6.5 + 8
    return [c.x - w / 2, c.y - 22, c.x + w / 2, c.y + 6]
  }
  for (let vuelta = 0; vuelta < 120; vuelta++) {
    let movido = false
    for (let i = 0; i < dentro.length; i++) {
      for (let j = i + 1; j < dentro.length; j++) {
        const a = dentro[i]
        const b = dentro[j]
        const [ax0, ay0, ax1, ay1] = caja(a)
        const [bx0, by0, bx1, by1] = caja(b)
        const sx = Math.min(ax1, bx1) - Math.max(ax0, bx0)
        const sy = Math.min(ay1, by1) - Math.max(ay0, by0)
        if (sx <= 0 || sy <= 0) continue
        movido = true
        // Se separan por el eje en que menos se solapan.
        if (sy < sx) {
          const d = (sy / 2 + 1) * (a.y <= b.y ? -1 : 1)
          a.y += d
          b.y -= d
        } else {
          const d = (sx / 2 + 1) * (a.x <= b.x ? -1 : 1)
          a.x += d
          b.x -= d
        }
      }
    }
    if (!movido) break
  }
  nodos.push(...cotizadas)

  const aristas = []
  for (const [clave, nus] of de) {
    for (const [id, pc] of nus) aristas.push({ source: id, target: clave, tipo: 'participacion', porcentaje: pc })
  }
  // Los consejeros compartidos, entre las cotizadas que unen.
  const enMapa = new Map(nodos.map((n) => [n.id, n]))
  for (const x of r.compartidos ?? []) {
    if (!x.persona) continue
    const en = x.en.filter((e) => enMapa.has(e.clave))
    if (en.length < 2) continue
    const mx = en.reduce((s, e) => s + enMapa.get(e.clave).x, 0) / en.length
    const my = en.reduce((s, e) => s + enMapa.get(e.clave).y, 0) / en.length
    nodos.push({ id: x.clave, tipo: 'persona', clave: x.clave, nombre: x.nombre, corto: nombrePropio(x.nombre), x: mx, y: my + 10 })
    for (const e of en) aristas.push({ source: x.clave, target: e.clave, tipo: 'consejo' })
  }
  return { nodos, aristas, caja: [0, 0, ancho, alto] }
}

/** Todo junto. */
export function radiografia(cargos, grafo = null) {
  const economicos = nucleosEconomicos(cargos)
  return {
    cifras: cifras(cargos),
    nucleos: economicos.nucleos,
    referencias: economicos.referencias,
    omnipresentes: economicos.omnipresentes,
    compartidos: economicos.compartidos,
    enNucleo: economicos.enNucleo,
    estado: estadoAccionista(cargos),
    flujos: flujosEntreAreas(cargos, grafo),
    puentes: puentes(cargos),
    gobiernos: nombramientosClave(cargos),
  }
}

/** Todo junto, con los rótulos del diagrama. */
export function radiografiaCompleta(cargos, grafo = null) {
  const r = radiografia(cargos, grafo)
  return { ...r, rotulos: rotulos(cargos, grafo, r), mapa: mapaDeNucleos(r, cargos) }
}
