import pytest
from pyartnet.output_correction import quadratic

from custom_components.artnet_led.util.channel_switch import from_values, to_values
from custom_components.artnet_led.util.white_mixing import (
    MIXING_CONSTANT_LUMEN,
    MIXING_MAX_OUTPUT,
    kelvin_to_white_levels,
    white_levels_to_kelvin_brightness,
)

min_k = 2500
max_k = 6500
# Mired midpoint of 2500 K (400 mired) and 6500 K (153.8 mired) is ~276.9 mired = ~3611 K
mid_k = 3611


@pytest.mark.parametrize("kelvin", [min_k, 3000, mid_k, 4500, 6000, max_k])
def test_constant_lumen_sum_is_brightness(kelvin):
    cold, warm = kelvin_to_white_levels(kelvin, 128, min_k, max_k, MIXING_CONSTANT_LUMEN)

    assert cold + warm == pytest.approx(128)
    assert 0 <= cold <= 128
    assert 0 <= warm <= 128


def test_constant_lumen_extremes_and_middle():
    assert kelvin_to_white_levels(min_k, 200, min_k, max_k, MIXING_CONSTANT_LUMEN) == pytest.approx((0, 200))
    assert kelvin_to_white_levels(max_k, 200, min_k, max_k, MIXING_CONSTANT_LUMEN) == pytest.approx((200, 0))

    cold, warm = kelvin_to_white_levels(mid_k, 200, min_k, max_k, MIXING_CONSTANT_LUMEN)
    assert cold == pytest.approx(100, abs=1)
    assert warm == pytest.approx(100, abs=1)


def test_constant_lumen_brightness_and_temperature_are_independent():
    for brightness in (10, 64, 128, 255):
        cold, warm = kelvin_to_white_levels(4000, brightness, min_k, max_k, MIXING_CONSTANT_LUMEN)
        # Same ratio regardless of brightness
        assert cold / (cold + warm) == pytest.approx(
            kelvin_to_white_levels(4000, 255, min_k, max_k, MIXING_CONSTANT_LUMEN)[0] / 255)


@pytest.mark.parametrize("kelvin", [min_k, 3000, mid_k, 5000, max_k])
def test_constant_lumen_with_quadratic_curve_keeps_total(kelvin):
    cold, warm = kelvin_to_white_levels(kelvin, 128, min_k, max_k, MIXING_CONSTANT_LUMEN, quadratic)

    assert cold + warm == pytest.approx(quadratic(128))


def test_max_output_matches_legacy_formula():
    # Middle of the Kelvin range: both channels at full brightness (legacy behaviour)
    cold, warm = kelvin_to_white_levels(4500, 128, min_k, max_k, MIXING_MAX_OUTPUT)
    assert cold == pytest.approx(128)
    assert warm == pytest.approx(128)

    cold, warm = kelvin_to_white_levels(min_k, 128, min_k, max_k, MIXING_MAX_OUTPUT)
    assert (cold, warm) == pytest.approx((0, 128))

    cold, warm = kelvin_to_white_levels(max_k, 128, min_k, max_k, MIXING_MAX_OUTPUT)
    assert (cold, warm) == pytest.approx((128, 0))


@pytest.mark.parametrize("kelvin", [min_k, 3000, mid_k, 5000, max_k])
def test_constant_lumen_roundtrip(kelvin):
    cold, warm = kelvin_to_white_levels(kelvin, 180, min_k, max_k, MIXING_CONSTANT_LUMEN)
    kelvin_back, brightness_back = white_levels_to_kelvin_brightness(cold, warm, min_k, max_k, MIXING_CONSTANT_LUMEN)

    assert brightness_back == 180
    assert kelvin_back == pytest.approx(kelvin, abs=30)


def test_to_values_constant_lumen_8bit():
    assert to_values("ch", 1, True, 128, color_temp_kelvin=min_k, min_kelvin=min_k, max_kelvin=max_k,
                     white_mixing=MIXING_CONSTANT_LUMEN) == [0, 128]
    assert to_values("ch", 1, True, 128, color_temp_kelvin=max_k, min_kelvin=min_k, max_kelvin=max_k,
                     white_mixing=MIXING_CONSTANT_LUMEN) == [128, 0]

    values = to_values("hc", 1, True, 128, color_temp_kelvin=mid_k, min_kelvin=min_k, max_kelvin=max_k,
                       white_mixing=MIXING_CONSTANT_LUMEN)
    assert sum(values) == 128
    assert abs(values[0] - values[1]) <= 1

    # Off: everything zero
    assert to_values("ch", 1, False, 128, color_temp_kelvin=mid_k, min_kelvin=min_k, max_kelvin=max_k,
                     white_mixing=MIXING_CONSTANT_LUMEN) == [0, 0]


def test_to_values_constant_lumen_16bit_keeps_resolution():
    values = to_values("ch", 256, True, 128, color_temp_kelvin=mid_k, min_kelvin=min_k, max_kelvin=max_k,
                       white_mixing=MIXING_CONSTANT_LUMEN)

    assert sum(values) == pytest.approx(128 * 256, abs=1)
    # Floats are kept until scaling: 16 bit values are not multiples of 256
    assert any(value % 256 != 0 for value in values)


def test_to_values_max_output_unchanged():
    values = to_values("ch", 1, True, 255, color_temp_kelvin=4500, min_kelvin=min_k, max_kelvin=max_k)
    assert values == [255, 255]

    values = to_values("ch", 1, True, 128, color_temp_kelvin=4500, min_kelvin=min_k, max_kelvin=max_k,
                       white_mixing=MIXING_MAX_OUTPUT)
    assert values == [128, 128]


def test_from_values_constant_lumen():
    is_on, brightness, _, _, _, cold, warm, kelvin, _, _ = from_values(
        "ch", 1, [64, 64], min_k, max_k, white_mixing=MIXING_CONSTANT_LUMEN)
    assert is_on
    assert brightness == 128
    assert (cold, warm) == (64, 64)
    assert kelvin == pytest.approx(mid_k, abs=30)

    is_on, brightness, _, _, _, cold, warm, kelvin, _, _ = from_values(
        "hc", 1, [0, 200], min_k, max_k, white_mixing=MIXING_CONSTANT_LUMEN)
    assert brightness == 200
    assert kelvin == max_k

    is_on, brightness, _, _, _, _, _, _, _, _ = from_values(
        "ch", 1, [0, 0], min_k, max_k, white_mixing=MIXING_CONSTANT_LUMEN)
    assert not is_on
    assert brightness == 0


def test_from_values_max_output_unchanged():
    is_on, brightness, _, _, _, cold, warm, kelvin, _, _ = from_values("ch", 1, [128, 128], min_k, max_k)
    assert brightness == 128
    assert (cold, warm) == (255, 255)
    assert kelvin == 4500
