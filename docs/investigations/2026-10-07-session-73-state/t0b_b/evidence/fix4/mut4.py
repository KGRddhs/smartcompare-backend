"""Round-4 polish (TBF21): prove each new Round-5 node red on its mutant.

One mutant at a time on the worktree hook: shutil byte copy, line-checked
edit (CRLF kept), the bounded runner with -k the killing node only, restore
from the copy, sha256 compare (stop on mismatch). The edits are copied from
the round-5 adversary's mut5.py / lfmut.py (same line numbers, same text).
Results append to mut4.jsonl in this folder.
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
         "d376cb56-c600-4d76-bfdb-9e15feff0cdc/scratchpad/t0b_b/fix4")
PYT = ("C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/"
       "d376cb56-c600-4d76-bfdb-9e15feff0cdc/scratchpad/harness/pyt.py")
VPY = "C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe"
GOOD = os.environ.get("MUT4_GOOD", "4e9a583c76575fe774312152cdf2b53759719c203473325599c9b9fbb3ed4e3b")
R2 = "tests/test_precommit_hook_phase_b_round2.py"
BS = chr(92)
FOUR = ("(" + BS + "bsk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}"
        "|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----)")
L211 = "if { LC_ALL=C grep -E '^" + BS + "+' \"$TMP/staged.ext\""
L212 = ("     LC_ALL=C tr '" + BS + "000' '" + BS + "n' < \"$STAGED_DIFF\" | LC_ALL=C grep -E '^"
        + BS + "+'")
L213 = "   } | LC_ALL=C grep -Ev '^" + BS + "+" + BS + "+" + BS + "+' | " + BS
L214 = "   grep -qE '" + FOUR + "'; then"
L220 = "   grep -qE -e \"$JWT_RE\" -e \"$CREDURL_RE\"; then"


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def edit(b, fn):
    ls = [x.decode("utf-8") for x in b.split(b"\n")]
    return "\n".join(fn(ls)).encode("utf-8")


def chk(ls, n, want):
    got = ls[n - 1].rstrip("\r")
    assert got == want, "line %d is %r, expected %r" % (n, got, want)


def rep(ls, n, old, new):
    s = ls[n - 1]
    assert s.count(old) == 1, "line %d: %r occurs %d times" % (n, old, s.count(old))
    ls[n - 1] = s.replace(old, new)


def bs1_sk_dropped(ls):
    chk(ls, 214, L214)
    rep(ls, 214, BS + "bsk-[A-Za-z0-9_-]{20,}|", "")
    return ls


def bs1_xox_dropped(ls):
    chk(ls, 214, L214)
    rep(ls, 214, "|xox[baprs]-[A-Za-z0-9-]{10,}", "")
    return ls


def bs2_credurl_dropped(ls):
    chk(ls, 220, L220)
    rep(ls, 220, " -e \"$CREDURL_RE\"", "")
    return ls


def m4_lc_all_dropped(ls):
    for n, want in ((211, L211), (212, L212), (213, L213), (217, L211), (218, L212), (219, L213)):
        chk(ls, n, want)
        ls[n - 1] = ls[n - 1].replace("LC_ALL=C ", "")
    return ls


def m1_ext_reader_dropped(ls):
    for n in (211, 217):
        chk(ls, n, L211)
        rep(ls, n, "LC_ALL=C grep -E '^" + BS + "+' \"$TMP/staged.ext\"", "")
    return ls


def bs_ext_reader_lc_dropped(ls):
    for n in (211, 217):
        chk(ls, n, L211)
        rep(ls, n, "LC_ALL=C grep -E", "grep -E")
    return ls


def m2_tr_reader_dropped(ls):
    for n in (212, 218):
        chk(ls, n, L212)
        ls[n - 1] = "     true\r"
    return ls


def bs_deleted_lines_too(ls):
    for n in (212, 218):
        chk(ls, n, L212)
        rep(ls, n, "grep -E '^" + BS + "+'", "grep -E '^[-+]'")
    return ls


def bs_plus3_filter_dropped(ls):
    for n in (213, 219):
        chk(ls, n, L213)
        rep(ls, n, L213, "   } | " + BS)
    return ls


MUTANTS = {
    "bs1_sk_dropped": (bs1_sk_dropped, "r5_dead_awk_sk_key_refused"),
    "bs1_xox_dropped": (bs1_xox_dropped, "r5_dead_awk_slack_token_refused"),
    "bs2_credurl_dropped": (bs2_credurl_dropped, "r5_dead_awk_credentialed_url_refused"),
    "m4_lc_all_dropped": (m4_lc_all_dropped,
                          "r5_dead_awk_utf8_locale_invalid_byte_same_line_akia_refused"),
    "m1_ext_reader_dropped": (m1_ext_reader_dropped,
                              "r5_dead_awk_utf8_locale_ext_diff_invalid_byte_line_refused"),
    "bs_ext_reader_lc_dropped": (bs_ext_reader_lc_dropped,
                                 "r5_dead_awk_utf8_locale_ext_diff_invalid_byte_line_refused"),
    "m2_tr_reader_dropped": (m2_tr_reader_dropped, "r5_dead_awk_hiding_textconv_akia_refused"),
    "bs_deleted_lines_too": (bs_deleted_lines_too,
                             "pin_r5_removing_a_committed_key_line_passes"
                             " or pin_r5_dead_awk_removing_a_committed_key_line_passes"),
    "bs_plus3_filter_dropped": (bs_plus3_filter_dropped,
                                "pin_r5_sk_word_in_a_new_file_path_passes"),
}


def dry():
    data = open(HOOK, "rb").read()
    for name, (fn, _) in MUTANTS.items():
        new = edit(data, fn)
        assert new != data
        print(name, "edit ok", hashlib.sha256(new).hexdigest()[:12],
              "CR", new.count(b"\r"), "delta", len(new) - len(data))


def run(name):
    fn, kexpr = MUTANTS[name]
    assert sha(HOOK) == GOOD, "hook is not at the good bytes before %s" % name
    bak = NOTES + "/hook.bak"
    shutil.copyfile(HOOK, bak)
    assert sha(bak) == GOOD
    t0 = time.time()
    rec = {"mutant": name, "k": kexpr}
    try:
        data = open(bak, "rb").read()
        new = edit(data, fn)
        assert new != data
        open(HOOK, "wb").write(new)
        rec["mutant_sha"] = sha(HOOK)[:12]
        log = NOTES + "/m_%s.log" % name
        p = subprocess.run([VPY, PYT, "--bound", "600", "--tag", "fix4_m_" + name, "--log", log,
                            "--cwd", WT, "--", R2, "-k", kexpr],
                           capture_output=True, timeout=700,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        out = p.stdout.decode("utf-8", "replace")
        rec["pyt"] = [ln for ln in out.splitlines() if ln.startswith("[pyt] tag=")][-1:]
        rec["failed"] = [ln[:160] for ln in out.splitlines() if ln.startswith("FAILED")][:6]
        rec["summary"] = [ln for ln in out.splitlines() if " passed" in ln or " failed" in ln][-1:]
        rec["rc"] = p.returncode
    finally:
        shutil.copyfile(bak, HOOK)
        rec["restored_sha"] = sha(HOOK)
        rec["restore_ok"] = rec["restored_sha"] == GOOD
        rec["sec"] = round(time.time() - t0)
    with open(NOTES + "/mut4.jsonl", "a") as fh:
        fh.write(json.dumps(rec) + "\n")
    print(json.dumps(rec), flush=True)
    if not rec["restore_ok"]:
        print("RESTORE MISMATCH - STOP", flush=True)
        sys.exit(3)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--dry"]:
        dry()
    else:
        for n in sys.argv[1:] or list(MUTANTS):
            run(n)
