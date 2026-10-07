"""Static pins of T0b Phase B: the hook text, .gitleaks.toml and the ci.yml
secret-scan job (addendum section 3.4, review corrections 1, 2, 3, 6, 10 f
and 11, rulings TB2-TB8).

Every node checks that its input exists before it parses it, so at the base
(no .gitleaks.toml, no secret-scan job, no Phase B hook lines) each RED node
fails by an assertion, never by a harness error. The PIN nodes (the
four-branch grep, the sqlfluff lines, the non-ASCII lines, the magic bytes of
the tracked binaries) pass at the base and must keep passing.

Security: the pinned sha256 of the gitleaks tarball and every 64-hex sample
are built at runtime; this file holds no credential-shaped literal.
"""

from __future__ import annotations

import fnmatch
import hashlib
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / ".githooks" / "pre-commit"
GITLEAKS_TOML = REPO_ROOT / ".gitleaks.toml"
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"

# The Phase B messages (the same strings as tests/test_precommit_hook_phase_b.py).
MSG_DIFF_FAILED = "could not read the staged diff (git diff failed)"
MSG_BINARY = "staged file is binary to git and not a known asset path:"
MSG_BINARY_REMEDY = (
    "convert it to text, or add the path to the allowlist in "
    ".githooks/pre-commit in its own commit"
)
MSG_BINARY_LIST_FAILED = "could not list the staged files for the binary check"
MSG_GITLEAKS = "gitleaks refused the staged changes"
MSG_GITLEAKS_REPORT = MSG_GITLEAKS + " (rule id and place above)"
MSG_GITLEAKS_NO_REPORT = (
    MSG_GITLEAKS + " (it exited non-zero with no finding report: a broken "
    ".gitleaks.toml, or a gitleaks other than 8.30.1)"
)
MSG_GITLEAKS_ABSENT = (
    "WARNING gitleaks not installed - secret scan skipped (CI runs it)"
)
MSG_GITLEAKS_TEMPLATE = "could not write the gitleaks report template"
MSG_GITLEAKSIGNORE = "a .gitleaksignore would silence gitleaks; remove it"
MSG_GITLEAKS_HEAD_CONFIG = "could not read .gitleaks.toml from HEAD for gitleaks"
MSG_ESLINT = "eslint found errors in staged client files"
MSG_ESLINT_STAGED = "eslint found errors in the staged content of"
MSG_ESLINT_DIRTY_FAILED = "could not list the unstaged client files for eslint"
MSG_ESLINT_CAP = (
    "NOTE more than 10 partially staged client files - eslint read their working copies"
)
MSG_ESLINT_ABSENT = (
    "NOTE eslint not available (no node or no SmartCompareApp/node_modules)"
    " - staged client files not linted"
)
MSG_STAGED_READ = "could not read the staged content of"

# Byte-equal pins (spec correction 6, ruling TB2: the grep line and the fail
# line stay; the PIPE line now reads the staged-diff file).
HOOK_CREDENTIAL_GREP = (
    "   grep -qE '(\\bsk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}"
    "|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----)'; then"
)
HOOK_CREDENTIAL_FAIL = '  fail "staged diff contains what looks like a credential'
HOOK_FILE_PIPE = 'if awk "$ADDED_LINES_AWK" "$STAGED_DIFF" | \\'
DIFF_RAW = "git diff --cached --no-color --no-ext-diff -U0 --text --no-textconv &&"
DIFF_TEXTCONV = "git diff --cached --no-color --no-ext-diff -U0 --text --textconv"
HOOK_JWT_RE = "eyJ[A-Za-z0-9_-]{7,}\\.[A-Za-z0-9_-]{10,}\\.[A-Za-z0-9_-]{10,}"

