"""Fable's closing pins for W4-14 (adversary r2's three minors, test rows only).
Count-checked, CRLF-aware edits; every edit must match exactly once. Run from anywhere."""
import io, os, sys, hashlib

WT = "C:/Users/SynAckITPC/Documents/AI/sc-w4-14"


def edit(rel, old, new, count=1):
    p = os.path.join(WT, rel)
    raw = io.open(p, "rb").read()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8")
    if crlf:
        text = text.replace("\r\n", "\n")
    n = text.count(old)
    assert n == count, (rel, "expected", count, "matches, found", n, old[:80])
    text = text.replace(old, new)
    out = text.replace("\n", "\r\n") if crlf else text
    io.open(p, "wb").write(out.encode("utf-8"))
    print("edited", rel, "crlf" if crlf else "lf", "sha16", hashlib.sha256(out.encode("utf-8")).hexdigest()[:16])


PY = "tests/test_arabic_verdict_output_w414.py"
TS = "SmartCompareApp/__tests__/i18n/referralExpiryPlurals.w414.test.ts"

# P1 - test_38: unrecognised values read as OFF (adversary r2 X4).
edit(PY,
     '    ("", False), ("0", False), ("false", False), ("off", False), (None, False),\n'
     '])\n'
     'def test_38_red_flag_reader_values_and_per_call(monkeypatch, raw, expected):\n',
     '    ("", False), ("0", False), ("false", False), ("off", False), (None, False),\n'
     '    # Fable pin (adversary r2 X4): an UNRECOGNISED value reads as OFF - the reader is\n'
     '    # an allowlist of the house truthy set, never "anything that is not falsy".\n'
     '    ("2", False), ("enabled", False), ("y", False), ("t", False), ("tru", False),\n'
     '    ("TRUE", True), ("On", True), (" yes ", True),\n'
     '])\n'
     'def test_38_red_flag_reader_values_and_per_call(monkeypatch, raw, expected):\n')

# P3 - the capture harness can return the RESULT too (adversary r2 X2).
edit(PY,
     '             scores="A=70 B=60"):\n',
     '             scores="A=70 B=60", with_result=False):\n')
edit(PY,
     '            loop.run_until_complete(es.generate_comparison(\n'
     '                p1, p2, "bahrain", "value", user_preferences=prefs, scores_summary=scores,\n'
     '                category=category, demographics_profile=demographics,\n'
     '                comparison_quality=quality, **extra))\n',
     '            result = loop.run_until_complete(es.generate_comparison(\n'
     '                p1, p2, "bahrain", "value", user_preferences=prefs, scores_summary=scores,\n'
     '                category=category, demographics_profile=demographics,\n'
     '                comparison_quality=quality, **extra))\n')
edit(PY,
     '    return {"system": captured["system"], "user": captured["user"], "kwargs": captured["kwargs"]}\n',
     '    out = {"system": captured["system"], "user": captured["user"], "kwargs": captured["kwargs"]}\n'
     '    if with_result:\n'
     '        out["result"] = result  # (comparison, usage) - the RETURN, for test_40\n'
     '    return out\n')

# test_40 appended at the end of the file.
p = os.path.join(WT, PY)
raw = io.open(p, "rb").read()
crlf = b"\r\n" in raw
text = raw.decode("utf-8").replace("\r\n", "\n")
assert "def test_40_" not in text
if not text.endswith("\n"):
    text += "\n"
text += (
    "\n\n"
    "# ------------------------------------------------------------ Fable pin (adversary r2 X2)\n"
    "\n\n"
    '@pytest.mark.parametrize("category", ["fragrances", "electronics", "other"])\n'
    '@pytest.mark.parametrize("lang", [None, "en", "ar"])\n'
    "def test_40_pin_flag_off_result_is_identical_not_only_the_prompt(monkeypatch, category, lang):\n"
    '    """PIN (Fable, adversary r2 X2). Flag OFF: the (comparison, usage) that\n'
    "    generate_comparison RETURNS for output_lang None / 'en' / 'ar' equals the no-kwarg\n"
    "    base - the identity claim covers the result, not only the prompt and the call\n"
    "    kwargs (kills an output-side fork such as `if output_lang == 'ar':\n"
    "    parsed[...] = ...` with no flag check). Flag ON with None / 'en' is identical too;\n"
    "    flag ON + 'ar' changes the PROMPT only, never the stubbed result.\"\"\"\n"
    '    _require_param(_es().generate_comparison, "output_lang", "generate_comparison")\n'
    "    monkeypatch.delenv(_FLAG, raising=False)\n"
    '    base = _capture(category, None, "normal", with_result=True)\n'
    '    got = _capture(category, None, "normal", output_lang=lang, with_result=True)\n'
    "    assert got == base\n"
    '    monkeypatch.setenv(_FLAG, "true")\n'
    '    on = _capture(category, None, "normal", output_lang=lang, with_result=True)\n'
    '    if lang == "ar":\n'
    '        assert on["result"] == base["result"], "flag ON + ar changed the RESULT, not only the prompt"\n'
    "    else:\n"
    "        assert on == base\n"
)
out = text.replace("\n", "\r\n") if crlf else text
io.open(p, "wb").write(out.encode("utf-8"))
print("appended test_40 to", PY, "sha16", hashlib.sha256(out.encode("utf-8")).hexdigest()[:16])

