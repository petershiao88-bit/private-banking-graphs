#!/bin/bash
# 雙擊啟動 Semantic Studio（macOS）。關掉這個終端機視窗就會停止服務。
cd "$(dirname "$0")/.." || exit 1          # 專案根目錄（config.yaml 所在）
export PYTHONPATH="$PWD/src"

pause_exit() { echo; read -r -p "按 Enter 關閉視窗…"; exit 1; }

# 第一次執行時建立 .venv；之後若缺套件（例如 requirements 有更新）就補裝
if [ ! -x ".venv/bin/python" ]; then
  command -v python3 >/dev/null 2>&1 || { echo "找不到 python3，請先安裝 Python 3.10 以上。"; pause_exit; }
  echo "第一次啟動：建立 .venv 並安裝套件，需要一點時間…"
  python3 -m venv .venv || pause_exit
fi
if ! .venv/bin/python -c "import rdflib, owlrl, yaml, pyshacl" >/dev/null 2>&1; then
  echo "安裝／更新套件…"
  .venv/bin/python -m pip install -q -r requirements.txt || { echo "套件安裝失敗。"; pause_exit; }
fi

# 連接埠以 config.yaml 的 studio.port 為準
PORT=$(.venv/bin/python -B -c "from ontology_kit.config import Config; print(Config().data['studio'].get('port', 8870))") || pause_exit
URL="http://127.0.0.1:${PORT}/"

# 連接埠已被佔用：確認是不是「正常回應的 Studio」，不是的話（例如舊版殘留、其他程式）詢問是否結束它
if lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  if curl -sf -m 5 -o /dev/null "${URL}" && curl -sf -m 10 -o /dev/null "${URL}api/state"; then
    echo "Semantic Studio 已在執行：${URL}"
    open "${URL}"
    exit 0
  fi
  echo "連接埠 ${PORT} 被下面的程式佔用，但它沒有正常回應（可能是之前開的舊版 Studio 沒關）："
  lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN
  PIDS=$(lsof -t -nP -iTCP:"${PORT}" -sTCP:LISTEN | sort -u | tr '\n' ' ')
  read -r -p "要結束這個程式（PID ${PIDS}）並重新啟動 Studio 嗎？[y/N] " ANSWER
  case "$ANSWER" in
    [yY]*) kill ${PIDS} 2>/dev/null; sleep 1
           lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1 && { kill -9 ${PIDS} 2>/dev/null; sleep 1; } ;;
    *) echo "沒有變更。也可以改 config.yaml 的 studio.port 換一個連接埠。"; pause_exit ;;
  esac
  if lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "無法釋放連接埠 ${PORT}。請改 config.yaml 的 studio.port 後再試。"; pause_exit
  fi
fi

(sleep 2; open "${URL}") &
.venv/bin/python -B -m semantic_studio --port "${PORT}" || pause_exit
