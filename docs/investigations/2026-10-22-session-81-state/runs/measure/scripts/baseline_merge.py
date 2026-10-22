"""Compare pass A and pass B record by record and tally by tally; write the deliverable.
argv[1] = pass A json, argv[2] = pass B json, argv[3] = output deliverable json."""
import hashlib
import json
import sys

A = json.load(open(sys.argv[1], encoding="utf-8"))
B = json.load(open(sys.argv[2], encoding="utf-8"))
OUT = sys.argv[3]

FIELDS = ["identity", "image_url", "price_not_estimated", "size", "concentration", "specs", "specs_count", "rating_real", "review_count", "price_has_timestamp", "pair_fragrance_stored", "pair_fragrance_content"]

ka = {(r["source"], r["index"]): r for r in A["products"]}
kb = {(r["source"], r["index"]): r for r in B["products"]}
disc = []
for k in sorted(set(ka) | set(kb)):
    if k not in ka or k not in kb:
        disc.append({"key": list(k), "issue": "present in only one pass", "in_a": k in ka, "in_b": k in kb})
        continue
    for f in FIELDS:
        if ka[k].get(f) != kb[k].get(f):
            disc.append({"key": list(k), "field": f, "a": ka[k].get(f), "b": kb[k].get(f)})

tally_disc = []
for sec in ("overall", "fragrance_by_content", "fragrance_by_stored_category"):
    for f, v in A[sec].items():
        if isinstance(v, dict) and "product_present" in v:
            bv = B[sec].get(f)
            for kk in ("product_present", "product_n", "pair_both_present", "pair_n"):
                if bv is None or bv.get(kk) != v[kk]:
                    tally_disc.append({"section": sec, "field": f, "key": kk, "a": v[kk], "b": None if bv is None else bv.get(kk)})
    sa = sum(r["specs_count"] for r in A["products"] if sec == "overall" or r["pair_" + ("fragrance_content" if sec == "fragrance_by_content" else "fragrance_stored")])
    if sa != B[sec]["specs_count_sum"]:
        tally_disc.append({"section": sec, "field": "specs_count_sum", "a": sa, "b": B[sec]["specs_count_sum"]})
ex_a = sorted(e["source"] for e in A["excluded"])
ex_b = sorted(B["excluded"])
if ex_a != ex_b:
    tally_disc.append({"section": "excluded", "a": ex_a, "b": ex_b})

