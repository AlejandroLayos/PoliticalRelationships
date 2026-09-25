/**
 * Colores y etiquetas de los esquemas FollowTheMoney que usamos.
 *
 * ## El color es dato
 *
 * Tres tonos, y los tres dicen QUIÉN es cada cosa: administración (quien
 * paga), empresa (quien cobra) y partido u organización. En toda la web
 * significan lo mismo —en las listas, en el flujo de la ficha, en el visor de
 * red—, así que se aprenden una vez. Ver docs/diseno.md.
 *
 * Están medidos con daltonismo simulado y CIEDE2000, todos los pares a la
 * vez: peor par ΔE 22,9 con deuteranopia y 32,4 en visión normal (la paleta
 * anterior daba 9,4 con deuteranopia). Tres y no más: con cuatro no hay
 * juego que pase todos los pares.
 *
 * Dos fusiones deliberadas:
 *
 * - `LegalEntity` comparte el azul con `Company`: a efectos de este mapa son
 *   lo mismo, alguien privado que cobra dinero público.
 * - `Contract` va en gris porque no es un actor: es el papel que une al
 *   órgano que adjudica con la empresa que cobra.
 *
 * `Person` conserva entrada por si un conector la crea, pero no se publica
 * nunca (spec §12), así que no gasta un color.
 *
 * ## Dos formas del mismo color
 *
 * - `VAR_POR_ESQUEMA` da una variable CSS. Es lo que usa todo lo que se pinta
 *   con HTML o SVG: sobre papel sale el tono de papel y dentro del visor el
 *   del visor, sin que el componente tenga que saber dónde está.
 * - `COLOR_POR_ESQUEMA` da el hexadecimal del visor, para el lienzo de Sigma,
 *   que pinta con WebGL y no sabe leer una variable CSS.
 */

/** Gris de lo que no es un actor, en el visor. */
export const COLOR_POR_DEFECTO = '#7b7a80'

/** Hexadecimales del VISOR. Sólo para el lienzo; en HTML, `VAR_POR_ESQUEMA`. */
export const COLOR_POR_ESQUEMA = {
  PublicBody: '#e5703d', // administración
  Company: '#5d9ded', // empresa
  LegalEntity: '#5d9ded', // el mismo azul: también es quien cobra
  Organization: '#35b28c', // partido u organización
  Person: '#7b7a80', // no se publica; si aparece, no finge ser una serie
  Contract: '#7b7a80', // el expediente no es un actor
  Position: '#7b7a80',
}

/** Qué tipo de actor es cada esquema: el nombre de su token de color. */
export const TIPO_POR_ESQUEMA = {
  PublicBody: 'adm',
  Company: 'emp',
  LegalEntity: 'emp',
  Organization: 'par',
  Person: 'neutro',
  Contract: 'neutro',
  Position: 'neutro',
}

/** Cómo se llama cada tipo en una leyenda. */
export const NOMBRE_TIPO = {
  adm: 'Administración',
  emp: 'Empresa',
  par: 'Partido u organización',
  neutro: 'Otro',
}

/** 'adm', 'emp', 'par' o 'neutro'. */
export function tipoDe(esquema) {
  return TIPO_POR_ESQUEMA[esquema] ?? 'neutro'
}

/**
 * De qué está hecho un grupo: la parte de cada tipo, por número de
 * entidades, en el orden fijo adm, emp, par, neutro y sin los que no hay.
 *
 * @param {Record<string, number>} porEsquema cuántas entidades de cada esquema
 * @returns {{tipo: string, parte: number}[]}
 */
export function mezclaDeTipos(porEsquema) {
  const cuenta = { adm: 0, emp: 0, par: 0, neutro: 0 }
  let total = 0
  for (const [esquema, n] of Object.entries(porEsquema ?? {})) {
    cuenta[tipoDe(esquema)] += n
    total += n
  }
  if (!total) return []
  return Object.entries(cuenta)
    .filter(([, n]) => n > 0)
    .map(([tipo, n]) => ({ tipo, parte: n / total }))
}

/** El token CSS de cada tipo. Sirve igual en papel y en el visor. */
export const VAR_POR_ESQUEMA = Object.fromEntries(
  Object.entries(TIPO_POR_ESQUEMA).map(([esquema, tipo]) => [esquema, `var(--${tipo})`]),
)

/** El color de un tipo, para HTML y SVG. */
export function colorTipo(esquema) {
  return `var(--${tipoDe(esquema)})`
}

export const NOMBRE_ESQUEMA = {
  PublicBody: 'Organismo público',
  Organization: 'Organización',
  Company: 'Empresa',
  LegalEntity: 'Persona jurídica',
  Person: 'Persona',
  Contract: 'Contrato',
  Position: 'Cargo público',
  Project: 'Proyecto',
  Document: 'Documento',
}

export const NOMBRE_ARISTA = {
  Payment: 'Pago / subvención',
  ContractAward: 'Adjudicación',
  Ownership: 'Participación',
  Directorship: 'Cargo en consejo',
  Occupancy: 'Ocupa el cargo',
  Membership: 'Pertenencia',
  Employment: 'Empleo',
  Representation: 'Representación',
  UnknownLink: 'Conexión sin clasificar',
}

export const NOMBRE_ESTADO = {
  asserted: 'Afirmado por la fuente',
  inferred: 'Inferido por Sinapsis',
  disputed: 'En disputa',
  retracted: 'Retirado',
}

export function etiquetaEsquema(s) {
  return NOMBRE_ESQUEMA[s] ?? s
}

/**
 * En plural. Los nombres llevan adjetivo y no valen con una `s` al final:
 * «8 persona jurídica» y «21 organismo público» es lo que se estaba leyendo
 * en el resumen de cada núcleo.
 */
const PLURAL_ESQUEMA = {
  PublicBody: 'organismos públicos',
  Organization: 'organizaciones',
  Company: 'empresas',
  LegalEntity: 'personas jurídicas',
  Person: 'personas',
  Contract: 'expedientes',
}

export function etiquetaEsquemaPlural(s, n) {
  if (n === 1) return etiquetaEsquema(s).toLowerCase()
  return PLURAL_ESQUEMA[s] ?? `${etiquetaEsquema(s).toLowerCase()}s`
}
export function etiquetaArista(s) {
  return NOMBRE_ARISTA[s] ?? s
}
