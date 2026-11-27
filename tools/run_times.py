"""Run times for Table 2 from the committed raw output files.

For every results/raw_test_*.jsonl file: number of attempts, first and last call timestamp, wall-clock span, sum of
per-call latency, median and 95th percentile latency, and records with more than one attempt. Token counts are not
stored in the raw files and come from the provider dashboards.

Timestamps. The harness writes time.strftime("%Y-%m-%dT%H:%M:%S") with no zone, that is the machine's local time.
The runs were made in America/Chicago while daylight time was in force (UTC minus 5 throughout 3 to 6 October 2026),
so UTC is local plus five hours; both are printed, and the paper reports UTC (ISO 8601 dates).

Usage: python -m tools.run_times > results/run_times.md
"""
from __future__ import annotations
import glob, json, os, statistics
from collections import defaultdict
from datetime import datetime, timedelta

LOCAL_TO_UTC = timedelta(hours=5)   # America/Chicago, daylight time (CDT), in force for every run


def utc(d):
    return (d + LOCAL_TO_UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if d else ""

ORDER = ["gpt-5.5-2026-04-23", "claude-sonnet-5", "gemini-3.1-pro-preview", "deepseek-v4-pro", "llama3.1:8b"]


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def fmt_span(seconds):
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m:02d}m {s:02d}s"


def main():
    rows = []
    for f in sorted(glob.glob("results/raw_test_*.jsonl")):
        L = [json.loads(l) for l in open(f)]
        cfg = L[0]["_config"]; calls = [x for x in L[1:] if "record_id" in x]
        lat = [x["latency_s"] for x in calls if isinstance(x.get("latency_s"), (int, float))]
        ts = [parse_ts(x.get("ts")) for x in calls if x.get("ts")]
        per_rec = defaultdict(int)
        for x in calls:
            per_rec[x["record_id"]] += 1
        rows.append(dict(
            model=cfg["model"]["id"], wf=cfg["workflow"], run=cfg.get("run_id"), file=os.path.basename(f),
            attempts=len(calls), records=len(per_rec), multi=sum(1 for v in per_rec.values() if v > 1),
            first=min(ts) if ts else None, last=max(ts) if ts else None,
            span=(max(ts) - min(ts)).total_seconds() if ts else None,
            lat_sum=sum(lat), lat_med=statistics.median(lat) if lat else None,
            lat_p95=sorted(lat)[int(0.95 * (len(lat) - 1))] if lat else None,
        ))
    rows.sort(key=lambda r: (ORDER.index(r["model"]) if r["model"] in ORDER else 99, r["wf"], r["run"]))
    print("## Run times from the committed raw files (results/raw_test_*.jsonl)\n")
    print("Wall-clock span is last call minus first call in the file (runs were sometimes interleaved or resumed, so spans can overlap across files); latency sum is the total of per-call latencies; p95 is the 95th percentile per-call latency.\n")
    print("Timestamps in the raw files are machine local time (America/Chicago, daylight time, UTC minus 5 for every run); the UTC columns add five hours.\n")
    print("| Model | Workflow | Run | Attempts | Records | Records with retries | First call (local) | Last call (local) | First call (UTC) | Last call (UTC) | Wall-clock span | Latency sum | Median latency, s | p95 latency, s |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['model']} | {r['wf']} | {r['run']} | {r['attempts']} | {r['records']} | {r['multi']} | {r['first'].isoformat(timespec='seconds') if r['first'] else ''} | {r['last'].isoformat(timespec='seconds') if r['last'] else ''} | {utc(r['first'])} | {utc(r['last'])} | {fmt_span(r['span']) if r['span'] is not None else ''} | {fmt_span(r['lat_sum'])} | {r['lat_med']:.1f} | {r['lat_p95']:.1f} |")
    print("\n## Per model, all files\n")
    print("| Model | Attempts | Latency sum | Median latency, s | First call (local) | Last call (local) | First call (UTC) | Last call (UTC) |")
    print("|---|---|---|---|---|---|---|---|")
    for m in ORDER:
        rr = [r for r in rows if r["model"] == m]
        if not rr:
            continue
        lats = []
        for f in [r["file"] for r in rr]:
            L = [json.loads(l) for l in open(os.path.join("results", f))][1:]
            lats += [x["latency_s"] for x in L if isinstance(x.get("latency_s"), (int, float))]
        print(f"| {m} | {sum(r['attempts'] for r in rr)} | {fmt_span(sum(lats))} | {statistics.median(lats):.1f} | {min(r['first'] for r in rr).isoformat(timespec='seconds')} | {max(r['last'] for r in rr).isoformat(timespec='seconds')} | {utc(min(r['first'] for r in rr))} | {utc(max(r['last'] for r in rr))} |")
    allfirst = min(r['first'] for r in rows); alllast = max(r['last'] for r in rows)
    print(f"\nAll test runs: first call {allfirst.isoformat(timespec='seconds')} local ({utc(allfirst)}), last call {alllast.isoformat(timespec='seconds')} local ({utc(alllast)}); in UTC the runs fall on 4 to 6 October 2026.")
    print("\nToken counts are not recorded in the raw files; they come from the provider dashboards for 4 to 6 October 2026 (UTC).")


if __name__ == "__main__":
    main()
