# Reconocimiento de fuentes

Informes generados por `.github/workflows/reconocer-fuente.yml` antes de
escribir un conector.

No son documentación de fuentes integradas —eso vive en
[`docs/data-sources.md`](../data-sources.md)—. Son lo que se ve desde fuera,
anotado sin interpretar, para decidir si merece la pena el conector y de qué
tipo tiene que ser.

Existen por una lección concreta: en BDNS se dedujo el nombre de un campo del
enumerado de parámetros de búsqueda, se dio por bueno, y estaba mal. El 79 % de
las aristas de la primera ingesta salió sin identificador fiscal. Con un PDF ese
error sería peor: no avisan cuando los lees mal, sólo devuelven basura con
aspecto de dato.
