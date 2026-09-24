"""The flag-OFF byte-identity harness (scripts/verify_flag_byte_identity.py).

M11 backlog item 2 (recorded M10 verify finding): the previous scratchpad-only
harness fed ONE fixed query to every corpus page, so 586/588 pages hashed the
literal ``None`` extraction — near-zero discrimination. These tests pin the
three properties the port exists for, on a tiny synthetic corpus (zero
network, zero real corpus dependency):

  * queries are derived PER PAGE, so extractors actually run (non-None
    extractions appear in the payload);
  * two different extractions hash to two different overall SHAs;
  * a rerun over the same corpus is deterministic (same SHA, twice).
"""

import json

import pytest

from scripts.verify_flag_byte_identity import (
    derive_page_query,
    load_manifest,
    run_harness,
)


def _pdp_html(title: str, price: str, currency: str = "BHD") -> str:
    """A minimal but realistic PDP: JSON-LD Product + matching <title>."""
    ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "Product",
        "name": title,
        "brand": {"@type": "Brand", "name": title.split()[0]},
        "offers": {
            "@type": "Offer",
            "price": price,
            "priceCurrency": currency,
            "availability": "https://schema.org/InStock",
        },
    })
    body = "<p>" + ("filler " * 200) + "</p>"
    return (
        "<html><head><title>%s | Test Store</title>"
        '<script type="application/ld+json">%s</script>'
        "</head><body>%s</body></html>" % (title, ld, body)
    )


PAGES = [
    ("https://shop-a.example/products/atlas-oud-noir-50ml",
     "Atlas Oud Noir 50ml", "20.500"),
    ("https://shop-b.example/products/meridian-amber-veil-100ml",
     "Meridian Amber Veil 100ml", "34.900"),
    ("https://shop-c.example/products/cobalt-santal-drift-75ml",
     "Cobalt Santal Drift 75ml", "12.750"),
]


@pytest.fixture
def corpus(tmp_path):
    """(records, manifest_path, html_dir) for the 3-page fixture corpus."""
    html_dir = tmp_path / "html"
    html_dir.mkdir()
    rows = []
    for i, (url, title, price) in enumerate(PAGES):
        p = html_dir / ("page%d.html" % i)
        p.write_text(_pdp_html(title, price), encoding="utf-8")
        rows.append({
            "url": url,
            "path": str(p),
            "domain": url.split("/")[2],
            "page_currency": "BHD",
        })
    manifest = tmp_path / "corpus.jsonl"
    manifest.write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8",
    )
    records, skipped = load_manifest(str(manifest), str(html_dir))
    assert skipped == 0
    return records, manifest, html_dir


class TestQueryDerivation:
    def test_manifest_query_wins(self):
        assert derive_page_query(
            {"derived_query": "Hand Derived Name", "url": "https://x/p/slug"},
            "<title>Other</title>",
        ) == "Hand Derived Name"

    def test_page_title_is_used_when_manifest_has_none(self):
        q = derive_page_query(
            {"url": "https://x/products/foo", "brand": "Atlas"},
            "<html><head><title>Oud Noir 50ml | Store</title></head></html>",
        )
        assert "Oud Noir" in q and "Atlas" in q
        assert "Store" not in q  # the site-suffix segment is dropped

    def test_slug_is_the_last_resort(self):
        q = derive_page_query(
            {"url": "https://x/products/amber-veil-100ml"}, "",
        )
        assert q == "amber veil 100ml"

    def test_queries_are_per_page_never_a_fixed_constant(self, corpus):
        records, _, _ = corpus
        queries = {r["query"] for r in records}
        assert len(queries) == len(records) == 3