DEFS = {
    "unit_of_count": "product = one of the two products of one stored comparison response; pair = one stored response (both products). Repeated captures of the same query are counted as separate observations (w412 rows 3-5, 12-13, 15-25 repeat pairs).",
    "product_source": "the RAW top-level products[] alias (result_gate._raw_products), image_url from overview.products[i] then products[i] (result_gate._image_present order), specs from specs.products[i].specs then products[i].specs (result_gate._specs_of)",
    "identity": "present = NOT result_gate.product_is_placeholder (normalised brand+name dedup and name alone not in {'', unknown, unknown product, n/a, product, this product})",
    "image_url": "present = string starting https:// with a dotted host, path not .svg/.svgz, no placeholder token (placeholder, no-image, noimage, no_image, default-image). Extension recorded in image_ext_counts (tif counted as raster).",
    "price_not_estimated": "present = price.amount a real number > 0 AND price.unavailable is not True AND price.estimated is not True AND price.source_method != 'estimated' (result_gate.price_is_present_literal plus amount > 0). source_method and timestamp presence recorded per product.",
    "price_timestamp": "price dict carries any of retrieved_at, fetched_at, timestamp, as_of, scraped_at, updated_at, observed_at, captured_at, price_ts, last_seen, checked_at. (Response-level metadata.timestamp is recorded per pair separately.)",
    "price_url_kind": "search_page = url contains google.com/search, /search, ?q=, &q=, ?s=, ?kw= or search?; pdp_or_other = any other non-empty url; none = no url",
    "size": "present = price.size non-NA, or a specs key in {volume,size,net_volume,net_content,net_weight,count,capacity,storage,pack_size,quantity} non-NA, or a size token (number + ml/l/oz/g/kg/gb/tb/tablets/capsules/softgels/count/ct/pcs/sachets) in name/full_name/variant",
    "concentration": "fragrance pairs only: specs.concentration or price.concentration non-NA, or a concentration phrase (extrait, parfum intense, eau de parfum/EDP, eau de toilette/EDT, eau de cologne/EDC, eau fraiche, parfum) in name/full_name/variant",
    "specs": "specs_count = result_gate.real_spec_rows_one_side (string keys not starting with _, value not in NA {'', n/a, na, none, unknown, -}); present = count >= 1",
    "rating_real": "present = rating a real number in (0,5], rating_derived is not True (result_gate.rating_is_real), rating_source is a dict with a non-empty name and extract_method not in {gpt_review_aggregate, derive_rating_from_scores, derived, estimated}",
    "review_count": "present = review_count a real number > 0",
    "fragrance_by_stored_category": "pair whose stored response category (category or category_used) is 'fragrances', or both products' stored category is 'fragrances'",
    "fragrance_by_content": "INFERRED classification over MEASURED fields: stored-fragrance pairs plus pairs where either product has a concentration phrase or perfume word in brand/name/full_name/variant, or a FRAGRANCE_BRAND_KEYWORDS brand (app/services/price_service.py) together with an ml/oz size token, or >= 2 populated fragrance spec keys (scent_family, notes_top/heart/base, longevity, sillage, concentration). Catches w412 rows 20-25 (Tom Ford perfumes stored as category 'other').",
    "pair_rate": "pair_both_present / pair_n where a pair counts only when BOTH products have the field present",
    "tags": "every count and rate in this file is measured from the fixture bytes at the code root; only the fragrance_by_content membership rule is an inferred classification",
}

result = {
    "unit": "S81-02 MEAS-ZERO + COMPLETENESS-BASELINE (the 'before')",
    "generated": "2026-10-22",
    "code_root": A["code_root"],
    "code_root_sha": "95cf6f864b4e70980ca191daa064c0118e223c13",
    "inputs": A["inputs"],
    "n_stored_responses_read": A["n_responses_read"],
    "excluded": A["excluded"],
    "definitions": DEFS,
    "headline_fragrance_pairs_by_content": {f: {"pair_rate": A["fragrance_by_content"][f]["pair_rate"], "pair_both_present": A["fragrance_by_content"][f]["pair_both_present"], "pair_n": A["fragrance_by_content"][f]["pair_n"], "product_rate": A["fragrance_by_content"][f]["product_rate"], "product_n": A["fragrance_by_content"][f]["product_n"], "tag": "measured"} for f in ("identity", "image_url", "price_not_estimated", "rating_real")},
    "overall": A["overall"],
    "fragrance_by_content": A["fragrance_by_content"],
    "fragrance_by_stored_category": A["fragrance_by_stored_category"],
    "second_pass": {
        "method": "scripts/baseline_b.py: no app.* import; walks tests/fixtures and detects full-response shapes structurally; own normaliser, own concentration regex, FRAGRANCE_BRAND_KEYWORDS read from price_service.py source via ast; compared record by record (12 fields x every product) and tally by tally by scripts/baseline_merge.py",
        "pass_a_script": "scripts/baseline_a.py (imports app.services.result_gate predicates and price_service.extract_concentration behind a dotenv stub and a socket deny guard; net calls attempted: %d)" % len(A["net_calls_attempted"]),
        "products_compared": len(set(ka) & set(kb)),
        "record_discrepancies": disc,
        "tally_discrepancies": tally_disc,
        "agree_exactly": not disc and not tally_disc,
        "pass_b_file": "baseline_completeness_pass2.json",
    },
    "pairs": A["pairs"],
    "products": A["products"],
}
with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(result, fh, indent=1, ensure_ascii=True)
    fh.write("\n")
print("agree_exactly", result["second_pass"]["agree_exactly"], "record_disc", len(disc), "tally_disc", len(tally_disc))
for d in (disc + tally_disc)[:20]:
    print(d)
