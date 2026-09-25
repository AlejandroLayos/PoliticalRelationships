/**
 * El nombre legible de un documento de procedencia.
 *
 * Los ficheros de sindicación de la Plataforma se llaman todos igual salvo la
 * marca de tiempo y la página, que van al final. Cuando el panel recortaba por
 * la izquierda salían cinco enlaces que empezaban por «…masAgregadasSinMenores»
 * y no se distinguía uno de otro.
 */
import { describe, expect, it } from 'vitest'
import { enumerar, fechaCorta, nombreDocumento, nombreFuente, siglaFuente } from './procedencia.js'

describe('nombreDocumento', () => {
  it('lee la marca de tiempo y la página del nombre del fichero', () => {
    expect(
      nombreDocumento(
        'https://contrataciondelestado.es/sindicacion/sindicacion_1044/PlataformasAgregadasSinMenores_20260901_030025_1.atom',
      ),
    ).toBe('1/9/2026 03:00 · pág. 1')
  })

  it('distingue dos documentos del mismo feed', () => {
    const a = nombreDocumento('https://x.test/a/Feed_20260901_030025_1.atom')
    const b = nombreDocumento('https://x.test/a/Feed_20260902_030027_1.atom')
    expect(a).not.toBe(b)
  })

  it('sin página, sólo la fecha', () => {
    expect(nombreDocumento('https://x.test/a/Feed_20261231_235959.atom')).toBe('31/12/2026 23:59')
  })

  it('si no hay marca de tiempo, el nombre del fichero', () => {
    expect(nombreDocumento('https://x.test/a/informe.pdf')).toBe('informe.pdf')
  })

  it('un nombre larguísimo sin marca se recorta, pero por el final', () => {
    const largo = `https://x.test/${'a'.repeat(80)}.pdf`
    const salida = nombreDocumento(largo)
    expect(salida.length).toBeLessThanOrEqual(40)
    expect(salida.endsWith('…')).toBe(true)
  })

  it('una URL que no lo es no revienta', () => {
    expect(nombreDocumento('esto no es una url')).toBe('esto no es una url')
  })
})


describe('nombreFuente', () => {
  const fuentes = [
    { id: 'placsp', name: 'Plataforma de Contratación del Sector Público' },
    { id: 'bdns', name: 'Base de Datos Nacional de Subvenciones' },
  ]

  it('traduce el identificador al nombre de la fuente', () => {
    expect(nombreFuente(fuentes, 'bdns')).toBe('Base de Datos Nacional de Subvenciones')
  })

  it('una fuente desconocida se enseña tal cual, no en blanco', () => {
    expect(nombreFuente(fuentes, 'tcu')).toBe('tcu')
    expect(nombreFuente(undefined, 'tcu')).toBe('tcu')
  })
})

describe('enumerar', () => {
  it('junta los nombres como se leen', () => {
    expect(enumerar(['A'])).toBe('A')
    expect(enumerar(['A', 'B'])).toBe('A y B')
    expect(enumerar(['A', 'B', 'C'])).toBe('A, B y C')
  })

  it('no repite: los 29 documentos de un organismo vienen del mismo sitio', () => {
    expect(enumerar(['A', 'A', 'A'])).toBe('A')
  })

  it('sin nombres, cadena vacía', () => {
    expect(enumerar([])).toBe('')
    expect(enumerar(['', null])).toBe('')
  })
})

describe('fechaCorta', () => {
  it('escribe la fecha de descarga', () => {
    expect(fechaCorta('2026-09-18T18:33:29.273593+00:00')).toBe('18/9/2026')
  })

  it('sin fecha o con basura, vacío y no una excepción', () => {
    expect(fechaCorta('')).toBe('')
    expect(fechaCorta(null)).toBe('')
    expect(fechaCorta('no es una fecha')).toBe('')
  })
})

describe('siglaFuente', () => {
  const fuentes = [{ id: 'bdns', name: 'Base de Datos Nacional de Subvenciones' }, { id: 'boe', name: 'BOE' }]

  it('las fuentes conocidas van con su sigla', () => {
    expect(siglaFuente(fuentes, 'bdns')).toBe('BDNS')
    expect(siglaFuente([], 'placsp')).toBe('PLACSP')
  })

  it('sin sigla, el nombre; sin nombre, el identificador', () => {
    expect(siglaFuente(fuentes, 'boe')).toBe('BOE')
    expect(siglaFuente(fuentes, 'otra')).toBe('otra')
  })
})
