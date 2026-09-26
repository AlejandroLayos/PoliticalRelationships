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
 * (spec §12). De lo que hizo antes o después, sólo lo que afirma una fuente
 * oficial en ese papel: la autorización de la Oficina de Conflictos de
 * Intereses y lo que el diputado declaró al Congreso.
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
  if (p.fuente === 'congreso') return p.hasta ? '' : 'sin baja en el Congreso'
  if (p.desde && !p.hasta) return 'no consta cese'
  // La Oficina de Conflictos de Intereses da la fecha de cese y no la del
  // nombramiento: no es que sea anterior a lo leído, es que no la publica.
  if (!p.desde && p.hasta) return p.fuente === 'oci' ? 'la fuente no da el nombramiento' : 'nombramiento anterior a lo leído'
  return ''
}

/** Cómo se nombra la fuente de un periodo. */
export function nombreFuente(p) {
  if (p.fuente === 'oci') return 'Oficina de Conflictos de Intereses'
  if (p.fuente === 'congreso') return 'Congreso de los Diputados'
  return 'BOE'
}

/**
 * La formación con la que fue elegido diputado quien tenía un cargo en una
 * fecha: la del mandato del Congreso que la cubre, o la del más cercano
 * anterior. Sólo si su ficha está unida al Congreso por las dos señales
 * (nombre y cargo en su biografía); si no, ''.
 */
export function formacionEn(persona, fecha) {
  const mandatos = (persona?.periodos ?? [])
    .filter((p) => p.fuente === 'congreso' && p.formacion && p.desde)
    .sort((a, b) => (a.desde < b.desde ? -1 : 1))
  if (!mandatos.length || !fecha) return ''
  const cubre = mandatos.find((m) => m.desde <= fecha && (!m.hasta || fecha <= m.hasta))
  if (cubre) return cubre.formacion
  const anteriores = mandatos.filter((m) => m.desde <= fecha)
  return anteriores.length ? anteriores[anteriores.length - 1].formacion : ''
}

/**
 * Todos los actos de todas las personas, del más reciente al más antiguo.
 * Es la columna de «nombramientos y ceses» de la sección.
 */
