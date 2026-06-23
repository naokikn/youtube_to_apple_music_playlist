#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INPUT_FILE="${PROJECT_ROOT}/input/playlist_url.txt"
OUTPUT_DIR="${PROJECT_ROOT}/output"
OUTPUT_FILE="${OUTPUT_DIR}/playlist_items.jsonl"

if [[ ! -f "${INPUT_FILE}" ]]; then
  echo "エラー: playlist URLファイルが見つかりません: ${INPUT_FILE}" >&2
  exit 1
fi

PLAYLIST_URL="$(awk 'NF { print; exit }' "${INPUT_FILE}")"
if [[ -z "${PLAYLIST_URL}" ]]; then
  echo "エラー: ${INPUT_FILE} にYouTubeプレイリストURLを1行で入力してください。" >&2
  exit 1
fi

if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "エラー: yt-dlp コマンドが見つかりません。macOSでは 'brew install yt-dlp' でインストールできます。" >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"

yt-dlp \
  --skip-download \
  --dump-json \
  --no-flat-playlist \
  --ignore-errors \
  --no-warnings \
  --output-na-placeholder "" \
  "${PLAYLIST_URL}" \
  > "${OUTPUT_FILE}"

LINE_COUNT="$(wc -l < "${OUTPUT_FILE}" | tr -d ' ')"
echo "出力: ${OUTPUT_FILE}"
echo "行数: ${LINE_COUNT}"
