"""S81-16 KB-SEED-BATCH: one Haiku Message Batch over the held corpus pages.

ENABLE_KB_SEED (read per call, the FIRST statement of ``main``):
unset / false / garbage -> OFF (one INFO line, exit 0, nothing read);
true / 1 / yes / on -> DRY RUN (corpus + registry read, counts, the USD bound
and the request shape; nothing is sent anywhere);
apply -> ONE batch (thinking disabled, a JSON-schema output, max_tokens 2048),
then cited kb_specs rows plus the kb_products / kb_variants identity rows
(S81-14 builder outputs, insert-ignore). Never kb_offers, never kb_images.

Spend: the in-script bound KB_SEED_MAX_USD (at most 10) is checked before any
submission whatever the breaker state; with ENABLE_LLM_SPEND_BREAKER ON the
offclock lane is reserved strictly before the create and settled after the
results (recorded instead when the reserve failed open); one llm_spend_ledger
row per batch, written only after a complete results read (a partial read
settles the ticket with None, so the bound stays held, and writes no ledger
row; the later --resume writes it once). ``--resume <batch id>`` re-derives
the juice set WITHOUT the existing-specs filter and the juice cap (R-G2-6
governs fresh runs only), reads the batch again completely (no bound check,
no reserve, no create), writes the ONE ledger row, the rows (insert-ignore;
a juice that already owns kb_seed_batch rows counts ``already_seeded``) and
deletes the batch after the writes.
"""
from __future__ import annotations

import os

# The key snapshot BEFORE any app import (the seed_spec_spine rule: an app import
# runs load_dotenv(override=True)). Read only in APPLY; never logged, never in
# the report, never in a request payload.
_STARTUP_ANTHROPIC_KEY = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import logging  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from typing import Any, Dict, List, Optional, Tuple  # noqa: E402
from urllib.parse import urlsplit  # noqa: E402

from scripts import kb_seed_common as common  # noqa: E402

logger = logging.getLogger("seed_kb_batch")

FLAG = "ENABLE_KB_SEED"
PREFIX = "[KB_SEED]"
EXTRACTOR = "kb_seed_batch"
ROLE = "kb_seed"
MAX_TOKENS = 2048
EXISTING_CHUNK = 100
USAGE_LOG_ROWS = 20
SEED_FIELDS = (
    "scent_family", "notes_top", "notes_heart", "notes_base", "longevity", "sillage",
    "season", "occasion", "launch_year", "perfumer", "audience",
)
SEED_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["fields"],
    "properties": {"fields": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["field", "value", "snippet"],
        "properties": {"field": {"type": "string", "enum": list(SEED_FIELDS)},
                       "value": {"type": "string"}, "snippet": {"type": "integer"}}}}},
}
# GATE_S81_G2 GC-1: this sentence, the system composition and the digest / user
# layouts below are pinned byte-for-byte by tests/fixtures/s81_s16_batch_request_golden.json.
SEED_RULES = (
    "SEED RULES: return only the fields a numbered page states; each field carries the "
    "1-based page number in 'snippet'; omit every field no page states."
)
_EMPTY_VALUES = ("n/a", "na", "null", "none", "unknown")
_URL_RE = re.compile(r"https?://[^\s\"'<>)]+", re.I)
_YEAR_RE = re.compile(r"^(17|18|19|20)[0-9]{2}$")
_GTIN_KEYS = ("gtin13", "gtin", "gtin12", "gtin14", "gtin8")
VALUE_MAX = 2000


def kb_seed_mode() -> str:
    return common.run_mode(FLAG)


# --- seams (module attributes read at call time) ----------------------------

def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _now():
    return common._now()


def _anthropic_factory(**kw: Any) -> Any:
    import importlib

    return importlib.import_module("anthropic").Anthropic(**kw)


def _say(msg: str, *args: Any) -> None:
    logger.info(PREFIX + " " + msg, *args)