# The two lines of the 845ece15 hook that contain the words "sqlfluff lint"
# (correction 13: no new line may contain them).
BASE_SQLFLUFF_LINES = [
    "#    blocking a commit whose SQL is clean. Measured 2026-08-31: `sqlfluff lint",
    "    PYTHONIOENCODING=utf-8 sqlfluff lint --dialect postgres $SQL_FILES"
    ' || fail "sqlfluff failed on staged migrations"',
]
# sha256 prefixes (16 hex) of the 11 non-ASCII lines of the 845ece15 hook
# (em dashes in comments and two messages); no other line may be non-ASCII.
BASE_NON_ASCII_LINE_DIGESTS = {
    "97344cd6fb3b61af",
    "53e8c30002042e89",
    "c05e42e9de8b1d8f",
    "102e014caa3365c3",
    "1fa5092e65d2a121",
    "63321b1121f345eb",
    "23a5f1b0bc0b4256",
    "fd943e40124039d1",
    "964851ffdda11dd3",
    "8f41a8e9fc19d4d7",
    "6e95b5db699e616c",
}

# The magic bytes of every extension the binary allowlist admits (TB3).
MAGIC = {
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".ttf": (b"\x00\x01\x00\x00", b"true"),
    ".otf": (b"OTTO",),
}
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

# TB3 sample paths: admitted (the widening) and refused (no pure-extension
# entry, no PDF, archive, database or executable anywhere).
TB3_ADMITTED = [
    "docs/investigations/2026-10-05-session-72-state/screenshot.png",
    "docs/investigations/2026-10-05-session-72-state/photo.jpg",
    "docs/investigations/2026-10-05-session-72-state/photo.jpeg",
    "docs/investigations/2026-10-05-session-72-state/shot.webp",
    "docs/investigations/2026-10-05-session-72-state/anim.gif",
    "docs/brand/new-mark.png",
    "SmartCompareApp/assets/images/new.webp",
    "SmartCompareApp/assets/images/new.jpg",
    "SmartCompareApp/assets/images/new.gif",
    "SmartCompareApp/assets/fonts/New.otf",
    "SmartCompareApp/assets/fonts/New.ttf",
    "app/static/new.png",
    "test_images/5.jpeg",
]
TB3_REFUSED = [
    "misc/new.png",
    "new.png",
    "app/new.png",
    "SmartCompareApp/src/new.png",
    "tests/fixtures/new.png",
    "docs/investigations/2026-10-05-session-72-state/report.pdf",
    "docs/x.zip",
    "docs/x.docx",
    "docs/x.sqlite",
    "SmartCompareApp/assets/x.exe",
    "SmartCompareApp/assets/x.pdf",
    "SmartCompareApp/assets/x.zip",
    "data/x.db",
]

# Ruling TB8: the pinned tarball and its sha256 (built at runtime).
GL_VERSION = "8.30.1"
GL_TARBALL = "gitleaks_8.30.1_linux_x64.tar.gz"
GL_SHA256 = (
    "551f6fc83ea457d6" + "2a0d98237cbad105" + "af8d557003051f41" + "f3e7ca7b3f2470eb"
)

# Review correction 2: the narrowed file-digest allowlist (regexTarget match).
NARROWED_DIGEST_RE = (
    r"[\w-]\.(?:py|pyi|ts|tsx|js|jsx|mjs|cjs|json|md|sql|txt|ya?ml|toml|sh|ps1"
    r"|html?|css|png|jpe?g|webp|ttf|lock|snap|csv|log|out|diff|patch|xml|svg)"
    r'"?\s*[:=,]\s*"?[0-9a-f]{64}\b'
)
PASSWORD_FIXTURE_PATH = r"^tests/test_retro_w1_9_429\.py$"
FIXTURE_PATH = "^tests/fixtures/"
FIXTURE_RULES = {"generic-api-key", "gcp-api-key", "algolia-api-key"}


def _hex64(seed: str) -> str:
    return hashlib.sha256(seed.encode("ascii")).hexdigest()


# ---------------------------------------------------------------------------
# Hook helpers
# ---------------------------------------------------------------------------


def _hook_text() -> str:
    assert HOOK.is_file(), "the hook is missing: %s" % HOOK
    return HOOK.read_bytes().decode("utf-8").replace("\r\n", "\n")


def _hook_code() -> list:
    """Non-comment LOGICAL lines (backslash continuations joined)."""
    joined = _hook_text().replace("\\\n", " ")
    lines = [ln for ln in joined.split("\n") if ln.strip()]
    return [ln for ln in lines if not ln.lstrip().startswith("#")]


