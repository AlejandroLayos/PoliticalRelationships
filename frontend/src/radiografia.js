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
  const add = (de, a, etiqueta, hechos, extra = {}) => {
    if (hechos.length) flujos.push({ de, a, etiqueta, n: hechos.length, hechos, ...extra })
  }

  // Gobierno → Estado accionista: los nombramientos de quien lo preside.
  add(
    'gobierno',
    'estado',
    'nombra a quien preside',
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
  add('estado', 'empresas', 'es accionista de', deEstado.filter((h) => !cotizadas[h.cotizada]?.medio).sort(porPct))
  add('estado', 'medios', 'es accionista de', deEstado.filter((h) => cotizadas[h.cotizada]?.medio).sort(porPct))
  add('accionistas', 'empresas', 'participaciones significativas', deGrandes.sort(porPct))
  add('accionistas', 'medios', 'son dueños de', aMedios.sort(porPct))

  // Empresas ↔ empresas: consejeros compartidos.
  const { compartidos } = nucleosEconomicos(cargos)
  add(
    'empresas',
    'empresas',
    'comparten consejeros',
    compartidos.filter((x) => x.persona).map((x) => ({ texto: `${x.nombre}: ${x.en.map((e) => e.nombre).join(' · ')}`, persona: x.clave, fuente: 'cnmv' })),
  )

  // Gobierno → empresas: ex altos cargos autorizados a trabajar en ellas.
  const puertas = []
  for (const [clave, lista] of Object.entries(cargos?.empresas ?? {})) {
    for (const a of lista) {
      puertas.push({ texto: `${a.nombre} (${a.cargoAnterior ?? 'alto cargo'}) → ${a.actividad}`, persona: a.persona, entidad: clave, cotizada: !!cotizadas[clave], desde: a.fecha ?? null, fuente: 'oci' })
    }
  }
  add('gobierno', 'empresas', 'ex altos cargos autorizados a trabajar en', puertas.sort((a, b) => b.cotizada - a.cotizada))

  // Parlamento → empresas: lo que declararon los diputados.
  const declarados = []
  for (const [clave, lista] of Object.entries(cargos?.declarantes ?? {})) {
    for (const d of lista) declarados.push({ texto: `${d.nombre} (${d.formacion ?? ''}) → ${d.empleador ?? ''}`, persona: d.persona, entidad: clave, fuente: 'congreso' })
  }
  add('parlamento', 'empresas', 'diputados que declararon actividad en', declarados)

  // Justicia: quién propone a las altas instancias.
  const propuestas = { Gobierno: [], 'Congreso de los Diputados': [], Senado: [], 'Consejo General del Poder Judicial': [] }
  for (const p of cargos?.personas ?? []) {
    for (const x of p.periodos ?? []) {
      if (x.ambito !== 'justicia' || !propuestas[x.propuesta]) continue
      propuestas[x.propuesta].push({ texto: `${p.nombre}: ${x.cargo}`, persona: p.clave, desde: x.desde ?? null, fuente: 'boe', url: x.urlDesde ?? '' })
    }
  }
  add('parlamento', 'justicia', 'propone al CGPJ y al Constitucional', [...propuestas['Congreso de los Diputados'], ...propuestas.Senado])
  add('justicia', 'justicia', 'el CGPJ propone la cúpula judicial', propuestas['Consejo General del Poder Judicial'])
  add('gobierno', 'justicia', 'propone', propuestas.Gobierno)

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
    add('administracion', 'empresas', 'contratos y subvenciones a', aEmpresas.sort(porImporte), { importe: suma(aEmpresas) })
    add('administracion', 'partidos', 'subvenciones a', aPartidos.sort(porImporte), { importe: suma(aPartidos) })
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
  }
}
