"""S81-02: fragrance rows of data/bh_gcc_sources.json (read-only, no import of app code).
argv[1] = code root, argv[2] = output json."""
import json
import os
import re
import sys
from collections import Counter

ROOT, OUT = sys.argv[1], sys.argv[2]
REG = "data/bh_gcc_sources.json"
DESC = "data/search_descriptors.json"
rows = json.load(open(os.path.join(ROOT, REG), encoding="utf-8"))
desc = json.load(open(os.path.join(ROOT, DESC), encoding="utf-8"))
dh = desc.get("hosts") or {}

# literal registry rows (source_router._LITERAL_ROWS) shadow a catalog row on the same apex
src = open(os.path.join(ROOT, "app", "services", "source_router.py"), encoding="utf-8").read()
start = src.index("_LITERAL_ROWS: List[Source] = [")
end = src.index("\n]\n", start)
lit_block = src[start:end]
literal_domains = sorted(set(re.findall(r'Source\(\s*"([^"]+)"', lit_block)))

FEED = ("woo_store_json", "shopify", "salla_api", "magento_graphql", "algolia")


def norm(d):
    d = d.lower()
    return d[4:] if d.startswith("www.") else d


def shadowed(d):
    d = norm(d)
    return any(d == norm(l) or d.endswith("." + norm(l)) for l in literal_domains)


def descriptor(d):
    e = dh.get(d) or dh.get(norm(d))
    return e if isinstance(e, dict) else None


frag = [r for r in rows if "fragrances" in (r.get("categories") or [])]
live = [r for r in frag if r.get("status") == "live"]


def tier_order(r):
    return (0 if r.get("tier") == "bahrain" else 1, 0 if r.get("country") == "BH" else 1, r.get("priority_rank") or 9999, r.get("domain"))


def row_view(r):
    d = descriptor(r["domain"])
    return {
        "domain": r["domain"], "tier": r.get("tier"), "country": r.get("country"), "currency": r.get("currency"),
        "mechanism": r.get("mechanism") or "", "genuine_method": r.get("genuine_method") or "",
        "is_render_only": r.get("is_render_only"), "is_shopify": r.get("is_shopify"), "is_algolia": r.get("is_algolia"),
        "priority_rank": r.get("priority_rank"),
        "row_search_key_present": "search" in r,
        "row_search_kind": (r.get("search") or {}).get("kind") if isinstance(r.get("search"), dict) else None,
        "descriptor_in_search_descriptors_json": d is not None,
        "descriptor_kind": d.get("kind") if d else None,
        "descriptor_has_q_template": bool(d and "{q}" in (d.get("url_template") or "")),
        "descriptor_robots_allowed": d.get("robots_allowed") if d else None,
        "shadowed_by_literal_row": shadowed(r["domain"]),
    }


live_v = [row_view(r) for r in sorted(live, key=tier_order)]
feed_v = [v for v in live_v if v["mechanism"] in FEED]
nomech_v = [v for v in live_v if v["mechanism"] == ""]
other_mech = [v for v in live_v if v["mechanism"] and v["mechanism"] not in FEED]

