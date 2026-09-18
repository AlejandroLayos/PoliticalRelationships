import { describe, expect, it } from 'vitest'
import { construirDirectorio, construirDirectorioDesdeIndice } from './directorio.js'

function grafo() {
  return {
    nodes: [
      { id: 'sas', caption: 'SERVICIO DE SALUD', schema: 'PublicBody', properties: {} },
      { id: 'ayto', caption: 'AYUNTAMIENTO', schema: 'PublicBody', properties: {} },
      { id: 'dipu', caption: 'DIPUTACIÓN', schema: 'PublicBody', properties: {} },
      { id: 'grande', caption: 'CONSTRUCTORA SA', schema: 'Company', properties: {} },
      { id: 'ubicua', caption: 'CONSULTORA UBICUA SL', schema: 'Company', properties: {} },
      { id: 'ext', caption: 'PHARMA BV', schema: 'Company', properties: { entidad_extranjera: true } },
      { id: 'partido', caption: 'PARTIDO', schema: 'Organization', properties: { partido_politico: true } },
      { id: 'tcu', caption: 'Tribunal de Cuentas', schema: 'PublicBody', properties: {} },
      { id: 'exp', caption: 'EXPEDIENTE 1/2025', schema: 'Contract', properties: {} },
    ],
    edges: [
      { id: '1', source: 'sas', target: 'grande', amount: '9000000', schema: 'ContractAward' },
      { id: '2', source: 'sas', target: 'ext', amount: '400000', schema: 'ContractAward' },
      { id: '3', source: 'ayto', target: 'ubicua', amount: '1000', schema: 'ContractAward' },
      { id: '4', source: 'dipu', target: 'ubicua', amount: '2000', schema: 'ContractAward' },
      { id: '5', source: 'sas', target: 'ubicua', amount: '3000', schema: 'ContractAward' },
      { id: '6', source: 'partido', target: 'tcu', amount: '50000', schema: 'Debt' },
      // Estructura: no es dinero y no puede colarse en ninguna lista.
      { id: '7', source: 'ayto', target: 'exp', schema: 'UnknownLink' },
    ],
  }
}

describe('construirDirectorio', () => {
  const d = construirDirectorio(grafo())

  it('ordena a los pagadores por dinero repartido', () => {
    expect(d.pagadores[0].caption).toBe('SERVICIO DE SALUD')
    expect(d.pagadores[0].total).toBe(9_403_000)
    expect(d.pagadores[0].n).toBe(3)
  })

  it('ordena a los receptores por dinero cobrado', () => {
    expect(d.receptores.map((x) => x.caption)).toEqual([
      'CONSTRUCTORA SA',
      'PHARMA BV',
      'CONSULTORA UBICUA SL',
    ])
  })

  it('los transversales se ordenan por número de administraciones, no por dinero', () => {
    // Justo lo que distingue esta lista de la de receptores: la ubicua cobra
    // cinco mil euros y la constructora nueve millones, pero la ubicua ha
    // cobrado de tres administraciones distintas y la constructora de una.
    expect(d.transversales[0].caption).toBe('CONSULTORA UBICUA SL')
    expect(d.transversales[0].n).toBe(3)
    expect(d.transversales.map((x) => x.caption)).not.toContain('CONSTRUCTORA SA')
  })

  it('una sanción no convierte al Tribunal de Cuentas en receptor de dinero', () => {
    expect(d.receptores.map((x) => x.id)).not.toContain('tcu')
    expect(d.pagadores.map((x) => x.id)).not.toContain('partido')
  })

  it('lista a los sancionados con su cuantía', () => {
    expect(d.sancionados).toHaveLength(1)
    expect(d.sancionados[0].caption).toBe('PARTIDO')
    expect(d.sancionados[0].total).toBe(50000)
    expect(d.sancionados[0].partido).toBe(true)
  })

  it('separa el capital extranjero', () => {
    expect(d.extranjeras.map((x) => x.caption)).toEqual(['PHARMA BV'])
    expect(d.extranjeras[0].total).toBe(400000)
  })

  it('un expediente no encabeza ninguna lista', () => {
    const todas = [...d.pagadores, ...d.receptores, ...d.transversales]
    expect(todas.map((x) => x.schema)).not.toContain('Contract')
  })

  it('la estructura sin dinero no suma al total', () => {
    expect(d.totales.dineroTotal).toBe(9_406_000)
    expect(d.totales.nOperaciones).toBe(5)
  })

  it('cuenta partidos y extranjeras', () => {
    expect(d.totales.nPartidos).toBe(1)
    expect(d.totales.nExtranjeras).toBe(1)
    expect(d.totales.totalSancionado).toBe(50000)
  })

  it('respeta el límite de cada lista', () => {
    const d2 = construirDirectorio(grafo(), { limite: 1 })
    expect(d2.pagadores).toHaveLength(1)
    expect(d2.receptores).toHaveLength(1)
  })

  it('no revienta sin datos', () => {
    const vacio = construirDirectorio(undefined)
    expect(vacio.pagadores).toEqual([])
    expect(vacio.totales.dineroTotal).toBe(0)
  })
})

