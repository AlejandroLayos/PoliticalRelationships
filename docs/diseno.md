# Diseño: un diario de datos con archivo

Sinapsis publica documentos oficiales que conectan dinero público con nombres.
Lo que se ve tiene que leerse como se lee la sección de datos de un periódico
serio, no como un tablero de vigilancia. La credibilidad es la mitad del
producto: un dato bien presentado y mal interpretado es una acusación falsa
(spec §12).

De ahí salen seis reglas. Si algo nuevo no cabe en ellas, se discute antes de
hacerlo.

## 1. Papel y tinta

La página es papel (`--papel`) y el texto es tinta (`--tinta`). Se separa con
filetes —reglas finas—, no con cajas. Una caja sólo cuando agrupa algo que se
pulsa entero.

Antes era un tema oscuro. Un fondo negro con nombres de empresas y cifras en
naranja dice «inteligencia», «vigilancia», «expediente»: justo lo que el
proyecto no puede insinuar.

## 2. El color es dato

Nunca decora. Tres tonos y un gris, y significan lo mismo en toda la web:

| token    | quién es                                  |
|----------|-------------------------------------------|
| `--adm`  | administración: quien paga                |
| `--emp`  | empresa o persona jurídica: quien cobra   |
| `--par`  | partido u organización                    |
| `--neutro` | el expediente, que no es un actor        |

Medidos con daltonismo simulado (Machado 2009) y CIEDE2000, todos los pares a
la vez: peor par ΔE 22,9 con deuteranopia, 17,6 con protanopia, 32,4 en visión
normal. Pasan contraste AA de texto sobre papel.

Consecuencias:

- **Un enlace es tinta subrayada**, no azul. Si fuera azul se leería como una
  empresa.
- **El orden se dice con un número, no con un color.** El mapa numera sus
  grupos (01, 02…) y la lista de al lado lleva los mismos números. Ocho
  colores para ocho grupos obligaban a casar tonos parecidos de memoria, y
  además chocaban con los tres de tipo.
- **En el flujo de una ficha, la cinta lleva el color de la contraparte**: lo
  cobrizo viene de una administración, lo azul va a una empresa. La dirección
  la dice el lado —izquierda entra, derecha sale—, que ya lo decía.
- `--sancion` (lacre) y `--aviso` (ámbar) son estados, no series: van siempre
  con su palabra al lado.

## 3. Tipografía de periódico

- **Newsreader** (serif con eje óptico) para titulares, nombres de entidad y
  cifras destacadas. Diseñada para prensa.
- **Public Sans** para interfaz y datos. Neutra y con cifras tabulares.
- **IBM Plex Mono** para lo que es referencia de archivo: sellos, números de
  expediente, NIF, números de puesto.

Alojadas con la web, no pedidas a Google Fonts: cada petición manda la IP del
visitante a un tercero, y en 2022 un tribunal alemán lo consideró una
infracción del RGPD.

## 4. Cada cifra con su sello

La procedencia no va escondida en un desplegable: es un **sello** (`.sello`),
en mono y recuadrado como el registro de entrada de un papel oficial, que dice
de qué fuente sale un dato y, cuando se puede, enlaza a la ficha pública del
expediente. Es la promesa del proyecto hecha visible.

## 5. El visor

Lo que se explora —el mapa y las conexiones— se abre en un **visor** oscuro
encajado en la página, como una lámina: es donde las cosas se iluminan al
pasar por encima, y una luz sólo se ve sobre negro. Lo que se lee —la portada
y la ficha— es papel. `.visor` redefine los mismos tokens, así que un componente
no necesita saber si está en papel o dentro del visor.

El lienzo de Sigma pinta con WebGL y no lee CSS: usa `COLOR_POR_ESQUEMA`
(hexadecimales del visor) y `sobreFondo`, porque además ignora el alfa de las
aristas (ver `color.js`).

Dentro del visor, **un expediente es un papel, no un actor**: va pequeño, gris
y sin rótulo fijo, y su título sale al pasar por encima. Los rótulos son para
los actores —quién paga, quién cobra—, que es lo que se viene a leer.

