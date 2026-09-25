/**
 * El mapa del dinero como círculos que contienen a su gente.
 *
 * ## Por qué círculos anidados
 *
 * El mapa eran dos vistas pegadas: unos bloques estáticos —un rectángulo por
 * grupo— y, al pulsar uno, un salto a otra pantalla con un diagrama de nodos.
 * Entre las dos no había continuidad: se perdía de dónde se venía, y los
 * bloques no enseñaban nada de lo que había dentro.
 *
 * Aquí es un solo dibujo. Cada grupo es un círculo, y dentro están sus
 * organismos y empresas, cada uno del color de su tipo y del tamaño de su
 * dinero. Desde fuera se ve ya de qué está hecho cada grupo —un organismo con
 * su nube de proveedores, o una red de administraciones que se pagan entre
 * sí—; al pulsar, la cámara entra en el círculo y los de dentro se nombran.
 *
 * El área es el dato en los dos niveles. El valor de una entidad es el dinero
 * de sus relaciones DENTRO del grupo; como cada relación cuenta en sus dos
 * extremos, el área de un grupo es proporcional al dinero que se mueve dentro
 * de él, que es la cifra que lleva escrita.
 *
 * Aquí sólo hay cálculo, sin DOM: se prueba aparte (`mapa.test.js`) y el
 * componente `MapaCirculos.vue` sólo pinta.
 */
import { pack, packSiblings, hierarchy } from 'd3-hierarchy'
import { analizarNucleos, colapsarNodosDePaso, conEstructura, aNumero } from './nucleos.js'

/**
 * El análisis de grupos con los filtros del mapa aplicados.
 *
 * Los filtros quitan entidades ANTES de contar, no después: «sólo partidos»
 * no puede enseñar grupos calculados sobre entidades que no están en
 * pantalla. Los grupos en sí se detectan sobre el grafo entero, para que un
 * filtro no los rehaga y el grupo 03 siga siendo el 03.
 */
export function analizarMapa(
  datos,
  { minImporte = 0, mostrarExpedientes = false, soloExtranjero = false, soloPartidos = false } = {},
) {
  const fuente = mostrarExpedientes ? datos : colapsarNodosDePaso(datos)
  const { grafo, nucleos } = analizarNucleos(fuente)
  const porId = new Map((fuente?.nodes ?? []).map((n) => [n.id, n]))

  const fuera = new Set()
  grafo.forEachNode((id, attrs) => {
    if (minImporte > 0 && attrs.dinero < minImporte) fuera.add(id)
    const n = porId.get(id)
    if (soloExtranjero && !n?.properties?.entidad_extranjera) fuera.add(id)
    if (soloPartidos && attrs.esquema !== 'Organization') fuera.add(id)
  })

  const vivos = new Map()
  grafo.forEachNode((id, a) => {
    if (fuera.has(id)) return
    const c = a.nucleo ?? -1
    if (!vivos.has(c)) vivos.set(c, new Set())
    vivos.get(c).add(id)
  })

  // El dinero de cada grupo, el de cada entidad dentro de su grupo, y el
  // total en pantalla.
  const dineroGrupo = new Map()
  const interno = new Map()
  let total = 0
  grafo.forEachEdge((_e, attrs, s, t) => {
    if (fuera.has(s) || fuera.has(t)) return
    total += attrs.importe
    const cs = grafo.getNodeAttribute(s, 'nucleo')
    if (cs !== grafo.getNodeAttribute(t, 'nucleo')) return
    dineroGrupo.set(cs, (dineroGrupo.get(cs) ?? 0) + attrs.importe)
    interno.set(s, (interno.get(s) ?? 0) + attrs.importe)
    interno.set(t, (interno.get(t) ?? 0) + attrs.importe)
  })

  /*
    Los pagos, con su DIRECCIÓN, sacados de las aristas originales y no del
    grafo de grupos, que es no dirigido: dos relaciones de sentido contrario
    entre los mismos dos se funden allí en una, y decir «paga a» sobre esa
    fusión sería inventarse el sentido de una de ellas.
  */
  const pagos = new Map()
  for (const a of fuente?.edges ?? []) {
    const { source: s, target: t } = a
    if (!grafo.hasNode(s) || !grafo.hasNode(t) || s === t) continue
    if (fuera.has(s) || fuera.has(t)) continue
    if (grafo.getNodeAttribute(s, 'nucleo') !== grafo.getNodeAttribute(t, 'nucleo')) continue
    const clave = `${s}|${t}`
    const p = pagos.get(clave) ?? { de: s, a: t, importe: 0, n: 0 }
    p.importe += aNumero(a.amount)
    p.n += 1
    pagos.set(clave, p)
  }

  const visibles = nucleos
    .map((n) => {
      const ids = vivos.get(n.id)
      if (!ids) return null
      const tipos = {}
      for (const id of ids) {
        const e = grafo.getNodeAttribute(id, 'esquema')
        tipos[e] = (tipos[e] ?? 0) + 1
      }
      return {
        ...n,
        tamano: ids.size,
        dinero: dineroGrupo.get(n.id) ?? 0,
        principales: n.principales.filter((m) => ids.has(m.id)),
        tipos,
        miembros: [...ids],
      }
    })
    .filter((n) => n && n.tamano > 1)
    .sort((a, b) => b.dinero - a.dinero || b.tamano - a.tamano)

  const entidades = [...vivos.values()].reduce((s, v) => s + v.size, 0)
  return { grafo, porId, nucleos: visibles, totalDinero: total, entidades, interno, pagos }
}

