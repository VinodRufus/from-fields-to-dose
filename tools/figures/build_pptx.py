"""Editable PowerPoint versions of Figures 1 to 9, built from the same committed files and the same data functions as the
PNG/PDF scripts. Diagrams are native shapes and connectors; bar and donut charts are native PowerPoint charts with the
numbers in their embedded worksheets; the dot-and-interval plot is a native scatter chart with error bars; the heat
maps are native tables. Everything can be moved, recoloured or retyped in PowerPoint.

Usage: python tools/figures/build_pptx.py [--out docs/figures/F2D_Figures_Editable.pptx]
"""
from __future__ import annotations
import argparse, collections, copy, csv, os, sys, textwrap
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.getcwd())
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.chart.data import CategoryChartData, XyChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION, XL_MARKER_STYLE, XL_TICK_LABEL_POSITION
from pptx.oxml.ns import qn
from lxml import etree

from common import ORDER, SHORT, BANDS, BAND_LABEL, BLUE, ORANGE, GREEN, AMBER, RAMP5, RAMP3, CAT4, load_cells
from analysis.analyze import by_scenario, cluster_boot_mean
import make_fig1, make_fig_workflows, make_fig_testset, make_fig_h3, make_fig_abstention, make_fig_small_model, make_fig_classes

INK = RGBColor(0x22, 0x22, 0x22); INK2 = RGBColor(0x55, 0x55, 0x55); LINE = RGBColor(0x6b, 0x72, 0x80)
SW, SH = 13.333, 7.5


def rgb(h):
    h = h.lstrip("#"); return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def text(slide, x, y, w, h, s, size=10, bold=False, color=INK, align=PP_ALIGN.LEFT, italic=False, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.04); tf.margin_top = tf.margin_bottom = Inches(0.02); tf.vertical_anchor = anchor
    lines = s if isinstance(s, list) else [s]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run(); r.text = line; r.font.size = Pt(size); r.font.bold = bold; r.font.italic = italic; r.font.color.rgb = color; r.font.name = "Calibri"
    return tb


def box(slide, x, y, w, h, title, body, fill, tc=INK, edge=None, title_size=11, body_size=9, align=PP_ALIGN.LEFT):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.adjustments[0] = 0.06
    shp.fill.solid(); shp.fill.fore_color.rgb = rgb(fill)
    if edge:
        shp.line.color.rgb = rgb(edge); shp.line.width = Pt(0.75)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False; no_shadow(shp)
    tf = shp.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = tf.margin_right = Inches(0.14); tf.margin_top = Inches(0.1); tf.margin_bottom = Inches(0.08)
    p = tf.paragraphs[0]; p.alignment = align
    r = p.add_run(); r.text = title; r.font.size = Pt(title_size); r.font.bold = True; r.font.color.rgb = tc; r.font.name = "Calibri"
    if body:
        p2 = tf.add_paragraph(); p2.alignment = align; p2.space_before = Pt(4)
        r2 = p2.add_run(); r2.text = body; r2.font.size = Pt(body_size); r2.font.color.rgb = tc; r2.font.name = "Calibri"
    return shp


def no_shadow(shape):
    spPr = shape._element.spPr
    if spPr.find(qn("a:effectLst")) is None:
        etree.SubElement(spPr, qn("a:effectLst"))


def set_plot_layout(chart, x, y, w, h):
    """Manual plot-area layout as fractions of the chart frame, so donuts in a grid come out the same size."""
    pa = chart._chartSpace.chart.plotArea
    lay = pa.find(qn("c:layout"))
    if lay is None:
        lay = etree.Element(qn("c:layout")); pa.insert(0, lay)
    for ch in list(lay): lay.remove(ch)
    ml = etree.SubElement(lay, qn("c:manualLayout"))
    etree.SubElement(ml, qn("c:layoutTarget")).set("val", "inner")
    etree.SubElement(ml, qn("c:xMode")).set("val", "edge"); etree.SubElement(ml, qn("c:yMode")).set("val", "edge")
    for tag, v in (("c:x", x), ("c:y", y), ("c:w", w), ("c:h", h)):
        etree.SubElement(ml, qn(tag)).set("val", f"{v:.4f}")


def delete_point_label(point):
    dLbl = point.data_label._get_or_add_dLbl()
    for ch in list(dLbl):
        if ch.tag != qn("c:idx"): dLbl.remove(ch)
    etree.SubElement(dLbl, qn("c:delete")).set("val", "1")


