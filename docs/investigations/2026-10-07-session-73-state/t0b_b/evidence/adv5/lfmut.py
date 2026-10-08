"""Replay scenarios on LF byte copies of mutants (never the worktree):
current hook vs mutant, sh and dash. Usage: lfmut.py MUTANT:scen1,scen2 ..."""

import json
import os
import subprocess
import sys

import adv5
from adv5 import adv, S, write, dead_awk, nscen, UTF8
import mut5
from mut5 import chk, rep, L211, L212, L213, edit

NOTES = adv5.NOTES


def m1_ext_reader_dropped(ls):
    for n in (211, 217):
        chk(ls, n, L211)
        rep(ls, n, "LC_ALL=C grep -E '^\\+' \"$TMP/staged.ext\"", "")
    return ls


def m2_tr_reader_dropped(ls):
    for n in (212, 218):
        chk(ls, n, L212)
        ls[n - 1] = "     true\r"
    return ls


def m4_lc_all_dropped(ls):
    for n in (211, 212, 213, 217, 218, 219):
        ls[n - 1] = ls[n - 1].replace("LC_ALL=C ", "")
    return ls


EXTRA = {"m1_ext_reader_dropped": m1_ext_reader_dropped,
         "m2_tr_reader_dropped": m2_tr_reader_dropped,
         "m4_lc_all_dropped": m4_lc_all_dropped}


@nscen
def da_sk_only(r):
    dead_awk(r)
    r.add("a.txt", "t %s\n" % S["sk"])


@nscen
def da_xox_only(r):
    dead_awk(r)
    r.add("a.txt", "t %s\n" % S["xox"])


@nscen
def da_credurl_only(r):
    dead_awk(r)
    r.add("a.txt", "db %s/x\n" % S["url"])


@nscen
def wa_sk_learn_path_header(r):
    r.add("docs/sk- learn-integration-notes-2026.md", "plain notes\n")


def lf_of(name):
    p = NOTES + "/mut_%s.lf" % name
    if not os.path.exists(p):
        fn = EXTRA.get(name) or mut5.MUTANTS[name][0]
        data = open(NOTES + "/hook.lf", "rb").read()  # never the worktree (mutants run there)
        open(p, "wb").write(edit(data, fn).replace(b"\r\n", b"\n"))
    return p


def main():
    os.makedirs(adv.SCR, exist_ok=True)
    out = []
    for spec in sys.argv[1:]:
        mname, scens = spec.split(":")
        mp = lf_of(mname)
        for sc in scens.split(","):
            r = adv.Repo(("x%s_%s" % (mname[:10], sc))[:40])
            extra = adv.SCEN[sc](r) or {}
            res = {"mutant": mname, "scen": sc,
                   "cur_sh": r.run(adv.NEW_HOOK, adv.SH, extra)["rc"],
                   "base_sh": r.run(adv.BASE_HOOK, adv.SH, extra)["rc"]}
            for sk, shell in (("sh", adv.SH), ("dash", adv.DASH)):
                rr = r.run(mp, shell, extra)
                res["mut_" + sk] = rr["rc"]
                res["mut_leak_" + sk] = rr["leaked"]
            res["verdict"] = ("KILLED-BY-SCENARIO" if res["mut_sh"] != res["cur_sh"] or res["mut_dash"] != res["cur_sh"]
                              else "same")
            print(json.dumps(res), flush=True)
            out.append(res)
            with open(NOTES + "/lfmut.jsonl", "a") as fh:
                fh.write(json.dumps(res) + "\n")


if __name__ == "__main__":
    main()
