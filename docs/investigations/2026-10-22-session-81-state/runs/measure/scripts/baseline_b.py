"""S81-02 MEAS-ZERO pass B: independent re-derivation of the completeness tally.

No app.* import at all. Different traversal (walks tests/fixtures and detects
full-response shapes structurally instead of a hard-coded file list), different
predicate implementations (own normaliser, own concentration regex, the fragrance
brand set read from price_service.py SOURCE via ast, not imported). Same written
definitions as pass A (see baseline_completeness.json "definitions").
argv[1] = code root, argv[2] = output json.
"""
import ast
import json
import os
import re
import sys

ROOT = sys.argv[1]
OUT = sys.argv[2]
FIX = os.path.join(ROOT, "tests", "fixtures")

PH = {"", "unknown", "unknown product", "n/a", "product", "this product"}
NA = {"", "n/a", "na", "none", "unknown", "-"}
_NRE = re.compile("[^0-9a-z" + chr(0x0600) + "-" + chr(0x06FF) + "]+")
CONC = re.compile(r"\b(extrait|parfum\s+intense|eau\s+de\s+parfum|edp|eau\s+de\s+toilette|edt|eau\s+de\s+cologne|edc|eau\s+fraiche|parfum)\b", re.I)
FRAGWORD = re.compile(r"\b(perfume|cologne|eau de parfum|eau de toilette|edp|edt|parfum|extrait|attar)\b", re.I)
MLTOK = re.compile(r"\b\d+(\.\d+)?\s*(ml|fl\.?\s*oz|oz)\b", re.I)
SIZETOK = re.compile(
    r"\b\d+([.,]\d+)?\s*(ml|l|ltr|litre|liter|fl\.?\s*oz|oz|g|gm|kg|gb|tb|tablets?|capsules?|softgels?|caps|count|ct|pcs|pieces|sachets?)\b",
    re.I,
)
SIZEKEYS = {"volume", "size", "net_volume", "net_content", "net_weight", "count", "capacity", "storage", "pack_size", "quantity"}
FRAGKEYS = {"scent_family", "notes_top", "notes_heart", "notes_base", "longevity", "sillage", "concentration"}
TSKEYS = {"retrieved_at", "fetched_at", "timestamp", "as_of", "scraped_at", "updated_at", "observed_at", "captured_at", "price_ts", "last_seen", "checked_at"}
BAD_RATING_METHODS = {"gpt_review_aggregate", "derive_rating_from_scores", "derived", "estimated"}


