"""Benchmark the deployed cloud speech recognition (Groq whisper-large-v3) on the paper's eval set.

Same request as the app (backend/app/services/live/asr.py): verbose_json, word timestamps, the
shared verbatim Manglish prompt, language auto-detected. Per clip it records the transcript, the
wall-clock latency and the billed audio length (Groq bills at least 10 s per request).
Also sends 10 silent / noise-only clips with no VAD in front (worst case).

Resumable: clips already in eval/paper/groq_results.csv are skipped. Reads OPENAI_API_KEY and
OPENAI_BASE_URL from backend/.env (never printed).

    fine-tune/.venv-app/bin/python fine-tune/scripts/eval_groq.py
"""

import csv
import random
import struct
import sys
import time
import wave
from pathlib import Path

from openai import OpenAI, RateLimitError

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "fine-tune" / "eval" / "paper"
OUT = PAPER / "groq_results.csv"
MODEL = "whisper-large-v3"
PROMPT = "Umm, okay lah, so, uh, macam this week saya busy sikit, you know... but boleh la."  # = coach/transcription.py
# Free-tier limits for whisper-large-v3 (console.groq.com/docs/rate-limits, 2026-10-15): 20 RPM, 2,000 RPD,
# 7,200 audio-seconds/hour, 28,800/day. A whole run bills ~5,750 s in 520 requests, so one run fits in an hour;
# these caps stop a run (or a rerun) before it could reach the hourly audio limit or the daily request limit.
MAX_BILLED_SEC_PER_RUN, MAX_REQUESTS_PER_RUN, MIN_SEC_BETWEEN_REQUESTS = 6500, 600, 3.1
FIELDS = ["clip_id", "group", "reference", "hypothesis", "language", "audio_sec", "latency_sec", "words_with_timestamps"]


def env():
    vals = {}
    for line in (ROOT / "backend" / ".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals


def duration(path):
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def make_silence(path, seconds=8, noise=False):
    rng = random.Random(0)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        n = 16000 * seconds
        w.writeframes(b"".join(struct.pack("<h", int(rng.gauss(0, 1500)) if noise else 0) for _ in range(n)))


def clips():
    for r in csv.DictReader(open(PAPER / "manifest.csv", encoding="utf-8")):
        yield r["clip_id"], r["group"], r["reference"], PAPER / "clips" / f"{r['clip_id']}.wav"
    sil = PAPER / "silence"
    sil.mkdir(exist_ok=True)
    for name, noise in (("silence_8s", False), ("noise_8s", True)):
        p = sil / f"{name}.wav"
        if not p.exists():
            make_silence(p, noise=noise)
        yield name, "silence", "", p
    for p in sorted((ROOT / "fine-tune" / "data" / "clips").glob("silent_dev_*.wav")):
        yield p.stem, "silence", "", p


def transcribe(client, path):
    for attempt in range(8):
        try:
            t = time.perf_counter()
            with open(path, "rb") as f:
                r = client.audio.transcriptions.create(
                    model=MODEL, file=f, prompt=PROMPT, response_format="verbose_json",
                    timestamp_granularities=["word"],
                )
            return r, time.perf_counter() - t
        except RateLimitError as e:
            wait = float(e.response.headers.get("retry-after", 2 ** attempt * 5))
            print(f"  rate limited, waiting {wait:.0f}s", flush=True)
            time.sleep(wait + 1)
    raise RuntimeError(f"gave up on {path.name}")


def main():
    cfg = env()
    if not cfg.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY missing in backend/.env")
    client = OpenAI(api_key=cfg["OPENAI_API_KEY"], base_url=cfg.get("OPENAI_BASE_URL"), max_retries=0, timeout=120)
    done = set()
    if OUT.exists():
        done = {r["clip_id"] for r in csv.DictReader(open(OUT, encoding="utf-8"))}
    new = not OUT.exists()
    with open(OUT, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        todo = [c for c in clips() if c[0] not in done]
        billed = 0.0
        for i, (cid, group, ref, path) in enumerate(todo, 1):
            billed += max(10.0, duration(path))
            if billed > MAX_BILLED_SEC_PER_RUN or i > MAX_REQUESTS_PER_RUN:
                print(f"free-tier budget reached ({i - 1} requests, {billed:.0f} s billed): stopping; rerun after an hour to resume")
                break
            started = time.perf_counter()
            r, latency = transcribe(client, path)
            w.writerow({
                "clip_id": cid, "group": group, "reference": ref, "hypothesis": (r.text or "").strip(),
                "language": getattr(r, "language", ""), "audio_sec": round(duration(path), 2),
                "latency_sec": round(latency, 3), "words_with_timestamps": len(getattr(r, "words", None) or []),
            })
            f.flush()
            time.sleep(max(0.0, MIN_SEC_BETWEEN_REQUESTS - (time.perf_counter() - started)))  # stay under 20 RPM
            if i % 25 == 0:
                print(f"{i}/{len(todo)}", flush=True)
    print("GROQ_DONE")


if __name__ == "__main__":
    main()
