#!/bin/bash
set -ex

PYTHON_FILE="app.py"
LOG_FILE="reranker_service.log"

pip install loguru

if [ ! -f "$PYTHON_FILE" ]; then
    echo "Error: $PYTHON_FILE not found!"
    exit 1
fi

echo "Starting reranker service..."
nohup python3 "$PYTHON_FILE" > "$LOG_FILE" 2>&1 &

PID=$!
echo "Service started with PID: $PID"