# app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from sqlalchemy import func

from db import init_db, SessionLocal, ProductScore
from models import ScorePayload
from scoring import compute_score, map_rating
from suggestions import rule_based_suggestions, llm_supplement
from config import DEFAULT_WEIGHTS

app = Flask(__name__, static_folder="frontend")
CORS(app)

# Ensure tables exist on startup (no-op if they already do)
init_db()


def parse_weights(payload_weights, query_args):
    """
    Determine which scoring weights to use for this request.

    Priority:
    1. request.json["weights"] (payload_weights)
    2. query string overrides (?w_gwp=...&w_circularity=...&w_cost=...)
    3. DEFAULT_WEIGHTS from config

    After merging, weights are normalized so that they sum to 1.0.

    Example final dict:
        {
          "gwp": 0.5,
          "circularity": 0.3,
          "cost": 0.2
        }
    """

    # Start with global defaults so we always have something sane
    chosen_weights = dict(DEFAULT_WEIGHTS)

    # Override using explicit weights passed in the JSON payload (if present)
    if isinstance(payload_weights, dict):
        for weight_key in ("gwp", "circularity", "cost"):
            if weight_key in payload_weights:
                try:
                    chosen_weights[weight_key] = float(payload_weights[weight_key])
                except Exception:
                    # If casting fails, ignore and keep previous value
                    pass

    # Override using query string params (e.g. ?w_gwp=0.5)
    for weight_key in ("gwp", "circularity", "cost"):
        query_param_key = f"w_{weight_key}"
        if query_param_key in query_args:
            try:
                chosen_weights[weight_key] = float(query_args[query_param_key])
            except Exception:
                # Ignore invalid numbers
                pass

    # Normalize weights so their sum is 1.0
    total_weight_sum = sum(chosen_weights.values()) or 1.0
    normalized_weights = {
        weight_key: weight_value / total_weight_sum
        for weight_key, weight_value in chosen_weights.items()
    }

    return normalized_weights


@app.route("/score", methods=["POST"])
def score():
    """
    POST /score

    Request body JSON example:
    {
      "product_name": "Reusable Bottle",
      "materials": ["aluminum","plastic"],
      "weight_grams": 300,
      "transport": "air",
      "packaging": "recyclable",
      "gwp": 5.0,
      "cost": 10.0,
      "circularity": 80.0,
      "weights": {"gwp":0.5,"circularity":0.3,"cost":0.2}  # optional
    }

    What this route does:
    1. Parse and validate user payload
    2. Resolve weights (payload + query overrides, normalized)
    3. Compute sustainability score and rating
    4. Generate improvement suggestions (rule-based + AI/LLM)
    5. Persist one ProductScore row in the DB
    6. Return a detailed JSON response including subscores, suggestions, etc.

    Response JSON includes:
    {
      "product_name": "...",
      "sustainability_score": <float>,
      "rating": "A" | "B" | ...,
      "subscores": {...},
      "weights": {...},
      "suggestions": [... all unique suggestions ...],
      "ai_suggestions": [... only AI suggestions ...],
      "rule_suggestions": [... only rule suggestions ...]
    }
    """

    # Safely read incoming JSON (returns {} if body is empty/invalid)
    request_data = request.get_json(silent=True) or {}

    # Convert raw dict to a strongly-typed payload object
    payload = ScorePayload.from_dict(request_data)

    # Perform payload-level validation (required fields, ranges, etc.)
    validation_errors = payload.validate()
    if validation_errors:
        return jsonify({
            "error": "validation_error",
            "details": validation_errors
        }), 400

    # Compute the effective weights (JSON weights + query overrides + defaults)
    normalized_weights = parse_weights(payload.weights, request.args)

    # Calculate final sustainability score and the component subscores
    # compute_score(...) should return:
    #   overall_score (float), subscore_breakdown (dict)
    overall_score, subscore_breakdown = compute_score(
        payload.gwp,
        payload.circularity,
        payload.cost,
        normalized_weights
    )

    # Map numeric score to a discrete rating label like "A", "B", etc.
    rating_letter = map_rating(overall_score)

    # Human-readable summary string describing the product,
    # sent to the LLM to give it context for suggestions.
    llm_summary_text = (
        f"{payload.product_name}: "
        f"GWP={payload.gwp}, "
        f"Circularity={payload.circularity}, "
        f"Cost={payload.cost}, "
        f"Transport={payload.transport}, "
        f"Packaging={payload.packaging} "
        f"→ Score={overall_score} ({rating_letter})"
    )

    # Rule-based suggestions (deterministic heuristics) from suggestions.py
    rule_suggestion_list = rule_based_suggestions(request_data)

    # AI-driven suggestions (LLM) from suggestions.py
    ai_suggestion_list = llm_supplement(request_data, llm_summary_text)

    # Merge both suggestion lists, keeping order but removing duplicates
    merged_suggestion_list = []
    seen_suggestions = set()
    for suggestion_text in (rule_suggestion_list + ai_suggestion_list):
        if suggestion_text and suggestion_text not in seen_suggestions:
            seen_suggestions.add(suggestion_text)
            merged_suggestion_list.append(suggestion_text)

    # Persist the request + results into the database
    db_session = SessionLocal()
    db_record = ProductScore(
        product_name=payload.product_name,
        materials=payload.materials,
        weight_grams=payload.weight_grams,
        transport=payload.transport,
        packaging=payload.packaging,
        gwp=payload.gwp,
        cost=payload.cost,
        circularity=payload.circularity,
        sustainability_score=overall_score,
        rating=rating_letter,
        suggestions=merged_suggestion_list,  # stored combined
        raw_payload=request_data,            # full raw request for traceability / audit
    )
    db_session.add(db_record)
    db_session.commit()

    # Build the API response
    response_body = {
        "product_name": payload.product_name,
        "sustainability_score": overall_score,
        "rating": rating_letter,
        "subscores": subscore_breakdown,
        "weights": normalized_weights,
        "suggestions": merged_suggestion_list,       # merged (for backward compatibility)
        "ai_suggestions": ai_suggestion_list,        # AI-only
        "rule_suggestions": rule_suggestion_list     # rule-only
    }

    return jsonify(response_body), 200


