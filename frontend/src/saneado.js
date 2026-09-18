/**
 * Red de seguridad sobre la instantánea publicada.
 *
 * La regla de verdad vive en la ingesta (ver `docs/adr/0005-importes-que-no-se-publican.md`):
 * cuando un importe no es atribuible a quien está al otro lado de la arista,
 * no se publica la cifra. Esto la vuelve a aplicar al cargar el grafo.
 *
 * No es desconfianza del conector, es que **la instantánea y el código se
 * despliegan por separado**. El fichero `grafo.json` lo regenera un workflow;
 * la web la despliega Vercel en cada push. Entre que se arregla el conector y
 * que se publica una instantánea nueva hay una ventana —esta vez fueron
 * cuarenta minutos— en la que el código nuevo sirve datos viejos. Y lo que se
 * veía en esa ventana era «INDRA recibió 908 millones de euros», con nombre y
 * apellidos, en la portada.
 *
 * Con esto cualquier instantánea se lee bien, incluidas las que ya están
 * commiteadas en el histórico del repositorio.
 *
 * Sobre una instantánea generada por la ingesta corregida no hace nada: esas
 * aristas ya vienen sin `amount`. Es idempotente a propósito.
 *
 * ## Lo que se puede rehacer aquí y lo que no
 *
 * Las dos reglas del ADR 0005 se pueden comprobar con lo que el volcado ya
 * lleva: el presupuesto viaja en las propiedades del contrato, y para los
 * importes compartidos basta con mirar las adjudicaciones del mismo contrato.
 * Cualquier regla futura que dependa de datos que el volcado no publica, no.
 */

/** Ver ADR 0005. Mismos umbrales que la ingesta, a propósito. */
const VECES_PRESUPUESTO_INVEROSIMIL = 10

function comoNumero(v) {
  if (v === undefined || v === null || v === '') return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

/** Clave de agrupación. El id es un UUID y el importe un número: `|` no aparece en ninguno. */
function clave(a) {
  return `${a.source}|${a.amount}`
}

/**
 * Devuelve el grafo con las cifras no atribuibles retiradas.
 *
 * No muta la entrada y no copia lo que no cambia: devuelve aristas nuevas sólo
 * para las afectadas, y el mismo objeto de entrada si no hay ninguna.
 */
export function sanearImportes(datos) {
  const aristas = datos?.edges ?? []
  const nodos = datos?.nodes ?? []
  if (!aristas.length) return datos

  const presupuesto = new Map()
  for (const n of nodos) {
    if (n.schema !== 'Contract') continue
    const p = comoNumero(n.properties?.budgetAmount)
    if (p !== null && p > 0) presupuesto.set(n.id, p)
  }

  // Cuántas adjudicaciones del mismo contrato llevan exactamente el mismo
  // importe. Dos ya bastan: desde fuera no hay manera de distinguir dos lotes
  // de idéntico valor de un acuerdo marco repartido entre sus adjudicatarios.
  const repeticiones = new Map()
  for (const a of aristas) {
    if (a.schema !== 'ContractAward' || !a.amount) continue
    const k = clave(a)
    repeticiones.set(k, (repeticiones.get(k) ?? 0) + 1)
  }

  let cambiadas = 0
  const saneadas = aristas.map((a) => {
    if (a.schema !== 'ContractAward' || !a.amount) return a

    const veces = repeticiones.get(clave(a)) ?? 0
    if (veces > 1) {
      cambiadas += 1
      return sinCifra(a, {
        importeCompartido: String(a.amount),
        adjudicatariosQueComparten: veces,
        motivoImporteDudoso:
          `el mismo importe figura en ${veces} adjudicaciones de este contrato:` +
          ' es el valor del acuerdo marco o del lote, no lo que recibe cada adjudicatario',
      })
    }

    const presu = presupuesto.get(a.source)
    const importe = comoNumero(a.amount)
    if (presu && importe !== null && importe > presu * VECES_PRESUPUESTO_INVEROSIMIL) {
      cambiadas += 1
      return sinCifra(a, {
        importeSinInterpretar: String(a.amount),
        motivoImporteDudoso:
          `supera en más de ${VECES_PRESUPUESTO_INVEROSIMIL} veces el presupuesto` +
          ` base de licitación (${presu})`,
      })
    }

    return a
  })

  if (!cambiadas) return datos
  return { ...datos, edges: saneadas, importesSaneados: cambiadas }
}

function sinCifra(a, motivo) {
  const copia = { ...a, properties: { ...(a.properties ?? {}), ...motivo } }
  delete copia.amount
  // La confianza no puede ser mayor que la de la afirmación más floja que la
  // sostiene, y aquí la cifra ya no se sostiene.
  copia.confidence = Math.min(copia.confidence ?? 1, 0.5)
  return copia
}
