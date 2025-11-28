#!/bin/bash
# Quick start script for AdvisorMatch API

echo "🚀 Starting AdvisorMatch API..."
echo ""

# Kill any existing processes on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null

# Start the API
cd "$(dirname "$0")"
python3 api.py
