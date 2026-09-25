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

const FONDO_PLACA = 'rgba(18, 19, 21, 0.84)' // --visor, casi opaco
const MARGEN_X = 4
const MARGEN_Y = 3
const RADIO = 2

/**
 * Firma de Sigma 3: `(contexto, datos, ajustes)`. `datos` trae ya las
 * coordenadas en píxeles de pantalla y el tamaño del nodo.
 *
 * `centrada` coloca el rótulo debajo del nodo y no a su derecha. En el mapa de
 * núcleos el nodo rotulado es el más gordo de su mancha, así que a la derecha
 * el nombre cae encima de la mancha vecina y parece suyo: «Consejería de
 * Presidencia» escrito sobre el borrón azul de al lado. Centrado debajo se lee
 * de quién es. En la vista de conexiones no hace falta, porque ahí los nodos
 * están sueltos y el rótulo lateral no invade a nadie.
 */
function pintar(ctx, datos, ajustes, centrada) {
  if (!datos.label) return

  ctx.font = `${ajustes.labelWeight} ${ajustes.labelSize}px ${ajustes.labelFont}`
  const ancho = ctx.measureText(datos.label).width
  const alto = ajustes.labelSize + MARGEN_Y * 2
  const x = centrada ? datos.x - ancho / 2 : datos.x + datos.size + MARGEN_X
  const y = centrada
    ? datos.y + datos.size + MARGEN_Y * 2
    : datos.y + ajustes.labelSize / 3 - alto + MARGEN_Y

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

export function dibujarEtiquetaConPlaca(ctx, datos, ajustes) {
  pintar(ctx, datos, ajustes, false)
}

export function dibujarEtiquetaCentrada(ctx, datos, ajustes) {
  pintar(ctx, datos, ajustes, true)
}
