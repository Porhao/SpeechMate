"""Generate standard-accent (US/UK) English test utterances with the Kokoro TTS server.

The Malaysian-accented clips (make_synth.py) don't catch a model that *translates*
non-Malaysian English into Malay, so the benchmark also needs plain US/UK English.
Run inside the backend container while the `kokoro` service is up.
"""
import json
import subprocess
import urllib.request
from pathlib import Path

OUT = Path("/models/eval/synth_kokoro"); OUT.mkdir(parents=True, exist_ok=True)
CASES = [
    ("af_heart", "Tell me about a time you worked in a team that disagreed, and what you did about it."),
    ("am_michael", "I'm a final year statistics student and I built dashboards during my internship."),
    ("bf_emma", "The main message of my presentation is that small daily habits beat last minute cramming."),
    ("bm_george", "Could you give me a specific example of how you measured the result of that project?"),
    ("af_bella", "We compared both tools with real data and delivered the report two weeks early."),
    ("am_michael", "Honestly, I think the hardest part was explaining the method to people without a technical background."),
]
manifest = []
for i, (voice, text) in enumerate(CASES):
    path = OUT / f"english_std_{i}.wav"
    if not path.exists():
        req = urllib.request.Request("http://kokoro:8880/v1/audio/speech", method="POST",
                                     data=json.dumps({"model": "kokoro", "input": text, "voice": voice, "response_format": "wav"}).encode(),
                                     headers={"Content-Type": "application/json"})
        raw = urllib.request.urlopen(req, timeout=120).read()
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "-", "-ar", "16000", "-ac", "1", str(path)], input=raw, check=True)
    manifest.append({"category": "english_std", "path": str(path), "text": text})
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
print("SYNTH_DONE", len(manifest))
