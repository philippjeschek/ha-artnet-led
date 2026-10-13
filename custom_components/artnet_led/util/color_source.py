"""Read a colour temperature from another Home Assistant entity.

Used by ``color_temp`` lights that follow an external source (human centric lighting):
the source can be a numeric entity (``sensor``, ``input_number``, state in Kelvin) or any
entity exposing a ``color_temp_kelvin`` / ``color_temp_mired`` attribute, such as the
Adaptive Lighting switch or another light.
"""
from __future__ import annotations

from homeassistant.const import STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN

_IGNORED_STATES = (None, "", STATE_UNKNOWN, STATE_UNAVAILABLE, STATE_OFF)


def kelvin_from_state(state, min_kelvin: int, max_kelvin: int) -> int | None:
    """Return the colour temperature in Kelvin a source entity currently provides.

    ``None`` means "no usable value": the entity is missing, unavailable, switched off or
    carries no colour temperature. The result is clamped to ``[min_kelvin, max_kelvin]``.
    """
    if state is None or state.state in _IGNORED_STATES:
        return None

    kelvin: float | None = None
    try:
        kelvin = float(state.state)
    except (TypeError, ValueError):
        attributes = getattr(state, "attributes", {}) or {}
        if attributes.get("color_temp_kelvin") is not None:
            kelvin = float(attributes["color_temp_kelvin"])
        elif attributes.get("color_temp_mired"):
            kelvin = 1_000_000 / float(attributes["color_temp_mired"])
        elif attributes.get("color_temp"):
            kelvin = 1_000_000 / float(attributes["color_temp"])

    if kelvin is None or kelvin <= 0:
        return None

    return int(round(min(max(kelvin, min_kelvin), max_kelvin)))

