import { describe, expect, it } from 'vitest'
import {
  cifras,
  esMercantilEstatal,
  estadoAccionista,
  flujosEntreAreas,
  nombrePropio,
  nombramientosClave,
  mapaDeNucleos,
  nombreCorto,
  radiografiaCompleta,
  sigla,
  nucleosEconomicos,
  puentes,
  radiografia,
  umbralOmnipresente,
} from './radiografia.js'

const acc = (clave, nombre, porcentaje, extra = {}) => ({ clave, nombre, porcentaje: String(porcentaje), ...extra })

function cargos() {
  return {
    presidencias: [{ persona: 'boe:persona:pres', nombre: 'Presidente Ejemplo', desde: '2018-06-02' }],
    personas: [
      {
        clave: 'boe:persona:sepi',
        nombre: 'Ana Sepi',
        periodos: [
          {
            cargo: 'Presidenta de la Sociedad Estatal de Participaciones Industriales',
            desde: '2021-03-31',
            urlDesde: 'https://boe/sepi',
            gobierno: { persona: 'boe:persona:pres', nombre: 'Presidente Ejemplo' },
          },
        ],
      },
      {
        clave: 'boe:persona:frob',
        nombre: 'Luis Frob',
        periodos: [{ cargo: 'Presidente del Fondo de Reestructuración Ordenada Bancaria (FROB)', desde: '2020-12-02' }],
      },
      {
        clave: 'boe:persona:juez',
        nombre: 'Juez Ejemplo',
        periodos: [{ cargo: 'Magistrado del Tribunal Supremo', ambito: 'justicia', propuesta: 'Consejo General del Poder Judicial', desde: '2022-01-01' }],
      },
      {
        clave: 'boe:persona:vocal',
        nombre: 'Vocal Ejemplo',
        periodos: [{ cargo: 'Vocal del Consejo General del Poder Judicial', ambito: 'justicia', propuesta: 'Congreso de los Diputados' }],
      },
    ],
    empresas: { 'nif:A1': [{ persona: 'oci:persona:x', nombre: 'Ex Alto Cargo', actividad: 'CONSEJERA DE TELCO', cargoAnterior: 'SECRETARIA DE ESTADO', fecha: '2020-01-01' }] },
    declarantes: {},
    formaciones: { PX: { nombre: 'PARTIDO X', entidad: { clave: 'nif:G1', nombre: 'PARTIDO X' } } },
    cotizadas: {
      'nif:A1': {
        clave: 'nif:A1',
        nombre: 'TELCO, S.A.',
        accionistas: [
          acc('cnmv:sociedad:sepi', 'SOCIEDAD ESTATAL DE PARTICIPACIONES INDUSTRIALES', 10),
          acc('cnmv:sociedad:caixa', 'CRITERIA CAIXA, S.A.U.', 9.99),
          acc('cnmv:sociedad:fundacion', 'FUNDACION BANCARIA LA CAIXA', 9.99),
          acc('cnmv:sociedad:blackrock', 'BLACKROCK INC.', 4.5),
        ],
        consejo: [{ clave: 'cnmv:persona:puente', nombre: 'PERSONA PUENTE', persona: true, cargo: 'Consejero' }],
      },
      'nif:A2': {
        clave: 'nif:A2',
        nombre: 'BANCO, S.A.',
        accionistas: [
          acc('cnmv:sociedad:caixa', 'CRITERIA CAIXA, S.A.U.', 30),
          acc('cnmv:sociedad:fundacion', 'FUNDACION BANCARIA LA CAIXA', 30),
          acc('cnmv:sociedad:frob', 'FROB', 16),
          acc('cnmv:sociedad:blackrock', 'BLACKROCK INC.', 4.5),
          acc('cnmv:persona:familia', 'AMANCIA RICA POSEE', 3, { persona: true }),
        ],
        consejo: [{ clave: 'cnmv:persona:puente', nombre: 'PERSONA PUENTE', persona: true, cargo: 'Consejero' }],
      },
      'nif:A3': {
        clave: 'nif:A3',
        nombre: 'AEROPUERTOS, S.M.E., S.A.',
        accionistas: [acc('cnmv:sociedad:enaire', 'ENAIRE', 51), acc('cnmv:sociedad:blackrock', 'BLACKROCK INC.', 4)],
      },
      'nif:A4': {
        clave: 'nif:A4',
        nombre: 'MODA, S.A.',
        accionistas: [acc('cnmv:persona:familia', 'AMANCIA RICA POSEE', 59, { persona: true })],
      },
      'nif:A5': {
        clave: 'nif:A5',
        nombre: 'TELE, S.A.',
        medio: true,
        sector: 'MEDIOS DE COMUNICACIÓN',
        accionistas: [acc('cnmv:sociedad:planeta', 'PLANETA CORPORACION, S.R.L.', 41.7)],
      },
    },
  }
}

