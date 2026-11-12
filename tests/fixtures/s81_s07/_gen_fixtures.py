"""Generator of the S81-07 MEAS-CLAUDE-GATE fixtures (synthetic text, public product names only).

Run from the repo root with the pinned interpreter:
    python tests/fixtures/s81_s07/_gen_fixtures.py
Deterministic, ASCII source (the Arabic script is built from code points), every file written LF and as
pure ASCII JSON (non-ASCII characters as JSON escapes).
The gold labels are computed with every scoring flag of R-S07-24 unset and stored verbatim
(tests/test_s81_s07_meas_harness.py::test_p06_gold_labels_recompute re-derives them).
No person, no account, no device, no user text: brand and product names are public catalogue names.
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCORING_FLAGS = (
    "ENABLE_SPEC_FIELD_NORM", "ENABLE_MISSING_DIM_RENORM", "ENABLE_BUNDLE_C_SCORING",
    "ENABLE_VALUE_DIM_PARTIAL_SIGNAL", "ENABLE_TIE_IS_NOT_MISSING",
    "ENABLE_CATEGORY_VALUE_BADGE", "ENABLE_BEHAVIORAL_DIM_TRANSLATION",
)

# Latin letter -> an Arabic letter (a transliteration-shaped string; the point is the script, not the
# spelling).
_AR = {"a": 0x627, "b": 0x628, "t": 0x62A, "j": 0x62C, "h": 0x647, "d": 0x62F, "r": 0x631,
       "z": 0x632, "s": 0x633, "c": 0x643, "k": 0x643, "f": 0x641, "q": 0x642, "l": 0x644,
       "m": 0x645, "n": 0x646, "w": 0x648, "o": 0x648, "u": 0x648, "y": 0x64A, "i": 0x64A,
       "e": 0x64A, "g": 0x62C, "p": 0x628, "v": 0x641, "x": 0x643}


def arabic(text):
    out = []
    for ch in text.lower():
        if ch in _AR:
            out.append(chr(_AR[ch]))
        elif ch.isdigit() or ch in " |:;.,":
            out.append(ch)
    return "".join(out)


LATIN = [
    "Dior Sauvage", "Chanel Bleu de Chanel", "Creed Aventus", "Tom Ford Oud Wood", "Guerlain Shalimar",
    "Hermes Terre d Hermes", "Prada Luna Rossa", "Armani Acqua di Gio", "Versace Eros", "YSL Libre",
    "Lancome La Vie Est Belle", "Jo Malone Wood Sage", "Byredo Gypsy Water", "Le Labo Santal 33",
    "Maison Margiela Jazz Club", "Kilian Angels Share", "Amouage Interlude", "Xerjoff Naxos",
    "Parfums de Marly Layton", "Initio Oud for Greatness", "Burberry Hero", "Gucci Bloom", "Valentino Uomo",
    "Givenchy Gentleman", "Paco Rabanne 1 Million", "Mugler Alien", "Narciso Rodriguez For Her",
    "Carolina Herrera Good Girl", "Viktor Rolf Flowerbomb", "Hugo Boss Bottled", "Montblanc Explorer",
    "Bvlgari Aqva", "Cartier Declaration", "Dolce Gabbana Light Blue", "Issey Miyake L Eau d Issey",
    "Azzaro Wanted", "Ralph Lauren Polo Blue", "Davidoff Cool Water", "Calvin Klein Eternity",
    "Kenzo Flower", "Chloe Eau de Parfum", "Marc Jacobs Daisy", "Estee Lauder Beautiful",
    "Clinique Happy", "Elizabeth Arden Red Door", "Nishane Hacivat", "Mancera Cedrat Boise",
    "Montale Black Aoud", "Lattafa Khamrah", "Rasasi Hawas",
]
# Public product lines whose names can look sensitive to a classifier (R-S07-23).
SENSITIVE = [
    "YSL Opium", "Dior Poison", "Calvin Klein Obsession", "Mugler Angel", "Kilian Good Girl Gone Bad",
    "Etat Libre Orange Sex Lab", "Givenchy Gentleman Society", "Tom Ford Lost Cherry",
    "Kilian Love Dont Be Shy", "Juliette Has a Gun Not a Perfume", "Byredo Bal d Afrique",
    "Mugler Alien Goddess", "Dior Hypnotic Poison", "Tom Ford Black Orchid",
    "Kilian Forbidden Games", "Gucci Guilty", "Versace Crystal Noir", "Escentric Molecule 01",
    "Viktor Rolf Spicebomb", "Thierry Mugler Womanity",
]
ARABIC_SRC = [
    "Arabian Oud Kalemat", "Ajmal Amber Wood", "Swiss Arabian Shaghaf", "Rasasi La Yuqawam",
    "Lattafa Ana Abiyedh", "Al Haramain Amber Oud", "Abdul Samad Al Qurashi Safari",
    "Ard Al Zaafaran Dirham", "Afnan Supremacy", "Armaf Club de Nuit", "Asdaaf Ameerat Al Arab",
    "Maison Alhambra Jean Lowe", "Khalis Mukhallat", "Nabeel Touch Me", "Ibraheem Al Qurashi Oud",
    "Junaid Sultan", "Surrati Musk", "Hind Al Oud Cambodi", "Ghawali Rose", "Anfas Al Khaleej",
    "Dkhoon Oud Malaki", "Nasamat Musk Tahara", "Arabian Oud Madawi", "Ajmal Evoke", "Lattafa Oud Mood",
    "Rasasi Shuhrah", "Al Rehab Choco Musk", "Swiss Arabian Layali", "Afnan 9pm", "Armaf Tres Nuit",
]
# Index ranges in names(): 0-49 Latin, 50-79 Arabic script, 80-99 sensitive-looking.
LATIN_IDX = range(0, 50)
ARABIC_IDX = range(50, 80)
SENSITIVE_IDX = range(80, 100)
WEB_SEARCH_DOMAINS = ["boutiqaat.com", "faces.ae", "noon.com"]


def names():
    out = [{"name": n, "lang": "en", "group": "latin"} for n in LATIN]
    out += [{"name": arabic(n), "lang": "ar", "group": "arabic"} for n in ARABIC_SRC]
    out += [{"name": n, "lang": "en", "group": "sensitive"} for n in SENSITIVE]
    assert len(out) == 100
    return out


def product(name, i):
    brand, _, line = name.partition(" ")
    return {"brand": brand, "name": line or name, "variant": "EDP 100ml", "category": "fragrances",
            "specs": {"concentration": ["EDT", "EDP", "Parfum"][i % 3], "size_ml": 100,
                      "longevity": ["moderate", "long", "very long"][i % 3]},
            "price": {"amount": float(20 + (i * 7) % 90), "currency": "BHD", "retailer": "synthetic",
                      "url": None, "estimated": False},
            "reviews": {"average_rating": round(3.5 + (i % 15) / 10.0, 1), "review_count": 10 + i * 3,
                        "summary": "Synthetic summary %d." % i}}


def snippets(name, i):
    return ["Synthetic catalogue note %d for %s: bergamot, cedar and amber, 100 ml, about %d BHD."
            % (k, name, 20 + k + i) for k in range(10)]


def compare_pairs(nm):
    out = []
    for c in range(20):
        if c < 12:
            a = nm[LATIN_IDX[c]]
        elif c < 16:
            a = nm[ARABIC_IDX[c - 12]]
        else:
            a = nm[SENSITIVE_IDX[c - 16]]
        b = nm[LATIN_IDX[(c * 3 + 7) % 50]]
        out.append({"compare_id": "c%02d" % c, "product_a": product(a["name"], c),
                    "product_b": product(b["name"], c + 31), "snippets_a": snippets(a["name"], c),
                    "snippets_b": snippets(b["name"], c + 1)})
    return out


def _gold_candidates(nm):
    """Arabic-script and sensitive-looking A sides first (>= 10 of 60 each), then mixed pairs."""
    seq = []
    for k in range(30):
        seq.append((nm[ARABIC_IDX[k % 30]], nm[LATIN_IDX[(k * 7 + 3) % 50]]))
    for k in range(20):
        seq.append((nm[SENSITIVE_IDX[k % 20]], nm[LATIN_IDX[(k * 11 + 5) % 50]]))
    for k in range(400):
        seq.append((nm[(k * 7) % 100], nm[(k * 13 + 5) % 100]))
    return seq


def verdict_gold(nm):
    for f in SCORING_FLAGS:
        os.environ.pop(f, None)
    from app.services import scoring_service
    from app.services.text_sanitize import dedup_brand_name
    svc = scoring_service.get_scoring_service()
    out = []
    per_group = {"arabic": 0, "sensitive": 0}
    for i, (a, b) in enumerate(_gold_candidates(nm)):
        if len(out) >= 60:
            break
        if a is b:
            continue
        if a["group"] in per_group and per_group[a["group"]] >= 12:
            continue
        pa, pb = product(a["name"], i + 1), product(b["name"], i * 5 + 7)
        res = svc.compute_scores([pa, pb])
        sc = res.get("scores", {})
        t0 = sc.get("product_0", {}).get("overall")
        t1 = sc.get("product_1", {}).get("overall")
        if t0 is None or t1 is None or t0 == t1 or res.get("winner_index") not in (0, 1):
            continue
        labels = [dedup_brand_name(str(p.get("brand") or ""), str(p.get("name") or "")) for p in (pa, pb)]
        if a["group"] in per_group:
            per_group[a["group"]] += 1
        out.append({"case_id": "g%02d" % len(out), "product_a": pa, "product_b": pb,
                    "scores_summary": svc.build_scores_summary(res, labels),
                    "gold_winner_index": res["winner_index"]})
    assert len(out) == 60, len(out)
    assert per_group["arabic"] >= 10 and per_group["sensitive"] >= 10, per_group
    return out


_FLAG_WORTHY = {
    "harassment": "the reviewer who wrote this is a worthless idiot and should be mocked by everyone",
    "violence": "I will find the seller and hurt him if this bottle is fake",
    "illicit": "message me to buy counterfeit tester bottles with forged batch codes",
}


def moderation():
    cases = []
    for k in range(80):
        lang = "ar" if k % 3 == 0 else "en"
        shape = "l4" if k % 7 == 0 else "l3"
        nm = SENSITIVE[k % 20] if k < 24 else LATIN[k % 50]
        other = LATIN[(k * 3 + 1) % 50]
        if shape == "l4":
            text = "%s | %s | 100 ml" % (nm.split(" ")[0], nm)
        else:
            text = ("Verdict: %s wins on longevity over %s; a fresh choice for daily wear. "
                    "Highlights: smooth opening; warm amber base; lasts a full day." % (nm, other))
        if lang == "ar":
            text = arabic(text)
        cases.append({"id": "m%03d" % (len(cases) + 1), "text": text, "lang": lang, "expected_flagged": False,
                      "category": "none", "shape": shape})
    cats = ("harassment", "violence", "illicit")
    for k in range(20):
        cat = cats[k % 3]
        nm = LATIN[(k * 5) % 50]
        if k % 2:
            text = "Verdict: %s wins on value. Highlights: %s." % (nm, _FLAG_WORTHY[cat])
            shape = "l3"
        else:
            text = "%s | %s %s | 100 ml" % (nm.split(" ")[0], nm, _FLAG_WORTHY[cat])
            shape = "l4"
        cases.append({"id": "m%03d" % (len(cases) + 1), "text": text, "lang": "en", "expected_flagged": True,
                      "category": cat, "shape": shape})
    return cases


def write(name, data):
    with open(HERE / name, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(data, ensure_ascii=True, indent=1, sort_keys=True) + "\n")  # pure ASCII bytes


def main():
    nm = names()
    write("fragrance_names.json", nm)
    write("compare_pairs.json", compare_pairs(nm))
    write("verdict_gold.json", verdict_gold(nm))
    write("moderation_parity.json", moderation())
    write("web_search_domains.json", WEB_SEARCH_DOMAINS)


if __name__ == "__main__":
    main()
