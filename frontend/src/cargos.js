/**
 * Los altos cargos del Estado, como los publica el BOE.
 *
 * Lógica pura sobre `cargos.json` (ver `ingest/sinapsis_ingest/exportar_cargos.py`):
 * buscar, ordenar y decir cada periodo sin decir más de lo que se sabe.
 *
 * ## Lo que un periodo NO dice
 *
 * - Sin `hasta` no significa «sigue en el cargo»: significa que no consta
 *   cese en lo leído. El BOE no publica un aviso de «sigue».
 * - Sin `desde` no significa que el cargo empezara ahí: el nombramiento es
 *   anterior a lo que se ha cargado, o no se pudo leer.
 *
 * Y la persona sale aquí por haber ocupado un cargo público, y sólo por eso
 * (spec §12). Nada de esta página habla de lo que hizo antes o después.
 */
import { normaliza } from './buscador.js'

const MESES = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
]
const MESES_CORTOS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

/** «2026-09-02» → «2 de septiembre de 2026». Sin `Date`: nada de husos. */
export function fechaLarga(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso ?? '')
  if (!m) return ''
  return `${Number(m[3])} de ${MESES[Number(m[2]) - 1]} de ${m[1]}`
}

/** «2026-09-02» → «2 sep 2026». */
export function fechaCorta(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso ?? '')
  if (!m) return ''
  return `${Number(m[3])} ${MESES_CORTOS[Number(m[2]) - 1]} ${m[1]}`
}

/**
 * Cómo se dice un periodo, en una línea. Nunca rellena lo que falta.
 */
export function tramo(p) {
  if (p.desde && p.hasta) return `${fechaCorta(p.desde)} – ${fechaCorta(p.hasta)}`
  if (p.desde) return `desde ${fechaCorta(p.desde)}`
  if (p.hasta) return `hasta ${fechaCorta(p.hasta)}`
  return ''
}

/**
 * Lo que falta en un periodo, dicho. `''` si no falta nada.
 */
export function huecoDelPeriodo(p) {
  if (p.desde && !p.hasta) return 'no consta cese'
  // La Oficina de Conflictos de Intereses da la fecha de cese y no la del
  // nombramiento: no es que sea anterior a lo leído, es que no la publica.
  if (!p.desde && p.hasta) return p.fuente === 'oci' ? 'la fuente no da el nombramiento' : 'nombramiento anterior a lo leído'
  return ''
}

/** Cómo se nombra la fuente de un periodo. */
export function nombreFuente(p) {
  return p.fuente === 'oci' ? 'Oficina de Conflictos de Intereses' : 'BOE'
}

/**
 * Todos los actos de todas las personas, del más reciente al más antiguo.
 * Es la columna de «nombramientos y ceses» de la sección.
 */
export function movimientos(datos, limite = 20) {
  const actos = []
  for (const persona of datos?.personas ?? []) {
    for (const p of persona.periodos ?? []) {
      if (p.desde) actos.push({ tipo: 'nombramiento', fecha: p.desde, boe: p.boeDesde, url: p.urlDesde, persona, periodo: p })
      if (p.hasta) actos.push({ tipo: 'cese', fecha: p.hasta, boe: p.boeHasta || nombreFuente(p), url: p.urlHasta, persona, periodo: p })
    }
    // Las autorizaciones de actividad privada, en la misma columna: son lo
    // que pasa después del cese.
    for (const a of persona.autorizaciones ?? []) {
      if (a.fecha) {
        actos.push({
          tipo: 'autorizacion',
          fecha: a.fecha,
          boe: 'Oficina de Conflictos de Intereses',
          url: a.url,
          persona,
          periodo: { cargo: a.actividad },
        })
      }
    }
  }
  // A igual fecha, el nombramiento arriba: al formarse un gobierno se cesa
  // y se vuelve a nombrar el mismo día, y en una columna de lo más reciente
  // a lo más antiguo lo último que pasó va primero.
  const orden = { autorizacion: 0, nombramiento: 1, cese: 2 }
  actos.sort((a, b) => (a.fecha < b.fecha ? 1 : a.fecha > b.fecha ? -1 : orden[a.tipo] - orden[b.tipo]))
  return actos.slice(0, limite)
}

/**
 * Busca por nombre, por cargo o por organismo. Cada palabra tiene que estar,
 * en cualquier orden, y al principio de una palabra: «gil» no encuentra a
 * «Virgilio».
 */
export function buscarCargos(datos, consulta) {
  const palabras = normaliza(consulta).split(/\s+/).filter((p) => p.length >= 2)
  const personas = datos?.personas ?? []
  if (!palabras.length) return personas
  return personas.filter((persona) => {
    const texto =
      ' ' +
      normaliza(
        [
          persona.nombre,
          ...(persona.periodos ?? []).flatMap((p) => [p.cargo, p.puesto, p.organismo]),
        ].join(' '),
      ).replace(/[^\p{L}\p{N}]+/gu, ' ')
    return palabras.every((p) => texto.includes(' ' + p))
  })
}

/** Una persona por su clave estable, o null. */
export function personaDeClave(datos, clave) {
  if (!clave) return null
  return (datos?.personas ?? []).find((p) => p.clave === clave) ?? null
}

