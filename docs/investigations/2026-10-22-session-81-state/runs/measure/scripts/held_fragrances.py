"""S81-02: distinct fragrance juices held at zero network cost + corpus fragrance PDP field presence.

argv[1] = code root, argv[2] = scraper-proof _proof dir, argv[3] = output json.
Imports app.services.spec_spine_service.spine_key behind a dotenv stub and a socket
deny guard (no .env read, no network). The corpora HTML is untrusted data: parsed with
re + json only, never executed.
"""
import hashlib
import html as htmlmod
import json
import os
import re
import socket
import sys
import types

ROOT, PROOF, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, ROOT)
_fake = types.ModuleType("dotenv")
_fake.load_dotenv = lambda *a, **k: False
_fake.find_dotenv = lambda *a, **k: ""
_fake.dotenv_values = lambda *a, **k: {}
sys.modules["dotenv"] = _fake
NET = []


def _deny(*a, **k):
    NET.append(str(a[:1]))
    raise OSError("netguard")


socket.socket.connect = _deny
socket.getaddrinfo = _deny
socket.create_connection = _deny
_env_before = set(os.environ)
from app.services.spec_spine_service import spine_key  # noqa: E402
from app.services.price_service import extract_concentration, FRAGRANCE_BRAND_KEYWORDS  # noqa: E402
ENV_ADDED = sorted(set(os.environ) - _env_before)

# Documented brand vocabulary for splitting a free-text juice string into brand + line.
# Longest match at the start of the string wins (case-insensitive). The repo has no
# brand splitter for free text (spine_key takes brand and name separately).
BRANDS = sorted({
    "tom ford", "creed", "christian dior", "dior", "ysl", "yves saint laurent", "hugo boss", "davidoff",
    "mfk", "maison francis kurkdjian", "initio", "chanel", "lattafa", "armaf", "rasasi", "ajmal",
    "swiss arabian", "al haramain", "afnan", "versace", "paco rabanne", "giorgio armani", "armani",
    "dolce & gabbana", "jo malone", "le labo", "mancera", "montale", "carolina herrera", "lancome",
    "nishane", "xerjoff", "maison margiela", "by kilian", "kilian", "prada", "valentino",
    "jean paul gaultier", "azzaro", "parfums de marly",
}, key=len, reverse=True)


def split_brand(s):
    low = s.strip().lower()
    for b in BRANDS:
        if low == b or low.startswith(b + " "):
            return s.strip()[:len(b)], s.strip()[len(b):].strip(), True
    return "", s.strip(), False


def key_of(brand, line):
    k = spine_key(brand, line, None, "fragrances")
    parts = k.split("|")
    return "|".join(parts[1:4]), k


def sides(q):
    return [x.strip() for x in re.split(r"\s+vs\.?\s+", q, flags=re.I) if x.strip()]


entries = []


def add(source_file, source_id, text):
    brand, line, resolved = split_brand(text)
    k3, full = key_of(brand, line)
    entries.append({"source_file": source_file, "source_id": source_id, "text": text, "brand": brand, "line": line,
                    "brand_resolved": resolved, "key": k3, "spine_key_full": full})


gold = json.load(open(os.path.join(ROOT, "data", "validation_gold_truth.json"), encoding="utf-8"))
gold_frag = [q for q in gold["queries"] if q.get("category") == "fragrances"]
for q in gold_frag:
    for s in sides(q["query"]):
        add("data/validation_gold_truth.json", q["id"], s)
warm = json.load(open(os.path.join(ROOT, "data", "warmer_catalog.json"), encoding="utf-8"))
warm_frag = [q for q in warm["queries"] if q.get("category") == "fragrances"]
for q in warm_frag:
    for s in sides(q["query"]):
        add("data/warmer_catalog.json", q["id"], s)
trend = json.load(open(os.path.join(ROOT, "data", "trending_curated.json"), encoding="utf-8"))
trend_rows = 0
for region, rows in trend.items():
    if region.startswith("_") or not isinstance(rows, list):
        continue
    for i, e in enumerate(rows):
        if str(e.get("tag", "")).lower().startswith("fragrance"):
            trend_rows += 1
            for side in ("a", "b"):
                add("data/trending_curated.json", "%s[%d].%s" % (region, i, side), e[side])