export function movimientos(datos, limite = 20) {
  const actos = []
  for (const persona of datos?.personas ?? []) {
    for (const p of persona.periodos ?? []) {
      // Las altas y bajas de diputados no son nombramientos ni ceses: la
      // columna es la de los Reales Decretos, y cuatrocientas altas del mismo
      // día la taparían entera.
      if (p.fuente === 'congreso') continue
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
          ...(persona.periodos ?? []).flatMap((p) => [
            p.cargo,
            p.puesto,
            p.organismo,
            p.formacion,
            p.circunscripcion,
          ]),
          // Para quién declaró trabajar: «indra» encuentra a quien lo declaró.
          ...(persona.declaraciones ?? []).map((d) => d.empleador),
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
      descripcion: [ultimo?.cargo, ultimo?.formacion].filter(Boolean).join(' · '),
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
  // Lo que empieza antes del eje —el escaño de un diputado desde 2023, en un
  // eje del BOE que arranca en 2025— también sale deshilachado por la
  // izquierda: cortado en el borde parecería empezar ahí.
  return (periodos ?? []).map((p) => ({
    periodo: p,
    inicio: p.desde ? x(p.desde) : 0,
    fin: p.hasta ? x(p.hasta) : 1,
    abiertoIzquierda: !p.desde || dia(p.desde) < a,
    abiertoDerecha: !p.hasta || dia(p.hasta) > b,
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
        salida.push({
          persona: persona.clave,
          nombre: persona.nombre,
          formacion: formacionEn(persona, p.desde || p.hasta),
          ...p,
        })
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
  let diputados = 0
  for (const persona of datos?.personas ?? []) {
    const fuentes = new Set((persona.periodos ?? []).map((p) => p.fuente ?? 'boe'))
    if (fuentes.has('boe')) boe += 1
    else if (fuentes.has('congreso')) diputados += 1
    else soloOci += 1
  }
  return { boe, soloOci, diputados }
}

/**
 * Quién sale en la lista: todos, quien tiene un Real Decreto (`boe`), los
 * diputados (`congreso`: quien tiene un mandato, unido o no a un alto cargo),
 * o quien tiene autorizaciones para el sector privado (`autorizados`).
 */
export function dePapel(personas, papel) {
  if (!papel || papel === 'todos') return personas
  // Quien tiene autorizaciones de la Oficina de Conflictos de Intereses, esté
  // o no unido a su ficha del BOE.
  if (papel === 'autorizados') return personas.filter((persona) => persona.autorizaciones?.length)
  // Las altas instancias judiciales y fiscales también salen del BOE, pero
  // no son altos cargos: cada una va en su lista.
  if (papel === 'justicia') {
    return personas.filter((persona) => (persona.periodos ?? []).some((p) => p.ambito === 'justicia'))
  }
  if (papel === 'boe') {
    return personas.filter((persona) =>
      (persona.periodos ?? []).some((p) => (p.fuente ?? 'boe') === 'boe' && p.ambito !== 'justicia'),
    )
  }
  return personas.filter((persona) =>
    (persona.periodos ?? []).some((p) => (p.fuente ?? 'boe') === papel),
  )
}

/**
 * El sector de una actividad declarada, como lo escribió el diputado:
 * «PÚBLICO», «Privado», «PRIVADO AGRICOLA», «Educación»… Sólo se reconocen
 * los dos claros; lo demás se enseña tal cual y sin color.
 */
export function sectorDeclarado(d) {
  const s = normaliza(d?.sector ?? '')
  if (/\bprivad/.test(s)) return 'privado'
  if (/\b(public|administracion|gubernamental|gobierno)/.test(s)) return 'publico'
  return ''
}

/** Cómo se llama la ficha: por lo más alto que se sabe de la persona. */
export function papelDeLaFicha(persona) {
  const periodos = persona?.periodos ?? []
  const delBoe = periodos.filter((p) => (p.fuente ?? 'boe') === 'boe')
  // Sólo altas instancias judiciales o fiscales: no es un alto cargo del
  // Gobierno, y la ficha no puede decir que lo es.
  if (delBoe.length && delBoe.every((p) => p.ambito === 'justicia')) return 'Justicia · alta instancia'
  if (delBoe.length) return 'Alto cargo'
  if (periodos.some((p) => p.fuente === 'congreso')) return 'Congreso de los Diputados'
  return 'Ex alto cargo'
}

/** «del Senado», «del Consejo General del Poder Judicial»: con su artículo. */
export function propuestaEnPalabras(quien) {
  return quien ? `del ${quien}` : ''
}

/**
 * Las personas nombradas —algún periodo del BOE— bajo la presidencia de
 * `presidente` (su clave). Es la fecha del Real Decreto contra las
 * presidencias leídas (`gobierno`, de exportar_cargos.py): dice quién
 * gobernaba, no a qué partido pertenece la persona.
 */
export function bajoGobierno(personas, presidente) {
  if (!presidente) return personas
  return personas.filter((persona) =>
    (persona.periodos ?? []).some((p) => p.gobierno?.persona === presidente),
  )
}

/**
 * Los gobiernos por los que se puede filtrar: una entrada por presidente,
 * con cuántas personas nombró, sólo si nombró a alguien en lo leído. En
 * orden de tiempo, como la franja de presidencias.
 */
export function gobiernos(datos) {
  const cuenta = new Map()
  for (const persona of datos?.personas ?? []) {
    const vistos = new Set()
    for (const p of persona.periodos ?? []) {
      const g = p.gobierno
      if (!g || vistos.has(g.persona)) continue
      vistos.add(g.persona)
      const x = cuenta.get(g.persona) ?? { ...g, personas: 0, primero: p.desde }
      x.personas += 1
      if (g.formacion) x.formacion = g.formacion
      if (p.desde && p.desde < x.primero) x.primero = p.desde
      cuenta.set(g.persona, x)
    }
  }
  return [...cuenta.values()]
    .sort((a, b) => (a.primero < b.primero ? -1 : 1))
    .map(({ primero, ...g }) => g)
}

/** «Gobierno de Mariano Rajoy Brey · PP», o sin la formación si no se sabe. */
export function nombreDeGobierno(g) {
  if (!g) return ''
  return `Gobierno de ${g.nombre}${g.formacion ? ` · ${g.formacion}` : ''}`
}

/**
 * Lo que un órgano pagó o adjudicó a una sociedad (`delOrgano`, de
 * exportar_cargos.py), en palabras: el verbo según de dónde sale el dinero,
 * cuántas veces, y los años. Las fechas son las que da cada fuente —concesión
 * en BDNS, publicación del expediente en PLACSP—, así que se dicen en años.
 */
export function delOrganoEnPalabras(d) {
  const pagos = d?.pagos ?? 0
  const adjudicaciones = d?.adjudicaciones ?? 0
  const verbo = pagos && adjudicaciones ? 'pagó o adjudicó' : pagos ? 'pagó' : 'adjudicó'
  const partes = []
  if (pagos) partes.push(`${pagos} ${pagos === 1 ? 'pago' : 'pagos'}`)
  if (adjudicaciones) partes.push(`${adjudicaciones} ${adjudicaciones === 1 ? 'adjudicación' : 'adjudicaciones'}`)
  const a = (d?.desde ?? '').slice(0, 4)
  const b = (d?.hasta ?? '').slice(0, 4)
  const cuando = a && b ? (a === b ? `en ${a}` : `entre ${a} y ${b}`) : ''
  return { verbo, cuantos: partes.join(' y '), cuando }
}

/**
 * Las formaciones de los diputados de la lista, con cuántas personas fueron
 * elegidas por cada una en alguna legislatura leída. Para navegar, no para
 * comparar: el número es el de escaños que salen aquí, no un indicador.
 */
export function formaciones(personas) {
  const cuenta = new Map()
  for (const persona of personas ?? []) {
    const suyas = new Set(
      (persona.periodos ?? []).filter((p) => p.fuente === 'congreso' && p.formacion).map((p) => p.formacion),
    )
    for (const f of suyas) cuenta.set(f, (cuenta.get(f) ?? 0) + 1)
  }
  return [...cuenta.entries()]
    .map(([formacion, personas]) => ({ formacion, personas }))
    .sort((a, b) => b.personas - a.personas || a.formacion.localeCompare(b.formacion, 'es'))
}

/** Quien fue elegido diputado por `formacion` en alguna legislatura leída. */
export function deFormacion(personas, formacion) {
  if (!formacion) return personas
  return personas.filter((persona) =>
    (persona.periodos ?? []).some((p) => p.fuente === 'congreso' && p.formacion === formacion),
  )
}

/**
 * La ficha del partido de una formación en el mapa del dinero, o null. El
 * puente lo da el Senado (siglas → nombre oficial) y el volcado lo resuelve
 * sólo con nombre exacto y único (`formaciones` de exportar_cargos.py).
 */
export function entidadDeFormacion(datos, formacion) {
  return datos?.formaciones?.[formacion]?.entidad ?? null
}

/**
 * Las formaciones cuyo partido es la entidad `clave` del mapa, con cuántos de
 * sus diputados salen en la sección. Para el panel del partido.
 */
export function formacionesDeEntidad(datos, clave) {
  if (!clave) return []
  const salida = []
  for (const [formacion, f] of Object.entries(datos?.formaciones ?? {})) {
    if (f?.entidad?.clave !== clave) continue
    salida.push({ formacion, nombre: f.nombre, personas: deFormacion(datos?.personas ?? [], formacion).length })
  }
  return salida.filter((f) => f.personas > 0)
}