def _first_index(lines: list, needle: str) -> int:
    for i, ln in enumerate(lines):
        if needle in ln:
            return i
    raise AssertionError("the hook has no non-comment line containing %r" % needle)


def _binary_allowlist() -> list:
    """The glob patterns of the binary allowlist: every case pattern with a
    '/' and a '*.ext' between the numstat listing and the binary refusal."""
    code = _hook_code()
    start = _first_index(code, "--numstat")
    end = _first_index(code, 'fail "' + MSG_BINARY)
    patterns = []
    for ln in code[start:end]:
        m = re.match(r"\s*([^\s()]+)\)", ln)
        if not m:
            continue
        for pat in m.group(1).split("|"):
            pat = pat.strip("\"'")
            if "/" in pat and re.search(r"\*\.[A-Za-z0-9]+$", pat):
                patterns.append(pat)
    assert patterns, "the hook has no binary allowlist (an inline case, TB3)"
    return patterns


def _admitted(path: str, patterns: list) -> bool:
    # fnmatch's * also crosses '/', like a pattern of a sh case statement.
    return any(fnmatch.fnmatchcase(path, pat) for pat in patterns)


def _git(*args: str) -> bytes:
    p = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args], capture_output=True, timeout=60
    )
    if p.returncode != 0:
        pytest.skip("not a git checkout with HEAD: %r" % p.stderr[-200:])
    return p.stdout


def _tracked_binaries() -> list:
    if shutil.which("git") is None:
        pytest.skip("git not on PATH")
    out = _git(
        "-c",
        "core.quotePath=false",
        "diff",
        "--numstat",
        "--no-textconv",
        EMPTY_TREE,
        "HEAD",
    ).decode("utf-8", "replace")
    paths = [ln.split("\t", 2)[2] for ln in out.splitlines() if ln.startswith("-\t-\t")]
    assert paths, "git reports no binary file at HEAD"
    return paths


# ---------------------------------------------------------------------------
# The staged diff (TB2, review correction 1, #315a, #316, TF7)
# ---------------------------------------------------------------------------


def test_hook_reads_the_staged_diff_once_raw_then_textconv():
    lines = [ln.strip() for ln in _hook_text().split("\n")]
    assert DIFF_RAW in lines, "the raw-view diff line is missing: %r" % DIFF_RAW
    assert DIFF_TEXTCONV in lines, "the textconv-view diff line is missing"
    i = lines.index(DIFF_RAW)
    assert lines[i + 1] == DIFF_TEXTCONV, "the raw view must come first, then textconv"
    tail = "\n".join(lines[i + 2 : i + 5])
    assert '> "$STAGED_DIFF"' in tail, "both views must go to the staged-diff file"
    assert 'fail "' + MSG_DIFF_FAILED + '"' in tail, "a failed git diff must refuse"


def test_hook_pipes_no_git_diff_into_a_check():
    bad = [
        ln.strip()
        for ln in _hook_code()
        if re.search(r"git diff --cached[^|]*-U0[^|]*\|", ln)
    ]
    assert not bad, "a check still reads a piped git diff (TF7, #316): %s" % bad


def test_hook_four_branch_grep_byte_equal_reading_the_file():
    lines = _hook_text().split("\n")
    assert HOOK_CREDENTIAL_GREP in lines, "the four-branch credential grep changed"
    i = lines.index(HOOK_CREDENTIAL_GREP)
    assert lines[i - 1] == HOOK_FILE_PIPE, "the four-branch line must read the file"
    assert lines[i + 1].startswith(HOOK_CREDENTIAL_FAIL), "the refusal text changed"


def test_hook_new_shapes_branch_reads_the_file():
    lines = _hook_text().split("\n")
    greps = [i for i, ln in enumerate(lines) if "grep -qE -e" in ln and "JWT_RE" in ln]
    assert greps, "the JWT / credentialed-URL grep is missing"
    assert lines[greps[0] - 1] == HOOK_FILE_PIPE, "4a must read the staged-diff file"


