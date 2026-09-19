/**
 * Área de influencia de una entidad.
 *
 * Esto es lo que contesta las preguntas que la gente se hace de verdad. No
 * "¿cómo es la red?", sino:
 *
 *   - Me pongo sobre un partido: ¿de quién recibe dinero? ¿a quién se lo paga?
 *     ¿le han sancionado? ¿hay capital extranjero cerca?
 *   - Me pongo sobre mi ayuntamiento: ¿qué empresas cobran de él? ¿cuánto?
 *     ¿esas empresas cobran también de otros sitios?
 *
 * Un grafo no contesta eso; una ficha sí. El grafo sirve para ver la forma, la
 * ficha para leer los hechos.
 *
 * ## La dirección de la arista significa cosas distintas según el esquema
 *
 * No basta con mirar source/target. En FollowTheMoney cada arista tiene su
 * dirección canónica y no todas son "dinero que va de A a B":
 *
 *   Payment        pagador  -> beneficiario   dinero
 *   ContractAward  contrato -> adjudicatario  dinero (tras colapsar, órgano -> empresa)
 *   Debt           deudor   -> acreedor       una multa: el deudor NO está pagando por un servicio
 *   UnknownLink    sujeto   -> objeto         estructura, sin dinero
 *
 * Tratar una sanción del Tribunal de Cuentas como "este partido paga a la
 * Administración" sería una lectura falsa de los datos, y en la ficha de un
 * partido saldría como si estuviera financiando al Estado. Por eso las
 * sanciones van en su propia sección.
 */

import { aNumero, dineroCorto } from './nucleos.js'

/** Aristas que mueven dinero de verdad, en dirección pagador -> receptor. */
const ESQUEMAS_DINERO = new Set(['Payment', 'ContractAward'])

/** Una multa no es financiación. Va aparte. */
const ESQUEMAS_SANCION = new Set(['Debt'])

function vacio(entidad = null) {
  return {
    entidad,
    recibeDe: [],
    pagaA: [],
    sanciones: [],
    totalRecibido: 0,
    totalPagado: 0,
    totalSancionado: 0,
    extranjero: { contrapartes: [], total: 0, porcentaje: 0, indicios: [], totalIndicios: 0 },
    comparten: [],
    compartenPor: [],
    red: { nodes: [], edges: [] },
  }
}

/**
 * Extranjera **probada**: lo afirma la letra del NIF, no nosotros.
 */
function esExtranjera(n) {
  return Boolean(n?.properties?.entidad_extranjera)
}

/**
 * Extranjera **por indicio**: sin NIF español y con forma societaria
 * extranjera al final del nombre. Va aparte de lo anterior en todo el camino
 * —aquí, en la ficha y en el dibujo— porque presentarlos juntos convertiría
 * una sospecha razonable en una afirmación.
 */
function indicioExtranjera(n) {
  return Boolean(n?.properties?.entidad_extranjera_indicio)
}

/**
 * Calcula la ficha.
 *
 * `datos` es el grafo completo ya publicado; `id`, la entidad sobre la que se
 * pregunta. Devuelve listas ya ordenadas por dinero: lo primero que se lee es
 * lo que más pesa.
 */