# --- knobs -------------------------------------------------------------------

def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="seed_kb_batch")
    p.add_argument("--corpus", action="append", default=[])
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--report", default=None)
    p.add_argument("--resume", default=None)
    return p.parse_args(argv if argv is not None else [])


def corpus_dirs(args: argparse.Namespace) -> List[str]:
    """--corpus (repeatable), else KB_SEED_CORPUS_DIRS (os.pathsep-separated; no
    default)."""
    if args.corpus:
        return list(args.corpus)
    raw = os.getenv("KB_SEED_CORPUS_DIRS") or ""
    return [d for d in raw.split(os.pathsep) if d.strip()]


def max_usd() -> float:
    return common.float_knob("KB_SEED_MAX_USD", 10.0, 0.0, 10.0)


def max_juices() -> int:
    return common.int_knob("KB_SEED_MAX_JUICES", 500, 1, 10000)


def poll_seconds() -> int:
    return common.int_knob("KB_SEED_POLL_SECONDS", 60, 10, 600)


def max_wait_seconds() -> int:
    return common.int_knob("KB_SEED_MAX_WAIT_SECONDS", 21600, 60, 86400)


def custom_id(pid: str) -> str:
    return "j" + hashlib.sha256(pid.encode("utf-8")).hexdigest()[:40]


# --- the corpus --------------------------------------------------------------

def _page_gtins(html: str) -> List[str]:
    """The gtin values of the page's first JSON-LD Product node (unchecked)."""
    from scripts import seed_spec_spine as ssp

    out: List[str] = []
    try:
        for node in ssp._iter_jsonld_nodes(html):
            if not ssp._is_product(node):
                continue
            for key in _GTIN_KEYS:
                val = node.get(key)
                if isinstance(val, (str, int)) and not isinstance(val, bool):
                    out.append(str(val).strip())
            break
    except Exception:  # noqa: BLE001 - a malformed node yields no gtin
        return out
    return out


def _page_host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def collect(dirs: List[str], by_host: Dict[str, Any], now: Any, counts: Dict[str, int]) -> Dict[str, Dict[str, Any]]:
    """The candidate juices {pid: {"brand", "name", "pages": [...]}} in sorted
    file order (the page rule: no deny-host link anywhere on the page, a
    seed_spec_spine candidate, a live registry row whose persisted robots record
    allows the page URL on its own origin, a minted product id)."""
    from app.services import deny_hosts as dh
    from scripts import seed_spec_spine as ssp

    kb = common.kb_leaf()
    juices: Dict[str, Dict[str, Any]] = {}
    for directory in dirs:
        for path in ssp.iter_corpus_files(directory):
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    raw = fh.read()
            except OSError:
                common.bump(counts, "unreadable")
                continue
            if any(dh.is_denied_url(u) for u in _URL_RE.findall(raw)):
                common.bump(counts, "deny_link")
                continue
            page = ssp.parse_page(path)
            if not page:
                common.bump(counts, "not_candidate")
                continue
            url = page.get("url") or ""
            row = common.merchant_for_host(by_host, _page_host(url))
            reason = common.url_gate(row, url, now)
            if reason is not None:
                common.bump(counts, reason)
                continue
            pid = kb.kb_product_id(page["brand"], page["name"])
            if pid is None:
                common.bump(counts, "no_identity")
                continue
            entry = juices.setdefault(pid, {"brand": page["brand"], "name": page["name"], "pages": []})
            if len(entry["pages"]) < ssp.MAX_PAGES_PER_FRAGRANCE:
                page = dict(page)
                page["gtins"] = _page_gtins(raw)
                entry["pages"].append(page)
            common.bump(counts, "candidate")
    return juices


