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

const BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

export const hayApiConfigurada = BASE !== ''

/** Estado compartido: true en cuanto una llamada cae a la demostración. */
export const estado = { esDemo: !hayApiConfigurada, motivo: hayApiConfigurada ? '' : 'sin-api' }

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
    () => pedir(`/v1/search?q=${encodeURIComponent(q)}&limit=${limite}`),
    () => buscarDemo(q, limite),
    'api-caida',
  )
}

export function entidad(id) {
  return conRespaldo(
    () => pedir(`/v1/entity/${encodeURIComponent(id)}`),
    () => entidadDemo(id),
    'api-caida',
  )
}

export function vecinos(id, profundidad = 1, limite = 300) {
  return conRespaldo(
    () => pedir(`/v1/entity/${encodeURIComponent(id)}/neighbors?depth=${profundidad}&limit=${limite}`),
    () => vecinosDemo(id, profundidad),
    'api-caida',
  )
}
