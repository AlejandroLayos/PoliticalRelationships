import { describe, expect, it } from 'vitest'
import { areaDeInfluencia, concentracion, redDeFlujo, resumenEnPalabras } from './influencia.js'

/**
 * Un caso con las tres clases de arista a la vez, porque lo que hay que
 * comprobar es justamente que NO se mezclan: un partido que cobra
 * subvenciones, que paga a una consultora, y al que el Tribunal de Cuentas ha
 * sancionado.
 */
function grafoDeUnPartido() {
  return {
    nodes: [
      { id: 'partido', caption: 'PARTIDO EJEMPLO', schema: 'Organization', properties: { partido_politico: true } },
      { id: 'interior', caption: 'MINISTERIO DEL INTERIOR', schema: 'PublicBody', properties: {} },
      { id: 'ayto', caption: 'AYUNTAMIENTO DE EJEMPLO', schema: 'PublicBody', properties: {} },
      { id: 'consultora', caption: 'CONSULTORA SL', schema: 'Company', properties: {} },
      { id: 'extranjera', caption: 'FOREIGN MEDIA BV', schema: 'Company', properties: { entidad_extranjera: true, motivo_extranjera: 'NIF de entidad extranjera (letra N)' } },
      { id: 'tcu', caption: 'Tribunal de Cuentas', schema: 'PublicBody', properties: {} },
      { id: 'rival', caption: 'OTRA EMPRESA SL', schema: 'Company', properties: {} },
    ],
    edges: [
      { id: 'p1', source: 'interior', target: 'partido', amount: '120000', schema: 'Payment', confidence: 1, status: 'asserted' },
      { id: 'p2', source: 'ayto', target: 'partido', amount: '30000', schema: 'Payment', confidence: 1, status: 'asserted' },
      { id: 'p3', source: 'partido', target: 'consultora', amount: '45000', schema: 'Payment', confidence: 1, status: 'asserted' },
      { id: 'p4', source: 'partido', target: 'extranjera', amount: '80000', schema: 'Payment', confidence: 1, status: 'asserted' },
      // Sanción del TdC: el partido es el DEUDOR. No está financiando al Estado.
      { id: 'd1', source: 'partido', target: 'tcu', amount: '50000', schema: 'Debt', confidence: 1, status: 'asserted', start_date: '2022-01-17' },
      // Otra empresa que cobra del mismo ministerio: ámbito de interés común.
      { id: 'p5', source: 'interior', target: 'rival', amount: '900000', schema: 'Payment', confidence: 1, status: 'asserted' },
      // Estructura sin dinero: no debe contarse como financiación.
      { id: 'u1', source: 'interior', target: 'partido', schema: 'UnknownLink', confidence: 1, status: 'asserted' },
    ],
  }
}

