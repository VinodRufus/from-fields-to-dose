"""Figure 8: H4 and the error classes. Panel A: share of each cell's dose-consequential outputs carrying each
automatic class, Llama 3.1 8B Workflow B and Workflow C, with 95 percent clustered bootstrap intervals (the frontier
cells have at most five such outputs, all arithmetic inconsistency, and are listed in the caption). Classes are not
mutually exclusive. Panel B: manual coding of the 288 residual extraction errors, first pass. Panel C: re-code of the
28-record sample. Panel A is computed from the scored run-1 files with analysis/analyze.py's helpers (identical to
tools/h4_classes.py); Panels B and C are parsed from results/h4_classes.txt, which the author produced from the
manual coding files in the working repository.

Usage: python tools/figures/make_fig_classes.py [--h4 results/h4_classes.txt] [--out docs/figures/F2D_Figure_8_Error_Classes_and_Manual_Coding]
"""
from __future__ import annotations
import argparse, ast, collections, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.getcwd())
from common import plt, save, style, donut, load_cells, BLUE, ORANGE, GREEN, AMBER, RAMP5, INK, INK2
from analysis.analyze import by_scenario, cluster_boot_mean

H4 = ("dose_basis", "weight_selection", "extraction:weight_wrong")
NICE = {"arithmetic_inconsistency": "Arithmetic inconsistency", "frequency": "Frequency", "dose_basis": "Dose basis (per day vs per dose)",
        "extraction:dose_wrong": "Extraction: dose value wrong", "extraction:weight_wrong": "Extraction: weight value wrong",
        "adult_fixed_dose_assumption": "Weight-based order labelled fixed", "weight_selection": "Weight selection",
        "unit_scale": "Unit scale", "route": "Route", "weight_unit": "Weight unit", "dose_cap": "Dose cap", "strength_vs_dose": "Strength vs dose",
        "normalization:dose_basis": "Normalization: dose basis", "malformed_output": "Malformed output"}
CODES = ["E1", "E2", "E3", "E4", "E5", "E6"]
CODE_LABEL = {"E1": "E1 extraction (copied wrongly or omitted)", "E2": "E2 normalization", "E3": "E3 association", "E4": "E4 temporal", "E5": "E5 volume vs dose", "E6": "E6 other"}


def shares(rows):
    dq = [r for r in rows if r.get("dose_consequential")]
    counts = collections.Counter(c for r in dq for c in r.get("codes", []))
    out = []
    for cls, n in counts.most_common():
        flagged = [dict(r, _f=(cls in r.get("codes", []))) for r in dq]
        out.append((cls, n, cluster_boot_mean(by_scenario(flagged, "_f"))))
    h4 = [dict(r, _f=any(c in H4 for c in r.get("codes", []))) for r in dq]
    return len(dq), out, (sum(r["_f"] for r in h4), cluster_boot_mean(by_scenario(h4, "_f")))


