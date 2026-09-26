import { describe, expect, it } from 'vitest'
import {
  buscarEnRed,
  capitalizar,
  claseDe,
  formaDeNif,
  nombreDeTipo,
  centroInicial,
  conexionesDe,
  construirRed,
  egoRed,
  puntosDeEntrada,
  rangoDeCargo,
} from './poder.js'

const SANCHEZ = { persona: 'boe:persona:ps', nombre: 'Pedro Sánchez', formacion: 'PSOE' }

function cargos() {
  return {
    presidencias: [{ persona: 'boe:persona:ps', nombre: 'Pedro Sánchez', desde: '2018-06-02', hasta: null, formacion: 'PSOE' }],
    formaciones: {
      PSOE: { nombre: 'PARTIDO SOCIALISTA OBRERO ESPAÑOL', entidad: { clave: 'nif:G1', nombre: 'PARTIDO SOCIALISTA OBRERO ESPAÑOL' } },
      VOX: { nombre: 'VOX' },
    },
    personas: [
      {
        clave: 'boe:persona:ps',
        nombre: 'Pedro Sánchez',
        periodos: [
          { puesto: 'Presidente del Gobierno', cargo: 'Presidente del Gobierno', organismo: 'Presidencia del Gobierno', desde: '2018-06-02', urlDesde: 'https://boe/1' },
          { puesto: 'Escaño en la XV legislatura', cargo: 'Escaño en la XV legislatura', organismo: '', fuente: 'congreso', formacion: 'PSOE', grupo: 'GS', circunscripcion: 'Madrid', desde: '2023-08-17', urlDesde: 'https://congreso/1' },
        ],
      },
      {
        clave: 'boe:persona:ana',
        nombre: 'Ana Ruiz',
        periodos: [
          { puesto: 'Ministro de Defensa', cargo: 'Ministra de Defensa', organismo: 'Ministerio de Defensa', desde: '2018-06-07', hasta: '2023-11-21', urlDesde: 'https://boe/2', gobierno: SANCHEZ },
        ],
        autorizaciones: [
          { actividad: 'INDRA SISTEMAS, S.A.', fecha: '2024-05-01', cargoAnterior: 'MINISTRA DE DEFENSA', url: 'https://oci/1', empresa: { clave: 'nif:A1', nombre: 'INDRA SISTEMAS SA' } },
          // Sin empresa del mapa: no hay nodo al que unirla, y no se inventa.
          { actividad: 'ASESORA EN SERVEIS FUNERARIS', fecha: '2024-06-01', url: 'https://oci/2' },
        ],
      },
      {
        clave: 'oci:persona:luis',
        nombre: 'Luis Gil',
        periodos: [
          { puesto: 'JEFE DEL MANDO', cargo: 'JEFE DEL MANDO', organismo: 'DEFENSA', hasta: '2024-01-01', fuente: 'oci', urlHasta: 'https://oci/3' },
        ],
        autorizaciones: [
          {
            actividad: 'INDRA SISTEMAS, S.A.',
            fecha: '2024-03-01',
            url: 'https://oci/4',
            empresa: { clave: 'nif:A1', nombre: 'INDRA SISTEMAS SA' },
            delOrgano: [{ organo: { clave: 'placsp:organo:mando', nombre: 'Mando de Apoyo' }, importe: '1500000', adjudicaciones: 2 }],
          },
        ],
      },
      {
        clave: 'oci:persona:eva',
        nombre: 'Eva Sanz',
        periodos: [{ puesto: 'VOCAL', cargo: 'VOCAL', organismo: 'ECONOMÍA Y COMPETITIVIDAD', hasta: '2015-01-01', fuente: 'oci' }],
      },
      {
        clave: 'congreso:persona:rafa',
        nombre: 'Rafa Mora',
        periodos: [{ puesto: 'Escaño en la XV legislatura', cargo: 'Escaño en la XV legislatura', organismo: '', fuente: 'congreso', formacion: 'VOX', desde: '2023-08-17' }],
        declaraciones: [
          { empleador: 'Universidad de Córdoba', descripcion: 'Profesor', periodo: '2014-2015', fechaRegistro: '2023-08-17', url: 'https://congreso/2', empresa: { clave: 'nif:Q1', nombre: 'UNIVERSIDAD DE CORDOBA' } },
          { empleador: 'Bufete propio', descripcion: 'Abogado', fechaRegistro: '2023-08-17', url: 'https://congreso/2' },
        ],
      },
    ],
  }
}

