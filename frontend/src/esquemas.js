/** Colores y etiquetas de los esquemas FollowTheMoney que usamos. */

export const COLOR_POR_DEFECTO = '#8b93a7'

export const COLOR_POR_ESQUEMA = {
  PublicBody: '#e8703a',    // naranja: dinero público
  Organization: '#c94f7c',  // magenta: partidos y asociaciones
  Company: '#3d8bd4',       // azul: empresas
  LegalEntity: '#6aa9d9',   // azul claro: jurídica sin tipo confirmado
  Person: '#4bb47f',        // verde: personas físicas
  Contract: '#b08cd9',      // violeta: expedientes
  Position: '#d9b04b',      // amarillo: cargos públicos
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
export function etiquetaArista(s) {
  return NOMBRE_ARISTA[s] ?? s
}
