"""Statistics for the real-speaker studies (TECHNICAL.md §IV.C), ready before the data arrives.

Every result comes with a 95% CI and is checked against the pre-registered threshold. Stdlib only.
CSV formats are in fine-tune/docs/EVALUATION.md.

    python fine-tune/scripts/study_stats.py asr     --refs eval/real/refs.json --hyps out/app_outputs.csv [--groups groups.csv]
    python fine-tune/scripts/study_stats.py events  --gold annotations.csv --system out/app_events.csv [--tolerance 0.5]
    python fine-tune/scripts/study_stats.py ratings --ratings ratings.csv --system out/app_scores.csv
    python fine-tune/scripts/study_stats.py likert  --responses uat.csv
    python fine-tune/scripts/study_stats.py selftest
"""

import argparse
import csv
import json
import math
import random
import re
import statistics
import sys
from itertools import combinations, product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paper_stats import edits, norm  # same WER normalisation as every benchmark  # noqa: E402

DRAWS, SEED = 5000, 0
THRESHOLDS = {"pronunciation": 0.7, "confidence": 0.5, "overall": 0.6}   # min correlation with raters
F1_TARGET, LIKERT_TARGET = 0.75, 4.0

# fine-tune/docs/STYLE_GUIDE.md: one spelling per spoken form, so spelling variants aren't counted as errors
SPELLING = {"la": "lah", "laa": "lah", "loh": "lor", "ma": "mah", "lei": "leh", "kann": "kan", "wei": "weh",
            "aiyoh": "aiyo", "waa": "wah", "ok": "okay", "okey": "okay", "bole": "boleh", "ape": "apa",
            "tak de": "takde", "aje": "je"}


def spelling_norm(text: str) -> list[str]:
    t = " " + " ".join(norm(text)) + " "
    t = re.sub(r"(\w)(lah) ", r"\1 lah ", t)                 # "kenyanglah" → "kenyang lah"
    for a, b in SPELLING.items():
        t = t.replace(f" {a} ", f" {b} ")
    return t.split()


def ci(xs: list[float]) -> tuple[float, float]:
    xs = sorted(xs)
    return xs[int(0.025 * len(xs))], xs[min(len(xs) - 1, int(0.975 * len(xs)))]


def boot(items: list, stat, draws: int = DRAWS) -> tuple[float, float]:
    """95% bootstrap CI of stat(sample) over items resampled with replacement (clips or participants)."""
    rng = random.Random(SEED)
    vals = []
    for _ in range(draws):
        v = stat([items[rng.randrange(len(items))] for _ in items])
        if v is not None:
            vals.append(v)
    return ci(vals) if vals else (float("nan"), float("nan"))


def ranks(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1                     # ties share the mean rank
        i = j + 1
    return r


def pearson(x, y):
    if len(x) < 3:
        return None
    mx, my = statistics.mean(x), statistics.mean(y)
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy) if sx and sy else None


def spearman(x, y):
    return pearson(ranks(x), ranks(y))


def fisher_ci(r: float, n: int) -> tuple[float, float]:
    if n < 4 or abs(r) >= 1:
        return (r, r)
    z, se = math.atanh(r), 1 / math.sqrt(n - 3)
    return math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se)


def perm_p(x, y, fn, draws: int = DRAWS) -> float:
    """Two-sided permutation p-value of a correlation."""
    r0, rng, y = abs(fn(x, y) or 0), random.Random(SEED), list(y)
    hits = 0
    for _ in range(draws):
        rng.shuffle(y)
        hits += abs(fn(x, y) or 0) >= r0 - 1e-12
    return (hits + 1) / (draws + 1)


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ── 1. Speech recognition ────────────────────────────────────────────────────

