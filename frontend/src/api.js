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

// Por defecto se habla con la API del mismo dominio (`/api/...`), que es lo
// que despliegan las funciones de Vercel. `VITE_API_URL` sirve para apuntar a
// un backend propio (el binario Go en un VPS, por ejemplo).
const BASE = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')

// Siempre hay una API a la que intentar llamar. Si no responde —porque la base
// aún está vacía o no hay Neon conectado— se cae a la demostración y se avisa.
export const hayApiConfigurada = true

/** Estado compartido: true en cuanto una llamada cae a la demostración. */
export const estado = { esDemo: false, motivo: '' }

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
  if (!hayApiConfigurada) return alternativa()
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
    () => buscarDemo(q, limite),
    'api-caida',
  )
}

export function entidad(id) {
  return conRespaldo(
    () => pedir(`${RUTA}/entity/${encodeURIComponent(id)}`),
    () => entidadDemo(id),
    'api-caida',
  )
}

export function vecinos(id, profundidad = 1, limite = 300) {
  return conRespaldo(
    () => pedir(`${RUTA}/entity/${encodeURIComponent(id)}/neighbors?depth=${profundidad}&limit=${limite}`),
    () => vecinosDemo(id, profundidad),
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
