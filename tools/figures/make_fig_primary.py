"""Figure 4: primary endpoint (A) and composite dose-consequence failure rate (B) by model and workflow, run 1,
304 non-abstention records per cell, with 95 percent clustered bootstrap intervals (2,000 resamples over scenarios,
analysis/analyze.py helpers). Panel C: appropriate abstention on the 57 abstention cases. Grouped bars, Workflow B
and Workflow C side by side.

Usage: python tools/figures/make_fig_primary.py [--out docs/figures/F2D_Figure_4_Primary_Endpoint_and_Composite]
"""
from __future__ import annotations
import argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.getcwd())
from common import plt, save, style, load_cells, ORDER, SHORT, BLUE, ORANGE, INK, INK2
from analysis.analyze import by_scenario, cluster_boot_mean


def est(rows, key):
    return cluster_boot_mean(by_scenario(rows, key))


def panel(ax, cells, key, title, ylabel, abst=False):
    w = 0.38
    for j, wf in enumerate(("B", "C")):
        xs, ys, lo, hi = [], [], [], []
        for i, m in enumerate(ORDER):
            rows = cells[(m, wf)]
            rows = [r for r in rows if r.get("abstention_case")] if abst else [r for r in rows if not r.get("abstention_case")]
            e, l, h = est(rows, key)
            xs.append(i + (j - 0.5) * w); ys.append(e); lo.append(e - l); hi.append(h - e)
        color = BLUE if wf == "B" else ORANGE
        ax.bar(xs, ys, width=w - 0.04, color=color, label=f"Workflow {wf} ({'end-to-end' if wf == 'B' else 'hybrid'})")
        ax.errorbar(xs, ys, yerr=[lo, hi], fmt="none", ecolor=INK, elinewidth=0.9, capsize=2.5)
        for x, y, hh in zip(xs, ys, hi):
            ax.text(x, min(y + hh + 0.02, 1.05), f"{y:.3f}", ha="center", va="bottom", fontsize=6.8, color=INK, rotation=90 if y > 0.7 else 0)
    ax.set_xticks(range(len(ORDER))); ax.set_xticklabels([SHORT[m].replace(" ", "\n", 1) for m in ORDER], fontsize=8)
    ax.set_xlim(-0.6, len(ORDER) - 0.4)
    ax.set_ylim(0, 1.2); ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_ylabel(ylabel, fontsize=8.6, color=INK2)
    ax.set_title(title, fontsize=9.6, loc="left", color=INK)
    style(ax)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/figures/F2D_Figure_4_Primary_Endpoint_and_Composite")
    a = ap.parse_args()
    cells = load_cells()
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4), dpi=200, gridspec_kw=dict(width_ratios=[1, 1, 1]))
    panel(axes[0], cells, "primary_endpoint", "A. Primary endpoint: complete dose-consistent regimen", "Proportion of 304 records")
    panel(axes[1], cells, "dose_consequential", "B. Composite dose-consequence failure", "Proportion of 304 records")
    panel(axes[2], cells, "appropriate_abstention", "C. Appropriate abstention (57 abstention cases)", "Proportion of 57 records", abst=True)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=2, frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, -0.03))
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    save(fig, a.out)
    for m in ORDER:
        for wf in ("B", "C"):
            na = [r for r in cells[(m, wf)] if not r.get("abstention_case")]
            print(m, wf, "primary", est(na, "primary_endpoint"), "composite", est(na, "dose_consequential"))


if __name__ == "__main__":
    main()
