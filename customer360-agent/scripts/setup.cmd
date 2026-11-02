@echo off
rem 第一次使用（Windows）：建立 .venv、安裝套件、檢查題庫、產出 context 包、測試 Qwen 連線。
setlocal
chcp 65001 >nul
cd /d "%~dp0.."
set "PYTHONPATH=%CD%\src"
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
  py -3 -m venv .venv 2>nul || python -m venv .venv
)
"%PY%" -c "import rdflib, owlrl, yaml, pyshacl" 2>nul || "%PY%" -m pip install -r requirements.txt
"%PY%" -X utf8 -B -m c360_agent check
"%PY%" -X utf8 -B -m c360_agent pack
"%PY%" -X utf8 -B -m c360_agent ping
pause