describe('areaDeInfluencia', () => {
  it('separa de quién recibe y a quién paga', () => {
    const a = areaDeInfluencia(grafoDeUnPartido(), 'partido')
    expect(a.recibeDe.map((x) => x.caption)).toEqual([
      'MINISTERIO DEL INTERIOR',
      'AYUNTAMIENTO DE EJEMPLO',
    ])
    expect(a.pagaA.map((x) => x.caption)).toEqual(['FOREIGN MEDIA BV', 'CONSULTORA SL'])
  })

  it('ordena por dinero: lo primero que se lee es lo que más pesa', () => {
    const a = areaDeInfluencia(grafoDeUnPartido(), 'partido')
    expect(a.recibeDe[0].total).toBe(120000)
    expect(a.pagaA[0].total).toBe(80000)
  })

  it('suma los totales de cada lado', () => {
    const a = areaDeInfluencia(grafoDeUnPartido(), 'partido')
    expect(a.totalRecibido).toBe(150000)
    expect(a.totalPagado).toBe(125000)
  })

  it('una sanción NO es el partido financiando al Estado', () => {
    // El fallo que esto evita: Debt va deudor -> acreedor, así que mirando
    // sólo la dirección una multa parecería un pago del partido a la
    // Administración y saldría en "a quién paga". Sería una lectura falsa.
    const a = areaDeInfluencia(grafoDeUnPartido(), 'partido')
    expect(a.pagaA.map((x) => x.caption)).not.toContain('Tribunal de Cuentas')
    expect(a.totalPagado).toBe(125000) // sin los 50.000 de la multa
    expect(a.sanciones).toHaveLength(1)
    expect(a.sanciones[0].importe).toBe(50000)
    expect(a.totalSancionado).toBe(50000)
  })

  it('la estructura sin dinero no cuenta como financiación', () => {
    const a = areaDeInfluencia(grafoDeUnPartido(), 'partido')
    // El UnknownLink del ministerio no puede inflar ni el total ni el número
    // de relaciones.
    const ministerio = a.recibeDe.find((x) => x.caption === 'MINISTERIO DEL INTERIOR')
    expect(ministerio.n).toBe(1)
  })

  it('mide la exposición a capital extranjero', () => {
    const a = areaDeInfluencia(grafoDeUnPartido(), 'partido')
    expect(a.extranjero.contrapartes.map((x) => x.caption)).toEqual(['FOREIGN MEDIA BV'])
    expect(a.extranjero.total).toBe(80000)
    // 80.000 de 275.000 movidos.
    expect(a.extranjero.porcentaje).toBeCloseTo((80000 / 275000) * 100, 5)
  })

  it('encuentra quién más cobra de sus mismos pagadores', () => {
    const a = areaDeInfluencia(grafoDeUnPartido(), 'partido')
    const rival = a.comparten.find((x) => x.caption === 'OTRA EMPRESA SL')
    expect(rival).toBeTruthy()
    expect(rival.pagadoresComunes).toBe(1)
    // Y la propia entidad no puede salir en su propia lista.
    expect(a.comparten.map((x) => x.id)).not.toContain('partido')
  })

  it('conserva la confianza de la relación más floja', () => {
    const datos = grafoDeUnPartido()
    datos.edges.push({
      id: 'p6', source: 'interior', target: 'partido', amount: '10', schema: 'Payment',
      confidence: 0.5, status: 'inferred',
    })
    const a = areaDeInfluencia(datos, 'partido')
    const ministerio = a.recibeDe.find((x) => x.caption === 'MINISTERIO DEL INTERIOR')
    expect(ministerio.confianza).toBe(0.5)
    expect(ministerio.inferido).toBe(true)
  })

  it('devuelve una ficha vacía si la entidad no existe', () => {
    const a = areaDeInfluencia(grafoDeUnPartido(), 'no-existe')
    expect(a.entidad).toBeNull()
    expect(a.recibeDe).toEqual([])
  })

  it('no revienta sin datos', () => {
    expect(() => areaDeInfluencia(undefined, 'x')).not.toThrow()
  })

  it('una entidad sin movimientos da totales a cero, no error', () => {
    const datos = {
      nodes: [{ id: 'solo', caption: 'SOLO', schema: 'Company', properties: {} }],
      edges: [],
    }
    const a = areaDeInfluencia(datos, 'solo')
    expect(a.totalRecibido).toBe(0)
    expect(a.extranjero.porcentaje).toBe(0)
  })
})

describe('redDeFlujo', () => {
  it('coloca a cada contraparte en su lado', () => {
    const datos = grafoDeUnPartido()
    const a = areaDeInfluencia(datos, 'partido')
    const { nodes } = a.red
    const porId = Object.fromEntries(nodes.map((n) => [n.id, n]))
    expect(porId.partido.lado).toBe('centro')
    expect(porId.interior.lado).toBe('izquierda')
    expect(porId.consultora.lado).toBe('derecha')
  })

  it('no mete en el flujo la arista de la sanción', () => {
    const a = areaDeInfluencia(grafoDeUnPartido(), 'partido')
    expect(a.red.edges.map((e) => e.schema)).not.toContain('Debt')
  })

  it('dice cuántas contrapartes se ha dejado fuera al recortar', () => {
    const nodes = [{ id: 'c', caption: 'CENTRO', schema: 'PublicBody', properties: {} }]
    const edges = []
    for (let i = 0; i < 20; i += 1) {
      nodes.push({ id: `e${i}`, caption: `E${i}`, schema: 'Company', properties: {} })
      edges.push({ id: `a${i}`, source: 'c', target: `e${i}`, amount: String(100 - i), schema: 'Payment', confidence: 1, status: 'asserted' })
    }
    const a = areaDeInfluencia({ nodes, edges }, 'c')
    expect(a.red.recortadoDerecha).toBe(6)
  })
})

