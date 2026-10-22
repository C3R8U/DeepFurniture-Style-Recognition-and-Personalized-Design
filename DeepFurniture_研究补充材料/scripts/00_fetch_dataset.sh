#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-./DeepFurniture}"
printf 'Downloading published dataset (~43.5 GB) into %s\n' "$ROOT"
if ! command -v hf >/dev/null 2>&1; then
  echo 'Install first: python -m pip install huggingface_hub[cli]' >&2
  exit 1
fi
hf download byliu/DeepFurniture --repo-type dataset --local-dir "$ROOT"
if [ ! -f "$ROOT/uncompress_dataset.sh" ]; then
  echo 'Official uncompress_dataset.sh was not downloaded' >&2
  exit 2
fi
(
  cd "$ROOT"
  bash uncompress_dataset.sh -s data -t uncompressed_data
)
printf 'Dataset extracted: %s/uncompressed_data\n' "$ROOT"
