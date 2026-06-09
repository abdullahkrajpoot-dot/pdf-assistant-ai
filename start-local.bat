@echo off
cd /d "%~dp0"
python -m streamlit run streamlit_app.py --server.address localhost --server.port 5000 --server.headless true
