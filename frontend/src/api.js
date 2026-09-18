/**
 * Cliente de la API de Sinapsis.
 *
 * Si no hay API configurada o no responde, la aplicación cae al conjunto de
 * demostración. Eso NO se disimula: `esDemo` se propaga hasta la interfaz, que
 * lo anuncia con un aviso permanente. Un mapa de dinero público que enseña
 * datos inventados sin decirlo sería exactamente lo contrario de lo que este
 * proyecto pretende.
 */

import { buscarDemo, entidadDemo, vecinosDemo } from './demo.js'
import { crearGrafoLocal, normaliza } from './grafoLocal.js'
import { sanearImportes } from './saneado.js'

// Por defecto se habla con la API del mismo dominio (`/api/...`), que es lo
// que despliegan las funciones de Vercel. `VITE_API_URL` sirve para apuntar a
// un backend propio (el binario Go en un VPS, por ejemplo).
const BASE = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')

// Siempre hay una API a la que intentar llamar. Si no responde —porque la base
// aún está vacía o no hay Neon conectado— se cae a la demostración y se avisa.
export const hayApiConfigurada = true

/** Estado compartido: true en cuanto una llamada cae a la demostración. */
export const estado = { esDemo: false, motivo: '', instantanea: null }

/**
 * Instantánea estática publicada por GitHub Actions.
 *
 * Son datos REALES con su procedencia, sólo que congelados en el momento de
 * generarlos en vez de consultados en vivo. Por eso no llevan la banda de
 * demostración: llevan su fecha.
 */
let _grafoEstatico = null

export async function cargarInstantanea() {
  if (_grafoEstatico !== null) return _grafoEstatico
  try {
    const r = await fetch('/datos/grafo.json', { headers: { Accept: 'application/json' } })
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    const bruto = await r.json()
    if (!bruto.nodes?.length) throw new Error('instantánea vacía')
    // La instantánea y el código se despliegan por separado, así que la web
    // puede estar sirviendo un volcado anterior al último arreglo del
    // conector. Las cifras no atribuibles se retiran aquí también.
    const datos = sanearImportes(bruto)
    _grafoEstatico = crearGrafoLocal(datos)
    estado.instantanea = {
      generado: datos.generado,
      truncado: Boolean(datos.truncado),
      total: datos.total_entidades_en_base ?? datos.nodes.length,
      fuentes: datos.fuentes ?? [],
      // Una fuente registrada que no aportó nada no puede anunciarse como si
      // hubiera aportado: el cartel diría "datos reales de BDNS" con cero
      // entidades de BDNS dentro.
      fuentesConDatos: (datos.fuentes ?? []).filter((f) => (f.entidades ?? 1) > 0),
      fuentesSinDatos: (datos.fuentes ?? []).filter((f) => f.entidades === 0),
      importesSaneados: datos.importesSaneados ?? 0,
    }
    return _grafoEstatico
  } catch {
    _grafoEstatico = false
    return false
  }
}

/**
 * Índice de TODAS las entidades ingeridas, sin aristas.
 *
 * El mapa está acotado a propósito —por encima de unos miles de nodos el
 * navegador sufre— pero ese tope acotaba también la búsqueda, y ahí el efecto
 * era otro: quien buscaba el ayuntamiento de su pueblo y no estaba entre los
 * nodos publicados leía «Sin resultados», que es indistinguible de «esa
 * entidad no existe en ninguna fuente». Existe; no cupo.
 *
 * Se carga perezosamente, en la primera búsqueda: el que sólo mira el mapa no
 * lo descarga.
 */
let _indice = null
let _cargandoIndice = null

export async function cargarIndice() {
  if (_indice !== null) return _indice
  if (_cargandoIndice) return _cargandoIndice
  _cargandoIndice = (async () => {
    try {
      const r = await fetch('/datos/indice.json', { headers: { Accept: 'application/json' } })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const d = await r.json()
      _indice = Array.isArray(d.entidades) ? d : { total: 0, entidades: [] }
    } catch {
      // Sin índice la búsqueda sigue funcionando sobre el mapa. Es un hueco,
      // no un fallo.
      _indice = { total: 0, entidades: [] }
    }
    return _indice
  })()
  return _cargandoIndice
}

export function indiceCargado() {
  return _indice
}