def legend_shapes(slide, x, y, items, cols=1, col_w=3.0, row_h=0.24, size=8.5):
    for i, (label, color) in enumerate(items):
        r, c = divmod(i, cols)
        sq = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x + c * col_w), Inches(y + r * row_h + 0.05), Inches(0.16), Inches(0.12))
        sq.fill.solid(); sq.fill.fore_color.rgb = rgb(color); sq.line.fill.background(); no_shadow(sq)
        text(slide, x + c * col_w + 0.2, y + r * row_h - 0.02, col_w - 0.25, row_h + 0.05, label, size=size, color=INK2)


def connector(slide, x0, y0, x1, y1, arrow=False, color=LINE, width=1.0):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x0), Inches(y0), Inches(x1), Inches(y1))
    c.line.color.rgb = color; c.line.width = Pt(width)
    if arrow:
        ln = c.line._get_or_add_ln()
        tail = etree.SubElement(ln, qn("a:tailEnd")); tail.set("type", "triangle"); tail.set("w", "med"); tail.set("len", "med")
    return c


def path(slide, pts, color=LINE):
    for (x0, y0), (x1, y1) in zip(pts[:-2], pts[1:-1]):
        connector(slide, x0, y0, x1, y1, color=color)
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    connector(slide, x0, y0, x1, y1, arrow=True, color=color)


def slide_title(slide, s):
    text(slide, 0.3, 0.15, SW - 0.6, 0.4, s, size=13, bold=True)


def style_chart(chart, legend=True, legend_pos=XL_LEGEND_POSITION.BOTTOM, font=9):
    chart.font.size = Pt(font); chart.font.name = "Calibri"
    chart.has_legend = legend
    if legend:
        chart.legend.position = legend_pos; chart.legend.include_in_layout = False; chart.legend.font.size = Pt(font)


def add_error_bars(series, plus, minus, direction="y"):
    """Custom error bars on a chart series (not exposed by python-pptx; injected as XML before c:cat / c:xVal)."""
    ser = series._element
    eb = etree.SubElement(ser, qn("c:errBars"))
    if direction:
        etree.SubElement(eb, qn("c:errDir")).set("val", direction)
    etree.SubElement(eb, qn("c:errBarType")).set("val", "both")
    etree.SubElement(eb, qn("c:errValType")).set("val", "cust")
    etree.SubElement(eb, qn("c:noEndCap")).set("val", "0")
    for tag, vals in (("c:plus", plus), ("c:minus", minus)):
        el = etree.SubElement(eb, qn(tag)); lit = etree.SubElement(el, qn("c:numLit"))
        etree.SubElement(lit, qn("c:formatCode")).text = "General"
        etree.SubElement(lit, qn("c:ptCount")).set("val", str(len(vals)))
        for i, v in enumerate(vals):
            pt = etree.SubElement(lit, qn("c:pt")); pt.set("idx", str(i)); etree.SubElement(pt, qn("c:v")).text = f"{v:.6f}"
    sp = etree.SubElement(eb, qn("c:spPr")); ln = etree.SubElement(sp, qn("a:ln")); ln.set("w", "9525")
    sf = etree.SubElement(ln, qn("a:solidFill")); etree.SubElement(sf, qn("a:srgbClr")).set("val", "222222")
    # move before c:cat / c:xVal / c:val to respect schema order
    anchor = None
    for tag in ("c:cat", "c:xVal", "c:val", "c:yVal"):
        anchor = ser.find(qn(tag))
        if anchor is not None:
            break
    if anchor is not None:
        ser.remove(eb); anchor.addprevious(eb)


def color_series(series, hexcolor):
    series.format.fill.solid(); series.format.fill.fore_color.rgb = rgb(hexcolor)
    series.format.line.fill.background()


def donut_chart(slide, x, y, w, h, labels, values, colors, title=None, legend=False, hole=55, label_min_share=0.06, plot=(0.1, 0.14, 0.8, 0.82)):
    cd = CategoryChartData(); cd.categories = labels; cd.add_series("Records", values)
    gf = slide.shapes.add_chart(XL_CHART_TYPE.DOUGHNUT, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    ch = gf.chart; style_chart(ch, legend=legend, font=8)
    ch.has_title = bool(title)
    if title:
        ch.chart_title.text_frame.text = title
        ch.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(10); ch.chart_title.text_frame.paragraphs[0].runs[0].font.bold = False
    pl = ch.plots[0]
    hs = pl._element.find(qn("c:holeSize"))
    if hs is None:
        hs = etree.SubElement(pl._element, qn("c:holeSize"))
    hs.set("val", str(hole))
    set_plot_layout(ch, *plot)
    ser = pl.series[0]
    total = sum(values)
    for i, (v, c) in enumerate(zip(values, colors)):
        pt = ser.points[i]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb(c)
        pt.format.line.color.rgb = RGBColor(255, 255, 255); pt.format.line.width = Pt(1)
        if total and v / total >= label_min_share and v > 0:
            dl = pt.data_label; dl.has_text_frame = True; dl.text_frame.text = str(v)
            dl.text_frame.paragraphs[0].runs[0].font.size = Pt(8); dl.text_frame.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255) if v / total > 0.08 else INK
    return gf


