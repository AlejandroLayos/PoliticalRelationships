/**
 * Utilidades comunes de las funciones de Vercel.
 *
 * Estas funciones son la MISMA API que sirve `backend/` en Go, reimplementada
 * sobre el driver serverless de Neon. No es duplicación por gusto: un binario
 * Go de larga vida y una función efímera son modelos de ejecución distintos, y
 * Vercel sólo admite el segundo. El contrato —rutas, forma del JSON, reglas de
 * confianza— es idéntico, y `docs/adr/0004-despliegue-vercel.md` explica por
 * qué conviven.
 *
 * Si cambias el contrato de una, mira la otra. El esquema SQL es el árbitro.
 */

import { neon } from '@neondatabase/serverless'

/** Conexión sobre HTTP: sin sockets persistentes, que es lo que rompe en serverless. */
export function db() {
  const url = process.env.DATABASE_URL || process.env.POSTGRES_URL
  if (!url) {
    throw new Error(
      'falta DATABASE_URL. Añade Neon desde el marketplace de Vercel: la integración la define sola.',
    )
  }
  return neon(url)
}

export function json(res, code, cuerpo) {
  res.setHeader('Content-Type', 'application/json; charset=utf-8')
  // La API es de lectura pública; el frontend puede estar en otro dominio.
  res.setHeader('Access-Control-Allow-Origin', '*')
  // Los datos cambian como mucho una vez al día: cachear en el borde ahorra
  // consultas a la base y hace la navegación instantánea.
  res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=3600')
  res.status(code).send(JSON.stringify(cuerpo))
}

export function error(res, code, mensaje) {
  json(res, code, { error: mensaje })
}

/** Sin base de datos poblada, la respuesta debe decirlo, no fingir un grafo vacío. */
export function sinBaseDeDatos(res, err) {
  console.error('error de base de datos:', err.message)
  error(res, 503, 'la base de datos no está disponible o no tiene el esquema aplicado')
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export function esUUID(v) {
  return typeof v === 'string' && UUID.test(v)
}

/**
 * Convierte una fila de `entities` al nodo que espera el frontend.
 * Mismo shape que produce `aNodoJSON` en Go.
 */
export function aNodo(fila, depth = 0) {
  return {
    id: fila.id,
    schema: fila.ftm_schema,
    caption: fila.caption,
    ...(fila.nif ? { nif: fila.nif } : {}),
    depth,
  }
}

/**
 * Mismo shape que `aAristaJSON` en Go.
 *
 * `confidence` y `status` van SIEMPRE, aunque valgan lo esperable: es la
 * invariante 5 impuesta en la API. Quien consuma esto en crudo tiene que poder
 * distinguir lo afirmado de lo inferido.
 */
export function aArista(fila) {
  return {
    id: fila.id,
    schema: fila.ftm_schema,
    source: fila.source_entity_id,
    target: fila.target_entity_id,
    ...(fila.amount ? { amount: String(fila.amount) } : {}),
    ...(fila.currency ? { currency: fila.currency } : {}),
    confidence: Number(fila.confidence),
    status: fila.status,
    ...(fila.start_date ? { start_date: String(fila.start_date).slice(0, 10) } : {}),
    ...(fila.end_date ? { end_date: String(fila.end_date).slice(0, 10) } : {}),
  }
}

/** Sigue la cadena de fusiones hasta la entidad viva. */
export async function canonica(sql, id) {
  let actual = id
  for (let i = 0; i < 16; i++) {
    const filas = await sql`SELECT canonical_id FROM entities WHERE id = ${actual}`
    if (!filas.length) return null
    if (!filas[0].canonical_id) return actual
    actual = filas[0].canonical_id
  }
  throw new Error('cadena de fusiones demasiado larga')
}
