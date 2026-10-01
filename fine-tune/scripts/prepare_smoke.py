"""F4 smoke-test data: FLEURS ms_my *validation* clips -> data/ in the plan's layout (§5).

Only proves the training pipeline runs; it is not Manglish. FLEURS is CC BY 4.0. The STT
benchmark uses the *test* split, so nothing here leaks into it. A few silent clips with
empty transcripts exercise the silence path (plan §4.4).
"""
import csv
import io
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import soundfile as sf
from huggingface_hub import hf_hub_download

N_TRAIN, N_DEV, N_SILENT = 200, 40, 6
DATA = Path(__file__).resolve().parent.parent / "data"
CLIPS = DATA / "clips"
CLIPS.mkdir(parents=True, exist_ok=True)

src = hf_hub_download("google/fleurs", "ms_my/validation/0000.parquet",
                      repo_type="dataset", revision="refs/convert/parquet")
rows = {"train": [], "dev": []}
for batch in pq.ParquetFile(src).iter_batches(batch_size=32, columns=["id", "audio", "raw_transcription"]):
    for r in batch.to_pylist():
        # Split by sentence id: FLEURS repeats a sentence across speakers, so a clip-level
        # split would put the same text in train and dev
        split = "dev" if r["id"] % 6 == 0 else "train"
        if len(rows[split]) >= (N_DEV if split == "dev" else N_TRAIN):
            continue
        audio, sr = sf.read(io.BytesIO(r["audio"]["bytes"]))
        if sr != 16000 or len(audio) > 30 * sr:  # Whisper cuts at 30 s; the label wouldn't
            continue
        name = f"fleurs_{split}_{len(rows[split]):03d}.wav"
        sf.write(CLIPS / name, audio, sr)
        rows[split].append({"file_name": name, "transcript": r["raw_transcription"],
                            "language": "ms", "speaker": "fleurs", "source": "fleurs-validation"})
    if len(rows["train"]) >= N_TRAIN and len(rows["dev"]) >= N_DEV:
        break

for i in range(N_SILENT):
    split = "dev" if i < 2 else "train"
    name = f"silent_{i}.wav"
    noise = np.random.default_rng(i).normal(0, 0.002, 16000 * 5)  # near-silent room tone
    sf.write(CLIPS / name, noise, 16000)
    rows[split].append({"file_name": name, "transcript": "", "language": "ms",
                        "speaker": "silence", "source": "generated"})

for split, rs in rows.items():
    with open(DATA / f"{split}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file_name", "transcript", "language", "speaker", "source"])
        w.writeheader()
        w.writerows(rs)
    print(split, len(rs), "clips")