def bar_chart(slide, x, y, w, h, categories, series, colors, kind=XL_CHART_TYPE.COLUMN_CLUSTERED, title=None, ymax=None, number_format='0.000', legend=True, labels=True, error=None, gap=60, overlap=None, font=8, axis_title=None, label_hide_below=10):
    cd = CategoryChartData(); cd.categories = categories
    for name, vals in series:
        cd.add_series(name, vals)
    gf = slide.shapes.add_chart(kind, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    ch = gf.chart; style_chart(ch, legend=legend, font=font)
    ch.has_title = bool(title)
    if title:
        ch.chart_title.text_frame.text = title
        r = ch.chart_title.text_frame.paragraphs[0].runs[0]; r.font.size = Pt(10); r.font.bold = False
    plot = ch.plots[0]; plot.gap_width = gap
    if overlap is not None:
        plot.overlap = overlap
    va = ch.value_axis; va.has_major_gridlines = True; va.major_gridlines.format.line.color.rgb = RGBColor(0xd9, 0xd9, 0xd9)
    va.format.line.fill.background(); va.tick_labels.font.size = Pt(font); va.tick_labels.number_format = '0.0' if (ymax or 0) <= 1.3 else '0'; va.tick_labels.number_format_is_linked = False
    if ymax is not None:
        va.maximum_scale = ymax; va.minimum_scale = 0
    if axis_title:
        va.has_title = True; va.axis_title.text_frame.text = axis_title; va.axis_title.text_frame.paragraphs[0].runs[0].font.size = Pt(font); va.axis_title.text_frame.paragraphs[0].runs[0].font.bold = False
    ca = ch.category_axis; ca.tick_labels.font.size = Pt(font); ca.format.line.color.rgb = RGBColor(0x99, 0x99, 0x99)
    for i, (s, c) in enumerate(zip(plot.series, colors)):
        color_series(s, c)
        vals = series[i][1]
        if labels:
            s.data_labels.show_value = True; s.data_labels.number_format = number_format; s.data_labels.number_format_is_linked = False
            s.data_labels.font.size = Pt(font - 1)
            clustered = kind in (XL_CHART_TYPE.COLUMN_CLUSTERED, XL_CHART_TYPE.BAR_CLUSTERED)
            s.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END if clustered else XL_LABEL_POSITION.CENTER
            if kind == XL_CHART_TYPE.COLUMN_CLUSTERED:
                # vertical labels: inside the bar for tall bars, above it for short ones
                txPr = s.data_labels._element.get_or_add_txPr(); txPr.find(qn("a:bodyPr")).set("rot", "-5400000"); txPr.find(qn("a:bodyPr")).set("vert", "horz")
                for k, v in enumerate(vals):
                    dl = s.points[k].data_label
                    dl.position = XL_LABEL_POSITION.INSIDE_END if v >= 0.3 else XL_LABEL_POSITION.OUTSIDE_END
                    dl.font.size = Pt(font - 1); dl.font.color.rgb = RGBColor(255, 255, 255) if v >= 0.3 else INK
            if not clustered:
                for k, v in enumerate(vals):
                    if v < label_hide_below:
                        delete_point_label(s.points[k])
            if kind == XL_CHART_TYPE.BAR_CLUSTERED:
                for k, v in enumerate(vals):
                    if v == 0:
                        delete_point_label(s.points[k])
                    elif v >= 0.15 and ymax is not None and ymax <= 1.3:
                        dl = s.points[k].data_label; dl.position = XL_LABEL_POSITION.INSIDE_BASE
                        dl.font.size = Pt(font - 1); dl.font.color.rgb = RGBColor(255, 255, 255)
        if error and error[i] is not None:
            add_error_bars(s, error[i][0], error[i][1], direction=None)
    return gf


# ---------------------------------------------------------------- figures

def fig1(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); slide_title(s, "Figure 1. Study flow (every count computed from committed files)")
    c = make_fig1.counts(); rows = make_fig1.flow_spec(c)
    X0, W, GAP, GUT, Y0 = 2.67, 8.0, 0.3, 0.3, 0.7
    heights = [0.72, 0.85, 0.9, 0.85, 0.72, 0.95]
    y = Y0; placed = []
    for row, h in zip(rows, heights):
        n = len(row); w = (W - GUT * (n - 1)) / n; r = []
        for i, (title, body, fill) in enumerate(row):
            x = X0 + i * (w + GUT)
            box(s, x, y, w, h, title, body, fill, edge="#8a94a6", title_size=11, body_size=9)
            r.append((x, y, w, h))
        placed.append(r); y += h + GAP
    for r in range(len(placed) - 1):
        top, bot = placed[r], placed[r + 1]
        yf = top[0][1] + top[0][3]; yt = bot[0][1]; ym = (yf + yt) / 2
        cxt = [b[0] + b[2] / 2 for b in top]; cxb = [b[0] + b[2] / 2 for b in bot]
        if len(top) == 1 and len(bot) == 1:
            connector(s, cxt[0], yf, cxb[0], yt, arrow=True)
        elif len(bot) == 2:
            connector(s, cxt[0], yf, cxt[0], ym); connector(s, cxb[0], ym, cxb[1], ym)
            for cx in cxb: connector(s, cx, ym, cx, yt, arrow=True)
        else:
            for cx in cxt: connector(s, cx, yf, cx, ym)
            connector(s, cxt[0], ym, cxt[1], ym); connector(s, cxb[0], ym, cxb[0], yt, arrow=True)


def fig2(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); slide_title(s, "Figure 2. Composition of the locked test set (361 records)")
    d = make_fig_testset.data(); band_n, lvl_n, basis_n, gen_n, drug_n, bands = d["band_n"], d["lvl_n"], d["basis_n"], d["gen_n"], d["drug_n"], d["bands"]
    l1 = ["Fully specified regimen", "Abstention case"]; v1 = [d["na"], d["ab"]]
    l2 = [f"{BAND_LABEL[b]}, {bands[b]['min_days']} to {bands[b]['max_days']} d" for b in BANDS]; v2 = [band_n[b] for b in BANDS]
    l3 = ["Level 1: bare order", "Level 2: history and plan", "Level 3: admission note"]; v3 = [lvl_n[k] for k in (1, 2, 3)]
    bk = ["mg/kg/day", "mg/kg/dose", "mcg/kg/day", "mcg/kg/dose"]; v4 = [basis_n[k] for k in bk]
    D = 2.3
    donut_chart(s, 0.3, 0.65, 3.2, D, l1, v1, [BLUE, ORANGE], title="A. Record type")
    legend_shapes(s, 0.6, 0.65 + D, [(f"{l} ({v})", c) for l, v, c in zip(l1, v1, [BLUE, ORANGE])], col_w=2.9, size=8)
    donut_chart(s, 3.6, 0.65, 3.2, D, l2, v2, RAMP5, title="B. Age band")
    legend_shapes(s, 3.8, 0.65 + D, [(f"{l} ({v})", c) for l, v, c in zip(l2, v2, RAMP5)], col_w=3.1, size=7.5, row_h=0.21)
    donut_chart(s, 0.3, 4.1, 3.2, D, l3, v3, RAMP3, title="C. Documentation complexity")
    legend_shapes(s, 0.6, 4.1 + D, [(f"{l} ({v})", c) for l, v, c in zip(l3, v3, RAMP3)], col_w=2.9, size=8)
    donut_chart(s, 3.6, 4.1, 3.2, D, bk, v4, CAT4, title="D. Dosing basis in the order")
    legend_shapes(s, 3.8, 4.1 + D, [(f"{l} ({v})", c) for l, v, c in zip(bk, v4, CAT4)], cols=2, col_w=1.55, size=8)
    drugs = sorted(drug_n.items(), key=lambda kv: kv[1])
    bar_chart(s, 7.1, 0.7, 6.0, 6.5, [k for k, _ in drugs], [("Records", [v for _, v in drugs])], [BLUE], kind=XL_CHART_TYPE.BAR_CLUSTERED,
              title=f"E. Records per medication ({len(drug_n)} represented of 21 sourced; {gen_n['template']} template, {gen_n['paraphrase']} paraphrased)", number_format='0', legend=False, gap=40, ymax=55)


def fig3(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); slide_title(s, "Figure 3. The two workflows and the four scoring levels")
    boxes, connectors, scorer, labels = make_fig_workflows.spec()
    ox, oy = 1.0, 0.7   # offset the 11 x 6 inch layout onto the slide
    for key, (x, y, w, h, title, body, fill, tc) in boxes.items():
        box(s, ox + x, oy + y, w, h, title, body, fill, tc=INK if key == "note" else RGBColor(255, 255, 255), edge="#b9cbe8" if key == "note" else None, title_size=11, body_size=9, align=PP_ALIGN.CENTER)
    sx, sy, sw, sh = scorer
    box(s, ox + sx, oy + sy, sw, sh, "", None, "#f6f8fc", edge="#9fb8dc")
    pad = 0.12; lh = (sh - pad * 5) / 4
    for i, ((t, dsc), fc) in enumerate(zip(make_fig_workflows.LEVELS, make_fig_workflows.LEVEL_FILLS)):
        box(s, ox + sx + pad, oy + sy + pad + i * (lh + pad), sw - 2 * pad, lh, t, dsc, fc, title_size=10, body_size=8.5)
    for key, (x, y, t) in labels.items():
        if key in ("B", "C", "S"):
            text(s, ox + x - 0.04, oy + y - 0.32, 4, 0.3, t, size=11, bold=True)
        else:
            yy = 6.3 if key == "obs" else 6.75
            text(s, ox + x - 0.04, yy, 7.2, 0.45, t, size=9, color=INK2, italic=(key == "obs"))
    for p in connectors:
        path(s, [(ox + x, oy + y) for x, y in p])


def fig4(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); slide_title(s, "Figure 4. Primary endpoint, composite failure and appropriate abstention by model and workflow (run 1; 95 percent clustered bootstrap intervals)")
    cells = load_cells()
    panels = [("A. Primary endpoint: complete dose-consistent regimen (304 records)", "primary_endpoint", False),
              ("B. Composite dose-consequence failure (304 records)", "dose_consequential", False),
              ("C. Appropriate abstention (57 abstention cases)", "appropriate_abstention", True)]
    for j, (title, key, abst) in enumerate(panels):
        series, err = [], []
        for wf in ("B", "C"):
            vals, plus, minus = [], [], []
            for m in ORDER:
                rows = [r for r in cells[(m, wf)] if bool(r.get("abstention_case")) == abst]
                e, lo, hi = cluster_boot_mean(by_scenario(rows, key)); vals.append(round(e, 4)); plus.append(hi - e); minus.append(e - lo)
            series.append((f"Workflow {wf} ({'end-to-end' if wf == 'B' else 'hybrid'})", vals)); err.append((plus, minus))
        bar_chart(s, 0.3 + j * 4.3, 0.75, 4.2, 6.1, [SHORT[m] for m in ORDER], series, [BLUE, ORANGE], title=title, ymax=1.2, error=err, gap=60, overlap=-10, legend=False)
    legend_shapes(s, 4.2, 6.95, [("Workflow B (end-to-end)", BLUE), ("Workflow C (hybrid)", ORANGE)], cols=2, col_w=2.4, size=9)


def fig5(prs):
    """Dot-and-interval plot drawn with native shapes: grid lines, interval lines, circle and square markers, text."""
    s = prs.slides.add_slide(prs.slide_layouts[6]); slide_title(s, "Figure 5. H3 under the two protocol wordings: paired Workflow C minus Workflow B differences per model")
    cells = load_cells(); lk = make_fig_h3.locked(cells); tr = make_fig_h3.text_rule("results/analysis_sensitivity_text_rule.txt")
    panels = [("A. Section 1 wording: composite failure rate (negative favours the hybrid workflow)", "S1", -1, "left"),
              ("B. Section 16 wording: primary endpoint (positive favours the hybrid workflow)", "S16", +1, "right")]
    XMIN, XMAX = -0.36, 0.36
    for j, (title, key, good, side) in enumerate(panels):
        px = 0.4 + j * 6.6                      # panel left
        text(s, px, 0.7, 6.3, 0.35, title, size=10, bold=True)
        lx, pw = px + 1.45, 4.6                # plot left and width (inches)
        top, rowh = 1.3, 0.95
        def X(v): return lx + (v - XMIN) / (XMAX - XMIN) * pw
        # grid, zero line, tick labels
        for v in (-0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3):
            c = connector(s, X(v), top - 0.1, X(v), top + rowh * len(ORDER) - 0.05, color=RGBColor(0x88, 0x88, 0x88) if v == 0 else RGBColor(0xd9, 0xd9, 0xd9), width=0.9 if v == 0 else 0.6)
            text(s, X(v) - 0.3, top + rowh * len(ORDER) - 0.02, 0.6, 0.25, f"{v:+.1f}" if v else "0", size=8, color=INK2, align=PP_ALIGN.CENTER)
        text(s, lx, top + rowh * len(ORDER) + 0.22, pw, 0.3, "Difference, Workflow C minus Workflow B", size=8.5, color=INK2, align=PP_ALIGN.CENTER)
        for i, m in enumerate(ORDER):
            cy = top + i * rowh + rowh / 2
            text(s, px, cy - 0.3, 1.4, 0.3, SHORT[m], size=9, bold=True, align=PP_ALIGN.RIGHT)
            e, lo, hi = lk[m][key]
            text(s, px, cy - 0.05, 1.4, 0.3, f"{e:+.3f} [{lo:+.3f}, {hi:+.3f}]", size=7.5, color=INK2, align=PP_ALIGN.RIGHT)
            for src, color, shape, dy in ((lk, BLUE, MSO_SHAPE.OVAL, -0.12), (tr, ORANGE, MSO_SHAPE.RECTANGLE, 0.14)):
                if src is None: continue
                e, lo, hi = src[m][key]; yy = cy + dy
                met = (hi < 0) if good < 0 else (lo > 0)
                clip = lambda v: max(XMIN, min(XMAX, v))
                connector(s, X(clip(lo)), yy, X(clip(hi)), yy, color=rgb(color), width=1.4)
                for v in (lo, hi):
                    if XMIN <= v <= XMAX: connector(s, X(v), yy - 0.05, X(v), yy + 0.05, color=rgb(color), width=1.2)
                if XMIN <= e <= XMAX:
                    d = 0.15 if shape == MSO_SHAPE.OVAL else 0.13
                    mk = s.shapes.add_shape(shape, Inches(X(e) - d / 2), Inches(yy - d / 2), Inches(d), Inches(d))
                    mk.fill.solid(); mk.fill.fore_color.rgb = rgb(color) if met else RGBColor(255, 255, 255)
                    mk.line.color.rgb = rgb(color); mk.line.width = Pt(1.25); no_shadow(mk)
                else:
                    text(s, X(XMAX) - 1.6 if e > XMAX else X(XMIN) + 0.05, yy - 0.12, 1.6, 0.25, f"{e:+.3f} [{lo:+.3f}, {hi:+.3f}] off scale", size=7, color=rgb(color), align=PP_ALIGN.RIGHT if e > XMAX else PP_ALIGN.LEFT)
    legend_shapes(s, 0.6, 6.75, [("Locked scorer (as registered by hash); circle", BLUE), ("Protocol's written Level 3 rule (sensitivity); square", ORANGE)], cols=2, col_w=4.3, size=8.5)
    text(s, 0.6, 7.02, 12.3, 0.35, "Filled marker: the interval excludes zero in the hypothesised direction. Hollow: the interval includes zero or opposes the hypothesis. Numbers under each model name are the locked-scorer estimate and interval.", size=8, color=INK2)


def fig6(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); slide_title(s, "Figure 6. Abstention outcomes on the 57 abstention cases, one donut per model and workflow (run 1)")
    cells = load_cells(); keys = ["Appropriate abstention", "Unsupported value supplied", "Other miss"]
    for i, wf in enumerate(("B", "C")):
        for j, m in enumerate(ORDER):
            ab = [r for r in cells[(m, wf)] if r.get("abstention_case")]
            c = collections.Counter(make_fig_abstention.cat(r) for r in ab)
            vals = [c["appropriate"], c["unsupported"], c["other"]]
            donut_chart(s, 0.2 + j * 2.6, 0.7 + i * 2.95, 2.55, 2.9, keys, vals, [GREEN, ORANGE, AMBER], title=f"{SHORT[m]}, Workflow {wf} ({c['appropriate'] / len(ab):.3f})", label_min_share=0.05, plot=(0.12, 0.16, 0.76, 0.8))
    legend_shapes(s, 0.4, 6.6, [("Appropriate abstention (null value, field named)", GREEN), ("Unsupported value supplied for the missing element", ORANGE), ("Other miss (none in any cell)", AMBER)], cols=3, col_w=4.2, size=8.5)
    text(s, 0.3, 6.95, 12.7, 0.4, "Every frontier cell: 52 appropriate, 5 unsupported values (the same five stale-weight notes). Llama 3.1 8B: 44 and 13 (B), 47 and 10 (C). No cell has an 'other miss'.", size=8.5, color=INK2)


def fig7(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); slide_title(s, "Figure 7. Llama 3.1 8B composite failures by workflow and scoring rule (components mutually exclusive)")
    d = make_fig_small_model.parse("results/analysis_sensitivity_text_rule.txt")
    cats = ["Workflow B, locked scorer", "Workflow B, written rule", "Workflow C, locked scorer", "Workflow C, written rule"]
    bars = [("B", "locked"), ("B", "text"), ("C", "locked"), ("C", "text")]
    series, colors = [], []
    for key, name, color in make_fig_small_model.COMPONENTS:
        vals = []
        for wf, rule in bars:
            v = d[wf]["comps"].get(key, 0)
            if key == "one_missing_other_within" and rule == "locked":
                v = 0
            vals.append(v)
        series.append((name, vals)); colors.append(color)
    bar_chart(s, 0.8, 0.75, 8.0, 6.4, cats, series, colors, kind=XL_CHART_TYPE.COLUMN_STACKED, number_format='0', ymax=320, gap=55, overlap=100, axis_title="Composite failures (304 non-abstention records)")
    text(s, 9.0, 1.0, 4.0, 3.5, [f"Totals: Workflow B {d['B']['locked']} of {d['B']['n']} (locked) and {d['B']['text']} (written rule); Workflow C {d['C']['locked']} under both rules.",
                                  "The written rule fails a record when one of the two mg/kg values is missing and the other is within tolerance; the locked scorer judges such a record on the value present.",
                                  "Source: results/analysis_sensitivity_text_rule.txt."], size=9, color=INK2)


def fig8(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); slide_title(s, "Figure 8. Automatic error classes (Llama 3.1 8B) and manual coding of the 288 residual extraction errors")
    cells = load_cells()
    rowsB = [r for r in cells[("llama3.1:8b", "B")] if not r.get("abstention_case")]; rowsC = [r for r in cells[("llama3.1:8b", "C")] if not r.get("abstention_case")]
    nB, sB, h4B = make_fig_classes.shares(rowsB); nC, sC, h4C = make_fig_classes.shares(rowsC)
    classes = []
    for cls, _, _ in sB + sC:
        if cls not in classes: classes.append(cls)
    dB = {c: (n, ci) for c, n, ci in sB}; dC = {c: (n, ci) for c, n, ci in sC}
    cats = [make_fig_classes.NICE.get(c, c) for c in classes][::-1]
    def col(d):
        vals, plus, minus = [], [], []
        for c in classes[::-1]:
            n, (e, lo, hi) = d.get(c, (0, (0.0, 0.0, 0.0))); vals.append(round(e, 4)); plus.append(hi - e); minus.append(e - lo)
        return vals, (plus, minus)
    vB, eB = col(dB); vC, eC = col(dC)
    bar_chart(s, 0.3, 0.75, 6.6, 6.2, cats, [(f"Workflow C ({nC} dose-consequential outputs)", vC), (f"Workflow B ({nB} dose-consequential outputs)", vB)], [ORANGE, BLUE], kind=XL_CHART_TYPE.BAR_CLUSTERED,
              title="A. Share of dose-consequential outputs carrying each class (95 percent clustered bootstrap intervals)", ymax=1.2, error=[eC, eB], gap=50, overlap=-10)
    n_first, first, n_rec, rec, agree = make_fig_classes.parse_manual("results/h4_classes.txt")
    pal = [BLUE, AMBER, GREEN, "#8fb5e5", ORANGE, "#999999"]
    labels = [make_fig_classes.CODE_LABEL[c] for c in make_fig_classes.CODES]
    donut_chart(s, 7.1, 0.75, 3.0, 3.0, labels, [first.get(c, 0) for c in make_fig_classes.CODES], pal, title=f"B. First pass ({n_first} errors)")
    donut_chart(s, 10.2, 0.75, 3.0, 3.0, labels, [rec.get(c, 0) for c in make_fig_classes.CODES], pal, title=f"C. Re-code ({n_rec} records; agreement {agree} of {n_rec})")
    legend_shapes(s, 7.3, 3.95, [(f"{labels[i]}: first pass {first.get(c, 0)}, re-code {rec.get(c, 0)}", pal[i]) for i, c in enumerate(make_fig_classes.CODES)], col_w=5.8, size=8.5)
    text(s, 7.2, 5.6, 5.9, 1.2, [f"Registered H4 classes together: Workflow B {h4B[0]} of {nB} ({h4B[1][0]:.3f} [{h4B[1][1]:.3f}, {h4B[1][2]:.3f}]); Workflow C {h4C[0]} of {nC}.", "Classes are not mutually exclusive. The frontier cells' 12 dose-consequential outputs all carry arithmetic inconsistency only."], size=9, color=INK2)


def fig9(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); slide_title(s, "Figure 9. Composite failure rate by stratum and model, Workflow B and Workflow C (challenge strata overlap)")
    rows = list(csv.DictReader(open("results/by_stratum_run1.csv")))
    KINDS = ["complexity", "age_band", "generation", "challenge"]
    strata = []
    for kind in KINDS:
        seen = []
        for r in rows:
            if r["stratum_kind"] == kind and r["stratum"] not in seen: seen.append(r["stratum"])
        if kind == "age_band": seen = [b for b in BANDS if b in seen]
        strata += [(kind, st) for st in seen]
    val = {(r["stratum_kind"], r["stratum"], r["model"], r["workflow"]): (float(r["composite_failure_rate"]), int(r["n"])) for r in rows}
    NICE = {"birth_weight": "birth weight present", "concentration_volume": "concentration and volume", "derive_per_dose": "per-dose amount withheld", "discontinued_same_drug": "discontinued order, same drug", "dose_cap": "maximum in the order", "lb_documentation": "weight in pounds", "mcg_drug": "microgram drug", "multiple_meds": "second medication", "multiple_weights": "prior-visit weight", "per_day_basis": "per-day basis", "weight_tail": "weight in the upper tail"}
    def lab(k, st):
        n = val[(k, st, ORDER[0], "B")][1]
        if k == "age_band": return f"{BAND_LABEL[st]} (n={n})"
        if k == "generation": return f"{'Paraphrased note' if st == 'paraphrase' else 'Template note'} (n={n})"
        return f"{NICE.get(st, st)} (n={n})"
    def shade(v):
        # light to dark blue
        stops = [(0, (0xf4, 0xf8, 0xfd)), (0.33, (0x9c, 0xc0, 0xee)), (0.66, (0x3b, 0x80, 0xd9)), (1.0, (0x0f, 0x3d, 0x7a))]
        for (a, ca), (b, cb) in zip(stops[:-1], stops[1:]):
            if v <= b:
                t = (v - a) / (b - a); return RGBColor(*[int(ca[i] + (cb[i] - ca[i]) * t) for i in range(3)])
        return RGBColor(*stops[-1][1])
    for j, wf in enumerate(("B", "C")):
        x0 = 0.3 + j * 6.6; w = 6.4; nrow = len(strata) + 1
        tbl = s.shapes.add_table(nrow, 6, Inches(x0), Inches(0.7), Inches(w), Inches(6.5)).table
        tbl.columns[0].width = Inches(2.3)
        for c in range(1, 6): tbl.columns[c].width = Inches((w - 2.3) / 5)
        hdr = [f"Workflow {wf}"] + [SHORT[m] for m in ORDER]
        for c, h in enumerate(hdr):
            cell = tbl.cell(0, c); cell.text = h; cell.fill.solid(); cell.fill.fore_color.rgb = RGBColor(0xee, 0xf1, 0xf6)
            p = cell.text_frame.paragraphs[0]; p.runs[0].font.size = Pt(8); p.runs[0].font.bold = True; p.runs[0].font.color.rgb = INK; p.alignment = PP_ALIGN.CENTER if c else PP_ALIGN.LEFT
        for i, (k, st) in enumerate(strata, start=1):
            cell = tbl.cell(i, 0); cell.text = lab(k, st); cell.fill.solid(); cell.fill.fore_color.rgb = RGBColor(255, 255, 255)
            p = cell.text_frame.paragraphs[0]; p.runs[0].font.size = Pt(7.5); p.runs[0].font.color.rgb = INK
            for c, m in enumerate(ORDER, start=1):
                v, n = val[(k, st, m, wf)]
                cell = tbl.cell(i, c); cell.text = f"{v:.3f}" if v > 0 else "0"; cell.fill.solid(); cell.fill.fore_color.rgb = shade(v)
                p = cell.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; p.runs[0].font.size = Pt(7.5); p.runs[0].font.color.rgb = RGBColor(255, 255, 255) if v > 0.55 else INK
        for i in range(nrow):
            tbl.rows[i].height = Inches(6.5 / nrow)
            for c in range(6):
                cell = tbl.cell(i, c); cell.margin_top = cell.margin_bottom = Inches(0.01); cell.margin_left = cell.margin_right = Inches(0.04); cell.vertical_anchor = MSO_ANCHOR.MIDDLE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/figures/F2D_Figures_Editable.pptx")
    a = ap.parse_args()
    prs = Presentation(); prs.slide_width = Inches(SW); prs.slide_height = Inches(SH)
    for f in (fig1, fig2, fig3, fig4, fig5, fig6, fig7, fig8, fig9):
        f(prs)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    prs.save(a.out); print("wrote", a.out)


if __name__ == "__main__":
    main()
