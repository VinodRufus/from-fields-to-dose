"""Send one tiny JSON request to every configured model (generator, auditor, evaluated) and report OK/FAIL."""
from harness.common import load_config, call_model, extract_json, ModelError, check_generator_exclusion
cfg = load_config(); check_generator_exclusion(cfg)
todo = [("generator", cfg.get("generator")), ("auditor", cfg.get("auditor"))] + [("model", m) for m in cfg.get("models", [])]
for role, m in todo:
    if not m or not m.get("id"): print(f"{role:9s} (no id configured, skipped)"); continue
    try:
        out = call_model(m, "Reply with JSON only.", 'Return {"ok": true, "model": "<your model name>"}', want_json=True)
        j = extract_json(out)
        print(f"{role:9s} OK   {m['id']:40s} -> {str(j)[:80] if j else out[:80]!s}")
    except ModelError as e:
        print(f"{role:9s} FAIL {m['id']:40s} -> {e}")
