import { describe, expect, it } from 'vitest'
import {
  analizarMapa,
  balanceDe,
  caminosDe,
  colocarGrupos,
  disponerMapa,
  gruposDelMapa,
  MINIMO_RELATIVO,
  proyectar,
  vistaDe,
} from './mapa.js'

/*
  Dos grupos que no se tocan: un organismo con sus tres proveedores, y otro
  con los suyos. Louvain los separa sin duda posible, que es lo que hace
  falta para probar lo de dentro de cada uno.
*/
function datos() {
  const n = (id, schema, props) => ({ id, caption: id, schema, properties: props })
  const pago = (id, source, target, amount) => ({ id, source, target, amount: String(amount), schema: 'Payment' })
  return {
    nodes: [
      n('ayto', 'PublicBody'),
      n('e1', 'Company'),
      n('e2', 'Company'),
      n('e3', 'Company', { entidad_extranjera: true }),
      n('cons', 'PublicBody'),
      n('f1', 'Company'),
      n('f2', 'Company'),
      n('par', 'Organization'),
    ],
    edges: [
      pago('p1', 'ayto', 'e1', 100),
      pago('p2', 'ayto', 'e2', 50),
      pago('p3', 'ayto', 'e3', 30),
      pago('p4', 'e1', 'ayto', 5),
      pago('q1', 'cons', 'f1', 900),
      pago('q2', 'cons', 'f2', 400),
      pago('q3', 'cons', 'par', 10),
    ],
  }
}

function grupoDe(analisis, id) {
  return analisis.nucleos.find((g) => g.miembros.includes(id))
}

describe('analizarMapa', () => {
  it('el valor de una entidad es su dinero dentro del grupo', () => {
    const a = analizarMapa(datos())
    // El organismo cuenta todas sus relaciones; cada empresa, la suya.
    expect(a.interno.get('ayto')).toBe(185)
    expect(a.interno.get('e1')).toBe(105)
    expect(a.interno.get('e3')).toBe(30)
  })

  it('el dinero del grupo es el de sus relaciones internas, contado una vez', () => {
    const a = analizarMapa(datos())
    expect(grupoDe(a, 'ayto').dinero).toBe(185)
    expect(grupoDe(a, 'cons').dinero).toBe(1310)
  })

  it('los pagos guardan su sentido aunque haya relaciones en los dos', () => {
    const a = analizarMapa(datos())
    expect(a.pagos.get('ayto|e1')).toMatchObject({ de: 'ayto', a: 'e1', importe: 100 })
    expect(a.pagos.get('e1|ayto')).toMatchObject({ de: 'e1', a: 'ayto', importe: 5 })
  })

  it('los filtros quitan entidades antes de contar', () => {
    const a = analizarMapa(datos(), { soloExtranjero: true })
    // Sin su organismo, la extranjera se queda sola: un grupo de uno no es grupo.
    expect(a.nucleos).toEqual([])

    // e2 mueve 50 y e3 30: los dos por debajo de 60, y su dinero se va con ellos.
    const b = analizarMapa(datos(), { minImporte: 60 })
    expect(grupoDe(b, 'ayto').miembros.sort()).toEqual(['ayto', 'e1'])
    expect(grupoDe(b, 'ayto').dinero).toBe(105)
  })
})

describe('la edición de una comunidad', () => {
  function conTerritorio() {
    const d = datos()
    for (const n of d.nodes) {
      if (n.id === 'ayto') n.territorio = 'Andalucía'
      if (n.id === 'cons') n.territorio = 'Galicia'
    }
    return d
  }

  it('deja sus organismos y a quien cobra de ellos', () => {
    const a = analizarMapa(conTerritorio(), { territorio: 'Andalucía' })
    const ids = a.nucleos.flatMap((g) => g.miembros).sort()
    expect(ids).toEqual(['ayto', 'e1', 'e2', 'e3'])
  })

  it('el grupo se llama como quien queda, no como quien se ha ido', () => {
    const a = analizarMapa(conTerritorio(), { territorio: 'Andalucía' })
    const [g] = a.nucleos
    expect(g.principales.map((m) => m.id)).toContain('ayto')
    expect(g.etiqueta).toBe('ayto')
  })

  it('sin organismos de esa comunidad no queda nada, en vez de todo', () => {
    const a = analizarMapa(conTerritorio(), { territorio: 'Aragón' })
    expect(a.nucleos).toEqual([])
  })
})

describe('gruposDelMapa', () => {
  it('numera en el orden de la lista, el del dinero', () => {
    const a = analizarMapa(datos())
    const g = gruposDelMapa(a, { conPequenos: true })
    expect(g.map((x) => x.numero)).toEqual(['01', '02'])
    expect(g[0].miembros).toContain('cons')
  })

  it('sin los pequeños, el mismo corte que la lista', () => {
    const a = analizarMapa(datos())
    expect(gruposDelMapa(a)).toEqual([])
  })
})

