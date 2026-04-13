#!/bin/bash
set -e

echo "Starting Flask API backend on port 8000..."
python flask_app.py &
FLASK_PID=$!

echo "Waiting for Flask to start..."
sleep 2

echo "Starting Streamlit frontend on port 5000..."
streamlit run streamlit_app.py

wait $FLASK_PID
