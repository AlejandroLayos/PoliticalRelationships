import { crearGrafoLocal } from './grafoLocal.js'

/**
 * Conjunto de DEMOSTRACIÓN. Datos inventados.
 *
 * Ninguna entidad de este fichero corresponde a un organismo, empresa, partido
 * o persona real. Los nombres son deliberadamente ficticios —"Ministerio de
 * Ejemplo", "Constructora Ficticia SL"— para que nadie pueda confundirlos con
 * un hecho.
 *
 * Sirve para que la interfaz se pueda ver y probar sin backend. La estructura
 * sí es la real: los mismos esquemas FollowTheMoney, las mismas direcciones de
 * arista y los mismos campos `confidence` y `status` que devuelve la API.
 *
 * En cuanto haya una API conectada (`VITE_API_URL`), esto no se usa.
 */

const E = (id, schema, caption, extra = {}) => ({ id, schema, caption, ...extra })

const ENTIDADES = [
  E('org-hacienda', 'PublicBody', 'Ministerio de Ejemplo'),
  E('org-dgpruebas', 'PublicBody', 'Dirección General de Pruebas'),
  E('org-ccaa', 'PublicBody', 'Consejería de Muestra'),
  E('org-ayto', 'PublicBody', 'Ayuntamiento de Villa Ficticia'),

  E('emp-constructora', 'Company', 'Constructora Ficticia SL', { nif: 'B00000001' }),
  E('emp-obras', 'Company', 'Obras y Servicios Imaginarios SA', { nif: 'A00000002' }),
  E('emp-consultora', 'Company', 'Consultora Hipotética SL', { nif: 'B00000003' }),
  E('emp-medios', 'Company', 'Grupo Editorial Inventado SA', { nif: 'A00000004' }),
  E('emp-energia', 'Company', 'Energías Supuestas SL', { nif: 'B00000005' }),
  E('emp-limpieza', 'Company', 'Limpiezas Hipotéticas SL', { nif: 'B00000006' }),

  E('ong-cultura', 'LegalEntity', 'Asociación Cultural de Ejemplo'),
  E('ong-deporte', 'LegalEntity', 'Club Deportivo Ficticio'),

  E('par-alfa', 'Organization', 'Partido Alfa (ficticio)', { nif: 'G00000010' }),
  E('par-beta', 'Organization', 'Partido Beta (ficticio)', { nif: 'G00000011' }),

  E('per-uno', 'Person', 'Persona Ejemplo Primera'),
  E('per-dos', 'Person', 'Persona Ejemplo Segunda'),

  E('con-001', 'Contract', 'Renovación del alumbrado de Villa Ficticia'),
  E('con-002', 'Contract', 'Servicio de limpieza viaria 2025'),
  E('con-003', 'Contract', 'Asistencia técnica para el plan de muestra'),

  E('pos-alcaldia', 'Position', 'Alcaldía de Villa Ficticia'),
]

const A = (id, schema, source, target, extra = {}) => ({
  id,
  schema,
  source,
  target,
  confidence: 1,
  status: 'asserted',
  ...extra,
})

const ARISTAS = [
  // Subvenciones: organismo -> beneficiario
  A('a1', 'Payment', 'org-hacienda', 'emp-constructora', { amount: '250000.00', currency: 'EUR', start_date: '2025-03-14' }),
  A('a2', 'Payment', 'org-dgpruebas', 'emp-consultora', { amount: '75000.00', currency: 'EUR', start_date: '2025-04-02' }),
  A('a3', 'Payment', 'org-ccaa', 'ong-cultura', { amount: '12000.00', currency: 'EUR', confidence: 0.7, start_date: '2025-02-10' }),
  A('a4', 'Payment', 'org-ccaa', 'ong-deporte', { amount: '8500.00', currency: 'EUR', confidence: 0.7 }),
  A('a5', 'Payment', 'org-hacienda', 'emp-medios', { amount: '430000.00', currency: 'EUR', start_date: '2025-01-20' }),
  A('a6', 'Payment', 'org-hacienda', 'par-alfa', { amount: '1200000.00', currency: 'EUR', start_date: '2025-01-05' }),
  A('a7', 'Payment', 'org-hacienda', 'par-beta', { amount: '980000.00', currency: 'EUR', start_date: '2025-01-05' }),

  // Contratación: Contract -> adjudicatario (dirección canónica de FtM)
  A('a8', 'ContractAward', 'con-001', 'emp-constructora', { amount: '90078.51', currency: 'EUR', start_date: '2025-05-11' }),
  A('a9', 'ContractAward', 'con-001', 'emp-obras', { amount: '45000.00', currency: 'EUR', start_date: '2025-05-11' }),
  A('a10', 'ContractAward', 'con-002', 'emp-limpieza', { amount: '310000.00', currency: 'EUR', start_date: '2025-06-01' }),
  A('a11', 'ContractAward', 'con-003', 'emp-consultora', { amount: '58000.00', currency: 'EUR', start_date: '2025-07-15' }),

  // Consejos de administración
  A('a12', 'Directorship', 'per-uno', 'emp-constructora'),
  A('a13', 'Directorship', 'per-uno', 'emp-energia'),
  A('a14', 'Directorship', 'per-dos', 'emp-medios'),

  // Cargo público: Person -> Position
  A('a15', 'Occupancy', 'per-dos', 'pos-alcaldia', { start_date: '2023-06-17' }),

  // Participación accionarial
  A('a16', 'Ownership', 'emp-energia', 'emp-medios', { confidence: 0.85 }),

  // Conexión observada cuya naturaleza no está clara. Se dibuja distinta y
  // lleva status 'inferred': es lo que el proyecto NO puede presentar como
  // probado.
  A('a17', 'UnknownLink', 'emp-constructora', 'par-alfa', { confidence: 0.45, status: 'inferred' }),
  A('a18', 'UnknownLink', 'emp-medios', 'par-beta', { confidence: 0.38, status: 'inferred' }),
]

// El órgano de contratación va como propiedad del contrato, igual que en la
// API real: en FollowTheMoney no existe arista órgano->contrato.
const AUTORIDAD = {
  'con-001': 'org-ayto',
  'con-002': 'org-ayto',
  'con-003': 'org-ccaa',
}

const PROCEDENCIA_FALSA = [
  {
    source_id: 'demostracion',
    url: 'https://example.invalid/documento-de-ejemplo',
    content_hash: '0'.repeat(64),
    retrieved_at: '2026-01-01T00:00:00Z',
    extractor_version: 'demo/1',
    excerpt: 'Documento de ejemplo. No corresponde a ninguna fuente real.',
  },
]

const _grafo = crearGrafoLocal({
  nodes: ENTIDADES.map((e) => ({
    ...e,
    properties: AUTORIDAD[e.id] ? { authority: AUTORIDAD[e.id] } : {},
  })),
  edges: ARISTAS,
  provenance: Object.fromEntries(ENTIDADES.map((e) => [e.id, PROCEDENCIA_FALSA])),
})

export const buscarDemo = (q, limite) => _grafo.buscar(q, limite)
export const entidadDemo = (id) => _grafo.entidad(id)
export const vecinosDemo = (id, profundidad) => _grafo.vecinos(id, profundidad)

export const ENTIDAD_INICIAL = 'emp-constructora'
