import { describe, expect, it } from 'vitest'
import {
  bajoGobierno,
  buscarCargos,
  delOrganoEnPalabras,
  dePapel,
  fechaCorta,
  fechaLarga,
  formacionEn,
  gobiernos,
  huecoDelPeriodo,
  lineaDeTiempo,
  marcasDeAnios,
  movimientos,
  nombreDeGobierno,
  organismos,
  papelDeLaFicha,
  personaDeClave,
  presidencias,
  recuento,
  resultadosDeCargos,
  sectorDeclarado,
  tramo,
} from './cargos.js'

// La forma de `cargos.json`, con los datos de dos Reales Decretos reales del
// 2 de septiembre de 2026 (BOE-A-2026-18439 y 18440) y un periodo inventado
// para cubrir el caso de un cese sin nombramiento.
const datos = {
  actosDesde: '2012-01-03',
  actosHasta: '2026-09-02',
  personas: [
    {
      clave: 'boe:persona:sara-hernandez-del-olmo',
      nombre: 'Sara Hernández del Olmo',
      periodos: [
        {
          puesto: 'Secretario General de Transporte Terrestre',
          cargo: 'Secretaria General de Transporte Terrestre',
          organismo: 'Ministerio de Transportes y Movilidad Sostenible',
          desde: '2026-09-02',
          boeDesde: 'BOE-A-2026-18440',
          urlDesde: 'https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-18440',
        },
        {
          puesto: 'Secretario General de Movilidad Sostenible',
          cargo: 'Secretaria General de Movilidad Sostenible',
          organismo: 'Ministerio de Transportes y Movilidad Sostenible',
          hasta: '2026-09-02',
          boeHasta: 'BOE-A-2026-18439',
          urlHasta: 'https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-18439',
        },
      ],
    },
    {
      clave: 'boe:persona:virgilio-ruiz-gil',
      nombre: 'Virgilio Ruiz Gil',
      periodos: [
        {
          puesto: 'Director General de Carreteras',
          cargo: 'Director General de Carreteras',
          organismo: 'Ministerio de Fomento',
          desde: '2012-01-03',
          hasta: '2014-05-10',
          boeDesde: 'A',
          boeHasta: 'B',
        },
      ],
    },
  ],
}

describe('fechas', () => {
  it('sin Date ni husos', () => {
    expect(fechaLarga('2026-09-02')).toBe('2 de septiembre de 2026')
    expect(fechaCorta('2026-09-02')).toBe('2 sep 2026')
    expect(fechaCorta('')).toBe('')
  })
})

describe('tramo y hueco', () => {
  it('dice lo que hay', () => {
    expect(tramo({ desde: '2012-01-03', hasta: '2014-05-10' })).toBe('3 ene 2012 – 10 may 2014')
    expect(tramo({ desde: '2026-09-02' })).toBe('desde 2 sep 2026')
    expect(tramo({ hasta: '2026-09-02' })).toBe('hasta 2 sep 2026')
  })
  it('y dice lo que falta, sin rellenarlo', () => {
    // Sin cese no quiere decir «sigue en el cargo».
    expect(huecoDelPeriodo({ desde: '2026-09-02' })).toBe('no consta cese')
    expect(huecoDelPeriodo({ hasta: '2026-09-02' })).toBe('nombramiento anterior a lo leído')
    expect(huecoDelPeriodo({ desde: 'a', hasta: 'b' })).toBe('')
  })
})

describe('movimientos', () => {
  it('del más reciente al más antiguo, con el nombramiento arriba si es el mismo día', () => {
    const m = movimientos(datos)
    expect(m.map((a) => [a.fecha, a.tipo])).toEqual([
      ['2026-09-02', 'nombramiento'],
      ['2026-09-02', 'cese'],
      ['2014-05-10', 'cese'],
      ['2012-01-03', 'nombramiento'],
    ])
    expect(m[0].boe).toBe('BOE-A-2026-18440')
    expect(m[1].boe).toBe('BOE-A-2026-18439')
  })
  it('respeta el límite', () => {
    expect(movimientos(datos, 2)).toHaveLength(2)
  })
})

describe('buscarCargos', () => {
  it('por nombre, cargo u organismo, sin tildes', () => {
    expect(buscarCargos(datos, 'hernandez').map((p) => p.nombre)).toEqual(['Sara Hernández del Olmo'])
    expect(buscarCargos(datos, 'carreteras').map((p) => p.nombre)).toEqual(['Virgilio Ruiz Gil'])
    expect(buscarCargos(datos, 'movilidad transportes')).toHaveLength(1)
  })
  it('al principio de palabra: «gil» no encuentra a Virgilio por dentro', () => {
    expect(buscarCargos(datos, 'gil').map((p) => p.nombre)).toEqual(['Virgilio Ruiz Gil'])
    expect(buscarCargos(datos, 'ilio')).toEqual([])
  })
  it('sin consulta, todos', () => {
    expect(buscarCargos(datos, ' ')).toHaveLength(2)
  })
})