describe('las operaciones sin cifra se cuentan, no se esconden', () => {
  it('cuenta las que constan sin importe utilizable', () => {
    // Tras suprimir el importe de los acuerdos marco, el total baja mucho. Si
    // no se dice cuántas operaciones quedaron sin cifra, ese dinero parece no
    // haber existido nunca.
    const g = grafo()
    g.edges.push({
      id: '8', source: 'sas', target: 'grande', schema: 'ContractAward',
      properties: { motivoImporteDudoso: 'es el valor del acuerdo marco' },
    })
    const d = construirDirectorio(g)
    expect(d.totales.nSinCifra).toBe(1)
    // Y sigue contando como operación: ocurrió.
    expect(d.totales.nOperaciones).toBe(6)
    // Pero no inventa dinero.
    expect(d.totales.dineroTotal).toBe(9_406_000)
  })
})

describe('construirDirectorioDesdeIndice', () => {
  const indice = {
    total: 4,
    entidades: [
      { id: 'sas', schema: 'PublicBody', caption: 'SERVICIO DE SALUD', pagado: '9000000.00', receptores: 3, enMapa: true },
      { id: 'ayto', schema: 'PublicBody', caption: 'AYUNTAMIENTO DE UN PUEBLO', pagado: '1200.00', receptores: 2 },
      { id: 'ubicua', schema: 'Company', caption: 'CONSULTORA UBICUA SL', recibido: '5000.00', pagadores: 6 },
      { id: 'grande', schema: 'Company', caption: 'CONSTRUCTORA SA', recibido: '9000000.00', pagadores: 1, enMapa: true },
      { id: 'ext', schema: 'Company', caption: 'PHARMA BV', recibido: '400000.00', pagadores: 1, extranjera: true },
    ],
  }
  const d = construirDirectorioDesdeIndice(indice)

  it('cubre también lo que no cabe en el mapa', () => {
    // Es la razón de ser del índice: el ayuntamiento de un pueblo pequeño no
    // entra en el grafo publicado, y con rankings calculados sobre el grafo
    // «quién reparte más dinero público» contestaba en realidad «de los que
    // caben en el mapa, quién reparte más».
    expect(d.pagadores.map((x) => x.caption)).toContain('AYUNTAMIENTO DE UN PUEBLO')
    expect(d.pagadores.find((x) => x.id === 'ayto').enMapa).toBe(false)
    expect(d.pagadores.find((x) => x.id === 'sas').enMapa).toBe(true)
  })

  it('ordena por dinero', () => {
    expect(d.pagadores[0].caption).toBe('SERVICIO DE SALUD')
    expect(d.receptores[0].caption).toBe('CONSTRUCTORA SA')
  })

  it('los transversales van por número de pagadores, no por dinero', () => {
    expect(d.transversales[0].caption).toBe('CONSULTORA UBICUA SL')
    expect(d.transversales[0].n).toBe(6)
  })

  it('no cuenta el dinero dos veces', () => {
    // Sumar lo pagado Y lo recibido contaría cada operación dos veces, una en
    // quien la paga y otra en quien la cobra.
    expect(d.totales.dineroTotal).toBe(9_001_200)
  })

  it('no incluye a quien no mueve dinero por ese lado', () => {
    expect(d.pagadores.map((x) => x.id)).not.toContain('grande')
    expect(d.receptores.map((x) => x.id)).not.toContain('sas')
  })

  it('separa el capital extranjero', () => {
    expect(d.extranjeras.map((x) => x.caption)).toEqual(['PHARMA BV'])
  })

  it('devuelve null sin índice, para que se use el grafo', () => {
    expect(construirDirectorioDesdeIndice(null)).toBeNull()
    expect(construirDirectorioDesdeIndice({ entidades: [] })).toBeNull()
  })
})