class TestHarnessRuns:
    def test_extractors_actually_run(self, corpus):
        """The de-degeneration property: with per-page queries the JSON-LD
        extraction engages, so non-None results appear — not 586/588 None."""
        records, _, _ = corpus
        payload, sha = run_harness(records, flags=[])
        assert payload["non_none_extractions"] > 0
        assert payload["distinct_queries"] == 3
        # 3 pages x 2 gate modes x 2 currency legs
        assert len(payload["results"]) == 12
        assert len(sha) == 64

    def test_a_rerun_is_deterministic(self, corpus):
        records, _, _ = corpus
        _, sha1 = run_harness(records, flags=["ENABLE_JSONLD_FIRST"])
        _, sha2 = run_harness(records, flags=["ENABLE_JSONLD_FIRST"])
        assert sha1 == sha2

    def test_two_different_extractions_hash_differently(self, corpus, tmp_path):
        """Change ONE page's price and the overall SHA must move — the exact
        discrimination the fixed-query harness lacked."""
        records, _, html_dir = corpus
        _, sha_before = run_harness(records, flags=[])
        # Rewrite page 1 with a different price; identical everything else.
        url, title, _ = PAGES[1]
        (html_dir / "page1.html").write_text(
            _pdp_html(title, "99.900"), encoding="utf-8",
        )
        _, sha_after = run_harness(records, flags=[])
        assert sha_before != sha_after

    def test_flag_env_is_restored_after_the_sweep(self, corpus, monkeypatch):
        records, _, _ = corpus
        monkeypatch.setenv("ENABLE_JSONLD_FIRST", "true")
        monkeypatch.delenv("ENABLE_EXACT_PRICE_GATE", raising=False)
        run_harness(records, flags=["ENABLE_JSONLD_FIRST"])
        import os
        assert os.environ.get("ENABLE_JSONLD_FIRST") == "true"
        assert "ENABLE_EXACT_PRICE_GATE" not in os.environ


# ===========================================================================
# R-W04 retro (W0-4 minor, harness only): --flags-on and --compare.
#
# The reviewer found the harness can only force flags OFF, so the recorded W0-4 gate never
# exercised ENABLE_PRICE_PARSE_OFFLOAD=true and the merge-time "no result change" sentence
# was asserted, not measured. The ruling: --flags-on forces the named flags to 'true' for the
# sweep (env set per call and restored), and --compare <other-results.json> prints the
# results-array sha equality and the first N differing records. The results-array digest is
# the reviewer's formula (the one that produced a1b3460c...):
#   sha256(json.dumps(payload["results"], sort_keys=True, ensure_ascii=True))
# Tests marked RED fail today on argparse (exit 2, "unrecognized arguments"); PINs pass today.
# ===========================================================================

import hashlib  # noqa: E402
import os  # noqa: E402
import socket  # noqa: E402

import scripts.verify_flag_byte_identity as vfbi  # noqa: E402
from app.services import price_service as ps  # noqa: E402

_PROBE_FLAG = "ENABLE_W04_HARNESS_PROBE"
_LOOPBACK = {"127.0.0.1", "::1", "localhost", "0.0.0.0", "", None}

# The payload keys the harness writes today. A new key on the default (no --flags-on) path
# would move every recorded OVERALL SHA256 (9504e5a9..., ec120b8b..., cfd13914...), so the
# harness change must add keys only when the new options are used.
_BASE_PAYLOAD_KEYS = {
    "n_records", "skipped_no_html", "flags_forced_off", "results",
    "distinct_queries", "non_none_extractions",
}


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    """R-W04: block every non-loopback connect / getaddrinfo for every test in this file."""
    attempts = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_getaddrinfo = socket.getaddrinfo

    def _host(address):
        host = address[0] if isinstance(address, tuple) and address else address
        return host.decode("ascii", "replace") if isinstance(host, bytes) else host

    def guard_connect(self, address):
        if _host(address) not in _LOOPBACK:
            attempts.append(("connect", _host(address)))
            raise OSError("R-W04 zero-network guard: blocked connect")
        return real_connect(self, address)

    def guard_connect_ex(self, address):
        if _host(address) not in _LOOPBACK:
            attempts.append(("connect_ex", _host(address)))
            raise OSError("R-W04 zero-network guard: blocked connect_ex")
        return real_connect_ex(self, address)

    def guard_getaddrinfo(host, *args, **kwargs):
        name = host.decode("ascii", "replace") if isinstance(host, bytes) else host
        if name not in _LOOPBACK:
            attempts.append(("getaddrinfo", name))
            raise socket.gaierror("R-W04 zero-network guard: blocked getaddrinfo")
        return real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guard_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guard_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guard_getaddrinfo)
    yield
    assert not attempts, "R-W04 zero-network guard: the test attempted network I/O: %r" % (
        attempts,
    )


@pytest.fixture(autouse=True)
def _probe_flag_restored(monkeypatch):
    """main() pins every --flags name to 'false' before the app import and never restores it,
    so register the probe flag with monkeypatch first: whatever a test's main() leaves behind,
    teardown returns the variable to its original (normally unset) state."""
    monkeypatch.setenv(_PROBE_FLAG, "w04-teardown-sentinel")
    monkeypatch.delenv(_PROBE_FLAG)
    yield