def existing_seeded(client: Any, pids: List[str]) -> set:
    """The juices that already own a kb_specs row written by THIS seeder (a row
    of another extractor never skips a juice: R-G2-6)."""
    found: set = set()
    for i in range(0, len(pids), EXISTING_CHUNK):
        chunk = pids[i:i + EXISTING_CHUNK]
        resp = (client.table(common.KB_SPECS_TABLE).select("product_id")
                .eq("extractor", EXTRACTOR).in_("product_id", chunk).execute())
        data = getattr(resp, "data", None)
        if not isinstance(data, list):
            raise TypeError("kb_specs read is not a list")
        found.update(r.get("product_id") for r in data if isinstance(r, dict))
    return found


# --- the request (GC-1: the strings and layouts are pinned) ------------------

def system_prompt() -> str:
    from app.services import extraction_service as es

    return es.SPECS_SYSTEM_STATIC_PREFIX_NO_FABRICATION + "\n\n" + es.SEARCH_RESULTS_GUARD + "\n\n" + SEED_RULES


def user_prompt(juice: Dict[str, Any]) -> str:
    from app.services import extraction_service as es
    from app.utils import prompt_sanitizer as ps

    digest = "\n\n".join(
        "[snippet_%d] %s\n%s" % (i, p.get("host") or "", ps.sanitize_untrusted_block(p.get("text") or ""))
        for i, p in enumerate(juice["pages"], start=1)
    )
    return ("<USER_INPUT>" + ps.sanitize_prompt_input(juice["brand"] + " " + juice["name"]) + "</USER_INPUT>\n\n"
            + es._wrap_search_context(digest))


def build_requests(juices: Dict[str, Dict[str, Any]], model: str) -> List[Dict[str, Any]]:
    system = system_prompt()
    out = []
    for pid in sorted(juices):
        out.append({"custom_id": custom_id(pid), "params": {
            "model": model, "max_tokens": MAX_TOKENS, "system": system,
            "messages": [{"role": "user", "content": user_prompt(juices[pid])}],
            "thinking": {"type": "disabled"},
            "output_config": {"format": {"type": "json_schema", "schema": SEED_SCHEMA}},
        }})
    return out


def request_bound(requests: List[Dict[str, Any]], model: str) -> float:
    """The sync-rate USD upper bound of every request (the breaker's own
    estimators; the conservative rate when the model is unpriced)."""
    from app.services import llm_spend_breaker as br

    total = 0.0
    for req in requests:
        params = req["params"]
        msgs = [{"role": "system", "content": params["system"]}] + list(params["messages"])
        pt = br.prompt_token_upper_bound(msgs, response_format=params["output_config"],
                                         provider="anthropic", model=model)
        bound = br.upper_bound_usd("anthropic", model, pt, MAX_TOKENS)
        if bound is None:
            bound = br.conservative_bound_usd("anthropic", pt, MAX_TOKENS)
        total += float(bound)
    return total


# --- results -> rows ---------------------------------------------------------

def valid_fields(payload: Any, n_pages: int, run_year: int, audiences: Any) -> Optional[List[Dict[str, Any]]]:
    """The cited fields of one answer; None when the answer is not the schema's
    shape (counted bad_json). A field without a valid page number, an empty
    value, a future or malformed year or an unknown audience is omitted."""
    if not isinstance(payload, dict) or not isinstance(payload.get("fields"), list):
        return None
    out = []
    for item in payload["fields"]:
        if not isinstance(item, dict):
            continue
        field, value, snippet = item.get("field"), item.get("value"), item.get("snippet")
        if field not in SEED_FIELDS:
            continue
        if not isinstance(snippet, int) or isinstance(snippet, bool) or not 1 <= snippet <= n_pages:
            continue
        if not isinstance(value, str):
            continue
        value = value.strip()
        if not 1 <= len(value) <= VALUE_MAX or value.lower() in _EMPTY_VALUES:
            continue
        if field == "launch_year" and (not _YEAR_RE.match(value) or int(value) > run_year):
            continue
        if field == "audience" and value not in audiences:
            continue
        out.append({"field": field, "value": value, "snippet": snippet})
    return out


