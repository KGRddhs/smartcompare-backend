"""Round-5 adversary part 2 (new hook only): gitleaks shims + real gitleaks,
ESLint batching, signals, xtrace, the unit's own commit, CI step replay.
Adapted from the round-4 adv2.py; points at the CURRENT hook LF copy."""

import glob
import json
import os
import subprocess
import sys

import adv5  # sets adv.NOTES / SCR / hooks to this folder
from adv5 import adv

NEW_HOOK = adv.NEW_HOOK
SH, DASH, GL, S, Repo, write, PNG = adv.SH, adv.DASH, adv.GL, adv.S, adv.Repo, adv.write, adv.PNG
NOTES = adv5.NOTES
UNIT = "C:/Users/SynAckITPC/Documents/AI/sc-s71-t0b"
UNIT_CFG = open(UNIT + "/.gitleaks.toml", "rb").read().decode("utf-8").replace("\r\n", "\n")
SPECS = ("C:/Users/SynAckITPC/Documents/AI/sc-docs-70/docs/investigations/"
         "2026-10-05-session-72-state/specs")
HOSTILE = "[extend]\nuseDefault = true\n\n[[allowlists]]\ndescription = \"all\"\npaths = ['''.*''']\n"
NINE = [".githooks/pre-commit", ".github/workflows/ci.yml", ".gitleaks.toml", "tests/test_ci_gates.py",
        "tests/test_gitleaks_config.py", "tests/test_precommit_hook_phase_b.py",
        "tests/test_precommit_hook_phase_b_round2.py", "tests/test_precommit_hook_round2.py",
        "tests/test_secret_scan_static.py"]

GL_SHIM = r'''
log="$SHIM_LOG"
: > "$log/argv"
cfg=""; rp=""; prev=""
for a; do printf '%s\n' "$a" >> "$log/argv"; [ "$prev" = "--config" ] && cfg=$a; [ "$prev" = "--report-path" ] && rp=$a; prev=$a; done
[ -n "$cfg" ] && cp "$cfg" "$log/config"
env | grep -E '^(GITLEAKS_CONFIG|GITLEAKS_CONFIG_TOML|GIT_CONFIG_COUNT|GIT_CONFIG_KEY_[01]|GIT_CONFIG_VALUE_[01])=' > "$log/env"
case "$SHIM_MODE" in
  err0) printf '9:51PM INF x\n9:51PM ERR [git] warning: boom\n' >&2; exit 0;;
  infwrn0) printf '9:51PM INF 1 commits scanned.\n9:51PM WRN leaks found: 0\n' >&2; exit 0;;
  rc1report) printf 'generic-api-key a.txt:1\n' > "$rp"; exit 1;;
  rc1empty) : > "$rp"; exit 1;;
  rc2) exit 2;;
  colorerr0) printf '\033[90m9:51PM\033[0m \033[31mERR\033[0m boom\n' >&2; exit 0;;
  errstdout0) printf '9:51PM ERR [git] boom\n'; exit 0;;
  sleep) sleep 8; exit 0;;
esac
exit 0
'''

R = []
_N = 0


def rec(name, **kw):
    kw["name"] = name
    R.append(kw)
    with open(NOTES + "/adv5b.jsonl", "a") as fh:
        fh.write(json.dumps(kw) + "\n")
    print("%-44s %s" % (name, {k: v for k, v in kw.items() if k != "name"}), flush=True)


def shim_case(mode, head_cfg=None, worktree_cfg=None, shell="sh", extra=None):
    global _N
    _N += 1
    r = Repo("g%d_%s_%s_%s" % (_N, mode, "h" if head_cfg else "n", shell), head_config=head_cfg)
    r.shim_tool("gitleaks", GL_SHIM)
    log = r.base + "/shimlog"
    os.makedirs(log)
    if worktree_cfg is not None:
        write(r.root + "/.gitleaks.toml", worktree_cfg)
    r.add("a.txt", "plain\n")
    env = {"SHIM_LOG": log, "SHIM_MODE": mode}
    env.update(extra or {})
    res = r.run(NEW_HOOK, SH if shell == "sh" else DASH, env)
    cfg = open(log + "/config").read() if os.path.exists(log + "/config") else None
    argv = open(log + "/argv").read().split("\n") if os.path.exists(log + "/argv") else []
    genv = open(log + "/env").read() if os.path.exists(log + "/env") else ""
    return res, cfg, argv, genv


