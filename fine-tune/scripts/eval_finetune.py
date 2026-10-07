"""Shipped model vs fine-tune on eval/paper, through the app's own asr.whisper_segments (plan F6).

Run with .venv-app from a folder without backend/.env:

    cd /tmp && WHISPER_CPU_THREADS=8 <repo>/fine-tune/.venv-app/bin/python <repo>/fine-tune/scripts/eval_finetune.py

Configs (all CT2 int8 on CPU, auto-detected language, VAD, as the app runs):
    shipped     out/ct2_base, the app's verbatim prompt   (= today's SpeechMate)
    ft          out/ct2, no prompt                         (as trained)
    ft_prompt   out/ct2, the app's prompt                  (if dropped in without a code change)
Writes eval/paper/finetune_results.csv and prints WER per group.
"""
import csv
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent / "backend"))
from app.config import settings  # noqa: E402
from app.services.live import asr  # noqa: E402

EVAL = ROOT / "eval" / "paper"
CONFIGS = [("shipped", ROOT / "out" / "ct2_base", True), ("ft", ROOT / "out" / "ct2", False),
           ("ft_prompt", ROOT / "out" / "ct2", True)]
APP_PROMPT = asr.VERBATIM_PROMPT
manifest = list(csv.DictReader(open(EVAL / "manifest.csv", encoding="utf-8")))
out = {r["clip_id"]: dict(r) for r in manifest}

for name, model_dir, prompt in CONFIGS:
    settings.whisper_model_size = str(model_dir)
    asr._whisper_model.cache_clear()
    asr.VERBATIM_PROMPT = APP_PROMPT if prompt else None   # whisper_segments reads the module global
    t = time.time()
    for i, r in enumerate(manifest, 1):
        segments, _ = asr.whisper_segments(EVAL / "clips" / f"{r['clip_id']}.wav", None)
        out[r["clip_id"]][name] = " ".join(s.text.strip() for s in segments).strip()
        if i % 100 == 0:
            print(f"{name}: {i} clips, {(time.time() - t) / i:.1f} s/clip", flush=True)

fields = ["clip_id", "corpus", "group", "reference"] + [c[0] for c in CONFIGS]
with open(EVAL / "finetune_results.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    w.writerows(out.values())


def norm(t):
    return re.findall(r"[a-z0-9']+", t.lower().replace("’", "'"))


def edits(r, h):
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1])); prev, d[j] = d[j], cur
    return d[len(h)]


for group in ("english", "mixed"):
    g = [r for r in out.values() if r["group"] == group]
    n = sum(len(norm(r["reference"])) for r in g)
    print(group, " | ".join(f"{c[0]} {sum(edits(norm(r['reference']), norm(r[c[0]])) for r in g) / n:.1%}" for c in CONFIGS))