def _lang(value: str) -> str:
    return "ar" if any(0x0600 <= ord(ch) <= 0x06FF for ch in value) else "en"


def juice_rows(pid: str, juice: Dict[str, Any], fields: List[Dict[str, Any]], model: str,
               observed: Any) -> Dict[str, Any]:
    """Builder rows for one juice: the product, its variants (a size or a valid
    gtin), one spec row per (field, lang), each citing its page URL."""
    from app.services import price_service as ps

    kb = common.kb_leaf()
    conc = pid.split("|")[3]
    conc = None if conc == "-" else conc
    first = juice["pages"][0]
    gtins = [g for p in juice["pages"] for g in p.get("gtins", []) if kb.gtin_check_digit_ok(g)]
    product = kb.build_product_row(id=pid, brand=first["brand"], name=first["name"],
                                   concentration=conc, identity_confidence="high" if gtins else "medium",
                                   updated_at=observed)
    variants: Dict[str, Dict[str, Any]] = {}
    for page in juice["pages"]:
        ml = ps.extract_size_ml_any(page.get("name") or "")
        ml = ml if isinstance(ml, int) and 1 <= ml <= 5000 else None
        gtin = next((g for g in page.get("gtins", []) if kb.gtin_check_digit_ok(g)), None)
        if ml is None and gtin is None:
            continue
        vid = kb.kb_variant_key(pid, conc, ml)
        if vid is None or vid in variants:
            continue
        row = kb.build_variant_row(id=vid, product_id=pid, concentration=conc, size_ml=ml, gtin=gtin,
                                   updated_at=observed)
        if row is not None:
            variants[vid] = row
    specs: Dict[Tuple[str, str], Dict[str, Any]] = {}
    refused = 0
    for f in fields:
        lang = _lang(f["value"])
        if (f["field"], lang) in specs:
            continue
        row = kb.build_spec_row(product_id=pid, field=f["field"], value=f["value"], extractor=EXTRACTOR,
                                model=model, cited=True, source_url=juice["pages"][f["snippet"] - 1]["url"],
                                lang=lang, captured_at=observed)
        if row is None:
            refused += 1
            continue
        specs[(f["field"], lang)] = row
    return {"products": [product] if product else [], "variants": list(variants.values()),
            "specs": list(specs.values()), "refused": refused + (0 if product else 1)}


