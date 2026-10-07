"""Merge the LoRA adapter into its base model and convert it for faster-whisper (plan F7).

    .venv/bin/python scripts/export.py [base model] [converter venv]

Base defaults to the Mesolitica model trained on. The converter venv needs ctranslate2 +
transformers==4.56.2 + torch (default .venv-convert/).

Writes out/merged/ (Hugging Face, fp16) and out/ct2/ (CTranslate2 int8, what the app loads).
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from peft import PeftModel
from transformers import WhisperForConditionalGeneration

ROOT = Path(__file__).resolve().parent.parent
BASE = sys.argv[1] if len(sys.argv) > 1 else "mesolitica/Malaysian-whisper-large-v3-turbo-v3"
MERGED, CT2 = ROOT / "out" / "merged", ROOT / "out" / "ct2"

base = WhisperForConditionalGeneration.from_pretrained(BASE, torch_dtype=torch.float16)
merged = PeftModel.from_pretrained(base, ROOT / "out" / "adapter").merge_and_unload()
merged.save_pretrained(MERGED)
# Tokenizer/preprocessor/generation files: the base repo's originals, untouched by training.
# (transformers 5 re-saves them in a format the converter's transformers 4.x can't read.)
snapshot_download(BASE, local_dir=MERGED, allow_patterns=[
    "tokenizer*", "vocab.json", "merges.txt", "*special_tokens*", "added_tokens.json",
    "normalizer.json", "preprocessor_config.json", "generation_config.json"])
# transformers 5 writes "dtype"; the converter's transformers 4.x only knows "torch_dtype"
cfg = json.loads((MERGED / "config.json").read_text())
cfg["torch_dtype"] = cfg.pop("dtype", cfg.get("torch_dtype", "float16"))
(MERGED / "config.json").write_text(json.dumps(cfg, indent=2))
print("merged ->", MERGED, flush=True)

# The converter needs transformers >= 4.56 (like backend/scripts/convert_whisper.sh); pass its venv
converter = Path(sys.argv[2] if len(sys.argv) > 2 else ROOT / ".venv-convert") / "bin" / "ct2-transformers-converter"
shutil.rmtree(CT2, ignore_errors=True)
subprocess.run([str(converter), "--model", str(MERGED), "--output_dir", str(CT2), "--quantization", "int8",
                "--copy_files", "tokenizer.json", "preprocessor_config.json", "--low_cpu_mem_usage", "--force"], check=True)
print("converted ->", CT2)