describe('el Estado accionista, por lo que dicen sus fuentes', () => {
  it('la SEPI, porque el BOE nombra a quien la preside', () => {
    const e = estadoAccionista(cargos())
    expect(e.get('cnmv:sociedad:sepi').cargos[0]).toMatchObject({ nombre: 'Ana Sepi', desde: '2021-03-31' })
  })
  it('el FROB, por su sigla entre paréntesis en el cargo', () => {
    expect(estadoAccionista(cargos()).get('cnmv:sociedad:frob').cargos).toHaveLength(1)
  })
  it('ENAIRE, por tener la mayoría de una sociedad mercantil estatal', () => {
    expect(estadoAccionista(cargos()).get('cnmv:sociedad:enaire').motivo).toMatch(/mercantil estatal/)
  })
  it('Criteria no es el Estado', () => {
    expect(estadoAccionista(cargos()).has('cnmv:sociedad:caixa')).toBe(false)
  })
  it('la marca S.M.E., escrita de varias formas', () => {
    expect(esMercantilEstatal('AENA, S.M.E., S.A.')).toBe(true)
    expect(esMercantilEstatal('AENA SME SA')).toBe(true)
    expect(esMercantilEstatal('SMEAGOL, S.A.')).toBe(false)
  })
})

describe('los núcleos', () => {
  it('el Estado es un núcleo, con todas sus participaciones', () => {
    const { nucleos } = nucleosEconomicos(cargos())
    const estado = nucleos.find((n) => n.estado)
    expect(nucleos[0]).toBe(estado)
    expect(estado.cotizadas.map((c) => c.clave).sort()).toEqual(['nif:A1', 'nif:A2', 'nif:A3'])
    expect(estado.participaciones[0]).toMatchObject({ nombre: 'ENAIRE', porcentaje: 51 })
  })

  it('dos titulares con las mismas participaciones son un grupo', () => {
    const { nucleos } = nucleosEconomicos(cargos())
    const caixa = nucleos.find((n) => n.titulares.some((t) => t.clave === 'cnmv:sociedad:caixa'))
    expect(caixa.titulares.map((t) => t.clave).sort()).toEqual(['cnmv:sociedad:caixa', 'cnmv:sociedad:fundacion'])
    // Por nombre: BANCO antes que TELCO.
    expect(caixa.cotizadas.map((c) => c.clave)).toEqual(['nif:A2', 'nif:A1'])
  })

  it('una cotizada puede estar en dos núcleos: la disputa por su control', () => {
    const { enNucleo } = nucleosEconomicos(cargos())
    expect(enNucleo.get('nif:A1')).toHaveLength(2)
  })

  it('menos de un 5 % no hace núcleo', () => {
    const { nucleos } = nucleosEconomicos(cargos())
    // La familia tiene un 59 % en una y un 3 % en otra: no es un núcleo.
    expect(nucleos.some((n) => n.titulares.some((t) => t.clave === 'cnmv:persona:familia'))).toBe(false)
  })

  it('la cotizada de un solo dueño sale como referencia, con él', () => {
    const { referencias } = nucleosEconomicos(cargos())
    const moda = referencias.find((r) => r.clave === 'nif:A4')
    expect(moda.principal).toMatchObject({ nombre: 'AMANCIA RICA POSEE', porcentaje: 59, persona: true })
  })

  it('la gestora que está en casi todas se aparta', () => {
    // Con un umbral bajo, BlackRock (en tres de cinco) sería omnipresente.
    expect(umbralOmnipresente(5)).toBe(8)
    const c = cargos()
    for (let i = 6; i < 40; i++) {
      c.cotizadas[`nif:B${i}`] = { clave: `nif:B${i}`, nombre: `OTRA ${i}`, accionistas: [acc('cnmv:sociedad:blackrock', 'BLACKROCK INC.', 5)] }
    }
    const { omnipresentes, nucleos } = nucleosEconomicos(c)
    expect(omnipresentes.map((o) => o.clave)).toEqual(['cnmv:sociedad:blackrock'])
    expect(nucleos.some((n) => n.titulares.some((t) => t.clave === 'cnmv:sociedad:blackrock'))).toBe(false)
  })

  it('los consejeros compartidos son puentes, no núcleos', () => {
    const { nucleos, compartidos } = nucleosEconomicos(cargos())
    expect(compartidos.map((x) => x.clave)).toEqual(['cnmv:persona:puente'])
    expect(nucleos.find((n) => !n.estado).consejeros.map((x) => x.clave)).toEqual(['cnmv:persona:puente'])
  })
})