def part_shims():
    exp = {"err0": 1, "infwrn0": 0, "rc1report": 1, "rc1empty": 1, "rc2": 1,
           "colorerr0": "limit", "errstdout0": "limit"}
    for mode, want in exp.items():
        for shell in ("sh", "dash"):
            res, cfg, argv, genv = shim_case(mode, shell=shell)
            msg = [m for m in res["out"].splitlines() if m.startswith("pre-commit:")]
            rec("shim_%s_%s" % (mode, shell), rc=res["rc"], want=want, msg=msg[-2:],
                left=res["left"], nocolor=("--no-color" in argv), config_given=("--config" in argv))


def part_shimcfg():
    for head in (None, UNIT_CFG):
        res, cfg, argv, genv = shim_case("infwrn0", head_cfg=head, worktree_cfg=HOSTILE)
        rec("shim_config_head_%s" % ("unit" if head else "none"), rc=res["rc"],
            cfg_is_default=(cfg == "[extend]\nuseDefault = true\n"),
            cfg_is_head=(cfg is not None and cfg.replace("\r\n", "\n") == (head or "")),
            cfg_is_hostile=(cfg == HOSTILE))
    hp = adv.SCR + "/hostile.toml"
    os.makedirs(adv.SCR, exist_ok=True)
    write(hp, HOSTILE)
    res, cfg, argv, genv = shim_case("infwrn0", head_cfg=UNIT_CFG,
                                     extra={"GITLEAKS_CONFIG": hp, "GITLEAKS_CONFIG_TOML": HOSTILE})
    rec("shim_hostile_GITLEAKS_CONFIG_env", rc=res["rc"], child_env=genv.replace("\n", " | ")[:300],
        cfg_is_head=(cfg is not None and cfg.replace("\r\n", "\n") == UNIT_CFG))


def real_case(name, setup, head_cfg=None, extra=None, shells=("sh",)):
    r = Repo("r_" + name[:24], gl=True, head_config=head_cfg)
    setup(r)
    for shell in shells:
        res = r.run(NEW_HOOK, SH if shell == "sh" else DASH, extra, timeout=420)
        msg = [m for m in res["out"].splitlines() if m.startswith("pre-commit:") or ":" in m][-3:]
        rec("real_%s_%s" % (name, shell), rc=res["rc"], msg=msg, leaked=res["leaked"],
            left=res["left"], sec=res["sec"])


def docs_checkpoint(r):
    dst = "docs/s72/specs"
    lst = []
    for p in sorted(glob.glob(SPECS + "/**/*", recursive=True)):
        if os.path.isfile(p):
            rel = dst + "/" + os.path.relpath(p, SPECS).replace("\\", "/")
            data = open(p, "rb").read()
            write(r.root + "/" + rel, data)
            import hashlib
            lst.append("%s  %s" % (hashlib.sha256(data).hexdigest(), rel))
    write(r.root + "/docs/s72/SHA256SUMS.txt", "\n".join(lst) + "\n")
    r.git("add", "-A")


def unit_commit(r):
    for rel in NINE:
        write(r.root + "/" + rel, open(UNIT + "/" + rel, "rb").read())
    r.git("add", "-A")