def parse_manual(path):
    if not os.path.exists(path):
        raise SystemExit(f"STOP: {path} not found; run python -m tools.h4_classes --out {path} first")
    txt = open(path).read()
    m1 = re.search(r"First pass: (\d+) residual errors; codes (\{.*?\})", txt)
    m2 = re.search(r"Re-code: (\d+) records; agreement (\d+)/(\d+) = ([\d.]+); re-code distribution (\{.*?\})", txt)
    if not m1 or not m2:
        raise SystemExit(f"STOP: manual coding lines not found in {path}")
    first = ast.literal_eval(m1.group(2)); n_first = int(m1.group(1))
    rec = ast.literal_eval(m2.group(5)); n_rec, agree = int(m2.group(1)), int(m2.group(2))
    first = {k.split()[0].upper(): v for k, v in first.items()}
    rec = {k.split()[0].upper(): v for k, v in rec.items()}
    assert sum(first.values()) == n_first and sum(rec.values()) == n_rec
    return n_first, first, n_rec, rec, agree


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--h4", default="results/h4_classes.txt")
    ap.add_argument("--out", default="docs/figures/F2D_Figure_8_Error_Classes_and_Manual_Coding")
    a = ap.parse_args()
    cells = load_cells()
    fig = plt.figure(figsize=(13, 5.2), dpi=200)
    gs = fig.add_gridspec(1, 3, width_ratios=[2.2, 1, 1], wspace=0.35)
    ax = fig.add_subplot(gs[0, 0])
    rowsB = [r for r in cells[("llama3.1:8b", "B")] if not r.get("abstention_case")]
    rowsC = [r for r in cells[("llama3.1:8b", "C")] if not r.get("abstention_case")]
    nB, sB, h4B = shares(rowsB); nC, sC, h4C = shares(rowsC)
    classes = []
    for cls, _, _ in sB + sC:
        if cls not in classes:
            classes.append(cls)
    dB = {c: (n, ci) for c, n, ci in sB}; dC = {c: (n, ci) for c, n, ci in sC}
    ys = list(range(len(classes)))[::-1]
    h = 0.36
    for y, cls in zip(ys, classes):
        for off, d, color, wf in ((+h / 2, dB, BLUE, "B"), (-h / 2, dC, ORANGE, "C")):
            n, (e, lo, hi) = d.get(cls, (0, (0.0, 0.0, 0.0)))
            ax.barh(y + off, e, height=h - 0.03, color=color)
            if n:
                ax.errorbar([e], [y + off], xerr=[[e - lo], [hi - e]], fmt="none", ecolor=INK, elinewidth=0.8, capsize=2)
                ax.text(max(e, 0) + 0.012 + (hi - e), y + off, f"{n} ({e:.3f})", va="center", fontsize=7.3, color=INK)
    ax.set_yticks(ys); ax.set_yticklabels([NICE.get(c, c) for c in classes], fontsize=8.2)
    ax.set_xlim(0, 1.25); ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xlabel("Share of the cell's dose-consequential outputs carrying the class", fontsize=8.4, color=INK2)
    ax.set_title(f"A. Automatic error classes, Llama 3.1 8B (Workflow B: {nB} dose-consequential outputs; Workflow C: {nC})", fontsize=9.2, loc="left", color=INK)
    style(ax, grid_axis="x")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=BLUE, label=f"Workflow B; registered H4 classes together {h4B[0]} of {nB} ({h4B[1][0]:.3f} [{h4B[1][1]:.3f}, {h4B[1][2]:.3f}])"),
                       Patch(color=ORANGE, label=f"Workflow C; registered H4 classes together {h4C[0]} of {nC} ({h4C[1][0]:.3f})")],
              loc="upper center", bbox_to_anchor=(0.5, -0.12), frameon=False, fontsize=7.6)

    n_first, first, n_rec, rec, agree = parse_manual(a.h4)
    pal = [BLUE, AMBER, GREEN, "#8fb5e5", ORANGE, "#999999"]
    ax2 = fig.add_subplot(gs[0, 1])
    donut(ax2, [first.get(c, 0) for c in CODES], CODES, pal, title=f"B. Manual coding, first pass\n({n_first} residual extraction errors)", center_text=f"E1 {first.get('E1',0)/n_first:.3f}", fontsize=8)
    ax3 = fig.add_subplot(gs[0, 2])
    donut(ax3, [rec.get(c, 0) for c in CODES], CODES, pal, title=f"C. Re-code of {n_rec} sampled records\n(all E1 in the first pass)", center_text=f"agreement\n{agree} of {n_rec}\n({agree/n_rec:.3f})", fontsize=8)
    fig.legend(handles=[Patch(color=p, label=f"{CODE_LABEL[c]} (first pass {first.get(c, 0)}; re-code {rec.get(c, 0)})") for c, p in zip(CODES, pal)], loc="lower center", ncol=2, frameon=False, fontsize=7.8, bbox_to_anchor=(0.72, -0.12))
    save(fig, a.out)
    print("B", nB, sB, h4B); print("C", nC, sC, h4C); print("manual", n_first, first, n_rec, rec, agree)


if __name__ == "__main__":
    main()
