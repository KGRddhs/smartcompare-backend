"""Session 69 - run AFTER OpenAI credits are added. Read-only against production; spends a few
LLM calls (3 uncached compares + 1 stream). Never prints secrets. Exit 0 iff every probe passes.

  python docs/investigations/2026-09-29-session-69-state/verify_after_credits.py
  python ... --base https://web-production-58776.up.railway.app --pairs "A vs B" "C vs D"
"""
from __future__ import annotations
import argparse, json, sys, time
import httpx

DEFAULT_BASE = "https://web-production-58776.up.railway.app"
DEFAULT_PAIRS = [
    "iPhone 15 vs Galaxy S24",                                   # the canonical pair (parse-failure copy names it)
    "Dior Sauvage EDP 100ml vs Bleu de Chanel EDP 100ml",        # the pitch-prep fragrance pair (came back thin 2026-09-27)
    "Optimum Nutrition Gold Standard Whey vs Dymatize ISO100",  # supplements
]

def probe_compare(client: httpx.Client, base: str, q: str, region: str = "bahrain") -> dict:
    t = time.time()
    r = client.get(f"{base}/api/v1/text/compare", params={"q": q, "nocache": "true", "region": region})
    ms = int((time.time() - t) * 1000)
    out = {"q": q, "http": r.status_code, "ms": ms}
    try:
        d = r.json()
    except Exception:
        out["error"] = "non-json body"; return out
    out["success"] = d.get("success")
    out["error"] = d.get("error")
    prods = d.get("products") or []
    out["products"] = [(p.get("name"), p.get("price"), p.get("price_status") or p.get("price_confidence")) for p in prods][:2]
    ov = d.get("overview") or {}
    out["winner"] = (ov.get("winner") or {}).get("name") if isinstance(ov.get("winner"), dict) else ov.get("winner")
    out["specs_rows"] = len(d.get("specs") or d.get("spec_rows") or [])
    out["has_verdict"] = bool(d.get("verdict") or ov.get("winner"))
    return out

def probe_stream(client: httpx.Client, base: str, q: str) -> dict:
    t = time.time(); events = 0; last = ""
    with client.stream("GET", f"{base}/api/v1/text/compare/stream", params={"q": q, "nocache": "true"}, timeout=150) as r:
        for line in r.iter_lines():
            if line.startswith("event:") or line.startswith("data:"):
                events += 1; last = line[:120]
    return {"q": q, "http": r.status_code, "events": events, "last": last, "ms": int((time.time() - t) * 1000)}

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--base", default=DEFAULT_BASE); ap.add_argument("--pairs", nargs="*", default=DEFAULT_PAIRS)
    a = ap.parse_args()
    ok = True
    with httpx.Client(timeout=150) as c:
        h = c.get(f"{a.base}/health"); print("health", h.status_code, h.text[:80]); ok &= h.status_code == 200
        for q in a.pairs:
            res = probe_compare(c, a.base, q); print(json.dumps(res, ensure_ascii=False))
            ok &= res["http"] == 200 and bool(res.get("success", True)) and res.get("has_verdict", False)
        s = probe_stream(c, a.base, a.pairs[0]); print(json.dumps(s, ensure_ascii=False)); ok &= s["http"] == 200 and s["events"] > 0
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