def test_hook_env_value_pass_reads_the_file_with_the_z_trailer():
    blob = "\n".join(_hook_code())
    assert (
        "cat \"$STAGED_DIFF\" && printf 'Z\\n'" in blob
    ), "the .env value pass must read the staged-diff file and keep the Z trailer"


# ---------------------------------------------------------------------------
# The binary refusal (#315b, TB3)
# ---------------------------------------------------------------------------


def test_hook_binary_refusal_lists_with_numstat():
    code = _hook_code()
    numstat = [ln for ln in code if "--numstat" in ln]
    assert numstat, "the binary check has no numstat listing"
    for flag in (
        "--no-textconv",
        "--no-renames",
        "--diff-filter=ACMR",
        "core.quotePath=false",
    ):
        assert all(flag in ln for ln in numstat), "the numstat listing lacks %s" % flag
    blob = "\n".join(code)
    assert 'fail "' + MSG_BINARY in blob
    assert 'fail "' + MSG_BINARY_LIST_FAILED + '"' in blob
    assert MSG_BINARY_REMEDY in blob, "the binary refusal lacks its remedy (TB3)"


def test_binary_allowlist_admits_every_tracked_binary():
    patterns = _binary_allowlist()
    refused = [p for p in _tracked_binaries() if not _admitted(p, patterns)]
    assert not refused, "tracked binaries the hook would newly refuse: %s" % refused


def test_binary_allowlist_admits_the_tb3_roots():
    patterns = _binary_allowlist()
    missing = [p for p in TB3_ADMITTED if not _admitted(p, patterns)]
    assert not missing, "TB3 paths the allowlist does not admit: %s" % missing


def test_binary_allowlist_refuses_everything_else():
    patterns = _binary_allowlist()
    wide = [p for p in patterns if p.startswith("*") or "/" not in p]
    assert not wide, "an allowlist entry without a directory: %s" % wide
    admitted = [p for p in TB3_REFUSED if _admitted(p, patterns)]
    assert not admitted, "the allowlist admits paths TB3 refuses: %s" % admitted


def test_tracked_binaries_carry_the_magic_bytes_of_their_extension():
    bad = []
    for path in _tracked_binaries():
        ext = "." + path.rsplit(".", 1)[-1].lower()
        head = _git("cat-file", "blob", "HEAD:" + path)[:16]
        if ext == ".webp":
            ok = head[:4] == b"RIFF" and head[8:12] == b"WEBP"
        else:
            ok = any(head.startswith(m) for m in MAGIC.get(ext, ()))
        if not ok:
            bad.append(path)
    assert not bad, (
        "tracked binaries without the magic bytes of their extension: %s" % bad
    )


# ---------------------------------------------------------------------------
# The gitleaks pass (R1.2, corrections 1 and 7, TB6, TB8)
# ---------------------------------------------------------------------------


def _gitleaks_line() -> str:
    lines = [ln for ln in _hook_code() if "gitleaks git" in ln]
    assert lines, "the hook has no gitleaks git invocation"
    return lines[0]


def test_hook_gitleaks_invocation_flags():
    ln = _gitleaks_line()
    for needle in (
        "--pre-commit",
        "--staged",
        "--redact",
        "--no-banner",
        "--ignore-gitleaks-allow",
        "--report-format template",
        "--report-template",
        "--report-path",
        "GIT_CONFIG_KEY_0=color.ui",
        "GITLEAKS_CONFIG= ",
        "GITLEAKS_CONFIG_TOML= ",
    ):
        assert needle in ln, "the gitleaks line lacks %r: %s" % (needle, ln.strip())
    assert (
        " -v " not in ln and "--verbose" not in ln
    ), "the hook prints a template report"


def test_hook_gitleaks_reads_the_head_config_and_refuses_a_gitleaksignore():
    blob = "\n".join(_hook_code())
    assert "HEAD:.gitleaks.toml" in blob, "TB6: the config is a copy of HEAD's"
    assert '--config "$TOP/.gitleaks.toml"' not in blob, "TB6: never the working tree"
    assert ".gitleaksignore" in blob and 'fail "' + MSG_GITLEAKSIGNORE + '"' in blob


