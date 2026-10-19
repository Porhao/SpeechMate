"""Send study recordings through the deployed SpeechMate app and save what it measured,
in the CSV formats study_stats.py reads (fine-tune/docs/EVALUATION.md).

Each clip becomes one Conversation session for a dedicated evaluation account (never the
demo account): upload → analyse → read the analysis. The session is deleted afterwards
unless --keep. Uses the same speech-to-text and LLM as real users (Groq, Gemini), so it
counts against their quotas: about one STT request and one or two LLM calls per clip.

    python fine-tune/scripts/run_app_on_clips.py --clips fine-tune/eval/real --out fine-tune/eval/real/app
Writes app_outputs.csv (clip_id, transcript), app_events.csv (clip_id, type, t_sec),
app_scores.csv (clip_id, construct, score) and analysis/<clip_id>.json.
"""

import argparse
import csv
import json
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ACCOUNT = {"email": "eval@speechmate.dev", "password": "Eval-study-2026!", "full_name": "Evaluation runner"}


def call(base, method, path, body=None, token=None, raw_body=None, ctype="application/json"):
    data = raw_body if raw_body is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(base + path, method=method, data=data,
                                 headers={"Content-Type": ctype, **({"Authorization": f"Bearer {token}"} if token else {})})
    with urllib.request.urlopen(req, timeout=600) as r:
        out = r.read()
    return json.loads(out) if out else None


def login(base):
    try:
        call(base, "POST", "/auth/register", ACCOUNT)
    except urllib.error.HTTPError as e:
        if e.code not in (400, 409):
            raise
    token = call(base, "POST", "/auth/login", {k: ACCOUNT[k] for k in ("email", "password")})["access_token"]
    # The app refuses cloud processing without consent. Study participants give theirs on the signed
    # consent form (OWN_DATA_GUIDE.md); this records it for the evaluation account that submits their clips.
    call(base, "POST", "/users/me/consent", {"accept": True}, token)
    return token


def analyse(base, token, clip: Path) -> dict:
    s = call(base, "POST", "/live", {"session_type": "Conversation"}, token)
    call(base, "POST", f"/live/{s['id']}/end", {"duration_sec": 0}, token)
    bnd = uuid.uuid4().hex
    body = (f"--{bnd}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{clip.name}\"\r\n"
            "Content-Type: application/octet-stream\r\n\r\n").encode() + clip.read_bytes() + f"\r\n--{bnd}--\r\n".encode()
    call(base, "POST", f"/live/{s['id']}/recording", raw_body=body, token=token, ctype=f"multipart/form-data; boundary={bnd}")
    call(base, "POST", f"/live/{s['id']}/analyze", {}, token)
    while True:
        time.sleep(3)
        r = call(base, "GET", f"/live/{s['id']}", token=token)
        if r["status"] != "analyzing":
            return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", required=True, help="folder of .wav (or any audio/video) files; the file stem is the clip id")
    ap.add_argument("--out", required=True)
    ap.add_argument("--api", default="http://localhost:8000/api")
    ap.add_argument("--keep", action="store_true", help="keep the sessions in the evaluation account")
    a = ap.parse_args()
    out = Path(a.out)
    (out / "analysis").mkdir(parents=True, exist_ok=True)
    token = login(a.api)
    clips = sorted(p for p in Path(a.clips).iterdir() if p.suffix.lower() in (".wav", ".mp3", ".m4a", ".webm", ".mp4", ".flac"))
    for i, clip in enumerate(clips, 1):
        target = out / "analysis" / f"{clip.stem}.json"
        if target.exists():
            continue                                        # resumable
        r = analyse(a.api, token, clip)
        target.write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
        if not a.keep:
            call(a.api, "DELETE", f"/live/{r['id']}", token=token)
        print(f"{i}/{len(clips)} {clip.stem}: {r['status']}", flush=True)

    rows_t, rows_e, rows_s = [], [], []
    for f in sorted((out / "analysis").glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        an = r.get("analysis") or {}
        rows_t.append({"clip_id": f.stem, "transcript": an.get("transcript") or ""})
        rows_e += [{"clip_id": f.stem, "type": e["type"], "t_sec": e["t_sec"]} for e in (an.get("details") or {}).get("disfluencies") or []]
        for construct, value in (("pronunciation", (an.get("speech") or {}).get("pronunciation_score")),
                                 ("confidence", (an.get("vision") or {}).get("confidence_score")),
                                 ("overall", (an.get("communication_score") or {}).get("overall_score"))):
            if value is not None:
                rows_s.append({"clip_id": f.stem, "construct": construct, "score": value})
    for name, rows, fields in (("app_outputs.csv", rows_t, ["clip_id", "transcript"]),
                               ("app_events.csv", rows_e, ["clip_id", "type", "t_sec"]),
                               ("app_scores.csv", rows_s, ["clip_id", "construct", "score"])):
        with open(out / name, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fields)
            w.writeheader()
            w.writerows(rows)
    print(f"wrote {out}/app_outputs.csv, app_events.csv, app_scores.csv ({len(rows_t)} clips)")


if __name__ == "__main__":
    main()