describe('resumenEnPalabras', () => {
  it('resume la ficha en una frase legible', () => {
    const a = areaDeInfluencia(grafoDeUnPartido(), 'partido')
    const frase = resumenEnPalabras(a)
    expect(frase).toContain('recibe')
    expect(frase).toContain('reparte')
    expect(frase).toContain('expediente sancionador')
  })

  it('lo dice claro cuando no hay nada', () => {
    const datos = { nodes: [{ id: 'x', caption: 'X', schema: 'Company', properties: {} }], edges: [] }
    expect(resumenEnPalabras(areaDeInfluencia(datos, 'x'))).toContain('Sin movimientos')
  })
})

describe('cifras que no se publican', () => {
  it('cuenta las relaciones sin importe y dice por qué cuando se sabe', () => {
    // El caso real: PLACSP publicó un contrato de 22.000 € con un importe
    // adjudicado de 1.954 millones, y la ingesta no publica esa cifra. Si la
    // ficha se limita a no sumarla, el hueco no se distingue de «la fuente no
    // dio importe» — y la ausencia de dato pasa por dato.
    const datos = grafoDeUnPartido()
    datos.edges.push({
      id: 'p9', source: 'partido', target: 'consultora', schema: 'Payment',
      confidence: 0.5, status: 'asserted',
      properties: { motivoImporteDudoso: 'supera en más de 10 veces el presupuesto (22000)' },
    })
    const a = areaDeInfluencia(datos, 'partido')
    const c = a.pagaA.find((x) => x.caption === 'CONSULTORA SL')
    expect(c.sinCifra).toBe(1)
    expect(c.motivosSinCifra[0]).toContain('22000')
    // Y no inventa un importe para rellenar el hueco.
    expect(c.total).toBe(45000)
  })

  it('una relación sin importe y sin motivo no finge tenerlo', () => {
    const datos = grafoDeUnPartido()
    datos.edges.push({
      id: 'p10', source: 'interior', target: 'partido', schema: 'Payment',
      confidence: 1, status: 'asserted',
    })
    const a = areaDeInfluencia(datos, 'partido')
    const m = a.recibeDe.find((x) => x.caption === 'MINISTERIO DEL INTERIOR')
    expect(m.sinCifra).toBe(1)
    expect(m.motivosSinCifra).toEqual([])
  })
})

describe('indicio de capital extranjero', () => {
  function conIndicio() {
    const datos = grafoDeUnPartido()
    datos.nodes.push({
      id: 'sinnif',
      caption: 'META PLATFORMS IRELAND LIMITED',
      schema: 'Company',
      properties: {
        entidad_extranjera_indicio: true,
        motivo_extranjera_indicio: 'sin NIF español y con forma societaria extranjera en el nombre',
      },
    })
    datos.edges.push({
      id: 'p20', source: 'partido', target: 'sinnif', amount: '20000',
      schema: 'Payment', confidence: 1, status: 'asserted',
    })
    return areaDeInfluencia(datos, 'partido')
  }

  it('recoge las contrapartes sin NIF con forma extranjera', () => {
    const a = conIndicio()
    expect(a.extranjero.indicios.map((x) => x.caption)).toEqual(['META PLATFORMS IRELAND LIMITED'])
    expect(a.extranjero.totalIndicios).toBe(20000)
  })

  it('un indicio NO entra en el porcentaje de exposición probada', () => {
    // Ese porcentaje se lee como un hecho, así que sólo puede salir de hechos.
    // Con el indicio dentro pasaría de 80.000 a 100.000 sobre lo movido, y la
    // diferencia entre «lo dice su NIF» y «lo parece por el nombre» se habría
    // perdido por el camino.
    const a = conIndicio()
    expect(a.extranjero.total).toBe(80000)
    expect(a.extranjero.contrapartes.map((x) => x.caption)).toEqual(['FOREIGN MEDIA BV'])
  })

  it('una entidad probada por NIF no se duplica como indicio', () => {
    const a = conIndicio()
    expect(a.extranjero.indicios.map((x) => x.caption)).not.toContain('FOREIGN MEDIA BV')
  })
})