export function areaDeInfluencia(datos, id) {
  const nodos = datos?.nodes ?? []
  const aristas = datos?.edges ?? []
  const porId = new Map(nodos.map((n) => [n.id, n]))
  const entidad = porId.get(id)
  if (!entidad) return vacio()

  const entra = new Map() // quién me paga
  const sale = new Map() // a quién pago
  const sanciones = []

  function acumula(mapa, otroId, arista) {
    const otro = porId.get(otroId)
    if (!otro) return
    if (!mapa.has(otroId)) {
      mapa.set(otroId, {
        id: otroId,
        caption: otro.caption,
        schema: otro.schema,
        extranjera: esExtranjera(otro),
        extranjeraIndicio: indicioExtranjera(otro),
        total: 0,
        n: 0,
        // La confianza mínima de las relaciones que lo sostienen: si una
        // contraparte está ahí por una inferencia floja, hay que poder verlo.
        confianza: 1,
        inferido: false,
        // Relaciones cuya cifra no se publica. No es lo mismo que la fuente
        // no diera importe que que la ingesta no se creyera el que dio, y las
        // dos cosas acaban aquí como un hueco: sin decirlo, la ausencia de
        // dato parece un dato.
        sinCifra: 0,
        motivosSinCifra: [],
        // Los expedientes por los que pasa la relación. Al colapsar el
        // contrato para poder contestar «¿a qué empresas paga?» en vez de «¿a
        // qué expedientes?», el papel que lo justifica desaparece del grafo.
        // Guardar su id deja el rastro: la respuesta sigue siendo verificable.
        expedientes: [],
      })
    }
    const acc = mapa.get(otroId)
    acc.total += aNumero(arista.amount)
    acc.n += 1
    acc.confianza = Math.min(acc.confianza, arista.confidence ?? 1)
    if (arista.status === 'inferred') acc.inferido = true
    if (arista.viaDePaso && !acc.expedientes.includes(arista.viaDePaso)) {
      acc.expedientes.push(arista.viaDePaso)
    }
    if (arista.amount === undefined || arista.amount === null || arista.amount === '') {
      acc.sinCifra += 1
      const motivo = arista.properties?.motivoImporteDudoso
      if (motivo && !acc.motivosSinCifra.includes(motivo)) acc.motivosSinCifra.push(motivo)
    }
  }

  for (const a of aristas) {
    const esOrigen = a.source === id
    const esDestino = a.target === id
    if (!esOrigen && !esDestino) continue

    if (ESQUEMAS_SANCION.has(a.schema)) {
      // Debt va deudor -> acreedor. Si la entidad es el deudor, le han
      // sancionado; no está financiando a nadie.
      if (esOrigen) {
        const acreedor = porId.get(a.target)
        sanciones.push({
          id: a.id,
          acreedor: acreedor?.caption ?? '',
          acreedorId: a.target,
          importe: aNumero(a.amount),
          sinImporte: a.amount === undefined || a.amount === '' || a.amount === null,
          fecha: a.start_date ?? '',
          confianza: a.confidence ?? 1,
          propiedades: a.properties ?? {},
        })
      }
      continue
    }

    if (!ESQUEMAS_DINERO.has(a.schema)) continue

    if (esDestino) acumula(entra, a.source, a)
    else acumula(sale, a.target, a)
  }

  const recibeDe = [...entra.values()].sort((x, y) => y.total - x.total || y.n - x.n)
  const pagaA = [...sale.values()].sort((x, y) => y.total - x.total || y.n - x.n)
  const totalRecibido = recibeDe.reduce((s, x) => s + x.total, 0)
  const totalPagado = pagaA.reduce((s, x) => s + x.total, 0)

  // Capital extranjero EN SU ENTORNO: contrapartes no residentes, a un lado o
  // al otro. Es la pregunta "¿qué influencia extranjera tiene esto?" contestada
  // con lo que los datos afirman, que es la residencia fiscal de quien cobra o
  // paga, y nada más.
  const contrapartes = [...recibeDe, ...pagaA].filter((x) => x.extranjera)
  const totalExtranjero = contrapartes.reduce((s, x) => s + x.total, 0)
  // Los indicios se cuentan aparte y NO entran en el porcentaje de exposición:
  // ese número se lee como un hecho y sólo puede salir de hechos.
  const contrapartesIndicio = [...recibeDe, ...pagaA].filter(
    (x) => x.extranjeraIndicio && !x.extranjera,
  )
  const totalMovido = totalRecibido + totalPagado

  // Quién más cobra de sus mismos pagadores. Es lo que enseña el "ámbito de
  // interés": empresas que orbitan los mismos organismos.
  const comparten = new Map()
  const misPagadores = new Set(recibeDe.map((x) => x.id))
  for (const a of aristas) {
    if (!ESQUEMAS_DINERO.has(a.schema)) continue
    if (!misPagadores.has(a.source) || a.target === id) continue
    const otro = porId.get(a.target)
    if (!otro) continue
    if (!comparten.has(a.target)) {
      comparten.set(a.target, {
        id: a.target,
        caption: otro.caption,
        schema: otro.schema,
        extranjera: esExtranjera(otro),
        extranjeraIndicio: indicioExtranjera(otro),
        total: 0,
        pagadores: new Set(),
      })
    }
    const c = comparten.get(a.target)
    c.total += aNumero(a.amount)
    c.pagadores.add(a.source)
  }

  const compartenLista = [...comparten.values()]
    .map((c) => ({ ...c, pagadoresComunes: c.pagadores.size, pagadores: undefined }))
    .sort((x, y) => y.pagadoresComunes - x.pagadoresComunes || y.total - x.total)
    .slice(0, 15)

  // POR QUÉ orbitan, y a cuántos alcanza ese pagador.
  //
  // Sin esto el bloque insinúa. En la ficha del PSOE salían listados el PP,
  // VOX, Podemos y once partidos más, cada uno con su cifra, bajo el título
  // «orbitan a sus mismos pagadores». Es verdad y no dice absolutamente nada:
  // lo que comparten es la Dirección General de Política Interior, que es
  // quien paga la subvención electoral a todos los partidos. Descubrir que
  // los partidos cobran de quien paga a los partidos no es un hallazgo, y
  // presentarlo como una órbita común sí parece uno.
  //
  // Así que se dice cuál es el pagador compartido y a cuántos reparte. Con
  // «reparte entre 93 entidades» al lado, el lector ve solo que la
  // coincidencia no significa nada. Y cuando el pagador común sí es estrecho,
  // la misma frase lo deja claro en el otro sentido.
  const cuantasPorPagador = new Map()
  for (const c of comparten.values()) {
    for (const p of c.pagadores ?? []) {
      cuantasPorPagador.set(p, (cuantasPorPagador.get(p) ?? 0) + 1)
    }
  }
  const alcanceDe = new Map()
  for (const a of aristas) {
    if (!ESQUEMAS_DINERO.has(a.schema)) continue
    if (!cuantasPorPagador.has(a.source)) continue
    if (!alcanceDe.has(a.source)) alcanceDe.set(a.source, new Set())
    alcanceDe.get(a.source).add(a.target)
  }
  const compartenPor = [...cuantasPorPagador.entries()]
    .map(([idPagador, cuantos]) => ({
      id: idPagador,
      caption: porId.get(idPagador)?.caption ?? '',
      cuantos,
      alcance: alcanceDe.get(idPagador)?.size ?? 0,
    }))
    .filter((x) => x.caption)
    .sort((x, y) => y.cuantos - x.cuantos || y.alcance - x.alcance)
    .slice(0, 2)

  return {
    entidad,
    recibeDe,
    pagaA,
    sanciones: sanciones.sort((x, y) => y.importe - x.importe),
    totalRecibido,
    totalPagado,
    totalSancionado: sanciones.reduce((s, x) => s + x.importe, 0),
    extranjero: {
      contrapartes,
      total: totalExtranjero,
      porcentaje: totalMovido > 0 ? (totalExtranjero / totalMovido) * 100 : 0,
      indicios: contrapartesIndicio,
      totalIndicios: contrapartesIndicio.reduce((s, x) => s + x.total, 0),
    },
    comparten: compartenLista,
    compartenPor,
    red: redDeFlujo(datos, id, recibeDe, pagaA),
  }
}