smoke = json.load(open(os.path.join(ROOT, "data", "eval_smoke_subset.json"), encoding="utf-8"))
gold_by_id = {q["id"]: q for q in gold["queries"]}
smoke_frag = [i for i in smoke["ids"] if gold_by_id.get(i, {}).get("category") == "fragrances"]
for i in smoke_frag:
    for s in sides(gold_by_id[i]["query"]):
        add("data/eval_smoke_subset.json", i, s)

by_key = {}
for e in entries:
    by_key.setdefault(e["key"], {"key": e["key"], "texts": set(), "sources": set()})
    by_key[e["key"]]["texts"].add(e["text"])
    by_key[e["key"]]["sources"].add(e["source_file"])
keys = sorted(by_key)
bl = sorted({"|".join(k.split("|")[:2]) for k in keys})


def per_source(sf):
    return sorted({e["key"] for e in entries if e["source_file"] == sf})


# near-duplicate keys the repo logic does NOT fold (inferred: same juice spelled two ways)
def toks(k):
    b, l, c = k.split("|")
    return set(l.split("-")) - {""}


near = []
for i in range(len(keys)):
    for j in range(i + 1, len(keys)):
        a, b = keys[i], keys[j]
        ta, tb = toks(a), toks(b)
        same_brand = a.split("|")[0] == b.split("|")[0]
        if ta and tb and (ta == tb or ((ta <= tb or tb <= ta) and same_brand)):
            near.append([a, b])
        elif ta and tb and ta == tb and not same_brand:
            near.append([a, b])

# inferred same-juice folds (judgement, NOT repo logic): a line with no concentration folds into the
# same line with one; MFK = Maison Francis Kurkdjian; '1 Million' = 'One Million'. Flankers stay apart
# (Hawas vs Hawas Viper, Amber Oud vs Amber Oud Gold Edition are different juices).
INFERRED_SAME = [("mfk|540-baccarat-rouge|-", "francis+kurkdjian+maison|540-baccarat-rouge|-"),
                 ("paco+rabanne|1-million|-", "paco+rabanne|million-one|-")]
_parent = {k: k for k in keys}


def _find(x):
    while _parent[x] != x:
        x = _parent[x]
    return x


def _union(a, b):
    if a in _parent and b in _parent:
        _parent[_find(a)] = _find(b)


for a, b in INFERRED_SAME:
    _union(a, b)
for k in keys:
    b, l, c = k.split("|")
    if c == "-":
        for k2 in keys:
            if k2 != k and k2.startswith(b + "|" + l + "|"):
                _union(k, k2)
inferred_groups = {}
for k in keys:
    inferred_groups.setdefault(_find(k), []).append(k)
inferred_folds = [sorted(v) for v in inferred_groups.values() if len(v) > 1]

# fixture-response fragrance products (not in the headline count)
fixture_keys = set()
bc = json.load(open(os.path.join(os.path.dirname(OUT), "baseline_completeness.json"), encoding="utf-8"))
fix_src = {}
for p in bc["products"]:
    if p["pair_fragrance_content"]:
        fix_src.setdefault(p["source"], []).append(p["index"])


def load_resp(src):
    if "#row=" in src:
        f, row = src.split("#row=")
        for r in json.load(open(os.path.join(ROOT, f), encoding="utf-8")):
            if str(r["row"]) == row:
                return r["full_response"]
    return json.load(open(os.path.join(ROOT, src), encoding="utf-8"))


for src, idxs in fix_src.items():
    resp = load_resp(src)
    for i in idxs:
        p = resp["products"][i]
        b = p.get("brand") or ""
        n = p.get("name") or ""
        fixture_keys.add(key_of(b, n)[0])
fixture_new = sorted(fixture_keys - set(keys))

