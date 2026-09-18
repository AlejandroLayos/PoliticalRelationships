/**
 * Disposición del diagrama de flujo de dinero.
 *
 * La pregunta que contesta esta vista es literal: «de quién le entra y a quién
 * le sale». Un grafo de fuerzas no la contesta — sobre una entidad con treinta
 * vecinos sale siempre una estrella, y en una estrella todos los radios se ven
 * igual, así que no se distingue a quien paga de quien cobra ni al que mueve un
 * millón del que mueve mil euros.
 *
 * Tres columnas sí la contestan: pagadores a la izquierda, la entidad en medio,
 * beneficiarios a la derecha. La posición ya dice el papel de cada uno antes de
 * leer ni una etiqueta.
 *
 * ## Por qué el grosor va por raíz cuadrada y no proporcional
 *
 * El reparto del dinero público es brutalmente desigual: en los datos reales el
 * mayor adjudicatario de un organismo se lleva órdenes de magnitud más que la
 * mediana. Con grosores proporcionales, el primero ocupa la pantalla entera y
 * los demás se convierten en líneas de un píxel — es decir, la vista deja de
 * mostrar que existen. La raíz cuadrada conserva el orden y la diferencia se
 * sigue viendo de un vistazo, pero nadie desaparece.
 *
 * Como eso deforma la proporción, **la cifra exacta va escrita en cada banda**.
 * El dibujo ordena; el número es el dato.
 */

import { aNumero } from './nucleos.js'

const MARGEN = 14
const ALTO_MIN_FICHA = 26
// Una ficha es una etiqueta con una cifra: pasado cierto alto no comunica más,
// sólo ocupa. Sin tope, una entidad con tres contrapartes salía con tres
// bloques del tamaño de media pantalla y la banda de color se comía la vista.
// El sobrante se queda en blanco, que es lo que debe hacer el espacio vacío.
const ALTO_MAX_FICHA = 68
const HUECO = 6
const CABECERA = 30
// Banda inferior reservada para el «+N más». Sin ella se pintaba encima de la
// última ficha y de la ayuda de la esquina: tres textos superpuestos.
//
// En pantallas estrechas hace falta más, porque la leyenda pasa de una línea a
// tres y se comía la última ficha. Por eso es un parámetro.
const PIE = 22

function ancla(valor, min, max) {
  return Math.max(min, Math.min(max, valor))
}

/**
 * Reparte el alto disponible entre las contrapartes.
 *
 * Todas reciben un mínimo legible; el resto se reparte por raíz del importe.
 * Si no cabe ni el mínimo para todas, se reparte a partes iguales: más vale
 * una lista apretada que una banda de cero píxeles.
 */
export function repartirAlto(valores, disponible) {
  const n = valores.length
  if (!n) return []
  const libre = disponible - HUECO * (n - 1)
  if (libre <= 0) return valores.map(() => 0)
  if (n * ALTO_MIN_FICHA >= libre) return valores.map(() => libre / n)

  const pesos = valores.map((v) => Math.sqrt(Math.max(0, aNumero(v))))
  const suma = pesos.reduce((s, p) => s + p, 0)
  const extra = libre - n * ALTO_MIN_FICHA
  if (suma <= 0) return valores.map(() => Math.min(ALTO_MAX_FICHA, libre / n))
  return pesos.map((p) => Math.min(ALTO_MAX_FICHA, ALTO_MIN_FICHA + (extra * p) / suma))
}

function apilar(altos, desde) {
  let y = desde
  return altos.map((h) => {
    const caja = { y, h }
    y += h + HUECO
    return caja
  })
}

/** Una cinta de la ficha hasta el borde del centro (o al revés). */
function cinta(x1, y1a, y1b, x2, y2a, y2b) {
  const cx = (x1 + x2) / 2
  return [
    `M ${x1} ${y1a}`,
    `C ${cx} ${y1a} ${cx} ${y2a} ${x2} ${y2a}`,
    `L ${x2} ${y2b}`,
    `C ${cx} ${y2b} ${cx} ${y1b} ${x1} ${y1b}`,
    'Z',
  ].join(' ')
}

/**
 * Calcula la geometría completa del diagrama.
 *
 * `area` es lo que devuelve `areaDeInfluencia`. Devuelve cajas y rutas SVG ya
 * resueltas: el componente sólo pinta, no decide.
 */
