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
  if (!(await pagina.innerText('body')).includes('CONEXIONES')) throw new Error('sin panel')
})

await paso('el mapa del dinero dibuja sus bloques', async () => {
  await pagina.click('text=Mapa del dinero')
  await pagina.waitForTimeout(ESPERA_MAPA)
  const n = await pagina.locator('.bloque').count()
  if (n < 5) throw new Error(`${n} bloques`)
})

await paso('todo bloque dibujado lleva nombre', async () => {
  const sinNombre = await pagina.evaluate(() =>
    [...document.querySelectorAll('.bloque')].filter((b) => !b.querySelector('.nombre')).length,
  )
  if (sinNombre) throw new Error(`${sinNombre} bloques mudos`)
})

await paso('entrar en un grupo dibuja su red', async () => {
  await pagina.locator('.bloque').first().click()
  await pagina.waitForTimeout(ESPERA_MAPA)
  if (!(await pagina.innerText('body')).includes('Todos los grupos')) throw new Error('no entró')
  if (!(await pagina.locator('canvas').count())) throw new Error('sin lienzo')
})

await paso('volver a todos los grupos', async () => {
  await pagina.click('text=Todos los grupos')
  await pagina.waitForTimeout(3000)
  if ((await pagina.locator('.bloque').count()) < 5) throw new Error('no volvió')
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
  if ((await pagina.locator('.bloque').count()) < 5) throw new Error('cayó en la portada')
})

await navegador.close()

if (consola.length) {
  console.log('\nLa consola del navegador se ha quejado:')
  for (const linea of [...new Set(consola)].slice(0, 8)) console.log('  ·', linea)
}
const mal = fallos.length + consola.length
console.log(mal ? `\n${mal} problema(s).` : '\nTodo en pie.')
process.exit(mal ? 1 : 0)
