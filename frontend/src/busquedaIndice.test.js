import { afterEach, describe, expect, it, vi } from 'vitest'

/**
 * La búsqueda cubre el mapa Y el índice.
 *
 * El mapa está acotado; el índice no. Sin esta fusión, quien buscaba el
 * ayuntamiento de su pueblo y no estaba entre los nodos publicados leía «Sin
 * resultados», que es indistinguible de «esa entidad no existe en ninguna
 * fuente». Existe: no cupo.
 */

const GRAFO = {
  generado: '2026-09-18T00:00:00Z',
  fuentes: [{ id: 'placsp', name: 'PLACSP', entidades: 2 }],
  nodes: [
    { id: 'a', schema: 'PublicBody', caption: 'AYUNTAMIENTO DE EJEMPLO', degree: 2, properties: {} },
    { id: 'b', schema: 'Company', caption: 'EMPRESA GRANDE SL', degree: 1, properties: {} },
  ],
  edges: [{ id: 'e1', source: 'a', target: 'b', amount: '900000', schema: 'ContractAward', confidence: 1, status: 'asserted' }],
  provenance: {},
}

const INDICE = {
  total: 3,
  entidades: [
    { id: 'a', schema: 'PublicBody', caption: 'AYUNTAMIENTO DE EJEMPLO', pagado: '900000.00', receptores: 1, enMapa: true },
    { id: 'b', schema: 'Company', caption: 'EMPRESA GRANDE SL', recibido: '900000.00', pagadores: 1, enMapa: true },
    { id: 'c', schema: 'PublicBody', caption: 'AYUNTAMIENTO DE UN PUEBLO', pagado: '1200.00', receptores: 3 },
  ],
}

function stubFetch({ indice = INDICE } = {}) {
  vi.stubGlobal('fetch', vi.fn(async (url) => {
    if (String(url).includes('/datos/grafo.json')) {
      return { ok: true, json: async () => GRAFO }
    }
    if (String(url).includes('/datos/indice.json')) {
      if (!indice) return { ok: false, status: 404, json: async () => ({}) }
      return { ok: true, json: async () => indice }
    }
    // Cualquier llamada a la API: no hay servidor.
    throw new Error('sin API')
  }))
}

async function apiLimpia() {
  vi.resetModules()
  return import('./api.js')
}

afterEach(() => vi.unstubAllGlobals())