@app.route("/history", methods=["GET"])
def history():
    """
    GET /history?limit=50

    Returns most recent scored products (newest first), up to `limit`.

    Query params:
      limit (optional, int): max number of records to return. Default 50.

    Response example:
    [
      {
        "id": 12,
        "created_at": "2025-10-24T15:30:00Z",
        "product_name": "Reusable Bottle",
        "sustainability_score": 82.1,
        "rating": "A",
        "gwp": 5.0,
        "cost": 10.0,
        "circularity": 80.0,
        "transport": "air",
        "packaging": "recyclable",
        "materials": ["aluminum","plastic"]
      },
      ...
    ]
    """

    # Parse `limit` from query params, fallback to 50 on any error
    try:
        result_limit = int(request.args.get("limit", "50"))
    except Exception:
        result_limit = 50

    db_session = SessionLocal()

    # Query most recent ProductScore rows
    recent_scores_query = (
        db_session
        .query(ProductScore)
        .order_by(ProductScore.created_at.desc())
        .limit(result_limit)
    )

    recent_score_rows = recent_scores_query.all()

    # Serialize DB rows to plain dicts for JSON response
    history_payload = [
        {
            "id": score_row.id,
            "created_at": score_row.created_at.isoformat() + "Z",
            "product_name": score_row.product_name,
            "sustainability_score": score_row.sustainability_score,
            "rating": score_row.rating,
            "gwp": score_row.gwp,
            "cost": score_row.cost,
            "circularity": score_row.circularity,
            "transport": score_row.transport,
            "packaging": score_row.packaging,
            "materials": score_row.materials,
        }
        for score_row in recent_score_rows
    ]

    return jsonify(history_payload), 200


@app.route("/score-summary", methods=["GET"])
def score_summary():
    """
    GET /score-summary

    Returns high-level analytics across all stored ProductScore rows:
      - total_products: how many products have been scored
      - average_score: mean of sustainability_score across all products (rounded to 2 decimals)
      - ratings: histogram of ratings, e.g. {"A": 2, "B": 5, "C": 1}
      - top_issues: most common suggestion texts (top 5 across all products)

    Response example:
    {
      "total_products": 27,
      "average_score": 74.22,
      "ratings": {"A": 8, "B": 12, "C": 7},
      "top_issues": [
        "Switch to recycled packaging",
        "Reduce air freight usage",
        ...
      ]
    }
    """

    db_session = SessionLocal()

    # --- Aggregate counts and averages ---

    # Total number of scored products
    total_products = int(db_session.query(func.count(ProductScore.id)).scalar() or 0)

    # Average of all sustainability_score values
    average_score_val = float(
        db_session.query(func.avg(ProductScore.sustainability_score)).scalar() or 0.0
    )
    average_score_val = round(average_score_val, 2)

    # --- Rating histogram ---
    # Result shape from query:
    #   [
    #     ("A", 10),
    #     ("B", 4),
    #     ("C", 1),
    #   ]
    rating_count_pairs = (
        db_session
        .query(ProductScore.rating, func.count(ProductScore.id))
        .group_by(ProductScore.rating)
        .all()
    )
    # Convert list of tuples -> dict like {"A": 10, "B": 4, ...}
    rating_histogram = {rating_value: count for rating_value, count in rating_count_pairs}

    # --- Top recurring suggestions ---
    # We'll gather all 'suggestions' arrays from every row, then count frequency of each suggestion string.
    suggestion_frequency_map = {}

    # Each row returns a single column: ProductScore.suggestions
    all_suggestions_rows = db_session.query(ProductScore.suggestions).all()

    for (suggestions_list,) in all_suggestions_rows:
        # suggestions_list is expected to be a list[str] or None
        if not suggestions_list:
            continue
        for suggestion_text in suggestions_list:
            suggestion_frequency_map[suggestion_text] = (
                suggestion_frequency_map.get(suggestion_text, 0) + 1
            )

    # Sort suggestions by frequency (descending), take top 5
    sorted_suggestions = sorted(
        suggestion_frequency_map.items(),
        key=lambda kv: kv[1],
        reverse=True
    )
    top_issues = [suggestion for suggestion, _freq in sorted_suggestions[:5]]

    # Final response body
    summary_payload = {
        "total_products": total_products,
        "average_score": average_score_val,
        "ratings": rating_histogram,
        "top_issues": top_issues
    }

    return jsonify(summary_payload), 200


# Serve the tiny dashboard frontend (static index.html in ./frontend)
@app.route("/")
def index():
    """
    GET /

    Serves the dashboard UI (frontend/index.html).
    This lets someone open the root URL in a browser and see:
      - recent products
      - charts/graphs built off /score-summary and /history
    """
    return send_from_directory("frontend", "index.html")


if __name__ == "__main__":
    # NOTE:
    # - host="0.0.0.0" allows external access (e.g. from Docker or LAN)
    # - debug=True is ONLY for local dev; turn it off in prod
    app.run(host="0.0.0.0", port=5055, debug=True)
