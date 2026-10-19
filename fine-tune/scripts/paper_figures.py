"""Figures for the paper, drawn from the saved per-clip results (no models run).

    pip install matplotlib && python fine-tune/scripts/paper_figures.py
writes docs/figures/fig_asr_systems.{png,pdf} and docs/figures/fig_routing_paired.{png,pdf}.

Colours: categorical slots 1-4 of the validated dataviz palette, in fixed order (blue, orange,
aqua, yellow), checked with its validator on white. Two of them sit below 3:1 contrast on white,
so every bar carries its value as a label; hatching keeps the series apart in grayscale print.
"""

import csv
import random
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from paper_stats import edits, norm  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "fine-tune" / "eval" / "paper"
OUT = ROOT / "docs" / "figures"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
HATCH = ["", "//", "..", "xx"]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e2dc"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False})


def rows(name):
    with open(PAPER / name, newline="", encoding="utf-8") as f:
        return {r["clip_id"]: r for r in csv.DictReader(f)}


def wer_ci(pairs, draws=5000):
    """Corpus WER (%) and 95% bootstrap CI over clips. pairs: [(errors, ref_words)]."""
    wer = lambda ps: 100 * sum(e for e, _ in ps) / sum(n for _, n in ps)
    rng = random.Random(0)
    boots = sorted(wer([pairs[rng.randrange(len(pairs))] for _ in pairs]) for _ in range(draws))
    return wer(pairs), boots[int(0.025 * draws)], boots[int(0.975 * draws)]


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig_asr_systems():
    rt, ft, gq = rows("results.csv"), rows("finetune_results.csv"), rows("groq_results.csv")
    systems = [("Whisper large-v3 (local)", lambda c: rt[c]["routing_off"]),
               ("Malaysian Whisper (shipped)", lambda c: ft[c]["shipped"]),
               ("LoRA fine-tune (not deployed)", lambda c: ft[c]["ft"]),
               ("Groq whisper-large-v3 (deployed)", lambda c: gq[c]["hypothesis"])]
    groups = [("English\n(200, real speakers)", "english"), ("Manglish\n(200, synthetic voices)", "mixed")]
    fig, ax = plt.subplots(figsize=(3.5, 2.9))
    width = 0.19
    for s, (name, hyp) in enumerate(systems):
        xs, vals, lo, hi = [], [], [], []
        for g, (_, key) in enumerate(groups):
            ids = [c for c, r in rt.items() if r["group"] == key and c in gq]
            w, a, b = wer_ci([(edits(norm(rt[c]["reference"]), norm(hyp(c))), len(norm(rt[c]["reference"]))) for c in ids])
            xs.append(g + (s - 1.5) * (width + 0.02)); vals.append(w); lo.append(w - a); hi.append(b - w)
        ax.bar(xs, vals, width, color=SERIES[s], hatch=HATCH[s], edgecolor="white", linewidth=0.6, label=name, zorder=2)
        ax.errorbar(xs, vals, yerr=[lo, hi], fmt="none", ecolor=INK, elinewidth=0.7, capsize=1.5, zorder=3)
        for x, v, h in zip(xs, vals, hi):
            ax.text(x, v + h + 0.4, f"{v:.1f}", ha="center", va="bottom", fontsize=6, color=INK)
    ax.set_xticks(range(len(groups)), [g for g, _ in groups])
    ax.set_ylabel("Word error rate (%)")
    ax.yaxis.grid(True, color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_ylim(0, 20)
    ax.legend(frameon=False, fontsize=6, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, handlelength=1.6,
              columnspacing=1.0)
    save(fig, "fig_asr_systems")


def fig_routing_paired():
    rt = rows("results.csv")
    mixed = [r for r in rt.values() if r["group"] == "mixed"]
    pts = []
    for r in mixed:
        ref = norm(r["reference"])
        pts.append((100 * edits(ref, norm(r["routing_off"])) / len(ref), 100 * edits(ref, norm(r["routing_on"])) / len(ref)))
    worse = sum(1 for a, b in pts if b > a)
    fig, ax = plt.subplots(figsize=(3.5, 3.0))
    ax.plot([0, 100], [0, 100], color=MUTED, linewidth=0.8, linestyle="--", zorder=1)
    ax.scatter([a for a, _ in pts], [b for _, b in pts], s=12, color=SERIES[0], edgecolor="white", linewidth=0.5, zorder=2)
    ax.set_xlim(-2, 100); ax.set_ylim(-2, 100)
    ax.set_xlabel("WER per clip, Whisper alone (%)")
    ax.set_ylabel("WER per clip, routed to code-switch model (%)")
    ax.grid(True, color=GRID, linewidth=0.6, zorder=0)
    ax.text(55, 12, f"{worse} of {len(pts)} clips worse\nabove the dashed line", fontsize=7, color=INK)
    save(fig, "fig_routing_paired")


if __name__ == "__main__":
    fig_asr_systems()
    fig_routing_paired()
    print(f"wrote {OUT}/fig_asr_systems.png|pdf and fig_routing_paired.png|pdf")
