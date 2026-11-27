"""Figure 6: abstention outcomes on the 57 abstention cases, one donut per model and workflow (run 1). Categories are
mutually exclusive by precedence: appropriate abstention; otherwise an unsupported value supplied for the missing
element (the scorer's hallucinated flag); otherwise other miss. Counts come from the scored run-1 files.

Usage: python tools/figures/make_fig_abstention.py [--out docs/figures/F2D_Figure_6_Abstention_Outcomes]
"""
from __future__ import annotations
import argparse, collections, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import plt, save, donut, load_cells, ORDER, SHORT, GREEN, ORANGE, AMBER, INK, INK2


def cat(r):
    if r.get("appropriate_abstention"):
        return "appropriate"
    if r.get("hallucinated"):
        return "unsupported"
    return "other"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/figures/F2D_Figure_6_Abstention_Outcomes")
    a = ap.parse_args()
    cells = load_cells()
    fig, axes = plt.subplots(2, 5, figsize=(12.5, 5.6), dpi=200)
    keys = ["appropriate", "unsupported", "other"]
    colors = [GREEN, ORANGE, AMBER]
    for i, wf in enumerate(("B", "C")):
        for j, m in enumerate(ORDER):
            ab = [r for r in cells[(m, wf)] if r.get("abstention_case")]
            c = collections.Counter(cat(r) for r in ab)
            n = len(ab)
            vals = [c[k] for k in keys]
            donut(axes[i, j], vals, keys, colors, title=f"{SHORT[m]}, Workflow {wf}" if i == 0 else f"{SHORT[m]}, Workflow {wf}",
                  center_text=f"{c['appropriate']/n:.3f}\nappropriate", fontsize=8)
            print(m, wf, dict(c), "n", n)
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=GREEN, label="Appropriate abstention (null value, field named)"),
                        Patch(color=ORANGE, label="Unsupported value supplied for the missing element"),
                        Patch(color=AMBER, label="Other miss (none in any cell)")],
               loc="lower center", ncol=3, frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Abstention cases (57 records): the five frontier misses are the same five stale-weight notes in every frontier cell", fontsize=10, x=0.01, ha="left", color=INK)
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    save(fig, a.out)


if __name__ == "__main__":
    main()