describe('por qué orbitan', () => {
  /**
   * El bloque «orbitan a sus mismos pagadores» insinuaba.
   *
   * En la ficha del PSOE salían listados el PP, VOX, Podemos y once partidos
   * más, cada uno con su cifra. Es verdad y no dice nada: lo que comparten es
   * la Dirección General de Política Interior, que es quien paga la subvención
   * electoral a todos los partidos. Descubrir que los partidos cobran de quien
   * paga a los partidos no es un hallazgo, y presentarlo como una órbita común
   * sí lo parece.
   */
  function grafoDeSubvencionElectoral(cuantosPartidos) {
    const nodes = [{ id: 'dgpi', caption: 'D.G. DE POLÍTICA INTERIOR', schema: 'PublicBody', properties: {} }]
    const edges = []
    for (let i = 0; i < cuantosPartidos; i += 1) {
      nodes.push({ id: `p${i}`, caption: `PARTIDO ${i}`, schema: 'Organization', properties: {} })
      edges.push({
        id: `a${i}`, source: 'dgpi', target: `p${i}`, amount: `${1000 * (i + 1)}`,
        schema: 'Payment', confidence: 1, status: 'asserted',
      })
    }
    return { nodes, edges }
  }

  it('con un pagador que reparte entre catorce, no se lista a nadie', () => {
    // Decir al lado «reparte entre catorce» no bastaba: el matiz llega
    // después de haber leído trece nombres de partidos juntos. Si ningún
    // pagador compartido es estrecho, no hay lista, hay una frase.
    const area = areaDeInfluencia(grafoDeSubvencionElectoral(14), 'p0')
    expect(area.comparten).toEqual([])
    expect(area.compartenDeProgramaGeneral).toMatchObject({
      caption: 'D.G. DE POLÍTICA INTERIOR',
      alcance: 14,
      entidades: 13,
    })
  })

  it('con un pagador estrecho sí se lista, y sólo lo que ese pagador toca', () => {
    const { nodes, edges } = grafoDeSubvencionElectoral(14)
    nodes.push({ id: 'dip', caption: 'DIPUTACIÓN DE SORIA', schema: 'PublicBody', properties: {} })
    nodes.push({ id: 'emp', caption: 'EMPRESA SL', schema: 'Company', properties: {} })
    edges.push({ id: 'x1', source: 'dip', target: 'p0', amount: '500', schema: 'Payment', confidence: 1, status: 'asserted' })
    edges.push({ id: 'x2', source: 'dip', target: 'emp', amount: '500', schema: 'Payment', confidence: 1, status: 'asserted' })

    const area = areaDeInfluencia({ nodes, edges }, 'p0')
    // La empresa comparte la Diputación, que reparte entre dos: eso sí dice
    // algo. Los trece partidos siguen fuera, que comparten sólo la D.G.
    expect(area.comparten.map((c) => c.caption)).toEqual(['EMPRESA SL'])
    expect(area.compartenDeProgramaGeneral).toBe(null)
    const porNombre = Object.fromEntries(area.compartenPor.map((v) => [v.caption, v]))
    expect(porNombre['DIPUTACIÓN DE SORIA'].alcance).toBe(2)
  })

  it('justo en el umbral se sigue listando', () => {
    // Diez receptores es el límite de «este paga a unos pocos»; once ya no.
    expect(areaDeInfluencia(grafoDeSubvencionElectoral(10), 'p0').comparten.length).toBe(9)
    expect(areaDeInfluencia(grafoDeSubvencionElectoral(11), 'p0').comparten).toEqual([])
  })

  it('sin pagadores compartidos no hay nada que explicar', () => {
    const nodes = [
      { id: 'o', caption: 'ORGANISMO', schema: 'PublicBody', properties: {} },
      { id: 'e', caption: 'EMPRESA', schema: 'Company', properties: {} },
    ]
    const edges = [{ id: 'a', source: 'o', target: 'e', amount: '100', schema: 'Payment', confidence: 1, status: 'asserted' }]
    const area = areaDeInfluencia({ nodes, edges }, 'e')
    expect(area.compartenPor).toEqual([])
    expect(area.compartenDeProgramaGeneral).toBe(null)
  })
})