/**
 * El grafo completo de la instantánea, para el mapa de núcleos.
 *
 * Devuelve null si no hay instantánea: agrupar una ego-red no dice nada, así
 * que sin el conjunto entero el mapa no se dibuja.
 */
export function grafoCompleto() {
  return _grafoEstatico ? _grafoEstatico.crudo : null
}

/** Alternativa: primero la instantánea real, y sólo si no hay, la demostración. */
function alternativa(fnEstatico, fnDemo) {
  return () => {
    if (_grafoEstatico) {
      estado.esDemo = false
      estado.motivo = 'instantanea'
      return fnEstatico(_grafoEstatico)
    }
    estado.esDemo = true
    return fnDemo()
  }
}

// El backend Go sirve bajo /v1; las funciones de Vercel, en la raíz de /api.
const RUTA = BASE.endsWith('/api') ? '' : '/v1'

async function pedir(ruta, opciones = {}) {
  const respuesta = await fetch(`${BASE}${ruta}`, {
    ...opciones,
    headers: { Accept: 'application/json' },
  })
  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => ({}))
    throw new Error(cuerpo.error || `HTTP ${respuesta.status}`)
  }
  return respuesta.json()
}

/** Ejecuta `llamada` contra la API; si falla, cae a `alternativa` y lo marca. */
async function conRespaldo(llamada, alternativa, motivo) {
  try {
    const resultado = await llamada()
    estado.esDemo = false
    estado.motivo = ''
    return resultado
  } catch (err) {
    estado.esDemo = true
    estado.motivo = motivo
    console.warn('la API no respondió, se usa el conjunto de demostración:', err.message)
    return alternativa()
  }
}

export function buscar(q, limite = 25) {
  return conRespaldo(
    () => pedir(`${RUTA}/search?q=${encodeURIComponent(q)}&limit=${limite}`),
    alternativa((g) => g.buscar(q, limite), () => buscarDemo(q, limite)),
    'api-caida',
  )
}

/**
 * Busca en el mapa Y en el índice, en ese orden.
 *
 * Primero lo que está publicado en el grafo, porque de eso se puede enseñar la
 * red entera; después lo que sólo consta en el índice, marcado, porque de eso
 * sólo hay cifras. Nunca al revés: sería enviar a la gente a la ficha más
 * pobre teniendo la buena.
 */
export async function buscarTodo(q, limite = 25) {
  const enMapa = await buscar(q, limite)
  const resultados = enMapa.results ?? []
  if (estado.esDemo) return { results: resultados, soloIndice: 0 }

  const idx = await cargarIndice()
  if (!idx.entidades.length) return { results: resultados, soloIndice: 0 }

  const aguja = normaliza(q)
  const yaEstan = new Set(resultados.map((r) => r.id))
  const extra = []
  for (const e of idx.entidades) {
    if (extra.length >= limite) break
    if (yaEstan.has(e.id)) continue
    if (!normaliza(e.caption).includes(aguja)) continue
    extra.push({ ...e, soloIndice: true })
  }
  return { results: [...resultados, ...extra], soloIndice: extra.length, totalIndice: idx.total }
}

export function entidad(id) {
  return conRespaldo(
    () => pedir(`${RUTA}/entity/${encodeURIComponent(id)}`),
    alternativa((g) => g.entidad(id), () => entidadDemo(id)),
    'api-caida',
  )
}

export function vecinos(id, profundidad = 1, limite = 300) {
  return conRespaldo(
    () => pedir(`${RUTA}/entity/${encodeURIComponent(id)}/neighbors?depth=${profundidad}&limit=${limite}`),
    alternativa((g) => g.vecinos(id, profundidad, limite), () => vecinosDemo(id, profundidad)),
    'api-caida',
  )
}

/**
 * Pregunta si hay base de datos y si tiene contenido. Nunca lanza: la
 * respuesta "no hay base" es información, no un fallo.
 */
export async function estadoServidor() {
  if (RUTA !== '') return { conectada: false, vacia: true, motivo: 'backend-externo' }
  try {
    const r = await fetch(`${BASE}/estado`, { headers: { Accept: 'application/json' } })
    if (!r.ok) return { conectada: false, vacia: true, motivo: `HTTP ${r.status}` }
    return await r.json()
  } catch (e) {
    return { conectada: false, vacia: true, motivo: e.message }
  }
}
