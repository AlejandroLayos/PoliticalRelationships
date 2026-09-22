/**
 * El estado de la vista en la URL.
 *
 * Lo que se comprueba aquí es sobre todo que un enlace SIGA VALIENDO: la clave
 * de una entidad no puede ser su UUID, que se regenera en cada ingesta.
 */
import { describe, expect, it } from 'vitest'
import { accionDeEstado, direccionDeVista, mismoEstado, parametrosDeVista, vistaDeParametros } from './enlace.js'

describe('de estado a dirección', () => {
  it('la portada no lleva parámetros', () => {
    expect(direccionDeVista({ vista: 'portada', clave: '' })).toBe('/')
  })

  it('la ficha de una entidad lleva su clave', () => {
    expect(direccionDeVista({ vista: 'ficha', clave: 'nif:B12345678' })).toBe('/?e=nif%3AB12345678')
  })

  it('el mapa no arrastra la entidad seleccionada', () => {
    expect(direccionDeVista({ vista: 'mapa', clave: 'nif:B1' })).toBe('/?v=mapa')
  })

  it('la vista de conexiones lleva las dos cosas', () => {
    const d = direccionDeVista({ vista: 'vecindario', clave: 'bdns:organo:7' })
    expect(d).toContain('v=red')
    expect(d).toContain('e=bdns%3Aorgano%3A7')
  })

  it('respeta la ruta en la que está desplegada la web', () => {
    expect(direccionDeVista({ vista: 'portada', clave: '' }, '/sinapsis/')).toBe('/sinapsis/')
  })
})

describe('de dirección a estado', () => {
  it('lee la ficha', () => {
    expect(vistaDeParametros('?e=nif%3AB12345678')).toEqual({
      vista: 'ficha',
      clave: 'nif:B12345678',
    })
  })

  it('lee el mapa', () => {
    expect(vistaDeParametros('?v=mapa')).toEqual({ vista: 'mapa', clave: '' })
  })

  it('sin parámetros, la portada', () => {
    expect(vistaDeParametros('')).toEqual({ vista: 'portada', clave: '' })
    expect(vistaDeParametros(undefined)).toEqual({ vista: 'portada', clave: '' })
  })

  it('una vista desconocida no deja la web en un estado imposible', () => {
    // Un enlace viejo o mal copiado tiene que enseñar algo, no un error.
    expect(vistaDeParametros('?v=galaxia')).toEqual({ vista: 'portada', clave: '' })
  })

  it('«red» sin entidad no es una vista de conexiones de nadie', () => {
    expect(vistaDeParametros('?v=red')).toEqual({ vista: 'portada', clave: '' })
  })

  it('ida y vuelta: lo que se escribe es lo que se lee', () => {
    for (const estado of [
      { vista: 'portada', clave: '' },
      { vista: 'mapa', clave: '' },
      { vista: 'ficha', clave: 'nif:A28017895' },
      { vista: 'vecindario', clave: 'placsp:organo:ayuntamiento-de-bilbao-ff7f4243' },
    ]) {
      expect(vistaDeParametros(`?${parametrosDeVista(estado).toString()}`)).toEqual(estado)
    }
  })
})

describe('mismoEstado', () => {
  it('no apila dos veces la misma entrada', () => {
    expect(mismoEstado({ vista: 'ficha', clave: 'a' }, { vista: 'ficha', clave: 'a' })).toBe(true)
    expect(mismoEstado({ vista: 'ficha', clave: 'a' }, { vista: 'ficha', clave: 'b' })).toBe(false)
    expect(mismoEstado({ vista: 'mapa' }, { vista: 'mapa', clave: '' })).toBe(true)
  })
})

describe('accionDeEstado', () => {
  it('el enlace al mapa lleva al mapa, aunque no lleve entidad', () => {
    // El fallo real: la comprobación de «¿existe la clave?» iba por delante,
    // `?v=mapa` no lleva ninguna, y el enlace abría la portada. Callado.
    expect(accionDeEstado({ vista: 'mapa', clave: '' }, false)).toBe('mapa')
  })

  it('una ficha que existe se abre', () => {
    expect(accionDeEstado({ vista: 'ficha', clave: 'nif:A28017895' }, true)).toBe('ficha')
    expect(accionDeEstado({ vista: 'vecindario', clave: 'nif:A28017895' }, true)).toBe('vecindario')
  })

  it('una ficha que ya no está en la instantánea cae en la portada', () => {
    expect(accionDeEstado({ vista: 'ficha', clave: 'nif:B00000000' }, false)).toBe('portada')
    expect(accionDeEstado({ vista: 'vecindario', clave: 'nif:B00000000' }, false)).toBe('portada')
  })

  it('sin clave no hay ficha', () => {
    expect(accionDeEstado({ vista: 'ficha', clave: '' }, true)).toBe('portada')
  })

  it('la portada es la portada', () => {
    expect(accionDeEstado({ vista: 'portada', clave: '' }, false)).toBe('portada')
  })
})
