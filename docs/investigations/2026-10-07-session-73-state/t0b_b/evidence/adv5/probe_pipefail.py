"""SHELLOPTS=pipefail (bash imports it from the environment): early grep -q match + SIGPIPE upstream."""
import json
import adv5
from adv5 import adv, S

import os
os.makedirs(adv.SCR, exist_ok=True)
out = []
for case in ("big_first_line_akia", "small_akia"):
    r = adv.Repo("pf_" + case)
    if case.startswith("big"):
        body = "k %s\n" % S["akia"] + "".join("line %07d plain text here\n" % i for i in range(120000))
    else:
        body = "k %s\n" % S["akia"]
    r.add("a.txt", body)
    for dead in (False, True):
        if dead:
            r.shim_tool("awk", "exit 1\n")
        res = {"case": case, "dead_awk": dead}
        for hk, hook in (("base", adv.BASE_HOOK), ("new", adv.NEW_HOOK)):
            for env in ({}, {"SHELLOPTS": "pipefail"}):
                rr = r.run(hook, adv.SH, env)
                res["%s_%s" % (hk, "pf" if env else "plain")] = rr["rc"]
                res.setdefault("leak", []).extend(rr["leaked"])
        print(json.dumps(res), flush=True)
        out.append(res)
open(adv5.NOTES + "/probe_pipefail.json", "w").write(json.dumps(out, indent=1))
