"""S81-02 MEAS-ZERO pass A: per-field completeness over stored comparison responses.

Read-only. Zero network. Reads fixtures from the code root given as argv[1], writes
the JSON named by argv[2]. Uses the repo predicates from app/services/result_gate.py
(imported; that module imports only os/re/typing and text_sanitize -> re) and the
repo extract_concentration from app/services/price_service.py (imported behind a
dotenv stub and a socket deny guard). Pass B (baseline_b.py) re-derives everything
without any repo import.
"""
import glob
import json
import os
import re
import socket
import sys
import types

ROOT = sys.argv[1]
OUT = sys.argv[2]
sys.path.insert(0, ROOT)

# guards: no .env read, no network
_fake = types.ModuleType("dotenv")
_fake.load_dotenv = lambda *a, **k: False
_fake.find_dotenv = lambda *a, **k: ""
_fake.dotenv_values = lambda *a, **k: {}
sys.modules["dotenv"] = _fake
NET_CALLS = []


def _deny(*a, **k):
    NET_CALLS.append(str(a[:1]))
    raise OSError("netguard")


socket.socket.connect = _deny
socket.getaddrinfo = _deny
socket.create_connection = _deny

from app.services import result_gate as RG  # noqa: E402
from app.services.price_service import extract_concentration, FRAGRANCE_BRAND_KEYWORDS  # noqa: E402

FRAG_SPEC_KEYS = ("scent_family", "notes_top", "notes_heart", "notes_base", "longevity", "sillage", "concentration")
FRAG_WORDS_RE = re.compile(r"\b(perfume|cologne|eau de parfum|eau de toilette|edp|edt|parfum|extrait|attar)\b", re.I)
ML_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:ml|fl\.?\s*oz|oz)\b", re.I)
SIZE_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:ml|l|ltr|litre|liter|fl\.?\s*oz|oz|g|gm|kg|gb|tb|tablets?|capsules?|softgels?|caps|count|ct|pcs|pieces|sachets?)\b",
    re.I,
)
SIZE_SPEC_KEYS = ("volume", "size", "net_volume", "net_content", "net_weight", "count", "capacity", "storage", "pack_size", "quantity")
TS_KEYS = ("retrieved_at", "fetched_at", "timestamp", "as_of", "scraped_at", "updated_at", "observed_at", "captured_at", "price_ts", "last_seen", "checked_at")
DERIVED_METHODS = ("gpt_review_aggregate", "derive_rating_from_scores", "derived", "estimated")
NONRASTER_EXT = (".svg", ".svgz")
PLACEHOLDER_IMG = ("placeholder", "no-image", "noimage", "no_image", "default-image")


def _s(v):
    return v if isinstance(v, str) else ""


def load_responses():
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "tests", "fixtures", "lane1", "*_response.json"))):
        out.append((os.path.relpath(f, ROOT).replace("\\", "/"), json.load(open(f, encoding="utf-8"))))
    for f in sorted(glob.glob(os.path.join(ROOT, "tests", "fixtures", "comparison_baseline_d2*.json"))):
        out.append((os.path.relpath(f, ROOT).replace("\\", "/"), json.load(open(f, encoding="utf-8"))))
    wf = os.path.join(ROOT, "tests", "fixtures", "w412_corpus_min.json")
    for r in json.load(open(wf, encoding="utf-8")):
        out.append(("tests/fixtures/w412_corpus_min.json#row=%d" % r["row"], r["full_response"]))
    return out


def response_category(resp):
    return resp.get("category") or resp.get("category_used")


def raw_products(resp):
    return RG._raw_products(resp)


def overview_products(resp):
    return RG._overview_products(resp)


def image_of(resp, i):
    for prods in (overview_products(resp), raw_products(resp)):
        p = RG._product_at(prods, i)
        u = p.get("image_url")
        if isinstance(u, str) and u.strip():
            return u.strip()
    return None


def image_ok(url):
    if not isinstance(url, str) or not url.startswith("https://"):
        return False
    rest = url[len("https://"):]
    host = rest.split("/", 1)[0]
    if not host or "." not in host:
        return False
    path = rest.split("?", 1)[0].lower()
    if path.endswith(NONRASTER_EXT):
        return False
    if any(t in url.lower() for t in PLACEHOLDER_IMG):
        return False
    return True