def part_real():
    if not GL:
        rec("real_skipped_no_gitleaks")
        return
    def ghp(r):
        r.add("a.txt", "t = %s\n" % S["ghp"])
    def ghp_hostile(r):
        write(r.root + "/.gitleaks.toml", HOSTILE)
        ghp(r)
    def ghp_allow(r):
        r.add("a.txt", "t = %s # gitleaks:allow\n" % S["ghp"])
    def ghp_ignorefile(r):
        write(r.root + "/.gitleaksignore", "a.txt:github-pat:1\n")
        ghp(r)
    def clean_upper_png(r):
        r.add("a.txt", "plain\n")
        r.add("docs/shots/IMG_0002.PNG", PNG)
    def noisy_tc(r):
        tc = r.script("tc.sh", "echo 'driver notice' >&2\ncat \"$1\"\n")
        r.git("config", "diff.n.textconv", "sh " + tc)
        r.add(".gitattributes", "*.txt diff=n\n")
        r.add("a.txt", "plain\n")
    def ghp_color_diff_cfg(r):
        r.git("config", "color.diff", "always")
        ghp(r)
    hp = adv.SCR + "/hostile.toml"
    os.makedirs(adv.SCR, exist_ok=True)
    write(hp, HOSTILE)
    real_case("ghp_head_unit_hostile_wt", ghp_hostile, UNIT_CFG, shells=("sh", "dash"))
    real_case("ghp_gitleaks_allow", ghp_allow, UNIT_CFG, shells=("sh", "dash"))
    real_case("ghp_gitleaksignore", ghp_ignorefile, UNIT_CFG, shells=("sh", "dash"))
    real_case("ghp_env_hostile_cfg", ghp, UNIT_CFG, shells=("sh", "dash"),
              extra={"GITLEAKS_CONFIG": hp, "GITLEAKS_CONFIG_TOML": HOSTILE})
    real_case("clean_upper_png_docs", clean_upper_png, UNIT_CFG, shells=("sh", "dash"))
    real_case("noisy_textconv_clean", noisy_tc, UNIT_CFG, shells=("sh", "dash"))
    real_case("ghp_repo_color_diff_always", ghp_color_diff_cfg, UNIT_CFG)
    real_case("docs_checkpoint_head_unit", docs_checkpoint, UNIT_CFG, shells=("sh", "dash"))
    real_case("docs_checkpoint_head_none", docs_checkpoint, None)
    real_case("unit_nine_files_head_none", unit_commit, None, shells=("sh", "dash"))


def part_eslint():
    for nfiles, partial in ((70, 0), (1, 1), (12, 11), (129, 0), (70, 3)):
        name = "eslint_%d_%d" % (nfiles, partial)
        r = Repo(name)
        log = r.base + "/eslint.log"
        write(r.root + "/SmartCompareApp/node_modules/eslint/bin/eslint.js",
              "const fs=require('fs');const a=process.argv.slice(2);"
              "fs.appendFileSync(%r, JSON.stringify(a)+'\\n');process.exit(0);\n" % log)
        for i in range(nfiles):
            write(r.root + "/SmartCompareApp/src/b/F%03d.ts" % i, "export const a%d = %d;\n" % (i, i))
        r.git("add", "SmartCompareApp/src")
        for i in range(partial):
            write(r.root + "/SmartCompareApp/src/b/F%03d.ts" % i, "export const a%d = %d; // wt\n" % (i, i))
        res = r.run(NEW_HOOK, SH, timeout=420)
        calls = []
        if os.path.exists(log):
            calls = [json.loads(x) for x in open(log).read().splitlines()]
        rec(name, rc=res["rc"], ncalls=len(calls),
            sizes=[len([a for a in c if a.startswith("src/")]) for c in calls],
            stdin_calls=sum(1 for c in calls if "--stdin" in c),
            msg=[m for m in res["out"].splitlines() if m.startswith("pre-commit:")][-2:], sec=res["sec"])


def part_signals():
    for shell, sname in ((SH, "sh"), (DASH, "dash")):
        for sig in ("TERM", "HUP"):
            r = Repo("sig_%s_%s" % (sig, sname))
            r.shim_tool("gitleaks", GL_SHIM)
            log = r.base + "/shimlog"
            os.makedirs(log)
            r.add("a.txt", "k plain\n")
            env = dict(r.env)
            env.update({"SHIM_LOG": log, "SHIM_MODE": "sleep"})
            cmd = '%s "%s" & p=$!; sleep 5; kill -%s $p; wait $p; echo "rc=$?"' % (
                os.path.basename(shell).replace(".exe", ""), NEW_HOOK, sig)
            p = subprocess.run([shell, "-c", cmd], cwd=r.root, env=env, capture_output=True,
                               timeout=120, stdin=subprocess.DEVNULL)
            rec("signal_%s_%s" % (sig, sname), out=(p.stdout + p.stderr).decode("utf-8", "replace")[-200:],
                tmpdir_left=os.listdir(env["TMPDIR"]),
                gitdir_left=[x for x in os.listdir(r.root + "/.git") if x.startswith("qaren")])


