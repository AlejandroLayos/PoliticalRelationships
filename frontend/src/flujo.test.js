import { describe, expect, it } from 'vitest'
import { disponerFlujo, recortarAAncho, repartirAlto } from './flujo.js'
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

  it('apretadísimo sigue conservando el orden', () => {
    // Antes, cuando no cabían los mínimos, se repartía a partes iguales: una
    // lista de ocho bandas idénticas que afirma que todas cobran lo mismo.
    // Con el mínimo relativo siempre queda sitio con el que ordenar, y ocho
    // bandas de cinco píxeles en orden dicen más que ocho de siete iguales.
    const altos = repartirAlto([1, 2, 3, 4, 5, 6, 7, 8], 100)
    expect(altos[7]).toBeGreaterThan(altos[0])
    expect(Math.min(...altos)).toBeGreaterThan(0)
    const ocupa = altos.reduce((s, h) => s + h, 0) + 6 * 7
    expect(ocupa).toBeLessThanOrEqual(100.001)
  })

  it('no ocupa más de lo disponible', () => {
    const altos = repartirAlto([5, 500, 50_000], 300)
    const ocupa = altos.reduce((s, h) => s + h, 0) + 6 * 2
    expect(ocupa).toBeLessThanOrEqual(300.001)
  })

  it('con una lista vacía devuelve una lista vacía', () => {
    expect(repartirAlto([], 300)).toEqual([])
  })

  it('con muchas contrapartes el mínimo cede y la proporción se conserva', () => {
    // Un suelo fijo se come el reparto en cuanto la lista crece: con
    // dieciocho bandas en 850 px, 26 px de mínimo son 468 y dejan 278 para
    // decir algo. La banda de 40,6 M € salía 1,7 veces la de 3,0 M € cuando
    // por raíz le tocan 3,7. El suelo está para que nadie desaparezca, no
    // para aplanar la comparación.
    const valores = [40_600_000, ...Array.from({ length: 17 }, () => 3_000_000)]
    const altos = repartirAlto(valores, 850)
    const razon = altos[0] / altos[altos.length - 1]
    expect(razon).toBeGreaterThan(1.9)
    // Y nadie se queda en nada: sigue habiendo suelo, más bajo.
    expect(Math.min(...altos)).toBeGreaterThan(12)
    const ocupa = altos.reduce((s, h) => s + h, 0) + 6 * (altos.length - 1)
    expect(ocupa).toBeLessThanOrEqual(850.001)
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
  it('el grosor sigue diciendo algo aunque sobre sitio', () => {
    // Lo contrario de lo que afirmaba este test antes, y por un motivo medido.
    //
    // Topar el grosor a 68 px hacía que dos importes muy distintos salieran
    // idénticos en cuanto había sitio de sobra. En la ficha real de un
    // organismo con tres adjudicatarios —99,1 M €, 39,8 M € y 421 mil €— los
    // dos primeros salían exactamente igual de gruesos. El dibujo afirmaba
    // que repartía casi por igual, que es justo lo que este proyecto no puede
    // hacer.
    //
    // El tope sigue existiendo, pero es de la FICHA —la etiqueta con la
    // cifra—, y lo aplica `disponerFlujo`. La banda crece.
    const [a, b, c] = repartirAlto([99_100_000, 39_800_000, 421_000], 900)
    expect(a).toBeGreaterThan(b * 1.2)
    expect(b).toBeGreaterThan(c * 2)
  })

  it('la ficha sí se queda en su tamaño y se centra sobre la banda', () => {
    const nodes = [
      { id: 'c', caption: 'ORGANISMO', schema: 'PublicBody', properties: {} },
      { id: 'e', caption: 'EMPRESA', schema: 'Company', properties: {} },
    ]
    const edges = [
      { id: 'a', source: 'c', target: 'e', amount: '99100000', schema: 'ContractAward', confidence: 1, status: 'asserted' },
    ]
    const d = disponerFlujo(areaDeInfluencia({ nodes, edges }, 'c'), { ancho: 1000, alto: 900 })
    const [ficha] = d.derecha
    expect(ficha.h).toBeLessThanOrEqual(68)
    expect(ficha.bandaH).toBeGreaterThan(ficha.h)
    // Centrada: lo que sobra por arriba es lo que sobra por abajo.
    expect(ficha.y - ficha.bandaY).toBeCloseTo(ficha.bandaY + ficha.bandaH - (ficha.y + ficha.h), 5)
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

describe('recortarAAncho', () => {
  // Una medida de mentira pero exacta: siete píxeles por carácter.
  const medir = (t) => t.length * 7

  it('lo que cabe se deja entero', () => {
    expect(recortarAAncho('ROCHE FARMA SA', 200, medir)).toBe('ROCHE FARMA SA')
  })

  it('lo que no cabe se corta y lo cortado CABE', () => {
    const corto = recortarAAncho('VERTEX PHARMACEUTICALS (SPAIN) SL', 100, medir)
    expect(corto.endsWith('…')).toBe(true)
    expect(medir(corto)).toBeLessThanOrEqual(100)
  })

  it('no deja un espacio colgando antes de los puntos', () => {
    expect(recortarAAncho('UTE SSG DIGAMAR', 7 * 5, medir)).toBe('UTE…')
  })

  it('sin sitio no escribe nada, y sin texto tampoco', () => {
    expect(recortarAAncho('LO QUE SEA', 0, medir)).toBe('')
    expect(recortarAAncho('', 100, medir)).toBe('')
  })
})
