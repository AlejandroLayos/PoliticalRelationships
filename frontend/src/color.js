/**
 * Colores opacos que parecen translúcidos.
 *
 * ## Por qué existe esto
 *
 * **El programa de aristas de Sigma ignora el canal alfa.** Una arista
 * declarada `rgba(255,0,0,0.05)` se dibuja exactamente igual que
 * `rgba(255,0,0,1)`: rojo a saco. Se comprobó pintando de rojo transparente
 * todas las aristas de un grupo y viendo salir una maraña roja opaca.
 *
 * Eso convierte en inútil cualquier ajuste de opacidad sobre las aristas, y
 * aquí se habían hecho varios —bajar la telaraña de 0,18 a 0,11 y luego a
 * 0,05 para que dejara ver los nodos— que no hicieron absolutamente nada. La
 * maraña blanca que tapaba el dibujo seguía ahí porque no había manera de
 * atenuarla por ese camino.
 *
 * Como el lienzo es de un color liso, hay un camino que sí funciona: calcular
 * el color que RESULTARÍA de pintar ese translúcido sobre el fondo, y
 * declararlo opaco. Se ve idéntico y no depende de que nadie respete el alfa.
 */

/** El fondo del lienzo del grafo, en las tres componentes. */
export const FONDO_LIENZO = [0x10, 0x10, 0x12]

/**
 * El color opaco equivalente a pintar `[r,g,b]` con opacidad `alfa` sobre el
 * fondo del lienzo.
 *
 * @param {[number, number, number]} rgb
 * @param {number} alfa entre 0 y 1.
 * @param {[number, number, number]} fondo sobre qué se pinta.
 */
export function sobreFondo(rgb, alfa, fondo = FONDO_LIENZO) {
  const a = Math.min(1, Math.max(0, alfa))
  const c = rgb.map((canal, i) => Math.round(fondo[i] + (canal - fondo[i]) * a))
  return `rgb(${c[0]},${c[1]},${c[2]})`
}

/** Lo mismo, partiendo de un `#rrggbb`. Si no lo es, lo devuelve tal cual. */
export function hexSobreFondo(hex, alfa, fondo = FONDO_LIENZO) {
  const rgb = aRgb(hex)
  return rgb ? sobreFondo(rgb, alfa, fondo) : hex
}

/**
 * Un color a `[r,g,b]`, o `null` si no se sabe leer.
 *
 * Entiende `#rrggbb` y `rgb(r,g,b)`, y esto último no es un capricho: lo que
 * sale de `sobreFondo` es `rgb(...)`, así que en cuanto una arista ya
 * atenuada pasaba por `aclarar` para realzarla, se devolvía sin tocar y el
 * realce no se veía. El realce trabaja siempre sobre colores ya calculados.
 */
export function aRgb(color) {
  const hex = /^#?([0-9a-f]{6})$/i.exec(color ?? '')
  if (hex) {
    const v = Number.parseInt(hex[1], 16)
    return [(v >> 16) & 255, (v >> 8) & 255, v & 255]
  }
  const fn = /^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i.exec(color ?? '')
  if (fn) return [Number(fn[1]), Number(fn[2]), Number(fn[3])]
  return null
}

/** Mezcla un `#rrggbb` con un color, `k` de 0 a 1. Devuelve `rgb(...)`. */
export function mezclar(hex, k, hacia) {
  const rgb = aRgb(hex)
  if (!rgb) return hex
  const c = rgb.map((canal, i) => Math.round(canal + (hacia[i] - canal) * k))
  return `rgb(${c[0]},${c[1]},${c[2]})`
}

export const BLANCO = [255, 255, 255]

/** Aclara hacia el blanco. Lo que está bajo el cursor. */
export const aclarar = (hex, k) => mezclar(hex, k, BLANCO)

/** Apaga hacia el fondo: aleja en vez de ensuciar. */
export const apagar = (hex, k) => mezclar(hex, k, FONDO_LIENZO)