# ---------------- corpora: fragrance PDPs by host with JSON-LD field presence ----------------
LD_RE = re.compile(r"<script[^>]*type\s*=\s*[\"']application/ld\+json[\"'][^>]*>(.*?)</script>", re.I | re.S)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
OGT_RE = re.compile(r"<meta[^>]+property\s*=\s*[\"']og:title[\"'][^>]*content\s*=\s*[\"']([^\"']*)[\"']", re.I)
SIZE_TITLE_RE = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:ml|fl\.?\s*oz|oz)\b", re.I)
FRAG_WORD_RE = re.compile(r"\b(perfume|parfum|cologne|eau de parfum|eau de toilette|edp|edt|edc|extrait|attar|fragrance|oud)\b", re.I)


def ld_nodes(txt):
    out = []
    for m in LD_RE.finditer(txt):
        raw = m.group(1).strip()
        raw = re.sub(r"^\s*<!--|-->\s*$", "", raw)
        raw = re.sub(r"^\s*//\s*<!\[CDATA\[|//\s*\]\]>\s*$", "", raw)
        data = None
        for cand in (raw, htmlmod.unescape(raw)):
            try:
                data = json.loads(cand, strict=False)
                break
            except Exception:
                continue
        if data is None:
            continue
        stack = [data]
        while stack:
            x = stack.pop()
            if isinstance(x, list):
                stack.extend(x)
            elif isinstance(x, dict):
                out.append(x)
                for v in x.values():
                    if isinstance(v, (dict, list)):
                        stack.append(v)
    return out


def types_of(n):
    t = n.get("@type")
    if isinstance(t, str):
        return {t}
    if isinstance(t, list):
        return {x for x in t if isinstance(x, str)}
    return set()


def num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = re.sub(r"[^0-9.,]", "", v)
        if not s:
            return None
        if "," in s and "." in s:
            s = s.replace(",", "") if s.rfind(".") > s.rfind(",") else s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".") if len(s.split(",")[-1]) in (1, 2) else s.replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None
    return None


def offer_price(o):
    if isinstance(o, list):
        return any(offer_price(x) for x in o)
    if not isinstance(o, dict):
        return False
    for k in ("price", "lowPrice", "highPrice"):
        v = num(o.get(k))
        if v and v > 0:
            return True
    ps = o.get("priceSpecification")
    if isinstance(ps, (dict, list)) and offer_price(ps):
        return True
    return offer_price(o.get("offers")) if "offers" in o else False


def nonempty_str(v):
    return isinstance(v, str) and v.strip() != ""


def brand_ok(v):
    if nonempty_str(v):
        return True
    if isinstance(v, dict):
        return nonempty_str(v.get("name"))
    if isinstance(v, list):
        return any(brand_ok(x) for x in v)
    return False


def image_ok(v):
    if nonempty_str(v):
        return True
    if isinstance(v, dict):
        return nonempty_str(v.get("url")) or nonempty_str(v.get("contentUrl"))
    if isinstance(v, list):
        return any(image_ok(x) for x in v)
    return False


def page_fields(txt):
    nodes = [n for n in ld_nodes(txt) if types_of(n) & {"Product", "ProductGroup", "IndividualProduct", "ProductModel"}]
    variants = []
    for n in nodes:
        hv = n.get("hasVariant")
        if isinstance(hv, list):
            variants.extend([v for v in hv if isinstance(v, dict)])
    allp = nodes + variants
    tm = TITLE_RE.search(txt)
    title = htmlmod.unescape(re.sub(r"\s+", " ", tm.group(1))).strip() if tm else ""
    ogm = OGT_RE.search(txt)
    ogt = htmlmod.unescape(ogm.group(1)).strip() if ogm else ""
    names = [n.get("name") for n in allp if nonempty_str(n.get("name"))]
    return {
        "jsonld_product": bool(nodes),
        "jsonld_name": bool(names),
        "jsonld_brand": any(brand_ok(n.get("brand")) for n in allp),
        "jsonld_image": any(image_ok(n.get("image")) for n in allp),
        "jsonld_offers_price": any(offer_price(n.get("offers")) for n in allp),
        "size_in_title": bool(SIZE_ANY_RE.search(title)),
        "_title": title, "_ogt": ogt, "_names": names[:3],
    }


