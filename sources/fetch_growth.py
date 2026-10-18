"""Download growth reference LMS files: WHO weight-for-age 0-24 months (as wtageinf.csv) and CDC weight-for-age
2-20 years (as wtage.csv). CDC moved its data pages in 2024-25, so several URLs are tried; if all fail, the script
prints where to download by hand. Usage: python -m sources.fetch_growth"""
import csv, io, os, sys, urllib.request
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CANDIDATES = {
 "wtageinf.csv": [  # WHO 0-2 preferred (CDC-hosted WHO files), then CDC infant file as fallback
   "https://www.cdc.gov/growthcharts/data/who/WHOwtageinf.csv",
   "https://www.cdc.gov/growthcharts/who/data/WHOwtageinf.csv",
   "https://www.cdc.gov/growthcharts/data/zscore/wtageinf.csv",
 ],
 "wtage.csv": [
   "https://www.cdc.gov/growthcharts/data/zscore/wtage.csv",
   "https://www.cdc.gov/growthcharts/data/wtage.csv",
 ],
}
def ok_lms(text: str) -> bool:
    try:
        rows = list(csv.DictReader(io.StringIO(text)))
        return len(rows) > 10 and all(k in rows[0] for k in ("Sex", "Agemos", "L", "M", "S"))
    except Exception:
        return False
def main():
    for name, urls in CANDIDATES.items():
        dest = os.path.join(ROOT, "sources", name); got = False
        for u in urls:
            try:
                req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
                txt = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
                if ok_lms(txt):
                    open(dest, "w").write(txt); print(f"{name}: OK from {u}"); got = True; break
                print(f"{name}: {u} did not look like an LMS file")
            except Exception as e:
                print(f"{name}: {u} failed ({e})")
        if not got:
            print(f"\n{name}: DOWNLOAD BY HAND. Go to https://www.cdc.gov/growthcharts/ -> Data Files (Percentile Data Files with LMS Values)."
                  f" For wtageinf.csv use the WHO weight-for-age 0-2 years file (or CDC infant weight-for-age 0-36 months and record that as a deviation);"
                  f" for wtage.csv use CDC weight-for-age 2-20 years. Save as sources/{name} with columns Sex, Agemos, L, M, S.")
    print("\nRecord the source and download date of each file in protocol/DEVIATIONS.md (Section 6 of the protocol).")
if __name__ == "__main__": main()
