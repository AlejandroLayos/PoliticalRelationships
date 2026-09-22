import { describe, expect, it } from 'vitest'
import { aclarar, apagar, aRgb, FONDO_LIENZO, hexSobreFondo, sobreFondo } from './color.js'

describe('sobreFondo', () => {
  it('con opacidad 1 deja el color intacto', () => {
    expect(sobreFondo([255, 0, 0], 1)).toBe('rgb(255,0,0)')
  })

  it('con opacidad 0 devuelve el fondo', () => {
    expect(sobreFondo([255, 0, 0], 0)).toBe(`rgb(${FONDO_LIENZO.join(',')})`)
  })

  it('a la mitad, a la mitad de camino', () => {
    // 255 y 16 → 135 o 136 según el redondeo; basta con que esté en medio.
    const m = /rgb\((\d+),/.exec(sobreFondo([255, 0, 0], 0.5))
    expect(Number(m[1])).toBeGreaterThan(130)
    expect(Number(m[1])).toBeLessThan(140)
  })

  it('es monótono: más opacidad, más lejos del fondo', () => {
    const canal = (s) => Number(/rgb\((\d+),/.exec(s)[1])
    const valores = [0.05, 0.2, 0.5, 0.9].map((a) => canal(sobreFondo([200, 200, 200], a)))
    for (let i = 1; i < valores.length; i += 1) {
      expect(valores[i]).toBeGreaterThan(valores[i - 1])
    }
  })

  it('nunca declara alfa, que es el motivo de existir', () => {
    // Sigma ignora el alfa de las aristas: si esto volviera a emitir `rgba`,
    // la atenuación dejaría de verse y no lo diría ningún test.
    expect(sobreFondo([1, 2, 3], 0.3)).not.toContain('rgba')
    expect(hexSobreFondo('#3987e5', 0.3)).not.toContain('rgba')
  })
})

describe('aRgb', () => {
  it('lee un hexadecimal con y sin almohadilla', () => {
    expect(aRgb('#3987e5')).toEqual([0x39, 0x87, 0xe5])
    expect(aRgb('3987e5')).toEqual([0x39, 0x87, 0xe5])
  })

  it('lo que no es un hexadecimal de seis no lo es', () => {
    expect(aRgb('rgb(1,2,3)')).toBe(null)
    expect(aRgb('#abc')).toBe(null)
    expect(aRgb(null)).toBe(null)
  })
})

describe('aclarar y apagar', () => {
  it('aclarar del todo es blanco; apagar del todo es el fondo', () => {
    expect(aclarar('#3987e5', 1)).toBe('rgb(255,255,255)')
    expect(apagar('#3987e5', 1)).toBe(`rgb(${FONDO_LIENZO.join(',')})`)
  })

  it('sin mezcla, el color de partida', () => {
    expect(aclarar('#3987e5', 0)).toBe('rgb(57,135,229)')
  })

  it('lo que no es hexadecimal se devuelve tal cual', () => {
    expect(aclarar('rgb(1,2,3)', 0.5)).toBe('rgb(1,2,3)')
  })
})
