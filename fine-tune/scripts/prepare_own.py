"""Turn your own recording sessions (RECORDING_PROMPTS.md) into training and test data.

    data/own/<speaker>/clips.csv + the audio files it names (wav, m4a, mp3, webm, ... anything ffmpeg reads)
      → test speakers: eval/real/001.wav ... + refs.json  (for bench_stt.py --real; never trained on)
      → everyone else: data/clips/<speaker>_<clip>.wav + rows in data/train.csv / data/dev.csv
                       (source "own-recording")

clips.csv columns (see OWN_DATA_GUIDE.md): file_name, prompt, device, condition, transcript, language, notes.
`language` may be blank: prompts D1-D5 default to "ms", everything else to "en".

Run after prepare_public.py, which rewrites train.csv / dev.csv from scratch. Re-running this is safe:
earlier own-recording rows are replaced, not duplicated.

    python scripts/prepare_own.py --test s01 s02 [--dev s03]
    python scripts/prepare_own.py --selftest        # checks this script on two made-up speakers
"""

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import soundfile

ROOT = Path(__file__).resolve().parent.parent
SOURCE = "own-recording"
MAX_SEC, MIN_SEC = 30.0, 0.5
FIELDS = ["file_name", "transcript", "language", "speaker", "source"]


def default_language(prompt: str) -> str:
    return "ms" if prompt.strip().upper().startswith("D") else "en"


def is_silence(prompt: str) -> bool:
    return prompt.strip().upper().startswith("G")


def to_wav(src: Path, dst: Path) -> float:
    """16 kHz mono 16-bit WAV (STYLE_GUIDE.md §1). Returns the duration in seconds."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ar", "16000", "-ac", "1",
                    "-sample_fmt", "s16", str(dst)], check=True)
    return soundfile.info(str(dst)).duration


def read_speaker(folder: Path, problems: list[str]) -> list[dict]:
    """The usable clips of one speaker, converted to WAV in a temp folder next to the originals."""
    speaker = folder.name
    sheet = folder / "clips.csv"
    if not sheet.exists():
        problems.append(f"{speaker}: no clips.csv")
        return []
    clips = []
    with open(sheet, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name, prompt = (row.get("file_name") or "").strip(), (row.get("prompt") or "").strip()
            text = (row.get("transcript") or "").strip()
            where = f"{speaker}/{name or '?'}"
            src = folder / name
            if name and not src.exists():  # same number, other extension (the template says .m4a; a laptop gives .wav)
                src = next((p for p in sorted(folder.glob(f"{Path(name).stem}.*")) if p.suffix.lower() != ".csv"), src)
            if not name or not src.exists():
                problems.append(f"{where}: audio file not found")
                continue
            if not text and not is_silence(prompt):
                problems.append(f"{where}: no transcript (only silence clips, prompts G1-G2, may be empty)")
                continue
            lang = (row.get("language") or "").strip().lower() or default_language(prompt)
            if lang not in ("en", "ms"):
                problems.append(f"{where}: language must be en or ms, not '{lang}'")
                continue
            stem = Path(name).stem
            wav = folder / ".converted" / f"{stem if stem.startswith(speaker) else f'{speaker}_{stem}'}.wav"
            try:
                secs = to_wav(src, wav)
            except subprocess.CalledProcessError:
                problems.append(f"{where}: ffmpeg couldn't read this file")
                continue
            if secs > MAX_SEC:
                problems.append(f"{where}: {secs:.0f} s is over {MAX_SEC:.0f} s: split it on a pause")
                continue
            if secs < MIN_SEC:
                problems.append(f"{where}: shorter than {MIN_SEC} s")
                continue
            clips.append({"wav": wav, "secs": secs, "transcript": text, "language": lang, "speaker": speaker})
    return clips


def merge_csv(path: Path, rows: list[dict]) -> None:
    """Replace this script's earlier rows in `path`, keep everything else (the public data)."""
    kept = []
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            kept = [r for r in csv.DictReader(f) if r.get("source") != SOURCE]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(kept + rows)


