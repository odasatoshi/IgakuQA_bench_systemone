#!/usr/bin/env bash
# Run every decision model on all IgakuQA exams, then print the summary.
# Requires: IgakuQA cloned next to this directory, Ollama running with the models pulled.
set -euo pipefail
cd "$(dirname "$0")"
MODELS=${MODELS:-"d3:27b pplx-decider:latest clef:latest clef-flash:latest nimble-v3:latest kev:latest"}
for m in $MODELS; do
  echo "=== $m"
  python3 run_systemone.py --model "$m"
done
python3 summarize.py