### El mapa

Es un solo dibujo con cámara (`MapaCirculos.vue`, cuenta en `mapa.js`):

- **Cada grupo es un círculo y dentro está su gente**, cada entidad del color
  de su tipo. Desde fuera ya se ve de qué está hecho un grupo.
- **El área es el dato en los dos niveles**: el valor de una entidad es su
  dinero dentro del grupo, y el círculo del grupo suma el de los suyos. Los
  grupos diminutos se dibujan con un tamaño mínimo **y con el borde a
  trazos**, para que se note que están agrandados.
- **Entrar es un viaje, no un cambio de pantalla**: la cámara vuela hasta el
  grupo (`interpolateZoom` de d3) y se sabe de dónde se viene.
- **Pasar por una entidad dibuja sus caminos** desde quien paga hasta quien
  cobra, del color de quien paga, y por ellos corre el dinero en ese sentido.
  Si se dibujan menos de los que hay, se dice.
- En táctil, el primer toque señala y enseña una tarjeta; el segundo, o su
  botón, abre la ficha. Con teclado, el foco hace de ratón y Escape sale.

### Los cargos

La sección de altos cargos es papel, no visor: se lee como una página de
nombramientos de un periódico. El cargo va en la serif, como un titular
pequeño; las fechas, en la mono, como en un registro.

La línea de tiempo de una persona va de lo primero a lo último que se ha leído
del BOE, no de su vida: lo que queda fuera no se dibuja como sabido. Un periodo
sin nombramiento entra por el borde con un degradado; uno sin cese se sale por
el otro lado punteado. Cada barra lleva el número de su periodo en la lista.
Con menos de un año de eje no se dibuja: tres semanas son una raya con una mota.
Lo que empieza o acaba fuera del eje —el escaño de un diputado desde 2023 en
un eje del BOE que arranca en 2025— también entra fundido o sale punteado: una
barra cortada en seco en el borde parecería empezar ahí.

El cobrizo de la administración para lo que es cargo público; el azul de la
empresa para lo que es sector privado: una autorización para trabajar en una
sociedad, el nombre de esa sociedad, y la etiqueta «sector privado» de una
actividad declarada al Congreso.

Lo que declara un diputado se enseña con sus palabras y en su caja: el
empleador en la serif, como la actividad de una autorización, y la
descripción y el periodo tal cual los escribió, en mayúsculas si las puso.
Nada se corrige ni se completa: es su declaración, y así se dice.

Los nombres, en orden natural en toda la página. El Congreso y la Oficina
escriben «Apellidos, Nombre» y el BOE no; la misma persona se lee igual venga
de donde venga. «Escaño en la XV legislatura» y no «Diputado»: la fuente no
dice el género, y el BOE sí lo escribe en cada cargo.

## 6. Decir lo que no es

Cada lista, cada bloque, lleva su **nota** (`.nota`): lo que ese dato no
significa. En cursiva y con filete, como una nota del editor. Antes era texto
gris a pie de lista y se leía como la letra pequeña de un contrato, que es lo
contrario de lo que tiene que parecer.

## 7. Edición de noche

Con el sistema en modo oscuro, la página pasa a papel oscuro cálido y tinta
clara (`prefers-color-scheme: dark` en `estilos.css`). No es el tablero negro
de antes: sigue siendo papel. Los tres colores de tipo toman sus tonos del
visor, que son los que dan contraste sobre oscuro (todos por encima de 5:1), y
el visor sigue siendo más oscuro que la página.

## Piezas

| clase          | para qué                                            |
|----------------|-----------------------------------------------------|
| `.antetitulo`  | lo que va encima de un título: la sección           |
| `.nota`        | lo que un dato no significa                         |
| `.sello`       | la fuente o el documento de un dato                 |
| `.puesto-num`  | el número de orden en una lista                     |
| `.boton`       | acción: recuadrado en tinta, sin relleno            |
| `.punto-tipo`  | el punto de color de un tipo de actor               |
| `.visor`       | contenedor oscuro para las vistas de red            |
