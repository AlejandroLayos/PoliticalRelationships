import { describe, expect, it } from 'vitest'
import { colorTipo, etiquetaRelacion, mezclaDeTipos, tipoDe } from './esquemas.js'

describe('tipoDe', () => {
  it('la persona jurídica es empresa: las dos cobran dinero público', () => {
    expect(tipoDe('Company')).toBe('emp')
    expect(tipoDe('LegalEntity')).toBe('emp')
  })

  it('lo que no es un actor, o no se conoce, es neutro', () => {
    expect(tipoDe('Contract')).toBe('neutro')
    expect(tipoDe('Loquesea')).toBe('neutro')
    expect(tipoDe(undefined)).toBe('neutro')
  })

  it('el color es la variable CSS del tipo, que vale en papel y en el visor', () => {
    expect(colorTipo('PublicBody')).toBe('var(--adm)')
    expect(colorTipo('Organization')).toBe('var(--par)')
  })
})

describe('mezclaDeTipos', () => {
  it('suma los esquemas del mismo tipo y reparte por número de entidades', () => {
    const m = mezclaDeTipos({ Company: 6, LegalEntity: 2, PublicBody: 2 })
    expect(m).toEqual([
      { tipo: 'adm', parte: 0.2 },
      { tipo: 'emp', parte: 0.8 },
    ])
  })

  it('el orden es fijo, para que dos bloques se comparen a simple vista', () => {
    const m = mezclaDeTipos({ Organization: 1, Company: 1, PublicBody: 1 })
    expect(m.map((x) => x.tipo)).toEqual(['adm', 'emp', 'par'])
  })

  it('sin entidades no hay mezcla', () => {
    expect(mezclaDeTipos({})).toEqual([])
    expect(mezclaDeTipos(undefined)).toEqual([])
  })
})

describe('etiquetaRelacion', () => {
  it('un enlace sin esquema propio dice el papel que da la fuente', () => {
    const a = { schema: 'UnknownLink', properties: { role: 'órgano de contratación' } }
    expect(etiquetaRelacion(a)).toBe('Órgano de contratación')
  })

  it('sin papel, el nombre del esquema', () => {
    expect(etiquetaRelacion({ schema: 'UnknownLink' })).toBe('Conexión sin clasificar')
    expect(etiquetaRelacion({ schema: 'ContractAward', properties: { role: 'x' } })).toBe('Adjudicación')
  })
})