describe('los flujos entre áreas', () => {
  const grafo = {
    nodes: [
      { id: '1', clave: 'placsp:organo:ministerio', caption: 'Ministerio' },
      { id: '2', clave: 'nif:A1', caption: 'TELCO' },
      { id: '3', clave: 'nif:G1', caption: 'PARTIDO X' },
    ],
    edges: [
      { source: '1', target: '2', schema: 'ContractAward', amount: '1000000' },
      { source: '1', target: '3', schema: 'Payment', amount: '500000' },
      { source: '1', target: '2', schema: 'Debt', amount: '99' },
    ],
  }
  const por = (flujos, de, a) => flujos.find((f) => f.de === de && f.a === a)

  it('el Gobierno nombra a quien preside el Estado accionista', () => {
    const f = por(flujosEntreAreas(cargos(), grafo), 'gobierno', 'estado')
    expect(f.n).toBe(2)
  })
  it('el Estado es accionista de empresas, y los grandes accionistas de los medios', () => {
    const fl = flujosEntreAreas(cargos(), grafo)
    expect(por(fl, 'estado', 'empresas').n).toBe(3)
    expect(por(fl, 'accionistas', 'medios').hechos[0].texto).toMatch(/PLANETA/)
  })
  it('las puertas giratorias, el CGPJ, el Parlamento y el dinero', () => {
    const fl = flujosEntreAreas(cargos(), grafo)
    expect(por(fl, 'gobierno', 'empresas').hechos[0].cotizada).toBe(true)
    expect(por(fl, 'justicia', 'justicia').n).toBe(1)
    expect(por(fl, 'parlamento', 'justicia').n).toBe(1)
    expect(por(fl, 'administracion', 'empresas').importe).toBe(1000000)
    expect(por(fl, 'administracion', 'partidos').importe).toBe(500000)
  })
  it('sin hechos no hay flujo', () => {
    expect(por(flujosEntreAreas(cargos(), null), 'administracion', 'empresas')).toBeUndefined()
  })
})

describe('puentes y cifras', () => {
  it('el consejero en dos consejos, la familia en dos cotizadas, la puerta giratoria', () => {
    const p = puentes(cargos())
    expect(p.find((x) => x.tipo === 'consejos').nombre).toBe('PERSONA PUENTE')
    expect(p.find((x) => x.tipo === 'accionista').nombre).toBe('AMANCIA RICA POSEE')
    expect(p.find((x) => x.tipo === 'puerta').detalle[0]).toMatch(/TELCO/)
    expect(p.filter((x) => x.tipo === 'estado')).toHaveLength(2)
  })
  it('las cifras de cabecera', () => {
    expect(cifras(cargos())).toMatchObject({ cotizadas: 5, consejeros: 1, justicia: 2, gobiernos: 1 })
  })
  it('todo junto, sin grafo', () => {
    const r = radiografia(cargos())
    expect(r.nucleos.length).toBeGreaterThan(1)
    expect(r.referencias.length).toBeGreaterThan(0)
  })
})

describe('los nombres', () => {
  it.each([
    ['CRITERIA CAIXA, S.A.U.', 'Criteria Caixa, S.A.U.'],
    ['AENA, S.M.E., S.A.', 'Aena, S.M.E., S.A.'],
    ['MERLIN PROPERTIES, SOCIMI, S.A.', 'Merlin Properties, SOCIMI, S.A.'],
    ['AMANCIO ORTEGA GAONA', 'Amancio Ortega Gaona'],
    ['SOCIEDAD ESTATAL DE PARTICIPACIONES INDUSTRIALES', 'Sociedad Estatal de Participaciones Industriales'],
    ['BLACKROCK INC.', 'Blackrock INC.'],
    ['Ya Escrito Bien', 'Ya Escrito Bien'],
  ])('%s → %s', (de, a) => {
    expect(nombrePropio(de)).toBe(a)
  })
})

