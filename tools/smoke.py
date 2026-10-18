"""End-to-end smoke test with DEMO sources and fake models. No API keys."""
import os, subprocess, sys, glob, json
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
def run(args, env=None):
    print("$", " ".join(args)); subprocess.check_call([sys.executable, "-m"] + args, cwd=ROOT, env=env)
if __name__ == "__main__":
    src = "sources/dosing_sources.example.csv"
    env = dict(os.environ, F2D_SMOKE="1")
    lock = os.path.join(ROOT, "data", "test", "LOCK.json")
    if os.path.exists(lock) and not json.load(open(lock)).get("smoke"):
        sys.exit("data/test is locked with real data; refusing to run the smoke test")
    for p in glob.glob(os.path.join(ROOT, "data", "test", "*")) + glob.glob(os.path.join(ROOT, "results", "*_FAKE_*.jsonl")):
        if not p.endswith(".keep"): os.remove(p)
    run(["generator.build_corpus", "--dev", "--sources", src, "--variants", "2", "--allow-unverified"])
    run(["generator.paraphrase", "--split", "dev", "--fake", "--fraction", "0.5"])
    run(["generator.audit", "--split", "dev", "--fake"])
    run(["generator.build_corpus", "--test", "--sources", src, "--variants", "2", "--allow-unverified"], env=env)
    run(["tools.make_repeat_subset", "--split", "test"])
    run(["tools.lock_testset"])
    for wf in ("C", "B"):
        run(["harness.runner", "--split", "test", "--workflow", wf, "--fake", "--run-id", "run1"])
    for rid in ("run2", "run3"):
        run(["harness.runner", "--split", "test", "--workflow", "C", "--fake", "--run-id", rid, "--subset", "data/test/repeat_subset.txt"])
    run(["scoring.score", "--raw"] + glob.glob(os.path.join(ROOT, "results", "raw_test_*_FAKE_*.jsonl")))
    run(["analysis.analyze", "--scored"] + glob.glob(os.path.join(ROOT, "results", "scored_test_*_FAKE_run1.jsonl")))
    run(["analysis.stability", "--scored"] + [os.path.join(ROOT, "results", f"scored_test_C_FAKE_{r}.jsonl") for r in ("run1", "run2", "run3")])
    for p in glob.glob(os.path.join(ROOT, "data", "test", "*")) + glob.glob(os.path.join(ROOT, "results", "*_FAKE_*.jsonl")):
        if not p.endswith(".keep"): os.remove(p)
    print("\nSMOKE TEST PASSED. data/test cleaned. (dev data kept for inspection.)")
