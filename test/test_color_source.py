from types import SimpleNamespace

import pytest

from custom_components.artnet_led.util.color_source import kelvin_from_state

MIN_K = 2500
MAX_K = 6500


def _state(value, **attributes):
    return SimpleNamespace(state=value, attributes=attributes)


def test_missing_entity():
    assert kelvin_from_state(None, MIN_K, MAX_K) is None


@pytest.mark.parametrize("value", ["unknown", "unavailable", "off", ""])
def test_unusable_states(value):
    assert kelvin_from_state(_state(value, color_temp_kelvin=4000), MIN_K, MAX_K) is None


def test_numeric_state():
    assert kelvin_from_state(_state("4000"), MIN_K, MAX_K) == 4000
    assert kelvin_from_state(_state("3999.6"), MIN_K, MAX_K) == 4000


def test_adaptive_lighting_switch_attribute():
    assert kelvin_from_state(_state("on", color_temp_kelvin=5740, color_temp_mired=174), MIN_K, MAX_K) == 5740


def test_mired_fallback():
    assert kelvin_from_state(_state("on", color_temp_mired=250), MIN_K, MAX_K) == 4000
    assert kelvin_from_state(_state("on", color_temp=400), MIN_K, MAX_K) == 2500


def test_light_without_colour_temperature():
    assert kelvin_from_state(_state("on", brightness=200), MIN_K, MAX_K) is None
    assert kelvin_from_state(_state("on", color_temp_kelvin=None), MIN_K, MAX_K) is None


@pytest.mark.parametrize("value, expected", [("1000", MIN_K), ("9000", MAX_K), ("0", None), ("-5", None)])
def test_clamped_to_range(value, expected):
    assert kelvin_from_state(_state(value), MIN_K, MAX_K) == expected
