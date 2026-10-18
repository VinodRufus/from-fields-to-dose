"""Pull FDA labeling text (openFDA, same SPL corpus as DailyMed) for each candidate drug so the dosing
table can be filled with provenance. Usage: python -m sources.fetch_labels [--template sources/dosing_sources.template.csv] [--max 4]
Writes sources/labels/<drug>/<set_id>.txt and sources/labels/index.csv. You then READ the Dosage and Administration
and Pediatric Use sections and fill sources/dosing_sources.csv by hand. Nothing is auto-filled on purpose."""
from __future__ import annotations
import argparse, csv, json, os, sys, time, urllib.parse, urllib.request
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
API = "https://api.fda.gov/drug/label.json"
ROUTE_MAP = {"oral": "ORAL", "IV": "INTRAVENOUS", "IM": "INTRAMUSCULAR"}
FIELDS = ["indications_and_usage", "dosage_and_administration", "dosage_forms_and_strengths", "pediatric_use", "use_in_specific_populations", "boxed_warning"]

QUERY_OVERRIDES = {"amoxicillin-clavulanate": "amoxicillin and clavulanate potassium", "ibuprofen": 'ibuprofen" AND openfda.dosage_form:"SUSPENSION" AND openfda.product_type:"HUMAN PRESCRIPTION DRUG', "dexamethasone": 'dexamethasone" AND openfda.route:"ORAL" AND openfda.dosage_form:"SOLUTION', "azithromycin": 'azithromycin" AND openfda.dosage_form:"FOR SUSPENSION'}

def fetch(query: str, limit: int, key: str | None):
    q = f"{API}?search={urllib.parse.quote(query)}&limit={limit}" + (f"&api_key={key}" if key else "")
    req = urllib.request.Request(q, headers={"User-Agent": "fields-to-dose/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", default=os.path.join(ROOT, "sources", "dosing_sources.template.csv"))
    ap.add_argument("--max", type=int, default=4, help="labels to save per drug")
    ap.add_argument("--only", default=None, help="one drug name")
    a = ap.parse_args()
    key = os.environ.get("OPENFDA_API_KEY")
    rows = list(csv.DictReader(open(a.template, newline="")))
    seen = set(); out_dir = os.path.join(ROOT, "sources", "labels"); os.makedirs(out_dir, exist_ok=True)
    idx_path = os.path.join(out_dir, "index.csv"); new_index = not os.path.exists(idx_path)
    with open(idx_path, "a", newline="") as fi:
        w = csv.writer(fi)
        if new_index: w.writerow(["drug", "route", "set_id", "spl_version", "effective_time", "brand", "manufacturer", "file", "retrieved"])
        for r in rows:
            drug, route = r["drug"].strip(), r["route"].strip()
            if a.only and drug != a.only: continue
            if (drug, route) in seen: continue
            seen.add((drug, route))
            q = f'openfda.generic_name:"{QUERY_OVERRIDES.get(drug, drug)}"'
            if route in ROUTE_MAP: q += f' AND openfda.route:"{ROUTE_MAP[route]}"'
            try:
                res = fetch(q, a.max, key)
            except Exception as e:
                print(f"[{drug} {route}] FAILED: {e}  (try https://dailymed.nlm.nih.gov/dailymed/search.cfm?query={urllib.parse.quote(drug)} by hand)"); continue
            hits = res.get("results", [])
            print(f"[{drug} {route}] {len(hits)} label(s)")
            ddir = os.path.join(out_dir, drug.replace(" ", "_").replace("/", "-")); os.makedirs(ddir, exist_ok=True)
            for h in hits:
                of = h.get("openfda", {}); sid = h.get("set_id", "unknown"); eff = h.get("effective_time", ""); ver = h.get("version", "")
                brand = ";".join(of.get("brand_name", [])[:2]); manu = ";".join(of.get("manufacturer_name", [])[:1])
                fn = os.path.join(ddir, f"{sid}.txt")
                with open(fn, "w") as f:
                    f.write(f"DRUG: {drug}\nROUTE QUERY: {route}\nSET_ID: {sid}\nSPL VERSION: {ver}\nEFFECTIVE_TIME: {eff}\nBRAND: {brand}\nMANUFACTURER: {manu}\n")
                    f.write(f"DAILYMED: https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={sid}\nRETRIEVED: {time.strftime('%Y-%m-%d')}\n\n")
                    for fld in FIELDS:
                        v = h.get(fld)
                        if v: f.write(f"===== {fld.upper()} =====\n" + "\n".join(v) + "\n\n")
                w.writerow([drug, route, sid, ver, eff, brand, manu, os.path.relpath(fn, ROOT), time.strftime("%Y-%m-%d")])
            time.sleep(0.3)
    print(f"\nIndex: {os.path.relpath(idx_path, ROOT)}. Open each file, read DOSAGE_AND_ADMINISTRATION and PEDIATRIC_USE, fill sources/dosing_sources.csv.")

if __name__ == "__main__": main()
