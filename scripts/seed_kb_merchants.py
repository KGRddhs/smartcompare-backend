#!/usr/bin/env python3
"""Off-clock kb_merchants seed (S81-15 REGISTRY-ROBOTS-DENY). Owner-run; DRY RUN by default.

Builds the rows of migration 045's ``kb_merchants`` table (S81-14) from the 44
literal rows of ``app/services/source_router.py`` and the 368 rows of
``data/bh_gcc_sources.json``: 410 hosts (317 live, 92 candidate, 1 blocked: the
banned fragrance-database host, stored deny true as the owner's blocked list),
411 registry entries (noon.com carries its two ordered literal rows). Every row
is built by the S81-14 merchant row builder (``build_merchant_row``, never a copy
of it; ``merchant_registry.build_seed_rows`` calls it) and the seed adds
``created_at`` on INSERT only. Nothing here is imported by app code.

USAGE (variable NAMES only: ``SUPABASE_URL``, ``SUPABASE_SERVICE_KEY``; the dry
run needs neither):

  python -m scripts.seed_kb_merchants
      Dry run: prints ``rows=410 live=317 candidate=92 blocked=1 collisions=1
      entries=411`` and the per-platform counts; reads and writes nothing remote.

  python -m scripts.seed_kb_merchants --apply
      ONE read of the existing hosts, then inserts of new hosts in batches of at
      most 100 and, for existing hosts, an update of the SEED-OWNED columns only
      (country, currency_hint, adapter, search_template, registry, updated_at;
      platform / platform_confidence only where the stored platform is NULL; the
      deny triple for a banned host). It never writes deny false, status,
      blocked_reason, robots, challenge, tos, partner, health or politeness on an
      existing row (the cron, the owner and D16 own those). Idempotent.

  python -m scripts.seed_kb_merchants --classify [N] [--apply]
      The robots-gated platform probe (default N = 20) over LIVE rows whose
      platform is NULL and whose registry entries carry no mechanism (literal
      rows included), sorted by host: each row's robots record is read first and
      its same-site sample URL is fetched once only when robots allow. Prints the
      count per label. Dry run unless --apply, which writes platform +
      platform_confidence 'probe' where platform is still NULL.

  python -m scripts.seed_kb_merchants --source residential --hosts a.example,b.example [--apply]
      Records a robots read made from THIS machine (run it from a residential
      connection) as ``robots.source = 'residential'`` (ruling R-S15-4: the
      datacenter cron never downgrades such a record younger than 30 days).
      Dry run prints the states; --apply writes each row's update conditionally.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

# Load .env for LOCAL/manual runs (a Railway service injects env directly).
try:
    from dotenv import load_dotenv

    load_dotenv(override=False)
except Exception:  # noqa: BLE001
    pass

from app.services.merchant_registry import KB_MERCHANTS_TABLE as TABLE  # noqa: E402 (after load_dotenv)

BATCH_SIZE = 100
EXISTING_COLUMNS = "host,platform,platform_confidence,deny,status,blocked_reason"
CLASSIFY_COLUMNS = "host,status,platform,platform_confidence,registry,robots,currency_hint,updated_at"
#: PostgREST's default page cap on Supabase: a read this long may be truncated.
MAX_ROWS_ONE_READ = 1000
DEFAULT_CLASSIFY = 20


def _parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="seed_kb_merchants", description=__doc__.split("\n", 1)[0])
    parser.add_argument("--apply", action="store_true", help="write (default: dry run)")
    parser.add_argument("--classify", nargs="?", type=int, const=DEFAULT_CLASSIFY, default=None,
                        help="robots-gated platform probe over N live blank-mechanism rows (default 20)")
    parser.add_argument("--source", choices=("residential",), default=None,
                        help="record a robots read made from this machine with this source")
    parser.add_argument("--hosts", default="", help="comma-separated hosts for --source")
    return parser.parse_args(list(argv) if argv is not None else None)


def _admin_client() -> Any:
    from app.services.database_service import get_admin_supabase_client

    return get_admin_supabase_client()


def _load_json_rows() -> List[Dict[str, Any]]:
    from app.services import source_router as sr

    data = json.loads(sr._CATALOG_DATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("data/bh_gcc_sources.json is not a list")
    return data


def _data(result: Any) -> List[Dict[str, Any]]:
    data = getattr(result, "data", None)
    if not isinstance(data, list):
        raise TypeError("the kb_merchants read did not return a list")
    return [r for r in data if isinstance(r, dict)]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _seed(args: argparse.Namespace, client: Any) -> int:
    from app.services import merchant_registry as mr
    from app.services import source_router as sr

    literal_rows = list(sr._LITERAL_ROWS)
    json_rows = _load_json_rows()
    rows = mr.build_seed_rows(literal_rows, json_rows, _now())
    c = mr.seed_counts(rows, literal_rows, json_rows)
    print("rows=%d live=%d candidate=%d blocked=%d collisions=%d entries=%d" % (
        c["rows"], c["live"], c["candidate"], c["blocked"], c["collisions"], c["entries"]))
    platforms: Dict[str, int] = {}
    for row in rows:
        key = row.get("platform") or "null"
        platforms[key] = platforms.get(key, 0) + 1
    print("platforms " + " ".join("%s=%d" % (k, platforms[k]) for k in sorted(platforms)))
    if not args.apply:
        print("dry run: nothing written (pass --apply to write)")
        return 0
    client = client if client is not None else _admin_client()
    found = _data(client.table(TABLE).select(EXISTING_COLUMNS).range(0, 4999).execute())
    if len(found) >= MAX_ROWS_ONE_READ:
        print("refused: the existing-host read returned %d rows (a PostgREST page may be truncated); "
              "nothing written" % len(found))
        return 2
    existing = {str(r.get("host")): r for r in found}
    inserts, updates = mr.plan_seed(rows, existing)
    for start in range(0, len(inserts), BATCH_SIZE):
        client.table(TABLE).insert(inserts[start:start + BATCH_SIZE]).execute()
    for host, payload in updates:
        client.table(TABLE).update(payload).eq("host", host).execute()
    print("applied inserts=%d updates=%d" % (len(inserts), len(updates)))
    return 0


def _blank_mechanism(row: Dict[str, Any]) -> bool:
    registry = row.get("registry")
    if not isinstance(registry, list) or not registry:
        return False
    return all(isinstance(e, dict) and not (e.get("mechanism") or "") for e in registry)


def _default_probe() -> Any:
    from app.services import robots_registry as rr

    polite = rr.Politeness(asyncio.sleep)

    async def _probe(row: Dict[str, Any]) -> Optional[str]:
        return await rr.classify_host(row, rr.default_fetch, asyncio.sleep, rr.default_validate, polite)

    return _probe


def _classify(args: argparse.Namespace, client: Any, probe: Any) -> int:
    limit = max(0, int(args.classify))
    client = client if client is not None else _admin_client()
    rows = _data(client.table(TABLE).select(CLASSIFY_COLUMNS).eq("status", "live").is_("platform", "null")
                 .order("host").range(0, 4999).execute())
    eligible = sorted(
        (r for r in rows if r.get("status") == "live" and r.get("platform") is None and _blank_mechanism(r)),
        key=lambda r: str(r.get("host")),
    )
    picked = eligible[:limit]
    probe = probe if probe is not None else _default_probe()

    async def _run_all() -> List[Any]:
        out = []
        for row in picked:
            try:
                label = await probe(row)
            except Exception:  # noqa: BLE001 - one row never ends the run
                label = None
            out.append((row, label if isinstance(label, str) and label and label != "unknown" else None))
        return out

    results = asyncio.run(_run_all())
    labels: Dict[str, int] = {}
    for _row, label in results:
        labels[label or "unknown"] = labels.get(label or "unknown", 0) + 1
    print("classify eligible=%d probed=%d %s" % (
        len(eligible), len(picked), " ".join("%s=%d" % (k, labels[k]) for k in sorted(labels))))
    if not args.apply:
        print("dry run: nothing written (pass --apply to write)")
        return 0
    stamp = _now().isoformat()
    written = 0
    for row, label in results:
        if not label:
            continue
        payload = {"platform": label, "platform_confidence": "probe", "updated_at": stamp}
        client.table(TABLE).update(payload).eq("host", row.get("host")).is_("platform", "null").execute()
        written += 1
    print("applied platform=%d" % written)
    return 0


def _residential(args: argparse.Namespace, client: Any) -> int:
    from app.services import deny_hosts
    from app.services import robots_registry as rr

    hosts = [deny_hosts.normalize_host(h) for h in (args.hosts or "").split(",") if h.strip()]
    if not hosts:
        print("refused: --source needs --hosts")
        return 2
    client = client if client is not None else _admin_client()
    rows = _data(client.table(TABLE).select(rr.CRON_COLUMNS).in_("host", hosts).execute())

    async def _read_all() -> List[Any]:
        polite = rr.Politeness(asyncio.sleep)
        out = []
        for row in rows:
            now = rr.utc_now()
            result = await rr.probe_host(row, rr.default_fetch, asyncio.sleep, now, rr.default_validate, polite,
                                         run_gates=False)
            out.append((row, result["verdict"], rr.next_row_update(row, result["verdict"], now, None,
                                                                   source=args.source)))
        return out

    results = asyncio.run(_read_all())
    for row, verdict, _update in results:
        print("%s host=%s state=%s" % (args.source, row.get("host"), verdict.state))
    if not args.apply:
        print("dry run: nothing written (pass --apply to write)")
        return 0
    written = 0
    for row, _verdict, update in results:
        if update and rr.write_update(client, row, update):
            written += 1
    print("applied robots=%d" % written)
    return 0


def main(argv: Optional[Sequence[str]] = None, client: Any = None, probe: Any = None) -> int:
    """The seed entry point (``client`` / ``probe`` are test seams; production
    builds the service-role client only when a mode needs the table)."""
    args = _parse_args(argv)
    if args.classify is not None:
        return _classify(args, client, probe)
    if args.source:
        return _residential(args, client)
    return _seed(args, client)


if __name__ == "__main__":
    sys.exit(main())
