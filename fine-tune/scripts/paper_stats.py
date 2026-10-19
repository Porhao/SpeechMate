"""Confidence intervals and paired tests for the paper's speech-recognition comparisons.

Reads the per-clip outputs already saved in eval/paper/ (no models run) and prints, per group:
corpus WER for each system, a 95% bootstrap CI (clips resampled, 5000 draws, seed 0), and a
paired comparison: the bootstrap CI of the WER difference and an exact two-sided sign test
over clips whose error count differs. Same normalisation as eval_routing.py / eval_finetune.py.

    python fine-tune/scripts/paper_stats.py
"""

import csv
import random
import re
from math import comb
from pathlib import Path

PAPER = Path(__file__).resolve().parent.parent / "eval" / "paper"
DRAWS, SEED = 5000, 0


def norm(t):
    return re.findall(r"[a-z0-9']+", t.lower().replace("’", "'"))


def edits(r, h):
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev, d[j] = d[j], cur
    return d[len(h)]


def sign_test(wins, losses):
    """Exact two-sided binomial test, p = 0.5, ties dropped."""
    n, k = wins + losses, min(wins, losses)
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def compare(rows, a, b):
    """rows: [(ref_words, {system: errors})]. Prints WER + CI for a and b, and the paired difference."""
    rng = random.Random(SEED)
    n_ref = [len(r) for r, _ in rows]
    ea = [e[a] for _, e in rows]
    eb = [e[b] for _, e in rows]
    wer = lambda errs, idx: 100 * sum(errs[i] for i in idx) / sum(n_ref[i] for i in idx)
    full = range(len(rows))
    boots = []
    for _ in range(DRAWS):
        idx = [rng.randrange(len(rows)) for _ in rows]
        boots.append((wer(ea, idx), wer(eb, idx)))
    ci = lambda xs: (sorted(xs)[int(0.025 * DRAWS)], sorted(xs)[int(0.975 * DRAWS)])
    lo_a, hi_a = ci([x for x, _ in boots])
    lo_b, hi_b = ci([y for _, y in boots])
    lo_d, hi_d = ci([y - x for x, y in boots])
    wins = sum(y < x for x, y in zip(ea, eb))
    losses = sum(y > x for x, y in zip(ea, eb))
    print(f"  {a:>12}: {wer(ea, full):5.1f}%  [{lo_a:4.1f}, {hi_a:4.1f}]")
    print(f"  {b:>12}: {wer(eb, full):5.1f}%  [{lo_b:4.1f}, {hi_b:4.1f}]")
    print(f"  {b} - {a}: {wer(eb, full) - wer(ea, full):+5.1f} pts [{lo_d:+.1f}, {hi_d:+.1f}]; "
          f"clips better/worse/same {wins}/{losses}/{len(rows) - wins - losses}; sign test p = {sign_test(wins, losses):.2g}")
    return wer(ea, full), wer(eb, full)


def load(name, systems):
    by_group = {}
    with open(PAPER / name, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ref = norm(row["reference"])
            by_group.setdefault(row["group"], []).append((ref, {s: edits(ref, norm(row[s])) for s in systems}))
    return by_group


GROQ_USD_PER_HOUR, GROQ_MIN_BILLED_SEC = 0.111, 10  # console.groq.com/docs/speech-to-text, checked 2026-10-15


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p / 100 * len(xs)))]