describe('colocarGrupos', () => {
  const radios = [30, 22, 18, 15, 12, 10, 9, 7, 6, 5, 4, 3]

  it('ningún círculo pisa a otro y todos caben en el lienzo', () => {
    const c = colocarGrupos(radios, 900, 500)
    for (const x of c) {
      expect(x.x - x.r).toBeGreaterThanOrEqual(-0.01)
      expect(x.y - x.r).toBeGreaterThanOrEqual(-0.01)
      expect(x.x + x.r).toBeLessThanOrEqual(900.01)
      expect(x.y + x.r).toBeLessThanOrEqual(500.01)
    }
    for (let i = 0; i < c.length; i++) {
      for (let j = i + 1; j < c.length; j++) {
        const d = Math.hypot(c[i].x - c[j].x, c[i].y - c[j].y)
        expect(d).toBeGreaterThanOrEqual(c[i].r + c[j].r - 0.01)
      }
    }
  })

  it('el área sigue siendo el dato: los radios guardan su proporción', () => {
    const c = colocarGrupos(radios, 900, 500)
    expect(c[0].r / c[1].r).toBeCloseTo(30 / 22, 6)
  })

  it('en un lienzo apaisado se estira hacia los lados, no se queda en un círculo', () => {
    const c = colocarGrupos(radios, 1200, 500)
    const ancho = Math.max(...c.map((x) => x.x + x.r)) - Math.min(...c.map((x) => x.x - x.r))
    const alto = Math.max(...c.map((x) => x.y + x.r)) - Math.min(...c.map((x) => x.y - x.r))
    expect(ancho / alto).toBeGreaterThan(1.4)
  })

  it('es determinista', () => {
    expect(colocarGrupos(radios, 800, 600)).toEqual(colocarGrupos(radios, 800, 600))
  })
})

describe('disponerMapa', () => {
  it('cada entidad cae dentro del círculo de su grupo', () => {
    const a = analizarMapa(datos())
    const { grupos } = disponerMapa(a, gruposDelMapa(a, { conPequenos: true }), 800, 500)
    for (const g of grupos) {
      for (const m of g.miembros) {
        expect(Math.hypot(m.x - g.x, m.y - g.y) + m.r).toBeLessThanOrEqual(g.r + 0.01)
      }
    }
  })

  it('el área del grupo es proporcional a su dinero interno', () => {
    const a = analizarMapa(datos())
    const { grupos } = disponerMapa(a, gruposDelMapa(a, { conPequenos: true }), 800, 500)
    const [grande, pequeno] = grupos
    // Cada relación cuenta en sus dos extremos: 2 × 1310 frente a 2 × 185.
    expect((grande.r / pequeno.r) ** 2).toBeCloseTo(1310 / 185, 3)
  })
})

describe('el mínimo de tamaño', () => {
  it('un grupo diminuto se dibuja en el mínimo, y se dice', () => {
    const d = datos()
    // El segundo grupo pasa a mover casi nada.
    for (const e of d.edges) if (e.source === 'ayto' || e.target === 'ayto') e.amount = '0.01'
    const a = analizarMapa(d)
    const { grupos } = disponerMapa(a, gruposDelMapa(a, { conPequenos: true }), 800, 500)
    const [grande, pequeno] = grupos
    expect(pequeno.agrandado).toBe(true)
    expect(grande.agrandado).toBe(false)
    expect(pequeno.r / grande.r).toBeCloseTo(MINIMO_RELATIVO, 6)
    // La cifra sigue siendo la real.
    expect(pequeno.dinero).toBeCloseTo(0.04, 6)
  })
})

describe('caminos y balance', () => {
  it('los caminos van de más a menos dinero y con su sentido', () => {
    const a = analizarMapa(datos())
    const c = caminosDe(a, 'ayto')
    expect(c.map((p) => p.importe)).toEqual([100, 50, 30, 5])
    expect(c[3]).toMatchObject({ de: 'e1', a: 'ayto' })
    expect(caminosDe(a, 'ayto', 2)).toHaveLength(2)
  })

  it('el balance separa lo que paga de lo que cobra', () => {
    const a = analizarMapa(datos())
    expect(balanceDe(a, 'e1')).toEqual({ paga: 5, aCuantos: 1, cobra: 100, deCuantos: 1 })
  })
})

describe('la cámara', () => {
  it('sin grupo mira el dibujo entero, a escala uno', () => {
    const v = vistaDe(null, 800, 500)
    expect(proyectar(100, 50, v, 800, 500)).toEqual({ x: 100, y: 50, k: 1 })
  })

  it('con grupo, su centro cae en el centro de la pantalla', () => {
    const v = vistaDe({ x: 120, y: 80, r: 40 }, 800, 500)
    const p = proyectar(120, 80, v, 800, 500)
    expect(p.x).toBe(400)
    expect(p.y).toBe(250)
    // y el círculo ocupa casi todo el alto
    expect(40 * 2 * p.k).toBeCloseTo(500 / 1.08, 6)
  })
})
