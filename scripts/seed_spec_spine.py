"""UNIT D2 — the OFF-CLOCK seeder for the fragrance spec spine.

WHAT IT DOES. Walks a directory of ALREADY-CACHED PDP HTML, pulls the JSON-LD
Product name/brand/description plus the page's own og:description out of each
file, keeps only the pages that carry a fragrance signal, groups them by the
same normalised identity the runtime lookup uses
(``spec_spine_service.spine_key``), and makes ONE citation-or-omit LLM call PER
FRAGRANCE — not per page, and emphatically not per comparison. The result is
written to ``data/spec_spine.json`` (or ``--out``).

WHY ONE CALL PER FRAGRANCE IS THE WHOLE POINT. A fragrance's scent family and
note pyramid are the same fact every time anyone compares it. The live path
pays a completion for them on every cache miss; this pays once, off the clock,
from prose we already have on disk. B5 measured the raw material: 47/79
captured Gulf pages carry note lists, 56/79 carry family/accords.

IT READS NOTHING FROM THE NETWORK. Every input is a file. No Serper (403), no
retailer fetch, and — per house rule 7 — nothing from fragrantica.com or
parfumo.com, whose robots.txt disallow our agents by name and which served
decoy pages when probed. The ONLY outbound call this script can make is the
OpenAI completion, and that one is opt-in twice over: it needs
``OPENAI_API_KEY`` in the environment, and it is skipped entirely under
``--dry-run``.

THE PROMPT IS A3'S, NOT THE TRAINING-DATA ONE. It is built on
``extraction_service.SPECS_SYSTEM_STATIC_PREFIX_NO_FABRICATION`` — the prefix
that forbids training-data fallback and orders omission — and a field survives
only when the model returns ``<field>_source == "snippet_N"``. That matters
more here than on the live path: a spine row is written ONCE and then served
to every future comparison, so a fabrication seeded here would not decay with
a 7-day TTL, it would persist. A thin, honestly-empty spine is the correct
outcome for a thin corpus.

USAGE
    # what would be seeded, from the cached corpora, zero LLM calls:
    python scripts/seed_spec_spine.py --dry-run --dump-candidates cands.json

    # the real run (needs OPENAI_API_KEY; OpenAI is 429 as of this writing,
    # which is exactly why this is a script and not a startup task):
    python scripts/seed_spec_spine.py --corpus _proof/html --out data/spec_spine.json
"""
from __future__ import annotations

import argparse
import asyncio
import html as html_lib
import io
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.spec_spine_service import (  # noqa: E402
    SPINE_CATEGORY,
    SPINE_FIELDS,
    spine_key,
)

logger = logging.getLogger("seed_spec_spine")

# The default corpora — read-only, git-excluded, already on disk (house rule 7).
DEFAULT_CORPORA = ("_proof/html", "_proof/global/html")

# How much prose per page reaches the prompt. The descriptions that matter run
# 500-3500 chars; the cap bounds a pathological page without truncating a real
# note pyramid.
MAX_PAGE_TEXT_CHARS = 4000
# How many pages of one fragrance are cited. More pages is more corroboration,
# but the marginal page is usually the same marketing copy; 4 keeps the prompt
# small enough that the note lists stay in attention.
MAX_PAGES_PER_FRAGRANCE = 4

_JSONLD_BLOCK_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)
_OG_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\']og:(title|description|url)["\'][^>]*>', re.I
)
_CONTENT_RE = re.compile(r'content=["\'](.*?)["\']', re.I | re.S)
_CANONICAL_RE = re.compile(
    r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\'](.*?)["\']', re.I
)
_TAG_RE = re.compile(r"<[^>]+>")

# Prose markers that say "this page describes a FRAGRANCE", beyond the
# concentration/product-word signals price_service already knows. A page must
# carry at least one signal or it is not a spine candidate at all — the spine
# must never answer for a phone.
_FRAGRANCE_PROSE_MARKERS = (
    "top note", "heart note", "middle note", "base note", "fragrance family",
    "scent family", "olfactive", "accord", "sillage", "longevity",
    "eau de parfum", "eau de toilette",
)


# ---------------------------------------------------------------------------
# Page parsing — files only.
# ---------------------------------------------------------------------------
def _walk_json(node: Any, out: List[Dict[str, Any]]) -> None:
    if isinstance(node, dict):
        out.append(node)
        for value in node.values():
            _walk_json(value, out)
    elif isinstance(node, list):
        for value in node:
            _walk_json(value, out)


