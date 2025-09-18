#!/usr/bin/env bash
set -euo pipefail

# 開発用起動スクリプト
# 使用例:
#   ./scripts/run_dev.sh                 # 既定値で起動
#   FFMPEG_CRF=18 FFMPEG_PRESET=slow ./scripts/run_dev.sh
#   HOST=127.0.0.1 PORT=8080 ./scripts/run_dev.sh

# 既定値（環境変数で上書き可）
export FFMPEG_CRF="${FFMPEG_CRF:-23}"
export FFMPEG_PRESET="${FFMPEG_PRESET:-medium}"
export MAX_CONCURRENCY="${MAX_CONCURRENCY:-1}"
export MAX_UPLOAD_MB="${MAX_UPLOAD_MB:-200}"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

echo "[run_dev] FFMPEG_CRF=${FFMPEG_CRF} FFMPEG_PRESET=${FFMPEG_PRESET} MAX_CONCURRENCY=${MAX_CONCURRENCY} MAX_UPLOAD_MB=${MAX_UPLOAD_MB} HOST=${HOST} PORT=${PORT}"

exec uvicorn api.app.main:app \
  --host "${HOST}" \
  --port "${PORT}" \
  --log-level info


