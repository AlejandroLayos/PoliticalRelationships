import { db, json, error, esUUID, aNodo, aArista, canonica, sinBaseDeDatos } from '../../_lib.js'

/**
 * GET /api/entity/{id}/neighbors?depth=n&limit=m — ego-red.
 *
 * Se expande nivel a nivel, igual que la versión en Go: el grafo tiene ciclos
 * y una CTE recursiva sobre un grafo cíclico o explota o necesita detección de
 * ciclos que oscurece la consulta. Con profundidades de 1 a 3 son dos o tres
 * consultas acotadas.
 */
export default async function handler(req, res) {
  const { id } = req.query
  if (!esUUID(id)) return error(res, 400, 'id no es un UUID válido')

  const depth = req.query.depth === undefined ? 1 : Number(req.query.depth)
  if (!Number.isInteger(depth) || depth < 1 || depth > 3) {
    return error(res, 400, 'depth debe ser un entero entre 1 y 3')
  }
  const maxNodos = Math.min(Math.max(Number(req.query.limit) || 300, 1), 1000)

  try {
    const sql = db()
    const raiz = await canonica(sql, id)
    if (!raiz) return error(res, 404, 'entidad no encontrada')

    const filaRaiz = await sql`
      SELECT id, ftm_schema, caption, COALESCE(nif,'') AS nif
      FROM entities WHERE id = ${raiz}`
    if (!filaRaiz.length) return error(res, 404, 'entidad no encontrada')

    const visitados = new Map([[raiz, 0]])
    const nodos = [aNodo(filaRaiz[0], 0)]
    const aristas = new Map()
    let frontera = [raiz]
    let truncado = false

    for (let nivel = 1; nivel <= depth && frontera.length; nivel++) {
      const incidentes = await sql`
        SELECT id, ftm_schema, source_entity_id, target_entity_id,
               amount, currency, confidence, status, start_date, end_date
        FROM relationships
        WHERE (source_entity_id = ANY(${frontera}) OR target_entity_id = ANY(${frontera}))
          -- Una arista retractada se conserva por trazabilidad, no para
          -- seguir publicándola.
          AND status <> 'retracted'`

      const siguiente = []
      for (const a of incidentes) {
        if (!aristas.has(a.id)) aristas.set(a.id, aArista(a))
        for (const extremo of [a.source_entity_id, a.target_entity_id]) {
          if (visitados.has(extremo)) continue
          if (visitados.size >= maxNodos) {
            truncado = true
            continue
          }
          visitados.set(extremo, nivel)
          siguiente.push(extremo)
        }
      }
      if (!siguiente.length) break

      const nuevos = await sql`
        SELECT id, ftm_schema, caption, COALESCE(nif,'') AS nif
        FROM entities WHERE id = ANY(${siguiente})`
      for (const f of nuevos) nodos.push(aNodo(f, nivel))
      frontera = siguiente
    }

    // Una arista con un extremo fuera del conjunto colgaría en el vacío al
    // dibujarla. Se descarta y el recorte se anuncia.
    let salida = [...aristas.values()]
    if (truncado) {
      salida = salida.filter((a) => visitados.has(a.source) && visitados.has(a.target))
    }

    json(res, 200, { root: raiz, depth, nodes: nodos, edges: salida, truncated: truncado })
  } catch (err) {
    sinBaseDeDatos(res, err)
  }
}
