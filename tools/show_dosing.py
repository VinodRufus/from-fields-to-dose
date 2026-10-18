import sys, os, re, glob, textwrap
drug = sys.argv[1]; pick = sys.argv[2] if len(sys.argv) > 2 else None
files = sorted(glob.glob(os.path.join("sources", "labels", drug, "*.txt")))
if not files: sys.exit(f"no labels for {drug}")
WANT = ("DOSAGE_AND_ADMINISTRATION", "DOSAGE_AND_ADMINISTRATION_TABLE", "DOSAGE_FORMS_AND_STRENGTHS", "PEDIATRIC_USE", "USE_IN_SPECIFIC_POPULATIONS", "HOW_SUPPLIED")
FORMS = ["for oral suspension", "oral suspension", "oral solution", "chewable", "tablet", "capsule", "injection", "for injection", "elixir", "drops"]
for i, f in enumerate(files, 1):
    txt = open(f, encoding="utf-8", errors="replace").read()
    hdr = dict(re.findall(r"^([A-Z_ ]+): (.*)$", txt.split("=====")[0], re.M))
    low = txt.lower()
    forms = [w for w in FORMS if w in low]
    conc = sorted(set(m.group(0) for m in re.finditer(r"\d+(?:\.\d+)?\s*(?:mg|mcg)\s*(?:per|/)\s*(?:\d+(?:\.\d+)?\s*)?mL", txt, re.I)))[:8]
    print(f"\n{'='*100}\n[{i}/{len(files)}] BRAND: {hdr.get('BRAND')} | MFR: {hdr.get('MANUFACTURER')}\n  SET_ID: {hdr.get('SET_ID')} | SPL v{hdr.get('SPL VERSION')} | eff {hdr.get('EFFECTIVE_TIME')}\n  FORMS: {', '.join(forms) or '?'}\n  CONC:  {', '.join(conc) or '-'}")
    if pick and pick != "all" and pick != str(i): continue
    secs = dict(re.findall(r"===== ([A-Z_&]+) =====\n(.*?)(?=\n===== |\Z)", txt, re.S))
    for name in WANT:
        if name in secs:
            print(f"\n--- {name} ---")
            print(textwrap.fill(secs[name].strip(), 110, initial_indent="  ", subsequent_indent="  "))
    if not any(n in secs for n in WANT):
        print("  sections present:", ", ".join(secs) or "none")