AR_ATR = chr(0x0639) + chr(0x0637) + chr(0x0631)  # the Arabic word for perfume
AR_ML = chr(0x0645) + chr(0x0644)  # the Arabic ml abbreviation (also the prefix of the spelled-out unit)
FRAG_WORD_ML_RE = re.compile(r"\b(woda perfumowana|woda toaletowa|perfumy|profumo|perfumes?)\b|" + AR_ATR, re.I)
SIZE_ANY_RE = re.compile(r"\d+(?:[.,]\d+)?\s*(?:ml\b|fl\.?\s*oz\b|oz\b|" + AR_ML + ")", re.I)


def frag_content(fields, url):
    # store names ride after the first ' | ' of a <title>, so only the head of the title is read
    title_head = re.split(r"\s+\|\s+", fields["_title"])[0]
    path = re.sub(r"^https?://[^/]+", "", url or "")
    path = re.sub(r"%[0-9A-Fa-f]{2}", " ", path)
    path = re.sub(r"[-_/.?=&]+", " ", path)
    text = " ".join([title_head, fields["_ogt"], path] + [n for n in fields["_names"] if isinstance(n, str)])
    if extract_concentration(text) or FRAG_WORD_RE.search(text) or FRAG_WORD_ML_RE.search(text):
        return True
    low = text.lower()
    if SIZE_ANY_RE.search(text) and any(re.search(r"\b" + re.escape(b) + r"\b", low) for b in FRAGRANCE_BRAND_KEYWORDS):
        return True
    return False


PF = ("jsonld_product", "jsonld_name", "jsonld_brand", "jsonld_image", "jsonld_offers_price", "size_in_title")


def host_of(u):
    h = re.sub(r"^https?://", "", u or "").split("/")[0].lower()
    return h[4:] if h.startswith("www.") else h


def summarise(pages):
    hosts = {}
    for p in pages:
        h = hosts.setdefault(p["host"], {"host": p["host"], "n_pdps": 0, **{f: 0 for f in PF}})
        h["n_pdps"] += 1
        for f in PF:
            h[f] += 1 if p[f] else 0
    tot = {"n_pdps": len(pages), "n_hosts": len(hosts), **{f: sum(1 for p in pages if p[f]) for f in PF}}
    tot.update({f + "_rate": round(tot[f] / len(pages), 4) if pages else None for f in PF})
    return tot, sorted(hosts.values(), key=lambda x: (-x["n_pdps"], x["host"]))


# Gulf corpus
gulf_rows = [json.loads(l) for l in open(os.path.join(PROOF, "sweep2_curl_cffi.jsonl"), encoding="utf-8") if l.strip()]
gulf_pages, gulf_missing = [], 0
for r in gulf_rows:
    if not isinstance(r.get("url"), str):
        gulf_missing += 1
        continue
    f = os.path.join(PROOF, "html", hashlib.sha1((r.get("channel", "curl_cffi") + "|" + r["url"]).encode()).hexdigest() + ".html")
    if not os.path.exists(f):
        gulf_missing += 1
        continue
    txt = open(f, encoding="utf-8", errors="ignore").read()
    fl = page_fields(txt)
    gulf_pages.append({"host": host_of(r.get("final_url") or r["url"]), "flag_is_fragrance": r.get("is_fragrance") is True,
                       "blocked_recorded": r.get("structurally_blocked") is True or r.get("status") != 200,
                       "content_fragrance": frag_content(fl, r["url"]), **{k: fl[k] for k in PF}})
