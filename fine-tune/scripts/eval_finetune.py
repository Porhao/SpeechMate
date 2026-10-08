"""Shipped model vs fine-tune on eval/paper, through the app's own asr.whisper_segments (plan F6).

Run with .venv-app from a folder without backend/.env:

    cd /tmp && WHISPER_CPU_THREADS=8 <repo>/fine-tune/.venv-app/bin/python <repo>/fine-tune/scripts/eval_finetune.py

Configs (auto-detected language, VAD, the app's decoding settings):
    shipped      out/ct2_base, CPU int8, the app's verbatim prompt   (= today's SpeechMate)
    ft           out/ct2, CPU int8, no prompt                         (as trained)
    ft_prompt    out/ct2, CPU int8, the app's prompt                  (if dropped in unchanged)
    voicestudio  Whisper large-v3 (Systran/faster-whisper-large-v3), GPU float16, no prompt:
                 VoiceStudio's Faster-Whisper engine; its WhisperX default uses the same weights.
                 Needs the CUDA libs on LD_LIBRARY_PATH (e.g. from .venv's nvidia/*/lib).
Writes eval/paper/finetune_results.csv (resumes: only missing clip/config cells are run)
and prints WER per group.
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
CONFIGS = [("shipped", ROOT / "out" / "ct2_base", True, "cpu"), ("ft", ROOT / "out" / "ct2", False, "cpu"),
           ("ft_prompt", ROOT / "out" / "ct2", True, "cpu"), ("voicestudio", "large-v3", False, "cuda")]
APP_PROMPT = asr.VERBATIM_PROMPT
RESULTS = EVAL / "finetune_results.csv"
manifest = list(csv.DictReader(open(EVAL / "manifest.csv", encoding="utf-8")))
out = {r["clip_id"]: dict(r) for r in manifest}
if RESULTS.exists():   # resume: keep cells already transcribed
    for r in csv.DictReader(open(RESULTS, encoding="utf-8")):
        if r["clip_id"] in out:
            out[r["clip_id"]].update({c[0]: r[c[0]] for c in CONFIGS if r.get(c[0])})
app_loader = asr._whisper_model

for name, model, prompt, device in CONFIGS:
    todo = [r for r in manifest if name not in out[r["clip_id"]]]
    if not todo:
        continue
    app_loader.cache_clear()
    if device == "cpu":
        settings.whisper_model_size = str(model)
        asr._whisper_model = app_loader
    else:
        from faster_whisper import WhisperModel
        gpu_model = WhisperModel(model, device="cuda", compute_type="float16")
        asr._whisper_model = lambda: gpu_model
    asr.VERBATIM_PROMPT = APP_PROMPT if prompt else None   # whisper_segments reads the module global
    t = time.time()
    for i, r in enumerate(todo, 1):
        segments, _ = asr.whisper_segments(EVAL / "clips" / f"{r['clip_id']}.wav", None)
        out[r["clip_id"]][name] = " ".join(s.text.strip() for s in segments).strip()
        if i % 100 == 0:
            print(f"{name}: {i}/{len(todo)} clips, {(time.time() - t) / i:.1f} s/clip", flush=True)
    asr._whisper_model = app_loader

fields = ["clip_id", "corpus", "group", "reference"] + [c[0] for c in CONFIGS]
with open(RESULTS, "w", newline="", encoding="utf-8") as fh:
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


for group in ("english", "malay", "mixed"):
    g = [r for r in out.values() if r["group"] == group]
    n = sum(len(norm(r["reference"])) for r in g)
    print(group, " | ".join(f"{c[0]} {sum(edits(norm(r['reference']), norm(r[c[0]])) for r in g) / n:.1%}" for c in CONFIGS))
