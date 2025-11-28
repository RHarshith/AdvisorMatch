"""
Enhanced ranking algorithm for AdvisorMatch

Combines semantic similarity with recency weighting and activity bonuses
to rank professors based on research relevance.
"""

import sqlite3
import numpy as np
from typing import List, Dict, Tuple
from datetime import datetime
import math

from config import (
    DB_PATH,
    TOP_N_PER_PROFESSOR,
    DECAY_RATE,
    ACTIVITY_THRESHOLD_YEARS,
    ACTIVITY_BONUS_PER_PAPER,
    MAX_ACTIVITY_BONUS
)


def calculate_recency_weight(year: int, current_year: int = None) -> float:
    """
    Calculate recency weight using exponential decay.
    
    Args:
        year: Publication year
        current_year: Current year (defaults to current year)
    
    Returns:
        Recency weight between 0 and 1
    """
    if current_year is None:
        current_year = datetime.now().year
    
    if year is None:
        return 0.5  # Default weight for unknown years
    
    years_ago = current_year - year
    weight = math.exp(-DECAY_RATE * years_ago)
    
    return weight


def calculate_activity_bonus(recent_paper_count: int) -> float:
    """
    Calculate activity bonus based on recent publications.
    
    Args:
        recent_paper_count: Number of papers in last ACTIVITY_THRESHOLD_YEARS
    
    Returns:
        Activity bonus (capped at MAX_ACTIVITY_BONUS)
    """
    bonus = recent_paper_count * ACTIVITY_BONUS_PER_PAPER
    return min(bonus, MAX_ACTIVITY_BONUS)


def aggregate_papers_by_professor(
    paper_ids: List[str],
    similarities: List[float],
    conn: sqlite3.Connection
) -> Dict[int, List[Tuple[str, float, int]]]:
    """
    Aggregate papers by professor.
    
    Args:
        paper_ids: List of paper IDs from FAISS search
        similarities: Corresponding similarity scores
        conn: Database connection
    
    Returns:
        Dict mapping professor_id to list of (paper_id, similarity, year) tuples
    """
    cursor = conn.cursor()
    
    # Get professor-paper mappings
    placeholders = ','.join('?' * len(paper_ids))
    cursor.execute(f"""
        SELECT 
            ab.professor_id,
            pub.paper_id,
            pub.year
        FROM author_bridge ab
        JOIN publications pub ON ab.paper_id = pub.paper_id
        WHERE pub.paper_id IN ({placeholders})
    """, paper_ids)
    
    # Build mapping
    professor_papers = {}
    paper_similarity_map = dict(zip(paper_ids, similarities))
    
    for prof_id, paper_id, year in cursor.fetchall():
        if prof_id not in professor_papers:
            professor_papers[prof_id] = []
        
        similarity = paper_similarity_map.get(paper_id, 0.0)
        professor_papers[prof_id].append((paper_id, similarity, year))
    
    return professor_papers