def prepare(own: Path, data: Path, real: Path, test: set[str], dev: set[str]) -> list[str]:
    problems: list[str] = []
    speakers = sorted(p for p in own.iterdir() if p.is_dir()) if own.exists() else []
    if not speakers:
        return [f"no speaker folders in {own}"]
    unknown = (test | dev) - {p.name for p in speakers}
    if unknown:
        return [f"--test/--dev name speakers with no folder: {sorted(unknown)}"]
    if not test:
        problems.append("warning: no --test speakers, so there is nothing to measure real-speaker accuracy on")

    train_rows, dev_rows, refs, sources, hours = [], [], {}, [], {"train": 0.0, "dev": 0.0, "test": 0.0}
    for folder in speakers:
        for c in read_speaker(folder, problems):
            if c["speaker"] in test:
                key = f"{len(refs) + 1:03d}"
                real.mkdir(parents=True, exist_ok=True)
                (real / f"{key}.wav").write_bytes(c["wav"].read_bytes())
                refs[key] = c["transcript"]
                sources.append({"id": key, "file": c["wav"].name})
                hours["test"] += c["secs"] / 3600
                continue
            (data / "clips").mkdir(parents=True, exist_ok=True)
            (data / "clips" / c["wav"].name).write_bytes(c["wav"].read_bytes())
            row = {"file_name": c["wav"].name, "transcript": c["transcript"], "language": c["language"],
                   "speaker": c["speaker"], "source": SOURCE}
            split = "dev" if c["speaker"] in dev else "train"
            (dev_rows if split == "dev" else train_rows).append(row)
            hours[split] += c["secs"] / 3600

    merge_csv(data / "train.csv", train_rows)
    merge_csv(data / "dev.csv", dev_rows)
    if refs:
        (real / "refs.json").write_text(json.dumps(refs, ensure_ascii=False, indent=1), encoding="utf-8")
        with open(real / "sources.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["id", "file"])
            w.writeheader()
            w.writerows(sources)
    print(f"train: {len(train_rows)} clips ({hours['train']:.2f} h)   dev: {len(dev_rows)} clips ({hours['dev']:.2f} h)   "
          f"test: {len(refs)} clips ({hours['test']:.2f} h)")
    return problems


def selftest() -> None:
    """Two made-up speakers: s01 is the test speaker, s02 trains; one clip of each kind of problem."""
    import numpy as np

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        own, data, real = root / "own", root / "data", root / "real"
        tone = lambda s: (np.sin(np.arange(int(44100 * s)) / 10) * 0.1).astype("float32")  # noqa: E731
        sheets = {
            "s01": [("001.m4a", "A1", "Um, I went to KL lah.", ""), ("002.m4a", "G1", "", "")],  # 002 is really a .wav
            "s02": [("001.wav", "D1", "Keluarga saya ada 5 orang.", ""), ("002.wav", "B1", "", ""),  # no transcript
                    ("003.wav", "A2", "Too long.", ""), ("004.wav", "B3", "My strength is, like, teamwork.", "xx")],
        }
        for spk, rows in sheets.items():
            (own / spk).mkdir(parents=True)
            for name, prompt, *_ in rows:
                wav = own / spk / (Path(name).stem + ".wav")  # every clip exists as .wav; 001 of s01 also as .m4a
                soundfile.write(str(wav), tone(35 if prompt == "A2" else 3), 44100)
                if name == "001.m4a":  # a phone-style file
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), str(own / spk / name)], check=True)
            with open(own / spk / "clips.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["file_name", "prompt", "device", "condition", "transcript", "language", "notes"])
                for name, prompt, text, lang in rows:
                    w.writerow([name, prompt, "laptop", "quiet", text, lang, ""])
        merge_csv(data / "train.csv", [{"file_name": "pub.wav", "transcript": "x", "language": "en", "speaker": "p", "source": "fleurs"}])

        for _ in range(2):  # re-running must not duplicate rows
            problems = prepare(own, data, real, test={"s01"}, dev=set())
        rows = list(csv.DictReader(open(data / "train.csv", encoding="utf-8")))
        assert [r["source"] for r in rows] == ["fleurs", SOURCE], rows          # public row kept, own row once
        assert rows[1] == {"file_name": "s02_001.wav", "transcript": "Keluarga saya ada 5 orang.", "language": "ms",
                           "speaker": "s02", "source": SOURCE}, rows[1]           # D prompt → ms
        assert soundfile.info(str(data / "clips" / "s02_001.wav")).samplerate == 16000
        refs = json.loads((real / "refs.json").read_text(encoding="utf-8"))
        assert refs == {"001": "Um, I went to KL lah.", "002": ""}, refs         # m4a converted; silence allowed
        assert any("no transcript" in p for p in problems) and any("over 30 s" in p for p in problems), problems
        assert any("language must be" in p for p in problems), problems
    print("selftest ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", nargs="*", default=[], help="speakers kept out of training, for bench_stt.py --real")
    ap.add_argument("--dev", nargs="*", default=[], help="speakers used to choose the best training epoch")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        sys.exit(0)
    issues = prepare(ROOT / "data" / "own", ROOT / "data", ROOT / "eval" / "real", set(args.test), set(args.dev))
    for p in issues:
        print("  !", p)
    sys.exit(1 if any(not p.startswith("warning") for p in issues) else 0)  # skipped clips: fix and re-run
