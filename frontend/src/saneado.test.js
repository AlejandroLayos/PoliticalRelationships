import { describe, expect, it } from 'vitest'
import { sanearImportes } from './saneado.js'

function marco(nAdjudicatarios, importe = '900000000') {
  const nodes = [
    {
      id: 'c',
      caption: 'ACUERDO MARCO',
      schema: 'Contract',
      properties: { budgetAmount: '900000000' },
    },
  ]
  const edges = []
  for (let i = 0; i < nAdjudicatarios; i += 1) {
    nodes.push({ id: `e${i}`, caption: `EMPRESA ${i}`, schema: 'Company', properties: {} })
    edges.push({
      id: `a${i}`,
      source: 'c',
      target: `e${i}`,
      amount: importe,
      schema: 'ContractAward',
      confidence: 1,
      status: 'asserted',
    })
  }
  return { nodes, edges }
}

describe('sanearImportes', () => {
  it('retira el importe repetido entre adjudicatarios del mismo contrato', () => {
    // 20 × 900 millones eran 18.000 millones, el 85 % del dinero del mapa, y
    // la portada publicaba «esta empresa recibió 908 millones de euros».
    const g = sanearImportes(marco(20))
    expect(g.edges.every((e) => e.amount === undefined)).toBe(true)
    expect(g.edges[0].properties.adjudicatariosQueComparten).toBe(20)
    expect(g.edges[0].properties.motivoImporteDudoso).toContain('acuerdo marco')
    expect(g.edges[0].confidence).toBe(0.5)
    expect(g.importesSaneados).toBe(20)
  })

  it('conserva la adjudicación: lo que se descarta es la cifra', () => {
    const g = sanearImportes(marco(3))
    expect(g.edges.map((e) => e.target).sort()).toEqual(['e0', 'e1', 'e2'])
  })

  it('un adjudicatario único conserva su importe', () => {
    const g = sanearImportes(marco(1))
    expect(g.edges[0].amount).toBe('900000000')
  })

  it('importes distintos en el mismo contrato se respetan', () => {
    const g = marco(0)
    g.nodes.push({ id: 'x', caption: 'X', schema: 'Company', properties: {} })
    g.nodes.push({ id: 'y', caption: 'Y', schema: 'Company', properties: {} })
    g.edges.push(
      { id: '1', source: 'c', target: 'x', amount: '1000', schema: 'ContractAward', confidence: 1 },
      { id: '2', source: 'c', target: 'y', amount: '2000', schema: 'ContractAward', confidence: 1 },
    )
    const s = sanearImportes(g)
    expect(s.edges.map((e) => e.amount)).toEqual(['1000', '2000'])
  })

  it('el mismo importe en contratos DISTINTOS no se toca', () => {
    // Dos obras de 50.000 € en dos expedientes distintos son dos obras de
    // 50.000 €. La repetición sólo significa algo dentro de un contrato.
    const datos = {
      nodes: [
        { id: 'c1', caption: 'OBRA 1', schema: 'Contract', properties: {} },
        { id: 'c2', caption: 'OBRA 2', schema: 'Contract', properties: {} },
        { id: 'e', caption: 'EMPRESA', schema: 'Company', properties: {} },
      ],
      edges: [
        { id: '1', source: 'c1', target: 'e', amount: '50000', schema: 'ContractAward', confidence: 1 },
        { id: '2', source: 'c2', target: 'e', amount: '50000', schema: 'ContractAward', confidence: 1 },
      ],
    }
    expect(sanearImportes(datos)).toBe(datos)
  })

  it('retira un importe imposible frente al presupuesto', () => {
    const datos = {
      nodes: [
        { id: 'c', caption: 'TRANSPORTE', schema: 'Contract', properties: { budgetAmount: '22000' } },
        { id: 'e', caption: 'EMPRESA', schema: 'Company', properties: {} },
      ],
      edges: [
        {
          id: 'a', source: 'c', target: 'e', amount: '1954023643.40',
          schema: 'ContractAward', confidence: 1,
        },
      ],
    }
    const g = sanearImportes(datos)
    expect(g.edges[0].amount).toBeUndefined()
    expect(g.edges[0].properties.importeSinInterpretar).toBe('1954023643.40')
    expect(g.edges[0].properties.motivoImporteDudoso).toContain('22000')
  })

  it('un importe algo por encima del presupuesto se respeta', () => {
    const datos = {
      nodes: [
        { id: 'c', caption: 'OBRA', schema: 'Contract', properties: { budgetAmount: '22000' } },
        { id: 'e', caption: 'EMPRESA', schema: 'Company', properties: {} },
      ],
      edges: [
        { id: 'a', source: 'c', target: 'e', amount: '26000', schema: 'ContractAward', confidence: 1 },
      ],
    }
    expect(sanearImportes(datos).edges[0].amount).toBe('26000')
  })

  it('no toca los pagos ni las sanciones', () => {
    // La regla es de adjudicaciones. Dos subvenciones del mismo importe al
    // mismo beneficiario no son un acuerdo marco: son dos subvenciones.
    const datos = {
      nodes: [
        { id: 'o', caption: 'ORG', schema: 'PublicBody', properties: {} },
        { id: 'p', caption: 'PARTIDO', schema: 'Organization', properties: {} },
      ],
      edges: [
        { id: '1', source: 'o', target: 'p', amount: '5000', schema: 'Payment', confidence: 1 },
        { id: '2', source: 'o', target: 'p', amount: '5000', schema: 'Payment', confidence: 1 },
        { id: '3', source: 'p', target: 'o', amount: '5000', schema: 'Debt', confidence: 1 },
      ],
    }
    const g = sanearImportes(datos)
    expect(g.edges.map((e) => e.amount)).toEqual(['5000', '5000', '5000'])
  })

  it('es idempotente sobre una instantánea ya corregida', () => {
    // La ingesta arreglada ya publica esas aristas sin `amount`. Esto no puede
    // volver a marcarlas ni cambiar nada.
    const g = sanearImportes(marco(5))
    const otra = sanearImportes(g)
    expect(otra).toBe(g)
    expect(otra.importesSaneados).toBe(5)
  })

  it('devuelve el mismo objeto si no hay nada que sanear', () => {
    const datos = marco(1)
    expect(sanearImportes(datos)).toBe(datos)
    expect(sanearImportes(undefined)).toBe(undefined)
    expect(sanearImportes({ nodes: [], edges: [] }).edges).toEqual([])
  })
})
