/**
 * Prueba de humo: los diez caminos por los que pasa la gente.
 *
 * No comprueba cifras —de eso se encargan los tests de `src`, que corren en
 * la CI— sino que la web siga siendo NAVEGABLE: que la portada liste, que
 * pulsar una fila abra una ficha, que el mapa dibuje, que se pueda entrar en
 * un grupo y volver, que el botón de atrás del navegador funcione y que el
 * teclado sirva para buscar. Eso no se puede probar sin navegador, y son
 * justamente las cosas que se rompen en silencio: `?v=mapa` dejó de llevar al
 * mapa durante semanas y ningún test lo dijo, porque la lógica vivía dentro
 * de un `<script setup>` y no se exportaba nada.
 *
 * Vigila también la consola. Un «Container has no width» de Sigma no rompe
 * ninguna comprobación y deja un lienzo vacío al volver a una vista.
 *
 * ## No está en la CI, y es a propósito
 *
 * Levantar un navegador y esperar a que el mapa calcule sus núcleos son diez
 * segundos por paso: en la CI sería lento y, sobre todo, intermitente, y una
 * CI que falla a veces no la mira nadie. Se ejecuta a mano, con:
 *
 *     cd frontend && npm run humo

 * Si la máquina no trae un Chromium que Playwright encuentre, se le dice
 * dónde está con `SINAPSIS_NAVEGADOR=/ruta/a/chromium`.
 *
 * que compila, levanta la vista previa y la apaga al terminar. Si algún día
 * la instantánea de datos deja de tardar, esto se puede mover a la CI.
 */
// `playwright-core` y no `playwright`: el segundo se descarga trescientos
// megas de navegadores al instalar, y esto no corre en la CI. Aquí se usa el
// Chromium que ya tenga la máquina.
import { chromium } from 'playwright-core'

const URL = process.env.SINAPSIS_URL ?? 'http://127.0.0.1:4190/'
/** Lo que tarda el mapa en agrupar cuatro mil nodos, con holgura. */
const ESPERA_MAPA = 12000

const fallos = []
const consola = []

async function paso(nombre, fn) {
  try {
    await fn()
    console.log('  ✓', nombre)
  } catch (e) {
    fallos.push(nombre)
    console.log('  ✗', nombre, '—', String(e.message ?? e).split('\n')[0].slice(0, 140))
  }
}

/**
 * Abre el Chromium que haya.
 *
 * Sin navegador propio hay que decir dónde está el del sistema. El mensaje
 * importa: «Executable doesn't exist at …» no le dice a nadie qué hacer.
 */
async function abrirNavegador() {
  const suyo = process.env.SINAPSIS_NAVEGADOR
  try {
    return await chromium.launch(suyo ? { executablePath: suyo } : {})
  } catch (e) {
    console.error(
      [
        'No se ha podido abrir Chromium.',
        String(e.message ?? e).split('\n')[0],
        '',
        'Dile dónde está el tuyo:',
        '  SINAPSIS_NAVEGADOR=/ruta/a/chromium npm run humo',
        '',
        'O instala uno para Playwright:',
        '  npx playwright install chromium',
      ].join('\n'),
    )
    process.exit(2)
  }
}

const navegador = await abrirNavegador()
const pagina = await navegador.newPage({ viewport: { width: 1440, height: 900 } })
pagina.on('pageerror', (e) => consola.push(`error de página: ${e.message}`))
pagina.on('console', (m) => {
  // Las llamadas a `/api/*` fallan a propósito cuando se sirve la
  // instantánea estática: es el respaldo funcionando, no un fallo.
  const t = m.text()
  if (m.type() === 'error' && !t.includes('status of 404')) consola.push(t.slice(0, 160))
})

console.log(`Humo sobre ${URL}`)
await pagina.goto(URL, { waitUntil: 'networkidle' })
await pagina.waitForTimeout(ESPERA_MAPA)

await paso('la portada lista los rankings con sus cifras', async () => {
  const texto = await pagina.innerText('body')
  if (!texto.includes('Quién reparte más dinero público')) throw new Error('sin rankings')
  if (!/MM €|M €/.test(texto)) throw new Error('sin cifras')
})

await paso('desplegar una lista enseña más filas', async () => {
  const antes = await pagina.locator('.ranking li').count()
  await pagina.click('text=/Ver las \\d+ de la lista/')
  await pagina.waitForTimeout(300)
  const despues = await pagina.locator('.ranking li').count()
  if (despues <= antes) throw new Error(`${antes} → ${despues}`)
})

await paso('pulsar una fila abre su ficha', async () => {
  await pagina.click('.ranking button.fila')
  await pagina.waitForTimeout(6000)
  if (!(await pagina.innerText('body')).includes('Copiar enlace')) throw new Error('sin ficha')
})

await paso('la dirección lleva la clave estable, no el UUID', async () => {
  const u = decodeURIComponent(pagina.url())
  if (!/\?e=[a-z]+:/.test(u)) throw new Error(u)
})

await paso('conexiones dibuja el vecindario', async () => {
  await pagina.click('text=Ver sus conexiones')
  await pagina.waitForTimeout(9000)
  // Por el título de la lista del panel, no por el texto en mayúsculas: el
  // rótulo dejó de ir en versalitas con el rediseño y esto falló sin que
  // hubiera fallado nada.
  if (!(await pagina.locator('.panel h3', { hasText: 'Conexiones' }).count())) throw new Error('sin panel')
})

await paso('el mapa del dinero dibuja sus grupos', async () => {
  await pagina.click('text=Mapa del dinero')
  await pagina.waitForTimeout(ESPERA_MAPA)
  const n = await pagina.locator('svg .grupo').count()
  if (n < 5) throw new Error(`${n} grupos`)
})

