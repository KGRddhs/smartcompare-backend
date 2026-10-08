"""Round-5 adversary: base (845ece15) vs new hook under sh and dash.

Reuses the 71 scenarios of the round-4 harness (adv.py, imported read-only)
and adds backstop fail-open scenarios. Hermetic scratch repos under this
notes folder (GIT_* dropped, GIT_CONFIG_NOSYSTEM=1, tmp HOME / XDG / TMPDIR).
Sentinels are runtime-built and redacted from every stored output.
"""

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

OLD = ("C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/"
       "2979ae70-049c-4e99-87ac-061e7d245fff/scratchpad/t0b_b/adv-final")
sys.path.insert(0, OLD)
import adv  # noqa: E402

NOTES = ("C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/"
         "d376cb56-c600-4d76-bfdb-9e15feff0cdc/scratchpad/t0b_b/adv5")
adv.NOTES = NOTES
adv.BASE_HOOK = NOTES + "/base.lf"
adv.NEW_HOOK = os.environ.get("ADV_NEW_HOOK", NOTES + "/hook.lf")
adv.SCR = NOTES + "/s" + adv.RUN_ID[-5:]

S = adv.S
rot13 = adv.rot13
write = adv.write
PNG = adv.PNG
TTF = adv.TTF
scen = adv.scen
NEW = []


def nscen(fn):
    NEW.append(fn.__name__)
    return scen(fn)


def dead_awk(r):
    r.shim_tool("awk", "exit 1\n")


def ext_dec(r):
    # an external diff that prints the rot13-decoded new file as + lines
    return r.script("ext.sh", "tr 'A-Za-z' 'N-ZA-Mn-za-m' < \"$5\" | sed 's/^/+/'\n")


UTF8 = {"LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"}


@nscen
def da_textattr_nul_same_line_akia(r):
    dead_awk(r)
    r.add(".gitattributes", "*.txt diff\n")
    r.add("a.txt", b"x\x00 k " + S["akia"].encode() + b"\n")


@nscen
def da_textattr_nul_line_then_akia(r):
    dead_awk(r)
    r.add(".gitattributes", "*.txt diff\n")
    r.add("a.txt", b"x\x00y\nk " + S["akia"].encode() + b"\n")


@nscen
def wa_textattr_nul_same_line_akia(r):
    r.add(".gitattributes", "*.txt diff\n")
    r.add("a.txt", b"x\x00 k " + S["akia"].encode() + b"\n")


@nscen
def da_utf8_ff_same_line_akia(r):
    dead_awk(r)
    r.add("a.txt", b"caf\xff k " + S["akia"].encode() + b"\n")
    return dict(UTF8)


@nscen
def da_utf8_ff_earlier_line_akia(r):
    dead_awk(r)
    r.add("a.txt", b"caf\xff\n")
    r.add("z.txt", "k %s\n" % S["akia"])
    return dict(UTF8)


@nscen
def da_crlf_akia(r):
    dead_awk(r)
    r.add("a.txt", b"line\r\nk " + S["akia"].encode() + b"\r\n")


@nscen
def da_long_line_akia(r):
    dead_awk(r)
    r.add("big.txt", "x" * 300000 + " " + S["akia"] + "\n")


@nscen
def da_plusplus_akia(r):
    dead_awk(r)
    r.add("a.txt", "++%s\n" % S["akia"])


@nscen
def da_noprefix_akia(r):
    dead_awk(r)
    r.git("config", "diff.noprefix", "true")
    r.add("a.txt", "k %s\n" % S["akia"])


@nscen
def da_rename_edit_akia(r):
    dead_awk(r)
    r.add("old.txt", "plain\n" * 20)
    r.git("commit", "-q", "--no-verify", "-m", "x")
    r.git("mv", "old.txt", "new.txt")
    r.add("new.txt", "plain\n" * 20 + "k %s\n" % S["akia"])