def _iter_jsonld_nodes(html: str) -> Iterator[Dict[str, Any]]:
    """Every dict node in every JSON-LD block, in document order. Mirrors
    ``judgeme_service._iter_jsonld_nodes``; kept local so a batch script never
    imports the review stack."""
    for match in _JSONLD_BLOCK_RE.finditer(html):
        try:
            data = json.loads(match.group(1))
        except (ValueError, TypeError):
            continue
        nodes: List[Dict[str, Any]] = []
        _walk_json(data, nodes)
        for node in nodes:
            yield node


def _is_product(node: Dict[str, Any]) -> bool:
    types = node.get("@type") or node.get("type")
    types = types if isinstance(types, list) else [types]
    return any("product" in str(t).lower() for t in types if t)


def _text(value: Any) -> str:
    """A JSON-LD / meta string as PROSE: entity-decoded, tag-stripped,
    whitespace-collapsed.

    THE UNESCAPE IS NOT COSMETIC. The first real dry run over the corpora keyed
    6 of 184 fragrances on RAW entities — ``grey&#x20;flannel&#x20;eau&#x20;…``
    (beautysuccess.fr), ``Acqua dell&apos; Elba`` (notino.co.uk),
    ``Bath &amp; Body Works``. The runtime lookup sees the DECODED title, so an
    entity-bearing key can never be hit: the seed would be paid for, written,
    and never read once. Decoding is what makes the seeder's key and the
    lookup's key the same string.
    """
    if isinstance(value, dict):
        value = value.get("name") or value.get("@value") or ""
    if isinstance(value, list):
        value = value[0] if value else ""
    text = html_lib.unescape(str(value or ""))
    text = _TAG_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def _ascii(text: str) -> str:
    """``text`` with every non-ASCII character replaced by '?'.

    House rule 5: the Windows console is cp1252 and a raw non-ASCII ``print``
    raises UnicodeEncodeError. The corpora carry Arabic and Turkish titles
    (4 of 184 keys in the first real run), and the crash landed AFTER the
    candidate scan — i.e. it threw away work that had already been done. Every
    print in this script goes through here; the FILES it writes are UTF-8 and
    keep the real characters.
    """
    return (text or "").encode("ascii", "replace").decode("ascii")