describe('construirRed', () => {
  const red = construirRed(cargos())

  it('cada persona es un nodo y ninguna se une a otra persona', () => {
    expect(red.nodos.get('boe:persona:ana').tipo).toBe('persona')
    for (const a of red.aristas) {
      const tipos = [red.nodos.get(a.source).tipo, red.nodos.get(a.target).tipo]
      expect(tipos.filter((t) => t === 'persona').length).toBeLessThan(2)
    }
  })

  it('la autorización de la OCI une a la persona con la empresa del mapa, con su fuente', () => {
    const a = red.aristas.find((x) => x.relacion === 'autorizacion' && x.source === 'boe:persona:ana')
    expect(a.target).toBe('nif:A1')
    expect(a.hechos[0]).toMatchObject({ fuente: 'oci', url: 'https://oci/1', desde: '2024-05-01' })
  })

  it('una actividad sin entidad del mapa no crea nodo', () => {
    const nombres = [...red.nodos.values()].map((n) => n.nombre)
    expect(nombres.some((n) => /FUNERARIS|Bufete/i.test(n))).toBe(false)
  })

  it('el escaño une con el partido del mapa cuando el puente del Senado lo da', () => {
    const a = red.aristas.find((x) => x.relacion === 'escano' && x.source === 'boe:persona:ps')
    expect(a.target).toBe('nif:G1')
    expect(red.nodos.get('nif:G1')).toMatchObject({ tipo: 'partido', nombre: 'PSOE', entidad: 'nif:G1' })
    expect(a.hechos[0].texto).toBe('Escaño en la XV legislatura (GS · Madrid)')
  })

  it('sin puente, el partido es un nodo por sus siglas y no apunta a ninguna ficha', () => {
    const vox = red.nodos.get('partido:VOX')
    expect(vox.tipo).toBe('partido')
    expect(vox.entidad).toBeUndefined()
  })

  it('el Gobierno sale del BOE: nombramiento durante él, no militancia', () => {
    const a = red.aristas.find((x) => x.relacion === 'nombramiento' && x.source === 'boe:persona:ana')
    expect(a.target).toBe('gobierno:boe:persona:ps')
    // Ana no tiene escaño: no hay arista suya con ningún partido.
    expect(red.aristas.some((x) => x.source === 'boe:persona:ana' && x.relacion === 'escano')).toBe(false)
  })

  it('el presidente preside su Gobierno, y el Gobierno llega a los ministerios con cuántos nombramientos', () => {
    expect(red.aristas.some((x) => x.relacion === 'preside' && x.source === 'boe:persona:ps')).toBe(true)
    const m = red.aristas.find((x) => x.relacion === 'ministerio')
    expect(m.source).toBe('gobierno:boe:persona:ps')
    expect(red.nodos.get(m.target).nombre).toBe('Ministerio de Defensa')
    expect(m.hechos[0].texto).toBe('1 nombramiento en el BOE')
  })

  it('el ministerio de la OCI se une al del BOE sólo si es el mismo nombre', () => {
    const luis = red.aristas.find((x) => x.relacion === 'cargo' && x.source === 'oci:persona:luis')
    expect(red.nodos.get(luis.target).nombre).toBe('Ministerio de Defensa')
    const eva = red.aristas.find((x) => x.relacion === 'cargo' && x.source === 'oci:persona:eva')
    // No hay «Ministerio de Economía y Competitividad» en el BOE leído: se
    // queda con su nombre, sin añadirle palabras.
    expect(red.nodos.get(eva.target).nombre).toBe('Economía y competitividad')
  })

  it('el dinero del órgano a la sociedad (delOrgano) es una arista entre entidades', () => {
    const d = red.aristas.find((x) => x.relacion === 'dinero')
    expect([d.source, d.target]).toEqual(['placsp:organo:mando', 'nif:A1'])
    expect(d.hechos[0].importe).toBe(1500000)
  })

  it('el mismo hecho que llega dos veces se cuenta una', () => {
    const c = cargos()
    c.personas[1].periodos.push({ ...c.personas[1].periodos[0] })
    const r = construirRed(c)
    const a = r.aristas.find((x) => x.relacion === 'cargo' && x.source === 'boe:persona:ana')
    expect(a.hechos).toHaveLength(1)
  })
})

