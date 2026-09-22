import { describe, expect, it } from 'vitest'
import { repartirRectangulo } from './rectangulos.js'

const MARCO = { x: 0, y: 0, ancho: 800, alto: 500 }

function areas(cajas) {
  return cajas.map((c) => c.ancho * c.alto)
}

function seSolapan(a, b) {
  const e = 0.001
  return a.x < b.x + b.ancho - e && b.x < a.x + a.ancho - e && a.y < b.y + b.alto - e && b.y < a.y + a.alto - e
}

describe('repartirRectangulo', () => {
  it('el área de cada caja es proporcional a su valor', () => {
    // Es lo único que el dibujo afirma: un bloque el doble de grande es el
    // doble de dinero. Si esto falla, el mapa miente.
    const valores = [100, 50, 25, 25]
    const cajas = repartirRectangulo(valores, MARCO)
    const total = valores.reduce((s, v) => s + v, 0)
    const superficie = MARCO.ancho * MARCO.alto
    for (const [n, caja] of cajas.entries()) {
      expect(caja.ancho * caja.alto).toBeCloseTo((valores[n] / total) * superficie, 3)
    }
  })

  it('llena el marco entero', () => {
    const cajas = repartirRectangulo([7, 3, 2, 9, 4, 1, 6], MARCO)
    const suma = areas(cajas).reduce((s, a) => s + a, 0)
    expect(suma).toBeCloseTo(MARCO.ancho * MARCO.alto, 2)
  })

  it('no se sale del marco', () => {
    for (const caja of repartirRectangulo([9, 5, 4, 3, 2, 2, 1, 1], MARCO)) {
      expect(caja.x).toBeGreaterThanOrEqual(MARCO.x - 0.001)
      expect(caja.y).toBeGreaterThanOrEqual(MARCO.y - 0.001)
      expect(caja.x + caja.ancho).toBeLessThanOrEqual(MARCO.x + MARCO.ancho + 0.001)
      expect(caja.y + caja.alto).toBeLessThanOrEqual(MARCO.y + MARCO.alto + 0.001)
    }
  })

  it('ninguna caja pisa a otra', () => {
    const cajas = repartirRectangulo([40, 20, 15, 10, 6, 4, 3, 2], MARCO)
    for (let a = 0; a < cajas.length; a++) {
      for (let b = a + 1; b < cajas.length; b++) {
        expect(seSolapan(cajas[a], cajas[b])).toBe(false)
      }
    }
  })

  it('las cajas salen razonablemente cuadradas', () => {
    // El propósito del algoritmo. Con un reparto en tiras, cien bloques serían
    // cien rendijas de tres píxeles de ancho y no cabría ningún nombre.
    const valores = Array.from({ length: 60 }, (_, i) => 100 - i)
    const cajas = repartirRectangulo(valores, MARCO)
    const proporciones = cajas.map((c) => Math.max(c.ancho / c.alto, c.alto / c.ancho))
    const mediana = proporciones.sort((a, b) => a - b)[Math.floor(proporciones.length / 2)]
    expect(mediana).toBeLessThan(2.2)
  })

  it('conserva el orden de entrada', () => {
    const cajas = repartirRectangulo([5, 3, 1], MARCO)
    expect(cajas.map((c) => c.i)).toEqual([0, 1, 2])
  })

  it('lo que no es positivo no recibe caja', () => {
    // Un bloque de área cero no se puede pintar, y uno de área mínima diría
    // que ahí hay algo de dinero cuando lo que hay es un hueco.
    const cajas = repartirRectangulo([10, 0, -4, null, NaN, 5], MARCO)
    expect(cajas.map((c) => c.i)).toEqual([0, 5])
  })

  it('sin valores ni marco no revienta', () => {
    expect(repartirRectangulo([], MARCO)).toEqual([])
    expect(repartirRectangulo(null, MARCO)).toEqual([])
    expect(repartirRectangulo([1, 2], { x: 0, y: 0, ancho: 0, alto: 100 })).toEqual([])
  })
})
