"""Figure 7: composite failure for Llama 3.1 8B by workflow, under the locked scorer and the protocol-text rule.

Reads the mutually exclusive exposure components from results/analysis_sensitivity_text_rule.txt (primary tolerance
block) and draws four stacked bars: Workflow B locked, Workflow B text rule, Workflow C locked, Workflow C text rule.
Every number is parsed from the committed report; nothing is typed in.

Usage: python tools/figures/make_fig5.py [--report results/analysis_sensitivity_text_rule.txt] [--out docs/figures/F2D_Figure_7_Small_Model_Failure_Both_Rules]
Writes <out>.png, <out>.pdf and <out>.svg (the SVG is editable in Inkscape, Illustrator or PowerPoint).
"""
from __future__ import annotations
import argparse, re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["svg.fonttype"] = "none"

MODEL = "llama3.1:8b"
# Fixed categorical order and hues (validated: lightness, chroma, CVD and normal-vision separation pass).
COMPONENTS = [
    ("both_present_off", "Both exposures reported, off by more than 10 percent", "#2a78d6"),
    ("one_missing_other_off", "One exposure missing, the other off", "#eb6834"),
    ("both_missing", "Neither exposure reported or computable", "#1baf7a"),
    ("one_missing_other_within", "One exposure missing, the other within tolerance (fails the written rule only)", "#eda100"),
]


def parse(report: str):
    text = open(report).read()
    block = text.split("== Level 3 rule sensitivity at primary tolerance")[1].split("== H3")[0]
    out = {}
    for wf in ("B", "C"):
        m = re.search(re.escape(MODEL) + r"\s+wf=" + wf + r" n=(\d+)\n(.*?)(?=\n\S|\Z)", block, flags=re.S)
        if not m:
            raise SystemExit(f"STOP: no block for {MODEL} wf={wf} in {report}")
        n = int(m.group(1)); body = m.group(2)
        comps = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", re.search(r"exposure components \(mutually exclusive\): (.*)", body).group(1))}
        locked = int(re.search(r"composite failures: locked = .* = (\d+); text", body).group(1))
        textf = int(re.search(r"text = locked \+ one_missing_other_within = (\d+)", body).group(1))
        out[wf] = {"n": n, "comps": comps, "locked": locked, "text": textf}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default="results/analysis_sensitivity_text_rule.txt")
    ap.add_argument("--out", default="docs/figures/F2D_Figure_7_Small_Model_Failure_Both_Rules")
    a = ap.parse_args()
    d = parse(a.report)
    for wf in ("B", "C"):
        c = d[wf]["comps"]
        assert c["both_present_off"] + c["one_missing_other_off"] + c["both_missing"] + c["malformed"] == d[wf]["locked"]
        assert d[wf]["locked"] + c["one_missing_other_within"] == d[wf]["text"]

    bars = [("B", "locked"), ("B", "text"), ("C", "locked"), ("C", "text")]
    labels = ["Workflow B\nlocked scorer", "Workflow B\nwritten rule", "Workflow C\nlocked scorer", "Workflow C\nwritten rule"]
    fig, ax = plt.subplots(figsize=(7.2, 4.6), dpi=200)
    x = range(len(bars))
    bottoms = [0] * len(bars)
    for key, name, color in COMPONENTS:
        vals = []
        for wf, rule in bars:
            v = d[wf]["comps"].get(key, 0)
            if key == "one_missing_other_within" and rule == "locked":
                v = 0
            vals.append(v)
        ax.bar(x, vals, bottom=bottoms, color=color, width=0.62, edgecolor="white", linewidth=1.5, label=name)
        for xi, (v, b) in enumerate(zip(vals, bottoms)):
            if v >= 12:
                ax.text(xi, b + v / 2, str(v), ha="center", va="center", fontsize=9, color="white")
        bottoms = [b + v for b, v in zip(bottoms, vals)]
    for xi, (wf, rule) in enumerate(bars):
        total = d[wf][rule]; n = d[wf]["n"]
        ax.text(xi, total + 4, f"{total} of {n}", ha="center", va="bottom", fontsize=9.5, color="#222222")
    ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Composite failures (run 1, non-abstention records)", fontsize=9.5)
    ax.set_ylim(0, 304 * 1.08)
    ax.axhline(304, color="#999999", linewidth=0.8, linestyle=(0, (3, 3)))
    ax.text(len(bars) - 0.6, 304 + 4, "304 records", fontsize=8.5, color="#666666", ha="right", va="bottom")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#999999"); ax.spines["bottom"].set_color("#999999")
    ax.tick_params(colors="#333333", labelsize=9)
    ax.set_title("Llama 3.1 8B: composite dose-consequence failures by workflow and scoring rule", fontsize=10.5, loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=1, frameon=False, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(a.out + ".png", bbox_inches="tight")
    fig.savefig(a.out + ".pdf", bbox_inches="tight")
    fig.savefig(a.out + ".svg", bbox_inches="tight")
    svg = open(a.out + ".svg").read().replace("font-family: 'DejaVu Sans'", "font-family: 'DejaVu Sans', Arial, Helvetica, sans-serif")
    open(a.out + ".svg", "w").write(svg)
    print(f"wrote {a.out}.png and .pdf from {a.report}: B locked {d['B']['locked']}, B text {d['B']['text']}, C locked {d['C']['locked']}, C text {d['C']['text']}")


if __name__ == "__main__":
    main()