describe('el dinero del grafo', () => {
  it('sólo entre entidades que ya están en la red, y a través de los expedientes', () => {
    const grafo = {
      nodes: [
        { id: 'o', clave: 'placsp:organo:mando', schema: 'PublicBody' },
        { id: 'c', clave: 'placsp:contrato:1', schema: 'Contract' },
        { id: 'e', clave: 'nif:Q1', schema: 'PublicBody' },
        { id: 'x', clave: 'nif:ZZ', schema: 'Company' },
      ],
      edges: [
        { id: '1', source: 'o', target: 'c', schema: 'UnknownLink' },
        { id: '2', source: 'c', target: 'e', schema: 'ContractAward', amount: '200', start_date: '2024-01-02' },
        { id: '3', source: 'o', target: 'x', schema: 'Payment', amount: '999' },
      ],
    }
    const red = construirRed(cargos(), grafo)
    const d = red.aristas.filter((a) => a.relacion === 'dinero')
    expect(d.map((a) => `${a.source}>${a.target}`).sort()).toEqual(['placsp:organo:mando>nif:A1', 'placsp:organo:mando>nif:Q1'])
    expect(red.nodos.has('nif:ZZ')).toBe(false)
  })
})

describe('egoRed', () => {
  const red = construirRed(cargos())

  it('el centro, sus vecinos y las aristas entre ellos', () => {
    const e = egoRed(red, 'nif:A1')
    const ids = e.nodos.map((n) => n.id)
    expect(ids[0]).toBe('nif:A1')
    expect(ids).toEqual(expect.arrayContaining(['boe:persona:ana', 'oci:persona:luis', 'placsp:organo:mando']))
    for (const a of e.aristas) {
      expect(ids).toContain(a.source)
      expect(ids).toContain(a.target)
    }
  })

  it('con pocos vecinos da un segundo salto', () => {
    const e = egoRed(red, 'nif:A1')
    expect(e.nodos.find((n) => n.id === 'organismo:ministerio-de-defensa')?.salto).toBe(2)
  })

  it('con más vecinos que sitio, dibuja los primeros y cuenta los que no caben', () => {
    const e = egoRed(red, 'gobierno:boe:persona:ps', { limite: 1 })
    expect(e.nodos).toHaveLength(2)
    expect(e.ocultos).toBeGreaterThan(0)
    // Lo que no es persona va delante: el ministerio antes que la gente.
    expect(e.nodos[1].tipo).not.toBe('persona')
  })

  it('un nodo que no existe da una red vacía, no un error', () => {
    expect(egoRed(red, 'nada').nodos).toEqual([])
  })
})

describe('conexionesDe', () => {
  const red = construirRed(cargos())

  it('agrupa por relación y la titula desde el nodo', () => {
    const empresa = conexionesDe(red, 'nif:A1')
    const titulos = empresa.map((g) => g.titulo)
    expect(titulos).toContain('Ex altos cargos autorizados a trabajar aquí')
    expect(titulos).toContain('Cobró de')
    const persona = conexionesDe(red, 'boe:persona:ana').map((g) => g.titulo)
    expect(persona[0]).toBe('Autorización para trabajar en')
  })
})

describe('buscar y empezar', () => {
  const red = construirRed(cargos())

  it('busca por nombre y por siglas, desde el principio de palabra', () => {
    expect(buscarEnRed(red, 'indra').map((n) => n.id)).toEqual(['nif:A1'])
    expect(buscarEnRed(red, 'socialista').map((n) => n.id)).toEqual(['nif:G1'])
    expect(buscarEnRed(red, 'ndra')).toEqual([])
  })

  it('abre por el Gobierno en curso', () => {
    expect(centroInicial(red, cargos())).toBe('gobierno:boe:persona:ps')
  })

  it('propone las entidades a las que más personas con cargo están unidas', () => {
    const p = puntosDeEntrada(red)
    expect(p.entidades[0]).toMatchObject({ id: 'nif:A1', personas: 2 })
    expect(p.gobiernos.map((g) => g.id)).toEqual(['gobierno:boe:persona:ps'])
  })
})

describe('detalles', () => {
  it('capitaliza lo que viene en mayúsculas sin añadir palabras', () => {
    expect(capitalizar('ECONOMÍA Y COMPETITIVIDAD')).toBe('Economía y competitividad')
    expect(capitalizar('Ministerio de Defensa')).toBe('Ministerio de Defensa')
  })

  it('ordena los cargos como el BOE', () => {
    expect(rangoDeCargo('Ministra de Defensa')).toBeGreaterThan(rangoDeCargo('Secretaria de Estado de Defensa'))
    expect(rangoDeCargo('Secretario de Estado de Hacienda')).toBeGreaterThan(rangoDeCargo('Director General de Tributos'))
  })
})