def _g(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _answer(msg: Any) -> Any:
    """The parsed JSON of a succeeded message, None when truncated or unreadable."""
    try:
        if _g(msg, "stop_reason") == "max_tokens":
            return None
        return json.loads(_g(_g(msg, "content")[0], "text"))
    except Exception:  # noqa: BLE001 - counted bad_json by the caller
        return None


# --- the entry ---------------------------------------------------------------

def main(argv: Optional[List[str]] = None, client: Any = None) -> int:
    mode = kb_seed_mode()
    if mode == common.MODE_OFF:
        logger.info("%s mode=off ENABLE_KB_SEED not set; skipping run", PREFIX)
        return 0
    args = _parse_args(argv)
    mode = common.cli_mode(mode, args.dry_run)
    _say("mode=%s", mode)
    dirs = corpus_dirs(args)
    if not dirs:
        _say("no corpus")
        return 0
    client = common.resolve_client(client, PREFIX)
    if client is None:
        return 0
    try:
        rows = common.read_merchant_rows(client)
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s kb_merchants read failed (%s)", PREFIX, type(exc).__name__)
        return 0
    from app.services import model_config as mc

    model = mc.anthropic_model("text")
    observed = _now()
    counts: Dict[str, int] = {}
    juices = collect(dirs, common.rows_by_host(rows), observed, counts)
    try:
        done = existing_seeded(client, sorted(juices))
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s kb_specs read failed (%s)", PREFIX, type(exc).__name__)
        return 0
    if args.resume is None:
        kept = [pid for pid in sorted(juices) if pid not in done][:max_juices()]
    else:
        # F2-1: R-G2-6 (the seeded filter) and the juice cap govern FRESH runs
        # only; a resume sends nothing, its custom ids are fixed and the KB
        # upserts are insert-ignore, so it maps every juice of the corpus.
        kept = sorted(juices)
    counts["already_seeded"] = len(done & set(juices))
    juices = {pid: juices[pid] for pid in kept}
    counts["juices"] = len(juices)
    requests = build_requests(juices, model)
    common.write_report(args.report, {
        "requests": requests, "counts": counts,
        "juices": {custom_id(p): sorted({pg.get("host") or "" for pg in j["pages"]}) for p, j in juices.items()},
    })
    common.log_counts(PREFIX, counts)
    if not requests:
        _say("nothing to seed")
        return 0
    bound = request_bound(requests, model)
    if args.resume is None and bound > max_usd():
        _say("refused: bound=%.4f USD > KB_SEED_MAX_USD", bound)
        return 2
    _say("bound=%.4f USD requests=%d", bound, len(requests))
    if mode != common.MODE_APPLY:
        return 0
    key = _STARTUP_ANTHROPIC_KEY
    if not key:
        _say("no ANTHROPIC_API_KEY at startup; nothing sent")
        return 0
    seeded = frozenset(done) if args.resume is not None else frozenset()
    return _apply(args, client, requests, juices, model, bound, observed, key, seeded)


def _wait_ended(ac: Any, batch_id: Any) -> bool:
    """Poll every KB_SEED_POLL_SECONDS up to KB_SEED_MAX_WAIT_SECONDS."""
    waited = 0
    poll = poll_seconds()
    limit = max_wait_seconds()
    while True:
        if _g(ac.messages.batches.retrieve(batch_id), "processing_status") == "ended":
            return True
        if waited >= limit:
            return False
        _sleep(poll)
        waited += poll


def _read_results(ac: Any, batch_id: Any, juices: Dict[str, Dict[str, Any]], model: str, run_year: int,
                  counts: Dict[str, int], seeded: frozenset = frozenset(),
                  ) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]], bool]:
    """(fields per juice, usage records, read completed). A result whose
    custom_id maps to no juice is ``unmatched``, an unreadable answer
    ``bad_json``; neither writes nor raises. The usage of the first
    USAGE_LOG_ROWS rows is logged (ints only)."""
    from app.services import llm_pricing as lp

    kb = common.kb_leaf()
    by_cid = {custom_id(pid): pid for pid in juices}
    parsed: Dict[str, List[Dict[str, Any]]] = {}
    records: List[Dict[str, Any]] = []
    usage_lines = 0
    try:
        for item in ac.messages.batches.results(batch_id):
            result = _g(item, "result")
            rtype = _g(result, "type")
            if rtype != "succeeded":
                common.bump(counts, str(rtype or "unknown"))
                continue
            msg = _g(result, "message")
            usage = _g(msg, "usage")
            records.append(lp.anthropic_usage_record(model, usage, role=ROLE, batch=True))
            if usage_lines < USAGE_LOG_ROWS:
                usage_lines += 1
                logger.info("%s usage row=%d input=%d output=%d cache_read=%d", PREFIX, usage_lines,
                            int(_g(usage, "input_tokens", 0) or 0), int(_g(usage, "output_tokens", 0) or 0),
                            int(_g(usage, "cache_read_input_tokens", 0) or 0))
            pid = by_cid.get(_g(item, "custom_id"))
            if pid is None:
                common.bump(counts, "unmatched")
                continue
            if pid in seeded:
                common.bump(counts, "already_seeded")
            fields = valid_fields(_answer(msg), len(juices[pid]["pages"]), run_year, kb.KB_AUDIENCES)
            if fields is None:
                common.bump(counts, "bad_json")
                continue
            common.bump(counts, "succeeded")
            parsed[pid] = fields
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s results read failed (%s); resume with --resume batch_id=%s", PREFIX,
                       type(exc).__name__, batch_id)
        return parsed, records, False
    return parsed, records, True