def _tiny_corpus(tmp_path):
    rows = []
    for i, (url, name) in enumerate([
        ("https://shop-a.example/products/atlas-oud", "Atlas Oud Noir 50ml"),
        ("https://shop-b.example/products/meridian-amber", "Meridian Amber Veil 100ml"),
    ]):
        page = tmp_path / ("w04page%d.html" % i)
        page.write_text("<html><head><title>%s</title></head><body></body></html>" % name,
                        encoding="utf-8")
        rows.append({"url": url, "path": str(page), "name": name, "page_currency": "BHD"})
    manifest = tmp_path / "w04manifest.jsonl"
    manifest.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return str(manifest), rows


def _install_env_spy(monkeypatch):
    """Replace the extractor the harness imports at call time with one that records the probe
    flag's value per call and returns a result that depends on it."""
    seen = []

    def spy(html, query, currency, domain, url, **kwargs):
        value = os.environ.get(_PROBE_FLAG)
        seen.append(value)
        return {"amount": 1.0, "probe": value, "url": url}

    monkeypatch.setattr(ps, "extract_price_from_html", spy)
    return seen


def _run_main(argv):
    try:
        return vfbi.main(argv)
    except SystemExit as exc:  # argparse rejects an unknown option with SystemExit(2)
        pytest.fail("verify_flag_byte_identity.main(%r) exited %r: an option is missing" % (
            argv, exc.code))


