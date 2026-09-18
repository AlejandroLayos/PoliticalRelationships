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
    { id: 'a', schema: 'PublicBody', caption: 'AYUNTAMIENTO DE EJEMPLO', enMapa: true },
    { id: 'b', schema: 'Company', caption: 'EMPRESA GRANDE SL', enMapa: true },
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
    // De lo publicado se puede enseñar la red entera; de lo demás sólo cifras.
    // Ordenarlo al revés mandaría a la gente a la ficha más pobre teniendo la
    // buena.
    stubFetch()
    const api = await apiLimpia()
    await api.cargarInstantanea()
    const r = await api.buscarTodo('AYUNTAMIENTO')
    expect(r.results[0].soloIndice).toBeUndefined()
    expect(r.results.at(-1).soloIndice).toBe(true)
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
