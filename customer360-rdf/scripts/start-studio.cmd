@echo off
rem Semantic Studio launcher (Windows cmd). Double-click, or run: scripts\start-studio.cmd [--port 8871]
setlocal
chcp 65001 >nul
cd /d "%~dp0.."
set "PYTHONPATH=%CD%\src"

set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [1/3] Creating virtual environment .venv ...
  py -3 -m venv .venv 2>nul || python -m venv .venv
  if not exist "%PY%" (
    echo Python 3.10+ not found. Install it from https://www.python.org/ and tick "Add python.exe to PATH".
    pause
    exit /b 1
  )
)

"%PY%" -c "import sys, rdflib, owlrl, yaml, pyshacl; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>nul
if errorlevel 1 (
  echo [2/3] Installing packages from requirements.txt ...
  "%PY%" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Package install failed. Check the network or pip proxy settings, then run this file again.
    pause
    exit /b 1
  )
)

echo [3/3] Starting Semantic Studio. Close this window or press Ctrl+C to stop.
"%PY%" -X utf8 -B -m semantic_studio --open %*
pause
