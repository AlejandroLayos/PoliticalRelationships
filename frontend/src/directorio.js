/**
 * Por dónde se empieza.
 *
 * El mapa entero es una textura, no un diagrama: dos mil entidades en mil
 * píxeles son dos píxeles cuadrados cada una, y por mucho que se afine el
 * layout eso no se lee. Sirve para ver la forma y para hacerse una idea del
 * tamaño; no sirve para empezar a investigar.
 *
 * Lo que sí sirve es una lista ordenada. Quién reparte más dinero público,
 * quién más cobra, qué empresas cobran de más administraciones distintas, qué
 * partidos tienen expedientes del Tribunal de Cuentas. Eso se lee de un
 * vistazo, se ordena solo y lleva a una ficha.
 *
 * ## Todo se calcula sobre el grafo colapsado
 *
 * Igual que la ficha: entre un organismo y la empresa que cobra siempre hay un
 * expediente de por medio, y sin puentearlo «quién reparte más dinero» sale
 * contestado con una lista de contratos.
 *
 * ## Lo que estas listas NO dicen
 *
 * Que alguien encabece un ranking no significa nada irregular. Un servicio de
 * salud reparte más dinero que un ayuntamiento pequeño porque compra
 * medicamentos para una comunidad entera. Los textos de la interfaz tienen que
 * decirlo, porque una lista ordenada por dinero se lee sola como una lista de
 * sospechosos, y eso sería exactamente el falso positivo que este proyecto no
 * se puede permitir.
 */

import { aNumero } from './nucleos.js'

const ESQUEMAS_DINERO = new Set(['Payment', 'ContractAward'])
const ESQUEMAS_SANCION = new Set(['Debt'])

/** Tipos que son actores. Un expediente no encabeza ningún ranking. */
const ACTORES = new Set(['PublicBody', 'Organization', 'Company', 'LegalEntity', 'Person'])

function ficha(n) {
  return {
    id: n.id,
    caption: n.caption,
    schema: n.schema,
    extranjera: Boolean(n.properties?.entidad_extranjera),
    partido: Boolean(n.properties?.partido_politico),
    total: 0,
    contrapartes: new Set(),
  }
}

function rematar(mapa, limite) {
  return [...mapa.values()]
    .map((x) => ({ ...x, n: x.contrapartes.size, contrapartes: undefined }))
    .sort((a, b) => b.total - a.total || b.n - a.n)
    .slice(0, limite)
}

/**
 * Construye todas las listas de una pasada.
 *
 * `datos` es el grafo YA colapsado. `limite` acota cada lista; el resto se
 * alcanza por la búsqueda y por el mapa.
 */
export function construirDirectorio(datos, { limite = 25 } = {}) {
  const nodos = (datos?.nodes ?? []).filter((n) => ACTORES.has(n.schema))
  const porId = new Map(nodos.map((n) => [n.id, n]))
  const aristas = datos?.edges ?? []

  const paga = new Map()
  const cobra = new Map()
  const sancion = new Map()
  let dineroTotal = 0
  let totalSancionado = 0
  let nOperaciones = 0

  function toca(mapa, id, otroId, importe) {
    const n = porId.get(id)
    if (!n) return null
    if (!mapa.has(id)) mapa.set(id, ficha(n))
    const f = mapa.get(id)
    f.total += importe
    f.contrapartes.add(otroId)
    return f
  }

  for (const a of aristas) {
    const importe = aNumero(a.amount)

    if (ESQUEMAS_SANCION.has(a.schema)) {
      // Deudor -> acreedor. El sancionado es el origen; el Tribunal de Cuentas
      // no «cobra» de nadie en el sentido de estas listas.
      const f = toca(sancion, a.source, a.target, importe)
      if (f) {
        f.expedientes = (f.expedientes ?? 0) + 1
        totalSancionado += importe
      }
      continue
    }
    if (!ESQUEMAS_DINERO.has(a.schema)) continue
    if (!porId.has(a.source) || !porId.has(a.target)) continue

    toca(paga, a.source, a.target, importe)
    toca(cobra, a.target, a.source, importe)
    dineroTotal += importe
    nOperaciones += 1
  }

  // Transversales: cobran de MUCHAS administraciones distintas, que no es lo
  // mismo que cobrar mucho. Un proveedor de una sola administración puede
  // facturar más; el que aparece en diez es el que ha hecho el recorrido.
  const transversales = [...cobra.values()]
    .filter((x) => x.contrapartes.size >= 2)
    .map((x) => ({ ...x, n: x.contrapartes.size, contrapartes: undefined }))
    .sort((a, b) => b.n - a.n || b.total - a.total)
    .slice(0, limite)

  const extranjeras = [...cobra.values(), ...paga.values()]
    .filter((x) => x.extranjera)
    .reduce((m, x) => {
      // Una entidad puede estar en los dos mapas; se queda la suma de lo que
      // mueve, con sus contrapartes unidas.
      const prev = m.get(x.id)
      if (prev) {
        prev.total += x.total
        for (const c of x.contrapartes) prev.contrapartes.add(c)
      } else {
        m.set(x.id, { ...x, contrapartes: new Set(x.contrapartes) })
      }
      return m
    }, new Map())

  const sancionados = [...sancion.values()]
    .map((x) => ({ ...x, n: x.contrapartes.size, contrapartes: undefined }))
    .sort((a, b) => b.total - a.total || (b.expedientes ?? 0) - (a.expedientes ?? 0))
    .slice(0, limite)

  return {
    pagadores: rematar(paga, limite),
    receptores: rematar(cobra, limite),
    transversales,
    extranjeras: rematar(extranjeras, limite),
    sancionados,
    totales: {
      dineroTotal,
      nOperaciones,
      nActores: nodos.length,
      nPartidos: nodos.filter((n) => n.properties?.partido_politico).length,
      nExtranjeras: nodos.filter((n) => n.properties?.entidad_extranjera).length,
      nSancionados: sancion.size,
      totalSancionado,
    },
  }
}
