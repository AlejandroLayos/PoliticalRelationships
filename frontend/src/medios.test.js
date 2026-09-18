import { describe, expect, it } from 'vitest'
import { contratosDeMedios, esCpvDeMedios, etiquetaCpv } from './medios.js'

function grafo() {
  return {
    nodes: [
      { id: 'org', caption: 'AGENCIA DE TURISMO', schema: 'PublicBody', properties: {} },
      { id: 'org2', caption: 'AYUNTAMIENTO', schema: 'PublicBody', properties: {} },
      {
        id: 'c1', caption: 'Patrocinio publicitario para la promoción del turismo', schema: 'Contract',
        properties: { cpvCode: '79341000', sourceUrl: 'https://ejemplo/1' },
      },
      {
        id: 'c2', caption: 'Inserción de publicidad institucional en medios', schema: 'Contract',
        properties: { cpvCode: '79341200' },
      },
      // Consultoría de RRHH: la familia 7941 entera NO es publicidad.
      { id: 'c3', caption: 'Consultoría de recursos humanos', schema: 'Contract', properties: { cpvCode: '79414000' } },
      // Organización de congresos: roza el asunto y no lo es.
      { id: 'c4', caption: 'Organización de un congreso', schema: 'Contract', properties: { cpvCode: '79952000' } },
      { id: 'medio', caption: 'GRUPO EDITORIAL SA', schema: 'Company', properties: {} },
      { id: 'agencia', caption: 'AGENCIA DE MEDIOS SL', schema: 'Company', properties: {} },
      { id: 'rrhh', caption: 'CONSULTORA RRHH SL', schema: 'Company', properties: {} },
    ],
    edges: [
      { id: 'u1', source: 'org', target: 'c1', schema: 'UnknownLink' },
      { id: 'u2', source: 'org2', target: 'c2', schema: 'UnknownLink' },
      { id: 'u3', source: 'org', target: 'c3', schema: 'UnknownLink' },
      { id: 'u4', source: 'org', target: 'c4', schema: 'UnknownLink' },
      { id: 'a1', source: 'c1', target: 'medio', amount: '120000', schema: 'ContractAward', confidence: 1 },
      { id: 'a2', source: 'c2', target: 'agencia', amount: '80000', schema: 'ContractAward', confidence: 1 },
      { id: 'a3', source: 'c3', target: 'rrhh', amount: '900000', schema: 'ContractAward', confidence: 1 },
      { id: 'a4', source: 'c4', target: 'agencia', amount: '500000', schema: 'ContractAward', confidence: 1 },
    ],
  }
}

describe('etiquetaCpv', () => {
  it('reconoce los códigos de publicidad y medios', () => {
    expect(esCpvDeMedios('79341000')).toBe(true)
    expect(etiquetaCpv('92220000')).toBe('Servicios de televisión')
  })

  it('tolera el dígito de control', () => {
    expect(etiquetaCpv('79341000-3')).toBe('Publicidad')
  })

  it('NO cuela la familia 7941, que es consultoría de gestión', () => {
    // El error que esto evita: filtrar por prefijo metía consultoras de RRHH
    // (79414000) y de evaluación (79419000) en una lista titulada «quién cobra
    // de la publicidad institucional».
    expect(esCpvDeMedios('79414000')).toBe(false)
    expect(esCpvDeMedios('79419000')).toBe(false)
    expect(esCpvDeMedios('79411000')).toBe(false)
  })

  it('deja fuera lo que roza el asunto sin serlo', () => {
    expect(esCpvDeMedios('79952000')).toBe(false) // eventos
    expect(esCpvDeMedios('79342000')).toBe(false) // marketing genérico
    expect(esCpvDeMedios('')).toBe(false)
    expect(esCpvDeMedios(undefined)).toBe(false)
  })
})

describe('contratosDeMedios', () => {
  const m = contratosDeMedios(grafo())

  it('sólo recoge los contratos de publicidad y medios', () => {
    expect(m.nContratos).toBe(2)
    expect(m.contratos.map((c) => c.empresa)).toEqual(['GRUPO EDITORIAL SA', 'AGENCIA DE MEDIOS SL'])
    expect(m.total).toBe(200000)
  })

  it('un contrato de RRHH de 900.000 € no infla el total de publicidad', () => {
    expect(m.total).toBe(200000)
    expect(m.contratos.map((c) => c.empresa)).not.toContain('CONSULTORA RRHH SL')
  })

  it('cada contrato conserva sus dos extremos y su enlace', () => {
    const c = m.contratos[0]
    expect(c.organo).toBe('AGENCIA DE TURISMO')
    expect(c.empresa).toBe('GRUPO EDITORIAL SA')
    expect(c.etiqueta).toBe('Publicidad')
    expect(c.url).toBe('https://ejemplo/1')
  })

  it('agrega por empresa y por organismo', () => {
    expect(m.porEmpresa[0]).toMatchObject({ caption: 'GRUPO EDITORIAL SA', total: 120000, n: 1 })
    expect(m.porOrganismo.map((o) => o.caption)).toEqual(['AGENCIA DE TURISMO', 'AYUNTAMIENTO'])
    // La agencia cobró 500.000 € de un congreso, que no cuenta aquí.
    expect(m.porEmpresa.find((e) => e.caption === 'AGENCIA DE MEDIOS SL').total).toBe(80000)
  })

  it('no revienta sin datos ni sin contratos de medios', () => {
    expect(contratosDeMedios(undefined).contratos).toEqual([])
    expect(contratosDeMedios({ nodes: [], edges: [] }).total).toBe(0)
  })
})