export function disponerFlujo(area, { ancho, alto, maxPorLado = 12, pie = PIE } = {}) {
  const vacio = { centro: null, izquierda: [], derecha: [], cintas: [], recortado: { izquierda: 0, derecha: 0 } }
  if (!area?.entidad || !ancho || !alto) return vacio

  const anchoColumna = ancla(ancho * 0.27, 130, 270)
  const anchoCentro = ancla(ancho * 0.22, 150, 260)
  const xIzq = MARGEN
  const xDer = ancho - MARGEN - anchoColumna

  const arriba = CABECERA
  const abajo = alto - MARGEN - pie
  const util = abajo - arriba

  const izq = area.recibeDe.slice(0, maxPorLado)
  const der = area.pagaA.slice(0, maxPorLado)

  const altosIzq = repartirAlto(izq.map((x) => x.total), util)
  const altosDer = repartirAlto(der.map((x) => x.total), util)

  // Cada columna se centra verticalmente sobre lo que ocupa de verdad, para
  // que una entidad con dos pagadores y quince receptores no salga descuadrada.
  function inicio(altos) {
    const ocupa = altos.reduce((s, h) => s + h, 0) + HUECO * Math.max(0, altos.length - 1)
    return arriba + Math.max(0, (util - ocupa) / 2)
  }

  const cajasIzq = apilar(altosIzq, inicio(altosIzq))
  const cajasDer = apilar(altosDer, inicio(altosDer))

  // Con un lado vacío —pasa constantemente: un organismo que sólo adjudica, o
  // un partido del que sólo consta una sanción— centrar la entidad deja media
  // pantalla en blanco y el dibujo parece roto. Se desplaza hacia el lado
  // hueco, y las cintas cruzan el ancho entero.
  let xCen = (ancho - anchoCentro) / 2
  if (!izq.length && der.length) xCen = MARGEN + anchoColumna * 0.2
  else if (izq.length && !der.length) xCen = ancho - MARGEN - anchoCentro - anchoColumna * 0.2

  const altoCentro = ancla(util * 0.42, 110, 220)
  const yCentro = arriba + (util - altoCentro) / 2
  const centro = {
    id: area.entidad.id,
    caption: area.entidad.caption,
    schema: area.entidad.schema,
    x: xCen,
    y: yCentro,
    w: anchoCentro,
    h: altoCentro,
  }

  const fichas = (lista, cajas, x, lado) =>
    lista.map((c, i) => ({ ...c, lado, x, w: anchoColumna, y: cajas[i].y, h: cajas[i].h }))

  const izquierda = fichas(izq, cajasIzq, xIzq, 'izquierda')
  const derecha = fichas(der, cajasDer, xDer, 'derecha')

  // En el centro las cintas se apilan repartiéndose el borde, como en un
  // Sankey: el ancho del borde es el mismo para los dos lados, así que se ve
  // al instante si entra más de lo que sale.
  const margenBorde = 8
  const bordeUtil = altoCentro - margenBorde * 2

  function convergencia(items) {
    const suma = items.reduce((s, c) => s + c.h, 0)
    let y = yCentro + margenBorde
    return items.map((c) => {
      const h = suma > 0 ? (c.h / suma) * bordeUtil : 0
      const caja = { a: y, b: y + h }
      y += h
      return caja
    })
  }

  const convIzq = convergencia(izquierda)
  const convDer = convergencia(derecha)

  const cintas = [
    ...izquierda.map((c, i) => ({
      id: `in:${c.id}`,
      nodoId: c.id,
      lado: 'izquierda',
      total: c.total,
      extranjera: c.extranjera,
      inferido: c.inferido,
      d: cinta(c.x + c.w, c.y, c.y + c.h, centro.x, convIzq[i].a, convIzq[i].b),
    })),
    ...derecha.map((c, i) => ({
      id: `out:${c.id}`,
      nodoId: c.id,
      lado: 'derecha',
      total: c.total,
      extranjera: c.extranjera,
      inferido: c.inferido,
      d: cinta(c.x, c.y, c.y + c.h, centro.x + centro.w, convDer[i].a, convDer[i].b),
    })),
  ]

  return {
    centro,
    izquierda,
    derecha,
    cintas,
    recortado: {
      izquierda: area.recibeDe.length - izq.length,
      derecha: area.pagaA.length - der.length,
    },
  }
}
