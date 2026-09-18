import { describe, expect, it } from 'vitest'
import { aNumero, analizarNucleos, colorNucleo, dineroCorto, etiquetaDe, peso } from './nucleos.js'

/** Dos grupos densos unidos por una sola arista: el caso que Louvain debe separar. */
function grafoDeDosNucleos() {
  const nodes = [
    { id: 'org-a', caption: 'MINISTERIO A', schema: 'PublicBody' },
    { id: 'emp-a1', caption: 'EMPRESA A1', schema: 'Company' },
    { id: 'emp-a2', caption: 'EMPRESA A2', schema: 'Company' },
    { id: 'org-b', caption: 'AYUNTAMIENTO B', schema: 'PublicBody' },
    { id: 'emp-b1', caption: 'EMPRESA B1', schema: 'Company' },
    { id: 'emp-b2', caption: 'EMPRESA B2', schema: 'Company' },
  ]
  const edges = [
    { source: 'org-a', target: 'emp-a1', amount: '1000000', schema: 'Payment' },
    { source: 'org-a', target: 'emp-a2', amount: '900000', schema: 'Payment' },
    { source: 'emp-a1', target: 'emp-a2', amount: '800000', schema: 'Payment' },
    { source: 'org-b', target: 'emp-b1', amount: '1000000', schema: 'Payment' },
    { source: 'org-b', target: 'emp-b2', amount: '900000', schema: 'Payment' },
    { source: 'emp-b1', target: 'emp-b2', amount: '800000', schema: 'Payment' },
    // El único puente entre los dos grupos, y además barato.
    { source: 'emp-a2', target: 'emp-b1', amount: '1', schema: 'Payment' },
  ]
  return { nodes, edges }
}

describe('aNumero', () => {
  it('convierte el importe de texto sin romperse con lo que falta', () => {
    expect(aNumero('1234.56')).toBeCloseTo(1234.56)
    expect(aNumero(null)).toBe(0)
    expect(aNumero(undefined)).toBe(0)
    expect(aNumero('')).toBe(0)
    expect(aNumero('no soy un número')).toBe(0)
  })
})

describe('peso', () => {
  it('es logarítmico: un contrato enorme no puede decidir el mapa entero', () => {
    const chico = peso(1_000)
    const enorme = peso(100_000_000)
    expect(enorme).toBeGreaterThan(chico)
    // En lineal serían 100.000 veces; aquí ha de quedarse en un factor pequeño.
    expect(enorme / chico).toBeLessThan(3)
  })

  it('una arista sin importe sigue pesando: es una relación aunque no lleve cifra', () => {
    expect(peso(0)).toBeGreaterThan(0)
    expect(peso(null)).toBeGreaterThan(0)
  })
})

