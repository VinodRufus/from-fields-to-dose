"""Validate sources/dosing_sources.csv against Protocol Sections 4-5 before building the test set."""
import csv, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
p = os.path.join(ROOT, "sources", "dosing_sources.csv")
if not os.path.exists(p): sys.exit("sources/dosing_sources.csv not found (copy the template and fill it)")
rows = list(csv.DictReader(open(p, newline="")))
probs = []; ver = [r for r in rows if r.get("verified", "").strip().lower() == "true"]
def f(x):
    try: return float(x)
    except Exception: return None
for r in ver:
    d = r["drug"]
    for col in ("dose_min", "dose_max", "age_min_days", "age_max_days"):
        if f(r.get(col, "")) is None: probs.append(f"{d}: {col} missing or not numeric")
    if f(r.get("dose_min")) and f(r.get("dose_max")) and f(r["dose_min"]) > f(r["dose_max"]): probs.append(f"{d}: dose_min > dose_max")
    if r["dose_basis"] not in ("mg/kg/dose", "mg/kg/day", "mcg/kg/dose", "mcg/kg/day"): probs.append(f"{d}: bad dose_basis {r['dose_basis']}")
    if not any(x.strip().isdigit() for x in r.get("frequency_per_day_options", "").split("|")): probs.append(f"{d}: frequency_per_day_options empty")
    for col in ("source_id", "source_version", "retrieval_date", "source_type"):
        if not r.get(col, "").strip(): probs.append(f"{d}: {col} missing (provenance is mandatory)")
    if r["route"] not in ("oral", "IV", "IM"): probs.append(f"{d}: route must be oral, IV or IM")
drugs = {r["drug"] for r in ver}
mcg = {r["drug"] for r in ver if r["dose_basis"].startswith("mcg")}
caps = {r["drug"] for r in ver if f(r.get("max_per_dose_mg")) or f(r.get("max_per_day_mg"))}
liq = {r["drug"] for r in ver if r["route"] == "oral" and f(r.get("concentration_mg_per_ml"))}
par = {r["drug"] for r in ver if r["route"] in ("IV", "IM")}
both = {d for d in drugs if {r["dose_basis"] for r in ver if r["drug"] == d} >= {"mg/kg/dose", "mg/kg/day"}}
print(f"verified rows={len(ver)} of {len(rows)}; drugs={len(drugs)}; mcg drugs={len(mcg)} (need 3); with caps={len(caps)} (need 5); oral liquids with concentration={len(liq)} (need 3); parenteral={len(par)} (need 4); both per-dose and per-day={len(both)} (need 2)")
if len(drugs) < 15: probs.append("fewer than 15 verified drugs")
if len(mcg) < 3: probs.append("fewer than 3 mcg-dosed drugs")
if len(caps) < 5: probs.append("fewer than 5 drugs with a labeled maximum")
if len(liq) < 3: probs.append("fewer than 3 oral liquids with concentration")
if len(par) < 4: probs.append("fewer than 4 parenteral drugs")
if len(both) < 2: print("WARNING: fewer than 2 drugs with both per-dose and per-day rows (accepted deviation, see protocol/DEVIATIONS.md)")
if probs:
    print("PROBLEMS:"); [print(" -", x) for x in probs]; sys.exit(1)
print("OK")
