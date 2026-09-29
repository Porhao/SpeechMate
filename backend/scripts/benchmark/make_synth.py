"""Generate Malaysian-accented English and Manglish test utterances with the local Malaysian TTS."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, "/app")
from app.services import malaysian_tts as m

OUT = Path("/models/eval/synth"); OUT.mkdir(parents=True, exist_ok=True)
CASES = [
    ("english", "husein",  "My final year project helps students practise public speaking with an AI coach."),
    ("english", "idayu",   "I usually take the train from Petaling Jaya to Kuala Lumpur every morning."),
    ("english", "haqkiem", "During the interview I was nervous, but my answers were quite clear."),
    ("english", "idayu",   "The supervisor asked me to explain the method more clearly next week."),
    ("mixed",   "husein",  "Saya rasa presentation tadi okay, tapi slide kedua terlalu banyak text."),
    ("mixed",   "idayu",   "Actually I nak explain dulu the main problem, then baru masuk solution."),
    ("mixed",   "haqkiem", "Semalam I pergi Ipoh dengan family, makan chicken rice sampai kenyang lah."),
    ("mixed",   "idayu",   "Kalau you boleh slow down sikit, audience senang nak faham point you."),
]
manifest = []
for i, (cat, voice, text) in enumerate(CASES):
    path = OUT / f"{cat}_{i}.wav"
    if not path.exists():
        t = time.time(); m.synthesize(text, path, voice); print(f"{path.name} {time.time()-t:.0f}s", flush=True)
    manifest.append({"category": cat, "path": str(path), "text": text})
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
print("SYNTH_DONE")
