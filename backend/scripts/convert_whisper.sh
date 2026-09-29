#!/bin/sh
# Convert a Hugging Face (transformers) Whisper model to faster-whisper's CTranslate2
# format, into the shared model cache volume, then point WHISPER_MODEL_SIZE at it.
#
#   ./backend/scripts/convert_whisper.sh mesolitica/malaysian-whisper-small-v3
#   # backend/.env:  WHISPER_MODEL_SIZE=/models/ct2/malaysian-whisper-small-v3
#
# Runs in a throwaway container: the converter needs transformers 4.56 (newer than the
# app's pinned version), so it's installed only there.
set -e
REPO="${1:?usage: convert_whisper.sh <huggingface-repo-id>}"
NAME="$(basename "$REPO" | tr 'A-Z' 'a-z')"
docker run --rm -v speechmate_model_cache:/models -e HF_HOME=/models/huggingface speechmate-backend sh -c "
  pip install -q 'transformers==4.56.2' >/dev/null 2>&1 &&
  ct2-transformers-converter --model '$REPO' --output_dir '/models/ct2/$NAME' --quantization int8 \
    --copy_files tokenizer.json preprocessor_config.json --low_cpu_mem_usage --force"
echo "Converted. Set WHISPER_MODEL_SIZE=/models/ct2/$NAME in backend/.env and run ./start.sh"