def image_ext(url):
    if not isinstance(url, str):
        return None
    path = url.split("?", 1)[0].split("#", 1)[0]
    last = path.rsplit("/", 1)[-1]
    if "." in last:
        return last.rsplit(".", 1)[-1].lower()[:8]
    return "(none)"


def price_present_not_estimated(price):
    if not isinstance(price, dict):
        return False
    a = price.get("amount")
    if not RG._num(a) or a <= 0:
        return False
    if price.get("unavailable") is True or price.get("estimated") is True:
        return False
    return price.get("source_method") != "estimated"


def price_url_kind(price):
    if not isinstance(price, dict):
        return "none"
    u = _s(price.get("url")).lower()
    if not u:
        return "none"
    if "google.com/search" in u or "/search" in u or "?q=" in u or "&q=" in u or "?s=" in u or "?kw=" in u or "search?" in u:
        return "search_page"
    return "pdp_or_other"


def size_present(p, specs):
    price = p.get("price") if isinstance(p.get("price"), dict) else {}
    if not RG._is_na(price.get("size")) and price.get("size") is not None:
        return True
    if isinstance(specs, dict):
        for k in SIZE_SPEC_KEYS:
            if k in specs and not RG._is_na(specs.get(k)) and not (isinstance(specs.get(k), str) and specs.get(k).strip().lower() == "n/a"):
                return True
    for t in (p.get("name"), p.get("full_name"), p.get("variant")):
        if isinstance(t, str) and SIZE_RE.search(t):
            return True
    return False


def concentration_present(p, specs):
    if isinstance(specs, dict) and not RG._is_na(specs.get("concentration")) and specs.get("concentration") is not None:
        return True
    price = p.get("price") if isinstance(p.get("price"), dict) else {}
    if not RG._is_na(price.get("concentration")) and price.get("concentration") is not None:
        return True
    for t in (p.get("name"), p.get("full_name"), p.get("variant")):
        if isinstance(t, str) and extract_concentration(t):
            return True
    return False


def rating_real(p):
    if not RG.rating_is_real(p):
        return False
    r = p.get("rating")
    if not (0 < r <= 5):
        return False
    src = p.get("rating_source")
    if not isinstance(src, dict) or not _s(src.get("name")).strip():
        return False
    return _s(src.get("extract_method")) not in DERIVED_METHODS


def review_count_present(p):
    rc = p.get("review_count")
    return RG._num(rc) and rc > 0


def product_is_fragrance_content(p, specs):
    text = " ".join(_s(p.get(k)) for k in ("brand", "name", "full_name", "variant"))
    low = text.lower()
    if extract_concentration(text) or FRAG_WORDS_RE.search(text):
        return True
    if ML_RE.search(text) and any(re.search(r"\b" + re.escape(b) + r"\b", low) for b in FRAGRANCE_BRAND_KEYWORDS):
        return True
    if isinstance(specs, dict) and sum(1 for k in FRAG_SPEC_KEYS if not RG._is_na(specs.get(k)) and specs.get(k) is not None) >= 2:
        return True
    return False


FIELDS = ("identity", "image_url", "price_not_estimated", "size", "concentration", "specs", "rating_real", "review_count")


