import { describe, expect, it } from 'vitest'
import { disponerFlujo, repartirAlto } from './flujo.js'
import { areaDeInfluencia } from './influencia.js'

function grafo(nReceptores = 3) {
  const nodes = [{ id: 'c', caption: 'AYUNTAMIENTO', schema: 'PublicBody', properties: {} }]
  const edges = []
  nodes.push({ id: 'pag', caption: 'ESTADO', schema: 'PublicBody', properties: {} })
  edges.push({ id: 'e0', source: 'pag', target: 'c', amount: '500000', schema: 'Payment', confidence: 1, status: 'asserted' })
  for (let i = 0; i < nReceptores; i += 1) {
    nodes.push({ id: `r${i}`, caption: `EMPRESA ${i}`, schema: 'Company', properties: {} })
    edges.push({ id: `a${i}`, source: 'c', target: `r${i}`, amount: String(10 ** (i + 2)), schema: 'ContractAward', confidence: 1, status: 'asserted' })
  }
  return { nodes, edges }
}

describe('repartirAlto', () => {
  it('nadie se queda en cero mientras quepa el mínimo', () => {
    // Lo que esto evita: con reparto proporcional puro, una contraparte que
    // cobra mil euros al lado de una que cobra diez millones sale con menos de
    // un píxel — o sea, la vista afirma que no existe.
    const altos = repartirAlto([10_000_000, 1000], 400)
    expect(Math.min(...altos)).toBeGreaterThanOrEqual(26)
  })

  it('el que más cobra sigue siendo el más gordo', () => {
    const [grande, pequeno] = repartirAlto([10_000_000, 1000], 400)
    expect(grande).toBeGreaterThan(pequeno)
  })

  it('reparte a partes iguales cuando no caben los mínimos', () => {
    const altos = repartirAlto([1, 2, 3, 4, 5, 6, 7, 8], 100)
    expect(new Set(altos.map((h) => h.toFixed(4))).size).toBe(1)
  })

  it('no ocupa más de lo disponible', () => {
    const altos = repartirAlto([5, 500, 50_000], 300)
    const ocupa = altos.reduce((s, h) => s + h, 0) + 6 * 2
    expect(ocupa).toBeLessThanOrEqual(300.001)
  })

  it('con una lista vacía devuelve una lista vacía', () => {
    expect(repartirAlto([], 300)).toEqual([])
  })
})

describe('disponerFlujo', () => {
  const area = areaDeInfluencia(grafo(), 'c')
  const d = disponerFlujo(area, { ancho: 900, alto: 600 })

  it('coloca las columnas en su sitio: pagadores izquierda, receptores derecha', () => {
    expect(d.izquierda.every((c) => c.x < d.centro.x)).toBe(true)
    expect(d.derecha.every((c) => c.x > d.centro.x)).toBe(true)
  })

  it('las fichas no se solapan', () => {
    const ord = [...d.derecha].sort((a, b) => a.y - b.y)
    for (let i = 1; i < ord.length; i += 1) {
      expect(ord[i].y).toBeGreaterThanOrEqual(ord[i - 1].y + ord[i - 1].h)
    }
  })

  it('todo cabe dentro del lienzo', () => {
    for (const c of [...d.izquierda, ...d.derecha]) {
      expect(c.y).toBeGreaterThanOrEqual(0)
      expect(c.y + c.h).toBeLessThanOrEqual(600)
      expect(c.x + c.w).toBeLessThanOrEqual(900.001)
    }
  })

  it('hay una cinta por contraparte y ninguna suelta', () => {
    expect(d.cintas).toHaveLength(d.izquierda.length + d.derecha.length)
    const ids = new Set([...d.izquierda, ...d.derecha].map((c) => c.id))
    expect(d.cintas.every((c) => ids.has(c.nodoId))).toBe(true)
  })

  it('las rutas son SVG cerrado', () => {
    for (const c of d.cintas) {
      expect(c.d.startsWith('M ')).toBe(true)
      expect(c.d.endsWith('Z')).toBe(true)
      expect(c.d).not.toMatch(/NaN/)
    }
  })

  it('dice cuántas contrapartes quedaron fuera del dibujo', () => {
    const muchos = areaDeInfluencia(grafo(20), 'c')
    const g = disponerFlujo(muchos, { ancho: 900, alto: 600, maxPorLado: 12 })
    expect(g.derecha).toHaveLength(12)
    expect(g.recortado.derecha).toBe(8)
  })

  it('no revienta sin entidad ni sin medidas', () => {
    expect(disponerFlujo(null, { ancho: 900, alto: 600 }).centro).toBeNull()
    expect(disponerFlujo(area, {}).centro).toBeNull()
  })

  it('aguanta un lado vacío', () => {
    const solo = areaDeInfluencia(
      { nodes: [{ id: 'x', caption: 'X', schema: 'Company', properties: {} }], edges: [] },
      'x',
    )
    const g = disponerFlujo(solo, { ancho: 800, alto: 500 })
    expect(g.cintas).toEqual([])
    expect(g.centro.caption).toBe('X')
  })
})

describe('tamaños y hueco', () => {
  it('una ficha no crece sin límite aunque sobre sitio', () => {
    // Con tres contrapartes en una pantalla alta, el reparto proporcional puro
    // daba bloques de doscientos píxeles: la banda de color tapaba el dibujo y
    // no decía nada más que con sesenta.
    const altos = repartirAlto([100, 200, 300], 900)
    expect(Math.max(...altos)).toBeLessThanOrEqual(68)
  })

  it('con un lado vacío la entidad se corre hacia el hueco', () => {
    const nodes = [
      { id: 'c', caption: 'ORGANISMO', schema: 'PublicBody', properties: {} },
      { id: 'e', caption: 'EMPRESA', schema: 'Company', properties: {} },
    ]
    const edges = [
      { id: 'a', source: 'c', target: 'e', amount: '1000', schema: 'ContractAward', confidence: 1, status: 'asserted' },
    ]
    const soloSalida = disponerFlujo(areaDeInfluencia({ nodes, edges }, 'c'), { ancho: 1000, alto: 600 })
    expect(soloSalida.centro.x).toBeLessThan(1000 / 2 - 100)

    const soloEntrada = disponerFlujo(areaDeInfluencia({ nodes, edges }, 'e'), { ancho: 1000, alto: 600 })
    expect(soloEntrada.centro.x).toBeGreaterThan(1000 / 2)
  })
})