# P2 - the _two / _few / _many referral forms pinned by value (adversary r2 C3).
edit(TS,
     "    // The rejected R2 copy never ships in either language.\n"
     "    expect(Object.values(enCat).filter((v) => /^Expires now$/i.test(v))).toEqual([]);\n"
     "  });\n"
     "});\n",
     r"""    // The rejected R2 copy never ships in either language.
    expect(Object.values(enCat).filter((v) => /^Expires now$/i.test(v))).toEqual([]);
  });

  // Fable pin (adversary r2 C3): the _two / _few / _many forms are pinned by VALUE too
  // (the R2 pin covered _zero only, so a wrong dual/plural copy survived). Arabic as
  // \u escapes of the shipped catalog text; _few/_many keep {{count}}.
  const R2_PLURALS: [string, string, string, string, string][] = [
    // family, EN _two, AR _two (count 2), AR _few (count 3), AR _many (count 11)
    ['referrals.bonus.expiresInDays', 'Expires in 2 days',
      '\u062a\u0646\u062a\u0647\u064a \u062e\u0644\u0627\u0644 \u064a\u0648\u0645\u064a\u0646',
      '\u062a\u0646\u062a\u0647\u064a \u062e\u0644\u0627\u0644 {{count}} \u0623\u064a\u0627\u0645',
      '\u062a\u0646\u062a\u0647\u064a \u062e\u0644\u0627\u0644 {{count}} \u064a\u0648\u0645\u064b\u0627'],
    ['referrals.bonus.expiresInHours', 'Expires in 2 hours',
      '\u062a\u0646\u062a\u0647\u064a \u062e\u0644\u0627\u0644 \u0633\u0627\u0639\u062a\u064a\u0646',
      '\u062a\u0646\u062a\u0647\u064a \u062e\u0644\u0627\u0644 {{count}} \u0633\u0627\u0639\u0627\u062a',
      '\u062a\u0646\u062a\u0647\u064a \u062e\u0644\u0627\u0644 {{count}} \u0633\u0627\u0639\u0629'],
    ['referrals.bonus.expiresInMinutes', 'Expires in 2 minutes',
      '\u062a\u0646\u062a\u0647\u064a \u062e\u0644\u0627\u0644 \u062f\u0642\u064a\u0642\u062a\u064a\u0646',
      '\u062a\u0646\u062a\u0647\u064a \u062e\u0644\u0627\u0644 {{count}} \u062f\u0642\u0627\u0626\u0642',
      '\u062a\u0646\u062a\u0647\u064a \u062e\u0644\u0627\u0644 {{count}} \u062f\u0642\u064a\u0642\u0629'],
  ];

  it('PIN (Fable, adversary r2 C3): the _two/_few/_many forms carry the ruled copy and ar renders them at 2, 3 and 11', () => {
    const t = arT();
    const enCat = en as unknown as Record<string, string>;
    const arCat = ar as unknown as Record<string, string>;
    for (const [fam, enTwo, arTwo, arFew, arMany] of R2_PLURALS) {
      expect(enCat[`${fam}_two`]).toBe(enTwo);
      expect(arCat[`${fam}_two`]).toBe(arTwo);
      expect(arCat[`${fam}_few`]).toBe(arFew);
      expect(arCat[`${fam}_many`]).toBe(arMany);
      expect(t(fam, { count: 2 })).toBe(arTwo);
      expect(t(fam, { count: 3 })).toBe(arFew.replace('{{count}}', '3'));
      expect(t(fam, { count: 11 })).toBe(arMany.replace('{{count}}', '11'));
    }
  });
});
""")
print("done")
