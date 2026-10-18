import csv, sys
P = "sources/dosing_sources.csv"
drug, kv = sys.argv[1], dict(a.split("=", 1) for a in sys.argv[2:])
rows = list(csv.DictReader(open(P, newline="")))
cols = rows[0].keys(); hit = [r for r in rows if r["drug"] == drug]
if not hit: sys.exit(f"no row for {drug}; drugs: {[r['drug'] for r in rows]}")
bad = [k for k in kv if k not in cols]
if bad: sys.exit(f"unknown columns {bad}; valid: {list(cols)}")
hit[0].update(kv)
with open(P, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
print("\n".join(f"  {k:28s}= {v}" for k, v in hit[0].items()))
