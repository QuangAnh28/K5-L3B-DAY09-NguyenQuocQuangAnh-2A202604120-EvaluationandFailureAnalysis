"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import comb, isfinite
from numbers import Integral

import numpy as np
from scipy.stats import bootstrap

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    if len(human) != len(judge) or not human:
        raise ValueError("labels must be nonempty and equally sized")
    cm = dict(tp=0, fp=0, fn=0, tn=0)
    for h, j in zip(human, judge):
        if h not in ("PASS", "FAIL") or j not in ("PASS", "FAIL"):
            raise ValueError("labels must be PASS or FAIL")
        cm[("t" if h == j else "f") + ("p" if j == POS else "n")] += 1
    return cm


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    cm = confusion(human, judge)
    return (cm["tp"] / (cm["tp"] + cm["fp"]) if cm["tp"] + cm["fp"] else 0.0,
            cm["tp"] / (cm["tp"] + cm["fn"]) if cm["tp"] + cm["fn"] else 0.0)


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    cm = confusion(human, judge)
    n = len(human)
    po = (cm["tp"] + cm["tn"]) / n
    pe = ((cm["tp"] + cm["fn"]) * (cm["tp"] + cm["fp"])
          + (cm["tn"] + cm["fp"]) * (cm["tn"] + cm["fn"])) / n**2
    if pe == 1:
        raise ValueError("kappa undefined: expected agreement is one")
    return (po - pe) / (1 - pe)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    if any(not isfinite(v) or not 0 <= v <= 1 for v in (observed_rate, sensitivity, specificity)):
        raise ValueError("rates must be finite and in [0, 1]")
    if sensitivity + specificity <= 1:
        raise ValueError("Rogan-Gladen requires sensitivity + specificity > 1")
    return min(1.0, max(0.0, (observed_rate + specificity - 1) / (sensitivity + specificity - 1)))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    x, y = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if x.ndim != 1 or y.ndim != 1 or len(x) != len(y) or not len(x):
        raise ValueError("paired samples must be nonempty equal-length vectors")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("samples must be finite")
    if not 0 < confidence < 1 or n_resamples < 1:
        raise ValueError("invalid bootstrap configuration")
    delta = float(np.mean(x - y))
    if np.array_equal(x, y):
        return 0.0, 0.0, 0.0
    if len(x) == 1:
        return delta, delta, delta
    res = bootstrap((x, y), lambda u, v, axis: np.mean(u - v, axis=axis),
                    paired=True, method="percentile", n_resamples=n_resamples,
                    confidence_level=confidence, rng=np.random.default_rng(rng))
    return delta, float(res.confidence_interval.low), float(res.confidence_interval.high)


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    _validate_counts(n, c, k)
    return 1.0 - comb(n - c, k) / comb(n, k) if n - c >= k else 1.0


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    _validate_counts(n, c, k)
    return comb(c, k) / comb(n, k) if c >= k else 0.0


def _validate_counts(n: int, c: int, k: int) -> None:
    if any(isinstance(v, bool) or not isinstance(v, Integral) for v in (n, c, k)):
        raise ValueError("n, c, k must be integers")
    if n < 1 or not 0 <= c <= n or not 1 <= k <= n:
        raise ValueError("require n >= 1, 0 <= c <= n, 1 <= k <= n")