describe('qué es cada entidad', () => {
  it('lo dice la letra del NIF, que es una regla oficial', () => {
    expect(formaDeNif('nif:A28599033')).toEqual({ forma: 'Sociedad anónima', clase: 'emp' })
    expect(formaDeNif('nif:Q1418001B')).toEqual({ forma: 'Organismo público', clase: 'adm' })
    expect(formaDeNif('nif:G28477727')).toEqual({ forma: 'Asociación o fundación', clase: 'par' })
    expect(formaDeNif('placsp:organo:x')).toBeNull()
    expect(formaDeNif('nif:12345678Z')).toBeNull()
  })

  it('y con eso se pinta y se nombra', () => {
    const red = construirRed(cargos())
    expect(claseDe(red.nodos.get('nif:Q1'))).toBe('adm')
    expect(nombreDeTipo(red.nodos.get('nif:Q1'))).toBe('Organismo público')
    expect(claseDe(red.nodos.get('nif:A1'))).toBe('emp')
    expect(claseDe(red.nodos.get('placsp:organo:mando'))).toBe('adm')
    expect(nombreDeTipo(red.nodos.get('placsp:organo:mando'))).toBe('Órgano de la administración')
    expect(claseDe(red.nodos.get('boe:persona:ana'))).toBe('persona')
    expect(claseDe(red.nodos.get('nif:G1'))).toBe('par')
  })
})

describe('altas instancias judiciales', () => {
  function conJueces() {
    const c = cargos()
    c.personas.push(
      {
        clave: 'boe:persona:macias',
        nombre: 'José María Macías Castaño',
        periodos: [
          { puesto: 'Magistrado del Tribunal Constitucional', cargo: 'Magistrado del Tribunal Constitucional', organismo: 'Tribunal Constitucional', desde: '2024-07-30', ambito: 'justicia', propuesta: 'Senado', urlDesde: 'https://boe/tc1' },
        ],
      },
      {
        clave: 'boe:persona:campo',
        nombre: 'Juan Carlos Campo Moreno',
        periodos: [
          { puesto: 'Magistrado del Tribunal Constitucional', cargo: 'Magistrado del Tribunal Constitucional', organismo: 'Tribunal Constitucional', desde: '2022-12-31', ambito: 'justicia', propuesta: 'Gobierno', gobierno: SANCHEZ, urlDesde: 'https://boe/tc2' },
          { puesto: 'Ministro de Justicia', cargo: 'Ministro de Justicia', organismo: '', desde: '2020-01-13', hasta: '2021-07-12', gobierno: SANCHEZ, urlDesde: 'https://boe/mj' },
        ],
      },
    )
    return c
  }

  it('el proponente es un nodo, unido por «a propuesta de»', () => {
    const red = construirRed(conJueces())
    const a = red.aristas.find((x) => x.relacion === 'propuesta' && x.source === 'boe:persona:macias')
    expect(red.nodos.get(a.target)).toMatchObject({ tipo: 'organismo', nombre: 'Senado' })
    // Y el tribunal, como su organismo.
    const tc = red.aristas.find((x) => x.relacion === 'cargo' && x.source === 'boe:persona:macias')
    expect(red.nodos.get(tc.target).nombre).toBe('Tribunal Constitucional')
    // Sin Gobierno: nadie dice que lo nombrara ninguno.
    expect(red.aristas.some((x) => x.source === 'boe:persona:macias' && x.relacion === 'nombramiento')).toBe(false)
  })

  it('a propuesta del Gobierno, la arista va a ese Gobierno y no es un nombramiento durante', () => {
    const red = construirRed(conJueces())
    const suyas = red.aristas.filter((x) => x.source === 'boe:persona:campo' && x.target === 'gobierno:boe:persona:ps')
    expect(suyas.map((x) => x.relacion).sort()).toEqual(['nombramiento', 'propuesta'])
    const propuesta = suyas.find((x) => x.relacion === 'propuesta')
    expect(propuesta.hechos.map((h) => h.texto)).toEqual(['Magistrado del Tribunal Constitucional'])
    const nombramiento = suyas.find((x) => x.relacion === 'nombramiento')
    expect(nombramiento.hechos.map((h) => h.texto)).toEqual(['Ministro de Justicia'])
    // Ningún nodo «Gobierno» suelto por la propuesta.
    expect(red.nodos.has('organismo:gobierno')).toBe(false)
  })
})
