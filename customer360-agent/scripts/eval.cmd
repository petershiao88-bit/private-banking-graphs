@echo off
rem 跑完整評測（Windows），完成後打開報告。
setlocal
chcp 65001 >nul
cd /d "%~dp0.."
set "PYTHONPATH=%CD%\src"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "STAMP=%%i"
".venv\Scripts\python.exe" -X utf8 -B -m c360_agent eval --out "runs\%STAMP%" %*
if exist "runs\%STAMP%\report.html" start "" "runs\%STAMP%\report.html"
pause
