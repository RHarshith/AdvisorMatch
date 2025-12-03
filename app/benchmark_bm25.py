import sqlite3
import argparse
import time
from rank_bm25 import BM25Okapi
from typing import List, Dict, Tuple
import re

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "advisormatch_openalex.db"

def simple_tokenize(text: str) -> List[str]:
    """Simple tokenizer: lowercase and split by non-alphanumeric"""
    if not text:
        return []
    return re.findall(r'\w+', text.lower())

def load_corpus(db_path: str) -> Tuple[List[str], List[Dict]]:
    """Load publications from database and prepare corpus"""
    print("Loading corpus from database...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT paper_id, title, abstract, year, citation_count, venue
        FROM publications
    """)
    
    documents = []
    metadata = []
    
    for row in cursor.fetchall():
        paper_id, title, abstract, year, citations, venue = row
        
        # Combine title and abstract for indexing
        text = f"{title} {abstract if abstract else ''}"
        documents.append(text)
        
        metadata.append({
            'paper_id': paper_id,
            'title': title,
            'year': year,
            'citations': citations,
            'venue': venue
        })
    
    conn.close()
    print(f"Loaded {len(documents)} documents.")
    return documents, metadata

def get_professor_for_paper(paper_id: str, db_path: str) -> str:
    """Get professor name for a paper"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.name 
        FROM professors p
        JOIN author_bridge ab ON p.id = ab.professor_id
        WHERE ab.paper_id = ?
        LIMIT 1
    """, (paper_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "Unknown"

def main():
    parser = argparse.ArgumentParser(description="BM25 Search Benchmark")
    parser.add_argument("query", type=str, help="Search query")
    parser.add_argument("--top_k", type=int, default=10, help="Number of results to return")
    args = parser.parse_args()
    
    start_time = time.time()
    
    # 1. Load Corpus
    documents, metadata = load_corpus(DB_PATH)
    
    # 2. Tokenize Corpus
    print("Tokenizing corpus...")
    tokenized_corpus = [simple_tokenize(doc) for doc in documents]
    
    # 3. Initialize BM25
    print("Initializing BM25...")
    bm25 = BM25Okapi(tokenized_corpus)
    
    # 4. Process Query
    tokenized_query = simple_tokenize(args.query)
    print(f"\nQuery: '{args.query}'")
    print(f"Tokens: {tokenized_query}")
    
    # 5. Get Scores
    doc_scores = bm25.get_scores(tokenized_query)
    
    # 6. Rank Results
    # Create list of (index, score) tuples and sort
    ranked_results = sorted(enumerate(doc_scores), key=lambda x: x[1], reverse=True)
    
    # 7. Display Results
    print(f"\n--- Top {args.top_k} BM25 Results ---")
    print(f"Search time: {(time.time() - start_time):.4f}s\n")
    
    for i in range(min(args.top_k, len(ranked_results))):
        idx, score = ranked_results[i]
        if score <= 0: break # Stop if no match
        
        meta = metadata[idx]
        prof_name = get_professor_for_paper(meta['paper_id'], DB_PATH)
        
        print(f"{i+1}. Score: {score:.4f}")
        print(f"   Title: {meta['title']}")
        print(f"   Professor: {prof_name}")
        print(f"   Year: {meta['year']}")
        print(f"   ID: {meta['paper_id']}")
        print("-" * 50)

if __name__ == "__main__":
    main()
