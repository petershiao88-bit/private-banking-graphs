@echo off
rem 終端機捷徑（Windows）：scripts\c360a.cmd ask "基金手收怎麼算？" --mode plan
setlocal
chcp 65001 >nul
set "ROOT=%~dp0.."
set "PYTHONPATH=%ROOT%\src"
"%ROOT%\.venv\Scripts\python.exe" -X utf8 -B -m c360_agent %*
