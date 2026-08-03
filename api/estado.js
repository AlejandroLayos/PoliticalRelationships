import { db, json } from './_lib.js'

/**
 * GET /api/estado — ¿hay base de datos, y tiene algo dentro?
 *
 * Existe para que la interfaz distinga tres situaciones que se ven igual si
 * no preguntas: no hay API, la hay pero la base está vacía, o hay datos. La
 * segunda es la más confusa —parece que todo falla cuando en realidad sólo
 * falta la primera ingesta— y merecía una respuesta explícita.
 */
export default async function handler(req, res) {
  try {
    const sql = db()
    const filas = await sql`
      SELECT
        (SELECT count(*) FROM entities WHERE canonical_id IS NULL) AS entidades,
        (SELECT count(*) FROM relationships WHERE status <> 'retracted') AS aristas,
        (SELECT count(*) FROM raw_documents) AS documentos,
        (SELECT count(*) FROM review_queue WHERE status = 'pending') AS pendientes,
        (SELECT max(retrieved_at) FROM raw_documents) AS ultima_ingesta`
    const f = filas[0]
    const entidades = Number(f.entidades)
    json(res, 200, {
      conectada: true,
      vacia: entidades === 0,
      entidades,
      aristas: Number(f.aristas),
      documentos: Number(f.documentos),
      candidatos_pendientes: Number(f.pendientes),
      ultima_ingesta: f.ultima_ingesta ? new Date(f.ultima_ingesta).toISOString() : null,
    })
  } catch (err) {
    // 200 a propósito: "no hay base" es una respuesta válida a esta pregunta,
    // no un error del servidor.
    json(res, 200, { conectada: false, vacia: true, motivo: err.message })
  }
}
