# AdvisorMatch: AI-Powered Thesis Advisor Search

> Find your perfect thesis advisor using semantic search powered by machine learning

A full-stack web application that helps graduate students find suitable thesis advisors by matching their research interests with faculty expertise using natural language processing and semantic search.

## 🎯 Features

- **Semantic Search**: Uses Sentence-BERT embeddings to understand research interests beyond keyword matching
- **Enhanced Ranking**: Combines similarity scores with recency weighting and activity bonuses
- **Fast Search**: Sub-100ms response times with FAISS indexing
- **Modern UI**: Clean, responsive interface with Texas A&M branding
- **REST API**: Well-documented FastAPI backend with Swagger UI

## 🏗️ Architecture

```
AdvisorMatch/
├── app/                          # Backend API
│   ├── api.py                    # FastAPI application
│   ├── ranking.py                # Ranking algorithm
│   ├── models.py                 # Pydantic models
│   ├── config.py                 # Configuration
│   ├── generate_embeddings.py    # Embedding generation
│   ├── build_faiss_index.py      # FAISS index builder
│   ├── test_search.py            # Search testing
│   ├── advisormatch_openalex.db  # SQLite database
│   ├── faiss_index.bin           # FAISS index
│   └── paper_id_mapping.json     # Index mappings
├── frontend/                     # Web interface
│   ├── index.html                # Main page
│   ├── css/styles.css            # Styling
│   └── js/app.js                 # Application logic
└── requirements.txt              # Python dependencies
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Modern web browser

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Backend API

```bash
cd app
python3 api.py
```

The API will be available at: **http://localhost:8000**

### 3. Open the Frontend

```bash
cd frontend
open index.html  # macOS
# or just double-click index.html
```

### 4. Search for Advisors!

Enter your research interests (e.g., "machine learning for robotics") and get ranked results.

## 📊 How It Works

### 1. Data Collection
- Scrapes faculty information from university website
- Fetches publications from OpenAlex API
- Stores in SQLite database

### 2. Embedding Generation
- Uses Sentence-BERT (all-MiniLM-L6-v2) model
- Generates 384-dimensional embeddings for each publication
- Combines title + abstract for comprehensive representation

### 3. Indexing
- Builds FAISS index for efficient similarity search
- Enables sub-second search across 400+ publications

### 4. Ranking Algorithm

```
final_score = (avg_similarity × recency_weight) + activity_bonus
```

**Components:**
- **Similarity**: Average of top-5 most similar papers per professor
- **Recency**: Exponential decay (10% per year)
- **Activity**: Bonus for recent publications (last 2 years)

### 5. Search & Display
- User enters natural language query
- System finds semantically similar publications
- Aggregates and ranks professors
- Displays results with explanations

## 🔧 API Endpoints

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

### GET /api/professor/{id}
Get detailed professor information.

### GET /api/publication/{paper_id}
Get detailed publication information.

### GET /health
Health check endpoint.

**API Documentation:** http://localhost:8000/docs

## 📈 Dataset

- **Professors**: 85 faculty members from TAMU CSE
- **Publications**: 402 research papers
- **Embeddings**: 384-dimensional vectors
- **Index Size**: ~600KB

## 🎨 Frontend Features

- **Modern Design**: Texas A&M maroon and gold color scheme
- **Responsive Layout**: Works on desktop and mobile
- **Real-time Search**: Instant feedback with loading states
- **Detailed Results**: Score breakdowns and top publications
- **Error Handling**: Clear error messages and troubleshooting

## 🧪 Testing

### Test the API
```bash
# Health check
curl http://localhost:8000/health

# Search
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "top_k": 5}'
```

### Test Search Functionality
```bash
cd app
python3 test_search.py "natural language processing" --top-k 5 --authors
```

## 📚 Documentation

- **Frontend**: [frontend/README.md](frontend/README.md)
- **API**: [app/README_API.md](app/README_API.md)
- **Embeddings**: [app/README_EMBEDDINGS.md](app/README_EMBEDDINGS.md)
- **API Docs**: http://localhost:8000/docs (when server is running)

## 🛠️ Development

### Regenerate Embeddings
```bash
cd app
python3 generate_embeddings.py
```

### Rebuild FAISS Index
```bash
cd app
python3 build_faiss_index.py --verify
```

### Update Database
```bash
cd app
python3 ingest.py
```

## 📝 Project Timeline

- **Week 1**: Data collection and database setup ✅
- **Week 2**: Vector embeddings and FAISS indexing ✅
- **Week 3**: Backend API with enhanced ranking ✅
- **Week 4**: Frontend and final polish ✅

## 👥 Team

- **Course**: CSCE 670 - Information Storage and Retrieval
- **Institution**: Texas A&M University
- **Department**: Computer Science and Engineering

## 📄 License

This project was created for educational purposes as part of CSCE 670.

## 🙏 Acknowledgments

- OpenAlex API for publication data
- Sentence-Transformers library for embeddings
- FAISS library for efficient similarity search
- FastAPI framework for the backend API

---

**Made with ❤️ at Texas A&M University**