describe('analizarNucleos', () => {
  it('separa los dos grupos densos', () => {
    const { nucleos } = analizarNucleos(grafoDeDosNucleos())
    expect(nucleos.length).toBe(2)
    const porEtiqueta = Object.fromEntries(nucleos.map((n) => [n.etiqueta, n]))
    expect(Object.keys(porEtiqueta).sort()).toEqual(['AYUNTAMIENTO B', 'MINISTERIO A'])
    for (const n of nucleos) expect(n.tamano).toBe(3)
  })

  it('el dinero de un núcleo es el de dentro, no el del puente', () => {
    const { nucleos } = analizarNucleos(grafoDeDosNucleos())
    // 1.000.000 + 900.000 + 800.000 en cada lado; el puente de 1 € queda fuera.
    for (const n of nucleos) expect(n.dinero).toBe(2_700_000)
  })

  it('nombra el núcleo por el organismo, no por la empresa que más cobró', () => {
    const { nucleos } = analizarNucleos(grafoDeDosNucleos())
    expect(nucleos.map((n) => n.etiqueta).sort()).toEqual(['AYUNTAMIENTO B', 'MINISTERIO A'])
  })

  it('ordena por dinero: lo primero que se ve es donde más hay', () => {
    const datos = grafoDeDosNucleos()
    datos.edges[0].amount = '50000000'
    const { nucleos } = analizarNucleos(datos)
    expect(nucleos[0].etiqueta).toBe('MINISTERIO A')
    expect(nucleos[0].dinero).toBeGreaterThan(nucleos[1].dinero)
  })

  it('suma los importes cuando dos entidades se relacionan más de una vez', () => {
    const datos = {
      nodes: [
        { id: 'a', caption: 'A', schema: 'PublicBody' },
        { id: 'b', caption: 'B', schema: 'Company' },
      ],
      edges: [
        { source: 'a', target: 'b', amount: '100', schema: 'Payment' },
        { source: 'a', target: 'b', amount: '250', schema: 'ContractAward' },
      ],
    }
    const { porNodo, totalDinero } = analizarNucleos(datos)
    expect(totalDinero).toBe(350)
    expect(porNodo.get('a').dinero).toBe(350)
  })

  it('descarta las aristas que apuntan a un nodo que no está', () => {
    const datos = {
      nodes: [{ id: 'a', caption: 'A', schema: 'Company' }],
      edges: [{ source: 'a', target: 'fantasma', amount: '100' }],
    }
    const { grafo, totalDinero } = analizarNucleos(datos)
    expect(grafo.size).toBe(0)
    expect(totalDinero).toBe(0)
  })

  it('un nodo suelto no es un núcleo', () => {
    const datos = {
      nodes: [
        { id: 'solo', caption: 'SOLITARIO', schema: 'Company' },
        { id: 'a', caption: 'A', schema: 'PublicBody' },
        { id: 'b', caption: 'B', schema: 'Company' },
      ],
      edges: [{ source: 'a', target: 'b', amount: '100' }],
    }
    const { nucleos } = analizarNucleos(datos)
    expect(nucleos.every((n) => n.tamano > 1)).toBe(true)
    expect(nucleos.flatMap((n) => n.nodos)).not.toContain('solo')
  })

  it('no revienta con un grafo vacío', () => {
    const { nucleos, totalDinero } = analizarNucleos({ nodes: [], edges: [] })
    expect(nucleos).toEqual([])
    expect(totalDinero).toBe(0)
  })

  it('no revienta sin datos', () => {
    expect(() => analizarNucleos(undefined)).not.toThrow()
  })

  it('ignora los bucles de un nodo consigo mismo', () => {
    const datos = {
      nodes: [{ id: 'a', caption: 'A', schema: 'Company' }],
      edges: [{ source: 'a', target: 'a', amount: '100' }],
    }
    expect(analizarNucleos(datos).grafo.size).toBe(0)
  })
})

describe('etiquetaDe', () => {
  it('prefiere quien reparte el dinero al que lo recibe', () => {
    const miembros = [
      { esquema: 'Company', caption: 'EMPRESA GRANDE', dinero: 999 },
      { esquema: 'PublicBody', caption: 'ORGANISMO', dinero: 1 },
    ]
    expect(etiquetaDe(miembros)).toBe('ORGANISMO')
  })

  it('cae al primero si no hay ningún tipo de cabecera', () => {
    expect(etiquetaDe([{ esquema: 'Contract', caption: 'EXPEDIENTE 1' }])).toBe('EXPEDIENTE 1')
  })

  it('no revienta sin miembros', () => {
    expect(etiquetaDe([])).toBe('Núcleo')
  })
})

describe('colorNucleo', () => {
  it('es estable: el mismo núcleo mantiene su color entre repintados', () => {
    expect(colorNucleo(3)).toBe(colorNucleo(3))
  })

  it('los sueltos van en gris, no en un color de núcleo', () => {
    expect(colorNucleo(-1)).toBe('#6b7280')
    expect(colorNucleo(undefined)).toBe('#6b7280')
  })
})

describe('dineroCorto', () => {
  it('abrevia para que se pueda leer de un vistazo', () => {
    expect(dineroCorto(12_400_000)).toBe('12,4 M €')
    expect(dineroCorto(2_500_000_000)).toBe('2,5 MM €')
    expect(dineroCorto(45_000)).toBe('45 mil €')
    expect(dineroCorto(320)).toBe('320 €')
    expect(dineroCorto(null)).toBe('0 €')
  })
})
