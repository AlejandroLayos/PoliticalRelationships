import { createApp } from 'vue'
import App from './App.vue'

// Fuentes alojadas con la web, no pedidas a Google Fonts: cada petición a sus
// servidores manda la IP del visitante a un tercero, y en 2022 un tribunal
// alemán lo consideró una infracción del RGPD. Aquí se publican datos que
// conectan dinero público con nombres; no se empieza regalando visitas.
//
// Newsreader con eje óptico: el titular de la portada mide sesenta píxeles y
// el corte de texto, a ese tamaño, se ve blando. La cursiva sólo en peso, que
// pesa la mitad y sólo se usa en las notas.
import '@fontsource-variable/newsreader/opsz.css'
import '@fontsource-variable/newsreader/wght-italic.css'
import '@fontsource-variable/public-sans/wght.css'
import '@fontsource/ibm-plex-mono/400.css'
import '@fontsource/ibm-plex-mono/500.css'

import './estilos.css'

createApp(App).mount('#app')