def asr(refs: dict[str, str], hyps: dict[str, str], groups: dict[str, str]) -> dict:
    out = {}
    clips = [c for c in refs if c in hyps]
    for group in sorted({groups.get(c, "all") for c in clips}) + (["all"] if groups else []):
        ids = [c for c in clips if group == "all" or groups.get(c, "all") == group]
        res = {"clips": len(ids)}
        for name, tok in (("raw", norm), ("spelling_normalised", spelling_norm)):
            pairs = [(edits(tok(refs[c]), tok(hyps[c])), len(tok(refs[c]))) for c in ids]
            wer = lambda ps: 100 * sum(e for e, _ in ps) / max(1, sum(n for _, n in ps))
            res[name] = {"wer": round(wer(pairs), 1), "ci95": [round(v, 1) for v in boot(pairs, wer)]}
        out[group] = res
    silent = [c for c in clips if not norm(refs[c])]
    out["silent_clips_with_text"] = f"{sum(1 for c in silent if norm(hyps[c]))}/{len(silent)}"
    return out


# ── 2. Filler and disfluency detection ──────────────────────────────────────

def match_events(gold: list[float], system: list[float], tol: float) -> int:
    """Greedy one-to-one matches within ±tol seconds."""
    used, hits = set(), 0
    for g in sorted(gold):
        best = min((i for i, s in enumerate(system) if i not in used and abs(s - g) <= tol),
                   key=lambda i: abs(system[i] - g), default=None)
        if best is not None:
            used.add(best)
            hits += 1
    return hits


def events(gold_rows: list[dict], sys_rows: list[dict], tol: float) -> dict:
    def by(rows):
        d = {}
        for r in rows:
            d.setdefault((r["clip_id"], r["type"].strip().lower()), []).append(float(r["t_sec"]))
        return d
    gold, system = by(gold_rows), by(sys_rows)
    clips = sorted({c for c, _ in gold} | {c for c, _ in system})
    types = sorted({t for _, t in gold} | {t for _, t in system})
    out = {}
    for t in types + ["any"]:
        per_clip = []                                        # (true positives, system count, gold count)
        for c in clips:
            g = [x for (cc, tt), xs in gold.items() if cc == c and (t == "any" or tt == t) for x in xs]
            s = [x for (cc, tt), xs in system.items() if cc == c and (t == "any" or tt == t) for x in xs]
            per_clip.append((match_events(g, s, tol), len(s), len(g)))

        def f1(rows):
            tp, ns, ng = (sum(r[i] for r in rows) for i in range(3))
            return 2 * tp / (ns + ng) if ns + ng else None
        tp, ns, ng = (sum(r[i] for r in per_clip) for i in range(3))
        out[t] = {"gold": ng, "system": ns, "precision": round(tp / ns, 3) if ns else None,
                  "recall": round(tp / ng, 3) if ng else None, "f1": round(f1(per_clip) or 0, 3),
                  "f1_ci95": [round(v, 3) for v in boot(per_clip, f1)],
                  "meets_target": (f1(per_clip) or 0) >= F1_TARGET}
    return out


# ── 3. Human ratings: agreement and validity ────────────────────────────────

def icc2(matrix: list[list[float]]) -> tuple[float, float] | None:
    """ICC(2,1) and ICC(2,k): two-way random effects, absolute agreement (Koo & Li 2016).
    matrix = one row per clip, one column per rater (complete rows only)."""
    n, k = len(matrix), len(matrix[0]) if matrix else 0
    if n < 3 or k < 2:
        return None
    grand = statistics.mean(v for row in matrix for v in row)
    row_m = [statistics.mean(r) for r in matrix]
    col_m = [statistics.mean(matrix[i][j] for i in range(n)) for j in range(k)]
    ssr = k * sum((m - grand) ** 2 for m in row_m)
    ssc = n * sum((m - grand) ** 2 for m in col_m)
    sst = sum((v - grand) ** 2 for row in matrix for v in row)
    msr, msc = ssr / (n - 1), ssc / (k - 1)
    mse = (sst - ssr - ssc) / ((n - 1) * (k - 1))
    single = (msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n)
    average = (msr - mse) / (msr + (msc - mse) / n)
    return single, average


