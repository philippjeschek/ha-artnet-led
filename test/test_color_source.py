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


# --- manual hold -----------------------------------------------------------------------------

from custom_components.artnet_led.util.color_source import ManualHold, is_from_source  # noqa: E402


def test_is_from_source_tolerance():
    assert is_from_source(5595, 5590)
    assert is_from_source(5600, 5600)
    assert not is_from_source(3000, 5590)
    assert not is_from_source(5595, None)


def test_hold_until_off():
    hold = ManualHold(0)
    assert not hold.active(100)
    hold.start(100)
    assert hold.active(100) and hold.active(10 ** 9)
    assert hold.remaining(100) is None
    hold.on_turned_off()
    assert not hold.active(101)


def test_timed_hold_survives_off_and_expires():
    hold = ManualHold(36000)
    hold.start(1000)
    hold.on_turned_off()
    assert hold.active(1000 + 35999)
    assert hold.remaining(1000 + 30000) == 6000
    assert not hold.active(1000 + 36000)


def test_restore_ignores_stale_values():
    hold = ManualHold(36000)
    hold.restore(None, 1000)
    assert not hold.active(1000)
    hold.restore("garbage", 1000)
    assert not hold.active(1000)
    hold.restore(500, 1000)            # already expired
    assert not hold.active(1000)
    hold.restore(5000, 1000)
    assert hold.active(4999) and not hold.active(5000)
    hold.restore(float("inf"), 1000)
    assert hold.active(10 ** 9)
