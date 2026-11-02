#!/bin/bash
# 第一次使用：雙擊執行。建立 .venv、安裝套件、檢查題庫、產出 context 包、測試 Qwen 連線。
cd "$(dirname "$0")/.." || exit 1
export PYTHONPATH="$PWD/src"
pause_exit() { echo; read -r -p "按 Enter 關閉視窗…"; exit "${1:-1}"; }

if [ ! -x ".venv/bin/python" ]; then
  command -v python3 >/dev/null 2>&1 || { echo "找不到 python3，請先安裝 Python 3.10 以上。"; pause_exit; }
  echo "建立 .venv…"
  python3 -m venv .venv || pause_exit
fi
if ! .venv/bin/python -c "import rdflib, owlrl, yaml, pyshacl" >/dev/null 2>&1; then
  echo "安裝套件…"
  .venv/bin/python -m pip install -q -r requirements.txt || { echo "套件安裝失敗。"; pause_exit; }
fi

echo; echo "== 1. 檢查題庫與本體 =="
.venv/bin/python -B -m c360_agent check || pause_exit
echo; echo "== 2. 產出角色 context 包 =="
.venv/bin/python -B -m c360_agent pack || pause_exit
echo; echo "== 3. 測試地端 Qwen（端點在 config.yaml 的 llm.base_url）=="
.venv/bin/python -B -m c360_agent ping
echo
echo "完成。接著可以："
echo "  scripts/c360a ask \"基金手收怎麼算？\" --mode plan     # 問一題，看完整過程"
echo "  雙擊 scripts/eval.command                          # 跑完整評測並打開報告"
pause_exit 0
