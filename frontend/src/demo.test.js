import { describe, expect, it } from 'vitest'
import { buscarDemo, entidadDemo, vecinosDemo, ENTIDAD_INICIAL } from './demo.js'

describe('conjunto de demostración', () => {
  it('la entidad inicial existe', () => {
    expect(() => entidadDemo(ENTIDAD_INICIAL)).not.toThrow()
  })

  it('la búsqueda ignora acentos y mayúsculas', () => {
    const a = buscarDemo('energias').results
    const b = buscarDemo('ENERGÍAS').results
    expect(a.length).toBeGreaterThan(0)
    expect(a.map((e) => e.id)).toEqual(b.map((e) => e.id))
  })

  it('expande la ego-red nivel a nivel', () => {
    const uno = vecinosDemo(ENTIDAD_INICIAL, 1)
    const dos = vecinosDemo(ENTIDAD_INICIAL, 2)
    expect(uno.nodes.length).toBeGreaterThan(1)
    expect(dos.nodes.length).toBeGreaterThan(uno.nodes.length)
    expect(uno.nodes.find((n) => n.id === ENTIDAD_INICIAL).depth).toBe(0)
  })

  it('no repite nodos aunque el grafo tenga ciclos', () => {
    const v = vecinosDemo(ENTIDAD_INICIAL, 3)
    const ids = v.nodes.map((n) => n.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('toda arista referencia nodos presentes', () => {
    const v = vecinosDemo(ENTIDAD_INICIAL, 3)
    const ids = new Set(v.nodes.map((n) => n.id))
    for (const a of v.edges) {
      expect(ids.has(a.source), `origen ${a.source} ausente`).toBe(true)
      expect(ids.has(a.target), `destino ${a.target} ausente`).toBe(true)
    }
  })

  it('toda arista lleva confianza y estado', () => {
    // Invariante 5: nada inferido puede presentarse como probado.
    for (const a of vecinosDemo(ENTIDAD_INICIAL, 3).edges) {
      expect(typeof a.confidence).toBe('number')
      expect(a.confidence).toBeGreaterThanOrEqual(0)
      expect(a.confidence).toBeLessThanOrEqual(1)
      expect(a.status).toBeTruthy()
    }
  })

  it('hay al menos una arista inferida, para poder ver cómo se dibuja', () => {
    const v = vecinosDemo(ENTIDAD_INICIAL, 3)
    expect(v.edges.some((a) => a.status === 'inferred')).toBe(true)
  })

  it('las adjudicaciones van del contrato al adjudicatario', () => {
    // Dirección canónica de FollowTheMoney.
    const v = vecinosDemo(ENTIDAD_INICIAL, 3)
    const porId = new Map(v.nodes.map((n) => [n.id, n]))
    for (const a of v.edges.filter((e) => e.schema === 'ContractAward')) {
      expect(porId.get(a.source).schema).toBe('Contract')
    }
  })
})
