@echo off
REM Bitcoin Trading System - Optional Dependencies Installer
REM This script installs optional dependencies for better performance

echo ========================================
echo Bitcoin Trading System
echo Optional Dependencies Installer
echo ========================================
echo.

echo Installing FAISS (for better RAG performance)...
pip install faiss-cpu
echo.

echo Installing Google Sheets support (optional)...
pip install gspread google-auth
echo.

echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo TA-Lib was skipped (not needed - fallback works great)
echo.
echo Run: python test_api_clients.py
echo.
pause