describe('personaDeClave', () => {
  it('encuentra por la clave estable', () => {
    expect(personaDeClave(datos, 'boe:persona:virgilio-ruiz-gil')?.nombre).toBe('Virgilio Ruiz Gil')
    expect(personaDeClave(datos, 'boe:persona:nadie')).toBeNull()
    expect(personaDeClave(null, 'x')).toBeNull()
  })
})

describe('organismos', () => {
  it('cuenta actos, no periodos, y a igualdad, por orden alfabético', () => {
    expect(organismos(datos)).toEqual([
      { nombre: 'Ministerio de Fomento', actos: 2 },
      { nombre: 'Ministerio de Transportes y Movilidad Sostenible', actos: 2 },
    ])
  })
})

describe('resultadosDeCargos', () => {
  it('sólo por nombre en el buscador general', () => {
    expect(resultadosDeCargos(datos, 'sara')).toEqual([
      {
        id: 'cargo:boe:persona:sara-hernandez-del-olmo',
        clave: 'boe:persona:sara-hernandez-del-olmo',
        caption: 'Sara Hernández del Olmo',
        schema: 'Person',
        cargo: true,
        descripcion: 'Secretaria General de Transporte Terrestre',
      },
    ])
    // «transportes» es un ministerio: en el buscador general se busca el
    // organismo, no a todos los que pasaron por él.
    expect(resultadosDeCargos(datos, 'transportes')).toEqual([])
  })
})

describe('lineaDeTiempo', () => {
  it('coloca los periodos entre lo primero y lo último leído', () => {
    const [p] = lineaDeTiempo([{ desde: '2020-01-01', hasta: '2022-01-01' }], '2018-01-01', '2024-01-01')
    expect(p.inicio).toBeCloseTo(730 / 2191, 5)
    expect(p.fin).toBeCloseTo(1461 / 2191, 5)
    expect(p.abiertoIzquierda).toBe(false)
    expect(p.abiertoDerecha).toBe(false)
  })

  it('lo que no se sabe llega al borde, marcado como abierto', () => {
    const [sinCese, sinNombramiento] = lineaDeTiempo(
      [{ desde: '2023-01-01' }, { hasta: '2019-01-01' }],
      '2018-01-01',
      '2024-01-01',
    )
    expect(sinCese.fin).toBe(1)
    expect(sinCese.abiertoDerecha).toBe(true)
    expect(sinNombramiento.inicio).toBe(0)
    expect(sinNombramiento.abiertoIzquierda).toBe(true)
  })

  it('un eje vacío o al revés no dibuja nada', () => {
    expect(lineaDeTiempo([{ desde: '2020-01-01' }], '2024-01-01', '2020-01-01')).toEqual([])
    expect(lineaDeTiempo([{ desde: '2020-01-01' }], '', '')).toEqual([])
  })
})

describe('marcasDeAnios', () => {
  it('un año por marca si caben, dentro del eje', () => {
    const m = marcasDeAnios('2018-06-07', '2021-03-01')
    expect(m.map((x) => x.anio)).toEqual([2019, 2020, 2021])
    expect(m.every((x) => x.x > 0 && x.x < 1)).toBe(true)
  })
  it('espacia cuando son muchos', () => {
    expect(marcasDeAnios('2011-12-22', '2026-09-25', 6).map((x) => x.anio)).toEqual([
      2012, 2015, 2018, 2021, 2024,
    ])
  })
})

describe('Oficina de Conflictos de Intereses', () => {
  const conOci = {
    personas: [
      {
        clave: 'oci:persona:x',
        nombre: 'Banez Garcia, Fatima',
        periodos: [{ puesto: 'MINISTRA', cargo: 'MINISTRA DE EMPLEO Y SEGURIDAD SOCIAL', hasta: '2018-06-01', fuente: 'oci', urlHasta: 'u' }],
        autorizaciones: [
          { actividad: 'MIEMBRO DEL CONSEJO DE ADMINISTRACION DE LABORATORIOS FARMACEUTICOS ROVI, S.A.', fecha: '2019-12-13', url: 'u' },
        ],
      },
    ],
  }

  it('un cese sin nombramiento dice por qué, según la fuente', () => {
    expect(huecoDelPeriodo(conOci.personas[0].periodos[0])).toBe('la fuente no da el nombramiento')
  })

  it('las autorizaciones entran en la columna de lo último, por delante del cese', () => {
    const m = movimientos(conOci)
    expect(m.map((a) => [a.fecha, a.tipo])).toEqual([
      ['2019-12-13', 'autorizacion'],
      ['2018-06-01', 'cese'],
    ])
    expect(m[1].boe).toBe('Oficina de Conflictos de Intereses')
  })
})

