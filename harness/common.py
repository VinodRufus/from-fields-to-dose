"""Shared helpers: .env loading, model config, provider calls with retries."""
from __future__ import annotations
import json, os, sys, time, random
from typing import Dict, Any, Optional

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def load_env(path: str = os.path.join(ROOT, ".env")) -> None:
    if not os.path.exists(path): return
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, _, v = line.partition("="); k = k.strip(); v = v.strip().strip('"').strip("'")
        if k and k not in os.environ: os.environ[k] = v

def _coerce(v: str):
    v = v.strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")): return v[1:-1]
    if v == "": return ""
    if v.lower() in ("true", "false"): return v.lower() == "true"
    if v.lower() in ("null", "none", "~"): return None
    try:
        return int(v) if v.lstrip("-").isdigit() else float(v)
    except ValueError:
        return v

def load_yaml_min(path: str) -> Dict[str, Any]:
    """Tiny YAML subset loader (top-level keys, nested dict, list of dicts). No dependency."""
    try:
        import yaml  # type: ignore
        return yaml.safe_load(open(path))
    except ImportError:
        pass
    cfg: Dict[str, Any] = {"models": []}; cur = None; section = None
    for raw in open(path):
        line = raw.split("#")[0].rstrip()
        if not line.strip(): continue
        if not line.startswith(" "):
            key, _, val = line.partition(":"); key = key.strip(); val = val.strip(); section = key
            if val: cfg[key] = _coerce(val)
            elif key == "models": cfg["models"] = []
            else: cfg[key] = {}
            continue
        s = line.strip()
        if section == "models":
            if s.startswith("- "): cur = {}; cfg["models"].append(cur); s = s[2:]
            k, _, v = s.partition(":"); cur[k.strip()] = _coerce(v)
        else:
            k, _, v = s.partition(":"); cfg[section][k.strip()] = _coerce(v)
    return cfg

def load_config() -> Dict[str, Any]:
    load_env()
    return load_yaml_min(os.path.join(ROOT, "config", "models.yaml"))

def check_generator_exclusion(cfg):
    gen = cfg.get("generator") or {}
    gfam = (gen.get("family") or "").lower()
    for m in cfg.get("models", []):
        if not m.get("id"): continue
        if gfam and (str(m.get("family", "")).lower() == gfam):
            sys.exit(f"refusing: evaluated model {m['id']} shares family '{gfam}' with the generator (Protocol 7.1)")

def _api_key(m: Dict[str, Any]) -> Optional[str]:
    env = m.get("api_key_env")
    if env: return os.environ.get(env)
    return {"openai": os.environ.get("OPENAI_API_KEY"), "anthropic": os.environ.get("ANTHROPIC_API_KEY")}.get(m.get("provider"))

class ModelError(Exception): pass

def call_model(m: Dict[str, Any], system: str, user: str, want_json: bool = True) -> str:
    """One call with up to 6 retries on rate limits / transient errors. Raises ModelError otherwise."""
    prov = m["provider"]; key = _api_key(m)
    if prov in ("openai", "openai_compatible") and not key: raise ModelError(f"no API key for {m['id']} (set {m.get('api_key_env') or 'OPENAI_API_KEY'})")
    if prov == "anthropic" and not key: raise ModelError("ANTHROPIC_API_KEY not set")
    delay = 2.0
    for attempt in range(7):
        try:
            if prov in ("openai", "openai_compatible"):
                from openai import OpenAI  # type: ignore
                client = OpenAI(api_key=key, base_url=(m.get("base_url") or None))
                kw: Dict[str, Any] = {"model": m["id"], "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
                if m.get("temperature") is not None: kw["temperature"] = m["temperature"]
                if m.get("seed") is not None: kw["seed"] = m["seed"]
                mt = m.get("max_output_tokens", 800)
                if prov == "openai": kw["max_completion_tokens"] = mt
                else: kw["max_tokens"] = mt
                if want_json: kw["response_format"] = {"type": "json_object"}
                try:
                    r = client.chat.completions.create(**kw)
                except Exception as e:
                    msg = str(e)
                    # Some models reject temperature/seed/response_format; drop the offending key and retry once.
                    dropped = False
                    for bad in ("temperature", "seed", "response_format", "max_completion_tokens", "max_tokens"):
                        if bad in msg and bad in kw:
                            if bad == "max_completion_tokens": kw["max_tokens"] = kw.pop(bad)
                            elif bad == "max_tokens" and "max_completion_tokens" not in kw: kw["max_completion_tokens"] = kw.pop(bad)
                            else: kw.pop(bad)
                            dropped = True
                    if not dropped: raise
                    r = client.chat.completions.create(**kw)
                return r.choices[0].message.content or ""
            if prov == "anthropic":
                import anthropic  # type: ignore
                client = anthropic.Anthropic(api_key=key)
                kw = {"model": m["id"], "max_tokens": m.get("max_output_tokens", 800), "system": system,
                      "messages": [{"role": "user", "content": user}]}
                r = client.messages.create(**kw)
                return "".join(getattr(b, "text", "") for b in r.content)
            raise ModelError(f"unknown provider {prov}")
        except ModelError:
            raise
        except Exception as e:
            msg = str(e).lower()
            transient = any(t in msg for t in ("rate limit", "429", "overloaded", "503", "502", "timeout", "temporarily", "resource_exhausted", "quota")) and not any(t in msg for t in ("402", "credit", "insufficient_quota", "billing", "prepayment"))
            if attempt < 6 and transient:
                time.sleep(delay + random.uniform(0, 1)); delay = min(delay * 2, 90); continue
            raise ModelError(f"{type(e).__name__}: {e}")
    raise ModelError("retries exhausted")

def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Parse a JSON object from a model reply, tolerating code fences and leading prose."""
    if text is None: return None
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"): t = t[4:]
    try:
        return json.loads(t)
    except Exception:
        pass
    i, j = t.find("{"), t.rfind("}")
    if i >= 0 and j > i:
        try: return json.loads(t[i:j+1])
        except Exception: return None
    return None
