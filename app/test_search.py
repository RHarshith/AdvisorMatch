#!/usr/bin/env python3
"""
Test semantic search using FAISS index.

This script loads the FAISS index and performs semantic search
to find publications similar to a given query.

Usage:
    python3 test_search.py "your research query here" [--top-k N]
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import sqlite3
import numpy as np
import pickle
import json
import sys
import argparse
import faiss
from sentence_transformers import SentenceTransformer

DB_NAME = "advisormatch.db"
INDEX_FILE = "faiss_index.bin"
MAPPING_FILE = "paper_id_mapping.json"
MODEL_NAME = "all-MiniLM-L6-v2"  # 384-dimensional embeddings

def load_model():
    """Load the Sentence-BERT model."""
    print(f"Loading model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    return model

def load_faiss_index():
    """Load FAISS index from disk."""
    print(f"Loading FAISS index from: {INDEX_FILE}")
    index = faiss.read_index(INDEX_FILE)
    print(f"✓ Index loaded: {index.ntotal} vectors")
    return index

def load_paper_mapping():
    """Load paper ID mapping from disk."""
    print(f"Loading paper mapping from: {MAPPING_FILE}")
    with open(MAPPING_FILE, 'r') as f:
        mapping = json.load(f)
    # Convert string keys back to integers
    mapping = {int(k): v for k, v in mapping.items()}
    return mapping

def get_publication_details(conn, paper_ids: list):
    """
    Fetch publication details from database.
    Returns: dict of paper_id -> (title, year, citations, venue, abstract)
    """
    cursor = conn.cursor()
    
    # Create placeholders for SQL IN clause
    placeholders = ','.join('?' * len(paper_ids))
    
    cursor.execute(f"""
        SELECT paper_id, title, year, citation_count, venue, abstract
        FROM publications
        WHERE paper_id IN ({placeholders})
    """, paper_ids)
    
    results = {}
    for row in cursor.fetchall():
        paper_id, title, year, citations, venue, abstract = row
        results[paper_id] = {
            'title': title,
            'year': year,
            'citations': citations,
            'venue': venue,
            'abstract': abstract
        }
    
    return results

def search(query: str, model, index: faiss.Index, mapping: dict, conn, top_k: int = 10):
    """
    Perform semantic search for the query.
    """
    print(f"\nQuery: \"{query}\"")
    print("="*80)
    
    # Generate query embedding
    print("Generating query embedding...")
    query_embedding = model.encode([query], normalize_embeddings=True)
    query_embedding = query_embedding.astype('float32')
    
    # Search FAISS index
    print(f"Searching for top {top_k} similar publications...")
    distances, indices = index.search(query_embedding, top_k)
    
    # Get paper IDs
    paper_ids = [mapping[idx] for idx in indices[0]]
    
    # Fetch publication details
    publications = get_publication_details(conn, paper_ids)
    
    # Display results
    print(f"\nTop {top_k} Results:")
    print("="*80)
    
    for i, (idx, dist) in enumerate(zip(indices[0], distances[0]), 1):
        paper_id = mapping[idx]
        pub = publications.get(paper_id, {})
        
        print(f"\n[{i}] Similarity: {dist:.4f}")
        print(f"    Title: {pub.get('title', 'N/A')}")
        print(f"    Year: {pub.get('year', 'N/A')}")
        print(f"    Citations: {pub.get('citations', 'N/A')}")
        print(f"    Venue: {pub.get('venue', 'N/A')}")
        
        abstract = pub.get('abstract', '')
        if abstract:
            preview = abstract[:200] + "..." if len(abstract) > 200 else abstract
            print(f"    Abstract: {preview}")
        
        print("-"*80)

def get_author_rankings(conn, paper_ids: list, similarities: list, top_n: int = 5):
    """
    Aggregate paper results to rank authors.
    Simple version: count papers per author and average similarity.
    """
    cursor = conn.cursor()
    
    # Get authors for these papers
    placeholders = ','.join('?' * len(paper_ids))
    cursor.execute(f"""
        SELECT ab.professor_id, p.name, pub.paper_id
        FROM author_bridge ab
        JOIN professors p ON ab.professor_id = p.id
        JOIN publications pub ON ab.paper_id = pub.paper_id
        WHERE pub.paper_id IN ({placeholders})
    """, paper_ids)
    
    # Aggregate by professor
    professor_scores = {}
    for prof_id, prof_name, paper_id in cursor.fetchall():
        if prof_id not in professor_scores:
            professor_scores[prof_id] = {
                'name': prof_name,
                'papers': [],
                'similarities': []
            }
        
        # Find similarity for this paper
        paper_idx = paper_ids.index(paper_id)
        similarity = similarities[paper_idx]
        
        professor_scores[prof_id]['papers'].append(paper_id)
        professor_scores[prof_id]['similarities'].append(similarity)
    
    # Calculate average similarity for each professor
    rankings = []
    for prof_id, data in professor_scores.items():
        avg_similarity = np.mean(data['similarities'])
        rankings.append({
            'professor_id': prof_id,
            'name': data['name'],
            'avg_similarity': avg_similarity,
            'num_papers': len(data['papers'])
        })
    
    # Sort by average similarity
    rankings.sort(key=lambda x: x['avg_similarity'], reverse=True)
    
    return rankings[:top_n]

def main(query: str, top_k: int = 10, show_authors: bool = False):
    """
    Main function to perform semantic search.
    """
    print("="*80)
    print("AdvisorMatch: Semantic Search")
    print("="*80)
    
    # Load components
    model = load_model()
    index = load_faiss_index()
    mapping = load_paper_mapping()
    
    # Connect to database
    conn = sqlite3.connect(DB_NAME)
    
    # Perform search
    search(query, model, index, mapping, conn, top_k)
    
    # Show author rankings if requested
    if show_authors:
        print("\n" + "="*80)
        print("Top Authors for this Query:")
        print("="*80)
        
        # Get paper IDs and similarities from search
        query_embedding = model.encode([query], normalize_embeddings=True).astype('float32')
        distances, indices = index.search(query_embedding, top_k)
        paper_ids = [mapping[idx] for idx in indices[0]]
        
        rankings = get_author_rankings(conn, paper_ids, distances[0].tolist())
        
        for i, prof in enumerate(rankings, 1):
            print(f"\n{i}. {prof['name']}")
            print(f"   Average Similarity: {prof['avg_similarity']:.4f}")
            print(f"   Matching Papers: {prof['num_papers']}")
    
    conn.close()
    
    print("\n" + "="*80)
    print("Search complete!")
    print("="*80)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test semantic search")
    parser.add_argument("query", type=str, nargs='?', default="machine learning for healthcare", 
                       help="Research query to search for")
    parser.add_argument("--top-k", type=int, default=10, help="Number of results to return")
    parser.add_argument("--authors", action="store_true", help="Show author rankings")
    
    args = parser.parse_args()
    
    try:
        main(args.query, args.top_k, args.authors)
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        print("\nMake sure you have run the following steps first:", file=sys.stderr)
        print("  1. python3 generate_embeddings.py", file=sys.stderr)
        print("  2. python3 build_faiss_index.py", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