describe('presidencias', () => {
  it('sólo el Presidente del Gobierno, del BOE, por orden', () => {
    const d = {
      personas: [
        { clave: 'b', nombre: 'Pedro Sánchez Pérez-Castejón', periodos: [{ puesto: 'Presidente del Gobierno', desde: '2018-06-02' }] },
        {
          clave: 'a',
          nombre: 'Mariano Rajoy Brey',
          periodos: [
            { puesto: 'Presidente del Gobierno', desde: '2011-12-21', hasta: '2018-06-02' },
            { puesto: 'Presidente del Gobierno', desde: '2012-01-01', fuente: 'oci' },
          ],
        },
        { clave: 'c', nombre: 'Otra', periodos: [{ puesto: 'Presidente del CSN', desde: '2015-01-01' }] },
      ],
    }
    expect(presidencias(d).map((p) => p.nombre)).toEqual(['Mariano Rajoy Brey', 'Pedro Sánchez Pérez-Castejón'])
  })
})

describe('recuento', () => {
  it('cada persona en su fuente', () => {
    const d = {
      personas: [
        { periodos: [{ desde: 'x' }] },
        { periodos: [{ hasta: 'x', fuente: 'oci' }] },
        { periodos: [{ hasta: 'x', fuente: 'oci' }, { desde: 'y' }] },
        { periodos: [{ desde: 'x', fuente: 'congreso' }] },
        { periodos: [{ desde: 'x', fuente: 'congreso' }, { desde: 'y' }] },
      ],
    }
    expect(recuento(d)).toEqual({ boe: 3, soloOci: 1, diputados: 1 })
  })
})

describe('formacionEn', () => {
  const persona = {
    periodos: [
      { puesto: 'Presidente del Gobierno', desde: '2018-06-02' },
      { fuente: 'congreso', formacion: 'PSOE', desde: '2016-07-18', hasta: '2016-10-29' },
      { fuente: 'congreso', formacion: 'PSOE', desde: '2019-11-27', hasta: '2023-05-30' },
    ],
  }
  it('la del mandato que cubre la fecha, o la del anterior más cercano', () => {
    expect(formacionEn(persona, '2020-01-01')).toBe('PSOE')
    expect(formacionEn(persona, '2018-06-02')).toBe('PSOE')
  })
  it('sin mandatos del Congreso unidos, nada', () => {
    expect(formacionEn({ periodos: [{ desde: '2018-01-01' }] }, '2018-06-02')).toBe('')
    expect(formacionEn(persona, '2010-01-01')).toBe('')
  })
  it('el Congreso no dice cese, dice baja', () => {
    expect(huecoDelPeriodo({ fuente: 'congreso', desde: '2023-08-17' })).toBe('sin baja en el Congreso')
  })
})

// Una diputada con su declaración de actividades, la forma que escribe
// exportar_cargos.py; los textos son de la declaración real de un diputado.
const diputada = {
  clave: 'congreso:persona:x',
  nombre: 'Pérez Gil, Ana',
  periodos: [
    {
      puesto: 'Escaño en la XV legislatura',
      cargo: 'Escaño en la XV legislatura',
      desde: '2023-08-17',
      fuente: 'congreso',
      formacion: 'PP',
      circunscripcion: 'Cádiz',
    },
  ],
  declaraciones: [
    { empleador: 'UNIPREX S.A.U.', sector: 'Privado', periodo: '2019-2021', descripcion: 'COLABORADOR' },
  ],
}

describe('diputados', () => {
  it('sus altas no llenan la columna de nombramientos y ceses', () => {
    expect(movimientos({ personas: [diputada] })).toEqual([])
  })
  it('se encuentran por formación, circunscripción y por para quién declararon trabajar', () => {
    const d = { personas: [diputada, ...datos.personas] }
    expect(buscarCargos(d, 'pp').map((p) => p.nombre)).toEqual(['Pérez Gil, Ana'])
    expect(buscarCargos(d, 'cadiz').map((p) => p.nombre)).toEqual(['Pérez Gil, Ana'])
    expect(buscarCargos(d, 'uniprex').map((p) => p.nombre)).toEqual(['Pérez Gil, Ana'])
  })
  it('en el buscador general, con su formación', () => {
    expect(resultadosDeCargos({ personas: [diputada] }, 'perez')[0].descripcion).toBe(
      'Escaño en la XV legislatura · PP',
    )
  })
  it('la lista por papel', () => {
    const d = [diputada, ...datos.personas]
    expect(dePapel(d, 'congreso')).toEqual([diputada])
    expect(dePapel(d, 'boe')).not.toContain(diputada)
    expect(dePapel(d, 'todos')).toHaveLength(d.length)
    const autorizada = { clave: 'oci:x', periodos: [{ hasta: '2020-01-01', fuente: 'oci' }], autorizaciones: [{ actividad: 'X' }] }
    expect(dePapel([...d, autorizada], 'autorizados')).toEqual([autorizada])
  })
  it('la ficha se llama por lo más alto que se sabe', () => {
    expect(papelDeLaFicha(diputada)).toBe('Congreso de los Diputados')
    expect(papelDeLaFicha(datos.personas[0])).toBe('Alto cargo')
    expect(papelDeLaFicha({ periodos: [{ fuente: 'oci', hasta: '2020-01-01' }] })).toBe('Ex alto cargo')
  })
})

