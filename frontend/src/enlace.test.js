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

describe('la edición de una comunidad', () => {
  it('va en la portada y en el mapa', () => {
    expect(direccionDeVista({ vista: 'portada', clave: '', territorio: 'Andalucía' })).toBe(
      '/?t=Andaluc%C3%ADa',
    )
    expect(vistaDeParametros('?v=mapa&t=Andaluc%C3%ADa')).toEqual({
      vista: 'mapa',
      clave: '',
      territorio: 'Andalucía',
    })
  })

  it('una ficha es la misma se mire desde donde se mire', () => {
    expect(direccionDeVista({ vista: 'ficha', clave: 'nif:A1', territorio: 'Andalucía' })).toBe(
      '/?e=nif%3AA1',
    )
  })

  it('cambiar de edición es cambiar de estado', () => {
    const a = { vista: 'portada', clave: '' }
    expect(mismoEstado(a, { ...a, territorio: 'Galicia' })).toBe(false)
    expect(mismoEstado({ ...a, territorio: '' }, a)).toBe(true)
  })
})

describe('dentro del mapa', () => {
  it('una entidad encendida en el mapa va en la dirección', () => {
    const estado = { vista: 'mapa', clave: '', destacada: 'nif:A28017895' }
    expect(direccionDeVista(estado)).toBe('/?v=mapa&e=nif%3AA28017895')
    expect(vistaDeParametros('?v=mapa&e=nif%3AA28017895')).toEqual(estado)
  })

  it('un grupo abierto se nombra por su entidad principal', () => {
    const estado = { vista: 'mapa', clave: '', grupo: 'placsp:organo:metro-de-madrid' }
    expect(direccionDeVista(estado)).toBe('/?v=mapa&g=placsp%3Aorgano%3Ametro-de-madrid')
    expect(vistaDeParametros(`?${parametrosDeVista(estado)}`)).toEqual(estado)
  })

  it('la entidad manda sobre el grupo: ya dice en cuál está', () => {
    const p = parametrosDeVista({ vista: 'mapa', destacada: 'a', grupo: 'b' })
    expect(p.get('e')).toBe('a')
    expect(p.has('g')).toBe(false)
  })

  it('abrir otro grupo es otro estado', () => {
    const a = { vista: 'mapa', clave: '', grupo: 'x' }
    expect(mismoEstado(a, { ...a, grupo: 'y' })).toBe(false)
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

describe('los cargos públicos', () => {
  it('van a su sección, con la persona en `p` y no en `e`', () => {
    const estado = { vista: 'cargos', clave: '', persona: 'boe:persona:sara-hernandez-del-olmo' }
    expect(direccionDeVista(estado)).toBe('/?v=cargos&p=boe%3Apersona%3Asara-hernandez-del-olmo')
    expect(vistaDeParametros('?v=cargos&p=boe:persona:sara-hernandez-del-olmo')).toEqual(estado)
  })

  it('la sección sin persona también es un enlace', () => {
    expect(direccionDeVista({ vista: 'cargos' })).toBe('/?v=cargos')
    expect(vistaDeParametros('?v=cargos')).toEqual({ vista: 'cargos', clave: '' })
  })

  it('una edición o una entidad no se cuelan en la dirección de los cargos', () => {
    const p = parametrosDeVista({ vista: 'cargos', clave: 'nif:A1', territorio: 'Andalucía' })
    expect(p.toString()).toBe('v=cargos')
  })

  it('dos personas distintas son dos estados', () => {
    expect(mismoEstado({ vista: 'cargos', persona: 'a' }, { vista: 'cargos', persona: 'b' })).toBe(false)
    expect(mismoEstado({ vista: 'cargos', persona: 'a' }, { vista: 'cargos', persona: 'a' })).toBe(true)
  })

  it('se abre la sección aunque no lleve entidad', () => {
    expect(accionDeEstado({ vista: 'cargos', clave: '' }, false)).toBe('cargos')
  })
})

describe('la red de poder', () => {
  it('lleva el nodo del centro y vuelve igual', () => {
    const estado = { vista: 'poder', clave: '', nodo: 'gobierno:boe:persona:x' }
    expect(direccionDeVista(estado)).toBe('/?v=poder&n=gobierno%3Aboe%3Apersona%3Ax')
    expect(vistaDeParametros('?v=poder&n=gobierno:boe:persona:x')).toEqual(estado)
  })

  it('sin nodo, abre la red por donde empiece', () => {
    expect(direccionDeVista({ vista: 'poder' })).toBe('/?v=poder')
    expect(vistaDeParametros('?v=poder')).toEqual({ vista: 'poder', clave: '' })
    expect(accionDeEstado({ vista: 'poder', clave: '' }, false)).toBe('poder')
  })

  it('dos centros distintos son dos entradas de historial', () => {
    expect(mismoEstado({ vista: 'poder', nodo: 'a' }, { vista: 'poder', nodo: 'b' })).toBe(false)
    expect(mismoEstado({ vista: 'poder', nodo: 'a' }, { vista: 'poder', nodo: 'a' })).toBe(true)
  })

  it('ni una entidad ni una edición se cuelan en su dirección', () => {
    const p = parametrosDeVista({ vista: 'poder', clave: 'nif:A1', territorio: 'Andalucía', nodo: 'nif:B2' })
    expect(p.toString()).toBe('v=poder&n=nif%3AB2')
  })
})