/**
 * Los grupos que se dibujan, con su número de puesto.
 *
 * El número es el de la lista de al lado —el mismo orden, el del dinero—:
 * el círculo 03 es la fila 03. Con `conPequenos`, también los de menos de
 * seis entidades, numerados detrás.
 */
export function gruposDelMapa(analisis, { conPequenos = false } = {}) {
  const lista = conPequenos ? analisis.nucleos : conEstructura(analisis.nucleos)
  return lista.map((n, i) => ({ ...n, numero: String(i + 1).padStart(2, '0') }))
}

/**
 * Coloca los círculos de los grupos llenando un rectángulo.
 *
 * Un empaquetado de círculos a secas acaba en un círculo grande, y en una
 * pantalla apaisada eso deja dos franjas vacías a los lados. Se parte de
 * `packSiblings` —que los junta sin solaparlos— y se estira hacia la forma
 * del lienzo con una gravedad más fuerte en el eje corto, deshaciendo los
 * solapes que el estirón crea. Es determinista: la misma entrada da la misma
 * colocación, en cualquier máquina.
 *
 * @param {number[]} radios en unidades cualesquiera, proporcionales a la raíz del valor
 * @returns {{x: number, y: number, r: number}[]} ya en píxeles del lienzo
 */
export function colocarGrupos(radios, ancho, alto, { margen = 12 } = {}) {
  /*
    Cuánto hay que estirar depende de la proporción del lienzo y de cómo sean
    los círculos —cuatro grandes no se colocan como cuarenta medianos—, así
    que se prueban unas cuantas intensidades y se queda la que más llena. Con
    una sola fija, en una pantalla apaisada el conjunto ocupaba dos tercios
    del ancho y dejaba franjas vacías a los lados.
  */
  // Con los grupos pequeños puestos son doscientos círculos y la cuenta es
  // cuadrática: una sola intensidad y menos vueltas, o el mapa tarda un
  // segundo en aparecer.
  const muchos = radios.length > 80
  let mejor = null
  for (const anisotropia of muchos ? [2] : [1, 1.5, 2, 2.5, 3]) {
    const c = colocarUna(radios, ancho, alto, { margen, anisotropia, iteraciones: muchos ? 150 : 300 })
    const area = c.reduce((s, q) => s + q.r * q.r, 0)
    if (!mejor || area > mejor.area + 1e-9) mejor = { c, area }
  }
  return mejor?.c ?? []
}

