#!/bin/bash
# Re-ingest publications with increased paper limit (20 per professor)

echo "🔄 Re-ingesting publications with 20 papers per professor..."
echo ""
echo "This will:"
echo "  - Fetch up to 20 papers per professor (was 5)"
echo "  - Update advisormatch_openalex.db"
echo "  - Regenerate embeddings for new papers"
echo "  - Rebuild FAISS index"
echo ""
echo "Estimated time: 10-15 minutes"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Cancelled."
    exit 1
fi

cd "$(dirname "$0")"

echo ""
echo "Step 1/4: Re-ingesting publications..."
python3 ingest.py

echo ""
echo "Step 2/4: Generating embeddings for new papers..."
python3 generate_embeddings.py

echo ""
echo "Step 3/4: Rebuilding FAISS index..."
python3 build_faiss_index.py

echo ""
echo "Step 4/4: Verifying data..."
python3 -c "
import sqlite3
conn = sqlite3.connect('advisormatch_openalex.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM professors')
profs = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM publications')
pubs = cursor.fetchone()[0]

cursor.execute('SELECT AVG(cnt) FROM (SELECT COUNT(*) as cnt FROM author_bridge GROUP BY professor_id)')
avg_papers = cursor.fetchone()[0]

print(f'✓ Professors: {profs}')
print(f'✓ Publications: {pubs}')
print(f'✓ Avg papers per professor: {avg_papers:.1f}')

conn.close()
"

echo ""
echo "✅ Re-ingestion complete!"
echo ""
echo "Next steps:"
echo "  1. Restart the API server: cd app && python3 api.py"
echo "  2. Test the search with more comprehensive data"