describe('sectorDeclarado', () => {
  it('sólo los dos claros, escritos como se escriban', () => {
    expect(sectorDeclarado({ sector: 'PRIVADO AGRICOLA' })).toBe('privado')
    expect(sectorDeclarado({ sector: 'Privado' })).toBe('privado')
    expect(sectorDeclarado({ sector: 'PÚBLICO' })).toBe('publico')
    expect(sectorDeclarado({ sector: 'ADMINISTRACIÓN PÚBLICA' })).toBe('publico')
    expect(sectorDeclarado({ sector: 'Gubernamental' })).toBe('publico')
    expect(sectorDeclarado({ sector: 'Educación' })).toBe('')
    expect(sectorDeclarado({})).toBe('')
  })
})

describe('lineaDeTiempo fuera del eje', () => {
  it('lo que empieza o acaba fuera de lo leído sale abierto por ese lado', () => {
    const [b] = lineaDeTiempo([{ desde: '2023-08-17', hasta: '2027-01-01' }], '2025-05-14', '2026-09-16')
    expect(b.inicio).toBe(0)
    expect(b.fin).toBe(1)
    expect(b.abiertoIzquierda).toBe(true)
    expect(b.abiertoDerecha).toBe(true)
  })
})

describe('gobiernos', () => {
  const rajoy = { persona: 'boe:persona:rajoy', nombre: 'Mariano Rajoy Brey', formacion: 'PP' }
  const sanchez = { persona: 'boe:persona:sanchez', nombre: 'Pedro Sánchez Pérez-Castejón' }
  const d = {
    personas: [
      { clave: 'a', periodos: [{ desde: '2012-01-01', gobierno: rajoy }, { desde: '2013-01-01', gobierno: rajoy }] },
      { clave: 'b', periodos: [{ desde: '2019-01-01', gobierno: sanchez }, { desde: '2015-01-01', gobierno: rajoy }] },
      { clave: 'c', periodos: [{ hasta: '2019-01-01' }] },
    ],
  }
  it('uno por presidente, contando personas y no periodos, en orden de tiempo', () => {
    expect(gobiernos(d).map((g) => [g.nombre, g.personas])).toEqual([
      ['Mariano Rajoy Brey', 2],
      ['Pedro Sánchez Pérez-Castejón', 1],
    ])
  })
  it('el filtro, por la clave del presidente', () => {
    expect(bajoGobierno(d.personas, rajoy.persona).map((p) => p.clave)).toEqual(['a', 'b'])
    expect(bajoGobierno(d.personas, sanchez.persona).map((p) => p.clave)).toEqual(['b'])
    expect(bajoGobierno(d.personas, '')).toHaveLength(3)
  })
  it('el nombre, sin formación si no se sabe', () => {
    expect(nombreDeGobierno(rajoy)).toBe('Gobierno de Mariano Rajoy Brey · PP')
    expect(nombreDeGobierno(sanchez)).toBe('Gobierno de Pedro Sánchez Pérez-Castejón')
    expect(nombreDeGobierno(null)).toBe('')
  })
})

describe('delOrganoEnPalabras', () => {
  it('el verbo según de dónde sale el dinero, y los años', () => {
    expect(delOrganoEnPalabras({ pagos: 1, adjudicaciones: 0, desde: '2016-03-01', hasta: '2016-03-01' })).toEqual({
      verbo: 'pagó',
      cuantos: '1 pago',
      cuando: 'en 2016',
    })
    expect(delOrganoEnPalabras({ pagos: 0, adjudicaciones: 3, desde: '2015-01-01', hasta: '2018-12-31' })).toEqual({
      verbo: 'adjudicó',
      cuantos: '3 adjudicaciones',
      cuando: 'entre 2015 y 2018',
    })
    expect(delOrganoEnPalabras({ pagos: 2, adjudicaciones: 1 }).verbo).toBe('pagó o adjudicó')
    expect(delOrganoEnPalabras({ pagos: 2, adjudicaciones: 1 }).cuando).toBe('')
  })
})
