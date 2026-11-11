"""Generate the voiceover with Kokoro (the app's Kokoro-FastAPI container, af_heart) and time the captions.

Writes composition/assets/voice/<scene>.wav and tools/timing.json:
  {scene: {"dur": seconds, "chunks": [{"en", "ms", "start", "end"}]}}
Caption times come from Kokoro's own word timestamps, matched to each chunk by its letters.
Run: python3 tools/build_voice.py   (from brag-output/)
"""
import base64, io, json, re, sys, urllib.request, wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from narration import SCENES

URL = "http://localhost:8880/dev/captioned_speech"
VOICE, SPEED, GAP = "af_heart", 0.95, 0.45   # GAP: silence between paragraphs (s)
OUT = Path(__file__).parent.parent / "composition" / "assets" / "voice"
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())


def speak(text):
    body = json.dumps({"model": "kokoro", "input": text, "voice": VOICE, "speed": SPEED,
                       "response_format": "wav", "stream": False, "return_timestamps": True}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=300))
    w = wave.open(io.BytesIO(base64.b64decode(d["audio"])))
    # Kokoro streams its WAV, so the header's frame count is a placeholder: read everything, reset it
    return w.getparams()._replace(nframes=0), w.readframes(w.getnframes()), [t for t in d["timestamps"] if norm(t["word"])]


def align(chunks, words, offset):
    """Give each chunk the time span of the Kokoro words whose letters spell it."""
    out, i = [], 0
    for c in chunks:
        need, got, first = norm(c[2] if len(c) > 2 else c[0]), "", i
        while i < len(words) and len(got) < len(need):
            got += norm(words[i]["word"]); i += 1
        assert got == need, f"caption/voice mismatch: {need!r} vs {got!r}"
        out.append({"en": c[0], "ms": c[1], "start": round(offset + words[first]["start_time"], 3),
                    "end": round(offset + words[i - 1]["end_time"], 3),
                    # word ends, so a long caption can be paged in step with the voice
                    "word_ends": [round(offset + w["end_time"], 3) for w in words[first:i]]})
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    timing = {}
    for sid, paragraphs, min_dur in SCENES:
        pcm, params, chunks, t = b"", None, [], 0.0
        for p in paragraphs:
            params, frames, words = speak(" ".join(c[2] if len(c) > 2 else c[0] for c in p))
            if pcm:
                pcm += b"\0" * (int(GAP * params.framerate) * params.sampwidth * params.nchannels)
                t += GAP
            chunks += align(p, words, t)
            pcm += frames
            t += len(frames) / (params.framerate * params.sampwidth * params.nchannels)
        with wave.open(str(OUT / f"{sid}.wav"), "wb") as w:
            w.setparams(params); w.writeframes(pcm)
        timing[sid] = {"dur": round(t, 3), "min": min_dur, "chunks": chunks}
        print(f"{sid}: {t:6.2f}s  {len(chunks)} captions")
    (Path(__file__).parent / "timing.json").write_text(json.dumps(timing, indent=1, ensure_ascii=False))
    print(f"total voice: {sum(v['dur'] for v in timing.values()):.1f}s")


if __name__ == "__main__":
    main()