def ratings(rating_rows: list[dict], system_rows: list[dict]) -> dict:
    out = {}
    for construct in sorted({r["construct"] for r in rating_rows}):
        rs = [r for r in rating_rows if r["construct"] == construct]
        raters = sorted({r["rater"] for r in rs})
        table = {}
        for r in rs:
            table.setdefault(r["clip_id"], {})[r["rater"]] = float(r["score"])
        complete = [c for c in table if all(x in table[c] for x in raters)]
        matrix = [[table[c][x] for x in raters] for c in complete]
        res = {"clips": len(table), "raters": len(raters), "complete_clips": len(complete)}
        iccs = icc2(matrix)
        if iccs:
            res["icc_2_1"], res["icc_2_k"] = round(iccs[0], 3), round(iccs[1], 3)
            res["icc_2_k_ci95"] = [round(v, 3) for v in boot(matrix, lambda m: (icc2(m) or (None, None))[1])]
        res["rater_pairs_spearman"] = {f"{a}~{b}": round(spearman([table[c][a] for c in complete],
                                                                  [table[c][b] for c in complete]) or 0, 3)
                                       for a, b in combinations(raters, 2)}
        mean_rating = {c: statistics.mean(table[c].values()) for c in table}
        sys_scores = {r["clip_id"]: float(r["score"]) for r in system_rows if r["construct"] == construct and r["score"] not in ("", None)}
        both = [c for c in mean_rating if c in sys_scores]
        if len(both) >= 4:
            x, y = [sys_scores[c] for c in both], [mean_rating[c] for c in both]
            rho, r = spearman(x, y), pearson(x, y)
            res["system_vs_raters"] = {
                "n": len(both), "spearman": round(rho, 3), "spearman_ci95": [round(v, 3) for v in fisher_ci(rho, len(both))],
                "spearman_p": round(perm_p(x, y, spearman), 4), "pearson": round(r, 3),
                "pearson_ci95": [round(v, 3) for v in fisher_ci(r, len(both))],
            }
            if construct in THRESHOLDS:
                res["system_vs_raters"]["threshold"] = THRESHOLDS[construct]
                res["system_vs_raters"]["meets_threshold"] = (rho if construct == "confidence" else r) >= THRESHOLDS[construct]
        out[construct] = res
    return out


# ── 4. User study (Likert) ──────────────────────────────────────────────────

def wilcoxon(diffs: list[float]) -> tuple[float, float]:
    """Wilcoxon signed-rank test: (two-sided p, effect size r). Exact for n ≤ 20, else normal approx."""
    d = [x for x in diffs if x != 0]
    n = len(d)
    if n == 0:
        return 1.0, 0.0
    rk = ranks([abs(x) for x in d])
    w = sum(r for r, x in zip(rk, d) if x > 0)
    mean = n * (n + 1) / 4
    if n <= 20:
        dist = [sum(r for r, s in zip(rk, signs) if s) for signs in product((0, 1), repeat=n)]
        p = sum(1 for v in dist if abs(v - mean) >= abs(w - mean) - 1e-9) / len(dist)
    else:
        ties = {}
        for r in rk:
            ties[r] = ties.get(r, 0) + 1
        var = n * (n + 1) * (2 * n + 1) / 24 - sum(t ** 3 - t for t in ties.values()) / 48
        z = (w - mean) / math.sqrt(var)
        p = math.erfc(abs(z) / math.sqrt(2))
    z_eff = (w - mean) / math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    return min(1.0, p), z_eff / math.sqrt(n)


def likert(rows: list[dict]) -> dict:
    """rows: participant, condition, item, score. Per item: mean per condition (vs ≥ 4 target);
    with two conditions, a paired Wilcoxon test across participants."""
    out = {}
    for item in sorted({r["item"] for r in rows}):
        rs = [r for r in rows if r["item"] == item]
        conds = sorted({r["condition"] for r in rs})
        per = {c: {r["participant"]: float(r["score"]) for r in rs if r["condition"] == c} for c in conds}
        res = {c: {"n": len(v), "mean": round(statistics.mean(v.values()), 2),
                   "mean_ci95": [round(x, 2) for x in boot(list(v.values()), statistics.mean)],
                   "meets_target": statistics.mean(v.values()) >= LIKERT_TARGET} for c, v in per.items()}
        if len(conds) == 2:
            a, b = conds
            both = [p for p in per[a] if p in per[b]]
            p, r = wilcoxon([per[b][x] - per[a][x] for x in both])
            res[f"{b}_vs_{a}"] = {"paired_n": len(both), "wilcoxon_p": round(p, 4), "effect_size_r": round(r, 3)}
        out[item] = res
    return out


