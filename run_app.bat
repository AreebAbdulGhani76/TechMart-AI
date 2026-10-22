@echo off
title TechMart AI Assistant - Streamlit Edition
cd /d "%~dp0"

echo ===================================================
echo   🛍️ TechMart AI Sales & Policy RAG Assistant
echo   Streamlit Professional Edition
echo ===================================================
echo.
echo Launching Streamlit web application on http://localhost:8501 ...
echo.

.\.venv\Scripts\streamlit.exe run app.py
