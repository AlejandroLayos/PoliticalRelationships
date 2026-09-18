"""Golden test del conector del Tribunal de Cuentas.

Obligatorio según CLAUDE.md para los parsers de fuentes, y aquí más que en
ningún otro sitio: un PDF no avisa cuando lo lees mal, devuelve basura con
aspecto de dato. La muestra es el expediente sancionador de la contabilidad
electoral de 2019 tal y como lo sirve el organismo, capturada por
`scripts/capturar_muestra_tcu.py` (el entorno de desarrollo no alcanza
www.tcu.es; la captura la hace el runner).

Los valores esperados no salen de mi cabeza: salen de leer el fichero real.
Si el Tribunal rediseña el PDF, estos números cambiarán y el test lo dirá.
Eso no es un test frágil, es exactamente para lo que existe.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from sinapsis_ingest.connectors.base import RawDocument
from sinapsis_ingest.connectors.tcu import TCUConnector

MUESTRA = Path(__file__).parent / "golden" / "tcu_sancionadores_2019.pdf"

pytestmark = pytest.mark.skipif(
    not MUESTRA.exists(),
    reason="falta la muestra golden; la captura el workflow «Reconocer fuente»",
)


@pytest.fixture
def conector() -> TCUConnector:
    return TCUConnector()


@pytest.fixture
def crudo() -> RawDocument:
    return RawDocument(
        source_id="tcu",
        url="https://www.tcu.es/ejemplo/sancionadores-2019.pdf",
        content=MUESTRA.read_bytes(),
        media_type="application/pdf",
        retrieved_at=datetime(2026, 8, 3, tzinfo=UTC),
    )


@pytest.fixture
def normalizados(conector, crudo):
    return [n for r in conector.parse(crudo) if (n := conector.normalize(r)) is not None]


# --- parse ----------------------------------------------------------------


def test_extrae_los_expedientes_de_las_tres_paginas(conector, crudo):
    assert len(list(conector.parse(crudo))) == 33


def test_parse_es_puro(conector, crudo):
    """Dos pasadas sobre los mismos bytes dan lo mismo: si no, no hay golden."""
    primera = [r.data for r in conector.parse(crudo)]
    segunda = [r.data for r in conector.parse(crudo)]
    assert primera == segunda


def test_cada_registro_enlaza_con_su_crudo(conector, crudo):
    for r in conector.parse(crudo):
        assert r.raw_content_hash == crudo.content_hash
        assert r.extractor_version == conector.extractor_version


def test_las_continuaciones_no_se_toman_por_partidos(conector, crudo):
    """Las filas partidas traen colas como "ANULADA" o "SANCIÓN*".

    Tratarlas como registros crearía formaciones políticas fantasma con ese
    nombre, que es el fallo más vistoso que puede tener este parser.
    """
    nombres = {r.data["formacion"] for r in conector.parse(crudo)}
    for fantasma in ("ANULADA", "SANCIÓN*", "SANCION*", ""):
        assert fantasma not in nombres
    # Y ninguno debería ser un fragmento suelto de dos palabras en mayúsculas.
    assert all(len(n) > 3 for n in nombres)


# --- normalize ------------------------------------------------------------


def test_todos_los_expedientes_traen_nif(normalizados):
    """Es lo que hace que el TdC converja con BDNS y PLACSP.

    Si esto baja, el conector deja de aportar lo que lo hace valioso: enlazar
    al mismo partido a través de tres fuentes distintas.
    """
    con_nif = [n for n in normalizados if n.entidades[0].dedupe_key.startswith("nif:")]
    assert len(con_nif) == len(normalizados) == 33


def test_la_arista_es_una_deuda_del_partido_con_el_organismo(normalizados):
    n = normalizados[0]
    arista = n.aristas[0]
    assert arista.ftm_schema == "Debt"
    assert arista.source_key == n.entidades[0].dedupe_key
    assert arista.target_key == "tcu:organo:tribunal-de-cuentas"


def test_el_primer_expediente_sale_tal_y_como_esta_en_el_pdf(normalizados):
    n = normalizados[0]
    assert n.entidades[0].caption == "AGRUPACION POPULAR POR GUADARRAMA"
    assert n.entidades[0].nif == "G86187317"
    assert n.entidades[0].properties["partido_politico"] is True
    assert n.aristas[0].amount == Decimal("50000.00")
    assert n.aristas[0].start_date == date(2022, 1, 17)
    assert n.aristas[0].currency == "EUR"
    assert n.aristas[0].confidence == 1.0
    assert n.aristas[0].properties["origen"] == "EE.LL. 2019"


def test_una_celda_con_varios_importes_no_se_interpreta(normalizados):
    """Precisión sobre exhaustividad.

    Hay celdas con dos o tres cifras ("50.000,00 1.318,64**"): la sanción, y
    lo que fija después la resolución del recurso. Elegir una sería atribuirle
    a un partido una multa que quizá no es la suya. Se deja sin importe, se
    conserva el texto y baja la confianza, para que un humano lo resuelva.
    """
    ambiguos = [n for n in normalizados if n.aristas[0].confidence < 1.0]
    assert ambiguos, "la muestra tiene celdas con varios importes"
    for n in ambiguos:
        assert n.aristas[0].amount is None
        assert n.aristas[0].currency == ""
        assert n.aristas[0].properties["cuantiaSinInterpretar"]


def test_el_dinero_inequívoco_cuadra(normalizados):
    con_importe = [n for n in normalizados if n.aristas[0].amount is not None]
    assert len(con_importe) == 16
    assert sum(n.aristas[0].amount for n in con_importe) == Decimal("578587.44")


def test_las_claves_de_arista_no_se_repiten(normalizados):
    """Si colapsaran, reejecutar el conector perdería sanciones."""
    claves = [n.aristas[0].dedupe_key for n in normalizados]
    assert len(set(claves)) == len(claves)


def test_ningun_expediente_pierde_la_fecha(normalizados):
    sin_fecha = [n for n in normalizados if n.aristas[0].start_date is None]
    assert not sin_fecha


# --- robustez -------------------------------------------------------------


def test_un_pdf_ilegible_no_revienta(conector):
    raw = RawDocument(
        source_id="tcu",
        url="https://ejemplo.test/roto.pdf",
        content=b"esto no es un PDF",
        media_type="application/pdf",
    )
    assert list(conector.parse(raw)) == []
