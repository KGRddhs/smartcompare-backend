"""Mutants for Fable's three W4-14 closing pins. Each: byte snapshot -> mutate -> run the
ONE relevant file (pytest through pyt.py, jest by path under timeout) -> restore -> sha check.
python mut_fable.py X4 | X2 | C3 | all"""
import io, os, sys, shutil, hashlib, subprocess, json

WT = "C:/Users/SynAckITPC/Documents/AI/sc-w4-14"
NSP = "C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/0a2845de-abfe-4bca-b433-df4ce9787ab5/scratchpad"
PY = "C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe"
SNAP = os.path.join(NSP, "w414fable", "snap")
os.makedirs(SNAP, exist_ok=True)
ES = "app/services/extraction_service.py"
AR = "SmartCompareApp/src/i18n/ar.json"


def sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def run_py(tag, expr=""):
    cmd = [PY, os.path.join(NSP, "harness", "pyt.py"), "--bound", "600", "--tag", tag,
           "--log", os.path.join(NSP, "w414fable", tag + ".log"), "--cwd", WT, "--",
           "tests/test_arabic_verdict_output_w414.py", "-q"] + (["-k", expr] if expr else [])
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    for k in ("ENABLE_ARABIC_VERDICT_OUTPUT", "ENABLE_VERDICT_PROMPT_TRUTH", "ENABLE_COHORT_PERSONALIZATION"):
        env.pop(k, None)
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
    lines = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith("[pyt]") or " passed" in l or " failed" in l]
    return "\n".join(lines[-3:])


def run_jest(tag):
    cmd = ["timeout", "-k", "15", "600", "node", "node_modules/jest/bin/jest.js", "--ci",
           "__tests__/i18n/referralExpiryPlurals.w414.test.ts"]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.join(WT, "SmartCompareApp"),
                       encoding="utf-8", errors="replace")
    lines = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith("Tests:") or l.startswith("Test Suites:")]
    return f"[jest] tag={tag} rc={r.returncode} " + " | ".join(lines)


def mutate(rel, fn):
    p = os.path.join(WT, rel)
    snap = os.path.join(SNAP, rel.replace("/", "__"))
    shutil.copyfile(p, snap)
    before = sha(p)
    raw = io.open(p, "rb").read()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8").replace("\r\n", "\n")
    text2 = fn(text)
    assert text2 != text, "mutant did not apply"
    io.open(p, "wb").write((text2.replace("\n", "\r\n") if crlf else text2).encode("utf-8"))
    return before, snap


def restore(rel, before, snap):
    p = os.path.join(WT, rel)
    shutil.copyfile(snap, p)
    after = sha(p)
    assert after == before, ("RESTORE MISMATCH", rel, before, after)
    return "restored sha ok " + before[:16]


def m_X4(text):
    old = ('    return os.environ.get("ENABLE_ARABIC_VERDICT_OUTPUT", "").strip().lower() in (\n'
           '        "1", "true", "yes", "on",\n'
           '    )\n')
    assert text.count(old) == 1
    return text.replace(old, '    return os.environ.get("ENABLE_ARABIC_VERDICT_OUTPUT", "").strip().lower() not in (\n'
                             '        "", "0", "false", "no", "off",\n'
                             '    )\n')


def m_X2(text):
    lines = text.split("\n")
    start = next(i for i, l in enumerate(lines) if l.startswith("async def generate_comparison("))
    idx = next(i for i in range(start, len(lines)) if "parsed = json.loads(result)" in lines[i])
    ind = lines[idx][: len(lines[idx]) - len(lines[idx].lstrip())]
    lines.insert(idx + 1, ind + 'if output_lang == "ar":')
    lines.insert(idx + 2, ind + '    parsed["winner_reason"] = "AR"')
    return "\n".join(lines)


def m_C3(text):
    d = json.loads(text)
    d["referrals.bonus.expiresInHours_two"] = d["referrals.bonus.expiresInHours_zero"]
    # keep the file's formatting: replace only the one value string in the text
    key = '"referrals.bonus.expiresInHours_two": '
    i = text.index(key) + len(key)
    j = text.index('"', i + 1)
    while text[j - 1] == "\\":
        j = text.index('"', j + 1)
    return text[:i] + json.dumps(d["referrals.bonus.expiresInHours_two"], ensure_ascii=False) + text[j + 1:]


MUTS = {
    "X4": (ES, m_X4, lambda: run_py("mutX4", "test_38")),
    "X2": (ES, m_X2, lambda: run_py("mutX2", "test_40 or test_31")),
    "C3": (AR, m_C3, lambda: run_jest("mutC3")),
}

which = sys.argv[1:] or ["all"]
names = list(MUTS) if which == ["all"] else which
for n in names:
    rel, fn, runner = MUTS[n]
    before, snap = mutate(rel, fn)
    try:
        print(f"=== mutant {n} on {rel} ===")
        print(runner())
    finally:
        print(restore(rel, before, snap))
