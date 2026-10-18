"""Fetch labels for one drug with a specific openFDA query (same output format as sources/fetch_labels)."""
import csv, json, os, sys, time, urllib.parse, urllib.request
API = "https://api.fda.gov/drug/label.json"
FIELDS = ["indications_and_usage", "dosage_and_administration", "dosage_forms_and_strengths", "pediatric_use", "use_in_specific_populations", "boxed_warning", "how_supplied", "description"]
QUERIES = {
 "ibuprofen": ['openfda.generic_name:"ibuprofen" AND dosage_and_administration:"mg/kg"',
               'openfda.generic_name:"ibuprofen" AND openfda.route:"ORAL" AND openfda.product_type:"HUMAN PRESCRIPTION DRUG"',
               'openfda.brand_name:"ibuprofen" AND description:"oral suspension" AND dosage_and_administration:"fever"'],
 "dexamethasone": ['openfda.generic_name:"dexamethasone" AND openfda.route:"ORAL" AND description:"oral solution"',
                   'openfda.generic_name:"dexamethasone" AND how_supplied:"0.5 mg per 5 mL"',
                   'openfda.generic_name:"dexamethasone" AND openfda.route:"ORAL" AND openfda.dosage_form:"SOLUTION"'],
 "azithromycin": ['openfda.generic_name:"azithromycin" AND openfda.dosage_form:"FOR SUSPENSION"',
                  'openfda.generic_name:"azithromycin" AND dosage_forms_and_strengths:"for oral suspension"',
                  'openfda.generic_name:"azithromycin" AND openfda.route:"ORAL" AND description:"for oral suspension"'],
}
drug = sys.argv[1]; limit = int(sys.argv[2]) if len(sys.argv) > 2 else 15
key = os.environ.get("OPENFDA_API_KEY")
ddir = os.path.join("sources", "labels", drug); os.makedirs(ddir, exist_ok=True)
for q in QUERIES[drug]:
    u = f"{API}?search={urllib.parse.quote(q)}&limit={limit}" + (f"&api_key={key}" if key else "")
    try:
        res = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "fields-to-dose/1.0"}), timeout=60).read())
    except Exception as e:
        print(f"  no hits for: {q}  ({e})"); continue
    hits = res.get("results", []); print(f"[{drug}] {len(hits)} label(s) for: {q}")
    with open(os.path.join("sources", "labels", "index.csv"), "a", newline="") as fi:
        w = csv.writer(fi)
        for h in hits:
            of = h.get("openfda", {}); sid = h.get("set_id", "unknown"); eff = h.get("effective_time", ""); ver = h.get("version", "")
            brand = ";".join(of.get("brand_name", [])[:2]); manu = ";".join(of.get("manufacturer_name", [])[:1])
            fn = os.path.join(ddir, f"{sid}.txt")
            with open(fn, "w") as f:
                f.write(f"DRUG: {drug}\nROUTE QUERY: {q}\nSET_ID: {sid}\nSPL VERSION: {ver}\nEFFECTIVE_TIME: {eff}\nBRAND: {brand}\nMANUFACTURER: {manu}\n")
                f.write(f"DAILYMED: https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={sid}\nRETRIEVED: {time.strftime('%Y-%m-%d')}\n\n")
                for fld in FIELDS:
                    v = h.get(fld)
                    if v: f.write(f"===== {fld.upper()} =====\n" + "\n".join(v) + "\n\n")
            w.writerow([drug, q, sid, ver, eff, brand, manu, fn, time.strftime("%Y-%m-%d")])
    break
else:
    print(f"[{drug}] every query returned nothing")
