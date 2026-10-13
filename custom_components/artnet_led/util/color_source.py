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


# A turn_on whose colour temperature is this close to the source is treated as coming from the
# source itself (e.g. Adaptive Lighting injecting its value into an intercepted turn_on call).
SOURCE_TOLERANCE_KELVIN = 25


def is_from_source(kelvin: float, source_kelvin: int | None,
                   tolerance: int = SOURCE_TOLERANCE_KELVIN) -> bool:
    """True when a requested colour temperature matches what the source currently provides."""
    return source_kelvin is not None and abs(kelvin - source_kelvin) <= tolerance


class ManualHold:
    """Remembers that the user picked a colour temperature by hand.

    ``hold_seconds`` > 0: the choice is kept for that long, also across off/on and restarts.
    ``hold_seconds`` == 0: the choice is kept until the light is turned off.
    Time is passed in explicitly (unix seconds) so the logic stays testable.
    """

    def __init__(self, hold_seconds: float = 0):
        self.hold_seconds = max(0.0, float(hold_seconds or 0))
        self.until: float | None = None

    def start(self, now: float) -> None:
        self.until = now + self.hold_seconds if self.hold_seconds > 0 else float("inf")

    def clear(self) -> None:
        self.until = None

    def on_turned_off(self) -> None:
        """A hold without duration ends when the light goes off; a timed hold survives it."""
        if self.until is not None and self.until == float("inf"):
            self.until = None

    def active(self, now: float) -> bool:
        return self.until is not None and now < self.until

    def remaining(self, now: float) -> float | None:
        """Seconds left on a timed hold, ``None`` when there is no timed hold."""
        if self.until is None or self.until == float("inf"):
            return None
        return max(0.0, self.until - now)

    def restore(self, until, now: float) -> None:
        """Take over a persisted ``until`` value (unix seconds), ignoring stale or bogus ones."""
        try:
            value = float(until)
        except (TypeError, ValueError):
            return
        if value == float("inf") or value > now:
            self.until = value