def frag_brands():
    src = open(os.path.join(ROOT, "app", "services", "price_service.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "FRAGRANCE_BRAND_KEYWORDS" for t in node.targets):
            return set(ast.literal_eval(node.value))
    raise SystemExit("FRAGRANCE_BRAND_KEYWORDS not found")


FB = frag_brands()


def nrm(t):
    return _NRE.sub(" ", t.casefold()).strip() if isinstance(t, str) else ""


def isna(v):
    return v is None or (isinstance(v, str) and v.strip().lower() in NA)


def realnum(v):
    return type(v) in (int, float)


def disp(brand, name):
    b = brand.strip() if isinstance(brand, str) else ""
    n = name.strip() if isinstance(name, str) else ""
    if not b:
        return n
    if not n:
        return b
    toks_b = b.lower().split()
    toks_n = n.lower().split()
    # strip every leading repeat of the brand token run from the name
    while toks_n[:len(toks_b)] == toks_b and len(toks_n) >= len(toks_b):
        toks_n = toks_n[len(toks_b):]
    rest = " ".join(toks_n)
    return (b + " " + rest).strip() if rest else b


def placeholder(p):
    return nrm(disp(p.get("brand"), p.get("name"))) in PH or nrm(p.get("name")) in PH


def collect():
    found = []
    for dirpath, dirnames, files in os.walk(FIX):
        dirnames.sort()
        for fn in sorted(files):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
            try:
                data = json.load(open(path, encoding="utf-8"))
            except Exception:
                continue
            if isinstance(data, dict) and isinstance(data.get("products"), list) and data["products"] and isinstance(data["products"][0], dict) and ("overview" in data or "scoring" in data or "comparison" in data):
                found.append((rel, data))
            elif isinstance(data, list) and data and all(isinstance(x, dict) and isinstance(x.get("full_response"), dict) for x in data):
                for x in data:
                    found.append((rel + "#row=" + str(x.get("row")), x["full_response"]))
    return found


def prods_of(resp):
    raw = resp.get("products")
    if isinstance(raw, list) and len(raw) >= 2:
        return raw
    ov = resp.get("overview") if isinstance(resp.get("overview"), dict) else {}
    return ov.get("products") if isinstance(ov.get("products"), list) else []


def ov_prods(resp):
    ov = resp.get("overview") if isinstance(resp.get("overview"), dict) else {}
    o = ov.get("products")
    if isinstance(o, list) and len(o) >= 2:
        return o
    r = resp.get("products")
    return r if isinstance(r, list) else []


def at(lst, i):
    return lst[i] if i < len(lst) and isinstance(lst[i], dict) else {}


def specs_for(resp, i):
    sb = resp.get("specs")
    if isinstance(sb, dict) and isinstance(sb.get("products"), list) and i < len(sb["products"]) and isinstance(sb["products"][i], dict):
        return sb["products"][i].get("specs")
    return at(prods_of(resp), i).get("specs")


def img_for(resp, i):
    for lst in (ov_prods(resp), prods_of(resp)):
        u = at(lst, i).get("image_url")
        if isinstance(u, str) and u.strip():
            return u.strip()
    return None


IMG_RE = re.compile(r"^https://[^/\s]+\.[^/\s]+(/|$)")


def img_ok(u):
    if not isinstance(u, str) or not IMG_RE.match(u):
        return False
    low = u.lower()
    if low.split("?")[0].endswith((".svg", ".svgz")):
        return False
    return not any(t in low for t in ("placeholder", "no-image", "noimage", "no_image", "default-image"))


def count_specs(s):
    if not isinstance(s, dict):
        return 0
    n = 0
    for k, v in s.items():
        if isinstance(k, str) and not k.startswith("_") and not isna(v):
            n += 1
    return n


def b_record(resp, i):
    p = at(prods_of(resp), i)
    s = specs_for(resp, i)
    pr = p.get("price") if isinstance(p.get("price"), dict) else None
    out = {}
    out["identity"] = not placeholder(p)
    out["image_url"] = img_ok(img_for(resp, i))
    ok = False
    if pr is not None:
        a = pr.get("amount")
        ok = realnum(a) and a > 0 and pr.get("unavailable") is not True and pr.get("estimated") is not True and pr.get("source_method") != "estimated"
    out["price_not_estimated"] = bool(ok)
    out["price_has_timestamp"] = bool(pr) and bool(TSKEYS & set(pr))
    sz = False
    if pr is not None and pr.get("size") is not None and not isna(pr.get("size")):
        sz = True
    if not sz and isinstance(s, dict):
        sz = any((k in s) and not isna(s[k]) for k in SIZEKEYS)
    if not sz:
        sz = any(isinstance(p.get(k), str) and SIZETOK.search(p.get(k)) for k in ("name", "full_name", "variant"))
    out["size"] = bool(sz)
    sc = count_specs(s)
    out["specs_count"] = sc
    out["specs"] = sc >= 1
    r = p.get("rating")
    src = p.get("rating_source") if isinstance(p.get("rating_source"), dict) else None
    out["rating_real"] = bool(realnum(r) and 0 < r <= 5 and p.get("rating_derived") is not True and src is not None and isinstance(src.get("name"), str) and src.get("name").strip() and (src.get("extract_method") if isinstance(src.get("extract_method"), str) else "") not in BAD_RATING_METHODS)
    rc = p.get("review_count")
    out["review_count"] = bool(realnum(rc) and rc > 0)
    conc = (isinstance(s, dict) and not isna(s.get("concentration"))) or (pr is not None and not isna(pr.get("concentration"))) or any(isinstance(p.get(k), str) and CONC.search(p.get(k)) for k in ("name", "full_name", "variant"))
    out["_conc"] = bool(conc)
    txt = " ".join(p.get(k) for k in ("brand", "name", "full_name", "variant") if isinstance(p.get(k), str))
    fc = bool(CONC.search(txt) or FRAGWORD.search(txt))
    if not fc and MLTOK.search(txt):
        low = txt.lower()
        fc = any(re.search(r"\b" + re.escape(b) + r"\b", low) for b in FB)
    if not fc and isinstance(s, dict):
        fc = sum(1 for k in FRAGKEYS if not isna(s.get(k))) >= 2
    out["_frag"] = fc
    out["_cat"] = p.get("category") or resp.get("category") or resp.get("category_used")
    return out


FIELDS = ["identity", "image_url", "price_not_estimated", "size", "concentration", "specs", "rating_real", "review_count"]


def main():
    rows = []
    excluded = []
    for src, resp in collect():
        if len(prods_of(resp)) < 2:
            excluded.append(src)
            continue
        recs = [b_record(resp, 0), b_record(resp, 1)]
        cat = resp.get("category") or resp.get("category_used")
        stored = cat == "fragrances" or (recs[0]["_cat"] == "fragrances" and recs[1]["_cat"] == "fragrances")
        content = stored or recs[0]["_frag"] or recs[1]["_frag"]
        for i, r in enumerate(recs):
            r["concentration"] = r["_conc"] if content else None
            r["source"] = src
            r["index"] = i
            r["pair_fragrance_stored"] = stored
            r["pair_fragrance_content"] = content
            rows.append(r)

    def tally(sel_key):
        rs = [r for r in rows if sel_key is None or r[sel_key]]
        pairs = {}
        for r in rs:
            pairs.setdefault(r["source"], []).append(r)
        res = {}
        for f in FIELDS:
            if f == "concentration" and sel_key is None:
                continue
            pp = sum(1 for v in pairs.values() if all(x[f] is True for x in v) and len(v) == 2)
            res[f] = {"product_present": sum(1 for r in rs if r[f] is True), "product_n": len(rs), "pair_both_present": pp, "pair_n": len(pairs)}
        res["specs_count_sum"] = sum(r["specs_count"] for r in rs)
        res["price_has_timestamp"] = sum(1 for r in rs if r["price_has_timestamp"])
        return res

    out = {
        "unit": "S81-02 completeness baseline (pass B, independent)",
        "excluded": excluded,
        "overall": tally(None),
        "fragrance_by_content": tally("pair_fragrance_content"),
        "fragrance_by_stored_category": tally("pair_fragrance_stored"),
        "products": [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows],
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
        fh.write("\n")
    print("B products", len(rows), "excluded", len(excluded))


main()
