# Vrtta Sustainability Scoring (Flask + SQLite + Tiny Dashboard)

### Endpoints

- `POST /score` → computes score, rating, suggestions, persists to SQLite  
- `GET /history?limit=50` → latest submissions  
- `GET /score-summary` → totals, average, ratings histogram, top issues  

Weights can be passed in the JSON body under `weights` or in the query string (`?w_gwp=&w_circularity=&w_cost=`). They auto-normalize.

### Quickstart

```bash
python -m venv .venv
. .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# (Optional) Create a .env file to override defaults or enable AI suggestions
# Example:
#   echo "LLM_PROVIDER=openai" >> .env
#   echo "LLM_API_KEY=sk-your-openai-key" >> .env
#   echo "GWP_MAX=50" >> .env
#   echo "COST_MAX=100" >> .env
#   echo "CIRCULARITY_MAX=100" >> .env

python app.py          # serves API + dashboard on http://localhost:5055

# Run unit tests

python -m unittest discover tests

