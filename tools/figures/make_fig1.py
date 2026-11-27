"""Figure 1: study flow from locked synthetic records to scored outputs, with every count computed from committed files.

Counts: data/test/scenarios.jsonl, data/test/records.jsonl, data/test/repeat_subset.txt, data/test/LOCK.json,
sources/dosing_sources.csv (labels sourced) and results/scored_test_*.jsonl. No number is typed in.

Layout: one column, boxes of equal width on a fixed grid, straight vertical connectors at box centres, and an elbow
split and merge around the two record-type boxes. flow_spec() returns the same content for the PowerPoint builder.

Usage: python tools/figures/make_fig1.py [--out docs/figures/F2D_Figure_1_Study_Flow]
"""
from __future__ import annotations
import argparse, csv, glob, json, os, sys, textwrap
sys.path.insert(0, os.path.dirname(__file__))
from common import plt, save, INK, INK2
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


def counts():
    S = [json.loads(l) for l in open("data/test/scenarios.jsonl")]
    R = [json.loads(l) for l in open("data/test/records.jsonl")]
    lock = json.load(open("data/test/LOCK.json"))
    repeat = {l.strip() for l in open("data/test/repeat_subset.txt") if l.strip()}
    drugs_sourced = len({row["drug"] for row in csv.DictReader(open("sources/dosing_sources.csv"))})
    drugs_in_set = len({s["drug"] for s in S})
    na = sum(1 for r in R if not r["abstention_case"]); ab = len(R) - na
    para = sum(1 for r in R if r["generation_method"].startswith("paraphrase"))
    runs = {}
    for f in sorted(glob.glob("results/scored_test_*.jsonl")):
        L = [json.loads(l) for l in open(f)]
        cfg = L[0]["_config"]; recs = [x for x in L[1:] if "record_id" in x]
        runs.setdefault(cfg.get("run_id"), []).append((cfg["model"]["id"], cfg["workflow"], len(recs), sum(1 for x in recs if not x.get("abstention_case")), sum(1 for x in recs if x.get("malformed"))))
    models = sorted({m for v in runs.values() for m, *_ in v}); wfs = sorted({w for v in runs.values() for _, w, *_ in v})
    r1 = runs["run1"]; rep = [x for k, v in runs.items() if k != "run1" for x in v]
    return dict(
        drugs_sourced=drugs_sourced, drugs_in_set=drugs_in_set, n=len(R), na=na, ab=ab, para=para,
        locked_at=lock["locked_at"][:10], n_models=len(models), n_wf=len(wfs), cells=len(r1),
        run1_outputs=sum(x[2] for x in r1), run1_na=sum(x[3] for x in r1), run1_mal=sum(x[4] for x in r1),
        repeat_n=len(repeat), repeat_runs=len(runs) - 1, repeat_files=len(rep), repeat_outputs=sum(x[2] for x in rep), repeat_na=sum(x[3] for x in rep), repeat_mal=sum(x[4] for x in rep),
    )


GREY, BLUEF, ORANGEF, GREENF = "#f3f5f8", "#e8f0fb", "#fbf0e8", "#eef7f1"