def test_hook_gitleaks_messages():
    blob = "\n".join(_hook_code())
    for fail_text in (
        MSG_GITLEAKS_REPORT,
        MSG_GITLEAKS_NO_REPORT,
        MSG_GITLEAKS_TEMPLATE,
        MSG_GITLEAKS_HEAD_CONFIG,
    ):
        assert 'fail "' + fail_text + '"' in blob, "missing refusal %r" % fail_text
    assert "pre-commit: " + MSG_GITLEAKS_ABSENT in blob


# ---------------------------------------------------------------------------
# Step order (TB7) and ESLint (R2.4, corrections 5 and 9)
# ---------------------------------------------------------------------------


def test_hook_runs_every_secret_check_before_the_python_checks():
    code = _hook_code()
    order = [
        'fail "staged diff contains what looks like a credential',
        'fail "staged diff contains a JWT or a credentialed URL',
        'fail ".env must never be committed"',
        'fail "' + MSG_BINARY,
        "staged diff contains the value of .env variable(s):",
        'fail "' + MSG_GITLEAKS,
        'materialise "$PY_FILES"',
        'fail "python syntax error in staged files"',
        'fail "ruff blocking tier failed"',
        'fail "black allowlist check failed',
        'fail "skill frontmatter check failed:',
        "sqlfluff lint",
        'fail "' + MSG_ESLINT,
    ]
    where = [_first_index(code, needle) for needle in order]
    pairs = [
        (order[i], order[i + 1])
        for i in range(len(order) - 1)
        if where[i] >= where[i + 1]
    ]
    assert not pairs, "TB7 order broken (first, then): %s" % pairs


def test_hook_eslint_step():
    code = _hook_code()
    eslint = [ln for ln in code if "eslint.js" in ln]
    assert eslint, "the hook has no ESLint step"
    blob = "\n".join(code)
    assert "node_modules/eslint/bin/eslint.js" in blob
    assert "--stdin" in blob and "--stdin-filename" in blob
    assert "-gt 10" in blob, "the cap of 10 partially staged files is missing"
    for bad in ("--fix", "--cache", "--max-warnings"):
        assert not any(bad in ln for ln in eslint), "eslint must not run with %s" % bad
    piped = [ln for ln in code if re.search(r"git show [^|]*\|(?!\|)", ln)]
    assert not piped, "the staged blob must be materialised first (correction 5)"
    for text in (
        MSG_ESLINT,
        MSG_ESLINT_STAGED,
        MSG_ESLINT_DIRTY_FAILED,
        MSG_STAGED_READ,
    ):
        assert 'fail "' + text in blob, "missing refusal %r" % text
    for note in (MSG_ESLINT_CAP, MSG_ESLINT_ABSENT):
        assert "pre-commit: " + note in blob, "missing note %r" % note


# ---------------------------------------------------------------------------
# PINs on the hook text (green at the base and after)
# ---------------------------------------------------------------------------


def test_hook_lines_with_sqlfluff_lint_are_the_base_ones():
    lines = [ln for ln in _hook_text().split("\n") if "sqlfluff lint" in ln]
    assert (
        lines == BASE_SQLFLUFF_LINES
    ), "a line containing 'sqlfluff lint' changed or was added"


def test_hook_non_ascii_lines_are_the_base_ones():
    new = []
    for n, ln in enumerate(_hook_text().split("\n"), 1):
        if any(ord(c) > 127 for c in ln):
            if (
                hashlib.sha256(ln.encode("utf-8")).hexdigest()[:16]
                not in BASE_NON_ASCII_LINE_DIGESTS
            ):
                new.append(n)
    assert not new, "non-ASCII hook lines that are not base lines: %s" % new


def test_hook_new_branches_stay_separate_from_the_four_branch_grep():
    lines = _hook_text().split("\n")
    assert HOOK_CREDENTIAL_GREP in lines
    assert HOOK_JWT_RE not in HOOK_CREDENTIAL_GREP


# ---------------------------------------------------------------------------
# .gitleaks.toml (R1.4, corrections 2 and 3, TB4, TB5)
# ---------------------------------------------------------------------------


