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

/**
 * Los parámetros que corresponden a un estado de la vista.
 *
 * `territorio` es la edición: «?t=Andalucía» es la portada o el mapa de lo que
 * pagan las administraciones andaluzas. Sólo en esas dos vistas; una ficha es
 * la misma se mire desde donde se mire.
 */
export function parametrosDeVista({ vista, clave, territorio, destacada, grupo, persona }) {
  const p = new URLSearchParams()
  /*
    Los cargos públicos son otra sección con su propia clave (`p`, de
    persona): una persona con cargo no es una entidad del mapa del dinero, y
    mezclarlas en `e` haría que un enlace a un secretario de Estado intentara
    abrir una ficha que no existe.
  */
  if (vista === 'cargos') {
    p.set('v', 'cargos')
    if (persona) p.set('p', persona)
    return p
  }
  if (vista === 'mapa') p.set('v', 'mapa')
  else if (vista === 'vecindario') p.set('v', 'red')
  if (clave && vista !== 'mapa') p.set('e', clave)
  /*
    Dentro del mapa, la entidad encendida (`e`) o, si no hay, el grupo abierto
    (`g`). El grupo se nombra por la clave de su entidad principal y no por su
    número: el número lo pone el agrupamiento y cambia entre volcados; la
    clave de una entidad no cambia.
  */
  if (vista === 'mapa' && destacada) p.set('e', destacada)
  else if (vista === 'mapa' && grupo) p.set('g', grupo)
  if (territorio && (vista === 'portada' || vista === 'mapa')) p.set('t', territorio)
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
  const t = (p.get('t') ?? '').trim()
  const conTerritorio = t ? { territorio: t } : {}
  if (v === 'cargos') {
    const persona = (p.get('p') ?? '').trim()
    return { vista: 'cargos', clave: '', ...(persona ? { persona } : {}) }
  }
  if (v === 'mapa') {
    const g = p.get('g') ?? ''
    return {
      vista: 'mapa',
      clave: '',
      ...(clave ? { destacada: clave } : g ? { grupo: g } : {}),
      ...conTerritorio,
    }
  }
  if (v === 'red' && clave) return { vista: 'vecindario', clave }
  if (clave) return { vista: 'ficha', clave }
  return { vista: 'portada', clave: '', ...conTerritorio }
}

/** ¿Estos dos estados son el mismo? Para no apilar entradas repetidas. */
export function mismoEstado(a, b) {
  return (
    a.vista === b.vista &&
    (a.clave ?? '') === (b.clave ?? '') &&
    (a.territorio ?? '') === (b.territorio ?? '') &&
    (a.destacada ?? '') === (b.destacada ?? '') &&
    (a.grupo ?? '') === (b.grupo ?? '') &&
    (a.persona ?? '') === (b.persona ?? '')
  )
}

/**
 * Qué hay que pintar para un estado pedido, sabiendo si su entidad existe.
 *
 * Vive aquí y no en el componente porque el orden de las comprobaciones se
 * equivocó una vez y no se notó: `?v=mapa` no lleva ninguna entidad, la
 * comprobación de «¿existe la clave?» iba por delante, y el enlace al mapa
 * caía siempre en la rama de enlace roto y abría la portada. El enlace al
 * mapa no llevaba al mapa, y ningún test lo decía porque esto estaba dentro
 * de un `<script setup>`, que no exporta nada.
 *
 * @param {{vista: string, clave?: string}} estado lo que pide la dirección.
 * @param {boolean} existe si la clave corresponde a algo de esta instantánea.
 * @returns {'portada'|'mapa'|'cargos'|'vecindario'|'ficha'}
 */
export function accionDeEstado({ vista, clave }, existe) {
  if (vista === 'mapa') return 'mapa'
  if (vista === 'cargos') return 'cargos'
  if (vista === 'portada') return 'portada'
  // Un enlace a algo que ya no está en esta instantánea: la portada dice más
  // que una ficha vacía, y el buscador queda a mano.
  if (!clave || !existe) return 'portada'
  return vista === 'vecindario' ? 'vecindario' : 'ficha'
}
