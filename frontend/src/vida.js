/**
 * Lo que hace que un grafo parezca vivo.
 *
 * Un grafo de fuerzas quieto es la foto de un proceso: se ve el resultado y no
 * se ve que los nodos se empujan, que es de donde sale la forma. Aquí hay dos
 * cosas, y las dos son cálculo puro para poder probarlas sin navegador:
 *
 * - **La deriva.** Cada nodo respira alrededor de su punto de reposo, muy
 *   poco y a su propio ritmo. Los gordos se mueven menos: un punto grande es
 *   un organismo con mucho dinero alrededor, y que pese se nota. Sin eso todo
 *   flota igual y parece un salvapantallas.
 * - **La cercanía al cursor.** Devuelve cuánto le toca a un punto del foco del
 *   ratón, con caída suave para que el borde del halo no se vea.
 *
 * El bucle de fotogramas se queda en el componente: eso es Sigma y el
 * navegador, y no hay nada que probar ahí.
 */

/**
 * Una fase estable por nodo, sacada de su identificador.
 *
 * Con `Math.random()` cada carga daría una respiración distinta. No cambia
 * ningún dato, pero el agrupamiento se hizo determinista por una razón y no
 * hay motivo para meter azar donde no hace falta.
 */
export function faseDe(id) {
  let h = 2166136261
  const texto = String(id ?? '')
  for (let i = 0; i < texto.length; i += 1) {
    h ^= texto.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return ((h >>> 0) % 6283) / 1000
}

/**
 * Puntos de reposo, amplitudes y radio del foco para un conjunto de nodos.
 *
 * @param {Array<{id: string, x: number, y: number, size: number}>} nodos
 * @returns {{reposo: Map, radio: number, diagonal: number}}
 */
export function puntosDeReposo(nodos) {
  const reposo = new Map()
  if (!nodos?.length) return { reposo, radio: 0, diagonal: 0 }

  let minX = Infinity
  let maxX = -Infinity
  let minY = Infinity
  let maxY = -Infinity
  for (const n of nodos) {
    if (n.x < minX) minX = n.x
    if (n.x > maxX) maxX = n.x
    if (n.y < minY) minY = n.y
    if (n.y > maxY) maxY = n.y
  }
  const diagonal = Math.hypot(maxX - minX, maxY - minY) || 1

  for (const n of nodos) {
    reposo.set(n.id, {
      x: n.x,
      y: n.y,
      fase: faseDe(n.id),
      amplitud: (diagonal * 0.0045 * 14) / (8 + (n.size ?? 1)),
    })
  }
  return { reposo, radio: diagonal * 0.12, diagonal }
}

/**
 * Dónde está un nodo en el instante `t` (segundos desde que empezó la deriva).
 *
 * Dos senos de periodo distinto para que no se note el ciclo: con uno solo,
 * el dibujo entero late a la vez y parece un corazón.
 */
export function posicionEnDeriva(base, t) {
  return {
    x: base.x + Math.sin(t * 0.42 + base.fase) * base.amplitud,
    y: base.y + Math.cos(t * 0.31 + base.fase * 1.7) * base.amplitud,
  }
}

/**
 * Cuánto le toca a un punto del foco del cursor: 1 en el centro, 0 fuera.
 *
 * Coseno alzado y no lineal: así el borde del halo no se ve, que es lo que lo
 * hace parecer una luz y no un círculo recortado.
 */
export function cercania(x, y, raton, radio) {
  if (!raton || !radio) return 0
  const d = Math.hypot(x - raton.x, y - raton.y)
  if (d >= radio) return 0
  return (1 + Math.cos((d / radio) * Math.PI)) / 2
}

/**
 * ¿Aguanta esta máquina la animación?
 *
 * Se mide lo que se nota, que es la FLUIDEZ: cuánto tarda un fotograma en
 * llegar al siguiente. Medir lo que cuesta `refresh()` no sirve —se probó y
 * daba 1,8 ms mientras la página iba a 19 imágenes por segundo—, porque
 * `refresh()` sólo prepara búferes y devuelve: lo caro es pintarlos, y eso
 * pasa después y no se puede cronometrar desde aquí. El intervalo entre
 * fotogramas sí lo recoge todo, incluido lo que tarda la GPU.
 *
 * Con GPU, animar un grafo de doscientos nodos no se nota. Por software —o en
 * un teléfono viejo— la página pasa de 60 imágenes por segundo a 19 y se
 * vuelve pegajosa: ahí vale más el dibujo quieto, que sigue respondiendo al
 * cursor.
 *
 * Una vez que decide que no, no vuelve a decir que sí hasta que se redibuje
 * todo. Si volviera a intentarlo, apagar subiría la fluidez, la fluidez
 * encendería la animación otra vez y el dibujo daría tirones cada segundo.
 */
export function medidorDeFluidez(minimoPorSegundo = 24, calentamiento = 20) {
  const limite = 1000 / minimoPorSegundo
  let anterior = 0
  let media = 0
  let vistos = 0
  let rendido = false
  return {
    /** Anota el instante de un fotograma animado. */
    anota(ahora) {
      if (anterior) {
        const hueco = ahora - anterior
        // Un hueco enorme es la pestaña volviendo del fondo, no lentitud.
        if (hueco < 500) {
          vistos += 1
          media = vistos === 1 ? hueco : media * 0.9 + hueco * 0.1
          if (vistos > calentamiento && media > limite) rendido = true
        }
      }
      anterior = ahora
    },
    get viable() {
      return !rendido
    },
    get media() {
      return media
    },
  }
}
