#!/bin/bash
# 跑完整評測（四種模式 × 全部題目），完成後用瀏覽器打開報告。
cd "$(dirname "$0")/.." || exit 1
export PYTHONPATH="$PWD/src"
PY=".venv/bin/python"; [ -x "$PY" ] || { echo "請先雙擊 scripts/setup.command"; read -r -p "按 Enter 關閉…"; exit 1; }
OUT="runs/$(date +%Y%m%d-%H%M%S)"
"$PY" -B -m c360_agent eval --out "$OUT" "$@"
[ -f "$OUT/report.html" ] && open "$OUT/report.html"
read -r -p "按 Enter 關閉視窗…"
