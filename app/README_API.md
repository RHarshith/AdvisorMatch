# AdvisorMatch API

FastAPI backend for semantic search of thesis advisors.

## Quick Start

### 1. Start the API Server

```bash
cd app
python3 api.py
```

Or with uvicorn directly:
```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: **http://localhost:8000**

### 2. View API Documentation

Open your browser and visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## API Endpoints

### POST /api/search
Search for advisors based on research query.

**Request:**
```json
{
  "query": "machine learning for robotics",
  "top_k": 10,
  "include_publications": true
}
```

**Response:**
```json
{
  "query": "machine learning for robotics",
  "results": [
    {
      "professor_id": 42,
      "name": "Jason O'Kane",
      "department": "CSE",
      "college": "TAMU",
      "final_score": 0.85,
      "avg_similarity": 0.42,
      "recency_weight": 0.95,
      "activity_bonus": 0.15,
      "num_matching_papers": 3,
      "top_publications": [...]
    }
  ],
  "total_results": 10,
  "search_time_ms": 45
}
```

### GET /api/professor/{id}
Get detailed professor information.

### GET /api/publication/{paper_id}
Get detailed publication information.

### GET /health
Health check endpoint.

## Testing with cURL

```bash
# Search for advisors
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "top_k": 5}'

# Get professor details
curl http://localhost:8000/api/professor/42

# Health check
curl http://localhost:8000/health
```

## Testing with Python

```python
import requests

# Search
response = requests.post('http://localhost:8000/api/search', json={
    'query': 'natural language processing',
    'top_k': 5,
    'include_publications': True
})
results = response.json()

# Get professor
prof = requests.get('http://localhost:8000/api/professor/42').json()
```

## Ranking Algorithm

The API uses an enhanced ranking algorithm:

```
final_score = (avg_similarity × recency_weight) + activity_bonus
```

**Components:**
1. **Average Similarity** - Mean similarity of top-5 papers per professor
2. **Recency Weight** - Exponential decay (10% per year)
3. **Activity Bonus** - Bonus for recent publications (last 2 years)

## Configuration

Edit `config.py` to adjust:
- `TOP_K_PAPERS`: Number of papers to retrieve (default: 50)
- `TOP_N_PER_PROFESSOR`: Papers to consider per professor (default: 5)
- `DECAY_RATE`: Recency decay rate (default: 0.1)
- `ACTIVITY_THRESHOLD_YEARS`: Years for activity bonus (default: 2)

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn api:app --reload

# Run tests (if implemented)
pytest
```

## Architecture

```
app/
├── api.py              # FastAPI application
├── ranking.py          # Ranking algorithm
├── models.py           # Pydantic models
├── config.py           # Configuration
├── advisormatch_openalex.db
├── faiss_index.bin
└── paper_id_mapping.json
```
