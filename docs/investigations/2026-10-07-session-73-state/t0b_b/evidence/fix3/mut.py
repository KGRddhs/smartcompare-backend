"""Round-3 continuation mutant harness (T0b Phase B).

One mutant at a time: byte copy of the target (shutil.copyfile), count-checked
byte replacement, the killing nodes through the bounded runner (pyt.py), restore
from the byte copy, sha256 compare (abort on mismatch). Usage:

    python mut.py <mutant> [<mutant> ...]
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

WT = "C:/Users/SynAckITPC/Documents/AI/sc-s71-t0b"
NOTES = "C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/d376cb56-c600-4d76-bfdb-9e15feff0cdc/scratchpad/t0b_b/fix3"
PYT = "C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/d376cb56-c600-4d76-bfdb-9e15feff0cdc/scratchpad/harness/pyt.py"
VENV = "C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe"
HOOK = ".githooks/pre-commit"
CI = ".github/workflows/ci.yml"
R2 = "tests/test_precommit_hook_phase_b_round2.py"
PHB = "tests/test_precommit_hook_phase_b.py"
CR = b"\r\n"

# The three-line head of each backstop block (identical in both blocks).
B1 = b"if { LC_ALL=C grep -E '^\\+' \"$TMP/staged.ext\""
B2 = b"     LC_ALL=C tr '\\000' '\\n' < \"$STAGED_DIFF\" | LC_ALL=C grep -E '^\\+'"
B3 = b"   } | LC_ALL=C grep -Ev '^\\+\\+\\+' | \\"
B1n = b"if { grep -E '^\\+' \"$TMP/staged.ext\""
B2n = b"     tr '\\000' '\\n' < \"$STAGED_DIFF\" | grep -E '^\\+'"
B3n = b"   } | grep -Ev '^\\+\\+\\+' | \\"


def row(ext_glob: bytes, lower: bytes) -> bytes:
    return b"    *." + ext_glob + b") _cmp=${_bin%.*}." + lower + b" ;;" + CR


MUTANTS = {
    # TBF11: the CI flag mutant.
    "tbf11_ci_no_color_dropped": (
        CI,
        [(b"--no-banner --no-color -v", b"--no-banner -v", 1)],
        [R2, "-k", "ci_gitleaks_err_line_fails or ci_gitleaks_call_runs_without_colour or ci_real_gitleaks_err_line_fails"],
    ),
    # TBF15: the PR base is not checked.
    "C_pr_ends_head_only": (
        CI,
        [(b'ENDS="$PR_BASE $PR_HEAD"', b'ENDS="$PR_HEAD"', 1)],
        [R2, "-k", "ci_unreachable"],
    ),
    # TBF14 m1: the staged.ext reader dropped from both backstop blocks.
    "m1_ext_reader_dropped": (
        HOOK,
        [(B1 + CR + b"     LC_ALL=C tr", b"if { LC_ALL=C tr", 2)],
        [R2, "-k", "Round4 or b3_ or a1_"],
    ),
    # TBF14 m2: the tr reader dropped from both backstop blocks.
    "m2_tr_reader_dropped": (
        HOOK,
        [(B1 + CR + B2 + CR + b"   }", B1 + CR + b"   }", 2)],
        [R2, "-k", "Round4 or b3_ or a1_"],
    ),
    # TBF14 m3: NUL deleted instead of mapped to a line break.
    "m3_tr_d": (
        HOOK,
        [(rb"tr '\000' '\n' <", rb"tr -d '\000' <", 2)],
        [PHB, R2, "-k", "i315_utf16_aws_key or utf16 or dump"],
    ),
    # TBF14 m4: LC_ALL=C dropped from the backstop pipelines.
    "m4_lc_all_dropped": (
        HOOK,
        [(B1 + CR + B2 + CR + B3, B1n + CR + B2n + CR + B3n, 2)],
        [R2, "-k", "f1_dead_awk_utf8 or Round4 or b3_"],
    ),
    # TBF16: one row of the extension case deleted.
    "H_jpeg_case_row_dropped": (HOOK, [(row(b"[Jj][Pp][Ee][Gg]", b"jpeg"), b"", 1)], [R2, "-k", "f4_ or a3_"]),
    "H_ttf_case_row_dropped": (HOOK, [(row(b"[Tt][Tt][Ff]", b"ttf"), b"", 1)], [R2, "-k", "f4_ or a3_"]),
    "H_gif_case_row_dropped": (HOOK, [(row(b"[Gg][Ii][Ff]", b"gif"), b"", 1)], [R2, "-k", "f4_ or a3_"]),
    "H_webp_case_row_dropped": (HOOK, [(row(b"[Ww][Ee][Bb][Pp]", b"webp"), b"", 1)], [R2, "-k", "f4_ or a3_"]),
    "H_otf_case_row_dropped": (HOOK, [(row(b"[Oo][Tt][Ff]", b"otf"), b"", 1)], [R2, "-k", "f4_ or a3_"]),
    # TBF10: --no-color dropped from the hook's gitleaks call.
    "tbf1_no_color_dropped": (
        HOOK,
        [(b"--redact --no-banner --no-color \\", b"--redact --no-banner \\", 1)],
        [R2, "-k", "tbf1_"],
    ),
}

# Frozen-file dead-awk nodes for the survivors (completeness).
for _m in ("m1_ext_reader_dropped", "m2_tr_reader_dropped", "m4_lc_all_dropped"):
    MUTANTS[_m + "__frozen_d1"] = (MUTANTS[_m][0], MUTANTS[_m][1],
        ["tests/test_precommit_hook_round2.py", "-k", "d1_ or r3_"])


def sha(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def run(name: str) -> dict:
    rel, edits, pyargs = MUTANTS[name]
    target = os.path.join(WT, rel)
    backup_dir = os.path.join(NOTES, "mut_backup")
    os.makedirs(backup_dir, exist_ok=True)
    backup = os.path.join(backup_dir, name + ".orig")
    shutil.copyfile(target, backup)
    orig_sha = sha(target)
    assert sha(backup) == orig_sha, "byte copy differs from the target"
    data = open(target, "rb").read()
    for old, new, count in edits:
        n = data.count(old)
        if n != count:
            raise SystemExit("%s: expected %d occurrence(s), found %d of %r" % (name, count, n, old[:60]))
        data = data.replace(old, new)
    mut_sha = hashlib.sha256(data).hexdigest()
    log = os.path.join(NOTES, "mut_%s.log" % name)
    result = {"mutant": name, "target": rel, "orig_sha": orig_sha, "mut_sha": mut_sha}
    try:
        with open(target, "wb") as fh:
            fh.write(data)
        assert sha(target) == mut_sha
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        cmd = [VENV, PYT, "--bound", "600", "--tag", "m_" + name, "--log", log, "--cwd", WT, "--", *pyargs, "-q", "-rA"]
        p = subprocess.run(cmd, capture_output=True, env=env, timeout=700)
        out = p.stdout.decode("utf-8", "replace")
        result["pyt"] = [ln for ln in out.splitlines() if ln.startswith("[pyt] tag=")]
        text = open(log, encoding="utf-8", errors="replace").read()
        result["failed"] = sorted(set(re.findall(r"^FAILED (\S+)", text, re.M)))
        result["passed"] = sorted(set(re.findall(r"^PASSED (\S+)", text, re.M)))
        result["skipped"] = len(re.findall(r"^SKIPPED", text, re.M))
    finally:
        shutil.copyfile(backup, target)
        after = sha(target)
        result["restored_sha"] = after
        result["restore_ok"] = after == orig_sha
        if after != orig_sha:
            print(json.dumps(result, indent=1))
            raise SystemExit("RESTORE MISMATCH for %s: %s != %s" % (name, after, orig_sha))
    return result


def main() -> None:
    with open(os.path.join(NOTES, "mutants.jsonl"), "a", encoding="utf-8") as out:
        for name in sys.argv[1:]:
            t0 = time.time()
            res = run(name)
            res["elapsed"] = round(time.time() - t0, 1)
            out.write(json.dumps(res) + "\n")
            out.flush()
            print("%s: pyt=%s failed=%d passed=%d skipped=%d restore_ok=%s" % (
                name, res.get("pyt"), len(res.get("failed", [])), len(res.get("passed", [])),
                res.get("skipped", 0), res["restore_ok"]))
            for f in res.get("failed", []):
                print("   FAILED " + f)


if __name__ == "__main__":
    main()
