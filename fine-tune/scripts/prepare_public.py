"""Training data from public CC BY 4.0 sources -> data/ in the plan's layout (§4, §5).

    Manglish  emhaihsan/Synth-Manglish  2,457 synthetic clips, 21 TTS voices (~7 h)
    Malay     google/fleurs ms_my       real speakers   } guard data, ~30% of the
    English   google/fleurs en_us       real speakers   } speech (plan §4.4)
    Silence   generated room tone, empty transcript (~4%)
    Noise     noisy copies of ~10% of the speech clips

Dev = held-out Synth-Manglish voices + FLEURS validation: split by speaker, never the
real-recording test set. Transcripts follow STYLE_GUIDE.md particle spellings.
Replaces the smoke-test data (prepare_smoke.py rebuilds that). Attribution: RESULTS.md.
"""
import csv
import io
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import soundfile as sf
from huggingface_hub import HfFileSystem, hf_hub_download

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent / "backend"))
from app.services.live.language import estimate_language_ratio  # noqa: E402  same lexicon as the app

DATA, SR = ROOT / "data", 16000
CLIPS = DATA / "clips"
DEV_VOICES = {"nurin", "rizal", "johari"}   # 1 female + 2 male voices held out for dev
N_GUARD = 450                               # FLEURS clips per language for train
N_DEV_SYNTH, N_DEV_FLEURS = 120, 40
SILENT_SHARE, NOISY_SHARE = 0.04, 0.10
# ponytail: the app's lexicon misses many Malay words ("cari", "baju", "semua"), so a
# Malay-framed sentence scores ~0.45. 0.35 tags those "ms"; a language-ID model would be exact.
MALAY_CUTOFF = 0.35
rng = np.random.default_rng(0)

# STYLE_GUIDE.md §3-4: one spelling per particle
STYLE = {"la": "lah", "wei": "weh", "aiyoh": "aiyo", "ok": "okay", "okey": "okay", "loh": "lor"}
STYLE_RE = re.compile(r"\b(" + "|".join(STYLE) + r")\b", re.IGNORECASE)


def styled(text: str) -> str:
    def fix(m):
        new = STYLE[m.group(1).lower()]
        return new.capitalize() if m.group(1)[0].isupper() else new
    return STYLE_RE.sub(fix, text.strip())


def decode(audio_bytes: bytes) -> np.ndarray:
    """Any format (MP3 24 kHz, WAV 16 kHz) -> 16 kHz mono float32."""
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", "pipe:0", "-f", "f32le", "-ac", "1", "-ar", str(SR), "pipe:1"],
                         input=audio_bytes, capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32)


rows = {"train": [], "dev": []}


def add(split, name, audio, transcript, language, speaker, source):
    if len(audio) > 30 * SR or (transcript and len(audio) < SR):   # Whisper cuts at 30 s; <1 s is a bad clip
        return False
    sf.write(CLIPS / name, audio, SR)
    rows[split].append({"file_name": name, "transcript": transcript, "language": language,
                        "speaker": speaker, "source": source})
    return True


if CLIPS.exists():
    shutil.rmtree(CLIPS)
CLIPS.mkdir(parents=True)

# --- Manglish: Synth-Manglish, split by voice ----------------------------
n_dev = 0
for shard in ("00000", "00001"):
    path = hf_hub_download("emhaihsan/Synth-Manglish", f"parquet/train-{shard}-of-00002.parquet", repo_type="dataset")
    for batch in pq.ParquetFile(path).iter_batches(batch_size=64, columns=["file_name", "text", "audio"]):
        for r in batch.to_pylist():
            voice = r["file_name"].split("__")[1]          # 000001__ahmad_yusuf__voice.mp3
            split = "dev" if voice in DEV_VOICES else "train"
            if split == "dev" and n_dev >= N_DEV_SYNTH:
                continue
            text = styled(r["text"])
            _, malay = estimate_language_ratio(text)
            stem = r["file_name"].split("__")[0]
            if add(split, f"synth_{stem}.wav", decode(r["audio"]["bytes"]), text,
                   "ms" if malay > MALAY_CUTOFF else "en", voice, "synth-manglish"):
                n_dev += split == "dev"
    print("synth-manglish:", {s: len(v) for s, v in rows.items()}, flush=True)

# --- Guard data: FLEURS Malay and English (streamed, only the row groups needed) --
fs = HfFileSystem()
for lang, code in (("ms", "ms_my"), ("en", "en_us")):
    for split, fleurs_split, limit in (("train", "train", N_GUARD), ("dev", "validation", N_DEV_FLEURS)):
        f = pq.ParquetFile(fs.open(f"datasets/google/fleurs@refs%2Fconvert%2Fparquet/{code}/{fleurs_split}/0000.parquet"))
        n, seen = 0, set()
        for batch in f.iter_batches(batch_size=32, columns=["id", "audio", "raw_transcription"]):
            for r in batch.to_pylist():
                if n >= limit:
                    break
                if r["id"] in seen:   # FLEURS repeats each sentence across speakers: one of each
                    continue
                seen.add(r["id"])
                n += add(split, f"fleurs_{lang}_{split}_{n:04d}.wav", decode(r["audio"]["bytes"]),
                         r["raw_transcription"], lang, f"fleurs-{lang}", f"fleurs-{fleurs_split}")
            if n >= limit:
                break
        print(f"fleurs {code} {fleurs_split}: {n}", flush=True)

# --- Noisy copies of some training speech (plan §4.4) ---------------------
# ponytail: synthetic white/brown noise at 5-20 dB SNR; real café/traffic noise would be better
speech = [r for r in rows["train"]]
for i, r in enumerate(rng.choice(len(speech), int(len(speech) * NOISY_SHARE), replace=False)):
    src = speech[r]
    audio, _ = sf.read(CLIPS / src["file_name"], dtype="float32")
    noise = rng.normal(0, 1, len(audio)).astype(np.float32)
    if i % 2:
        noise = np.cumsum(noise)
        noise -= np.convolve(noise, np.ones(400) / 400, mode="same")   # brown-ish: rumbly, minus drift
    snr_db = rng.uniform(5, 20)
    noise *= np.sqrt(np.mean(audio ** 2) / (np.mean(noise ** 2) + 1e-12) / 10 ** (snr_db / 10))
    add("train", f"noisy_{i:04d}.wav", np.clip(audio + noise, -1, 1), src["transcript"],
        src["language"], src["speaker"], src["source"] + "+noise")

# --- Silence: empty transcripts (plan §4.4) -------------------------------
for split in ("train", "dev"):
    for i in range(max(6, int(len(rows[split]) * SILENT_SHARE))):
        audio = rng.normal(0, 10 ** rng.uniform(-3.5, -2.5), SR * int(rng.integers(3, 9))).astype(np.float32)
        add(split, f"silent_{split}_{i:03d}.wav", audio, "", "en" if i % 2 else "ms", "silence", "generated")

for split, rs in rows.items():
    with open(DATA / f"{split}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file_name", "transcript", "language", "speaker", "source"])
        w.writeheader()
        w.writerows(rs)
    secs = sum(sf.info(CLIPS / r["file_name"]).duration for r in rs)
    by_source = {}
    for r in rs:
        by_source[r["source"]] = by_source.get(r["source"], 0) + 1
    print(f"{split}: {len(rs)} clips, {secs / 3600:.1f} h", by_source)
