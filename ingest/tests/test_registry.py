"""Tests del registro de conectores."""

from __future__ import annotations

import pytest

from sinapsis_ingest import registry


@pytest.fixture(autouse=True)
def registro_limpio():
    registry._reset_for_tests()
    yield
    registry._reset_for_tests()


class _ConectorFalso:
    source_id = "falso"
    extractor_version = "falso/1"


def test_register_y_get():
    registry.register("falso", _ConectorFalso)
    assert isinstance(registry.get("falso"), _ConectorFalso)


def test_get_de_desconocido_menciona_los_disponibles():
    registry.register("falso", _ConectorFalso)
    with pytest.raises(KeyError, match="falso"):
        registry.get("inexistente")


def test_no_se_puede_registrar_dos_veces():
    registry.register("falso", _ConectorFalso)
    with pytest.raises(ValueError, match="ya está registrado"):
        registry.register("falso", _ConectorFalso)


def test_available_devuelve_orden_alfabetico():
    registry.register("zeta", _ConectorFalso)
    registry.register("alfa", _ConectorFalso)
    assert registry.available() == ["alfa", "zeta"]


def test_available_vacio_al_principio():
    assert registry.available() == []