@nscen
def da_deleted_line_akia(r):
    dead_awk(r)
    r.add("a.txt", "k %s\n" % S["akia"])
    r.git("commit", "-q", "--no-verify", "-m", "x")
    r.add("a.txt", "plain\n")


@nscen
def da_ext_reveal_akia(r):
    dead_awk(r)
    r.git("config", "diff.dx.command", "sh " + ext_dec(r))
    r.add(".gitattributes", "*.enc diff=dx\n")
    r.add("s.enc", "k %s\n" % rot13(S["akia"]))


@nscen
def da_ext_reveal_ff_same_line_utf8(r):
    dead_awk(r)
    r.git("config", "diff.dx.command", "sh " + ext_dec(r))
    r.add(".gitattributes", "*.enc diff=dx\n")
    r.add("s.enc", b"\xff k " + rot13(S["akia"]).encode() + b"\n")
    return dict(UTF8)


@nscen
def da_ext_empty_akia(r):
    dead_awk(r)
    ext = r.script("ext.sh", "exit 0\n")
    r.add("s.txt", "k %s\n" % S["akia"])
    return {"GIT_EXTERNAL_DIFF": ext}


@nscen
def da_textconv_hide_akia(r):
    dead_awk(r)
    r.git("config", "diff.h.textconv", "true")
    r.add(".gitattributes", "*.txt diff=h\n")
    r.add("s.txt", "k %s\n" % S["akia"])


@nscen
def da_textconv_reveal_jwt(r):
    dead_awk(r)
    tc = r.script("tc.sh", "tr 'A-Za-z' 'N-ZA-Mn-za-m' < \"$1\"\n")
    r.git("config", "diff.rot.textconv", "sh " + tc)
    r.add(".gitattributes", "*.enc diff=rot\n")
    r.add("s.enc", "k %s\n" % rot13(S["jwt"]))


@nscen
def da_color_ui_always_akia(r):
    dead_awk(r)
    r.git("config", "color.ui", "always")
    r.add("a.txt", "k %s\n" % S["akia"])


@nscen
def da_png_then_credurl(r):
    dead_awk(r)
    r.add("docs/a.png", PNG)
    r.add("z.txt", "db %s/x\n" % S["url"])


@nscen
def da_png_then_xox_sk(r):
    dead_awk(r)
    r.add("docs/a.png", PNG)
    r.add("y.txt", "t %s\n" % S["xox"])
    r.add("z.txt", "t %s\n" % S["sk"])


@nscen
def da_env_value_after_png(r):
    dead_awk(r)
    write(r.root + "/.env", "MY_API_KEY=%s\n" % S["envv"])
    r.add("docs/a.png", PNG)
    r.add("a.txt", "v %s\n" % S["envv"])


@nscen
def da_dead_tr_akia(r):
    dead_awk(r)
    r.shim_tool("tr", "exit 1\n")
    r.add("a.txt", "k %s\n" % S["akia"])


@nscen
def dead_tr_only_akia(r):
    r.shim_tool("tr", "exit 1\n")
    r.add("a.txt", "k %s\n" % S["akia"])


@nscen
def dead_tr_only_dotenv(r):
    r.shim_tool("tr", "exit 1\n")
    r.add("app/.env", "A=b\n")


@nscen
def dead_grep_akia(r):
    r.shim_tool("grep", "exit 1\n")
    r.add("a.txt", "k %s\n" % S["akia"])


@nscen
def da_utf16_key_png_magic(r):
    dead_awk(r)
    r.add("docs/a.png", bytes.fromhex("89504e470d0a1a0a") + ("k " + S["akia"] + "\n").encode("utf-16-le"))


@nscen
def wa_png_with_plus_akia_after_nul(r):
    # honest-looking asset whose bytes carry "\n+AKIA..." after a NUL: both readers
    r.add("docs/a.png", PNG + b"\x00" + S["akia"].encode() + b"\n")