def _results_sha(results):
    return hashlib.sha256(
        json.dumps(results, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()


class TestW04HarnessFlagsOnAndCompare:
    def test_flags_forces_the_flag_off_per_call(self, monkeypatch, tmp_path):
        """PIN (green today): --flags forces the named flag to 'false' on every call."""
        manifest, _rows = _tiny_corpus(tmp_path)
        seen = _install_env_spy(monkeypatch)
        monkeypatch.setenv(_PROBE_FLAG, "true")
        assert _run_main(["--corpus", manifest, "--flags", _PROBE_FLAG]) == 0
        assert len(seen) == 8 and set(seen) == {"false"}, seen

    def test_default_run_payload_shape_and_digest_are_unchanged(
        self, monkeypatch, tmp_path, capsys,
    ):
        """PIN (green today and after): without the new options the payload keeps exactly
        today's keys, and the printed OVERALL SHA256 is still sha256 of the indent=1
        canonical payload, so every recorded base digest stays reproducible."""
        manifest, _rows = _tiny_corpus(tmp_path)
        _install_env_spy(monkeypatch)
        out_path = tmp_path / "w04base.json"
        capsys.readouterr()
        assert _run_main(["--corpus", manifest, "--flags", _PROBE_FLAG,
                          "--out", str(out_path)]) == 0
        printed = capsys.readouterr().out
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        assert set(payload) == _BASE_PAYLOAD_KEYS, sorted(payload)
        digest = hashlib.sha256(json.dumps(
            payload, sort_keys=True, ensure_ascii=True, indent=1,
        ).encode("utf-8")).hexdigest()
        assert "OVERALL SHA256 " + digest in printed, printed

    def test_flags_on_forces_true_per_call_and_restores(self, monkeypatch, tmp_path):
        """RED today: there is no --flags-on, so the harness cannot sweep a flag ON."""
        manifest, _rows = _tiny_corpus(tmp_path)
        seen = _install_env_spy(monkeypatch)
        monkeypatch.setenv(_PROBE_FLAG, "prior-value")

        rc = _run_main(["--corpus", manifest, "--flags-on", _PROBE_FLAG,
                        "--out", str(tmp_path / "w04on.json")])

        assert rc == 0
        assert len(seen) == 8 and set(seen) == {"true"}, (
            "--flags-on must force %s='true' on all 8 calls (2 pages x 2 gates x 2 legs): %r"
            % (_PROBE_FLAG, seen)
        )
        assert os.environ.get(_PROBE_FLAG) == "prior-value", (
            "--flags-on must restore the previous environment value, got %r"
            % os.environ.get(_PROBE_FLAG)
        )

    def test_flags_on_restores_an_unset_flag_to_unset(self, monkeypatch, tmp_path):
        """RED today: an unset flag forced ON for the sweep is unset again afterwards."""
        manifest, _rows = _tiny_corpus(tmp_path)
        seen = _install_env_spy(monkeypatch)
        monkeypatch.delenv(_PROBE_FLAG, raising=False)

        rc = _run_main(["--corpus", manifest, "--flags-on", _PROBE_FLAG])

        assert rc == 0 and set(seen) == {"true"}, seen
        assert _PROBE_FLAG not in os.environ, os.environ.get(_PROBE_FLAG)

    def test_compare_reports_a_mismatch(self, monkeypatch, tmp_path, capsys):
        """RED today: there is no --compare. A differing record must be visible."""
        manifest, rows = _tiny_corpus(tmp_path)
        _install_env_spy(monkeypatch)
        base_path = tmp_path / "w04cmpbase.json"
        assert _run_main(["--corpus", manifest, "--out", str(base_path)]) == 0
        base = json.loads(base_path.read_text(encoding="utf-8"))
        other = json.loads(json.dumps(base))
        target = other["results"][0]
        target["result"] = {"amount": 999.0, "probe": "tampered", "url": target["url"]}
        other_path = tmp_path / "w04cmpother.json"
        other_path.write_text(json.dumps(other, sort_keys=True, indent=1), encoding="utf-8")
        capsys.readouterr()

        rc = _run_main(["--corpus", manifest, "--compare", str(other_path)])
        out = capsys.readouterr().out

        assert rc in (0, 1)
        assert _results_sha(base["results"]) in out and _results_sha(other["results"]) in out, (
            "--compare must print both results-array digests: %r" % out
        )
        assert target["url"] in out, "--compare must print the first differing record: %r" % out

    def test_compare_reports_equality(self, monkeypatch, tmp_path, capsys):
        """RED today: --compare against an identical payload prints the (equal) digest and
        lists no record as differing."""
        manifest, rows = _tiny_corpus(tmp_path)
        _install_env_spy(monkeypatch)
        base_path = tmp_path / "w04eqbase.json"
        assert _run_main(["--corpus", manifest, "--out", str(base_path)]) == 0
        base = json.loads(base_path.read_text(encoding="utf-8"))
        capsys.readouterr()

        rc = _run_main(["--corpus", manifest, "--compare", str(base_path)])
        out = capsys.readouterr().out

        assert rc == 0
        assert _results_sha(base["results"]) in out, out
        assert not any(r["url"] in out for r in rows), (
            "an equal comparison must not list any record as differing: %r" % out
        )

    def test_flags_on_vs_off_compare_surfaces_the_flag_fork(self, monkeypatch, tmp_path, capsys):
        """RED today: the W0-4 use case end to end. Sweep with the probe flag forced OFF, then
        sweep with it forced ON and --compare against the OFF payload: the spy's result depends
        on the flag, so every record differs and the output must say so."""
        manifest, rows = _tiny_corpus(tmp_path)
        _install_env_spy(monkeypatch)
        off_path = tmp_path / "w04off.json"
        assert _run_main(["--corpus", manifest, "--flags", _PROBE_FLAG,
                          "--out", str(off_path)]) == 0
        off = json.loads(off_path.read_text(encoding="utf-8"))
        capsys.readouterr()

        _run_main(["--corpus", manifest, "--flags-on", _PROBE_FLAG,
                   "--compare", str(off_path)])
        out = capsys.readouterr().out

        assert _results_sha(off["results"]) in out, out
        assert any(r["url"] in out for r in rows), (
            "flag ON vs OFF differs on every record; --compare must list one: %r" % out
        )


# ===========================================================================
# R-W04 fixer: the --compare contract beyond the ruling's minimum. The retro adversary found
# these behaviours unpinned (each mutant survived this file): the per-url occurrence number in
# the record key, exit 1 on a results mismatch (decided by the results-array digest, not by the
# records --compare happens to print), and exit 2 for a flag named in both --flags and
# --flags-on.
# ===========================================================================


def _dup_url_corpus(tmp_path):
    """Three manifest rows, two of them the SAME url with different pages. The real _proof
    corpus lists 3 urls twice, which is why --compare keys a record on its occurrence too."""
    dup = "https://shop-d.example/products/dup-page"
    rows = []
    for i, (url, name) in enumerate([
        (dup, "Atlas Oud Noir 50ml"),
        ("https://shop-e.example/products/solo-page", "Meridian Amber Veil 100ml"),
        (dup, "Cobalt Santal Drift 75ml"),
    ]):
        page = tmp_path / ("w04dup%d.html" % i)
        page.write_text("<html><head><title>%s</title></head><body></body></html>" % name,
                        encoding="utf-8")
        rows.append({"url": url, "path": str(page), "name": name, "page_currency": "BHD"})
    manifest = tmp_path / "w04dupmanifest.jsonl"
    manifest.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return str(manifest), dup


def _tampered_copy(tmp_path, payload, pick, name):
    """Write a copy of ``payload`` whose first record matching ``pick`` has a changed result;
    return (path, the tampered record)."""
    other = json.loads(json.dumps(payload))
    target = next(r for r in other["results"] if pick(r))
    target["result"] = {"amount": 999.0, "probe": "tampered", "url": target["url"]}
    path = tmp_path / name
    path.write_text(json.dumps(other, sort_keys=True, indent=1), encoding="utf-8")
    return path, target


class TestW04HarnessCompareContract:
    def test_compare_keys_duplicate_urls_by_occurrence(self, monkeypatch, tmp_path, capsys):
        """PIN: a url listed twice yields two distinct keys per (gate, leg). Tampering the
        FIRST occurrence must be reported as exactly 1 differing record of 12 (3 rows x 2 gates
        x 2 legs), named with occurrence=0. Keyed without the occurrence, the two rows collapse
        into one key holding the second (untampered) row on both sides, and the difference
        disappears from the DIFF list."""
        manifest, dup = _dup_url_corpus(tmp_path)
        _install_env_spy(monkeypatch)
        base_path = tmp_path / "w04dupbase.json"
        assert _run_main(["--corpus", manifest, "--out", str(base_path)]) == 0
        base = json.loads(base_path.read_text(encoding="utf-8"))
        assert len(base["results"]) == 12
        other_path, target = _tampered_copy(
            tmp_path, base, lambda r: r["url"] == dup, "w04dupother.json",
        )
        capsys.readouterr()

        rc = _run_main(["--corpus", manifest, "--compare", str(other_path)])
        out = capsys.readouterr().out

        assert rc == 1, out
        assert "DIFFERING RECORDS 1 of 12" in out, out
        assert "DIFF corpus=%s url=%s gate=%s leg=%s occurrence=0" % (
            target["corpus"], dup, target["gate"], target["leg"],
        ) in out, out

    def test_compare_exit_status_follows_the_results_digest(self, monkeypatch, tmp_path, capsys):
        """PIN: a mismatch exits 1 even when --compare-max 0 prints no DIFF record. The exit
        status is the results-array digest equality, never the printed subset."""
        manifest, _rows = _tiny_corpus(tmp_path)
        _install_env_spy(monkeypatch)
        base_path = tmp_path / "w04exitbase.json"
        assert _run_main(["--corpus", manifest, "--out", str(base_path)]) == 0
        base = json.loads(base_path.read_text(encoding="utf-8"))
        other_path, _target = _tampered_copy(tmp_path, base, lambda r: True, "w04exitother.json")
        capsys.readouterr()

        rc = _run_main(["--corpus", manifest, "--compare", str(other_path),
                        "--compare-max", "0"])
        out = capsys.readouterr().out

        assert rc == 1, out
        assert "equal=False" in out and "DIFFERING RECORDS 1 of 8" in out, out
        assert not [ln for ln in out.splitlines() if ln.startswith("DIFF ")], out

    def test_compare_equal_exits_0(self, monkeypatch, tmp_path, capsys):
        """PIN: the equal case prints equal=True, 0 differing, and exits 0."""
        manifest, _rows = _tiny_corpus(tmp_path)
        _install_env_spy(monkeypatch)
        base_path = tmp_path / "w04eq0base.json"
        assert _run_main(["--corpus", manifest, "--out", str(base_path)]) == 0
        capsys.readouterr()
        rc = _run_main(["--corpus", manifest, "--compare", str(base_path)])
        out = capsys.readouterr().out
        assert rc == 0 and "equal=True" in out and "DIFFERING RECORDS 0 of 8" in out, out

    def test_a_flag_named_in_both_flags_and_flags_on_exits_2(self, monkeypatch, tmp_path, capsys):
        """PIN: one flag cannot be forced OFF and ON in the same sweep. main() refuses with
        exit 2 before any extraction runs and leaves the environment untouched."""
        manifest, _rows = _tiny_corpus(tmp_path)
        seen = _install_env_spy(monkeypatch)
        monkeypatch.delenv(_PROBE_FLAG, raising=False)
        capsys.readouterr()

        rc = _run_main(["--corpus", manifest, "--flags", _PROBE_FLAG,
                        "--flags-on", _PROBE_FLAG])
        out = capsys.readouterr().out

        assert rc == 2, out
        assert "both --flags and --flags-on" in out and _PROBE_FLAG in out, out
        assert seen == [], seen
        assert _PROBE_FLAG not in os.environ
