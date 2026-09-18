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
import json
import re
import subprocess
import sys
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
RUTA = "frontend/public/datos/grafo.json"

# Prefiltro barato antes de parsear JSON de varios megas. Es a propósito laxo:
# los volcados de agosto de 2026 se serializaban compactos —`"schema":"Person"`,
# sin espacio— y los de septiembre con separadores por defecto. Buscar la forma
# con espacio no encontraba nada y el ensayo decía «no hay nada que borrar»
# sobre dos blobs con 27 personas cada uno. Se busca la palabra suelta y decide
# el parseo, que es lo único que no depende del formato.
PISTA = b'"Person"'

MOTIVO = (
    "se retiraron personas físicas (nombre, DNI y procedencia) del historial:"
    " minimización de datos personales, RGPD. Ver docs/spec.md §12."
)


def redactar(datos: dict) -> tuple[dict, int]:
    """Devuelve el volcado sin datos personales y cuántos se quitaron.

    Dos cosas distintas:

    - Las entidades de esquema `Person` se van enteras: la ficha ES de una
      persona.
    - A las demás se les quita el NIF si resulta ser un DNI o un NIE. La ficha
      se queda —una UTE adjudicataria de un contrato público es un dato— pero
      el identificador personal no se publica.
    """
    nodos = datos.get("nodes") or []
    personales = {n["id"] for n in nodos if n.get("schema") == ESQUEMA_PERSONAL}

    nifs_retirados = 0
    for n in nodos:
        if n["id"] in personales:
            continue
        if es_identificador_personal(n.get("nif")):
            n.pop("nif", None)
            props = n.get("properties")
            if isinstance(props, dict):
                props.pop("nif", None)
            nifs_retirados += 1

    if not personales and not nifs_retirados:
        return datos, 0

    datos["nodes"] = [n for n in nodos if n["id"] not in personales]
    datos["edges"] = [
        a
        for a in (datos.get("edges") or [])
        if a.get("source") not in personales and a.get("target") not in personales
    ]
    procedencia = datos.get("provenance")
    if isinstance(procedencia, dict):
        datos["provenance"] = {k: v for k, v in procedencia.items() if k not in personales}

    datos["redactado"] = {
        "entidades_retiradas": len(personales),
        "identificadores_retirados": nifs_retirados,
        "motivo": MOTIVO,
    }
    return datos, len(personales) + nifs_retirados


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


def _blobs_afectados() -> list[tuple[str, int, str]]:
    salida = subprocess.run(
        ["git", "rev-list", "--all", "--objects", "--", RUTA],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    vistos: dict[str, None] = {}
    for linea in salida.splitlines():
        partes = linea.split(maxsplit=1)
        if len(partes) == 2:
            vistos.setdefault(partes[0], None)

    afectados = []
    for sha in vistos:
        tipo = subprocess.run(
            ["git", "cat-file", "-t", sha], capture_output=True, text=True
        ).stdout.strip()
        if tipo != "blob":
            continue
        crudo = subprocess.run(
            ["git", "cat-file", "-p", sha], capture_output=True
        ).stdout
        if b'"nodes"' not in crudo:
            continue
        try:
            datos = json.loads(crudo)
        except Exception:
            continue
        nodos = datos.get("nodes", [])
        personas = [n for n in nodos if n.get("schema") == ESQUEMA_PERSONAL]
        con_dni = [
            n
            for n in nodos
            if n.get("schema") != ESQUEMA_PERSONAL and es_identificador_personal(n.get("nif"))
        ]
        if personas or con_dni:
            afectados.append((sha, len(personas), len(con_dni)))
    return afectados


def comprobar() -> int:
    """Informa de qué hay que retirar. Sale con 1 si encuentra algo.

    No imprime ningún nombre ni ningún número: el informe de un problema de
    datos personales no puede ser otra copia de los datos personales.
    """
    afectados = _blobs_afectados()
    if not afectados:
        print("No queda ningún dato personal en los volcados del historial.")
        return 0

    print(f"{len(afectados)} blob(s) con datos personales:\n")
    print("  blob                                      fichas   identificadores")
    print("                                          personales  en otras fichas")
    fichas = identificadores = 0
    for sha, n_personas, n_dni in afectados:
        fichas += n_personas
        identificadores += n_dni
        print(f"  {sha}  {n_personas:>8}   {n_dni:>13}")
    print(f"\nFichas de personas físicas, que se retiran enteras: {fichas}")
    print("DNI o NIE colgando de otras fichas, de los que se retira")
    print(f"sólo el identificador: {identificadores}")
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
    if not afectados:
        print("No hay nada que reescribir.")
        return 0

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
    callback = (
        "import sys, json\n"
        f"sys.path.insert(0, {aqui!r})\n"
        "from redactar_particulares_del_historico import redactar\n"
        "if b'\"nodes\"' in blob.data:\n"
        "    try:\n"
        "        d = json.loads(blob.data)\n"
        "    except Exception:\n"
        "        d = None\n"
        "    if d is not None:\n"
        "        d, cuantos = redactar(d)\n"
        "        if cuantos:\n"
        "            blob.data = json.dumps(d, ensure_ascii=False).encode('utf-8')\n"
    )
    return subprocess.run(
        ["git", "filter-repo", "--force", "--blob-callback", callback],
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