def _og_tags(html: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for match in _OG_RE.finditer(html):
        content = _CONTENT_RE.search(match.group(0))
        if content:
            out.setdefault(match.group(1).lower(), _text(content.group(1)))
    return out


def _page_url(html: str, node: Dict[str, Any]) -> str:
    og = _og_tags(html).get("url") or ""
    if og.startswith("http"):
        return og
    canonical = _CANONICAL_RE.search(html)
    if canonical and canonical.group(1).startswith("http"):
        return canonical.group(1)
    for key in ("url", "@id"):
        val = str(node.get(key) or "")
        if val.startswith("http"):
            return val
    return ""


def _has_fragrance_signal(surface: str) -> bool:
    """True iff this page is plausibly a fragrance PDP.

    Three independent signals, any one of which is enough: a concentration
    token (EDP/EDT/Extrait/...), one of ``price_service``'s generic fragrance
    product words (perfume / cologne / attar / oud / ...), or note-pyramid
    prose. Deliberately a UNION and deliberately checked here rather than
    after the LLM: a page that is not a fragrance must never reach the prompt,
    let alone the store.
    """
    from app.services.price_service import (
        FRAGRANCE_PRODUCT_KEYWORDS,
        extract_concentration,
    )

    lowered = (surface or "").lower()
    if not lowered:
        return False
    if extract_concentration(lowered):
        return True
    if any(marker in lowered for marker in _FRAGRANCE_PROSE_MARKERS):
        return True
    return any(
        re.search(r"\b" + re.escape(word) + r"\b", lowered)
        for word in FRAGRANCE_PRODUCT_KEYWORDS
    )


def parse_page(path: str) -> Optional[Dict[str, str]]:
    """One cached PDP file -> a spine page candidate, or None.

    None when the file is unreadable, carries no JSON-LD Product with a brand
    AND a name, or shows no fragrance signal. Never raises: a corpus of a few
    hundred scraped pages always contains something malformed, and one bad
    file must not end a seed run.
    """
    try:
        html = io.open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    og = _og_tags(html)
    for node in _iter_jsonld_nodes(html):
        if not _is_product(node):
            continue
        name = _text(node.get("name")) or og.get("title", "")
        brand = _text(node.get("brand"))
        if not name or not brand:
            continue
        description = _text(node.get("description")) or og.get("description", "")
        surface = " ".join(x for x in (name, brand, description) if x)
        if not _has_fragrance_signal(surface):
            continue
        url = _page_url(html, node)
        return {
            "brand": brand,
            "name": name,
            "url": url,
            "host": urlparse(url).netloc if url else "",
            "path": str(path),
            "text": " ".join((name, description)).strip()[:MAX_PAGE_TEXT_CHARS],
        }
    return None


def iter_corpus_files(directory: str) -> Iterator[str]:
    root = Path(directory)
    if not root.is_dir():
        logger.warning("corpus dir not found, skipping: %s", directory)
        return
    for path in sorted(root.rglob("*.html")):
        yield str(path)


def build_candidates(
    directories: List[str], limit: Optional[int] = None
) -> Dict[str, Dict[str, Any]]:
    """Group every fragrance page in ``directories`` by spine key.

    The grouping is the amortisation: two retailers describing one juice
    become ONE candidate and therefore ONE completion. Returns
    ``{spine_key: {"brand", "name", "pages": [page, ...]}}``. Pure file I/O —
    no network, no LLM, no store write.
    """
    out: Dict[str, Dict[str, Any]] = {}
    for directory in directories:
        for path in iter_corpus_files(directory):
            page = parse_page(path)
            if not page:
                continue
            key = spine_key(page["brand"], page["name"], category=SPINE_CATEGORY)
            entry = out.setdefault(
                key, {"brand": page["brand"], "name": page["name"], "pages": []}
            )
            if len(entry["pages"]) < MAX_PAGES_PER_FRAGRANCE:
                entry["pages"].append(page)
            if limit and len(out) >= limit:
                return out
    return out


# ---------------------------------------------------------------------------
# The (opt-in) LLM step.
# ---------------------------------------------------------------------------
def _seed_prompt(brand: str, name: str, pages: List[Dict[str, str]]) -> Dict[str, str]:
    """The citation-or-omit seed prompt.

    Built on A3's ``SPECS_SYSTEM_STATIC_PREFIX_NO_FABRICATION`` — the SAME
    contract the live specs path enforces under ENABLE_SPECS_NO_FABRICATION —
    never ``SPECS_SYSTEM_STATIC_PREFIX``, which explicitly orders training-data
    fallback. The snippet digest is numbered exactly as
    ``_format_numbered_search_results`` numbers it, so ``snippet_N`` means the
    same thing to the model here as it does there.
    """
    from app.services.extraction_service import SPECS_SYSTEM_STATIC_PREFIX_NO_FABRICATION

    fields_json = ",\n    ".join(f'"{f}": null' for f in SPINE_FIELDS)
    system = SPECS_SYSTEM_STATIC_PREFIX_NO_FABRICATION + f"""
CATEGORY: fragrances

You are building a REUSABLE fragrance record. Unlike a one-off answer, what you
return here is stored and served to every future comparison of this fragrance,
so an uncited guess does not expire - it persists. Returning three cited fields
out of nine is the correct answer when the pages support three.

REQUIRED SCHEMA:
{{
    "brand": "...",
    "model": "...",
    {fields_json}
}}

- notes_top / notes_heart / notes_base: the note lists as the page states them,
  comma-separated. If a page lists notes without splitting them into top/heart/
  base, put them in notes_top and leave the other two out - do NOT distribute
  them across the pyramid yourself.
- scent_family: the olfactive family the page names (e.g. "Aromatic Fougere",
  "Oriental Woody"). Never inferred from the note list.
- concentration: only when the page states it (Eau de Parfum / EDT / Extrait).
- Every field you return MUST carry "<field>_source": "snippet_N".

Return ONLY valid JSON (no markdown) matching the schema above."""

    digest = "\n".join(
        f"[snippet_{i + 1}] {p.get('host') or p.get('path')}\n   {p['text']}"
        for i, p in enumerate(pages)
    )
    user = f"""<USER_INPUT>
Fragrance: {brand} {name}
</USER_INPUT>

RETAILER PAGE TEXT:
{digest}

Return ONLY valid JSON (no markdown) matching the schema above."""
    return {"system": system, "user": user}


async def extract_spine_specs(
    brand: str, name: str, pages: List[Dict[str, str]]
) -> Dict[str, str]:
    """ONE completion for ONE fragrance -> its cited spine fields.

    A field survives only when the model returned ``<field>_source`` starting
    with ``snippet_``; an uncited or placeholder value is DROPPED, exactly as
    ``extract_specs`` drops it under ENABLE_SPECS_NO_FABRICATION. Returns
    ``{}`` on any failure — a seed run that half-fails must leave a smaller
    spine, never a wrong one.

    This is the ONLY function in this module that touches the network, and it
    is unreachable under ``--dry-run`` or without ``OPENAI_API_KEY``.
    """
    from app.services.extraction_service import get_client
    from app.services.model_config import standard_model

    prompt = _seed_prompt(brand, name, pages)
    try:
        response = await get_client().chat.completions.create(
            model=standard_model(),
            messages=[
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]},
            ],
            max_tokens=900,
            temperature=0.1,
        )
        raw_text = (response.choices[0].message.content or "").strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        raw = json.loads(raw_text)
    except Exception as exc:  # noqa: BLE001 — one bad fragrance must not end the run
        logger.warning("seed extraction failed for %s %s: %s", brand, name, exc)
        return {}

    out: Dict[str, str] = {}
    for field in SPINE_FIELDS:
        value = raw.get(field)
        source = raw.get(f"{field}_source")
        cited = isinstance(source, str) and source.strip().lower().startswith("snippet_")
        if value is None or not cited:
            continue
        text = ", ".join(str(v) for v in value) if isinstance(value, list) else str(value)
        text = text.strip()
        if not text or text.lower() in ("n/a", "na", "null", "none"):
            continue
        out[field] = text
    return out


