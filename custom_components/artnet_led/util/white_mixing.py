"""Mixing algorithms for tunable white (cold white + warm white) fixtures.

Two strategies are available:

- ``max_output`` (legacy): the channel ratio is linear in Kelvin and the larger channel
  is always driven at full brightness. Mid temperatures therefore run both channels at
  100 % and are up to twice as bright as the extremes.
- ``constant_lumen``: cold + warm always add up to the requested brightness, so changing
  the color temperature does not change the light output. The split is linear in mireds
  (same approach as Home Assistant's ``color_temperature_to_rgbww``), kept in floats so
  16 bit channels keep their resolution.
"""
from __future__ import annotations

from typing import Callable

MIXING_MAX_OUTPUT = "max_output"
MIXING_CONSTANT_LUMEN = "constant_lumen"
MIXING_MODES = [MIXING_MAX_OUTPUT, MIXING_CONSTANT_LUMEN]

OutputCorrection = Callable[[float], float]


def kelvin_to_white_levels(kelvin: float, brightness: float, min_kelvin: int, max_kelvin: int,
                           mode: str = MIXING_MAX_OUTPUT,
                           output_correction: OutputCorrection | None = None) -> tuple[float, float]:
    """Return (cold_white, warm_white) in the range 0..255 for the given color temperature."""
    kelvin = min(max(kelvin, min_kelvin), max_kelvin)

    if mode == MIXING_CONSTANT_LUMEN:
        total = output_correction(brightness) if output_correction else brightness
        # HA splits linear in mireds and guarantees cold + warm == total. We re-do the split with
        # floats to keep the precision for 16 bit channels.
        max_mireds = 1000000 / min_kelvin
        min_mireds = 1000000 / max_kelvin
        mired = 1000000 / kelvin if kelvin else max_mireds
        cold_ratio = (max_mireds - mired) / (max_mireds - min_mireds)
        cold = total * cold_ratio
        warm = total - cold
        return cold, warm

    # Legacy behaviour: linear in Kelvin, normalised so the dominant channel equals brightness.
    cold_raw = 255 * (kelvin - min_kelvin) / (max_kelvin - min_kelvin)
    warm_raw = 255 - cold_raw
    max_raw = max(1.0, cold_raw, warm_raw)
    return cold_raw * brightness / max_raw, warm_raw * brightness / max_raw


def white_levels_to_kelvin_brightness(cold_white: float, warm_white: float, min_kelvin: int, max_kelvin: int,
                                      mode: str = MIXING_MAX_OUTPUT) -> tuple[int, int]:
    """Inverse of :func:`kelvin_to_white_levels`; returns (color_temp_kelvin, brightness)."""
    white_sum = cold_white + warm_white

    if mode == MIXING_CONSTANT_LUMEN:
        if white_sum == 0:
            kelvin = round((min_kelvin + max_kelvin) / 2)
        else:
            max_mireds = 1000000 / min_kelvin
            min_mireds = 1000000 / max_kelvin
            mired = max_mireds - (cold_white / white_sum) * (max_mireds - min_mireds)
            kelvin = min(max(round(1000000 / mired), min_kelvin), max_kelvin)
        return kelvin, int(min(255, round(white_sum)))

    if white_sum == 0:
        kelvin = round((min_kelvin + max_kelvin) / 2)
    else:
        cold_ratio = cold_white / white_sum
        kelvin = round(min_kelvin - min_kelvin * cold_ratio + max_kelvin * cold_ratio)
    return kelvin, int(round(max(cold_white, warm_white)))


__all__ = [
    "MIXING_MAX_OUTPUT",
    "MIXING_CONSTANT_LUMEN",
    "MIXING_MODES",
    "kelvin_to_white_levels",
    "white_levels_to_kelvin_brightness",
]
