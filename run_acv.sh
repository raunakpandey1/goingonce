#!/usr/bin/env bash
# Start the ACV-style React frontend + agent API on http://localhost:8000
set -e
cd "$(dirname "$0")"
if [ ! -d acv-frontend/node_modules ]; then (cd acv-frontend && npm install); fi
(cd acv-frontend && npx vite build)
exec .venv/bin/uvicorn api:app --port 8000
