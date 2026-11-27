"""Check that the 'locked' columns of results/analysis_sensitivity_text_rule.txt equal results/analysis_primary.txt.
Usage: python tools/check_locked_columns.py
Prints one line per model and workflow and ends with ALL MATCH or MISMATCH."""
import re, sys
prim, sens = {}, {}
for l in open("results/analysis_primary.txt"):
    m = re.match(r"(\S+)\s+wf=([BC])\s+primary=([\d.]+) \[([\d.]+),([\d.]+)\].*dose_consequential=([\d.]+) \[([\d.]+),([\d.]+)\]", l)
    if m: prim[(m.group(1), m.group(2))] = tuple(m.group(i) for i in (3, 4, 5, 6, 7, 8))
cur = None; block = 0
for l in open("results/analysis_sensitivity_text_rule.txt"):
    if l.startswith("== Level 3 rule sensitivity at primary tolerance"): block = 1
    elif l.startswith("== "): block = 0
    if not block: continue
    m = re.match(r"(\S+)\s+wf=([BC]) n=", l)
    if m: cur = (m.group(1), m.group(2)); sens.setdefault(cur, {}); continue
    m = re.search(r"primary endpoint\s+locked=([\d.]+) \[([\d.]+),([\d.]+)\]", l)
    if m and cur: sens[cur]["pe"] = m.groups(); continue
    m = re.search(r"dose-consequential locked=([\d.]+) \[([\d.]+),([\d.]+)\]", l)
    if m and cur: sens[cur]["dq"] = m.groups()
ok = True
for k in sorted(prim):
    s = sens.get(k)
    if not s or "pe" not in s or "dq" not in s:
        print(f"{k[0]:24s} wf={k[1]}  missing in sensitivity output"); ok = False; continue
    same = (s["pe"] + s["dq"]) == prim[k]
    ok &= same
    print(f"{k[0]:24s} wf={k[1]}  primary {prim[k][0]} [{prim[k][1]},{prim[k][2]}] vs {s['pe'][0]} [{s['pe'][1]},{s['pe'][2]}]   dose-consequential {prim[k][3]} [{prim[k][4]},{prim[k][5]}] vs {s['dq'][0]} [{s['dq'][1]},{s['dq'][2]}]   {'match' if same else 'MISMATCH'}")
print("ALL MATCH" if ok and len(sens) >= len(prim) else "MISMATCH")
sys.exit(0 if ok else 1)