describe('rótulos y nombres cortos', () => {
  it('siglas de los nombres largos', () => {
    expect(sigla('Sociedad Estatal de Participaciones Industriales')).toBe('SEPI')
    expect(sigla('FROB')).toBe('FROB')
  })
  it('el nombre corto de la CNMV, o el nombre sin la forma jurídica', () => {
    expect(nombreCorto({ nombre: 'PROMOTORA DE INFORMACIONES, S.A.', abreviada: 'PRISA' })).toBe('PRISA')
    expect(nombreCorto({ nombre: 'TELCO, S.A.' })).toBe('TELCO')
  })
  it('cada caja con sus nombres', () => {
    const r = radiografiaCompleta(cargos())
    expect(r.rotulos.estado.split(' · ').sort()).toEqual(['ENAIRE', 'FROB', 'SEPI'])
    expect(r.rotulos.medios).toBe('Tele')
    expect(r.rotulos.gobierno).toBe('Gobiernos de Ejemplo')
    // Con dos apellidos, el primero: «Mariano Rajoy Brey» → Rajoy.
    const c = cargos()
    c.presidencias.push({ persona: 'boe:persona:rajoy', nombre: 'Mariano Rajoy Brey' })
    expect(radiografiaCompleta(c).rotulos.gobierno).toBe('Gobiernos de Ejemplo y Rajoy')
    // Una palabra por titular del núcleo.
    expect(r.rotulos.accionistas).toBe('Criteria…')
  })
  it('a «grandes empresas» sólo llega lo que va a una cotizada', () => {
    const c = cargos()
    c.empresas['nif:Q1'] = [{ persona: 'oci:persona:y', nombre: 'Otra', actividad: 'UNIVERSIDAD', fecha: '2020-01-01' }]
    c.declarantes['nif:Q1'] = [{ persona: 'congreso:persona:z', nombre: 'Diputada', empleador: 'UNIVERSIDAD' }]
    const fl = flujosEntreAreas(c, null)
    expect(fl.find((f) => f.de === 'gobierno' && f.a === 'empresas').n).toBe(1)
    expect(fl.find((f) => f.de === 'parlamento' && f.a === 'empresas')).toBeUndefined()
  })
})

describe('el mapa de los núcleos', () => {
  it('núcleos, cotizadas y puentes, colocados igual cada vez', () => {
    const r = radiografia(cargos())
    const a = mapaDeNucleos(r, cargos())
    const b = mapaDeNucleos(r, cargos())
    expect(a.nodos.map((n) => [n.id, n.x.toFixed(3)])).toEqual(b.nodos.map((n) => [n.id, n.x.toFixed(3)]))
    const tipos = new Set(a.nodos.map((n) => n.tipo))
    expect([...tipos].sort()).toEqual(['cotizada', 'nucleo', 'persona'])
    // Telco está en dos núcleos: dos aristas de participación.
    expect(a.aristas.filter((e) => e.tipo === 'participacion' && e.target === 'nif:A1')).toHaveLength(2)
    // La persona que está en dos consejos, unida a los dos.
    expect(a.aristas.filter((e) => e.tipo === 'consejo')).toHaveLength(2)
  })
})

describe('lo que nombra cada Gobierno', () => {
  it('reguladores, empresas públicas y órganos de control, por el nombre de la institución', () => {
    const c = cargos()
    const g = { persona: 'boe:persona:pres', nombre: 'Presidente Ejemplo' }
    c.personas.push(
      { clave: 'boe:persona:cnmv', nombre: 'Presi CNMV', periodos: [{ cargo: 'Presidenta de la Comisión Nacional del Mercado de Valores', desde: '2020-01-01', gobierno: g }] },
      {
        clave: 'boe:persona:be',
        nombre: 'Gobernador BE',
        periodos: [
          { cargo: 'Ministro de Inclusión', desde: '2020-01-13', gobierno: g },
          { cargo: 'Gobernador del Banco de España', desde: '2024-09-01', gobierno: g },
        ],
      },
      { clave: 'boe:persona:sec', nombre: 'Sección', periodos: [{ cargo: 'Presidenta de la Sección Segunda del Consejo de Estado', gobierno: g }] },
      { clave: 'boe:persona:min', nombre: 'Ministra', periodos: [{ cargo: 'Ministra de Hacienda', gobierno: g }] },
    )
    const [gob] = nombramientosClave(c)
    expect(gob.grupos.reguladores.map((x) => x.nombre)).toEqual(['Gobernador BE', 'Presi CNMV'])
    expect(gob.grupos.empresas.map((x) => x.nombre)).toEqual(['Ana Sepi'])
    // Del Gobierno al regulador, según el mismo BOE.
    expect(gob.grupos.reguladores[0].antes).toBe('Ministro de Inclusión')
    expect(gob.grupos.reguladores[1].antes).toBeUndefined()
    // Una sección del Consejo de Estado no es su presidencia.
    expect(gob.grupos.control).toBeUndefined()
    expect(gob.ministros).toBe(2)
  })
})
