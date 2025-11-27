# Vector Embeddings & Semantic Search

This directory contains scripts for semantic search functionality using Sentence-BERT embeddings and FAISS indexing.

## Quick Start

### 1. Generate Embeddings (if not already done)
```bash
python3 generate_embeddings.py
```

### 2. Build FAISS Index
```bash
python3 build_faiss_index.py --verify
```

### 3. Test Search
```bash
python3 test_search.py "machine learning for robotics" --top-k 5 --authors
```

## Scripts

### `generate_embeddings.py`
Generates semantic embeddings for all publications using Sentence-BERT (all-MiniLM-L6-v2).

**Options:**
- `--batch-size N` - Batch size for embedding generation (default: 32)
- `--test` - Test mode: process only 5 publications

### `build_faiss_index.py`
Builds FAISS index from stored embeddings for efficient similarity search.

**Options:**
- `--verify` - Verify index after building

### `test_search.py`
Test semantic search functionality.

**Usage:**
```bash
python3 test_search.py "query" [--top-k N] [--authors]
```

**Options:**
- `--top-k N` - Number of results to return (default: 10)
- `--authors` - Show author rankings

## Technical Details

- **Model:** all-MiniLM-L6-v2 (384-dimensional embeddings)
- **Index Type:** FAISS IndexFlatIP (cosine similarity)
- **Dataset:** 402 publications from TAMU CSE faculty

## Example Queries

```bash
# Robotics research
python3 test_search.py "machine learning for robotics" --authors

# NLP research
python3 test_search.py "natural language processing" --top-k 5

# Computer vision
python3 test_search.py "computer vision deep learning"
```
