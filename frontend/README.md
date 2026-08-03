# Frontend de Sinapsis

Vue 3 + Vite + [Sigma.js](https://www.sigmajs.org/) y
[graphology](https://graphology.github.io/), con layout ForceAtlas2. Es lo que
produce el aspecto de red orgánica.

## Cómo lee los datos

```
VITE_API_URL=https://api.tu-dominio.es   # apunta al backend Go
```

- **Con `VITE_API_URL`**: consume `/v1/search`, `/v1/entity/{id}` y
  `/v1/entity/{id}/neighbors`.
- **Sin ella, o si la API no responde**: cae al conjunto de
  `src/demo.js` y **lo anuncia con una banda permanente**. Los datos de ese
  fichero son inventados y los nombres deliberadamente ficticios
  («Constructora Ficticia SL»). Publicar un mapa de dinero público con datos
  falsos sin decirlo sería lo contrario de lo que este proyecto pretende.

## Cómo se navega

Se busca una entidad y desde ahí se expande el vecindario: **clic** para ver la
ficha, **doble clic** para expandir la red desde ese nodo. No hay «ver el grafo
entero», y no es un descuido — una maraña de cien mil nodos es espectacular en
una captura e inútil para investigar.

## Cómo se dibuja la incertidumbre

- El **grosor y el color** de una arista dependen de su `confidence`.
- Las aristas con `status = 'inferred'` van finas y en ámbar, distintas de las
  afirmadas por la fuente.
- El panel lateral muestra **siempre** el estado y la confianza de cada
  conexión, no sólo cuando son malos.
- El tamaño del nodo crece con su grado: lo muy conectado se ve sin buscarlo.

## Desarrollo

```bash
npm install
npm run dev      # servidor de desarrollo
npm run test     # vitest
npm run build    # a dist/
```

## Despliegue en Vercel

El `vercel.json` de la raíz del repositorio ya declara el build y el directorio
de salida, así que **no hace falta tocar el panel de Vercel**. Define
`VITE_API_URL` en las variables de entorno del proyecto para conectar datos
reales; sin ella el despliegue funciona igual, en modo demostración.

El resto de la pila (Postgres, Neo4j, Redis, la API y el worker) **no puede ir
en Vercel**: son servicios con estado y procesos largos. Ver `docs/spec.md §14`.
