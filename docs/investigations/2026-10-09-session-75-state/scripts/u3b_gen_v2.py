"""Generate __tests__/consent/aiConsentV2.s75.test.ts from the ASCII template.

UB-R19: the Arabic strings are produced by encode('ascii', 'backslashreplace')
from U3B_AR_COPY.txt and the OPT_OUT_AR regex of aiProcessingConsent.s69, the
file is written by open().write, and the result is byte-checked (0 bytes > 127).
No non-ASCII character is ever printed.
"""
import hashlib
import re
import sys

NL = chr(10)
BS = chr(92)
NOTES = "C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/f9970d11-1fa0-400e-9fb3-dd91f335e519/scratchpad/u3b/red/"
SPECS = "C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/f9970d11-1fa0-400e-9fb3-dd91f335e519/scratchpad/specs/"
APP = "C:/Users/SynAckITPC/Documents/AI/sc-s74-ct/SmartCompareApp/"


def esc(s):
    return s.encode("ascii", "backslashreplace").decode("ascii")


def main():
    ar_text = open(SPECS + "U3B_AR_COPY.txt", "rb").read().decode("utf-8")
    lines = ar_text.split(NL)
    s1 = lines[4].strip()
    s2 = lines[7].strip()
    assert len(s1) == 145 and len(s2) == 482, (len(s1), len(s2))
    assert s2.count(s1) == 1
    ar_final = s2.rsplit(". ", 1)[1]
    assert len(ar_final) == 49, len(ar_final)
    assert s2.endswith(s1 + " " + ar_final)

    suite = open(APP + "__tests__/consent/aiProcessingConsent.s69.test.tsx", "rb").read().decode("utf-8")
    m = re.search(r"const OPT_OUT_AR = /(.*?)/;", suite)
    assert m, "OPT_OUT_AR not found in the s69 suite"
    opt_out_ar = m.group(1)
    words = opt_out_ar.split("|")
    assert len(words) == 4, words

    template = open(NOTES + "aiConsentV2.template.txt", "rb").read().decode("ascii")
    out = template.replace("@BS@", BS)
    out = out.replace("__AR_SENTENCE__", esc(s1))
    out = out.replace("__AR_FINAL__", esc(ar_final))
    out = out.replace("__AR_SECTION2__", esc(s2))
    out = out.replace("__OPT_OUT_AR__", esc(opt_out_ar))
    for i, w in enumerate(words):
        out = out.replace("__AR_WORD_%d__" % i, esc(w))
    assert "__" + "AR_" not in out and "@BS@" not in out, "placeholder left"
    data = out.replace(chr(13), "").encode("ascii")
    high = sum(1 for b in data if b > 127)
    assert high == 0, high
    for dest in (NOTES + "aiConsentV2.s75.test.ts", APP + "__tests__/consent/aiConsentV2.s75.test.ts"):
        with open(dest, "wb") as fh:
            fh.write(data)
        back = open(dest, "rb").read()
        assert back == data
        print(dest, "bytes", len(back), "bytes>127", sum(1 for b in back if b > 127),
              "crlf", back.count(b"\r\n"), "sha256", hashlib.sha256(back).hexdigest())
    # round-trip: the escapes decode back to the source strings
    dec = re.search(r"const AR_SECTION2 = '(.*)';", data.decode("ascii")).group(1)
    assert dec.encode("ascii").decode("unicode_escape") == s2
    dec1 = re.search(r"const AR_SENTENCE = '(.*)';", data.decode("ascii")).group(1)
    assert dec1.encode("ascii").decode("unicode_escape") == s1
    print("round-trip OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
