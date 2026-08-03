import { db, json, error, esUUID, sinBaseDeDatos } from '../_lib.js'

/** GET /api/entity/{id} — ficha con su procedencia. */
export default async function handler(req, res) {
  const { id } = req.query
  if (!esUUID(id)) return error(res, 400, 'id no es un UUID válido')

  try {
    const sql = db()
    const filas = await sql`
      SELECT id, ftm_schema, caption, COALESCE(nif,'') AS nif,
             COALESCE(country,'') AS country, properties, canonical_id
      FROM entities WHERE id = ${id}`
    if (!filas.length) return error(res, 404, 'entidad no encontrada')
    const e = filas[0]

    const proc = await sql`
      SELECT rd.source_id, rd.url, rd.content_hash, rd.retrieved_at,
             p.extractor_version, COALESCE(p.excerpt,'') AS excerpt
      FROM provenance p
      JOIN raw_documents rd ON rd.id = p.raw_document_id
      WHERE p.entity_id = ${id}
      ORDER BY rd.retrieved_at DESC`

    json(res, 200, {
      id: e.id,
      schema: e.ftm_schema,
      caption: e.caption,
      properties: e.properties ?? {},
      ...(e.nif ? { nif: e.nif } : {}),
      ...(e.country ? { country: e.country } : {}),
      // Si fue absorbida se dice: ocultarlo mostraría un duplicado sin avisar.
      ...(e.canonical_id ? { merged_into: e.canonical_id } : {}),
      provenance: proc.map((p) => ({
        source_id: p.source_id,
        url: p.url,
        content_hash: p.content_hash,
        retrieved_at: new Date(p.retrieved_at).toISOString(),
        extractor_version: p.extractor_version,
        ...(p.excerpt ? { excerpt: p.excerpt } : {}),
      })),
    })
  } catch (err) {
    sinBaseDeDatos(res, err)
  }
}
