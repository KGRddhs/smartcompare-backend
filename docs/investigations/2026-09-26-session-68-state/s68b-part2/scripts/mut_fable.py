"""Fable's re-run of adversary r3's surviving mutants E1-E5 on the final W4-11 bytes after the
pin rows were added. Byte snapshot -> count-checked CRLF-aware edit -> the 4 unit files through
pyt.py -> restore -> sha256 compare. Every row must go RED now."""
import hashlib, json, os, shutil, subprocess, sys

W = "C:/Users/SynAckITPC/Documents/AI/sc-w4-11"
NSP = "C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/0a2845de-abfe-4bca-b433-df4ce9787ab5/scratchpad"
PY = "C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, "snap")
LOGS = os.path.join(HERE, "mlogs")
os.makedirs(SNAP, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)
ES = "app/services/extraction_service.py"
OS_ = "app/services/openai_service.py"
UNIT = ["tests/test_prompt_fence.py", "tests/test_prompt_truth.py",
        "tests/test_model_config_enforced.py", "tests/test_price_fallback_may_decline.py"]
GAP_LINE = "_cons_gap += sum(1 for c in _items if isinstance(c, str) and _DATA_GAP_CON_RE.search(c))"
ROWS = [
    ("E1-name-slot-coercion-dropped", [(OS_, "{sanitize_prompt_input(_coerce_name_part(name))}",
                                        "{sanitize_prompt_input(name)}")]),
    ("E2-variant-slot-coercion-dropped", [(OS_, "{sanitize_prompt_input(_coerce_name_part(variant or ''))}",
                                           "{sanitize_prompt_input(variant or '')}")]),
    ("E3-gap-counted-per-match", [(ES, GAP_LINE,
                                   "_cons_gap += sum(len(_DATA_GAP_CON_RE.findall(c)) for c in _items if isinstance(c, str))")]),
    ("E4-list-join-no-space", [(OS_, 'return " ".join(str(item) for item in value)',
                                'return "".join(str(item) for item in value)')]),
    ("E5-coerce-after-sanitize-brand", [(OS_, "{sanitize_prompt_input(_coerce_name_part(brand))}",
                                         "{_coerce_name_part(sanitize_prompt_input(brand) if isinstance(brand, str) else brand)}")]),
]


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def snap_path(rel):
    return os.path.join(SNAP, rel.replace("/", "__"))


def apply(edits):
    for rel, old, new in edits:
        p = os.path.join(W, rel)
        raw = open(p, "rb").read()
        crlf = b"\r\n" in raw
        txt = raw.decode("utf-8")
        o = old.replace("\n", "\r\n") if crlf else old
        n = new.replace("\n", "\r\n") if crlf else new
        c = txt.count(o)
        if c != 1:
            raise SystemExit(f"anchor count {c} != 1 for {rel}: {old[:60]!r}")
        open(p, "wb").write(txt.replace(o, n).encode("utf-8"))


def run(tag):
    log = os.path.join(LOGS, tag + ".log")
    env = dict(os.environ)
    env.pop("ENABLE_VERDICT_PROMPT_TRUTH", None)
    env.pop("ENABLE_PRICE_FALLBACK_MAY_DECLINE", None)
    env["PYTHONIOENCODING"] = "utf-8"
    cmd = [PY, os.path.join(NSP, "harness", "pyt.py"), "--bound", "600", "--tag", "fable-" + tag,
           "--log", log, "--cwd", W, "--"] + UNIT + ["-q", "-rf"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    out = r.stdout + r.stderr
    summary = [l for l in out.splitlines() if " passed" in l or " failed" in l]
    fails = [l.strip() for l in open(log, encoding="utf-8", errors="replace") if l.startswith("FAILED")]
    return r.returncode, (summary[-1] if summary else out[-200:]), fails


results = {}
for name, edits in ROWS:
    rels = sorted({e[0] for e in edits})
    pre = {}
    for rel in rels:
        shutil.copyfile(os.path.join(W, rel), snap_path(rel))
        pre[rel] = sha(os.path.join(W, rel))
    try:
        apply(edits)
        rc, summary, fails = run(name)
    finally:
        for rel in rels:
            shutil.copyfile(snap_path(rel), os.path.join(W, rel))
    post = {rel: sha(os.path.join(W, rel)) for rel in rels}
    restored = all(pre[r] == post[r] for r in rels)
    verdict = "RED" if rc != 0 else "SURVIVES"
    results[name] = {"verdict": verdict, "summary": summary, "failed": fails[:6], "restored": restored}
    print(f"{name}: {verdict} | {summary} | restored={restored}")
    for f in fails[:4]:
        print("   ", f[:160])
json.dump(results, open(os.path.join(HERE, "results.json"), "w"), indent=1)
bad = [n for n, r in results.items() if r["verdict"] != "RED" or not r["restored"]]
print("ALL RED AND RESTORED" if not bad else f"PROBLEM: {bad}")