/** Los organismos con más actos, para dar el contexto de la sección. */
export function organismos(datos, limite = 8) {
  const cuenta = new Map()
  for (const persona of datos?.personas ?? []) {
    for (const p of persona.periodos ?? []) {
      if (!p.organismo) continue
      cuenta.set(p.organismo, (cuenta.get(p.organismo) ?? 0) + (p.desde ? 1 : 0) + (p.hasta ? 1 : 0))
    }
  }
  return [...cuenta.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'es'))
    .slice(0, limite)
    .map(([nombre, actos]) => ({ nombre, actos }))
}

/**
 * Filas para el buscador de la cabecera: personas con cargo, con el cargo
 * más reciente como descripción. Mismo criterio de coincidencia que arriba,
 * pero sólo sobre el NOMBRE: quien escribe «hacienda» en el buscador general
 * busca el ministerio, no a todos los que pasaron por él.
 */
export function resultadosDeCargos(datos, consulta, limite = 5) {
  const palabras = normaliza(consulta).split(/\s+/).filter((p) => p.length >= 2)
  if (!palabras.length) return []
  const salida = []
  for (const persona of datos?.personas ?? []) {
    const texto = ' ' + normaliza(persona.nombre).replace(/[^\p{L}\p{N}]+/gu, ' ')
    if (!palabras.every((p) => texto.includes(' ' + p))) continue
    const ultimo = persona.periodos?.[0]
    salida.push({
      id: `cargo:${persona.clave}`,
      clave: persona.clave,
      caption: persona.nombre,
      schema: 'Person',
      cargo: true,
      descripcion: ultimo?.cargo ?? '',
    })
    if (salida.length >= limite) break
  }
  return salida
}

/** Días desde el 1/1/1970 de una fecha ISO, sin `Date` y sin husos. */
function dia(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso ?? '')
  if (!m) return null
  // Días civiles de Howard Hinnant: exacto y sin depender de la zona horaria.
  let y = Number(m[1])
  const mes = Number(m[2])
  const d = Number(m[3])
  y -= mes <= 2 ? 1 : 0
  const era = Math.floor(y / 400)
  const yoe = y - era * 400
  const doy = Math.floor((153 * (mes + (mes > 2 ? -3 : 9)) + 2) / 5) + d - 1
  const doe = yoe * 365 + Math.floor(yoe / 4) - Math.floor(yoe / 100) + doy
  return era * 146097 + doe - 719468
}

/**
 * Los periodos de una persona sobre un eje de tiempo, en fracciones de 0 a 1.
 *
 * El eje va de lo primero a lo último que se ha leído del BOE (`desde` y
 * `hasta` del fichero), no de la vida de la persona: lo que queda fuera de lo
 * leído no se dibuja como si se supiera. Un periodo sin inicio arranca en el
 * borde con `abiertoIzquierda`; uno sin cese llega al final con
 * `abiertoDerecha`, y la interfaz los dibuja deshilachados, no como barras
 * cerradas.
 */
export function lineaDeTiempo(periodos, desde, hasta) {
  const a = dia(desde)
  const b = dia(hasta)
  if (a === null || b === null || b <= a) return []
  const x = (iso) => Math.min(1, Math.max(0, (dia(iso) - a) / (b - a)))
  return (periodos ?? []).map((p) => ({
    periodo: p,
    inicio: p.desde ? x(p.desde) : 0,
    fin: p.hasta ? x(p.hasta) : 1,
    abiertoIzquierda: !p.desde,
    abiertoDerecha: !p.hasta,
  }))
}

/** Los años que caben en el eje, para las marcas. Como mucho `n`. */
export function marcasDeAnios(desde, hasta, n = 6) {
  const a = Number((desde ?? '').slice(0, 4))
  const b = Number((hasta ?? '').slice(0, 4))
  if (!a || !b || b < a) return []
  const paso = Math.max(1, Math.ceil((b - a + 1) / n))
  const inicio = dia(desde)
  const total = dia(hasta) - inicio
  const salida = []
  // El primer 1 de enero que cae dentro del eje.
  const primero = desde.slice(5) === '01-01' ? a : a + 1
  for (let y = primero; y <= b; y += paso) {
    const f = (dia(`${y}-01-01`) - inicio) / total
    if (f >= 0 && f <= 1) salida.push({ anio: y, x: f })
  }
  return salida
}

/**
 * Las presidencias del Gobierno que hay en lo leído, de la más antigua a la
 * más reciente. Salen de los Reales Decretos de nombramiento y cese del
 * Presidente, sin inferir nada: si falta un cese, el periodo queda abierto
 * y se dice como cualquier otro.
 */
export function presidencias(datos) {
  const salida = []
  for (const persona of datos?.personas ?? []) {
    for (const p of persona.periodos ?? []) {
      if (p.puesto === 'Presidente del Gobierno' && (p.fuente ?? 'boe') === 'boe') {
        salida.push({ persona: persona.clave, nombre: persona.nombre, ...p })
      }
    }
  }
  return salida.sort((a, b) => ((a.desde || a.hasta) < (b.desde || b.hasta) ? -1 : 1))
}

/**
 * Cuántas personas salen de cada fuente. «408 personas nombradas por Real
 * Decreto» contaba también a quien sólo sale en la Oficina de Conflictos de
 * Intereses, que no publica nombramientos: cada cifra con su fuente.
 */
export function recuento(datos) {
  let boe = 0
  let soloOci = 0
  for (const persona of datos?.personas ?? []) {
    if ((persona.periodos ?? []).some((p) => (p.fuente ?? 'boe') === 'boe')) boe += 1
    else soloOci += 1
  }
  return { boe, soloOci }
}
