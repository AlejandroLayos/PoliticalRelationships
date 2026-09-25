import { describe, expect, it } from 'vitest'
import { analizarConsulta, empiezaPalabra, gradoDeCoincidencia, rotuloRelajado } from './buscador.js'

const grado = (caption, q) => gradoDeCoincidencia(caption, analizarConsulta(q))

describe('gradoDeCoincidencia', () => {
  it('la frase entera es lo que se buscaba', () => {
    expect(grado('Junta de Gobierno del Ayuntamiento de Móstoles', 'ayuntamiento de mostoles')).toBe(3)
  })

  it('no distingue acentos ni mayúsculas', () => {
    expect(grado('AYUNTAMIENTO DE MÓSTOLES', 'ayuntamiento de mostoles')).toBe(3)
    expect(grado('Ayuntamiento de Mostoles', 'AYUNTAMIENTO DE MÓSTOLES')).toBe(3)
  })

  it('las mismas palabras en otro orden valen, pero menos', () => {
    expect(grado('Ayuntamiento de Móstoles', 'mostoles ayuntamiento')).toBe(2)
  })

  it('con sólo la palabra distintiva entra, en el grado de abajo', () => {
    // El caso real: la contratación se publica por ÓRGANO, así que de un
    // pueblo hay un hospital, una empresa de reformas y una junta de
    // gobierno, y sólo la última lleva la palabra «ayuntamiento».
    expect(grado('Hospital Universitario de Móstoles', 'ayuntamiento de mostoles')).toBe(1)
    expect(grado('REFORMAS IVIASA MÓSTOLES 2014 S.L.', 'ayuntamiento de mostoles')).toBe(1)
  })

  it('lo que no tiene nada que ver se queda fuera', () => {
    expect(grado('Servicio Andaluz de Salud', 'ayuntamiento de mostoles')).toBe(0)
    expect(grado('Ayuntamiento de Getafe', 'ayuntamiento de mostoles')).toBe(0)
  })

  it('sin palabras distintivas no se relaja nada', () => {
    // «Ayuntamiento» a secas relajado devolvería media base ordenada por
    // dinero, que no contesta a nada.
    expect(grado('Consejería de Hacienda', 'ayuntamiento')).toBe(0)
    // Todas comunes: sólo entra lo que las lleva todas de verdad.
    expect(grado('Junta de Gobierno del Ayuntamiento de Gijón', 'junta de gobierno')).toBe(3)
    expect(grado('Gobierno Vasco', 'junta de gobierno')).toBe(0)
  })

  it('una consulta vacía no encuentra nada', () => {
    expect(grado('Lo que sea', '')).toBe(0)
    expect(grado('Lo que sea', '   ')).toBe(0)
  })

  it('las siglas societarias no distinguen', () => {
    expect(analizarConsulta('acciona sa').distintivas).toEqual(['acciona'])
  })
})

describe('empiezaPalabra', () => {
  it('no encuentra una palabra dentro de otra', () => {
    // Aena no está en la base: por subcadena salía una asociación de Baena
    // como primer resultado, e Intro llevaba a su ficha.
    expect(empiezaPalabra('asoc para el desarrollo en baena adibae', 'aena')).toBe(false)
    expect(gradoDeCoincidencia('ASOC … EN BAENA ADIBAE', analizarConsulta('Aena'))).toBe(0)
  })

  it('vale lo escrito a medias, desde el principio de la palabra', () => {
    expect(empiezaPalabra('hospital universitario de mostoles', 'mostol')).toBe(true)
    expect(gradoDeCoincidencia('Ferrovial Construcción, S.A.', analizarConsulta('ferrov'))).toBe(3)
  })

  it('la puntuación también parte palabras', () => {
    expect(empiezaPalabra('d.g.de politica interior', 'politica')).toBe(true)
    expect(empiezaPalabra('d.g.de politica interior', 'de politica')).toBe(true)
  })

  it('sigue buscando si la primera aparición cae dentro de otra palabra', () => {
    expect(empiezaPalabra('baena y aena', 'aena')).toBe(true)
  })
})

describe('rotuloRelajado', () => {
  it('nombra lo que se ha conservado de la búsqueda', () => {
    expect(rotuloRelajado(analizarConsulta('ayuntamiento de mostoles'))).toBe(
      'Otros resultados con «mostoles»',
    )
  })

  it('sin palabras distintivas no hay grupo que rotular', () => {
    expect(rotuloRelajado(analizarConsulta('ayuntamiento de la'))).toBe('')
  })
})
