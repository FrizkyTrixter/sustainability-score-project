# models.py
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class ScorePayload:
    """
    ScorePayload represents the request body for /score.

    Fields:
      product_name   : Name of the product being evaluated.
      materials      : List of material names (e.g. ["aluminum", "plastic"]).
      weight_grams   : Mass of the product in grams.
      transport      : Transport mode (e.g. "air", "sea", "truck", etc.).
      packaging      : Packaging description/type (e.g. "recyclable", "plastic wrap").
      gwp            : Global Warming Potential metric for the product (impact score).
      cost           : Cost of the product (numerical, assumed currency unit known to caller).
      circularity    : Circularity / recyclability score (0-100 or whatever your convention is).
      weights        : Optional object with custom weights for gwp/circularity/cost.
                       If provided, this overrides the default scoring weights.

    This dataclass is used as a clean typed internal representation after we
    parse and sanitize the raw JSON payload from the incoming Flask request.
    """

    product_name: str
    materials: List[str] = field(default_factory=list)
    weight_grams: float = 0.0
    transport: str = ""
    packaging: str = ""
    gwp: float = 0.0
    cost: float = 0.0
    circularity: float = 0.0
    # Optional per-request weights override (example: {"gwp":0.5,"circularity":0.3,"cost":0.2})
    weights: Optional[Dict[str, float]] = None

    @staticmethod
    def from_dict(raw_dict: Dict[str, Any]) -> "ScorePayload":
        """
        Safely construct a ScorePayload from an arbitrary dict (e.g. request.json).

        - Forces numeric-looking fields to float, with fallback defaults.
        - Strips the product_name.
        - Normalizes 'materials' into a list of strings.
        - Leaves 'weights' as-is (may be None or dict).

        We intentionally do not trust the raw incoming data types
        because Flask's request.get_json() can give us e.g. strings for numbers.
        """

        def to_float_maybe(value: Any, default: float = 0.0) -> float:
            """
            Try to convert `value` to float.
            If it fails, return `default` instead of raising.
            """
            try:
                return float(value)
            except Exception:
                return default

        return ScorePayload(
            product_name=str(raw_dict.get("product_name", "")).strip(),

            # Accepts any value in "materials" that is str/int/float and casts to str.
            # Filters out anything weird (like dicts or lists).
            materials=[
                str(material)
                for material in raw_dict.get("materials", [])
                if isinstance(material, (str, int, float))
            ],

            weight_grams=to_float_maybe(raw_dict.get("weight_grams", 0.0)),
            transport=str(raw_dict.get("transport", "")),
            packaging=str(raw_dict.get("packaging", "")),
            gwp=to_float_maybe(raw_dict.get("gwp", 0.0)),
            cost=to_float_maybe(raw_dict.get("cost", 0.0)),
            circularity=to_float_maybe(raw_dict.get("circularity", 0.0)),

            # weights stays raw here (dict or None); normalization happens later in parse_weights
            weights=raw_dict.get("weights"),
        )

    def validate(self) -> List[str]:
        """
        Validate that the required/critical fields in this payload are well-formed.

        Current validation rules:
        - product_name must not be empty.
        - gwp, cost, circularity, weight_grams must all be >= 0.

        Returns:
            A list of human-readable error strings. Empty list means "valid".
        """
        error_messages: List[str] = []

        # Require a product name so we can identify rows in history, summary tables, etc.
        if not self.product_name:
            error_messages.append("product_name is required.")

        # Ensure numeric fields are non-negative.
        for numeric_field_name in ["gwp", "cost", "circularity", "weight_grams"]:
            numeric_value = getattr(self, numeric_field_name)
            if numeric_value < 0:
                error_messages.append(f"{numeric_field_name} must be >= 0.")

        return error_messages
