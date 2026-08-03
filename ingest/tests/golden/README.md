# Muestras para golden tests

Un golden test compara la salida del parser contra una muestra **real** de la
fuente, guardada en disco. Los formatos oficiales cambian sin avisar; sin una
muestra real no te enteras hasta que la ingesta produce basura en silencio.

## Estado de las muestras

| Fichero | Origen | Golden test real |
|---|---|---|
| `bdns_concesiones_sintetica.json` | **Sintética** | ❌ no |
| `bdns_concesiones_real.json` | Captura de la API | ⏳ pendiente de capturar |

### Por qué hay una muestra sintética

`bdns_concesiones_sintetica.json` **no es una respuesta capturada de BDNS.**
Se construyó a partir de los nombres de campo que la API declara como
ordenables (`codConcesion`, `numeroConvocatoria`, `convocatoria`, `nivel1..3`,
`instrumento`, `urlBR`, `fechaConcesion`, `beneficiario`, `importe`,
`ayudaEquivalente`), verificados en el código de
[`bdns-fetch`](https://github.com/cruzlorite/bdns-fetch), más la envoltura de
paginación estilo Spring (`content`, `totalPages`, `number`) que usa la API.

Sirve para probar la **lógica** del parser —normalización de NIF, elección
entre `Person` y `Company`, jerarquía de órganos, importes decimales, registros
incompletos— pero **no valida el formato real**. Los datos que contiene son
inventados y están marcados como tales; ninguno corresponde a una subvención
existente.

### Cómo capturar la muestra real

Desde una máquina con salida a internet:

```bash
python scripts/capturar_muestra_bdns.py \
    --salida ingest/tests/golden/bdns_concesiones_real.json
```

El script descarga una página pequeña de concesiones y la guarda literal. Al
existir ese fichero, `test_bdns_golden.py` deja de saltarse y pasa a comparar
la salida del parser contra una entrada auténtica.

**Hasta entonces, el conector de BDNS no está verificado contra la fuente
real.** Está en `docs/data-sources.md §1`.

---

## PLACSP

| Fichero | Origen | Golden test |
|---|---|---|
| `placsp_agregadas_muestra.atom` | Real, **espejo de terceros** | ✅ sí, con reservas |

`placsp_agregadas_muestra.atom` es una respuesta **real** del feed
`PlataformasAgregadasSinMenores` de PLACSP (4 de enero de 2022), pero **no la
capturamos nosotros**: viene del repositorio
[`nextprocurement/sproc`](https://github.com/nextprocurement/sproc)
(`samples/PlataformasAgregadasSinMenores_20220104_030016_1_single.atom`), porque
el entorno de desarrollo no tiene salida hacia `contrataciondelestado.es`.

**Está modificada.** Quien la publicó añadió un segundo adjudicatario de prueba
(`A28526275 II` / `... ACISA) II`) que no existe en el original. Lo dejamos a
propósito: ejercita el caso de varios `WinningParty` por contrato, que es real
—lotes y UTEs— y que un parser ingenuo se comería.

Consecuencia: la estructura CODICE y los nombres de elemento **sí** están
verificados contra datos auténticos; los valores concretos no son citables como
hecho. Cuando haya salida a internet conviene capturar una muestra de primera
mano y sustituirla.
