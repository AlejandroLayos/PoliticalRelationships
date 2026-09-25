/**
 * Cómo se presenta la procedencia de una ficha.
 *
 * «Sin procedencia no se persiste» es la primera invariante del proyecto, así
 * que enseñar el documento del que sale cada cifra no es un adorno: es la
 * diferencia entre publicar un dato y afirmarlo sin más. Aquí vive la parte
 * que se puede probar aparte; el componente sólo pinta.
 */

/**
 * Nombre legible de un documento del feed.
 *
 * Los ficheros de sindicación de la Plataforma se llaman
 * `PlataformasAgregadasSinMenores_20260901_030025_1.atom`: lo único que
 * distingue a uno de otro son la marca de tiempo y el número de página, y van
 * al final. Recortando por la izquierda salían cinco enlaces que empezaban
 * todos por «…masAgregadasSinMenores», ocupaban dos renglones cada uno y no se
 * distinguía ninguno.
 *
 * La marca de tiempo se LEE del nombre del fichero, no se inventa: es el
 * propio nombre del documento. Si el patrón no casa, se enseña tal cual.
 */
const SELLO = /(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})\d{2}(?:_(\d+))?/
const MAX = 40

export function nombreDocumento(url) {
  let hoja = url
  try {
    hoja = new URL(url).pathname.split('/').filter(Boolean).pop() || url
  } catch {
    hoja = url
  }
  const m = SELLO.exec(hoja)
  if (!m) return hoja.length > MAX ? `${hoja.slice(0, MAX - 1)}…` : hoja
  const [, a, mes, d, h, min, pagina] = m
  const cuando = `${Number(d)}/${Number(mes)}/${a} ${h}:${min}`
  return pagina ? `${cuando} · pág. ${pagina}` : cuando
}

/** La fecha de descarga, en corto. Vacío si no se puede leer. */
export function fechaCorta(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('es-ES')
}

/**
 * `placsp` no le dice nada a nadie; el nombre de la fuente, sí.
 *
 * Las fuentes vienen en la cabecera del volcado, no en el grafo, así que hay
 * que pasárselas: sin ellas la ficha decía «29 documentos guardados de placsp».
 */
export function nombreFuente(fuentes, id) {
  return (fuentes ?? []).find((f) => f.id === id)?.name ?? id
}

/**
 * La sigla con que se conoce cada fuente, para su sello.
 *
 * «Base de Datos Nacional de Subvenciones» no cabe en un sello —en la ficha
 * se salía del panel—; BDNS es como la llama todo el que la usa, y el nombre
 * entero está en el detalle. Una fuente sin sigla conocida sale con su
 * nombre, o con su identificador si tampoco hay nombre.
 */
const SIGLAS = { bdns: 'BDNS', placsp: 'PLACSP', tcu: 'Tribunal de Cuentas' }

export function siglaFuente(fuentes, id) {
  return SIGLAS[id] ?? nombreFuente(fuentes, id)
}

/** «A», «A y B», «A, B y C». */
export function enumerar(nombres) {
  const unicos = [...new Set(nombres)].filter(Boolean)
  if (unicos.length <= 1) return unicos[0] ?? ''
  return `${unicos.slice(0, -1).join(', ')} y ${unicos[unicos.length - 1]}`
}
