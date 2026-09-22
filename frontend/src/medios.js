/**
 * Publicidad institucional y medios de comunicación.
 *
 * Es una de las preguntas con las que la gente llega —«¿qué medios cobran de
 * esta administración?»— y es también una de las más fáciles de contestar mal.
 * No hay ningún campo en los datos que diga «esto es un medio de
 * comunicación»: hay que deducirlo, y deducirlo con holgura significa acusar a
 * quien no toca.
 *
 * ## Lo que se usa y por qué
 *
 * El CPV, el vocabulario común de contratos públicos, que el órgano de
 * contratación asigna a cada expediente. Es un código oficial, publicado y
 * comprobable: no es una inferencia nuestra sobre el nombre de la empresa.
 *
 * La lista de abajo es **cerrada y por código exacto**, no por prefijo. La
 * primera versión filtraba por los cuatro primeros dígitos y metía en «medios»
 * la familia 7941 entera — que es consultoría de gestión: recursos humanos
 * (79414000), evaluación (79419000), producción (79415000). Habría publicado
 * una lista titulada «quién cobra de la publicidad institucional» con
 * consultoras de RRHH dentro. Un falso positivo aquí es una acusación falsa.
 *
 * Por el mismo motivo quedan FUERA códigos que rozan el asunto sin serlo:
 * marketing genérico (79342000), estudios de mercado, organización de ferias y
 * congresos (7995xxxx) o atención al cliente. Se pierde alcance y se gana en
 * que lo que salga sea cierto.
 *
 * ## Lo que esta lista no dice
 *
 * Que una empresa aparezca aquí no la convierte en un medio de comunicación:
 * puede ser la agencia que compra los espacios, la productora o la imprenta.
 * Lo que afirma el dato es el objeto del contrato, no la naturaleza del
 * adjudicatario, y así hay que enseñarlo. Por eso el bloque de la portada se
 * titula «gasto en publicidad institucional» y no «publicidad y medios»: con
 * los datos del 22/9 los cuatro contratos de cabeza los cobran dos
 * aerolíneas, un club de fútbol y un obrador. El filtro acierta; el título
 * anterior prometía otra cosa.
 */

import { aNumero } from './nucleos.js'

/** Código CPV exacto → cómo se llama en el vocabulario oficial. */
export const CPV_MEDIOS = {
  22200000: 'Periódicos, revistas y publicaciones periódicas',
  22210000: 'Periódicos',
  22211000: 'Revistas',
  22212000: 'Publicaciones periódicas',
  22213000: 'Revistas especializadas',
  79340000: 'Publicidad y marketing',
  79341000: 'Publicidad',
  79341100: 'Consultoría publicitaria',
  79341200: 'Gestión publicitaria',
  79341400: 'Campañas de publicidad',
  79341500: 'Publicidad aérea',
  79342200: 'Servicios de promoción',
  79416000: 'Relaciones públicas',
  79416100: 'Gestión de relaciones públicas',
  79416200: 'Consultoría de relaciones públicas',
  79970000: 'Servicios de edición',
  79980000: 'Servicios de suscripción',
  92200000: 'Servicios de radio y televisión',
  92210000: 'Servicios de radio',
  92211000: 'Producción radiofónica',
  92220000: 'Servicios de televisión',
  92221000: 'Producción televisiva',
  92400000: 'Agencias de noticias',
}

/** El CPV a veces llega con dígito de control («79341000-3»); se ignora. */
export function etiquetaCpv(cpv) {
  if (!cpv) return ''
  return CPV_MEDIOS[String(cpv).split('-')[0].trim()] ?? ''
}

export function esCpvDeMedios(cpv) {
  return Boolean(etiquetaCpv(cpv))
}

/**
 * Los contratos de publicidad y medios del grafo, con sus dos extremos.
 *
 * Toma el grafo **sin colapsar**, porque el CPV vive en el expediente: al
 * puentear los contratos ese dato desaparece del grafo.
 */
export function contratosDeMedios(datos, { limite = 20 } = {}) {
  const nodos = datos?.nodes ?? []
  const aristas = datos?.edges ?? []
  const porId = new Map(nodos.map((n) => [n.id, n]))

  const expedientes = nodos.filter(
    (n) => n.schema === 'Contract' && esCpvDeMedios(n.properties?.cpvCode),
  )
  if (!expedientes.length) {
    return { contratos: [], porEmpresa: [], porOrganismo: [], total: 0, nContratos: 0 }
  }
  const dentro = new Set(expedientes.map((n) => n.id))

  const organoDe = new Map()
  const adjudicaciones = []
  for (const a of aristas) {
    if (dentro.has(a.target) && a.schema === 'UnknownLink') organoDe.set(a.target, a.source)
    if (dentro.has(a.source) && a.schema === 'ContractAward') adjudicaciones.push(a)
  }

  const contratos = []
  const porEmpresa = new Map()
  const porOrganismo = new Map()
  let total = 0

  for (const a of adjudicaciones) {
    const exp = porId.get(a.source)
    const empresa = porId.get(a.target)
    if (!exp || !empresa) continue
    const organo = porId.get(organoDe.get(exp.id))
    const importe = aNumero(a.amount)
    total += importe

    contratos.push({
      id: a.id,
      contratoId: exp.id,
      titulo: exp.caption,
      cpv: exp.properties?.cpvCode ?? '',
      etiqueta: etiquetaCpv(exp.properties?.cpvCode),
      url: exp.properties?.sourceUrl ?? '',
      empresaId: empresa.id,
      empresa: empresa.caption,
      empresaExtranjera: Boolean(empresa.properties?.entidad_extranjera),
      organoId: organo?.id ?? '',
      organo: organo?.caption ?? '',
      importe,
      // Un importe que la ingesta no se creyó no puede sumar como si tal cosa.
      sinImporte: a.amount === undefined || a.amount === null || a.amount === '',
      confianza: a.confidence ?? 1,
    })

    for (const [mapa, id, caption] of [
      [porEmpresa, empresa.id, empresa.caption],
      [porOrganismo, organo?.id, organo?.caption],
    ]) {
      if (!id) continue
      if (!mapa.has(id)) mapa.set(id, { id, caption, total: 0, n: 0 })
      const acc = mapa.get(id)
      acc.total += importe
      acc.n += 1
    }
  }

  const ordenar = (m) =>
    [...m.values()].sort((x, y) => y.total - x.total || y.n - x.n).slice(0, limite)

  return {
    contratos: contratos.sort((x, y) => y.importe - x.importe),
    porEmpresa: ordenar(porEmpresa),
    porOrganismo: ordenar(porOrganismo),
    total,
    nContratos: expedientes.length,
  }
}