def _config() -> dict:
    assert GITLEAKS_TOML.is_file(), "the repo has no .gitleaks.toml (R1.4)"
    return tomllib.loads(GITLEAKS_TOML.read_text(encoding="utf-8"))


def _allowlists() -> list:
    lists = _config().get("allowlists")
    assert isinstance(lists, list) and lists, "the config has no [[allowlists]]"
    return lists


def test_gitleaks_config_extends_the_default_rules_first():
    cfg = _config()
    assert cfg.get("extend", {}).get("useDefault") is True, "[extend] useDefault = true"
    tables = re.findall(
        r"^\s*\[{1,2}([^\]]+)\]{1,2}\s*$",
        GITLEAKS_TOML.read_text(encoding="utf-8"),
        re.M,
    )
    assert tables and tables[0].strip() == "extend", "[extend] must be the first table"
    assert (
        "rules" not in cfg
    ), "no top-level [[rules]] (they would not extend a default)"


def test_gitleaks_config_every_allowlist_is_described():
    bare = [
        i
        for i, a in enumerate(_allowlists())
        if not str(a.get("description", "")).strip()
    ]
    assert not bare, "allowlists without a description: %s" % bare


def test_gitleaks_config_has_no_blanket_path_allowlist():
    for a in _allowlists():
        paths = a.get("paths") or []
        for pat in paths:
            for sample in (
                "docs/investigations/2026-10-05-session-72-state/reports/a.json",
                "docs/investigations/x.md",
            ):
                assert not re.search(pat, sample), "a path allowlist covers %s" % sample
        if paths:
            assert a.get("condition") == "AND", (
                "a path entry must be AND-scoped: %r" % a
            )
            assert a.get("regexes") or a.get("targetRules"), (
                "a bare path allowlist: %r" % a
            )


def test_gitleaks_config_digest_allowlist_is_the_narrowed_one():
    lists = _allowlists()
    digest = [a for a in lists if NARROWED_DIGEST_RE in (a.get("regexes") or [])]
    assert digest, "the narrowed file-digest allowlist (review correction 2) is missing"
    assert digest[0].get("regexTarget") == "match"
    for a in lists:
        for rx in a.get("regexes") or []:
            assert "\\.[A-Za-z]{1,5}" not in rx, "the draft's wide digest regex is back"
    rx = re.compile(NARROWED_DIGEST_RE)
    hexv = _hex64("t0b digest sample")
    for benign in (
        "api.ts: " + hexv,
        "authService.ts = " + hexv,
        '"src/services/api.ts", "' + hexv,
    ):
        assert rx.search(benign), (
            "the digest allowlist no longer clears %r" % benign[:20]
        )
    for real in (
        'self.token = "' + hexv + '"',
        'settings.key = "' + hexv + '"',
        "auth.key: " + hexv,
    ):
        assert not rx.search(real), "the digest allowlist silences %r" % real[:14]


def test_gitleaks_config_password_allowlist_is_path_limited():
    pw = [
        a
        for a in _allowlists()
        if any("password" in rx for rx in a.get("regexes") or [])
    ]
    assert pw, "the password-fixture allowlist is missing"
    for a in pw:
        assert a.get("paths") == [
            PASSWORD_FIXTURE_PATH
        ], "allowlist 3 paths: %r" % a.get("paths")
        assert a.get("condition") == "AND"


def test_gitleaks_config_fixture_allowlist_targets_three_public_key_rules():
    fx = [a for a in _allowlists() if FIXTURE_PATH in (a.get("paths") or [])]
    assert len(fx) == 1, "TB5: exactly one tests/fixtures allowlist, got %d" % len(fx)
    a = fx[0]
    assert a.get("paths") == [FIXTURE_PATH]
    assert a.get("condition") == "AND"
    rules = a.get("targetRules") or []
    assert len(rules) == 3 and set(rules) == FIXTURE_RULES, (
        "TB5 targetRules: %r" % rules
    )
    for other in _allowlists():
        assert "jwt" not in (other.get("targetRules") or []), "jwt must stay active"