def flow_spec(c):
    """Rows of the flow; each row is a list of one or two (title, body, face) nodes."""
    return [
        [("Dosing sources", f"{c['drugs_sourced']} medications from current FDA labeling, one label each, verified by the author; {c['drugs_in_set']} represented in the locked set", GREY)],
        [("Synthetic test set, generated and audited", f"{c['n']} scenarios, one record each; {c['para']} notes paraphrased by a local model and audited; blinded self-audit; locked {c['locked_at']} with SHA-256 digests of the data and scoring files", GREY)],
        [(f"{c['na']} non-abstention records", "Fully specified regimen; scored at four levels; enter the primary endpoint", BLUEF),
         (f"{c['ab']} abstention records", "A required element absent or conflicting; scored for appropriate abstention", ORANGEF)],
        [(f"{c['n_models']} models x {c['n_wf']} workflows = {c['cells']} cells, run 1 (4 to 6 October 2026, UTC)", f"{c['run1_outputs']:,} outputs scored ({c['run1_na']:,} non-abstention, {c['run1_mal']} malformed); Workflow B end-to-end, Workflow C hybrid with a deterministic calculator", GREY)],
        [(f"Repeat subset: {c['repeat_n']} records x {c['cells']} cells x {c['repeat_runs']} further runs", f"{c['repeat_outputs']:,} outputs ({c['repeat_na']:,} non-abstention, {c['repeat_mal']} malformed, counted as a failure); run-to-run stability", GREY)],
        [("Analysis", "Primary endpoint: complete dose-consistent regimen accuracy, clustered bootstrap by scenario; paired C minus B; pre-registered H1 to H5; Level 3 rule sensitivity (locked scorer against protocol text); manual coding of residual errors", GREENF)],
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/figures/F2D_Figure_1_Study_Flow")
    a = ap.parse_args()
    c = counts(); rows = flow_spec(c)
    # Geometry in inches: page 7.2 wide; column from X0 to X0+W; equal gaps; heights from wrapped line counts.
    PW, X0, W, GAP, PAD, GUT = 7.2, 0.35, 6.5, 0.42, 0.14, 0.3
    TITLE_H, LINE_H, BODY_FS = 0.26, 0.17, 8.2
    def wrap(text, width_in):
        return textwrap.wrap(text, max(20, int((width_in - 2 * PAD) / 0.0585)))
    layout = []  # (x, y_top, w, h, title, body_lines, face)
    y = 0.0
    for row in rows:
        n = len(row); w = (W - GUT * (n - 1)) / n
        items = []
        hmax = 0
        for title, body, face in row:
            lines = wrap(body, w)
            h = PAD + TITLE_H + len(lines) * LINE_H + PAD
            items.append((title, lines, face, w)); hmax = max(hmax, h)
        for i, (title, lines, face, w) in enumerate(items):
            layout.append((X0 + i * (w + GUT), y, w, hmax, title, lines, face))
        y += hmax + GAP
    total_h = y - GAP + 0.3
    fig = plt.figure(figsize=(PW, total_h), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, PW); ax.set_ylim(total_h, 0); ax.axis("off")  # y grows downward
    for x, yt, w, h, title, lines, face in layout:
        ax.add_patch(FancyBboxPatch((x, yt + 0.15), w, h, boxstyle="round,pad=0,rounding_size=0.08", lw=1.0, ec="#8a94a6", fc=face))
        ax.text(x + PAD, yt + 0.15 + PAD + 0.02, title, fontsize=9.6, fontweight="bold", color=INK, va="top", ha="left")
        ax.text(x + PAD, yt + 0.15 + PAD + TITLE_H, "\n".join(lines), fontsize=BODY_FS, color=INK2, va="top", ha="left", linespacing=1.32)
    # connectors
    def arrow(x0, y0, x1, y1):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=11, lw=1.0, color="#6b7280", shrinkA=0, shrinkB=0))
    def line(x0, y0, x1, y1):
        ax.plot([x0, x1], [y0, y1], color="#6b7280", lw=1.0, solid_capstyle="round")
    rows_boxes = []
    i = 0
    for row in rows:
        rows_boxes.append(layout[i:i + len(row)]); i += len(row)
    for r in range(len(rows_boxes) - 1):
        top, bot = rows_boxes[r], rows_boxes[r + 1]
        y_from = top[0][1] + 0.15 + top[0][3]; y_to = bot[0][1] + 0.15; ymid = (y_from + y_to) / 2
        cx_top = [b[0] + b[2] / 2 for b in top]; cx_bot = [b[0] + b[2] / 2 for b in bot]
        if len(top) == 1 and len(bot) == 1:
            arrow(cx_top[0], y_from, cx_bot[0], y_to)
        elif len(top) == 1 and len(bot) == 2:
            line(cx_top[0], y_from, cx_top[0], ymid); line(cx_bot[0], ymid, cx_bot[1], ymid)
            for cx in cx_bot: arrow(cx, ymid, cx, y_to)
        else:
            for cx in cx_top: line(cx, y_from, cx, ymid)
            line(cx_top[0], ymid, cx_top[1], ymid); arrow(cx_bot[0], ymid, cx_bot[0], y_to)
    save(fig, a.out)
    print({k: c[k] for k in ("drugs_sourced", "drugs_in_set", "n", "na", "ab", "para", "run1_outputs", "run1_na", "repeat_outputs", "repeat_mal")})


if __name__ == "__main__":
    main()
