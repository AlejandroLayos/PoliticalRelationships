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
  bloques (01, 02…) y la lista de al lado lleva los mismos números. Ocho
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

Las vistas de red se abren en un **visor** oscuro encajado en la página, como
una lámina: es donde los nodos se iluminan al pasar por encima, y una luz sólo
se ve sobre negro. `.visor` redefine los mismos tokens, así que un componente
no necesita saber si está en papel o dentro del visor.

El lienzo de Sigma pinta con WebGL y no lee CSS: usa `COLOR_POR_ESQUEMA`
(hexadecimales del visor) y `sobreFondo`, porque además ignora el alfa de las
aristas (ver `color.js`).

## 6. Decir lo que no es

Cada lista, cada bloque, lleva su **nota** (`.nota`): lo que ese dato no
significa. En cursiva y con filete, como una nota del editor. Antes era texto
gris a pie de lista y se leía como la letra pequeña de un contrato, que es lo
contrario de lo que tiene que parecer.

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