res = {
    "unit": "S81-02 registry fragrance rows",
    "generated": "2026-10-22",
    "source_file": REG,
    "code_root_sha": "95cf6f864b4e70980ca191daa064c0118e223c13",
    "registry_rows_total": {"value": len(rows), "file": REG, "tag": "measured"},
    "fragrance_rows_total": {"value": len(frag), "by_status": dict(Counter(r.get("status") for r in frag)), "file": REG, "tag": "measured"},
    "fragrance_rows_by_status_and_mechanism": {"value": {"%s|%s" % k: v for k, v in sorted(Counter((r.get("status"), r.get("mechanism") or "") for r in frag).items())}, "file": REG, "tag": "measured"},
    "live_fragrance_rows": {"value": len(live), "file": REG, "tag": "measured",
                            "by_mechanism": dict(Counter(v["mechanism"] for v in live_v)),
                            "by_country": dict(Counter(v["country"] for v in live_v)),
                            "by_currency": dict(Counter(v["currency"] for v in live_v)),
                            "by_tier": dict(Counter(v["tier"] for v in live_v)),
                            "by_genuine_method": dict(Counter(v["genuine_method"] for v in live_v)),
                            "with_row_search_key": sum(1 for v in live_v if v["row_search_key_present"]),
                            "with_descriptor_in_search_descriptors_json": sum(1 for v in live_v if v["descriptor_in_search_descriptors_json"]),
                            "with_descriptor_q_template": sum(1 for v in live_v if v["descriptor_has_q_template"]),
                            "descriptor_robots_allowed_true": sum(1 for v in live_v if v["descriptor_robots_allowed"] is True),
                            "shadowed_by_literal_row": sum(1 for v in live_v if v["shadowed_by_literal_row"])},
    "live_feed_hosts": {
        "definition": "live fragrance rows whose mechanism is one of %s, Bahrain tier first then country BH, then priority_rank" % (", ".join(FEED),),
        "count": len(feed_v), "by_mechanism": dict(Counter(v["mechanism"] for v in feed_v)),
        "bahrain_tier_count": sum(1 for v in feed_v if v["tier"] == "bahrain"),
        "hosts": feed_v, "file": REG, "tag": "measured"},
    "live_other_mechanism_hosts": {"count": len(other_mech), "hosts": other_mech, "file": REG, "tag": "measured"},
    "live_hosts_with_no_mechanism": {
        "definition": "live fragrance rows with mechanism '' (served by the generic page-scrape path; genuine_method recorded)",
        "count": len(nomech_v), "by_genuine_method": dict(Counter(v["genuine_method"] for v in nomech_v)),
        "bahrain_tier_count": sum(1 for v in nomech_v if v["tier"] == "bahrain"),
        "with_descriptor_q_template": sum(1 for v in nomech_v if v["descriptor_has_q_template"]),
        "hosts": nomech_v, "file": REG, "tag": "measured"},
    "live_rows_country_currency_mismatch": {
        "definition": "live fragrance rows whose currency is not the national currency of their country (BH BHD, UAE AED, KSA SAR, QA QAR, OM OMR, KW KWD) or whose tier 'bahrain' disagrees with country != BH",
        "rows": [{"domain": v["domain"], "tier": v["tier"], "country": v["country"], "currency": v["currency"], "mechanism": v["mechanism"]}
                 for v in live_v if {"BH": "BHD", "UAE": "AED", "KSA": "SAR", "QA": "QAR", "OM": "OMR", "KW": "KWD"}.get(v["country"]) != v["currency"] or (v["tier"] == "bahrain") != (v["country"] == "BH")],
        "file": REG, "tag": "measured"},
    "search_descriptors_json": {"hosts": len(dh), "updated": desc.get("_updated"), "file": DESC, "tag": "measured"},
    "literal_rows": {"domains": literal_domains, "count": len(literal_domains), "file": "app/services/source_router.py (_LITERAL_ROWS)", "tag": "measured"},
    "caveats": [
        "the catalog rows load only when ENABLE_BH_GCC_CATALOG_SOURCES is on (source_router._load_catalog_rows); its production state is not read here (CLAUDE.md records it ON since 2026-06-26, not a session-81 ledger line)",
        "a catalog row whose apex a literal row covers is skipped at load (shadowed_by_literal_row)",
        "status 'live' is the registry's own recorded liveness (scripts/verify_bh_gcc_sources.py), not re-measured; zero network here",
        "the search descriptor is read at runtime only behind ENABLE_SEARCH_DESCRIPTOR",
    ],
}
with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(res, fh, indent=1, ensure_ascii=True)
    fh.write("\n")
print("frag", len(frag), "live", len(live), "feed", len(feed_v), dict(Counter(v["mechanism"] for v in feed_v)), "bh_feed", res["live_feed_hosts"]["bahrain_tier_count"], "nomech", len(nomech_v), "other", len(other_mech), "shadowed", res["live_fragrance_rows"]["shadowed_by_literal_row"], "desc", res["live_fragrance_rows"]["with_descriptor_in_search_descriptors_json"], "q", res["live_fragrance_rows"]["with_descriptor_q_template"], "lits", len(literal_domains))
