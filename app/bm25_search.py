import sqlite3
import re
from pathlib import Path
from typing import List, Dict, Tuple
from rank_bm25 import BM25Okapi

class BM25Searcher:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.bm25 = None
        self.documents = []
        self.metadata = []
        self.load_corpus()

    def simple_tokenize(self, text: str) -> List[str]:
        """Simple tokenizer: lowercase and split by non-alphanumeric"""
        if not text:
            return []
        return re.findall(r'\w+', text.lower())

    def load_corpus(self):
        """Load publications from database and prepare corpus"""
        print("Loading BM25 corpus from database...")
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT paper_id, title, abstract, year, citation_count, venue, url
                FROM publications
            """)
            
            self.documents = []
            self.metadata = []
            
            for row in cursor.fetchall():
                paper_id, title, abstract, year, citations, venue, url = row
                
                # Combine title and abstract for indexing
                text = f"{title} {abstract if abstract else ''}"
                self.documents.append(self.simple_tokenize(text))
                
                self.metadata.append({
                    'paper_id': paper_id,
                    'title': title,
                    'abstract': abstract,
                    'year': year,
                    'citations': citations,
                    'venue': venue,
                    'url': url
                })
            
            conn.close()
            
            print(f"Initializing BM25 with {len(self.documents)} documents...")
            self.bm25 = BM25Okapi(self.documents)
            print("✓ BM25 initialized")
            
        except Exception as e:
            print(f"⚠ Failed to initialize BM25: {e}")

    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """Search the corpus using BM25"""
        if not self.bm25:
            return []
            
        tokenized_query = self.simple_tokenize(query)
        doc_scores = self.bm25.get_scores(tokenized_query)
        
        # Create list of (index, score) tuples and sort
        ranked_results = sorted(enumerate(doc_scores), key=lambda x: x[1], reverse=True)
        
        results = []
        conn = sqlite3.connect(self.db_path)
        
        for i in range(min(top_k, len(ranked_results))):
            idx, score = ranked_results[i]
            if score <= 0: break
            
            meta = self.metadata[idx].copy()
            meta['score'] = score
            
            # Get professor info
            prof_name = self.get_professor_for_paper(meta['paper_id'], conn)
            meta['professor_name'] = prof_name
            
            results.append(meta)
            
        conn.close()
        return results

    def get_professor_for_paper(self, paper_id: str, conn: sqlite3.Connection) -> str:
        """Get professor name for a paper"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.name 
            FROM professors p
            JOIN author_bridge ab ON p.id = ab.professor_id
            WHERE ab.paper_id = ?
            LIMIT 1
        """, (paper_id,))
        row = cursor.fetchone()
        return row[0] if row else "Unknown"
