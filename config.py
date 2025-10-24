# config.py
import os

# Default normalization ranges
GWP_MAX = float(os.getenv("GWP_MAX", "50"))           # higher is worse
COST_MAX = float(os.getenv("COST_MAX", "100"))        # higher is worse
CIRCULARITY_MAX = float(os.getenv("CIRCULARITY_MAX", "100"))  # higher is better

# Default weights (must sum to 1.0)
DEFAULT_WEIGHTS = {
    "gwp": float(os.getenv("W_GWP", "0.5")),
    "circularity": float(os.getenv("W_CIRCULARITY", "0.3")),
    "cost": float(os.getenv("W_COST", "0.2")),
}

# Optional LLM hook (off by default)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "")          # e.g., "openai"
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

