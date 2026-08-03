import { db, json, error, aNodo, sinBaseDeDatos } from './_lib.js'

/** GET /api/search?q=…&limit=… */
export default async function handler(req, res) {
  const q = (req.query.q || '').trim()
  if (q.length < 3) return error(res, 400, 'q debe tener al menos 3 caracteres')

  let limite = Number(req.query.limit) || 25
  if (!Number.isFinite(limite) || limite < 1 || limite > 100) limite = 25

  try {
    const sql = db()
    const filas = await sql`
      SELECT id, ftm_schema, caption, COALESCE(nif,'') AS nif
      FROM entities
      WHERE canonical_id IS NULL
        AND caption_normalizado LIKE '%' || sinapsis_normalizar_nombre(${q}) || '%'
      ORDER BY length(caption)
      LIMIT ${limite}`
    json(res, 200, { results: filas.map((f) => aNodo(f)) })
  } catch (err) {
    sinBaseDeDatos(res, err)
  }
}
