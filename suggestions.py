# suggestions.py
from typing import List, Dict
from config import LLM_PROVIDER, LLM_API_KEY

# RULES is a list of (predicate, suggestion_text) pairs.
# Each predicate is a function that inspects the raw payload dict and returns True/False.
# If the predicate returns True, we include the associated suggestion_text in the output.
RULES = [
    # --- Transport-related suggestions ---
    (
        lambda product: str(product.get("transport", "")).lower() == "air",
        "Avoid air transport where possible; prefer sea or rail to cut emissions.",
    ),
    (
        lambda product: str(product.get("transport", "")).lower() in {"road", "truck"},
        "Optimize logistics and consolidate shipments to reduce road-miles.",
    ),

    # --- Materials-related suggestions ---
    (
        lambda product: any(
            "plastic" in material.lower()
            for material in product.get("materials", [])
            if isinstance(material, str)
        ),
        "Reduce or replace plastic with recycled content or bio-based alternatives.",
    ),
    (
        lambda product: any(
            "aluminum" in material.lower()
            for material in product.get("materials", [])
            if isinstance(material, str)
        ),
        "Use high-recycled-content aluminum and closed-loop scrap recovery.",
    ),
    (
        lambda product: any(
            "steel" in material.lower()
            for material in product.get("materials", [])
            if isinstance(material, str)
        ),
        "Prefer low-carbon (EAF) steel or suppliers with verified green steel.",
    ),

    # --- Packaging-related suggestions ---
    (
        lambda product: str(product.get("packaging", "")).lower()
        not in {"recyclable", "biodegradable", "compostable"},
        "Switch to recyclable/compostable packaging and minimize material usage.",
    ),
    (
        lambda product: str(product.get("packaging", "")).lower() == "recyclable",
        "Add clear recycling instructions and minimize inks/laminates.",
    ),

    # --- Weight / design efficiency suggestions ---
    (
        lambda product: float(product.get("weight_grams", 0)) > 500,
        "Lightweight the product via design-for-minimal-mass and material swaps.",
    ),
    (
        lambda product: float(product.get("circularity", 0)) < 60,
        "Increase circularity: design for disassembly, repairability, and parts reuse.",
    ),

    # --- GWP & cost threshold suggestions ---
    (
        lambda product: float(product.get("gwp", 0)) > 20,
        "Target high-impact stages (materials & transport) to lower GWP substantially.",
    ),
    (
        lambda product: float(product.get("cost", 0)) > 50,
        "Lower cost via material optimization, supplier consolidation, or design simplification.",
    ),
]


def rule_based_suggestions(request_payload: Dict) -> List[str]:
    """
    Generate sustainability improvement suggestions using static, rule-based heuristics.

    How it works:
    - We evaluate each (predicate, message) pair in RULES against the raw request payload.
    - If the predicate returns True, we include the message.
    - We deduplicate messages so we don't repeat the same tip twice.

    Fallback:
    - If no rules fire at all, we still return a generic "you're already good" style suggestion.

    Parameters:
        request_payload: dict directly from the API call body (not the dataclass),
                         e.g. {
                           "transport": "air",
                           "materials": ["plastic", "aluminum"],
                           "packaging": "recyclable",
                           ...
                         }

    Returns:
        A list of unique human-readable suggestions (List[str]).
    """

    used_suggestion_texts = set()     # to prevent duplicate suggestions
    suggestion_list: List[str] = []   # final list to return

    for predicate_fn, suggestion_text in RULES:
        try:
            # If the rule applies AND we haven't already added this same suggestion_text
            if predicate_fn(request_payload) and suggestion_text not in used_suggestion_texts:
                used_suggestion_texts.add(suggestion_text)
                suggestion_list.append(suggestion_text)
        except Exception:
            # If a rule throws (bad type, etc.), skip it silently.
            # We don't want a single bad rule to kill the whole API response.
            continue

    # If nothing specific triggered, provide at least one positive baseline suggestion
    if not suggestion_list:
        suggestion_list.append(
            "Product already performs well; focus on supplier transparency and continuous improvement."
        )

    return suggestion_list


import openai

def llm_supplement(request_payload: Dict, llm_summary_text: str) -> List[str]:
    if not (LLM_PROVIDER == "openai" and LLM_API_KEY):
        return []

    try:
        openai.api_key = LLM_API_KEY

        llm_prompt = (
            "You are a sustainability analyst. Based on the product payload and summary, "
            "suggest up to 3 concise, actionable improvements. "
            "Avoid duplicates of common tips. Output as plain bullet lines (no numbering):\n\n"
            f"Payload: {request_payload}\n"
            f"Summary: {llm_summary_text}"
        )

        completion_response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": llm_prompt}
            ],
            temperature=0.2,
            max_tokens=180,
        )

        model_raw_text = completion_response["choices"][0]["message"]["content"] or ""
        cleaned_suggestions: List[str] = []
        for raw_line in model_raw_text.splitlines():
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            normalized_line = raw_line.strip("-• ").strip()
            if normalized_line and normalized_line not in cleaned_suggestions:
                cleaned_suggestions.append(normalized_line)
            if len(cleaned_suggestions) >= 3:
                break

        return cleaned_suggestions

    except Exception as e:
        print("Error occurred:", e)
        return []