# Global corpus
cm = json.load(open(os.path.join(PROOF, "global", "_corpus_cachemap.json"), encoding="utf-8"))["rows"]
glob_pages, glob_missing = [], 0
for r in cm:
    cp = r.get("_cache_path")
    path = None
    if cp:
        base = os.path.basename(cp.replace("\\", "/"))
        sub = os.path.basename(os.path.dirname(cp.replace("\\", "/")))
        cand = os.path.join(PROOF, "global", sub, base)
        if os.path.exists(cand):
            path = cand
    if path is None:
        glob_missing += 1
        continue
    txt = open(path, encoding="utf-8", errors="ignore").read()
    fl = page_fields(txt)
    glob_pages.append({"host": host_of(r.get("final_url") or r["url"]), "region": r.get("region"),
                       "blocked_recorded": r.get("blocked") is True or r.get("http_status") != 200,
                       "content_fragrance": frag_content(fl, r["url"]), **{k: fl[k] for k in PF}})

g_flag = [p for p in gulf_pages if p["flag_is_fragrance"]]
g_content = [p for p in gulf_pages if p["content_fragrance"]]
gl_content = [p for p in glob_pages if p["content_fragrance"]]
gfs, gfh = summarise(g_flag)
gcs, gch = summarise(g_content)
gls, glh = summarise(gl_content)
gfs["unblocked_subset"] = summarise([p for p in g_flag if not p["blocked_recorded"]])[0]
gcs["unblocked_subset"] = summarise([p for p in g_content if not p["blocked_recorded"]])[0]
gls["unblocked_subset"] = summarise([p for p in gl_content if not p["blocked_recorded"]])[0]
BLOCK_DEF = "unblocked_subset drops pages the corpus index records as blocked (gulf: structurally_blocked or status != 200; global: blocked or http_status != 200)"

