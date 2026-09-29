"""Benchmark Whisper variants for SpeechMate's live-conversation STT on CPU.

Categories:
  malay_real  – 25 real Malaysian speakers reading Malay (Google FLEURS ms_my test split)
  english     – Malaysian-accented English (local Malaysian TTS voices)
  mixed       – Manglish / code-switched (local Malaysian TTS voices)
Each config is run exactly as the app runs it (faster-whisper, int8, VAD filter,
the app's initial prompt, condition_on_previous_text=False).
"""
import gc, io, json, re, sys, time, wave
from pathlib import Path

import pyarrow.parquet as pq
from faster_whisper import WhisperModel

PROMPT = "Malaysian English conversation. The speaker may use words like lah, kan, tapi, sebenarnya."
EVAL = Path("/tmp/eval"); EVAL.mkdir(exist_ok=True)
TURBO = "/models/ct2/malaysian-whisper-large-v3-turbo-v3"
# (name, model, language, beam size)
CONFIGS = [
    ("whisper-medium (current, lang=en)", "medium", "en", 5),
    ("whisper-medium, lang=ms",           "medium", "ms", 5),
    ("mesolitica small-v3, lang=ms",      "/models/ct2/malaysian-whisper-small-v3", "ms", 5),
    ("mesolitica large-v3-turbo-v3, ms",  TURBO, "ms", 5),
]
if "--beam" in sys.argv:  # beam size 5 (faster-whisper default) vs 1 (greedy) on turbo
    CONFIGS = [("turbo-v3, beam 5", TURBO, "ms", 5), ("turbo-v3, beam 1", TURBO, "ms", 1)]
N_FLEURS = 25


def rss_mb() -> float:
    for line in open("/proc/self/status"):
        if line.startswith("VmRSS"):
            return int(line.split()[1]) / 1024
    return 0.0


def norm(t: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", t.lower().replace("’", "'"))


def edits(r: list[str], h: list[str]) -> int:
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1])); prev, d[j] = d[j], cur
    return d[len(h)]


def duration(path: str) -> float:
    import soundfile
    return soundfile.info(path).duration


# ── Test set ────────────────────────────────────────────────────────────────
items = []
# The FLEURS Parquet file is one ~520 MB row group, so reading any clip decodes ~3 GB.
# Extract the chosen clips once into the model cache; later runs just read those WAVs.
CACHE = Path("/models/eval/fleurs"); MANIFEST = CACHE / "manifest.json"
if not MANIFEST.exists():
    CACHE.mkdir(parents=True, exist_ok=True)
    rows = pq.read_table("/models/eval/fleurs_ms_test.parquet", columns=["id", "audio", "transcription"]).to_pylist()
    seen, picked = set(), []
    step = max(len(rows) // (N_FLEURS * 2), 1)
    for r in rows[::step]:                    # spread across the split; one clip per sentence id
        if r["id"] in seen:
            continue
        seen.add(r["id"]); picked.append(r)
        if len(picked) == N_FLEURS:
            break
    fleurs = []
    for i, r in enumerate(picked):
        p = CACHE / f"fleurs_{i}.wav"
        p.write_bytes(r["audio"]["bytes"])
        fleurs.append({"category": "malay_real", "path": str(p), "text": r["transcription"]})
    MANIFEST.write_text(json.dumps(fleurs, indent=1, ensure_ascii=False))
    del rows, picked
    if "--extract-only" in sys.argv:
        print("EXTRACTED", len(fleurs)); sys.exit()
items += json.loads(MANIFEST.read_text())
items += json.loads(Path("/models/eval/synth/manifest.json").read_text())
cats = ["malay_real", "english", "mixed"]
print("test set:", {c: sum(1 for it in items if it["category"] == c) for c in cats},
      f"| {sum(duration(it['path']) for it in items):.0f}s audio", flush=True)

# ── Run ─────────────────────────────────────────────────────────────────────
results = []
for name, model_id, lang, beam in CONFIGS:
    gc.collect(); base = rss_mb(); t = time.time()
    model = WhisperModel(model_id, device="cpu", compute_type="int8")
    load_s, mem = time.time() - t, rss_mb() - base
    model.transcribe(items[0]["path"], language=lang)          # warm-up, not timed
    per = {c: [0, 0] for c in cats}; audio_s = proc_s = 0.0; samples = []
    for it in items:
        t = time.time()
        segs, _ = model.transcribe(it["path"], language=lang, initial_prompt=PROMPT, vad_filter=True,
                                   condition_on_previous_text=False, beam_size=beam)
        hyp = " ".join(s.text.strip() for s in segs)
        proc_s += time.time() - t; audio_s += duration(it["path"])
        ref = norm(it["text"]); e = edits(ref, norm(hyp))
        per[it["category"]][0] += e; per[it["category"]][1] += len(ref)
        if it["category"] != "malay_real" or len(samples) < 12:
            samples.append({"category": it["category"], "ref": it["text"], "hyp": hyp})
    wer = {c: round(100 * e / n, 1) for c, (e, n) in per.items()}
    total = round(100 * sum(e for e, _ in per.values()) / sum(n for _, n in per.values()), 1)
    res = {"config": name, "wer": wer, "wer_all": total, "rtf": round(proc_s / audio_s, 3),
           "sec_per_5s_turn": round(5 * proc_s / audio_s, 2), "load_s": round(load_s, 1),
           "ram_mb": round(mem), "samples": samples}
    results.append(res)
    print(f"{name:38s} WER malay {wer['malay_real']:5.1f}% | english {wer['english']:5.1f}% | mixed {wer['mixed']:5.1f}% "
          f"| all {total:5.1f}% | {res['sec_per_5s_turn']:.2f}s per 5s turn | load {res['load_s']}s | +{res['ram_mb']} MB",
          flush=True)
    del model; gc.collect()

Path("/models/eval/results_beam.json" if "--beam" in sys.argv else "/models/eval/results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False))
print("BENCH_DONE")
