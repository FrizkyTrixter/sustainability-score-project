# This is scoring.py
from typing import Dict
from config import GWP_MAX, COST_MAX, CIRCULARITY_MAX


def clamp(value: float, lower_bound: float, upper_bound: float) -> float:
    """
    Restrict `value` to stay within [lower_bound, upper_bound].
    Used to prevent inputs from exceeding configured max/min thresholds.
    """
    return max(lower_bound, min(upper_bound, value))


def normalize_bad(raw_value: float, max_value: float) -> float:
    """
    Normalize a *bad* metric (where higher = worse) into a 0–100 score.

    Example: Global Warming Potential (GWP) or Cost — we want lower values
    to produce higher normalized scores.

    Parameters:
        raw_value:    The actual measured value.
        max_value:    The worst-case (maximum expected) value.

    Returns:
        A float in [0, 100] where:
          100 = best (lowest raw_value)
            0 = worst (highest raw_value within range)
    """
    if max_value <= 0:  # Prevent divide-by-zero
        return 100.0

    # Clamp to valid range before normalization
    clamped_value = clamp(raw_value, 0, max_value)
    normalized_score = (1 - (clamped_value / max_value)) * 100.0
    return normalized_score


def normalize_good(raw_value: float, max_value: float) -> float:
    """
    Normalize a *good* metric (where higher = better) into a 0–100 score.

    Example: Circularity (recyclability %) — we want higher values
    to produce higher normalized scores.

    Parameters:
        raw_value:    The actual measured value.
        max_value:    The ideal best-case (maximum expected) value.

    Returns:
        A float in [0, 100] where:
          100 = best (highest raw_value)
            0 = worst (lowest raw_value)
    """
    if max_value <= 0:
        return 100.0

    clamped_value = clamp(raw_value, 0, max_value)
    normalized_score = (clamped_value / max_value) * 100.0
    return normalized_score


def compute_score(
    gwp: float,
    circularity: float,
    cost: float,
    weights: Dict[str, float]
) -> tuple[float, Dict[str, float]]:
    """
    Compute the composite sustainability score (0–100) from normalized sub-scores.

    Parameters:
        gwp          : Global Warming Potential (bad metric)
        circularity  : Product circularity percentage (good metric)
        cost         : Product cost (bad metric)
        weights      : Dict of weighting factors for each metric,
                       e.g. {"gwp": 0.5, "circularity": 0.3, "cost": 0.2}

    Process:
        1. Normalize each metric to a 0–100 range.
        2. Ensure weights sum to 1.0 (auto-normalize if needed).
        3. Compute a weighted average of the sub-scores.

    Returns:
        (final_score, subscore_dict)
        final_score   : float (overall sustainability score 0–100)
        subscore_dict : {"gwp": <sub>, "circularity": <sub>, "cost": <sub>}
    """

    # --- Step 1: Normalize raw metrics to 0–100 scale ---
    gwp_subscore = normalize_bad(gwp, GWP_MAX)
    circularity_subscore = normalize_good(circularity, CIRCULARITY_MAX)
    cost_subscore = normalize_bad(cost, COST_MAX)

    # --- Step 2: Normalize weights to sum = 1.0 ---
    total_weight_sum = sum(weights.values()) or 1.0
    normalized_weights = {
        metric_name: weight_value / total_weight_sum
        for metric_name, weight_value in weights.items()
    }

    # --- Step 3: Compute weighted composite score ---
    overall_score = (
        gwp_subscore * normalized_weights["gwp"]
        + circularity_subscore * normalized_weights["circularity"]
        + cost_subscore * normalized_weights["cost"]
    )

    # Round to 2 decimals for clean display
    final_score = round(overall_score, 2)

    # Subscores returned for debugging and chart visualization
    subscore_dict = {
        "gwp": gwp_subscore,
        "circularity": circularity_subscore,
        "cost": cost_subscore,
    }

    return final_score, subscore_dict


def map_rating(score: float) -> str:
    """
    Convert a numeric 0–100 score into a letter rating bucket.

    Grading scale:
      90–100  → A+
      80–89   → A
      70–79   → B
      60–69   → C
      below 60 → D

    Returns:
        str : The rating label (e.g., "A+", "B", "D")
    """
    if score >= 90:
        return "A+"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    return "D"
