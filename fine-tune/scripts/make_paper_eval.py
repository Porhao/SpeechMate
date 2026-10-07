"""Evaluation set for the paper's routing WER comparison -> eval/paper/.

    english  200 FLEURS en_us *test* clips: real speakers, human transcripts (CC BY 4.0)
    mixed    200 Synth-Manglish clips from the 3 voices held out of training, minus the
             dev clips (synthetic TTS voices; CC BY 4.0). Only clips with both English and
             Malay words (by the app's lexicon).

No clip here is ever in data/train.csv. Writes eval/paper/clips/*.wav (16 kHz mono) and
eval/paper/manifest.csv: clip_id,corpus,group,reference.
"""
import csv
import subprocess
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import soundfile as sf
from huggingface_hub import HfFileSystem, hf_hub_download

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent / "backend"))
from app.services.live.language import estimate_language_ratio  # noqa: E402

OUT = ROOT / "eval" / "paper"
CLIPS = OUT / "clips"
CLIPS.mkdir(parents=True, exist_ok=True)
N = 200
HELD_OUT = {"nurin", "rizal", "johari"}   # = prepare_public.DEV_VOICES
dev_files = {r["file_name"] for r in csv.DictReader(open(ROOT / "data" / "dev.csv", encoding="utf-8"))}


def decode(audio_bytes: bytes) -> np.ndarray:
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", "pipe:0", "-f", "f32le", "-ac", "1", "-ar", "16000", "pipe:1"],
                         input=audio_bytes, capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32)


rows = []
# English-only: FLEURS en_us test, one clip per sentence
f = pq.ParquetFile(HfFileSystem().open("datasets/google/fleurs@refs%2Fconvert%2Fparquet/en_us/test/0000.parquet"))
seen = set()
for batch in f.iter_batches(batch_size=32, columns=["id", "audio", "raw_transcription"]):
    for r in batch.to_pylist():
        if len(seen) >= N or r["id"] in seen:
            continue
        audio = decode(r["audio"]["bytes"])
        if len(audio) > 30 * 16000:
            continue
        seen.add(r["id"])
        cid = f"en_{len(seen):03d}"
        sf.write(CLIPS / f"{cid}.wav", audio, 16000)
        rows.append({"clip_id": cid, "corpus": "FLEURS en_us test", "group": "english", "reference": r["raw_transcription"]})
    if len(seen) >= N:
        break
print("english:", len(seen), flush=True)

# Mixed: Synth-Manglish held-out voices, not used in dev
n = 0
for shard in ("00000", "00001"):
    path = hf_hub_download("emhaihsan/Synth-Manglish", f"parquet/train-{shard}-of-00002.parquet", repo_type="dataset")
    for batch in pq.ParquetFile(path).iter_batches(batch_size=64, columns=["file_name", "text", "audio"]):
        for r in batch.to_pylist():
            stem, voice = r["file_name"].split("__")[:2]
            english, malay = estimate_language_ratio(r["text"])
            if n >= N or voice not in HELD_OUT or f"synth_{stem}.wav" in dev_files or not (english and malay):
                continue
            audio = decode(r["audio"]["bytes"])
            if len(audio) > 30 * 16000:
                continue
            n += 1
            cid = f"mx_{n:03d}"
            sf.write(CLIPS / f"{cid}.wav", audio, 16000)
            # Reference kept exactly as the corpus gives it (no style-guide respelling)
            rows.append({"clip_id": cid, "corpus": f"Synth-Manglish (voice {voice})", "group": "mixed", "reference": r["text"].strip()})
print("mixed:", n, flush=True)

with open(OUT / "manifest.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["clip_id", "corpus", "group", "reference"])
    w.writeheader()
    w.writerows(rows)
