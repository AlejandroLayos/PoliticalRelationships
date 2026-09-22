import { describe, expect, it } from 'vitest'
import {
  cercania,
  despliegue,
  entre,
  faseDe,
  medidorDeFluidez,
  posicionEnDeriva,
  puntosDeReposo,
  realce,
  semillaDePosicion,
} from './vida.js'

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

describe('realce', () => {
  const correr = (r, ms, veces) => {
    let sigue = false
    for (let i = 0; i < veces; i += 1) sigue = r.avanza(ms)
    return sigue
  }

  it('nace apagado y no pide repintar', () => {
    const r = realce()
    expect(r.intensidad).toBe(0)
    expect(r.activo).toBe(false)
    expect(r.avanza(16)).toBe(false)
  })

  it('al apuntar sube hasta el tope y se para', () => {
    const r = realce(200)
    r.apunta('a')
    expect(correr(r, 16, 60)).toBe(false)
    expect(r.intensidad).toBe(1)
    expect(r.id).toBe('a')
  })

  it('no salta de golpe: a mitad de camino va a mitad', () => {
    // Sin transición, apuntar a un nodo es un corte y el ojo pierde dónde
    // estaba. Lo que se quiere ver es el vecindario saliendo de la masa.
    const r = realce(200)
    r.apunta('a')
    r.avanza(16)
    expect(r.intensidad).toBeGreaterThan(0)
    expect(r.intensidad).toBeLessThan(0.6)
  })

  it('al soltar baja hasta cero y suelta a quién realzaba', () => {
    const r = realce(200)
    r.apunta('a')
    correr(r, 16, 60)
    r.apunta('')
    expect(correr(r, 16, 60)).toBe(false)
    expect(r.intensidad).toBe(0)
    expect(r.id).toBe('')
  })

  it('mientras se apaga sigue sabiendo a quién, para no cortar el fundido', () => {
    const r = realce(200)
    r.apunta('a')
    correr(r, 16, 60)
    r.apunta('')
    r.avanza(16)
    expect(r.id).toBe('a')
    expect(r.activo).toBe(true)
  })

  it('cambiar de nodo a mitad del fundido apunta al nuevo', () => {
    const r = realce(200)
    r.apunta('a')
    r.avanza(16)
    r.apunta('b')
    expect(r.id).toBe('b')
  })

  it('un fotograma enorme no se pasa del tope', () => {
    const r = realce(200)
    r.apunta('a')
    r.avanza(5000)
    expect(r.intensidad).toBeLessThanOrEqual(1)
  })
})

describe('entre', () => {
  it('interpola y no se sale de los extremos', () => {
    expect(entre(10, 20, 0)).toBe(10)
    expect(entre(10, 20, 1)).toBe(20)
    expect(entre(10, 20, 0.5)).toBe(15)
    expect(entre(10, 20, -3)).toBe(10)
    expect(entre(10, 20, 9)).toBe(20)
  })
})

describe('semillaDePosicion', () => {
  it('la misma entidad arranca siempre en el mismo sitio', () => {
    // ForceAtlas2 es determinista si el punto de partida lo es. Con
    // `Math.random()` la misma instantánea salía dibujada distinta en cada
    // visita: girada, del revés, con los haces hacia otro lado.
    expect(semillaDePosicion('nif:B123')).toEqual(semillaDePosicion('nif:B123'))
  })

  it('cae dentro del cuadrado unidad', () => {
    for (const id of ['a', 'bb', 'placsp:organo:x-1234', '']) {
      const p = semillaDePosicion(id)
      expect(p.x).toBeGreaterThanOrEqual(0)
      expect(p.x).toBeLessThanOrEqual(1)
      expect(p.y).toBeGreaterThanOrEqual(0)
      expect(p.y).toBeLessThanOrEqual(1)
    }
  })

  it('no las pone todas en la diagonal', () => {
    const puntos = Array.from({ length: 40 }, (_, i) => semillaDePosicion(`n${i}`))
    const enLaDiagonal = puntos.filter((p) => Math.abs(p.x - p.y) < 0.02).length
    expect(enLaDiagonal).toBeLessThan(5)
  })

  it('reparte, no amontona', () => {
    const puntos = Array.from({ length: 200 }, (_, i) => semillaDePosicion(`e${i}`))
    const cuadrantes = new Set(puntos.map((p) => `${p.x < 0.5}${p.y < 0.5}`))
    expect(cuadrantes.size).toBe(4)
  })
})

describe('despliegue', () => {
  it('empieza a cero y acaba en uno', () => {
    const d = despliegue(1000)
    expect(d.avance).toBe(0)
    expect(d.acabado).toBe(false)
    while (d.avanza(16)) { /* hasta el final */ }
    expect(d.avance).toBe(1)
    expect(d.acabado).toBe(true)
  })

  it('frena al llegar, no va a velocidad constante', () => {
    // Lineal parece una cinta transportadora; algo que se coloca arranca
    // deprisa y frena.
    const d = despliegue(1000)
    d.avanza(500)
    expect(d.avance).toBeGreaterThan(0.8)
  })

  it('deja de pedir fotogramas cuando acaba', () => {
    const d = despliegue(100)
    d.avanza(200)
    expect(d.avanza(16)).toBe(false)
  })

  it('se puede mandar al final de golpe', () => {
    const d = despliegue(1000)
    d.termina()
    expect(d.acabado).toBe(true)
    expect(d.avance).toBe(1)
  })

  it('un fotograma enorme no se pasa', () => {
    const d = despliegue(1000)
    d.avanza(1e6)
    expect(d.avance).toBe(1)
  })
})