function colocarUna(radios, ancho, alto, { margen, anisotropia, iteraciones = 300 }) {
  if (!radios.length || !ancho || !alto) return []
  const circulos = radios.map((r) => ({ r: Math.max(r, 1e-9) }))
  packSiblings(circulos)
  if (circulos.length === 1) return [{ x: ancho / 2, y: alto / 2, r: Math.min(ancho, alto) / 2 - margen }]

  const rMax = Math.max(...circulos.map((c) => c.r))
  const hueco = rMax * 0.04
  const proporcion = ancho / alto
  const estiron = proporcion
  for (const c of circulos) {
    c.x *= estiron
    c.y /= estiron
  }

  // Gravedad hacia el centro, más fuerte en el eje corto: así el conjunto
  // toma la forma del lienzo y no la de un círculo.
  const gx = 0.01 * Math.min(1, 1 / proporcion ** anisotropia)
  const gy = 0.01 * Math.min(1, proporcion ** anisotropia)
  for (let it = 0; it < iteraciones; it++) {
    for (const c of circulos) {
      c.x -= c.x * gx
      c.y -= c.y * gy
    }
    for (let i = 0; i < circulos.length; i++) {
      const a = circulos[i]
      for (let j = i + 1; j < circulos.length; j++) {
        const b = circulos[j]
        let dx = b.x - a.x
        let dy = b.y - a.y
        let d = Math.hypot(dx, dy)
        const minimo = a.r + b.r + hueco
        if (d >= minimo) continue
        if (d < 1e-9) {
          // Coincidentes: se separan en una dirección fija, no al azar.
          dx = 1
          dy = 0
          d = 1
        }
        // Se mueve más el pequeño: el grande ancla el dibujo.
        const empuje = (minimo - d) / d
        const pa = b.r / (a.r + b.r)
        const pb = a.r / (a.r + b.r)
        a.x -= dx * empuje * pa
        a.y -= dy * empuje * pa
        b.x += dx * empuje * pb
        b.y += dy * empuje * pb
      }
    }
  }

  // Encajar en el rectángulo, con la misma escala en los dos ejes: un
  // círculo aplastado mentiría sobre su área.
  let x0 = Infinity
  let y0 = Infinity
  let x1 = -Infinity
  let y1 = -Infinity
  for (const c of circulos) {
    x0 = Math.min(x0, c.x - c.r)
    y0 = Math.min(y0, c.y - c.r)
    x1 = Math.max(x1, c.x + c.r)
    y1 = Math.max(y1, c.y + c.r)
  }
  const escala = Math.min((ancho - margen * 2) / (x1 - x0), (alto - margen * 2) / (y1 - y0))
  const dx = (ancho - (x1 - x0) * escala) / 2
  const dy = (alto - (y1 - y0) * escala) / 2
  return circulos.map((c) => ({
    x: dx + (c.x - x0) * escala,
    y: dy + (c.y - y0) * escala,
    r: c.r * escala,
  }))
}

/** El radio mínimo de un grupo, como parte del radio del mayor. */
export const MINIMO_RELATIVO = 0.07

/**
 * El dibujo entero: grupos colocados y, dentro de cada uno, sus entidades.
 *
 * El valor de una entidad es su dinero dentro del grupo. Las que no llevan
 * cifra —hay relaciones que se publican sin importe— reciben un suelo
 * minúsculo para que existan en el dibujo: una entidad del grupo que no
 * aparece se leería como que no está.
 */