def rank_professors(
    paper_ids: List[str],
    similarities: List[float],
    conn: sqlite3.Connection,
    top_k: int = 10
) -> List[Dict]:
    """
    Rank professors using enhanced algorithm.
    
    Algorithm:
        1. Aggregate papers by professor
        2. For each professor:
           a. Take top-N most similar papers
           b. Calculate average similarity
           c. Calculate weighted recency score
           d. Calculate activity bonus
           e. Combine into final score
        3. Sort by final score
    
    Args:
        paper_ids: List of paper IDs from FAISS search
        similarities: Corresponding similarity scores
        conn: Database connection
        top_k: Number of top professors to return
    
    Returns:
        List of professor rankings with scores
    """
    current_year = datetime.now().year
    
    # Aggregate papers by professor
    professor_papers = aggregate_papers_by_professor(paper_ids, similarities, conn)
    
    # Calculate scores for each professor
    rankings = []
    
    for prof_id, papers in professor_papers.items():
        # Sort papers by similarity (descending)
        papers_sorted = sorted(papers, key=lambda x: x[1], reverse=True)
        
        # Take top-N papers
        top_papers = papers_sorted[:TOP_N_PER_PROFESSOR]
        
        if not top_papers:
            continue
        
        # Calculate average similarity
        avg_similarity = np.mean([sim for _, sim, _ in top_papers])
        
        # Calculate weighted recency score
        recency_weights = [calculate_recency_weight(year, current_year) 
                          for _, _, year in top_papers]
        avg_recency_weight = np.mean(recency_weights)
        
        # Calculate activity bonus
        recent_papers = [p for p in papers 
                        if p[2] and p[2] >= current_year - ACTIVITY_THRESHOLD_YEARS]
        activity_bonus = calculate_activity_bonus(len(recent_papers))
        
        # Calculate final score
        final_score = (avg_similarity * avg_recency_weight) + activity_bonus
        
        rankings.append({
            'professor_id': prof_id,
            'final_score': final_score,
            'avg_similarity': float(avg_similarity),
            'recency_weight': float(avg_recency_weight),
            'activity_bonus': float(activity_bonus),
            'num_matching_papers': len(papers),
            'top_paper_ids': [pid for pid, _, _ in top_papers]
        })
    
    # Sort by final score (descending)
    rankings.sort(key=lambda x: x['final_score'], reverse=True)
    
    return rankings[:top_k]


def get_professor_details(professor_id: int, conn: sqlite3.Connection) -> Dict:
    """
    Get detailed professor information.
    
    Args:
        professor_id: Professor database ID
        conn: Database connection
    
    Returns:
        Professor details dict
    """
    cursor = conn.cursor()
    
    # Get professor info
    cursor.execute("""
        SELECT id, name, college, dept, interests, openalex_author_id
        FROM professors
        WHERE id = ?
    """, (professor_id,))
    
    row = cursor.fetchone()
    if not row:
        return None
    
    prof_id, name, college, dept, interests, oa_id = row
    
    # Count total publications
    cursor.execute("""
        SELECT COUNT(*)
        FROM author_bridge
        WHERE professor_id = ?
    """, (professor_id,))
    total_pubs = cursor.fetchone()[0]
    
    # Count recent publications
    current_year = datetime.now().year
    cursor.execute("""
        SELECT COUNT(*)
        FROM author_bridge ab
        JOIN publications p ON ab.paper_id = p.paper_id
        WHERE ab.professor_id = ? AND p.year >= ?
    """, (professor_id, current_year - ACTIVITY_THRESHOLD_YEARS))
    recent_pubs = cursor.fetchone()[0]
    
    return {
        'id': prof_id,
        'name': name,
        'college': college,
        'department': dept,
        'interests': interests,
        'url': None,  # URL not in database
        'openalex_author_id': oa_id,
        'total_publications': total_pubs,
        'recent_publications': recent_pubs
    }


def get_publication_details(paper_id: str, conn: sqlite3.Connection) -> Dict:
    """
    Get detailed publication information including authors.
    
    Args:
        paper_id: Paper ID
        conn: Database connection
    
    Returns:
        Publication details dict
    """
    cursor = conn.cursor()
    
    # Get publication info
    cursor.execute("""
        SELECT paper_id, title, abstract, year, citation_count, venue
        FROM publications
        WHERE paper_id = ?
    """, (paper_id,))
    
    row = cursor.fetchone()
    if not row:
        return None
    
    pid, title, abstract, year, citations, venue = row
    
    # Get authors
    cursor.execute("""
        SELECT p.id, p.name, ab.author_position, ab.is_primary_author
        FROM author_bridge ab
        JOIN professors p ON ab.professor_id = p.id
        WHERE ab.paper_id = ?
        ORDER BY ab.author_position
    """, (paper_id,))
    
    authors = []
    for prof_id, prof_name, position, is_primary in cursor.fetchall():
        authors.append({
            'professor_id': prof_id,
            'name': prof_name,
            'position': position,
            'is_primary': bool(is_primary)
        })
    
    return {
        'paper_id': pid,
        'title': title,
        'abstract': abstract,
        'year': year,
        'citation_count': citations,
        'venue': venue,
        'url': pid,  # Use paper_id as URL (OpenAlex ID)
        'authors': authors
    }