describe('concentración', () => {
  /**
   * «Reparte 224 M € entre 77 receptores» suena a mucho reparto, y puede que
   * los cinco primeros se lleven la mitad. El número de receptores no lo dice.
   */
  it('mide la parte del primero y la de los cinco primeros', () => {
    const lista = [
      { id: 'a', caption: 'GRANDE', total: 50 },
      { id: 'b', caption: 'B', total: 20 },
      { id: 'c', caption: 'C', total: 15 },
      { id: 'd', caption: 'D', total: 10 },
      { id: 'e', caption: 'E', total: 4 },
      { id: 'f', caption: 'F', total: 1 },
    ]
    const c = concentracion(lista)
    expect(c.primero).toBe(50)
    expect(c.nombrePrimero).toBe('GRANDE')
    expect(c.cabeza).toBe(99)
    expect(c.deCuantos).toBe(6)
    expect(c.cuantos).toBe(5)
  })

  it('con una sola contraparte no hay reparto del que hablar', () => {
    expect(concentracion([{ id: 'a', caption: 'A', total: 100 }])).toBeNull()
    expect(concentracion([])).toBeNull()
    expect(concentracion(null)).toBeNull()
  })

  it('sin dinero tampoco', () => {
    expect(concentracion([
      { id: 'a', caption: 'A', total: 0 },
      { id: 'b', caption: 'B', total: 0 },
    ])).toBeNull()
  })

  it('las contrapartes sin cifra no cuentan en el reparto', () => {
    // Si contaran como cero, bajarían el porcentaje del primero e inventarían
    // un reparto más amplio del que consta.
    const c = concentracion([
      { id: 'a', caption: 'A', total: 80 },
      { id: 'b', caption: 'B', total: 20 },
      { id: 'c', caption: 'SIN CIFRA', total: 0 },
    ])
    expect(c.primero).toBe(80)
    expect(c.deCuantos).toBe(2)
  })
})

describe('periodo', () => {
  const nodes = [
    { id: 'o', caption: 'ORGANISMO', schema: 'PublicBody', properties: {} },
    { id: 'e', caption: 'EMPRESA', schema: 'Company', properties: {} },
  ]
  const arista = (id, fecha) => ({
    id, source: 'o', target: 'e', amount: '100', schema: 'Payment',
    confidence: 1, status: 'asserted', start_date: fecha,
  })

  it('el primer y el último día con operaciones fechadas', () => {
    const area = areaDeInfluencia(
      { nodes, edges: [arista('a', '2025-03-06'), arista('b', '2025-12-04'), arista('c', '2025-07-04')] },
      'o',
    )
    expect(area.periodo).toEqual({ desde: '2025-03-06', hasta: '2025-12-04' })
  })

  it('sin fechas, no se inventa ninguna', () => {
    const area = areaDeInfluencia({ nodes, edges: [arista('a', undefined)] }, 'o')
    expect(area.periodo).toBeNull()
  })

  it('una sola operación tiene principio y fin el mismo día', () => {
    const area = areaDeInfluencia({ nodes, edges: [arista('a', '2025-05-05')] }, 'o')
    expect(area.periodo).toEqual({ desde: '2025-05-05', hasta: '2025-05-05' })
  })
})
