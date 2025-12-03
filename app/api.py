"""
AdvisorMatch FastAPI Application

REST API for semantic search of thesis advisors based on research interests.
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import sqlite3
import json
import time
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from config import (
    API_TITLE, API_VERSION, API_DESCRIPTION, CORS_ORIGINS,
    DB_PATH, INDEX_PATH, MAPPING_PATH, MODEL_NAME, TOP_K_PAPERS
)
from models import (
    SearchRequest, SearchResponse, ProfessorResult, PublicationSummary,
    ProfessorDetail, PublicationDetail, HealthResponse
)
from ranking import (
    rank_professors, get_professor_details, get_publication_details
)

# Initialize FastAPI app
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION
)

# Add CORS middleware - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (including file://)
    allow_credentials=False,  # Set to False when using allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for model, index, and mapping
model = None
index = None
paper_mapping = None


@app.on_event("startup")
async def startup_event():
    """Load model, FAISS index, and paper mapping on startup"""
    global model, index, paper_mapping
    
    print("Loading Sentence-BERT model...")
    model = SentenceTransformer(MODEL_NAME)
    
    print("Loading FAISS index...")
    index = faiss.read_index(str(INDEX_PATH))
    
    print("Loading paper ID mapping...")
    with open(MAPPING_PATH, 'r') as f:
        paper_mapping = json.load(f)
    # Convert string keys to integers
    paper_mapping = {int(k): v for k, v in paper_mapping.items()}
    
    print(f"✓ Startup complete. Index size: {index.ntotal} vectors")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "AdvisorMatch API",
        "version": API_VERSION,
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    db_connected = False
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM professors")
        cursor.fetchone()
        conn.close()
        db_connected = True
    except:
        pass
    
    return HealthResponse(
        status="healthy" if all([model, index, paper_mapping, db_connected]) else "degraded",
        version=API_VERSION,
        database_connected=db_connected,
        index_loaded=index is not None,
        model_loaded=model is not None
    )


@app.post("/api/search", response_model=SearchResponse, tags=["Search"])
async def search_advisors(request: SearchRequest):
    """
    Search for advisors based on research query.
    
    Uses semantic search with enhanced ranking algorithm that considers:
    - Semantic similarity to query
    - Publication recency (exponential decay)
    - Author activity (recent publications bonus)
    - Citation impact (log-normalized citation counts)
    """
    start_time = time.time()
    
    # Validate model and index are loaded
    if not all([model, index, paper_mapping]):
        raise HTTPException(status_code=503, detail="Service not ready. Model or index not loaded.")
    
    try:
        # Generate query embedding
        query_embedding = model.encode([request.query], normalize_embeddings=True)
        query_embedding = query_embedding.astype('float32')
        
        # Search FAISS index
        distances, indices = index.search(query_embedding, TOP_K_PAPERS)
        
        # Get paper IDs and similarities
        paper_ids = [paper_mapping[idx] for idx in indices[0]]
        similarities = distances[0].tolist()
        
        # Connect to database
        conn = sqlite3.connect(str(DB_PATH))
        
        # Rank professors
        rankings = rank_professors(paper_ids, similarities, conn, top_k=request.top_k)
        
        # Build response
        results = []
        for ranking in rankings:
            prof_id = ranking['professor_id']
            
            # Get professor details
            prof_details = get_professor_details(prof_id, conn)
            if not prof_details:
                continue
            
            # Get top publications if requested
            top_pubs = None
            if request.include_publications:
                top_pubs = []
                for paper_id in ranking['top_paper_ids'][:3]:  # Top 3 publications
                    pub_details = get_publication_details(paper_id, conn)
                    if pub_details:
                        # Find similarity for this paper
                        try:
                            paper_idx = paper_ids.index(paper_id)
                            similarity = similarities[paper_idx]
                        except ValueError:
                            similarity = 0.0
                        
                        top_pubs.append(PublicationSummary(
                            paper_id=pub_details['paper_id'],
                            title=pub_details['title'],
                            year=pub_details['year'],
                            similarity=similarity,
                            citations=pub_details['citation_count'],
                            venue=pub_details['venue']
                        ))
            
            # Create professor result
            results.append(ProfessorResult(
                professor_id=prof_id,
                name=prof_details['name'],
                department=prof_details['department'],
                college=prof_details['college'],
                interests=prof_details['interests'],
                url=prof_details['url'],
                final_score=ranking['final_score'],
                avg_similarity=ranking['avg_similarity'],
                recency_weight=ranking['recency_weight'],
                activity_bonus=ranking['activity_bonus'],
                citation_impact=ranking['citation_impact'],
                num_matching_papers=ranking['num_matching_papers'],
                top_publications=top_pubs
            ))
        
        conn.close()
        
        # Calculate search time
        search_time_ms = (time.time() - start_time) * 1000
        
        return SearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
            search_time_ms=search_time_ms
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/api/professor/{professor_id}", response_model=ProfessorDetail, tags=["Professors"])
async def get_professor(professor_id: int):
    """Get detailed information about a specific professor"""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        prof_details = get_professor_details(professor_id, conn)
        conn.close()
        
        if not prof_details:
            raise HTTPException(status_code=404, detail="Professor not found")
        
        return ProfessorDetail(**prof_details)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve professor: {str(e)}")


@app.get("/api/publication/{paper_id}", response_model=PublicationDetail, tags=["Publications"])
async def get_publication(paper_id: str):
    """Get detailed information about a specific publication"""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        pub_details = get_publication_details(paper_id, conn)
        conn.close()
        
        if not pub_details:
            raise HTTPException(status_code=404, detail="Publication not found")
        
        return PublicationDetail(**pub_details)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve publication: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
