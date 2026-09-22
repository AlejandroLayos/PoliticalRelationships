/**
 * El estado de la vista, en la URL.
 *
 * Hasta ahora toda la web vivía en la misma dirección: daba igual si estabas
 * en la portada, en el mapa o en la ficha de un ayuntamiento, la barra del
 * navegador decía lo mismo. Eso significa tres cosas, y las tres importan más
 * aquí que en otros sitios:
 *
 * - No se puede MANDAR nada. El sentido de esto es que alguien encuentre algo
 *   y se lo pase a otro; sin enlace, lo único que puede mandar es una captura.
 * - El botón de atrás del navegador salía de la web en vez de volver.
 * - Recargar te devolvía a la portada.
 *
 * ## Por qué la clave y no el identificador
 *
 * El `id` de una entidad es un UUID que se genera en cada ingesta, y la base
 * se levanta de cero todas las noches. Un enlace con el UUID funcionaría hoy
 * y no mañana — y sería peor que no tener enlace, porque no avisa: lleva a
 * «no encontrada» sin decir que el dato sigue ahí con otro número.
 *
 * `clave` es la que hace idempotente la ingesta (`nif:B12345678`,
 * `bdns:organo:1234`) y por definición no cambia entre volcados.
 */

/** Los parámetros que corresponden a un estado de la vista. */
export function parametrosDeVista({ vista, clave }) {
  const p = new URLSearchParams()
  if (vista === 'mapa') p.set('v', 'mapa')
  else if (vista === 'vecindario') p.set('v', 'red')
  if (clave && vista !== 'mapa') p.set('e', clave)
  return p
}

/** La dirección completa de un estado, relativa a la ruta actual. */
export function direccionDeVista(estado, ruta = '/') {
  const p = parametrosDeVista(estado)
  const cadena = p.toString()
  return cadena ? `${ruta}?${cadena}` : ruta
}

/**
 * Lee el estado de una cadena de búsqueda.
 *
 * Tolerante a propósito: una `v` que no conocemos cae en la portada en vez de
 * dejar la web en un estado imposible. Un enlace viejo o mal copiado enseña
 * algo, no un error.
 */
export function vistaDeParametros(busqueda) {
  const p = new URLSearchParams(busqueda ?? '')
  const clave = p.get('e') ?? ''
  const v = p.get('v') ?? ''
  if (v === 'mapa') return { vista: 'mapa', clave: '' }
  if (v === 'red' && clave) return { vista: 'vecindario', clave }
  if (clave) return { vista: 'ficha', clave }
  return { vista: 'portada', clave: '' }
}

/** ¿Estos dos estados son el mismo? Para no apilar entradas repetidas. */
export function mismoEstado(a, b) {
  return a.vista === b.vista && (a.clave ?? '') === (b.clave ?? '')
}
