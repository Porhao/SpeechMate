"""Routing WER comparison for the paper: SpeechMate's own asr._transcribe_local on eval/paper.

Run with .venv-app (the app's pinned faster-whisper/transformers), from a folder without
backend/.env, with a standard Whisper model (routing is bypassed for Malaysian Whisper):

    cd /tmp && WHISPER_MODEL_SIZE=large-v3 WHISPER_CPU_THREADS=8 \
        <repo>/fine-tune/.venv-app/bin/python <repo>/fine-tune/scripts/eval_routing.py

One pass gives both columns: routing off = Whisper's own transcript; routing on = the app's
final transcript (Whisper, or the code-switch wav2vec2 when Whisper isn't confidently English).
Appends to eval/paper/results.csv, so an interrupted run resumes.
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

assert not asr.is_malaysian_model(), "routing is bypassed for Malaysian Whisper: set WHISPER_MODEL_SIZE"
EVAL = ROOT / "eval" / "paper"
OUT = EVAL / "results.csv"
FIELDS = ["clip_id", "corpus", "group", "reference", "routing_off", "routing_on", "detected_language",
          "language_confidence", "routing_triggered", "engine_used", "seconds"]

# Capture Whisper's transcript inside the app's own routing function
whisper_text = {}
_whisper_segments = asr.whisper_segments


def whisper_segments(*args, **kwargs):
    segments, info = _whisper_segments(*args, **kwargs)
    whisper_text["last"] = " ".join(s.text.strip() for s in segments).strip()
    return segments, info


asr.whisper_segments = whisper_segments

done = {r["clip_id"] for r in csv.DictReader(open(OUT, encoding="utf-8"))} if OUT.exists() else set()
manifest = [r for r in csv.DictReader(open(EVAL / "manifest.csv", encoding="utf-8")) if r["clip_id"] not in done]
print(f"model {settings.whisper_model_size} | {len(done)} done, {len(manifest)} to go", flush=True)

with open(OUT, "a", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    if not done:
        w.writeheader()
    for i, r in enumerate(manifest, 1):
        whisper_text["last"] = ""
        warnings: list[str] = []
        t = time.time()
        res = asr._transcribe_local(EVAL / "clips" / f"{r['clip_id']}.wav", warnings)
        triggered = not (res.language == "en" and res.confidence >= asr.ENGLISH_CONFIDENCE_THRESHOLD)
        w.writerow({**r, "routing_off": whisper_text["last"], "routing_on": res.transcript,
                    "detected_language": res.language, "language_confidence": res.confidence,
                    "routing_triggered": triggered, "engine_used": res.engine, "seconds": round(time.time() - t, 2)})
        fh.flush()
        if warnings:
            print(r["clip_id"], warnings, flush=True)
        if i % 25 == 0:
            print(f"{len(done) + i} clips", flush=True)


# --- Sanity summary (same normalisation as bench_stt.py; the paper computes its own) --
def norm(t):
    return re.findall(r"[a-z0-9']+", t.lower().replace("’", "'"))


def edits(r, h):
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1])); prev, d[j] = d[j], cur
    return d[len(h)]


rows = list(csv.DictReader(open(OUT, encoding="utf-8")))
for group in ("english", "mixed"):
    g = [r for r in rows if r["group"] == group]
    n_words = sum(len(norm(r["reference"])) for r in g)
    off = sum(edits(norm(r["reference"]), norm(r["routing_off"])) for r in g) / n_words
    on = sum(edits(norm(r["reference"]), norm(r["routing_on"])) for r in g) / n_words
    trig = sum(r["routing_triggered"] == "True" for r in g)
    used = sum(r["engine_used"] == asr.CODESWITCH_MODEL_ID for r in g)
    print(f"{group}: {len(g)} clips | WER routing off {off:.1%} | on {on:.1%} | routing triggered {trig} | code-switch transcript used {used}")
