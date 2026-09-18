"""Retira del historial de git los nombres y DNI de personas físicas.

NO se ejecuta solo y NO se ejecuta dos veces sin pensarlo: reescribe el
historial del repositorio, cambia todos los SHA a partir del commit más
antiguo afectado y obliga a un `push --force`. Cualquiera que tenga un clon
tendrá que rehacerlo.

## Qué hay que borrar y por qué

Entre el 3/8/2026 y el 18/9/2026 la instantánea diaria publicó personas
físicas con nombre, apellidos y DNI. La corrección de los conectores —agregar
a los particulares en un nodo anónimo— existía desde el primer día, pero vivía
en una rama que no se desplegaba (ver «Detalles que muerden» en CLAUDE.md).

El rastro que queda hoy son **dos blobs** de
`frontend/public/datos/grafo.json`, con 27 particulares cada uno:

    37b85a142b1bf2f8fb5af656060c8bbdde51f079   (1,7 MB)
    8dba112694b4f28b7959d213f602e22d24057998   (2,2 MB)

alcanzables desde `main` y desde la rama de trabajo. El resto del historial
está limpio: los ficheros de prueba usan datos sintéticos («NOMBRE APELLIDO
APELLIDO», «12345678Z») y ningún otro blob contiene un patrón de DNI.

## Qué hace exactamente

Reescribe esos blobs —y cualquier otro volcado que aparezca con nodos
`Person`, por si acaso— quitando:

- los nodos de esquema `Person`, con su `caption`, su `nif` y sus propiedades;
- las aristas que cuelgan de ellos, porque el par (organismo, importe) seguiría
  señalando a la persona aunque su nombre no estuviera;
- sus entradas de procedencia, donde el extracto del documento original lleva
  el nombre dentro.

Deja el fichero como JSON válido y le añade una marca `redactado` que dice
cuántas entidades se retiraron y por qué. No se borra el fichero ni el commit:
el historial sigue contando lo que pasó, sin los datos personales.

## Cómo se usa

    pip install git-filter-repo
    python3 scripts/redactar_particulares_del_historico.py --comprobar   # sólo mira
    python3 scripts/redactar_particulares_del_historico.py --reescribir  # reescribe

`--reescribir` pide confirmación, guarda la URL del remoto antes de que
filter-repo la quite, comprueba el resultado y escribe al final las órdenes
exactas de `push --force` que faltan. No empuja nada por su cuenta.

## Esto NO termina con el push --force

**GitHub no borra las refs de los pull request.** `refs/pull/1/head` apunta a
`8a5613e`, cuyos antepasados incluyen los dos commits con datos personales, y
un `push --force` a las ramas no la toca: los nombres y los DNI se siguen
pudiendo descargar desde ahí.

Tampoco desaparecen los commits sueltos, que GitHub sigue sirviendo por su SHA
en la web y en la API aunque ninguna rama los alcance.

Las dos cosas sólo las arregla el soporte de GitHub. Hay que abrirles un
ticket pidiendo que purguen las refs de pull request y las cachés del
repositorio, citando los SHA. Sin ese paso el borrado está a medias, y es la
mitad que importa.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ESQUEMA_PERSONAL = "Person"

# DNI: ocho dígitos y letra. NIE: X/Y/Z, siete dígitos y letra. Los dos
# identifican a UNA persona, aunque cuelguen de la ficha de una empresa.
#
# Hizo falta después de la primera reescritura: quitar los nodos `Person`
# dejó limpio lo que estaba clasificado como persona, pero en el historial
# quedaba una UTE —`Company`, con forma societaria explícita— cuyo NIF era el
# DNI de uno de sus socios. La regla de «esto es una empresa» funcionaba bien
# y aun así seguía habiendo un DNI publicado.
_IDENTIFICADOR_PERSONAL = re.compile(r"^(?:[0-9]{8}|[XYZxyz][0-9]{7})[A-Za-z]$")


def es_identificador_personal(nif: str | None) -> bool:
    return bool(nif) and bool(_IDENTIFICADOR_PERSONAL.match(nif.strip()))
# Los DOS ficheros que se publican. Mirar sólo el grafo dejó el índice entero
# sin filtrar, con un NIE dentro.
RUTAS = ("frontend/public/datos/grafo.json", "frontend/public/datos/indice.json")

# Prefiltro barato antes de parsear JSON de varios megas. Es a propósito laxo:
# los volcados de agosto de 2026 se serializaban compactos —`"schema":"Person"`,
# sin espacio— y los de septiembre con separadores por defecto. Buscar la forma
# con espacio no encontraba nada y el ensayo decía «no hay nada que borrar»
# sobre dos blobs con 27 personas cada uno. Se busca la palabra suelta y decide
# el parseo, que es lo único que no depende del formato.
PISTA = b'"Person"'

# Residuos confirmados a mano, identificados por el SHA-256 de su `caption`.
#
# Va por hash y no por el texto a propósito: una lista de qué borrar por
# motivos de datos personales no puede ser, ella misma, otra copia de esos
# datos personales en el repositorio.
#
# El que hay es una UTE cuyo nombre oficial incluye el nombre y los dos
# apellidos de sus dos socios. Tenía un DNI por NIF, que es lo que la delataba,
# pero una redacción anterior le quitó el NIF y dejó la ficha: con la pista
# borrada quedó indistinguible de una empresa normal, y los nombres dentro.
#
# Tampoco servía cruzar por id con el índice, donde el NIF sí sobrevivía: los
# UUID se regeneran en cada ingesta, así que el id de un volcado de agosto no
# es el de un índice de septiembre.
#
# Cuando una redacción parcial ha borrado su propia pista, lo único que queda
# es una lista explícita y revisada. No es una heurística: es un caso
# comprobado uno a uno.
HASHES_CAPTION_PERSONAL = frozenset(
    {"ea0d7e13e63b3f03cdc0fd7da4713589388e75463c0503e923ebef6da62126cb"}
)


def _caption_confirmado_personal(caption: str | None) -> bool:
    if not caption:
        return False
    return hashlib.sha256(caption.encode("utf-8")).hexdigest() in HASHES_CAPTION_PERSONAL


MOTIVO = (
    "se retiraron personas físicas (nombre, DNI y procedencia) del historial:"
    " minimización de datos personales, RGPD. Ver docs/spec.md §12."
)


def redactar(datos: dict, ids_extra: set[str] | None = None) -> tuple[dict, int]:
    """Devuelve el volcado sin datos personales y cuántas entidades se fueron.

    Sirve para los DOS ficheros que se publican, que tienen forma distinta: el
    grafo guarda las entidades en `nodes` y el índice en `entidades`. La
    primera versión sólo miraba `nodes`, así que el índice pasó entero por el
    filtro sin que nadie lo notara — con cuatro identificadores personales
    dentro, y un DNI que en el grafo ya se había retirado.

    `ids_extra` son los id que el historial entero ya delató como personales,
    aunque en ESTE volcado no se note: ver `ids_personales()`.

    ## Por qué se va la entidad entera y no sólo el identificador

    La versión anterior le quitaba el NIF a la ficha y la dejaba publicada. No
    basta: en el historial había una UTE identificada por el DNI de un socio
    cuyo NOMBRE eran los nombres y apellidos de los dos socios. Quitado el DNI,
    seguían publicados los nombres.

    Detectar qué parte de un nombre es el de una persona es justo la heurística
    frágil que este proyecto evita en todas partes. Pero hay una señal
    objetiva y no hace falta adivinar nada: si la fuente identificó a esa parte
    contratante con un DNI o un NIE, es una persona física a efectos de
    publicación, y aquí sólo se publican personas jurídicas (spec §12).

    Se pierde alguna empresa real cuyo NIF vino mal escrito. Es un hueco en una
    instantánea vieja que nadie lee, y la regla del proyecto es explícita sobre
    hacia qué lado equivocarse: un falso positivo es una acusación falsa, un
    falso negativo es sólo un hueco.
    """
    clave = "nodes" if "nodes" in datos else ("entidades" if "entidades" in datos else None)
    if clave is None:
        return datos, 0
    entidades = datos.get(clave) or []

    objetivo = ids_extra or set()
    fuera = {
        e["id"]
        for e in entidades
        if e.get("schema") == ESQUEMA_PERSONAL
        or es_identificador_personal(e.get("nif"))
        or _caption_confirmado_personal(e.get("caption"))
        or e["id"] in objetivo
    }
    if not fuera:
        return datos, 0

    datos[clave] = [e for e in entidades if e["id"] not in fuera]
    if "edges" in datos:
        datos["edges"] = [
            a
            for a in (datos.get("edges") or [])
            if a.get("source") not in fuera and a.get("target") not in fuera
        ]
    procedencia = datos.get("provenance")
    if isinstance(procedencia, dict):
        datos["provenance"] = {k: v for k, v in procedencia.items() if k not in fuera}

    datos["redactado"] = {"entidades_retiradas": len(fuera), "motivo": MOTIVO}
    return datos, len(fuera)


def blob_callback(blob, metadata):  # (metadata: firma que exige git-filter-repo)
    """Lo llama git-filter-repo con cada blob del historial."""
    if b'"nodes"' not in blob.data:
        return
    try:
        datos = json.loads(blob.data)
    except Exception:
        return
    datos, cuantas = redactar(datos)
    if not cuantas:
        return
    blob.data = json.dumps(datos, ensure_ascii=False).encode("utf-8")


def _volcados_del_historial() -> list[tuple[str, bytes]]:
    """Todos los blobs de los ficheros publicados, con su contenido."""
    salida = subprocess.run(
        ["git", "rev-list", "--all", "--objects", "--", *RUTAS],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    vistos: dict[str, None] = {}
    for linea in salida.splitlines():
        partes = linea.split(maxsplit=1)
        if len(partes) == 2:
            vistos.setdefault(partes[0], None)

    volcados = []
    for sha in vistos:
        tipo = subprocess.run(
            ["git", "cat-file", "-t", sha], capture_output=True, text=True
        ).stdout.strip()
        if tipo != "blob":
            continue
        crudo = subprocess.run(["git", "cat-file", "-p", sha], capture_output=True).stdout
        if b'"nodes"' in crudo or b'"entidades"' in crudo:
            volcados.append((sha, crudo))
    return volcados


def ids_personales() -> set[str]:
    """Los id de entidad que EN ALGÚN volcado resultaron ser de una persona.

    Hace falta mirar el historial entero antes de tocar nada, y no volcado a
    volcado, porque la señal puede estar en un fichero y el dato personal en
    otro.

    Pasó de verdad: una pasada anterior le quitó el DNI a esa UTE en el
    grafo y dejó la ficha publicada.
    Con el DNI fuera, esa ficha quedó indistinguible de una empresa normal —y
    con los nombres de los dos socios todavía en el nombre—. La señal seguía
    existiendo, pero en el índice, que es otro fichero.

    El id de la entidad sí es estable entre ficheros y entre reescrituras. Se
    recogen aquí y luego se retiran de todas partes.
    """
    ids: set[str] = set()
    for _sha, crudo in _volcados_del_historial():
        try:
            datos = json.loads(crudo)
        except Exception:
            continue
        for e in datos.get("nodes") or datos.get("entidades") or []:
            if (
                e.get("schema") == ESQUEMA_PERSONAL
                or es_identificador_personal(e.get("nif"))
                or _caption_confirmado_personal(e.get("caption"))
            ):
                ids.add(e["id"])
    return ids


def _blobs_afectados() -> list[tuple[str, int, int]]:
    objetivo = ids_personales()
    afectados = []
    for sha, crudo in _volcados_del_historial():
        try:
            datos = json.loads(crudo)
        except Exception:
            continue
        entidades = datos.get("nodes") or datos.get("entidades") or []
        personas = [n for n in entidades if n.get("schema") == ESQUEMA_PERSONAL]
        otras = [
            n
            for n in entidades
            if n.get("schema") != ESQUEMA_PERSONAL
            and (n["id"] in objetivo or _caption_confirmado_personal(n.get("caption")))
        ]
        if personas or otras:
            afectados.append((sha, len(personas), len(otras)))
    return afectados


def _texto_pendiente() -> list[str]:
    """Patrones de texto que todavía casan en algún sitio del repositorio.

    La comprobación miraba sólo las entidades dentro de los volcados, así que
    decía «limpio» mientras quedaban nombres en el texto de los ficheros y en
    los mensajes de commit. Una comprobación que no cubre lo mismo que el
    borrado no sirve para autorizar un empujón irreversible.
    """
    pendientes = []
    for linea in SUSTITUCIONES_TEXTO:
        patron = linea.split("==>")[0]
        if not patron.startswith("regex:"):
            continue
        rx = re.compile(patron[len("regex:") :])

        mensajes = subprocess.run(
            ["git", "log", "--all", "--format=%B"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        if rx.search(mensajes):
            pendientes.append(f"{patron} (en mensajes de commit)")
            continue

        for _sha, crudo in _todos_los_blobs_de_texto():
            try:
                if rx.search(crudo.decode("utf-8", errors="ignore")):
                    pendientes.append(f"{patron} (en el contenido de un fichero)")
                    break
            except Exception:
                continue
    return pendientes


def _todos_los_blobs_de_texto() -> list[tuple[str, bytes]]:
    """Blobs de ficheros de texto del historial. Acotado a lo que puede llevar prosa."""
    salida = subprocess.run(
        ["git", "rev-list", "--all", "--objects"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    interesantes = (".py", ".md", ".yml", ".yaml", ".json", ".txt", ".sql", ".vue", ".js")
    fuera = []
    for linea in salida.splitlines():
        partes = linea.split(maxsplit=1)
        if len(partes) != 2 or not partes[1].endswith(interesantes):
            continue
        sha = partes[0]
        if subprocess.run(
            ["git", "cat-file", "-t", sha], capture_output=True, text=True
        ).stdout.strip() != "blob":
            continue
        crudo = subprocess.run(["git", "cat-file", "-p", sha], capture_output=True).stdout
        fuera.append((sha, crudo))
    return fuera


def comprobar() -> int:
    """Informa de qué hay que retirar. Sale con 1 si encuentra algo.

    No imprime ningún nombre ni ningún número: el informe de un problema de
    datos personales no puede ser otra copia de los datos personales.
    """
    afectados = _blobs_afectados()
    pendientes = _texto_pendiente()

    if not afectados and not pendientes:
        print("No queda ningún dato personal en el historial.")
        return 0

    if pendientes:
        print("Texto pendiente de sustituir:")
        for p in pendientes:
            print(f"  {p}")
        print()

    if not afectados:
        return 1

    print(f"{len(afectados)} blob(s) con datos personales:\n")
    print("  blob                                      fichas   identificadores")
    print("                                          personales  en otras fichas")
    fichas = identificadores = 0
    for sha, n_personas, n_dni in afectados:
        fichas += n_personas
        identificadores += n_dni
        print(f"  {sha}  {n_personas:>8}   {n_dni:>13}")
    print(f"\nFichas de esquema personal: {fichas}")
    print(f"Fichas identificadas con un DNI o un NIE: {identificadores}")
    print("Se retiran todas: si la fuente identificó a esa parte contratante con")
    print("un identificador personal, es una persona física a efectos de publicar.")
    print("\nLos commits que los contienen NO se borran: se reescribe su contenido.")
    return 1


def _remotos() -> dict[str, str]:
    """La URL de cada remoto. filter-repo los quita, así que se apuntan antes."""
    salida = subprocess.run(
        ["git", "remote", "-v"], capture_output=True, text=True, check=False
    ).stdout
    remotos = {}
    for linea in salida.splitlines():
        partes = linea.split()
        if len(partes) >= 2:
            remotos.setdefault(partes[0], partes[1])
    return remotos


def _ramas_locales() -> list[str]:
    salida = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname:short)", "refs/heads/"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return [r for r in salida.split() if r]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--comprobar", action="store_true", help="sólo informa, no toca nada")
    ap.add_argument("--reescribir", action="store_true", help="reescribe el historial")
    ap.add_argument("--si", action="store_true", help="no preguntar (para automatizar)")
    args = ap.parse_args()

    if args.comprobar or not args.reescribir:
        return comprobar()

    try:
        import git_filter_repo  # noqa: F401
    except ImportError:
        print("Falta git-filter-repo:  pip install git-filter-repo", file=sys.stderr)
        return 2

    afectados = _blobs_afectados()
    # El corte de «no hay nada que hacer» tiene que cubrir TODO lo que el
    # borrado hace, no sólo una parte.
    #
    # Miraba únicamente las entidades dentro de los volcados. Cuando lo que
    # quedaba eran nombres en el texto de los ficheros y en los mensajes de
    # commit, decía «no hay nada que reescribir», salía con 0, y filter-repo
    # —que es quien aplica las sustituciones— no llegaba a ejecutarse. El job
    # terminaba en verde sin haber tocado nada.
    #
    # Con sustituciones configuradas se ejecuta siempre. Si no casa ninguna,
    # filter-repo reconstruye los mismos commits y el resultado es idéntico:
    # no cuesta nada y no puede dejarse trabajo sin hacer.
    if not afectados and not SUSTITUCIONES_TEXTO:
        print("No hay nada que reescribir.")
        return 0
    if not afectados:
        print("Sin entidades que retirar; quedan las sustituciones de texto.")

    remotos = _remotos()
    ramas = _ramas_locales()

    print("Se va a REESCRIBIR el historial de este repositorio.\n")
    comprobar()
    print("\nConsecuencias:")
    print("  · Cambian TODOS los SHA a partir del commit más antiguo afectado.")
    print("  · Hace falta `push --force`, y quien tenga un clon tendrá que rehacerlo.")
    print(f"  · Ramas locales que se reescriben: {', '.join(ramas) or 'ninguna'}")
    print(f"  · Remotos apuntados para después: {remotos or 'ninguno'}")
    if not args.si:
        try:
            if input("\n¿Seguir? escribe «si»: ").strip().lower() not in {"si", "sí"}:
                print("Cancelado. No se ha tocado nada.")
                return 1
        except EOFError:
            print("Sin terminal para confirmar; usa --si si sabes lo que haces.")
            return 1

    codigo = _ejecutar_filter_repo()
    if codigo != 0:
        print("filter-repo falló; el repositorio NO se ha empujado.", file=sys.stderr)
        return codigo

    restantes = _blobs_afectados()
    if restantes:
        print(
            f"\n¡ATENCIÓN! Siguen quedando {len(restantes)} blob(s) con datos"
            " personales. NO empujes; revisa el guion.",
            file=sys.stderr,
        )
        return 1

    print("\nHistorial reescrito y comprobado: no queda ningún dato personal en los blobs.")
    print("\nFalta empujarlo. filter-repo quita los remotos a propósito, así que:\n")
    for nombre, url in remotos.items():
        print(f"    git remote add {nombre} {url}")
    for rama in ramas:
        destino = next(iter(remotos), "origin")
        print(f"    git push --force {destino} {rama}")

    print("\nY LO QUE FALTA DESPUÉS, que es la mitad que importa:\n")
    print("    GitHub no borra las refs de los pull request. `refs/pull/1/head`")
    print("    apunta a un commit cuyos antepasados llevan los datos personales,")
    print("    y el push --force no la toca. Tampoco desaparecen los commits")
    print("    sueltos, que GitHub sigue sirviendo por su SHA.")
    print("\n    Hay que abrir un ticket al soporte de GitHub pidiendo que purguen")
    print("    las refs de pull request y las cachés del repositorio, citando los")
    print("    SHA afectados. Sin eso, el borrado está a medias.")
    return 0


# Patrones que retiran nombres de persona del TEXTO del repositorio: código,
# comentarios y mensajes de commit.
#
# Hizo falta porque me pasó a mí. Al documentar el caso escribí el nombre
# completo de la UTE —con los nombres y apellidos de sus dos socios dentro— en
# los docstrings del guion, en los de su test y en varios mensajes de commit.
# O sea que retiré los datos personales de los ficheros de datos y los volví a
# publicar en la prosa que explicaba cómo los había retirado.
#
# El patrón no nombra a nadie: casa la forma «UTE <topónimo> (…)» y se queda
# con el topónimo, que es un nombre de lugar y no de persona. Así esta lista
# tampoco es otra copia de los datos personales.
SUSTITUCIONES_TEXTO = (
    r"regex:UTE PERAFITA \([^)]*\)==>UTE PERAFITA (socios retirados)",
)


def _ocurrencias_reales() -> list[tuple[str, str]]:
    """Los textos concretos que hay que sustituir, sacados del repositorio.

    Se extraen con el patrón en tiempo de ejecución en vez de escribirlos en
    el guion, por lo de siempre: una lista de qué borrar por datos personales
    no puede ser otra copia de esos datos. Aquí no se commitea nada; el
    fichero vive en /tmp mientras dura el borrado.

    Y se pasan a filter-repo como LITERALES. Con `regex:` no sustituía nada en
    los mensajes de commit —la comprobación posterior lo pilló y se negó a
    empujar, que para eso está—. Un literal no depende de cómo compile los
    patrones ni de si los aplica por líneas o de una vez.
    """
    fuentes = [
        subprocess.run(
            ["git", "log", "--all", "--format=%B"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
    ]
    for _sha, crudo in _todos_los_blobs_de_texto():
        fuentes.append(crudo.decode("utf-8", errors="ignore"))

    pares: dict[str, str] = {}
    for linea in SUSTITUCIONES_TEXTO:
        patron, reemplazo = linea.split("==>")
        if not patron.startswith("regex:"):
            continue
        rx = re.compile(patron[len("regex:") :])
        for texto in fuentes:
            for hallado in rx.findall(texto):
                # Lo ya sustituido vuelve a casar con el patrón. Sustituirlo
                # por sí mismo no rompe nada pero ensucia el fichero y deja
                # dudando de si el borrado hizo algo.
                if hallado == reemplazo:
                    continue
                pares.setdefault(hallado, reemplazo)
    return sorted(pares.items())


def _fichero_de_sustituciones() -> str:
    pares = _ocurrencias_reales()
    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        for original, nuevo in pares:
            # Formato de filter-repo: `literal==>reemplazo`, una por línea. Un
            # salto de línea dentro de la coincidencia no cabe ahí, y pasa
            # cuando el nombre quedó partido al ajustar el ancho del párrafo.
            #
            # Se trocea: el primer pedazo lleva el reemplazo entero y los
            # siguientes se van a la nada. Mapear cada trozo al texto completo
            # lo repetiría tantas veces como líneas ocupara.
            trozos = [t for t in original.split("\n") if t.strip()]
            if len(trozos) <= 1:
                f.write(f"{original}==>{nuevo}\n")
                continue
            f.write(f"{trozos[0]}==>{nuevo}\n")
            for trozo in trozos[1:]:
                f.write(f"{trozo}==>\n")
        return f.name


def _ejecutar_filter_repo() -> int:
    """Lanza git-filter-repo con `redactar()` como callback.

    El callback IMPORTA esta misma función en vez de repetirla dentro de una
    cadena de texto. La primera versión llevaba una copia del filtro embebida
    en el argumento, y en cuanto la regla creció —quitar también los DNI que
    cuelgan de empresas— las dos versiones se separaron: la probada por los
    tests y la que se ejecutaba de verdad. Una lógica que decide qué datos
    personales se publican no puede tener dos copias.
    """
    aqui = str(Path(__file__).resolve().parent)

    # El conjunto de id viaja por fichero y no por la línea de órdenes: son
    # cientos de UUID y hay límites de longitud de argumentos.
    with tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(sorted(ids_personales()), f)
        ruta_ids = f.name

    callback = (
        "import sys, json\n"
        f"sys.path.insert(0, {aqui!r})\n"
        "from redactar_particulares_del_historico import redactar\n"
        f"_ids = set(json.load(open({ruta_ids!r})))\n"
        "if b'\"nodes\"' in blob.data or b'\"entidades\"' in blob.data:\n"
        "    try:\n"
        "        d = json.loads(blob.data)\n"
        "    except Exception:\n"
        "        d = None\n"
        "    if d is not None:\n"
        "        d, cuantos = redactar(d, _ids)\n"
        "        if cuantos:\n"
        "            blob.data = json.dumps(d, ensure_ascii=False).encode('utf-8')\n"
    )
    sustituciones = _fichero_de_sustituciones()
    return subprocess.run(
        [
            "git",
            "filter-repo",
            "--force",
            "--blob-callback",
            callback,
            # En el contenido de los ficheros...
            "--replace-text",
            sustituciones,
            # ...y en los mensajes de commit, que son parte del repositorio
            # igual que los ficheros y no los toca ningún callback de blobs.
            "--replace-message",
            sustituciones,
        ],
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
