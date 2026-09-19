/**
 * Colores y etiquetas de los esquemas FollowTheMoney que usamos.
 *
 * Los colores están MEDIDOS. La tabla anterior tenía seis tonos elegidos a
 * ojo y no pasaba: `#6aa9d9` («persona jurídica») y `#3d8bd4` («empresa»)
 * estaban a ΔE 9,8 en visión NORMAL —el suelo es 15—, o sea que dos tipos
 * distintos se veían casi del mismo color sin necesidad de ninguna
 * deficiencia de visión; con deuteranopia eran el mismo color.
 *
 * Ahora son tres, y los tres pasan las seis comprobaciones con todos los
 * pares en juego, que es el caso de este mapa —se ven todos a la vez—:
 * peor par ΔE 9,4 con deuteranopia, 20,9 en visión normal, contraste ≥ 3:1.
 *
 * Tres y no cinco porque con cuatro o más no hay orden que pase todos los
 * pares. Las dos fusiones son deliberadas y dicen algo:
 *
 * - `LegalEntity` comparte el azul con `Company`: a efectos de este mapa son
 *   lo mismo, alguien privado que cobra dinero público. La diferencia la dice
 *   la etiqueta, que es donde tiene que estar.
 * - `Contract` va en gris porque no es un actor: es el papel que une al
 *   órgano que adjudica con la empresa que cobra.
 *
 * `Person` conserva entrada por si un conector la crea, pero no se publica
 * nunca (spec §12), así que no gasta un color categórico.
 */

/** Gris de lo que no es un actor. */
export const COLOR_POR_DEFECTO = '#6f6f78'

export const COLOR_POR_ESQUEMA = {
  PublicBody: '#d95926', // naranja: dinero público
  Company: '#3987e5', // azul: quien cobra
  LegalEntity: '#3987e5', // el mismo azul: también es quien cobra
  Organization: '#199e70', // verde azulado: partidos y asociaciones
  Person: '#6f6f78', // no se publica; si aparece, no finge ser una serie
  Contract: '#6f6f78', // el expediente no es un actor
  Position: '#6f6f78',
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