/**
 * La ego-red preparada para dibujarse como un flujo: pagadores a la izquierda,
 * la entidad en medio, beneficiarios a la derecha.
 *
 * Un force-directed sobre esto sale en estrella y no dice de qué lado está
 * cada uno. Colocarlos por columnas contesta de un vistazo "de aquí me entra,
 * por aquí me sale", que es justo la pregunta.
 */
export function redDeFlujo(datos, id, recibeDe, pagaA, maxPorLado = 14) {
  const porId = new Map((datos?.nodes ?? []).map((n) => [n.id, n]))
  const centro = porId.get(id)
  if (!centro) return { nodes: [], edges: [] }

  const izquierda = recibeDe.slice(0, maxPorLado)
  const derecha = pagaA.slice(0, maxPorLado)

  const nodes = [
    { ...centro, lado: 'centro' },
    ...izquierda.map((x) => ({ ...porId.get(x.id), lado: 'izquierda', total: x.total })),
    ...derecha.map((x) => ({ ...porId.get(x.id), lado: 'derecha', total: x.total })),
  ].filter((n) => n && n.id)

  const dentro = new Set(nodes.map((n) => n.id))
  const edges = (datos?.edges ?? []).filter(
    (a) =>
      ESQUEMAS_DINERO.has(a.schema) &&
      ((a.source === id && dentro.has(a.target)) || (a.target === id && dentro.has(a.source))),
  )

  return { nodes, edges, recortadoIzquierda: recibeDe.length - izquierda.length, recortadoDerecha: pagaA.length - derecha.length }
}

/** Una frase que resuma la ficha, para encabezarla. */
export function resumenEnPalabras(area) {
  if (!area?.entidad) return ''
  const partes = []
  if (area.totalRecibido > 0) {
    partes.push(`recibe ${dineroCorto(area.totalRecibido)} de ${area.recibeDe.length}`
      + ` ${area.recibeDe.length === 1 ? 'pagador' : 'pagadores'}`)
  }
  if (area.totalPagado > 0) {
    partes.push(`reparte ${dineroCorto(area.totalPagado)} entre ${area.pagaA.length}`
      + ` ${area.pagaA.length === 1 ? 'receptor' : 'receptores'}`)
  }
  if (area.sanciones.length) {
    partes.push(`${area.sanciones.length} ${area.sanciones.length === 1 ? 'expediente sancionador' : 'expedientes sancionadores'}`)
  }
  if (!partes.length) return 'Sin movimientos de dinero en lo publicado.'
  return `${partes.join(' · ')}.`
}
