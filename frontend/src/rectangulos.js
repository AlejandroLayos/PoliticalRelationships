/**
 * Reparto de un rectángulo en proporción a una lista de números.
 *
 * Es el algoritmo *squarified treemap* de Bruls, Huizing y van Wijk (2000):
 * va metiendo valores en una fila mientras eso mejore la proporción de las
 * cajas, y cuando deja de mejorar cierra la fila y sigue con lo que queda del
 * rectángulo.
 *
 * ## Por qué esto y no un grafo
 *
 * El mapa dibujaba los 2.428 nodos de la instantánea como puntos con muelles.
 * Un diagrama de nodos se lee hasta unos cien; con dos mil es una mancha, y
 * con dos mil y medio, una mancha con manchas dentro. Da igual cuánto se
 * afinen los tamaños y las opacidades: lo que hay en pantalla no se puede
 * leer porque hay demasiado.
 *
 * Quien entra aquí no quiere ver la red: quiere saber dónde se concentra el
 * dinero público y meterse en un sitio concreto. Eso son cien bloques, no dos
 * mil puntos, y un bloque cabe con su nombre escrito dentro.
 *
 * El área es el dato: un bloque el doble de grande es el doble de dinero. Sin
 * raíces ni escalas comprimidas — aquí no hace falta, porque no hay que
 * distinguir un punto de tres píxeles de otro de dos.
 */

/**
 * La peor proporción alto/ancho de una fila de áreas.
 *
 * @param {number[]} fila áreas de la fila.
 * @param {number} lado el lado corto del rectángulo que queda.
 */
function peorProporcion(fila, lado) {
  const suma = fila.reduce((s, a) => s + a, 0)
  if (suma <= 0 || lado <= 0) return Infinity
  const mayor = Math.max(...fila)
  const menor = Math.min(...fila)
  if (menor <= 0) return Infinity
  const l2 = lado * lado
  const s2 = suma * suma
  return Math.max((l2 * mayor) / s2, s2 / (l2 * menor))
}

/** Coloca una fila cerrada y devuelve lo que queda del rectángulo. */
function colocarFila(fila, marco) {
  const suma = fila.reduce((s, x) => s + x.area, 0)
  const cajas = []
  // La fila se tiende a lo largo del lado CORTO: es lo que mantiene las cajas
  // cuadradas, que es todo el propósito del algoritmo.
  if (marco.ancho <= marco.alto) {
    const alto = suma / marco.ancho
    let x = marco.x
    for (const item of fila) {
      const ancho = item.area / alto
      cajas.push({ i: item.i, x, y: marco.y, ancho, alto })
      x += ancho
    }
    return {
      cajas,
      resto: { x: marco.x, y: marco.y + alto, ancho: marco.ancho, alto: marco.alto - alto },
    }
  }
  const ancho = suma / marco.alto
  let y = marco.y
  for (const item of fila) {
    const alto = item.area / ancho
    cajas.push({ i: item.i, x: marco.x, y, ancho, alto })
    y += alto
  }
  return {
    cajas,
    resto: { x: marco.x + ancho, y: marco.y, ancho: marco.ancho - ancho, alto: marco.alto },
  }
}

/**
 * Reparte `marco` entre `valores`, en el orden dado.
 *
 * Devuelve una caja por valor, en el MISMO orden que entraron, con `i` como
 * índice de origen. Los valores que no son positivos no reciben caja: un
 * bloque de área cero no se puede pintar y uno de área mínima mentiría.
 *
 * @param {number[]} valores
 * @param {{x: number, y: number, ancho: number, alto: number}} marco
 */
export function repartirRectangulo(valores, marco) {
  const utiles = (valores ?? [])
    .map((v, i) => ({ i, v: Number(v) }))
    .filter((x) => Number.isFinite(x.v) && x.v > 0)
  if (!utiles.length || !marco || marco.ancho <= 0 || marco.alto <= 0) return []

  const total = utiles.reduce((s, x) => s + x.v, 0)
  const superficie = marco.ancho * marco.alto
  const items = utiles.map((x) => ({ i: x.i, area: (x.v / total) * superficie }))

  const salida = []
  let resto = { ...marco }
  let fila = []

  for (const item of items) {
    const lado = Math.min(resto.ancho, resto.alto)
    const areas = fila.map((f) => f.area)
    if (fila.length && peorProporcion(areas, lado) <= peorProporcion([...areas, item.area], lado)) {
      const { cajas, resto: queda } = colocarFila(fila, resto)
      salida.push(...cajas)
      resto = queda
      fila = []
    }
    fila.push(item)
  }
  if (fila.length) salida.push(...colocarFila(fila, resto).cajas)

  return salida.sort((a, b) => a.i - b.i)
}

/**
 * Como `repartirRectangulo`, pero junta la cola en un bloque «y N más».
 *
 * Un treemap de cien bloques termina en una esquina de rectángulos de seis
 * píxeles: no caben ni el nombre ni la cifra, así que son cajas negras que no
 * dicen nada y encima se pueden pulsar sin querer. Y no se pueden quitar sin
 * más, porque entonces el dibujo afirmaría que ese dinero no existe.
 *
 * Se juntan en uno solo, rotulado con cuántos son y cuánto suman. El área
 * sigue siendo exacta: el bloque del resto mide lo que miden todos juntos.
 *
 * El corte no es por número de bloques sino por TAMAÑO DIBUJADO, que es lo
 * que decide si cabe un nombre, y depende del lienzo: en una pantalla ancha
 * caben cuarenta y en un teléfono, ocho.
 *
 * El mínimo va por ancho y alto por separado, y no por «lado menor», porque
 * un rótulo no es cuadrado: un bloque de 45x120 tiene sitio de sobra por
 * abajo y ninguno por los lados. Con un solo número, la mitad de los bloques
 * pasaban el corte y salían igualmente mudos.
 *
 * @param {number[]} valores de mayor a menor.
 * @param {{x,y,ancho,alto}} marco
 * @param {{minAncho?: number, minAlto?: number, minimos?: number}} opciones
 * @returns {{cajas: Array, resto: {desde: number, cuantos: number, valor: number}|null}}
 */
export function repartirConResto(valores, marco, { minAncho = 86, minAlto = 40, minimos = 6 } = {}) {
  const lista = (valores ?? []).map(Number).filter((v) => Number.isFinite(v) && v > 0)
  if (!lista.length) return { cajas: [], resto: null }

  const pequena = (c) => c.ancho < minAncho || c.alto < minAlto
  let corte = lista.length
  let cajas = repartirRectangulo(lista, marco)

  // De uno en uno desde el final: cada vuelta recoloca, así que no vale
  // predecir cuántos sobran — hay que volver a mirar.
  while (corte > minimos && cajas.some(pequena)) {
    corte -= 1
    const cola = lista.slice(corte)
    const suma = cola.reduce((s, v) => s + v, 0)
    cajas = repartirRectangulo([...lista.slice(0, corte), suma], marco)
  }

  if (corte === lista.length) return { cajas, resto: null }
  return {
    cajas,
    resto: {
      desde: corte,
      cuantos: lista.length - corte,
      valor: lista.slice(corte).reduce((s, v) => s + v, 0),
    },
  }
}