describe('buscarTodo', () => {
  it('encuentra lo que está en el mapa', async () => {
    stubFetch()
    const api = await apiLimpia()
    await api.cargarInstantanea()
    const r = await api.buscarTodo('EJEMPLO')
    expect(r.results.map((x) => x.caption)).toContain('AYUNTAMIENTO DE EJEMPLO')
    expect(r.soloIndice).toBe(0)
  })

  it('encuentra también lo que sólo está en el índice, y lo marca', async () => {
    stubFetch()
    const api = await apiLimpia()
    await api.cargarInstantanea()
    const r = await api.buscarTodo('AYUNTAMIENTO')
    const captions = r.results.map((x) => x.caption)
    expect(captions).toContain('AYUNTAMIENTO DE EJEMPLO')
    expect(captions).toContain('AYUNTAMIENTO DE UN PUEBLO')
    expect(r.soloIndice).toBe(1)
    const pueblo = r.results.find((x) => x.caption === 'AYUNTAMIENTO DE UN PUEBLO')
    expect(pueblo.soloIndice).toBe(true)
    expect(pueblo.pagado).toBe('1200.00')
  })

  it('lo del mapa va primero', async () => {
    // Manda el dinero, no de qué lista salió cada fila. Quien busca un nombre
    // casi siempre busca al grande: con el bloque del mapa primero y el del
    // índice después, «ayuntamiento de madrid» dejaba arriba cualquier
    // organismo suyo muy conectado y el Ayuntamiento en medio de la lista.
    //
    // Lo de venir del mapa sigue contando, pero como DESEMPATE: a igual
    // dinero se prefiere la ficha de la que se puede enseñar la red entera.
    stubFetch()
    const api = await apiLimpia()
    await api.cargarInstantanea()
    const r = await api.buscarTodo('AYUNTAMIENTO')
    expect(r.results.map((x) => x.caption)).toEqual([
      'AYUNTAMIENTO DE EJEMPLO',
      'AYUNTAMIENTO DE UN PUEBLO',
    ])
    expect(r.results[0].soloIndice).toBeUndefined()
  })

  it('a igual dinero gana lo que está en el mapa', async () => {
    const api = await apiLimpia()
    const filas = [
      { id: 'i', caption: 'MISMO', pagado: '100', soloIndice: true },
      { id: 'm', caption: 'MISMO', pagado: '100' },
    ]
    expect(api.ordenarResultados(filas).map((x) => x.id)).toEqual(['m', 'i'])
  })

  it('las filas del mapa salen con sus cifras, que el índice sí tiene', async () => {
    // Sin cifra, buscar «ayuntamiento de» devuelve cuarenta nombres iguales y
    // hay que abrirlos uno a uno para saber cuál es el que mueve dinero.
    stubFetch()
    const api = await apiLimpia()
    await api.cargarInstantanea()
    const r = await api.buscarTodo('EMPRESA GRANDE')
    expect(r.results[0].recibido).toBe('900000.00')
  })

  it('no duplica lo que está en los dos sitios', async () => {
    stubFetch()
    const api = await apiLimpia()
    await api.cargarInstantanea()
    const r = await api.buscarTodo('EMPRESA GRANDE')
    expect(r.results.filter((x) => x.id === 'b')).toHaveLength(1)
  })

  it('sin índice la búsqueda sigue funcionando sobre el mapa', async () => {
    // Que falte el índice es un hueco, no un fallo: la web no puede quedarse
    // sin buscador porque un fichero no esté.
    stubFetch({ indice: null })
    const api = await apiLimpia()
    await api.cargarInstantanea()
    const r = await api.buscarTodo('EJEMPLO')
    expect(r.results.map((x) => x.caption)).toContain('AYUNTAMIENTO DE EJEMPLO')
    expect(r.soloIndice).toBe(0)
  })

  it('el índice se descarga una sola vez', async () => {
    stubFetch()
    const api = await apiLimpia()
    await api.cargarInstantanea()
    await api.buscarTodo('AYUNTAMIENTO')
    await api.buscarTodo('EMPRESA')
    const llamadas = fetch.mock.calls.filter(([u]) => String(u).includes('indice.json'))
    expect(llamadas).toHaveLength(1)
  })
})

describe('ordenarResultados', () => {
  async function ordenar(filas) {
    const { ordenarResultados } = await apiLimpia()
    return ordenarResultados(filas)
  }

  it('lo que más dinero mueve, primero', async () => {
    const filas = [
      { id: 'a', caption: 'PEQUEÑO', recibido: '100', pagado: '0' },
      { id: 'b', caption: 'GRANDE', recibido: '0', pagado: '900000' },
      { id: 'c', caption: 'MEDIANO', recibido: '5000', pagado: '0' },
    ]
    expect((await ordenar(filas)).map((r) => r.id)).toEqual(['b', 'c', 'a'])
  })

  it('a igualdad de dinero, el nombre más corto', async () => {
    // «AYUNTAMIENTO DE BURGOS» es lo que se buscaba; el otro es una de sus
    // partes.
    const filas = [
      { id: 'largo', caption: 'AYUNTAMIENTO DE BURGOS - SERVICIO DE PARQUES' },
      { id: 'corto', caption: 'AYUNTAMIENTO DE BURGOS' },
    ]
    expect((await ordenar(filas)).map((r) => r.id)).toEqual(['corto', 'largo'])
  })

  it('sin cifras no revienta y ordena por nombre', async () => {
    const filas = [{ id: 'b', caption: 'BBB' }, { id: 'a', caption: 'AAA' }]
    expect((await ordenar(filas)).map((r) => r.id)).toEqual(['a', 'b'])
  })

  it('no toca la lista original', async () => {
    const filas = [{ id: 'a', caption: 'A', pagado: '1' }, { id: 'b', caption: 'B', pagado: '2' }]
    await ordenar(filas)
    expect(filas.map((r) => r.id)).toEqual(['a', 'b'])
  })
})
