import { describe, expect, it } from 'vitest'
import { repartirConResto, repartirRectangulo } from './rectangulos.js'

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

describe('repartirConResto', () => {
  const marco = { x: 0, y: 0, ancho: 900, alto: 600 }
  /** Cien grupos con una cola larguísima, como los de verdad. */
  const muchos = Array.from({ length: 100 }, (_, i) => 1000 / (i + 1) ** 1.6)

  it('todo lo que se dibuja tiene tamaño para llevar su nombre', () => {
    const { cajas } = repartirConResto(muchos, marco, { minAncho: 86, minAlto: 40 })
    for (const c of cajas) {
      expect(c.ancho).toBeGreaterThanOrEqual(86)
      expect(c.alto).toBeGreaterThanOrEqual(40)
    }
  })

  it('el mínimo va por ancho y alto, no por lado menor', () => {
    // Un rótulo no es cuadrado: 45x120 tiene sitio por abajo y ninguno por
    // los lados. Con un solo número, la mitad de los bloques pasaban el corte
    // y salían igualmente mudos.
    const parejos = Array.from({ length: 30 }, (_, i) => 100 - i * 2)
    const marcoAncho = { x: 0, y: 0, ancho: 1200, alto: 300 }
    const { cajas, resto } = repartirConResto(parejos, marcoAncho, { minAncho: 100, minAlto: 30 })
    expect(resto).not.toBe(null)
    for (const c of cajas) expect(c.ancho).toBeGreaterThanOrEqual(100)
    // Y con el criterio de «lado menor» a 30 no se habría juntado nada, que
    // es el fallo: bloques estrechos y altos pasaban el corte y salían mudos.
    const porLadoMenor = repartirConResto(parejos, marcoAncho, { minAncho: 30, minAlto: 30 })
    expect(porLadoMenor.cajas.some((c) => c.ancho < 100)).toBe(true)
  })

  it('dice cuántos ha juntado y cuánto suman', () => {
    const { resto } = repartirConResto(muchos, marco, { minAncho: 86, minAlto: 40 })
    expect(resto.cuantos).toBeGreaterThan(0)
    expect(resto.desde + resto.cuantos).toBe(100)
    expect(resto.valor).toBeCloseTo(muchos.slice(resto.desde).reduce((s, v) => s + v, 0), 6)
  })

  it('el área sigue siendo exacta: el resto mide lo que miden todos juntos', () => {
    // Quitar la cola sin más haría que el dibujo afirmara que ese dinero no
    // existe. Juntarla conserva la proporción.
    const { cajas, resto } = repartirConResto(muchos, marco, { minAncho: 86, minAlto: 40 })
    const total = muchos.reduce((s, v) => s + v, 0)
    const superficie = marco.ancho * marco.alto
    const ultima = cajas[cajas.length - 1]
    expect(ultima.ancho * ultima.alto).toBeCloseTo((resto.valor / total) * superficie, 2)
  })

  it('en un lienzo pequeño junta más, y sigue cumpliendo el mínimo', () => {
    const grande = repartirConResto(muchos, marco, { minAncho: 86, minAlto: 40 })
    const movil = repartirConResto(muchos, { x: 0, y: 0, ancho: 360, alto: 420 }, { minAncho: 86, minAlto: 40 })
    expect(movil.resto.cuantos).toBeGreaterThan(grande.resto.cuantos)
    for (const c of movil.cajas) expect(Math.min(c.ancho, c.alto)).toBeGreaterThanOrEqual(26)
  })

  it('si todo cabe, no inventa un resto', () => {
    const { cajas, resto } = repartirConResto([50, 30, 20], marco, { minAncho: 86, minAlto: 40 })
    expect(resto).toBe(null)
    expect(cajas).toHaveLength(3)
  })

  it('nunca baja de un mínimo de bloques, aunque no quepan', () => {
    // Con un lienzo diminuto, juntarlo todo en uno dejaría un rectángulo sin
    // información. Antes de eso, se aceptan bloques pequeños.
    const { cajas } = repartirConResto(muchos, { x: 0, y: 0, ancho: 60, alto: 40 }, { minAncho: 86, minAlto: 40, minimos: 6 })
    expect(cajas.length).toBeGreaterThanOrEqual(6)
  })

  it('sin valores no revienta', () => {
    expect(repartirConResto([], marco)).toEqual({ cajas: [], resto: null })
    expect(repartirConResto(null, marco)).toEqual({ cajas: [], resto: null })
  })
})
