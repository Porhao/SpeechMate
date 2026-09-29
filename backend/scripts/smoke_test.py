"""End-to-end smoke test against a running API — exercises both agents.

    python scripts/smoke_test.py                       # sample deck, no voice sample
    python scripts/smoke_test.py --deck my.pptx --voice me.m4a --practice my_take.webm

Without --practice, the generated ideal video itself is uploaded as the
"practice" recording, so the whole loop runs with no microphone needed.
Outputs (video, JSON responses) are written to ./smoke_output/.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from make_sample_deck import build as build_sample_deck  # noqa: E402

OUT = Path("smoke_output")


def poll(client: httpx.Client, url: str, done: set[str], label: str, timeout: float) -> dict:
    start, last = time.time(), None
    while True:
        data = client.get(url).raise_for_status().json()
        progress = data.get("slides_progress")
        line = f"  {label}: {data['status']}" + (
            f"  (rendered {progress['rendered']}/{progress['total']}, scripted {progress['scripted']}, "
            f"synthesized {progress['synthesized']})" if progress else ""
        )
        if line != last:
            print(line)
            last = line
        if data["status"] in done:
            return data
        if time.time() - start > timeout:
            sys.exit(f"Timed out waiting for {label}")
        time.sleep(2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--deck", type=Path)
    parser.add_argument("--voice", type=Path, help="voice sample for cloning (optional)")
    parser.add_argument("--practice", type=Path, help="your practice recording (optional)")
    parser.add_argument("--requirement", default="For first-year university students, English course presentation")
    parser.add_argument("--timeout", type=float, default=900)
    args = parser.parse_args()

    OUT.mkdir(exist_ok=True)
    deck = args.deck or build_sample_deck(OUT / "sample_deck.pptx")
    client = httpx.Client(base_url=args.api, timeout=120)

    print("1. Health check")
    health = client.get("/health").raise_for_status().json()
    print("  ", json.dumps(health))

    print(f"2. Upload deck {deck}")
    files = {"pptx": (deck.name, deck.read_bytes())}
    if args.voice:
        files["voice_sample"] = (args.voice.name, args.voice.read_bytes())
    created = client.post(
        "/api/sessions", files=files, data={"requirement_prompt": args.requirement}
    ).raise_for_status().json()
    sid = created["session_id"]
    print(f"   session_id = {sid}")

    print("3. Ideal Presentation Agent")
    session = poll(client, f"/api/sessions/{sid}", {"complete", "failed"}, "session", args.timeout)
    if session["status"] == "failed":
        sys.exit(f"   FAILED: {session['error_detail']}")
    for w in session["warnings"]:
        print(f"   warning: {w}")

    scripts = client.get(f"/api/sessions/{sid}/scripts").raise_for_status().json()
    (OUT / "scripts.json").write_text(json.dumps(scripts, indent=2))
    for s in scripts["slides"]:
        print(f"   [slide {s['slide_index']} @ {s['start_sec']}s, {s['word_count']} words, "
              f"{s['script_source']}/{s['audio_source']}] {s['script_text'][:90]}...")

    video = OUT / "ideal_video.mp4"
    video.write_bytes(client.get(f"/api/sessions/{sid}/video").raise_for_status().content)
    print(f"   video saved to {video} ({video.stat().st_size // 1024} KB)")

    if not args.practice and all(s["audio_source"] == "silence" for s in scripts["slides"]):
        sys.exit(
            "   The ideal narration is silent (no TTS available: add OPENAI_API_KEY or install espeak-ng),\n"
            "   so it can't double as a practice recording. Re-run with --practice <your recording>."
        )

    print("4. Coach Agent — whole-deck practice")
    practice_file = args.practice or video
    pid = client.post(
        f"/api/sessions/{sid}/practice",
        files={"audio": (practice_file.name, practice_file.read_bytes())},
    ).raise_for_status().json()["practice_id"]
    practice = poll(client, f"/api/sessions/{sid}/practice/{pid}", {"complete", "failed"}, "practice", args.timeout)
    (OUT / "practice.json").write_text(json.dumps(practice, indent=2))
    if practice["status"] == "failed":
        sys.exit(f"   FAILED: {practice['error_detail']}")
    for w in practice["warnings"]:
        print(f"   warning: {w}")
    print("   metrics:", json.dumps(practice["metrics"]))
    fb = practice["feedback"]
    print(f"   encouragement: {fb['encouragement']}")
    for o in fb["observations"]:
        print(f"   - O: {o['observation']}\n     I: {o['impact']}\n     S: {o['suggestion']}")
    aud = practice["audience_feedback"]
    print(f"   audience ({aud['audience_profile']}): clarity {aud['clarity_score']}/5, "
          f"engagement {aud['engagement_score']}/5 — {aud['overall_impression']}")

    print("5. Coach Agent — per-slide practice (slide 1)")
    slide_audio = (
        args.practice.read_bytes() if args.practice
        else client.get(f"/api/sessions/{sid}/slides/1/audio").raise_for_status().content
    )
    pid2 = client.post(
        f"/api/sessions/{sid}/practice",
        files={"audio": (args.practice.name if args.practice else "slide1.wav", slide_audio)},
        data={"recording_granularity": "per_slide", "slide_index": "1"},
    ).raise_for_status().json()["practice_id"]
    p2 = poll(client, f"/api/sessions/{sid}/practice/{pid2}", {"complete", "failed"}, "practice", args.timeout)
    print(f"   status={p2['status']} duration={p2['metrics'] and p2['metrics']['duration_sec']}s "
          f"ideal={p2['metrics'] and p2['metrics']['ideal_duration_sec']}s")

    print("6. Chat follow-up")
    reply = client.post(
        f"/api/sessions/{sid}/practice/{pid}/chat",
        json={"message": "What is the single most important thing I should fix before my next run?"},
    ).raise_for_status().json()
    print(f"   coach: {reply['content']}")
    history = client.get(f"/api/sessions/{sid}/practice/{pid}/chat").raise_for_status().json()
    print(f"   chat history has {len(history['messages'])} messages")

    print(f"\nAll steps passed. Outputs in {OUT.resolve()}")


if __name__ == "__main__":
    main()
