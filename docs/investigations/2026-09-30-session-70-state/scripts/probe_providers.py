"""Provider liveness probe. Run as: railway run -s web python probe_providers.py
Prints STATUS ONLY - never a key, a URL carrying a key, or an env value."""
import json
import os
import urllib.error
import urllib.request


def call(req, timeout=30):
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # noqa: BLE001
        return None, type(e).__name__.encode()


def js(b):
    try:
        return json.loads(b)
    except Exception:  # noqa: BLE001
        return None


def present(name):
    return bool(os.environ.get(name, "").strip())


print("== env NAMES present ==")
for n in ["OPENAI_API_KEY", "SERPER_API_KEY", "FIRECRAWL_API_KEY", "SCRAPEDO_API_TOKEN",
          "BRIGHTDATA_API_KEY", "BRIGHTDATA_ZONE", "ZYTE_API_KEY", "OPENAI_MAX_RETRIES",
          "OPENAI_FALLBACK_MAX_RETRIES", "SERPER_LIFETIME_LIMIT"]:
    print(f"  {n}: {'set' if present(n) else 'UNSET'}")
for n in ["ENABLE_BRIGHTDATA_FALLBACK", "ENABLE_BRIGHTDATA_BUDGET_GATE", "ENABLE_FIRECRAWL",
          "ENABLE_SCRAPEDO", "ENABLE_PAGE_SCRAPE", "ENABLE_PAID_ROUTE_METERING"]:
    v = os.environ.get(n)
    print(f"  {n}: {'UNSET' if v is None else ('true' if v.strip().lower() in ('1','true','yes','on') else 'false-ish')}")

print("== OpenAI (1-token gpt-4o-mini) ==")
k = os.environ.get("OPENAI_API_KEY", "")
if k:
    body = json.dumps({"model": "gpt-4o-mini", "max_tokens": 1,
                       "messages": [{"role": "user", "content": "hi"}]}).encode()
    st, b = call(urllib.request.Request("https://api.openai.com/v1/chat/completions", data=body,
                 headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"}))
    d = js(b) or {}
    err = d.get("error") or {}
    print(f"  status={st} error.code={err.get('code')} error.type={err.get('type')}")

print("== Serper (1 search credit) ==")
k = os.environ.get("SERPER_API_KEY", "")
if k:
    st, b = call(urllib.request.Request("https://google.serper.dev/search",
                 data=json.dumps({"q": "iphone 15 price bahrain"}).encode(),
                 headers={"X-API-KEY": k, "Content-Type": "application/json"}))
    d = js(b) or {}
    print(f"  status={st} organic={len(d.get('organic', []) or [])} credits_field={d.get('credits')} msg={str(d.get('message'))[:80] if st != 200 else ''}")

print("== Firecrawl (credit usage, free) ==")
k = os.environ.get("FIRECRAWL_API_KEY", "")
if k:
    st, b = call(urllib.request.Request("https://api.firecrawl.dev/v1/team/credit-usage",
                 headers={"Authorization": f"Bearer {k}"}))
    d = js(b) or {}
    data = d.get("data") or {}
    print(f"  status={st} remaining_credits={data.get('remaining_credits')}")

print("== Scrape.do (account info, free) ==")
k = os.environ.get("SCRAPEDO_API_TOKEN", "")
if k:
    st, b = call(urllib.request.Request(f"https://api.scrape.do/info?token={k}"))
    d = js(b) or {}
    safe = {kk: d.get(kk) for kk in ("IsActive", "ConcurrentRequest", "MaxMonthlyRequest",
                                      "RemainingConcurrentRequest", "RemainingMonthlyRequest")}
    print(f"  status={st} {safe}")
print("== done ==")
