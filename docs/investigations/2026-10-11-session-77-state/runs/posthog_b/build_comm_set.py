"""Build the G3 comm file set at HEAD and chunk it (<= 25 files per chunk).
Usage: python -I build_comm_set.py <worktree> <outdir>"""
import glob
import json
import os
import re
import sys
from pathlib import Path

WT = Path(sys.argv[1])
OUT = Path(sys.argv[2])
REF = re.compile(
    r"product_analytics_service|feedback_service|database_service|app\.main\b|app/main\.py"
    r"|auth_routes|text_routes|fill_in_legal|processors\.json|legal_fill_in_u8|_env_safety"
)
tests = sorted((WT / "tests").glob("*.py"))
ref_set = set()
for p in tests:
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = p.read_text(encoding="utf-8", errors="replace")
    if REF.search(text):
        ref_set.add(p.name)
pins = set()
for pat in ("test_model_config*.py", "test_prompt_fence.py", "test_u3c_store_false_pin.py",
            "test_start_command*.py", "test_migration_index_predicate_immutability.py",
            "test_openai_key_log_hygiene_s69.py", "test_sentry_channels_u8d_unit.py",
            "test_events_allowlist_superset.py", "test_shutdown_drain.py",
            "test_auth_preference_toggles_w314.py", "test_u3b_sharing_branch_removed.py"):
    pins |= {Path(x).name for x in glob.glob(str(WT / "tests" / pat))}
drain = set()
for p in tests:
    if "drainingSeconds" in p.read_text(encoding="utf-8", errors="replace"):
        drain.add(p.name)
red = {"test_s77_posthog_server.py", "test_shutdown_drain.py"}
# Only collectable test modules (test_*.py); helper modules (_env_safety.py, conftest.py) excluded.
union = sorted(n for n in (ref_set | pins | drain | red) if n.startswith("test_"))
hook = [n for n in union if n.startswith("test_precommit_hook")]
rest = [n for n in union if n not in hook]
chunks = [rest[i:i + 25] for i in range(0, len(rest), 25)]
OUT.mkdir(parents=True, exist_ok=True)
meta = {
    "ref_set": len(ref_set), "pins_found": sorted(pins), "drain_pins": sorted(drain),
    "union": len(union), "hook_files": hook, "chunks": len(chunks),
}
(OUT / "comm_set.json").write_text(json.dumps({"meta": meta, "files": union, "chunks": chunks,
                                               "hook": hook}, indent=1), encoding="utf-8")
print(json.dumps(meta, indent=1))