# ---------------------------------------------------------------------------
# The ci.yml secret-scan job (R5, corrections 4, 5 and 11, TB8)
# ---------------------------------------------------------------------------


def _ci() -> dict:
    assert CI_YML.is_file()
    return yaml.safe_load(CI_YML.read_text(encoding="utf-8"))


def _job() -> dict:
    jobs = _ci().get("jobs") or {}
    assert "secret-scan" in jobs, "ci.yml has no secret-scan job (R5)"
    return jobs["secret-scan"]


def _steps() -> list:
    steps = _job().get("steps") or []
    assert steps, "the secret-scan job has no steps"
    return steps


def _run_text() -> str:
    return "\n".join(str(s.get("run", "")) for s in _steps())


def test_secret_scan_job_shape():
    job = _job()
    assert job.get("runs-on") == "ubuntu-latest"
    assert job.get("timeout-minutes") == 10, "timeout-minutes: 10 (TB8)"
    assert job.get("permissions") == {"contents": "read"}, job.get("permissions")
    assert "if" not in job, "the job must not be gated by if:"
    assert "continue-on-error" not in job, "the job must block"
    for step in _steps():
        assert "if" not in step, "a step is gated by if: %r" % step.get("name")
        assert "continue-on-error" not in step, "a step is non-blocking: %r" % step.get(
            "name"
        )


def test_secret_scan_job_checks_out_the_full_history():
    checkout = [
        s for s in _steps() if str(s.get("uses", "")).startswith("actions/checkout@")
    ]
    assert checkout, "no checkout step"
    assert (checkout[0].get("with") or {}).get("fetch-depth") == 0, "fetch-depth: 0"


def test_secret_scan_job_installs_the_pinned_verified_release():
    text = _run_text()
    assert "curl " in text and "--retry" in text, "curl --retry (review correction 11)"
    assert (
        "/download/v" + GL_VERSION + "/" + GL_TARBALL in text
    ), "the pinned release URL"
    sums = [ln for ln in text.splitlines() if GL_SHA256 in ln]
    assert sums and all("sha256sum -c" in ln for ln in sums), "the TB8 sha256, checked"
    assert re.search(r"version\)?\"?\s*=\s*\"" + re.escape(GL_VERSION) + '"', text), (
        "the installed gitleaks must report " + GL_VERSION
    )


def test_secret_scan_job_scans_the_event_range_redacted():
    text = _run_text()
    scan = [
        ln
        for ln in text.replace("\\\n", " ").splitlines()
        if re.search(r"gitleaks\"?\s+git\s", ln)
    ]
    assert scan, "no gitleaks git invocation in the job"
    line = scan[0]
    for flag in (
        "--log-opts",
        "--redact",
        " -v",
        "--exit-code 1",
        "--ignore-gitleaks-allow",
    ):
        assert flag in line, "the scan lacks %s: %s" % (flag, line.strip())
    env_blob = " ".join(str(s.get("env", "")) for s in _steps())
    for ctx in (
        "github.event.pull_request.base.sha",
        "github.event.pull_request.head.sha",
        "github.event.before",
        "github.sha",
    ):
        assert ctx in env_blob or ctx in text, "the job does not read %s" % ctx
    assert "0" * 40 in text and "-1 " in text, "the all-zero before (new branch) case"
    assert "pull_request" in text


def test_secret_scan_job_reads_the_config_from_the_range_base():
    text = _run_text()
    assert ":.gitleaks.toml" in text and "git show" in text and "--config" in text


def test_secret_scan_job_refuses_a_tracked_gitleaksignore():
    text = _run_text()
    guard = [ln for ln in text.splitlines() if ".gitleaksignore" in ln]
    assert guard, "no .gitleaksignore guard (TB6)"
    assert "exit 1" in text


def test_secret_scan_job_says_rotate_first():
    raw = CI_YML.read_text(encoding="utf-8")
    assert "secret-scan:" in raw, "ci.yml has no secret-scan job"
    head = raw[: raw.index("secret-scan:")]
    comment = "\n".join(head.splitlines()[-25:]).lower()
    assert (
        "rotate" in comment and "detection" in comment
    ), "the job comment must say detection, not prevention, and rotate first"