# ── Self-test: known answers on made-up data ────────────────────────────────

def selftest():
    a = asr({"1": "okay lah I try first", "2": "", "3": "saya rasa okay"},
            {"1": "ok la I try first", "2": "", "3": "saya rasa okay"}, {})
    assert a["all"]["raw"]["wer"] == 25.0 and a["all"]["spelling_normalised"]["wer"] == 0.0, a
    assert a["silent_clips_with_text"] == "0/1"
    assert spelling_norm("kenyanglah wei") == ["kenyang", "lah", "weh"]

    gold = [{"clip_id": "c1", "type": "filler", "t_sec": t} for t in (1.0, 5.0, 9.0)]
    sysr = [{"clip_id": "c1", "type": "filler", "t_sec": t} for t in (1.2, 5.9, 20.0)]
    e = events(gold, sysr, 0.5)["filler"]
    assert (e["precision"], e["recall"]) == (round(1 / 3, 3), round(1 / 3, 3)), e

    assert round(spearman([1, 2, 3, 4], [10, 20, 30, 40]), 9) == 1.0 and ranks([5, 5, 1]) == [2.5, 2.5, 1.0]
    perfect = [[1, 1], [2, 2], [3, 3], [4, 4]]
    assert icc2(perfect) == (1.0, 1.0)
    # Koo & Li style check: a constant +1 offset between raters lowers absolute agreement below 1
    assert icc2([[1, 2], [2, 3], [3, 4], [4, 5]])[0] < 1.0

    rng = random.Random(3)
    rows = []
    for clip in range(30):
        truth = rng.uniform(1, 7)
        for rater in ("A", "B", "C"):
            rows.append({"clip_id": str(clip), "rater": rater, "construct": "confidence", "score": round(truth + rng.gauss(0, 0.5))})
    system = [{"clip_id": str(c), "construct": "confidence",
               "score": statistics.mean(float(r["score"]) for r in rows if r["clip_id"] == str(c)) * 10 + rng.gauss(0, 3)}
              for c in range(30)]
    rr = ratings(rows, system)["confidence"]
    assert rr["icc_2_k"] > 0.8 and rr["system_vs_raters"]["spearman"] > 0.8 and rr["system_vs_raters"]["meets_threshold"], rr

    p, r = wilcoxon([1] * 10)
    assert p == 2 / 1024 and r > 0.8
    assert wilcoxon([1, -1] * 5)[0] == 1.0
    lk = likert([{"participant": str(i), "condition": c, "item": "actionable", "score": s}
                 for i in range(12) for c, s in (("generic", 3), ("grounded", 5 if i % 4 else 4))])
    assert lk["actionable"]["grounded"]["meets_target"] and lk["actionable"]["grounded_vs_generic"]["wilcoxon_p"] < 0.01
    print("study_stats selftest: all checks pass")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("asr"); s.add_argument("--refs", required=True); s.add_argument("--hyps", required=True)
    s.add_argument("--groups")
    s = sub.add_parser("events"); s.add_argument("--gold", required=True); s.add_argument("--system", required=True)
    s.add_argument("--tolerance", type=float, default=0.5)
    s = sub.add_parser("ratings"); s.add_argument("--ratings", required=True); s.add_argument("--system", required=True)
    s = sub.add_parser("likert"); s.add_argument("--responses", required=True)
    sub.add_parser("selftest")
    a = ap.parse_args()
    if a.cmd == "selftest":
        return selftest()
    if a.cmd == "asr":
        refs = json.loads(Path(a.refs).read_text(encoding="utf-8"))
        hyps = {r["clip_id"]: r["transcript"] for r in read_csv(a.hyps)}
        groups = {r["clip_id"]: r["group"] for r in read_csv(a.groups)} if a.groups else {}
        result = asr(refs, hyps, groups)
    elif a.cmd == "events":
        result = events(read_csv(a.gold), read_csv(a.system), a.tolerance)
    elif a.cmd == "ratings":
        result = ratings(read_csv(a.ratings), read_csv(a.system))
    else:
        result = likert(read_csv(a.responses))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