def _apply(args: argparse.Namespace, client: Any, requests: List[Dict[str, Any]], juices: Dict[str, Dict[str, Any]],
           model: str, bound: float, observed: Any, key: str, seeded: frozenset = frozenset()) -> int:
    from app.services import api_budget_service as abs_
    from app.services import llm_pricing as lp
    from app.services import llm_router as lr
    from app.services import llm_spend_breaker as br
    from app.services import model_config as mc

    resume = args.resume
    breaker = (resume is None) and br.spend_breaker_enabled()
    ticket = None
    if breaker:
        try:
            ticket = br.reserve(br.LANE_OFFCLOCK, bound)
        except abs_.LLMUnavailableError:
            _say("refused: the spend breaker refused the reserve")
            return 2
    ac = _anthropic_factory(api_key=key, max_retries=mc.anthropic_max_retries(), base_url=lr.ANTHROPIC_BASE_URL)
    period_start = common._now()
    if resume is None:
        try:
            batch = ac.messages.batches.create(requests=requests)
        except Exception as exc:  # noqa: BLE001 - the reserve stays held (conservative)
            logger.warning("%s batch create failed (%s)", PREFIX, type(exc).__name__)
            return 0
        batch_id = _g(batch, "id")
        # The batch id is the provider's handle for --resume (not a credential).
        _say("submitted batch_id=%s", batch_id)
    else:
        batch_id = resume
    if not _wait_ended(ac, batch_id):
        logger.warning("%s batch not ended; resume with --resume batch_id=%s", PREFIX, batch_id)
        return 0
    counts: Dict[str, int] = {} if resume is None else {"already_seeded": 0, "unmatched": 0}
    parsed, records, results_ok = _read_results(ac, batch_id, juices, model, observed.year, counts, seeded)
    period_end = common._now()
    writer = common.KbWriter(client)
    # F1-1: the ONE ledger row per batch is written only after a COMPLETE results
    # read (a later --resume that completes the read writes it once).
    if results_ok:
        try:
            writer.ledger(lp.spend_ledger_row(job=EXTRACTOR, lane="offclock", mode="batch", provider="anthropic",
                                              model=model, records=records, role=ROLE,
                                              provider_batch_id=str(batch_id), period_start=period_start,
                                              period_end=period_end))
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s ledger insert failed (%s)", PREFIX, type(exc).__name__)
    if breaker and not results_ok:
        # A partial read: the bound stays held for its Riyadh day (an invalid
        # actual issues no command); a failed-open reserve records nothing.
        if ticket is not None:
            br.settle(ticket, None)
    elif breaker:
        costs = [r.get("cost_usd") for r in records]
        actual = None if any(c is None for c in costs) else float(sum(costs))
        if ticket is not None:
            br.settle(ticket, actual)
        else:
            br.record(br.LANE_OFFCLOCK, actual, admitted_usd=bound)
    out: Dict[str, List[Dict[str, Any]]] = {"products": [], "variants": [], "specs": []}
    for pid in sorted(parsed):
        rows = juice_rows(pid, juices[pid], parsed[pid], model, observed)
        for name in out:
            out[name] += rows[name]
        common.bump(counts, "refused_by_builder", rows["refused"])
    writes_ok = True
    for name in ("products", "variants", "specs"):
        try:
            getattr(writer, name)(out[name])
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s %s write failed (%s)", PREFIX, name, type(exc).__name__)
            writes_ok = False
    counts.update({k: int(v) for k, v in writer.counts.items()})
    common.log_counts(PREFIX, counts)
    if results_ok and writes_ok:
        try:
            ac.messages.batches.delete(batch_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s batch delete failed (%s)", PREFIX, type(exc).__name__)
    return 0


run = main

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main(sys.argv[1:]))
