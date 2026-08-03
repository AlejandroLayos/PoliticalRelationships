/**
 * Grafo en memoria con la misma interfaz que la API.
 *
 * Lo usan dos cosas: el conjunto de demostración y la **instantánea** estática
 * que publica GitHub Actions. Las dos necesitan buscar, abrir una ficha y
 * expandir un vecindario exactamente igual que hace el servidor, así que la
 * lógica vive aquí una sola vez.
 *
 * La expansión es nivel a nivel, como en Go y en las funciones de Vercel: el
 * grafo tiene ciclos y hay que visitar cada nodo una vez.
 */

export function normaliza(t) {
  return (t || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
}

/**
 * @param {{nodes: Array, edges: Array, provenance?: Object}} datos
 */
export function crearGrafoLocal(datos) {
  const nodos = datos.nodes ?? []
  const aristas = (datos.edges ?? []).filter((a) => a.status !== 'retracted')
  const procedencia = datos.provenance ?? {}
  const porId = new Map(nodos.map((n) => [n.id, n]))

  function buscar(q, limite = 25) {
    const aguja = normaliza(q)
    const results = nodos
      .filter((n) => normaliza(n.caption).includes(aguja))
      .sort((a, b) => (b.degree ?? 0) - (a.degree ?? 0) || a.caption.length - b.caption.length)
      .slice(0, limite)
      .map((n) => ({ ...n, depth: 0 }))
    return { results }
  }

  function entidad(id) {
    const n = porId.get(id)
    if (!n) throw new Error('entidad no encontrada')
    return { ...n, provenance: procedencia[id] ?? [] }
  }

  function vecinos(id, profundidad = 1, limite = 300) {
    if (!porId.has(id)) throw new Error('entidad no encontrada')

    const visitados = new Map([[id, 0]])
    const usadas = new Map()
    let frontera = new Set([id])
    let truncado = false

    for (let nivel = 1; nivel <= Math.min(profundidad, 3) && frontera.size; nivel++) {
      const siguiente = new Set()
      for (const a of aristas) {
        if (!frontera.has(a.source) && !frontera.has(a.target)) continue
        usadas.set(a.id, a)
        for (const extremo of [a.source, a.target]) {
          if (visitados.has(extremo)) continue
          if (visitados.size >= limite) {
            truncado = true
            continue
          }
          visitados.set(extremo, nivel)
          siguiente.add(extremo)
        }
      }
      if (!siguiente.size) break
      frontera = siguiente
    }

    // Una arista con un extremo fuera colgaría en el vacío al dibujarla.
    const edges = [...usadas.values()].filter(
      (a) => visitados.has(a.source) && visitados.has(a.target),
    )
    const nodes = [...visitados.entries()]
      .map(([nid, depth]) => ({ ...porId.get(nid), depth }))
      .filter((n) => n.id)

    return { root: id, depth: profundidad, nodes, edges, truncated: truncado }
  }

  /** La entidad más conectada: el mejor punto de partida para mirar el mapa. */
  function entidadDestacada() {
    if (!nodos.length) return null
    return nodos.reduce((mejor, n) => ((n.degree ?? 0) > (mejor.degree ?? 0) ? n : mejor)).id
  }

  return { buscar, entidad, vecinos, entidadDestacada, total: nodos.length }
}
