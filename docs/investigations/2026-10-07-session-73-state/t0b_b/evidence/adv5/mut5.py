"""Round-5 own mutants on the round-3 lines of .githooks/pre-commit.

One mutant at a time: shutil byte copy, line-checked edit (CRLF kept),
the bounded runner with -k the killing node(s), restore from the copy,
sha256 compare (stop on mismatch). Results append to mut5.jsonl.
With --lf NAME the mutant is written to <notes>/mut_<NAME>.lf only (an LF
copy for the scenario harness) and the worktree is never touched.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

WT = "C:/Users/SynAckITPC/Documents/AI/sc-s71-t0b"
HOOK = WT + "/.githooks/pre-commit"
NOTES = ("C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/"
         "d376cb56-c600-4d76-bfdb-9e15feff0cdc/scratchpad/t0b_b/adv5")
PYT = ("C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/"
       "d376cb56-c600-4d76-bfdb-9e15feff0cdc/scratchpad/harness/pyt.py")
VPY = "C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe"
GOOD = "4e9a583c76575fe774312152cdf2b53759719c203473325599c9b9fbb3ed4e3b"
R2 = "tests/test_precommit_hook_phase_b_round2.py"
PB = "tests/test_precommit_hook_phase_b.py"
FOUR = ("(\\bsk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}"
        "|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----)")
L211 = "if { LC_ALL=C grep -E '^\\+' \"$TMP/staged.ext\""
L212 = "     LC_ALL=C tr '\\000' '\\n' < \"$STAGED_DIFF\" | LC_ALL=C grep -E '^\\+'"
L213 = "   } | LC_ALL=C grep -Ev '^\\+\\+\\+' | \\"
L214 = "   grep -qE '" + FOUR + "'; then"
L220 = "   grep -qE -e \"$JWT_RE\" -e \"$CREDURL_RE\"; then"
MSG1 = "  fail \"staged diff contains what looks like a credential"
MSG2 = "  fail \"staged diff contains a JWT or a credentialed URL"

F1A = "f1_dead_awk_after_an_allowlisted_png_akia"
F1J = "f1_dead_awk_after_an_allowlisted_png_jwt"
F1K = "f1_dead_awk_after_an_allowlisted_font"
F1F = "f1_awk_failing_on_a_file"
DEADSET = "(b3_ or f1_) and not dash"


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def lines_of(b):
    return b.split(b"\n")


def edit(b, fn):
    ls = [x.decode("utf-8") for x in lines_of(b)]
    out = fn(ls)
    return "\n".join(out).encode("utf-8")


def chk(ls, n, want):
    got = ls[n - 1].rstrip("\r")
    assert got.startswith(want) or got == want, "line %d is %r, expected %r" % (n, got, want)


def rep(ls, n, old, new, count=1):
    s = ls[n - 1]
    assert s.count(old) == count, "line %d: %r occurs %d times" % (n, old, s.count(old))
    ls[n - 1] = s.replace(old, new)


def m_bs1_removed(ls):
    chk(ls, 211, L211); chk(ls, 216, "fi")
    return ls[:210] + ls[216:]


def m_bs2_removed(ls):
    chk(ls, 217, L211); chk(ls, 222, "fi")
    return ls[:216] + ls[222:]


def m_bs_both_removed(ls):
    chk(ls, 211, L211); chk(ls, 222, "fi")
    return ls[:210] + ls[222:]


def m_probe_gate_restored(ls):
    chk(ls, 211, L211); chk(ls, 222, "fi")
    head = ["if ! printf '+x\\n' | awk \"$ADDED_LINES_AWK\" >/dev/null 2>&1; then\r"]
    return ls[:210] + head + ls[210:222] + ["fi\r"] + ls[222:]


def m_bs1_fail_to_echo(ls):
    chk(ls, 215, MSG1)
    rep(ls, 215, "  fail \"", "  echo \"pre-commit: ")
    return ls


def m_bs1_akia_dropped(ls):
    chk(ls, 214, L214)
    rep(ls, 214, "AKIA[0-9A-Z]{16}|", "")
    return ls


def m_bs1_pk_dropped(ls):
    chk(ls, 214, L214)
    rep(ls, 214, "|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", "")
    return ls


def m_bs1_sk_dropped(ls):
    chk(ls, 214, L214)
    rep(ls, 214, "\\bsk-[A-Za-z0-9_-]{20,}|", "")
    return ls


def m_bs1_xox_dropped(ls):
    chk(ls, 214, L214)
    rep(ls, 214, "|xox[baprs]-[A-Za-z0-9-]{10,}", "")
    return ls


def m_bs2_credurl_dropped(ls):
    chk(ls, 220, L220)
    rep(ls, 220, " -e \"$CREDURL_RE\"", "")
    return ls


def m_bs2_jwt_dropped(ls):
    chk(ls, 220, L220)
    rep(ls, 220, "-e \"$JWT_RE\" ", "")
    return ls


def m_bs_deleted_lines_too(ls):
    # the tr reader selects '-' lines as well (both blocks)
    for n in (212, 218):
        chk(ls, n, L212)
        rep(ls, n, "grep -E '^\\+'", "grep -E '^[-+]'")
    return ls


def m_bs_plus3_filter_dropped(ls):
    for n in (213, 219):
        chk(ls, n, L213)
        rep(ls, n, "   } | LC_ALL=C grep -Ev '^\\+\\+\\+' | \\", "   } | \\")
    return ls


def m_bs_ext_reader_lc_dropped(ls):
    for n in (211, 217):
        chk(ls, n, L211)
        rep(ls, n, "LC_ALL=C grep -E", "grep -E")
    return ls


def m_bs_tr_nul_to_space(ls):
    for n in (212, 218):
        chk(ls, n, L212)
        rep(ls, n, "tr '\\000' '\\n'", "tr '\\000' ' '")
    return ls


def m_bs_messages_swapped(ls):
    chk(ls, 215, MSG1); chk(ls, 221, MSG2)
    ls[214], ls[220] = ls[220], ls[214]
    return ls


def m_bs1_q_dropped(ls):
    chk(ls, 214, L214)
    rep(ls, 214, "   grep -qE '", "   grep -E '")
    return ls


def m_bs2_q_dropped(ls):
    chk(ls, 220, L220)
    rep(ls, 220, "   grep -qE -e", "   grep -E -e")
    return ls


def m_bs_reads_only_textconv_view(ls):
    # tr reader reads only the part of staged.diff after the raw view (sed from the 2nd diff
    # run): approximated by reading the external-diff block only
    for n in (212, 218):
        chk(ls, n, L212)
        rep(ls, n, "LC_ALL=C tr '\\000' '\\n' < \"$STAGED_DIFF\"",
            "LC_ALL=C sed -n '/^@@ external-diff view$/,$p' \"$STAGED_DIFF\"")
    return ls


MUTANTS = {
    "bs1_removed": (m_bs1_removed, [R2], "%s or b3_dead_awk_without_env" % F1A),
    "bs2_removed": (m_bs2_removed, [R2], "%s or b3_missing_awk" % F1J),
    "bs_both_removed": (m_bs_both_removed, [R2], F1A),
    "probe_gate_restored": (m_probe_gate_restored, [R2], F1F),
    "bs1_fail_to_echo": (m_bs1_fail_to_echo, [R2], F1A),
    "bs1_akia_dropped": (m_bs1_akia_dropped, [R2], "%s or b3_dead_awk_without_env" % F1A),
    "bs1_pk_dropped": (m_bs1_pk_dropped, [R2], F1K),
    "bs2_jwt_dropped": (m_bs2_jwt_dropped, [R2], "%s or b3_missing_awk" % F1J),
    "bs_messages_swapped": (m_bs_messages_swapped, [R2], "%s or %s" % (F1A, F1J)),
    "bs1_q_dropped": (m_bs1_q_dropped, [R2], F1A),
    "bs2_q_dropped": (m_bs2_q_dropped, [R2], F1J),
    "bs1_sk_dropped": (m_bs1_sk_dropped, [R2], DEADSET),
    "bs1_xox_dropped": (m_bs1_xox_dropped, [R2], DEADSET),
    "bs2_credurl_dropped": (m_bs2_credurl_dropped, [R2], DEADSET),
    "bs_deleted_lines_too": (m_bs_deleted_lines_too, [R2, PB], "pin_ or deleted"),
    "bs_plus3_filter_dropped": (m_bs_plus3_filter_dropped, [R2], DEADSET),
    "bs_ext_reader_lc_dropped": (m_bs_ext_reader_lc_dropped, [R2], DEADSET + " or a1_"),
    "bs_tr_nul_to_space": (m_bs_tr_nul_to_space, [R2, PB], "i315 or (f1_ and not dash)"),
    "bs_reads_only_ext_block": (m_bs_reads_only_textconv_view, [R2], DEADSET),
}


def make_lf(name):
    fn = MUTANTS[name][0]
    data = open(HOOK, "rb").read()
    new = edit(data, fn)
    out = NOTES + "/mut_%s.lf" % name
    open(out, "wb").write(new.replace(b"\r\n", b"\n"))
    return out


def run(name):
    fn, files, kexpr = MUTANTS[name]
    if os.environ.get("MUT_SH_ONLY") and "not dash" not in kexpr:
        kexpr = "(%s) and not dash" % kexpr
    assert sha(HOOK) == GOOD, "hook is not at the good bytes before %s" % name
    bak = NOTES + "/hook.bak"
    shutil.copyfile(HOOK, bak)
    assert sha(bak) == GOOD
    t0 = time.time()
    rec = {"mutant": name, "k": kexpr, "files": files}
    try:
        data = open(bak, "rb").read()
        new = edit(data, fn)
        assert new != data
        open(HOOK, "wb").write(new)
        rec["mutant_sha"] = sha(HOOK)[:12]
        log = NOTES + "/m_%s.log" % name
        p = subprocess.run([VPY, PYT, "--bound", "600", "--tag", "adv5_m_" + name, "--log", log,
                            "--cwd", WT, "--"] + files + ["-k", kexpr],
                           capture_output=True, timeout=700,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        out = p.stdout.decode("utf-8", "replace")
        rec["pyt"] = [ln for ln in out.splitlines() if ln.startswith("[pyt]")][-1:]
        rec["failed"] = [ln[:200] for ln in out.splitlines() if ln.startswith("FAILED")][:6]
        rec["summary"] = [ln for ln in out.splitlines() if " passed" in ln or " failed" in ln][-1:]
        rec["rc"] = p.returncode
    finally:
        shutil.copyfile(bak, HOOK)
        rec["restored_sha"] = sha(HOOK)[:12]
        rec["restore_ok"] = sha(HOOK) == GOOD
        rec["sec"] = round(time.time() - t0)
    with open(NOTES + "/mut5.jsonl", "a") as fh:
        fh.write(json.dumps(rec) + "\n")
    print(json.dumps(rec), flush=True)
    if not rec["restore_ok"]:
        print("RESTORE MISMATCH - STOP", flush=True)
        sys.exit(3)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--lf"]:
        for n in sys.argv[2:]:
            print(make_lf(n))
    else:
        for n in sys.argv[1:] or list(MUTANTS):
            run(n)
