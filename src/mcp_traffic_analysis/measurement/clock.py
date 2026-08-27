"""Clock abstractions used to make timing semantics testable."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ClockSample:
    """A paired wall-clock and monotonic-clock observation."""

    wall_time_utc: datetime
    monotonic_time_ns: int


class Clock(Protocol):
    """Source of paired time observations."""

    def sample(self) -> ClockSample:
        """Return one wall-clock and monotonic-clock observation."""
        ...


class SystemClock:
    """Production clock based on the operating system's UTC and monotonic clocks."""

    def sample(self) -> ClockSample:
        return ClockSample(
            wall_time_utc=datetime.now(UTC),
            monotonic_time_ns=time.monotonic_ns(),
        )