def part_xtrace():
    for shell, sname in ((SH, "sh"), (DASH, "dash")):
        r = Repo("xt_env_%s" % sname)
        write(r.root + "/.env", "MY_API_KEY=%s\n" % S["envv"])
        r.add("a.txt", "v %s\n" % S["envv"])
        res = r.run(NEW_HOOK, shell, flags=["-x"])
        rec("xtrace_env_value_%s" % sname, rc=res["rc"], leaked=res["leaked"])
        r1 = Repo("xt_akia_%s" % sname)
        r1.add("a.txt", "k %s\n" % S["akia"])
        res1 = r1.run(NEW_HOOK, shell, flags=["-x"])
        rec("xtrace_staged_akia_%s" % sname, rc=res1["rc"], leaked=res1["leaked"])
        r2 = Repo("xt_head_%s" % sname)
        blob = S["akia"][:12].encode() + b"\x00\x00" + b"rest"
        r2.add("docs/k.png", blob)
        p = subprocess.run([shell, "-x", NEW_HOOK], cwd=r2.root, env=r2.env, capture_output=True,
                           stdin=subprocess.DEVNULL, timeout=180)
        rec("xtrace_binary_head_%s" % sname, rc=p.returncode,
            head_hex_in_trace=(blob[:12].hex() in (p.stdout + p.stderr).decode("utf-8", "replace")))


def ci_step_text():
    import yaml
    doc = yaml.safe_load(open(UNIT + "/.github/workflows/ci.yml", encoding="utf-8"))
    steps = doc["jobs"]["secret-scan"]["steps"]
    return [s for s in steps if s.get("name", "").startswith("gitleaks over")][0]["run"]


def part_ci():
    if not GL:
        return
    step = ci_step_text()
    for case in ("pr_clean", "pr_ghp", "pr_noisy_textconv_ghp", "pr_base_missing", "push_ghp",
                 "pr_head_cfg_widened_ghp"):
        r = Repo("ci_" + case, gl=True, head_config=UNIT_CFG)
        base = r.git("rev-parse", "HEAD").strip()
        if case == "pr_noisy_textconv_ghp":
            tc = r.script("tc.sh", "echo 'driver notice' >&2\ncat \"$1\"\n")
            r.git("config", "diff.n.textconv", "sh " + tc)
            r.add(".gitattributes", "*.txt diff=n\n")
        if case == "pr_head_cfg_widened_ghp":
            r.add(".gitleaks.toml", HOSTILE)
        content = "t = %s\n" % S["ghp"] if "ghp" in case else "plain\n"
        r.add("a.txt", content)
        r.git("commit", "-q", "--no-verify", "-m", "c")
        head = r.git("rev-parse", "HEAD").strip()
        rt = r.base + "/runner"
        os.makedirs(rt)
        write(rt + "/gitleaks", "#!/bin/sh\nexec '%s' \"$@\"\n" % GL.replace("\\", "/"))
        if case.startswith("push"):
            env = {"EVENT_NAME": "push", "PR_BASE": "", "PR_HEAD": "", "PUSH_BEFORE": base,
                   "PUSH_SHA": head, "RUNNER_TEMP": rt}
        else:
            env = {"EVENT_NAME": "pull_request", "PR_BASE": base, "PR_HEAD": head,
                   "PUSH_BEFORE": "", "PUSH_SHA": head, "RUNNER_TEMP": rt}
        if case == "pr_base_missing":
            env["PR_BASE"] = "1234567890abcdef1234567890abcdef12345678"
        e = dict(r.env)
        e.update(env)
        p = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", step], cwd=r.root, env=e,
                           capture_output=True, timeout=240, stdin=subprocess.DEVNULL)
        log = open(rt + "/gitleaks.log", "rb").read() if os.path.exists(rt + "/gitleaks.log") else b""
        out, leaked = adv.redact((p.stdout + p.stderr).decode("utf-8", "replace"))
        rec("ci_" + case, rc=p.returncode, ansi_in_log=(b"\x1b" in log),
            plain_ERR=(b" ERR " in log), leaked=leaked,
            tail=[ln for ln in out.splitlines() if "::error::" in ln or "secret-scan range" in ln
                  or "leaks found" in ln or "ERR" in ln][-4:])


def main():
    os.makedirs(adv.SCR, exist_ok=True)
    for part in sys.argv[1:]:
        globals()["part_" + part]()


if __name__ == "__main__":
    main()