// Un círculo que se ve y no dice cuál es no lleva a su fila de la lista.
await paso('todo grupo que se ve lleva su número', async () => {
  const { visibles, rotulos } = await pagina.evaluate(() => ({
    visibles: [...document.querySelectorAll('svg .grupo .contorno')].filter(
      (c) => c.getBoundingClientRect().width >= 22,
    ).length,
    rotulos: document.querySelectorAll('.rotulo .numero').length,
  }))
  if (rotulos < visibles) throw new Error(`${visibles - rotulos} grupos sin número`)
})

await paso('entrar en un grupo enseña a los de dentro', async () => {
  await pagina.locator('svg .grupo').first().click()
  await pagina.waitForTimeout(2000)
  if (!(await pagina.innerText('body')).includes('Todos los grupos')) throw new Error('no entró')
  const n = await pagina.locator('svg .grupo.dentro .miembro').count()
  if (n < 5) throw new Error(`${n} entidades dentro`)
})

await paso('pasar por una entidad dibuja sus caminos', async () => {
  const cajas = await pagina.locator('svg .grupo.dentro .miembro').evaluateAll((els) =>
    els.map((e) => e.getBoundingClientRect()).map((r) => ({ x: r.x, y: r.y, w: r.width, h: r.height })),
  )
  const mayor = cajas.sort((a, b) => b.w * b.h - a.w * a.h)[0]
  await pagina.mouse.move(mayor.x + mayor.w / 2, mayor.y + mayor.h / 2)
  await pagina.waitForTimeout(800)
  if (!(await pagina.locator('.camino').count())) throw new Error('sin caminos')
  await pagina.mouse.move(5, 5)
})

await paso('el grupo también se ve como red', async () => {
  await pagina.click('.modo button:has-text("Red")')
  await pagina.waitForTimeout(ESPERA_MAPA)
  if (!(await pagina.locator('canvas').count())) throw new Error('sin lienzo')
  await pagina.click('.modo button:has-text("Círculos")')
  await pagina.waitForTimeout(800)
})

await paso('volver a todos los grupos', async () => {
  await pagina.click('text=Todos los grupos')
  await pagina.waitForTimeout(2000)
  if (await pagina.locator('svg .grupo.dentro').count()) throw new Error('sigue dentro')
  if ((await pagina.locator('svg .grupo').count()) < 5) throw new Error('no volvió')
})

await paso('el botón de atrás del navegador retrocede', async () => {
  await pagina.goBack()
  await pagina.waitForTimeout(4000)
  if (pagina.url().includes('v=mapa')) throw new Error(`no retrocedió: ${pagina.url()}`)
})

await paso('buscar y elegir con el teclado', async () => {
  await pagina.click('text=← Portada').catch(() => {})
  await pagina.waitForTimeout(1500)
  await pagina.fill('input', 'metro de madrid')
  await pagina.waitForTimeout(2500)
  await pagina.keyboard.press('ArrowDown')
  await pagina.keyboard.press('Enter')
  await pagina.waitForTimeout(6000)
  if (!(await pagina.innerText('body')).includes('Copiar enlace')) throw new Error('no abrió ficha')
})

await paso('un enlace directo a un mapa lleva al mapa', async () => {
  await pagina.goto(`${URL}?v=mapa`, { waitUntil: 'networkidle' })
  await pagina.waitForTimeout(ESPERA_MAPA)
  if ((await pagina.locator('svg .grupo').count()) < 5) throw new Error('cayó en la portada')
})

await paso('el botón de la portada abre el mapa', async () => {
  await pagina.goto(URL, { waitUntil: 'networkidle' })
  await pagina.waitForTimeout(ESPERA_MAPA)
  await pagina.click('text=Abrir el mapa del dinero')
  await pagina.waitForTimeout(3000)
  if ((await pagina.locator('svg .grupo').count()) < 5) throw new Error('no abrió el mapa')
})

// La edición de una comunidad. Sólo si el volcado trae comunidades: antes
// de la primera ingesta con `territorio.py` no las trae, y el selector no
// sale —que es lo correcto—.
await paso('elegir una comunidad cambia la portada y la dirección', async () => {
  await pagina.goto(URL, { waitUntil: 'networkidle' })
  await pagina.waitForTimeout(2000)
  const selector = pagina.locator('.selector-edicion select')
  if (!(await selector.count())) {
    console.log('    (el volcado no trae comunidades todavía: no hay edición que probar)')
    return
  }
  const opciones = await selector.locator('option').allTextContents()
  const comunidad = opciones.find((o) => o !== 'España')
  await selector.selectOption(comunidad)
  await pagina.waitForTimeout(3000)
  if (!(await pagina.locator('h1.titular').innerText()).includes(comunidad)) throw new Error('titular sin comunidad')
  if (!decodeURIComponent(pagina.url()).includes(`t=${comunidad}`)) throw new Error(`dirección: ${pagina.url()}`)
  await selector.selectOption('')
  await pagina.waitForTimeout(1000)
})

// Aena no está en la base. Por subcadena salía una asociación de Baena como
// primer resultado, e Intro llevaba a su ficha como si fuera lo buscado.
await paso('buscar lo que no está dice que no está', async () => {
  await pagina.fill('.buscador input', 'Aena')
  await pagina.waitForTimeout(2500)
  if (!(await pagina.innerText('body')).includes('Nada con «Aena»')) throw new Error('no lo dijo')
})

await navegador.close()

if (consola.length) {
  console.log('\nLa consola del navegador se ha quejado:')
  for (const linea of [...new Set(consola)].slice(0, 8)) console.log('  ·', linea)
}
const mal = fallos.length + consola.length
console.log(mal ? `\n${mal} problema(s).` : '\nTodo en pie.')
process.exit(mal ? 1 : 0)
