import { describe, expect, it } from 'vitest'
import { cercania, faseDe, medidorDeFluidez, posicionEnDeriva, puntosDeReposo } from './vida.js'

const NODOS = [
  { id: 'a', x: 0, y: 0, size: 4 },
  { id: 'b', x: 100, y: 0, size: 14 },
  { id: 'c', x: 100, y: 100, size: 4 },
]

describe('faseDe', () => {
  it('la misma entidad respira siempre igual', () => {
    // Con `Math.random()` cada carga daría una animación distinta. No cambia
    // ningún dato, pero el agrupamiento se hizo determinista por una razón.
    expect(faseDe('nif:B12345678')).toBe(faseDe('nif:B12345678'))
  })

  it('entidades distintas no van a la vez', () => {
    const fases = new Set(['a', 'b', 'c', 'd', 'e'].map(faseDe))
    expect(fases.size).toBe(5)
  })

  it('cae dentro de una vuelta completa', () => {
    for (const id of ['', 'x', 'placsp:organo:algo-largo-1234']) {
      expect(faseDe(id)).toBeGreaterThanOrEqual(0)
      expect(faseDe(id)).toBeLessThan(Math.PI * 2 + 0.001)
    }
  })
})

describe('puntosDeReposo', () => {
  it('el radio del foco sale del tamaño del dibujo', () => {
    const { radio, diagonal } = puntosDeReposo(NODOS)
    expect(diagonal).toBeCloseTo(Math.hypot(100, 100), 5)
    expect(radio).toBeCloseTo(diagonal * 0.12, 5)
  })

  it('los puntos gordos se mueven menos que los pequeños', () => {
    // Un punto grande es un organismo con mucho dinero alrededor: que pese se
    // nota. Sin esto todo flota igual y parece un salvapantallas.
    const { reposo } = puntosDeReposo(NODOS)
    expect(reposo.get('b').amplitud).toBeLessThan(reposo.get('a').amplitud)
  })

  it('la amplitud es pequeña comparada con el dibujo', () => {
    // Si se va de las manos, los nodos se cruzan y las aristas bailan: deja
    // de parecer una red y pasa a parecer una animación.
    const { reposo, diagonal } = puntosDeReposo(NODOS)
    for (const b of reposo.values()) expect(b.amplitud).toBeLessThan(diagonal * 0.01)
  })

  it('sin nodos no revienta', () => {
    expect(puntosDeReposo([]).reposo.size).toBe(0)
    expect(puntosDeReposo(null).radio).toBe(0)
  })
})

describe('posicionEnDeriva', () => {
  it('nunca se aleja más de la amplitud en cada eje', () => {
    const base = { x: 10, y: 20, fase: 1.2, amplitud: 3 }
    for (let t = 0; t < 60; t += 0.13) {
      const p = posicionEnDeriva(base, t)
      expect(Math.abs(p.x - base.x)).toBeLessThanOrEqual(3.0001)
      expect(Math.abs(p.y - base.y)).toBeLessThanOrEqual(3.0001)
    }
  })

  it('no late a la vez en los dos ejes', () => {
    // Con un solo periodo el dibujo entero se encoge y se estira como un
    // corazón. Los dos senos tienen que desincronizarse.
    const base = { x: 0, y: 0, fase: 0, amplitud: 1 }
    const iguales = []
    for (let t = 0; t < 40; t += 0.5) {
      const p = posicionEnDeriva(base, t)
      iguales.push(Math.abs(p.x - p.y) < 0.01)
    }
    expect(iguales.filter(Boolean).length).toBeLessThan(iguales.length / 2)
  })
})

describe('cercania', () => {
  const raton = { x: 0, y: 0 }

  it('en el centro, todo; fuera del radio, nada', () => {
    expect(cercania(0, 0, raton, 10)).toBeCloseTo(1, 6)
    expect(cercania(10, 0, raton, 10)).toBe(0)
    expect(cercania(50, 50, raton, 10)).toBe(0)
  })

  it('cae suave: en el borde vale casi cero', () => {
    // Un corte duro dibuja un círculo en la pantalla; el coseno alzado no.
    expect(cercania(9.5, 0, raton, 10)).toBeLessThan(0.01)
    expect(cercania(5, 0, raton, 10)).toBeCloseTo(0.5, 5)
  })

  it('sin cursor o sin radio no hay foco', () => {
    expect(cercania(0, 0, null, 10)).toBe(0)
    expect(cercania(0, 0, raton, 0)).toBe(0)
  })
})

describe('medidorDeFluidez', () => {
  const correr = (m, hueco, cuantos, desde = 1000) => {
    let t = desde
    for (let i = 0; i < cuantos; i += 1) {
      m.anota(t)
      t += hueco
    }
    return t
  }

  it('mientras no hay datos, se anima', () => {
    // Apagar antes de saber si hace falta sería apagar siempre.
    expect(medidorDeFluidez().viable).toBe(true)
  })

  it('a 60 por segundo sigue animando', () => {
    const m = medidorDeFluidez()
    correr(m, 16.7, 120)
    expect(m.viable).toBe(true)
  })

  it('a 19 por segundo se rinde', () => {
    // Es lo que se midió con render por software: ahí la respiración deja la
    // página pegajosa y vale más el dibujo quieto.
    const m = medidorDeFluidez()
    correr(m, 52, 120)
    expect(m.viable).toBe(false)
  })

  it('una pestaña que vuelve del fondo no cuenta como lentitud', () => {
    const m = medidorDeFluidez()
    let t = correr(m, 16.7, 120)
    m.anota(t + 30000)
    correr(m, 16.7, 40, t + 30000 + 16.7)
    expect(m.viable).toBe(true)
  })

  it('una vez que se rinde, no vuelve', () => {
    // Apagar sube la fluidez; si eso volviera a encenderla, el dibujo daría
    // tirones cada segundo.
    const m = medidorDeFluidez()
    correr(m, 52, 120)
    expect(m.viable).toBe(false)
    correr(m, 16.7, 200, 100000)
    expect(m.viable).toBe(false)
  })

  it('no se rinde por unos pocos fotogramas malos al arrancar', () => {
    const m = medidorDeFluidez()
    correr(m, 60, 8)
    expect(m.viable).toBe(true)
  })
})