# ---------------------------------------------------------------------------
# Store I/O + CLI.
# ---------------------------------------------------------------------------
def _load_out(path: str) -> Dict[str, Any]:
    try:
        with io.open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_json(path: str, payload: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")


async def _seed(candidates: Dict[str, Dict[str, Any]], out_path: str) -> int:
    """Run one completion per candidate and merge the results into the store.
    Returns the number of entries written."""
    store = _load_out(out_path)
    written = 0
    for key, cand in sorted(candidates.items()):
        specs = await extract_spine_specs(cand["brand"], cand["name"], cand["pages"])
        if not specs:
            print("  skip (no cited field): %s" % _ascii(key))
            continue
        store[key] = {
            "brand": cand["brand"],
            "name": cand["name"],
            "specs": specs,
            "seed_pages": len(cand["pages"]),
            "seed_urls": [p["url"] for p in cand["pages"] if p.get("url")],
            "seeded_at": datetime.now(timezone.utc).isoformat(),
        }
        written += 1
        print("  seeded %d field(s): %s" % (len(specs), _ascii(key)))
    _write_json(out_path, store)
    return written


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed the fragrance spec spine from cached PDP HTML (off-clock).",
    )
    parser.add_argument(
        "--corpus", action="append", default=None,
        help="directory of cached PDP .html (repeatable; default: the _proof corpora)",
    )
    parser.add_argument("--out", default="data/spec_spine.json", help="store to write")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="build candidates and stop - no LLM call, no store write",
    )
    parser.add_argument(
        "--dump-candidates", default=None,
        help="write the grouped candidates to this JSON file (works with --dry-run)",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="stop after N distinct fragrances",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    corpora = args.corpus or list(DEFAULT_CORPORA)

    candidates = build_candidates(corpora, limit=args.limit)
    pages = sum(len(c["pages"]) for c in candidates.values())
    print("candidates: %d fragrance(s) from %d page(s) across %d dir(s)"
          % (len(candidates), pages, len(corpora)))
    if args.dump_candidates:
        _write_json(args.dump_candidates, candidates)
        print("candidates written to %s" % _ascii(args.dump_candidates))

    if args.dry_run:
        for key, cand in sorted(candidates.items())[:20]:
            print("  %-2d page(s)  %s" % (len(cand["pages"]), _ascii(key)))
        print("dry run - no LLM call made, %s not written" % _ascii(args.out))
        return 0

    if not candidates:
        print("nothing to seed - no fragrance pages found in: %s" % _ascii(", ".join(corpora)))
        return 0

    # The no-op guard. OpenAI is 429 as of this unit; the seeder is built to be
    # runnable LATER, so "no key" is a normal, successful outcome, not an error.
    if not (os.getenv("OPENAI_API_KEY") or "").strip():
        print("OPENAI_API_KEY is not set - nothing seeded, %s not written." % _ascii(args.out))
        print("Re-run this command with the key set to perform the extraction; "
              "use --dry-run to inspect candidates without it.")
        return 0

    written = asyncio.run(_seed(candidates, args.out))
    print("seeded %d of %d fragrance(s) into %s" % (written, len(candidates), _ascii(args.out)))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
