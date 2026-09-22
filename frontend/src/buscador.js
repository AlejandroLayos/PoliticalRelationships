/**
 * Cómo se parece un nombre a lo que alguien ha escrito.
 *
 * ## El problema
 *
 * La contratación pública española no publica por ayuntamiento: publica por
 * **órgano de contratación**. Quien busca «ayuntamiento de Móstoles» encuentra
 * una sola entrada —«Junta de Gobierno del Ayuntamiento de Móstoles»— y se
 * queda con la idea de que de su pueblo hay 931 mil euros y poco más. En la
 * base hay también el Hospital Universitario de Móstoles y una empresa de
 * reformas de Móstoles, pero ninguno de los dos contiene la frase entera, así
 * que con una búsqueda por subcadena no salen.
 *
 * Eso no es un hueco de datos: es que la frase que la gente escribe y la que
 * el Boletín publica no son la misma, y de las dos la que hay que ceder es la
 * nuestra.
 *
 * ## Los tres grados
 *
 * 3. El nombre contiene la frase entera. Es lo que se buscaba.
 * 4. (no existe)
 * 2. Están todas las palabras, en cualquier orden. «Móstoles ayuntamiento».
 * 1. Están las palabras DISTINTIVAS. «Ayuntamiento», «consejería» o «dirección
 *    general» las lleva media base y no distinguen nada; el topónimo o el
 *    nombre propio, sí. Éstos se enseñan aparte y con su rótulo, porque no es
 *    lo que se pidió: es lo que hay alrededor.
 *
 * Si la consulta no tiene ninguna palabra distintiva —alguien escribe
 * «ayuntamiento» a secas— no se relaja nada: relajar ahí devolvería media
 * base ordenada por dinero, que no contesta a nada.
 */

/** Quita acentos y mayúsculas. Duplica a propósito lo de `grafoLocal`. */
export function normaliza(t) {
  return (t || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
}

/**
 * Palabras que lleva media base y no distinguen a nadie.
 *
 * No es una lista de «palabras vacías» del castellano: es la lista de lo que
 * se repite en los nombres oficiales de los órganos de contratación
 * españoles. Por eso están aquí «consejería» y «dirección», que fuera de este
 * contexto son palabras con todo el contenido del mundo.
 */
export const PALABRAS_COMUNES = new Set([
  'de', 'del', 'la', 'el', 'los', 'las', 'y', 'e', 'a', 'en', 'para', 'por',
  'ayuntamiento', 'ayto', 'concello', 'udala', 'ajuntament',
  'consejeria', 'conselleria', 'conselleria', 'departamento', 'departament',
  'direccion', 'general', 'generalitat', 'junta', 'gobierno', 'govern',
  'servicio', 'servicios', 'servei', 'serveis', 'area', 'concejalia',
  'secretaria', 'tecnica', 'subdireccion', 'delegacion', 'diputacion',
  'gerencia', 'instituto', 'agencia', 'consorcio', 'entidad', 'publica',
  'publico', 'municipal', 'provincial', 'autonoma', 'estatal', 'nacional',
  'sa', 'sl', 'slu', 'sau', 'sl u', 'ute', 'sociedad', 'anonima', 'limitada',
])

/**
 * Descompone lo que se ha escrito.
 *
 * @returns {{frase: string, todas: string[], distintivas: string[]}}
 */
export function analizarConsulta(q) {
  const frase = normaliza(q).trim().replace(/\s+/g, ' ')
  const todas = frase.split(' ').filter(Boolean)
  // Una palabra de una o dos letras no distingue aunque no esté en la lista.
  const distintivas = todas.filter((p) => p.length > 2 && !PALABRAS_COMUNES.has(p))
  return { frase, todas, distintivas }
}

/**
 * Cuánto se parece `caption` a la consulta ya analizada. 0 es «no se parece».
 *
 * @param {string} caption
 * @param {{frase: string, todas: string[], distintivas: string[]}} consulta
 */
export function gradoDeCoincidencia(caption, consulta) {
  if (!consulta.frase) return 0
  const nombre = normaliza(caption)
  if (nombre.includes(consulta.frase)) return 3
  if (consulta.todas.every((p) => nombre.includes(p))) return 2
  if (consulta.distintivas.length && consulta.distintivas.every((p) => nombre.includes(p))) return 1
  return 0
}

/**
 * Lo que se enseña encima del grupo relajado, o cadena vacía si no hay grupo.
 *
 * Decirlo importa: sin rótulo, quien busca «ayuntamiento de Móstoles» y ve un
 * hospital y una empresa de reformas en la lista piensa que el buscador se ha
 * equivocado, no que le están enseñando lo que hay alrededor.
 */
export function rotuloRelajado(consulta) {
  if (!consulta.distintivas.length) return ''
  return `Otros resultados con «${consulta.distintivas.join(' ')}»`
}