export function disponerMapa(analisis, grupos, ancho, alto) {
  if (!grupos.length || !ancho || !alto) return { grupos: [], porMiembro: new Map() }

  const valorDe = (id) => analisis.interno.get(id) ?? 0
  const totalInterno = grupos.reduce((s, g) => s + g.miembros.reduce((t, id) => t + valorDe(id), 0), 0)
  const suelo = Math.max(1, totalInterno * 2e-6)

  const conValores = grupos.map((g) => {
    const miembros = g.miembros.map((id) => {
      const a = analisis.grafo.getNodeAttributes(id)
      return {
        id,
        caption: analisis.porId.get(id)?.caption ?? a.label ?? id,
        esquema: a.esquema,
        valor: Math.max(valorDe(id), suelo),
        dentro: valorDe(id),
      }
    })
    return { g, miembros, valor: miembros.reduce((s, m) => s + m.valor, 0) }
  })

  /*
    Un mínimo de tamaño, y dicho. Con el área fiel, el grupo más pequeño de
    la instantánea medía un píxel de radio al lado de uno de ciento treinta:
    no se ve ni se puede pulsar, y un grupo que no se ve se lee como que no
    está. Los que no llegan al mínimo se dibujan en el mínimo y con el borde
    a trazos (`agrandado`); su cifra, en el rótulo y en la ficha flotante, es
    la de verdad.
  */
  const naturales = conValores.map((c) => Math.sqrt(c.valor))
  const minimo = Math.max(...naturales) * MINIMO_RELATIVO
  const colocados = colocarGrupos(
    naturales.map((r) => Math.max(r, minimo)),
    ancho,
    alto,
  )

  const porMiembro = new Map()
  const salida = conValores.map((c, i) => {
    const { x, y, r } = colocados[i]
    const raiz = hierarchy({ children: c.miembros })
      .sum((d) => d.valor ?? 0)
      .sort((a, b) => b.value - a.value)
    pack()
      .size([r * 2, r * 2])
      .padding(Math.max(0.4, r * 0.012))(raiz)
    const miembros = (raiz.children ?? []).map((h) => ({
      ...h.data,
      grupo: c.g.id,
      x: x - r + h.x,
      y: y - r + h.y,
      r: h.r,
    }))
    for (const m of miembros) porMiembro.set(m.id, m)
    return { ...c.g, x, y, r, miembros, agrandado: naturales[i] < minimo }
  })

  return { grupos: salida, porMiembro }
}

/**
 * Los caminos de una entidad dentro de su grupo, para iluminarlos al pasar.
 *
 * `de` es siempre quien paga y `a` quien cobra, según las aristas originales.
 * Van de más a menos dinero y con tope: una administración con doscientos
 * proveedores dibujaría doscientas líneas, y a partir de unas decenas ya no
 * se distingue ninguna.
 */
export function caminosDe(analisis, id, tope = 60) {
  const salida = []
  for (const p of analisis.pagos.values()) {
    if (p.de === id || p.a === id) salida.push(p)
  }
  salida.sort((x, y) => y.importe - x.importe || y.n - x.n)
  return salida.slice(0, tope)
}

/** Lo que una entidad paga y cobra dentro de su grupo, para su ficha flotante. */
export function balanceDe(analisis, id) {
  const b = { paga: 0, aCuantos: 0, cobra: 0, deCuantos: 0 }
  for (const p of analisis.pagos.values()) {
    if (p.de === id) {
      b.paga += p.importe
      b.aCuantos += 1
    } else if (p.a === id) {
      b.cobra += p.importe
      b.deCuantos += 1
    }
  }
  return b
}

/**
 * Hacia dónde mira la cámara: `[x, y, ancho visible]`, el formato de
 * `interpolateZoom` de d3. Sin grupo, el dibujo entero; con grupo, su
 * círculo con un poco de aire alrededor.
 */
export function vistaDe(grupo, ancho, alto) {
  if (!grupo) return [ancho / 2, alto / 2, Math.min(ancho, alto)]
  return [grupo.x, grupo.y, grupo.r * 2 * 1.08]
}

/** De coordenadas del dibujo a píxeles de pantalla, con la cámara en `vista`. */
export function proyectar(x, y, vista, ancho, alto) {
  const k = Math.min(ancho, alto) / vista[2]
  return { x: ancho / 2 + (x - vista[0]) * k, y: alto / 2 + (y - vista[1]) * k, k }
}

/** Una curva suave de `a` a `b`, arqueada siempre hacia el mismo lado. */
export function curva(a, b, arco = 0.18) {
  const mx = (a.x + b.x) / 2
  const my = (a.y + b.y) / 2
  const dx = b.x - a.x
  const dy = b.y - a.y
  return `M${a.x},${a.y} Q${mx - dy * arco},${my + dx * arco} ${b.x},${b.y}`
}
