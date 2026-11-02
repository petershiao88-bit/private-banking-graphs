#!/bin/bash
# 雙擊執行（macOS）：建立 Semantica 專用環境、跑兩個不接 LLM 的測試，結果寫到 results/。
# 環境建在 customer360-agent/.venv-semantica-<作業系統>（Mac 與 Linux 各一份，互不干擾），第一次需要下載約 150 MB，之後直接重用。
cd "$(dirname "$0")" || exit 1                 # experiments/semantica
AGENT_DIR="$(cd ../.. && pwd)"                  # customer360-agent
VENV="$AGENT_DIR/.venv-semantica-$(uname -s | tr '[:upper:]' '[:lower:]')"
PY="$VENV/bin/python"

pause_exit() { echo; read -r -p "按 Enter 關閉視窗…"; exit "${1:-1}"; }

if [ ! -x "$PY" ]; then
  command -v python3 >/dev/null 2>&1 || { echo "找不到 python3，請先安裝 Python 3.10 以上。"; pause_exit; }
  echo "第一次執行：建立 $VENV …"
  python3 -m venv "$VENV" || pause_exit
fi
if ! "$PY" -c "import semantica" >/dev/null 2>&1; then
  echo "安裝 semantica==0.7.0（第一次約需一兩分鐘）…"
  "$PY" -m pip install -q --upgrade pip >/dev/null 2>&1
  # Linux（aarch64、Python 3.10）可直接用 .wheels/ 裡存好的檔案離線安裝；Mac 走一般下載
  WHEELS=".wheels/linux-aarch64-cp310"
  if [ "$(uname -s)" = "Linux" ] && [ -d "$WHEELS" ]; then
    "$PY" -m pip install -q --no-index --find-links "$WHEELS" semantica==0.7.0 || pause_exit
  else
    "$PY" -m pip install -q semantica==0.7.0 || { echo "安裝失敗，請檢查網路或 pip 的 proxy 設定。"; pause_exit; }
  fi
fi

echo; echo "== 1/2 檢索與推理路徑（probe_paths.py）"
"$PY" probe_paths.py || pause_exit
echo; echo "== 2/2 規則推理與證明（probe_rules.py）"
"$PY" probe_rules.py > /dev/null || pause_exit
echo; echo "完成：結果在 $(pwd)/results/，說明見 README.md"
[ "$(uname -s)" = "Darwin" ] && open README.md
pause_exit 0
