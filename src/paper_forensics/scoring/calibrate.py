from __future__ import annotations


def identity_calibration(value: float) -> float:
    return max(0.0, min(1.0, value))