result = {
    "unit": "S81-02 held fragrance juices (zero network) + corpus fragrance PDP field presence",
    "generated": "2026-10-22",
    "code_root": ROOT.replace("\\", "/"),
    "code_root_sha": "95cf6f864b4e70980ca191daa064c0118e223c13",
    "guards": {"net_calls_attempted": NET, "env_names_added_by_import": ENV_ADDED, "dotenv": "stubbed (no .env read)"},
    "key_definition": {
        "key": "brand|line|concentration = fields 2-4 of app/services/spec_spine_service.py::spine_key(brand, line, None, 'fragrances') (the ml field is dropped); imported, pure function",
        "brand_split": "spine_key needs brand and name separately and the held sources carry one free-text string; the brand is the longest entry of the documented BRANDS list in scripts/held_fragrances.py matching the start of the string (case-insensitive); unmatched strings get brand '' (brand_resolved false)",
        "side_split": "a 'A vs B' query contributes both sides; a single-product query contributes itself",
        "concentration_absent": "'-' when the text names no concentration (spine_key convention); the same line with and without a concentration is two keys",
        "tag": "keys measured by the repo function; the brand split is a documented normalisation",
    },
    "sources": {
        "data/validation_gold_truth.json": {"fragrance_queries": len(gold_frag), "sides": sum(len(sides(q["query"])) for q in gold_frag), "distinct_keys": len(per_source("data/validation_gold_truth.json")), "tag": "measured"},
        "data/warmer_catalog.json": {"fragrance_queries": len(warm_frag), "sides": sum(len(sides(q["query"])) for q in warm_frag), "distinct_keys": len(per_source("data/warmer_catalog.json")), "tag": "measured"},
        "data/trending_curated.json": {"fragrance_rows": trend_rows, "sides": trend_rows * 2, "distinct_keys": len(per_source("data/trending_curated.json")), "tag": "measured"},
        "data/eval_smoke_subset.json": {"fragrance_ids": smoke_frag, "distinct_keys": len(per_source("data/eval_smoke_subset.json")), "new_keys_vs_gold": len(set(per_source("data/eval_smoke_subset.json")) - set(per_source("data/validation_gold_truth.json"))), "tag": "measured"},
    },
    "distinct_juice_count": {"value": len(keys), "unit": "distinct brand|line|concentration keys across the four sources", "tag": "measured"},
    "distinct_brand_line_count": {"value": len(bl), "unit": "distinct brand|line (concentration collapsed)", "tag": "measured"},
    "keys": [{"key": k, "texts": sorted(by_key[k]["texts"]), "sources": sorted(by_key[k]["sources"])} for k in keys],
    "inferred_distinct_juice_count": {"value": len(inferred_groups), "folds": inferred_folds,
                                      "rule": "a no-concentration key folds into the same brand|line with a concentration; MFK = Maison Francis Kurkdjian; 1 Million = One Million; flankers kept apart",
                                      "tag": "inferred"},
    "near_duplicate_pairs_not_folded_by_spine_key": {"pairs": near, "tag": "inferred (token subset or equal identity; possible same juice spelled two ways or a flanker)"},
    "unresolved_brand_texts": sorted({e["text"] for e in entries if not e["brand_resolved"]}),
    "empty_identity_keys": sorted({e["key"] for e in entries if e["key"].split("|")[1] == ""}),
    "entries": entries,
    "fixture_response_fragrance_keys_not_in_the_four_sources": {"keys": fixture_new, "source": "baseline_completeness.json fragrance_by_content products (lane1, comparison_baseline_d2*, w412)", "tag": "measured, not counted in distinct_juice_count"},
    "corpora": {
        "gulf": {
            "index": "sc-scraper-proof/_proof/sweep2_curl_cffi.jsonl (%d rows), html = sha1('curl_cffi|'+url) under _proof/html" % len(gulf_rows),
            "pages_with_cached_html": len(gulf_pages), "rows_without_html": gulf_missing,
            "fragrance_by_index_flag": {"definition": "sweep2 row is_fragrance == True (recorded by the 2026-08 sweep)", "totals": gfs, "by_host": gfh},
            "fragrance_by_content": {"definition": "inferred: the <title> head (before the first ' | '), og:title, the URL path or a JSON-LD Product name carries a concentration phrase (price_service.extract_concentration), a perfume word (EN/FR/ES/PT/PL perfume|parfum|cologne|woda perfumowana|woda toaletowa|perfumy|profumo, or the Arabic word for perfume), or an ml/oz/Arabic-ml size token together with a FRAGRANCE_BRAND_KEYWORDS brand; recall is imperfect (a fragrance page naming none of these, e.g. a bare line name, is missed)", "totals": gcs, "by_host": gch},
        },
        "global": {
            "index": "sc-scraper-proof/_proof/global/_corpus_cachemap.json (%d rows; corpus.json n_rows 328), html = each row's _cache_path" % len(cm),
            "pages_with_cached_html": len(glob_pages), "rows_without_html": glob_missing,
            "fragrance_by_content": {"definition": "as gulf fragrance_by_content (the global corpus has no is_fragrance flag)", "totals": gls, "by_host": glh},
        },
        "blocked_split": BLOCK_DEF,
        "field_definitions": {
            "jsonld_product": "a parseable application/ld+json block holds a node typed Product/ProductGroup/IndividualProduct/ProductModel",
            "jsonld_name": "a non-empty name on such a node or a hasVariant child",
            "jsonld_brand": "brand as a non-empty string, or a dict/list carrying a non-empty name",
            "jsonld_image": "image as a non-empty string, or a dict url/contentUrl, or a list holding one",
            "jsonld_offers_price": "offers (dict or list, nested offers / priceSpecification included) with price/lowPrice/highPrice parsing to a number > 0",
            "size_in_title": "the page <title> carries a number + ml / fl oz / oz / Arabic-ml token",
            "tag": "measured from the cached HTML bytes, zero network",
        },
    },
}
with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(result, fh, indent=1, ensure_ascii=True)
    fh.write("\n")
print("juices", len(keys), "brand_line", len(bl), "near", len(near), "unresolved", result["unresolved_brand_texts"])
print("gulf pages", len(gulf_pages), "missing", gulf_missing, "flag_frag", gfs["n_pdps"], gfs["n_hosts"], "content_frag", gcs["n_pdps"], gcs["n_hosts"])
print("global pages", len(glob_pages), "missing", glob_missing, "content_frag", gls["n_pdps"], gls["n_hosts"])
print("gulf flag totals", {k: v for k, v in gfs.items() if k.endswith("_rate")})
print("global totals", {k: v for k, v in gls.items() if k.endswith("_rate")})
print("net", NET, "env", ENV_ADDED)