@nscen
def wa_clean_png_ttf_utf8(r):
    r.add("docs/a.png", PNG)
    r.add("SmartCompareApp/assets/fonts/X.TTF", TTF)
    r.add("a.txt", b"caf\xc3\xa9 plain\n")
    return dict(UTF8)


@nscen
def wa_clean_invalid_utf8_text(r):
    r.add("a.txt", b"caf\xff plain\n")
    return dict(UTF8)


@nscen
def wa_honest_plus_lines(r):
    r.add("CHANGELOG.md", "+ added a thing\n++ double plus\n+++ triple\n")


@nscen
def wa_sk_musk_slug(r):
    r.add("a.json", '{"u": "https://x.example/products/white-musk-07-edp-body-lotion-gift-set"}\n')


def run_scenario(name):
    fn = adv.SCEN[name]
    r = adv.Repo(name[:28])
    extra = fn(r) or {}
    res = {"name": name}
    for hk, hook in (("base", adv.BASE_HOOK), ("new", adv.NEW_HOOK)):
        for sk, shell in (("sh", adv.SH), ("dash", adv.DASH)):
            try:
                res[hk + "_" + sk] = r.run(hook, shell, extra)
            except subprocess.TimeoutExpired:
                res[hk + "_" + sk] = {"rc": "TIMEOUT"}
    return res


def main():
    args = sys.argv[1:]
    if args == ["NEW"]:
        names = list(NEW)
    elif args == ["OLD"]:
        names = [n for n in adv.SCEN if n not in NEW]
    else:
        names = args or list(adv.SCEN)
    os.makedirs(adv.SCR, exist_ok=True)
    t0 = time.time()
    results = []
    stream = open(NOTES + "/adv5_%s.jsonl" % adv.RUN_ID, "a")
    with ThreadPoolExecutor(max_workers=int(os.environ.get("ADV_WORKERS", "4"))) as ex:
        futs = [ex.submit(run_scenario, n) for n in names]
        for f in as_completed(futs):
            try:
                res = f.result()
            except Exception as exc:  # harness failure, recorded
                res = {"name": "HARNESS-ERROR", "err": repr(exc)[:300]}
                print(res, flush=True)
                continue
            results.append(res)
            stream.write(json.dumps(res) + "\n")
            stream.flush()
    viol = []
    lines = []
    for res in sorted(results, key=lambda x: x["name"]):
        rcs = {k: res[k]["rc"] for k in ("base_sh", "base_dash", "new_sh", "new_dash")}
        tag = ""
        for sk in ("sh", "dash"):
            if rcs["base_" + sk] != 0 and rcs["new_" + sk] == 0:
                tag = "ADDITIVITY-VIOLATION"
        if rcs["base_sh"] == 0 and rcs["new_sh"] != 0:
            tag += " NEW-REFUSAL"
        if rcs["new_sh"] != rcs["new_dash"]:
            tag += " SHELL-DIFF"
        leaks = sorted(set(sum((res[k].get("leaked", []) for k in rcs), [])))
        lefts = sorted(set(sum((res[k].get("left", []) for k in rcs), [])))
        if tag.startswith("ADDITIVITY"):
            viol.append(res["name"])
        msg = res["new_sh"].get("out", "").strip().splitlines()
        msg = [m for m in msg if m.startswith("pre-commit:")]
        lines.append("%-36s base=%s/%s new=%s/%s %s%s%s | %s" % (
            res["name"], rcs["base_sh"], rcs["base_dash"], rcs["new_sh"], rcs["new_dash"], tag,
            (" LEAK=" + ",".join(leaks)) if leaks else "", (" LEFT=" + ",".join(lefts)) if lefts else "",
            (msg[-1][:90] if msg else "")))
    out = NOTES + "/adv5_%s.json" % adv.RUN_ID
    with open(out, "w") as fh:
        json.dump(results, fh, indent=1)
    print("\n".join(lines))
    print("violations:", viol)
    print("scenarios=%d elapsed=%ds json=%s" % (len(results), time.time() - t0, out))


if __name__ == "__main__":
    main()
