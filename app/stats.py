from __future__ import annotations

import math


def _erf(value: float) -> float:
    sign = -1 if value < 0 else 1
    x = abs(value)
    t = 1 / (1 + 0.3275911 * x)
    y = 1 - (
        (((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736)
        * t
        + 0.254829592
    ) * t * math.exp(-x * x)
    return sign * y


def two_proportion_z(x1: int, n1: int, x2: int, n2: int) -> dict[str, float] | None:
    if not n1 or not n2:
        return None
    pooled = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return {"z": 0.0, "p": 1.0}
    z = (x1 / n1 - x2 / n2) / se
    p = round(2 * (1 - 0.5 * (1 + _erf(abs(z) / math.sqrt(2)))), 3)
    return {"z": round(z, 3), "p": p}


def wilson_interval(x: int, n: int, z: float = 1.959963984540054) -> dict[str, float] | None:
    if not n:
        return None
    p = x / n
    denominator = 1 + z * z / n
    center = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return {
        "low": round((center - spread) / denominator * 100, 1),
        "high": round((center + spread) / denominator * 100, 1),
    }