def groq_section(routing, ft, path):
    """Deployed cloud ASR (eval_groq.py output) vs the local systems on the same clips."""
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    hyp = {r["clip_id"]: r for r in rows}
    print("\nDeployed cloud ASR: Groq whisper-large-v3 (app prompt, verbose_json, word timestamps)")
    with open(PAPER / "finetune_results.csv", newline="", encoding="utf-8") as f:
        ft_rows = {r["clip_id"]: r for r in csv.DictReader(f)}
    with open(PAPER / "results.csv", newline="", encoding="utf-8") as f:
        rt_rows = {r["clip_id"]: r for r in csv.DictReader(f)}
    for group in ("english", "mixed"):
        ids = [c for c, r in rt_rows.items() if r["group"] == group and c in hyp]
        pairs = []
        for c in ids:
            ref = norm(rt_rows[c]["reference"])
            pairs.append((ref, {
                "local_v3": edits(ref, norm(rt_rows[c]["routing_off"])),
                "shipped": edits(ref, norm(ft_rows[c]["shipped"])),
                "groq": edits(ref, norm(hyp[c]["hypothesis"])),
            }))
        print(f" {group} ({len(pairs)} clips): vs the same weights run locally")
        compare(pairs, "local_v3", "groq")
        print(f" {group}: vs the shipped Malaysian model")
        compare(pairs, "shipped", "groq")
    malay = [r for r in rows if r["group"] == "malay"]
    if malay:
        e = sum(edits(norm(r["reference"]), norm(r["hypothesis"])) for r in malay)
        n = sum(len(norm(r["reference"])) for r in malay)
        print(f" malay ({len(malay)} clips, FLEURS ms_my, real speakers): WER {100 * e / n:.1f}% (no local run on these clips)")
    langs = {}
    for r in rows:
        if r["group"] != "silence":
            langs.setdefault(r["group"], {}).setdefault(r["language"], 0)
            langs[r["group"]][r["language"]] += 1
    print(" detected language by group:", langs)
    sil = [r for r in rows if r["group"] == "silence"]
    if sil:
        with_text = [r for r in sil if norm(r["hypothesis"])]
        print(f" silence/noise clips with any text (no VAD in front): {len(with_text)}/{len(sil)}"
              + "".join(f"\n   {r['clip_id']}: {r['hypothesis']!r}" for r in with_text))
    speech = [r for r in rows if r["group"] != "silence"]
    lat = [float(r["latency_sec"]) for r in speech]
    audio = [float(r["audio_sec"]) for r in speech]
    print(f" latency per request (n={len(lat)}, audio {min(audio):.1f}-{max(audio):.1f} s): "
          f"median {pct(lat, 50):.2f} s, p90 {pct(lat, 90):.2f} s, p95 {pct(lat, 95):.2f} s, max {max(lat):.2f} s")
    no_words = sum(1 for r in speech if norm(r["hypothesis"]) and int(r["words_with_timestamps"]) == 0)
    print(f" clips with text but no word timestamps: {no_words}")
    billed = sum(max(GROQ_MIN_BILLED_SEC, a) for a in audio)
    print(f" cost of this run: {sum(audio) / 60:.1f} min audio, {billed / 60:.1f} min billed, "
          f"${billed / 3600 * GROQ_USD_PER_HOUR:.3f}")


def main():
    print("Routing (plain Whisper large-v3, app's _transcribe_local): routing_off vs routing_on")
    routing = load("results.csv", ["routing_off", "routing_on"])
    for group, rows in sorted(routing.items()):
        print(f" {group} ({len(rows)} clips)")
        compare(rows, "routing_off", "routing_on")
    print("\nShipped Mesolitica turbo-v3 vs LoRA fine-tune (no prompt)")
    ft = load("finetune_results.csv", ["shipped", "ft", "ft_prompt"])
    for group, rows in sorted(ft.items()):
        print(f" {group} ({len(rows)} clips)")
        compare(rows, "shipped", "ft")
    groq_path = PAPER / "groq_results.csv"
    if groq_path.exists():
        groq_section(routing, ft, groq_path)
    # Self-check: the corpus WERs reported in docs/benchmarks/stt-routing-and-finetune-2026-10-06.md
    def corpus(rows, s):
        return round(100 * sum(e[s] for _, e in rows) / sum(len(r) for r, _ in rows), 1)
    assert corpus(routing["english"], "routing_off") == 5.3 and corpus(routing["mixed"], "routing_on") == 36.7
    assert corpus(ft["english"], "shipped") == 9.4 and corpus(ft["mixed"], "ft") == 6.7
    print("\nself-check: reproduces the reported WERs")


if __name__ == "__main__":
    main()
