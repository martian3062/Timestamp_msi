from __future__ import annotations

from typing import Any


APPROACH_LABELS = ("Approach1", "Approach2", "MonteCarlo")


def normalize_approach_label(value: Any) -> str:
    if isinstance(value, str):
        compact = value.strip().lower().replace(" ", "").replace("-", "")
        if compact in {"approach1", "a1", "baseline1"}:
            return "Approach1"
        if compact in {"approach2", "a2", "patchclassification", "patchclassifier"}:
            return "Approach2"
        if compact in {"approach3", "a3", "montecarlo", "mc"}:
            return "MonteCarlo"
    return "Approach2"


def classify_experiment(
    *,
    name: str = "",
    model_type: str = "",
    parameters: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
) -> str:
    for payload in (parameters, metrics):
        if isinstance(payload, dict):
            direct = payload.get("approach_label")
            if direct is not None:
                return normalize_approach_label(direct)

    combined = " ".join(
        part for part in (name, model_type) if isinstance(part, str) and part.strip()
    ).lower()
    if "approach1" in combined or "baseline" in combined:
        return "Approach1"
    if (
        "approach3" in combined
        or "monte carlo" in combined
        or "montecarlo" in combined
        or "mc_" in combined
        or "stochastic" in combined
    ):
        return "MonteCarlo"

    return "Approach2"
