"""Figure 3: the two workflows and the four scoring levels (schematic; no data).

Layout on a fixed grid in inches: the note on the left, centred between the two workflow rows; the model boxes in one
column; the calculator in the hybrid row; the locked scorer as a container on the right spanning both rows. All
connectors are horizontal or vertical with right-angle elbows and meet boxes at their centre lines. spec() returns
the boxes and connectors for the PowerPoint builder.

Usage: python tools/figures/make_fig_workflows.py [--out docs/figures/F2D_Figure_3_Workflows_and_Scoring]
"""
from __future__ import annotations
import argparse, os, sys, textwrap
sys.path.insert(0, os.path.dirname(__file__))
from common import plt, save, BLUE, ORANGE, GREEN, INK, INK2
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

PW, PH = 11.0, 6.0
LEVELS = [
    ("Level 1  Field accuracy", "eight required fields after unit normalisation, 1 percent tolerance"),
    ("Level 2  Complete regimen", "all required fields correct together"),
    ("Level 3  Dosing consistency", "observed mg/kg per dose and per day within 10 percent of the canonical regimen"),
    ("Level 4  Composite dose-consequence", "exposure more than 10 percent off, or no exposure computable; 20 percent sensitivity"),
]
LEVEL_FILLS = ["#dbe7f8", "#c6d9f3", "#a9c6ec", "#8fb5e5"]


def spec():
    """Boxes: id -> (x, y_top, w, h, title, body, fill, text_colour). Connectors: list of point lists (elbows), arrowhead at the end."""
    rowB_y, rowC_y, bh = 1.05, 3.55, 1.25          # top of each workflow row, box height
    note = (0.3, (rowB_y + rowC_y + bh) / 2 - 0.85, 2.0, 1.7)
    mB = (3.0, rowB_y, 2.6, bh); mC = (3.0, rowC_y, 2.6, bh); calc = (6.1, rowC_y, 1.9, bh)
    scorer = (8.45, 0.55, 2.3, 4.95)
    boxes = {
        "note": (*note, "Synthetic pediatric note", "one of 361; the prompt has no rule on the age of a weight and does not say whether a maximum carries into mg/kg", "#eef3fb", INK),
        "mB": (*mB, "Language model", "extracts all fields AND computes dose_per_admin_mg, mg/kg per dose and mg/kg per day", BLUE, "white"),
        "mC": (*mC, "Language model", "extracts the fields only; no arithmetic", ORANGE, "white"),
        "calc": (*calc, "Deterministic calculator", "reconstructs mg/kg per dose and per day from the extracted fields", GREEN, "white"),
    }
    cyB = rowB_y + bh / 2; cyC = rowC_y + bh / 2; note_cx_right = note[0] + note[2]; trunk_x = 2.65
    connectors = [
        [(note_cx_right, cyB + (cyC - cyB) / 2), (trunk_x, cyB + (cyC - cyB) / 2), (trunk_x, cyB), (mB[0], cyB)],
        [(trunk_x, cyB + (cyC - cyB) / 2), (trunk_x, cyC), (mC[0], cyC)],
        [(mB[0] + mB[2], cyB), (scorer[0], cyB)],
        [(mC[0] + mC[2], cyC), (calc[0], cyC)],
        [(calc[0] + calc[2], cyC), (scorer[0], cyC)],
    ]
    labels = {
        "B": (3.0, rowB_y - 0.12, "Workflow B: end-to-end"),
        "C": (3.0, rowC_y - 0.12, "Workflow C: hybrid"),
        "S": (8.45, scorer[1] - 0.12, "Locked scorer: four levels"),
        "obs": (3.0, PH - 0.85, "Observed exposure at Levels 3 and 4: Workflow B, the model's own reported mg/kg fields; Workflow C, the calculator's reconstruction."),
        "pe": (3.0, PH - 0.45, "Primary endpoint: Level 2 passed and not dose-consequential (304 non-abstention records). Abstention cases (57): appropriate abstention or an unsupported value."),
    }
    return boxes, connectors, scorer, labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/figures/F2D_Figure_3_Workflows_and_Scoring")
    a = ap.parse_args()
    boxes, connectors, scorer, labels = spec()
    fig = plt.figure(figsize=(PW, PH), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, PW); ax.set_ylim(PH, 0); ax.axis("off")
    for key, (x, y, w, h, title, body, fill, tc) in boxes.items():
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08", fc=fill, ec="#b9cbe8" if key == "note" else fill, lw=1.0))
        chars = int((w - 0.3) / 0.058)
        ax.text(x + w / 2, y + 0.22, title, ha="center", va="top", fontsize=9.2, fontweight="bold", color=tc)
        ax.text(x + w / 2, y + 0.52, "\n".join(textwrap.wrap(body, chars)), ha="center", va="top", fontsize=7.9, color=tc, linespacing=1.3)
    # scorer container
    sx, sy, sw, sh = scorer
    ax.add_patch(FancyBboxPatch((sx, sy), sw, sh, boxstyle="round,pad=0,rounding_size=0.08", fc="#f6f8fc", ec="#9fb8dc", lw=1.0))
    pad = 0.12; lh = (sh - pad * 5) / 4
    for i, ((t, d), fc) in enumerate(zip(LEVELS, LEVEL_FILLS)):
        ly = sy + pad + i * (lh + pad)
        ax.add_patch(FancyBboxPatch((sx + pad, ly), sw - 2 * pad, lh, boxstyle="round,pad=0,rounding_size=0.05", fc=fc, ec=fc))
        tl = textwrap.wrap(t, 30)
        ax.text(sx + pad + 0.1, ly + 0.17, "\n".join(tl), fontsize=8.2, fontweight="bold", color=INK, va="top", linespacing=1.2)
        ax.text(sx + pad + 0.1, ly + 0.46 + 0.17 * (len(tl) - 1), "\n".join(textwrap.wrap(d, int((sw - 2 * pad - 0.2) / 0.052))), fontsize=7.2, color=INK2, va="top", linespacing=1.25)
    for key, (x, y, text) in labels.items():
        if key in ("B", "C", "S"):
            ax.text(x, y, text, fontsize=9.6, fontweight="bold", color=INK, va="bottom")
        else:
            ax.text(x, y, "\n".join(textwrap.wrap(text, 92)), fontsize=7.6, color=INK2, va="top", style="italic" if key == "obs" else "normal")
    for path in connectors:
        for (x0, y0), (x1, y1) in zip(path[:-2], path[1:-1]):
            ax.plot([x0, x1], [y0, y1], color="#6b7280", lw=1.1, solid_capstyle="round")
        (x0, y0), (x1, y1) = path[-2], path[-1]
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=11, lw=1.1, color="#6b7280", shrinkA=0, shrinkB=0))
    save(fig, a.out)


if __name__ == "__main__":
    main()
