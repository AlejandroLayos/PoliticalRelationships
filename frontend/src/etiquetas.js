/**
 * Etiquetas de nodo con placa, para los dos grafos.
 *
 * Sigma dibuja el texto a pelo sobre el lienzo. Sobre un fondo oscuro y vacío
 * se lee; encima de una mancha de color claro —verde, amarillo, turquesa— o de
 * otra etiqueta, no. Y en la vista de conexiones, donde un organismo con
 * treinta vecinos deja treinta nombres largos apiñados alrededor, el resultado
 * era una mancha de letras superpuestas: «AYUNTAMIENTO DE SANTANDER» encima de
 * «DIPUTACIÓN PROVINCIAL DE LUGO» encima de «D.G. DE POLÍTICA INTERIOR».
 *
 * Con una placa detrás, cada nombre se lee siempre, sobre lo que sea. No
 * resuelve el solape —eso lo decide la rejilla de Sigma— pero sí que el de
 * arriba sea legible en vez de quedar los dos ilegibles.
 */

const FONDO_PLACA = 'rgba(9, 13, 19, 0.82)'
const MARGEN_X = 4
const MARGEN_Y = 3
const RADIO = 4

/**
 * Firma de Sigma 3: `(contexto, datos, ajustes)`. `datos` trae ya las
 * coordenadas en píxeles de pantalla y el tamaño del nodo.
 */
export function dibujarEtiquetaConPlaca(ctx, datos, ajustes) {
  if (!datos.label) return

  ctx.font = `${ajustes.labelWeight} ${ajustes.labelSize}px ${ajustes.labelFont}`
  const ancho = ctx.measureText(datos.label).width
  const alto = ajustes.labelSize + MARGEN_Y * 2
  const x = datos.x + datos.size + MARGEN_X
  const y = datos.y + ajustes.labelSize / 3 - alto + MARGEN_Y

  ctx.beginPath()
  ctx.moveTo(x - MARGEN_X + RADIO, y)
  ctx.arcTo(x + ancho + MARGEN_X, y, x + ancho + MARGEN_X, y + alto, RADIO)
  ctx.arcTo(x + ancho + MARGEN_X, y + alto, x - MARGEN_X, y + alto, RADIO)
  ctx.arcTo(x - MARGEN_X, y + alto, x - MARGEN_X, y, RADIO)
  ctx.arcTo(x - MARGEN_X, y, x + ancho + MARGEN_X, y, RADIO)
  ctx.closePath()
  ctx.fillStyle = FONDO_PLACA
  ctx.fill()

  ctx.fillStyle = ajustes.labelColor.color
  ctx.fillText(datos.label, x, y + alto - MARGEN_Y - 1)
}