def main():
    responses = load_responses()
    products = []
    pairs = []
    excluded = []
    for src, resp in responses:
        prods = raw_products(resp)
        if len(prods) < 2:
            excluded.append({"source": src, "reason": "fewer than 2 products in stored response", "n_products": len(prods)})
            continue
        cat = response_category(resp)
        recs = []
        for i in range(2):
            p = RG._product_at(prods, i)
            specs = RG._specs_of(resp, i)
            price = p.get("price") if isinstance(p.get("price"), dict) else None
            img = image_of(resp, i)
            rec = {
                "source": src,
                "index": i,
                "category_stored": p.get("category") or cat,
                "identity": not RG.product_is_placeholder(p),
                "image_url": image_ok(img),
                "image_ext": image_ext(img),
                "price_not_estimated": price_present_not_estimated(price),
                "price_source_method": (price or {}).get("source_method"),
                "price_estimated_flag": (price or {}).get("estimated"),
                "price_has_timestamp": bool(price) and any(k in price for k in TS_KEYS),
                "price_url_kind": price_url_kind(price),
                "price_showable_repo": RG.price_is_showable(price),
                "size": size_present(p, specs),
                "specs_count": RG.real_spec_rows_one_side(specs),
                "rating_real": rating_real(p),
                "rating_is_real_repo": RG.rating_is_real(p),
                "rating_extract_method": (p.get("rating_source") or {}).get("extract_method") if isinstance(p.get("rating_source"), dict) else None,
                "review_count": review_count_present(p),
                "frag_content": product_is_fragrance_content(p, specs),
            }
            rec["specs"] = rec["specs_count"] >= 1
            rec["concentration_raw"] = concentration_present(p, specs)
            recs.append(rec)
        stored_frag = (cat == "fragrances") or all(r["category_stored"] == "fragrances" for r in recs)
        content_frag = stored_frag or any(r["frag_content"] for r in recs)
        for r in recs:
            r["pair_fragrance_stored"] = stored_frag
            r["pair_fragrance_content"] = content_frag
            r["concentration"] = r["concentration_raw"] if content_frag else None
            products.append(r)
        pairs.append({
            "source": src,
            "category_stored": cat,
            "fragrance_stored": stored_frag,
            "fragrance_content": content_frag,
            "query": resp.get("query") or (resp.get("metadata") or {}).get("query"),
            "response_timestamp_present": bool((resp.get("metadata") or {}).get("timestamp")),
        })

    def tally(prods, prs, frag_only):
        out = {}
        n_p = len(prods)
        n_pairs = len(prs)
        for f in FIELDS:
            if f == "concentration" and not frag_only:
                continue
            pc = sum(1 for r in prods if r[f] is True)
            by_pair = {}
            for r in prods:
                by_pair.setdefault(r["source"], []).append(r[f] is True)
            pp = sum(1 for v in by_pair.values() if len(v) == 2 and all(v))
            out[f] = {
                "product_present": pc, "product_n": n_p, "product_rate": round(pc / n_p, 4) if n_p else None,
                "pair_both_present": pp, "pair_n": n_pairs, "pair_rate": round(pp / n_pairs, 4) if n_pairs else None,
                "tag": "measured",
            }
        sc = [r["specs_count"] for r in prods]
        out["specs_count_mean"] = {"value": round(sum(sc) / len(sc), 3) if sc else None, "n": len(sc), "tag": "measured"}
        sm = {}
        for r in prods:
            k = str(r["price_source_method"])
            sm[k] = sm.get(k, 0) + 1
        out["price_source_method_counts"] = {"value": dict(sorted(sm.items())), "n": n_p, "tag": "measured"}
        out["price_has_timestamp"] = {"value": sum(1 for r in prods if r["price_has_timestamp"]), "n": n_p, "tag": "measured"}
        uk = {}
        for r in prods:
            uk[r["price_url_kind"]] = uk.get(r["price_url_kind"], 0) + 1
        out["price_url_kind_counts"] = {"value": dict(sorted(uk.items())), "n": n_p, "tag": "measured"}
        ie = {}
        for r in prods:
            ie[str(r["image_ext"])] = ie.get(str(r["image_ext"]), 0) + 1
        out["image_ext_counts"] = {"value": dict(sorted(ie.items())), "n": n_p, "tag": "measured"}
        return out

    fr_c = [r for r in products if r["pair_fragrance_content"]]
    fr_s = [r for r in products if r["pair_fragrance_stored"]]
    result = {
        "unit": "S81-02 MEAS-ZERO completeness baseline (pass A)",
        "code_root": ROOT.replace("\\", "/"),
        "net_calls_attempted": NET_CALLS,
        "inputs": sorted({s.split("#")[0] for s, _ in responses}),
        "n_responses_read": len(responses),
        "excluded": excluded,
        "overall": tally(products, pairs, False),
        "fragrance_by_content": tally(fr_c, [p for p in pairs if p["fragrance_content"]], True),
        "fragrance_by_stored_category": tally(fr_s, [p for p in pairs if p["fragrance_stored"]], True),
        "pairs": pairs,
        "products": products,
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(result, fh, indent=1, ensure_ascii=True, sort_keys=False)
        fh.write("\n")
    print("A products", len(products), "pairs", len(pairs), "excluded", len(excluded), "net", len(NET_CALLS))


main()
