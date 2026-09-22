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

/**
 * El realce al pasar por encima, con transición.
 *
 * Sin transición, apuntar a un nodo es un corte: todo el dibujo cambia de
 * golpe y el ojo pierde dónde estaba. Con doscientos milisegundos de fundido,
 * lo que se ve es que el vecindario SALE de la masa, y eso es lo que hace que
 * el gesto parezca una lupa y no un parpadeo.
 *
 * Esto lleva la cuenta del avance: a dónde va (1 si hay algo bajo el cursor,
 * 0 si no) y por dónde va. El dibujo lo hacen los reductores, que interpolan
 * con este número.
 */
export function realce(duracionMs = 200) {
  let destino = 0
  let valor = 0
  let quien = ''
  return {
    /** Apunta a un nodo, o a ninguno con cadena vacía. */
    apunta(id) {
      if (id) quien = id
      destino = id ? 1 : 0
    },
    /**
     * Avanza `ms` milisegundos. Devuelve `true` mientras siga moviéndose,
     * que es lo que dice si hace falta repintar.
     */
    avanza(ms) {
      if (valor === destino) return false
      const paso = Math.min(1, Math.max(0, ms) / duracionMs)
      valor += (destino - valor) * Math.min(1, paso * 3)
      if (Math.abs(destino - valor) < 0.01) valor = destino
      if (valor === 0) quien = ''
      return true
    },
    /** Cuánto realce hay ahora mismo, de 0 a 1. */
    get intensidad() {
      return valor
    },
    /** Quién lo lleva. Sigue valiendo mientras se apaga, para no cortar. */
    get id() {
      return quien
    },
    get activo() {
      return valor > 0.001
    },
  }
}

/** Interpola dos números. Para tamaños y grosores. */
export function entre(a, b, t) {
  return a + (b - a) * Math.min(1, Math.max(0, t))
}

/**
 * Una posición inicial estable para un nodo, dentro del cuadrado unidad.
 *
 * ForceAtlas2 es determinista si se le da el mismo punto de partida, pero el
 * punto de partida era `Math.random()`: la misma instantánea salía dibujada
 * distinta en cada visita —girada, del revés, con los haces hacia otro lado—.
 * Es el mismo problema que tenía el agrupamiento y por el mismo motivo: quien
 * se lleva una captura y quien abre el enlace ven dibujos distintos del mismo
 * día, y no se puede decir «el de la izquierda».
 *
 * Dos valores de la misma familia que la fase de la deriva, desfasados para
 * que no salgan todos en la diagonal.
 */
export function semillaDePosicion(id) {
  const a = faseDe(id)
  const b = faseDe(`${id}·y`)
  return { x: a / (Math.PI * 2), y: b / (Math.PI * 2) }
}

/**
 * El despliegue: de dónde arranca cada nodo a dónde acaba.
 *
 * ## Por qué no lo lleva el worker de ForceAtlas2
 *
 * `graphology-layout-forceatlas2/worker` existe, está instalado —viene con la
 * misma dependencia que se usa para colocar— y hace justo esto: correr la
 * simulación en un hilo aparte mientras el dibujo la va enseñando. Se probó y
 * se ve muy bien.
 *
 * Pero se para por RELOJ, y eso devuelve un problema que acababa de
 * arreglarse: en dos segundos, una máquina rápida hace muchas más iteraciones
 * que una lenta, así que el dibujo final vuelve a depender de dónde se mire.
 * Aquí eso importa —quien se lleva una captura y quien abre el enlace tienen
 * que ver lo mismo— y no hay manera de pedirle al supervisor «para a la
 * iteración 260».
 *
 * Así que la colocación se calcula entera y de una vez, que es determinista,
 * y lo que se anima es el VIAJE hasta ella. Sale igual de vivo, cuesta menos
 * —durante el despliegue no hay simulación, sólo interpolar— y acaba siempre
 * en el mismo sitio.
 */
export function despliegue(duracionMs = 1100) {
  let t = 0
  return {
    /** Avanza y devuelve `true` mientras queden fotogramas por dar. */
    avanza(ms) {
      if (t >= 1) return false
      t = Math.min(1, t + Math.max(0, ms) / duracionMs)
      return true
    },
    /** De golpe al final. Para quien pide menos movimiento. */
    termina() {
      t = 1
    },
    get acabado() {
      return t >= 1
    },
    /**
     * Cuánto camino se lleva hecho, suavizado.
     *
     * Cúbica de salida: arranca deprisa y frena al llegar, que es como se
     * mueve algo que se coloca. Lineal parece una cinta transportadora.
     */
    get avance() {
      return 1 - (1 - t) ** 3
    },
  }
}
