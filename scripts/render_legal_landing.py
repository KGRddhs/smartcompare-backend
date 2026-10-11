"""Render the legal markdown into the landing pages (unit U8, ruling UL1 / UL11).

The four legal pages and the two support pages carry ONE generated region
between ``<!-- legal:begin -->`` and ``<!-- legal:end -->``. Everything outside
the region (head, wordmark, footer, hreflang links, the language switch) is
hand-made chrome and is never touched.

Sources (repo-relative):

    landing/privacy.html      <- app/legal/privacy_policy.md
    landing/terms.html        <- app/legal/terms_of_service.md
    landing/ar/privacy.html   <- app/legal/privacy_policy_ar.md
    landing/ar/terms.html     <- app/legal/terms_of_service_ar.md
    landing/support.html      <- app/legal/support_contact.md
    landing/ar/support.html   <- app/legal/support_contact_ar.md

The Arabic pages render from the ``_ar.md`` files inside the existing
``dir="rtl"`` chrome; nothing here changes direction or language attributes.

Markdown subset (the documents use nothing else; there are no tables):
``#`` / ``##`` / ``###`` headings, paragraphs, ``- `` list items (one line
each), ``**bold**``, ``*emphasis*`` and ``[text](url)`` links whose URL is
http(s) or mailto. A line outside the subset (a numbered, ``*`` or ``+``
item, an indented ``- `` item, a ``>`` quote, a ``|`` table row, four or more
``#``, a horizontal rule, or a non-item line directly after an item) raises
``LegalRenderError`` instead of rendering differently from the App's
markdown. ALL text is HTML-escaped, so a ``<PLACEHOLDER:ID>`` token
renders as ``&lt;PLACEHOLDER:ID&gt;`` and raw HTML in a source never reaches a
page. Paragraphs between a level-1 heading and the first level-2 heading are
the document's front matter and get ``class="subtitle"``.

API (standard library only; importing this module has no side effect):

    render_markdown(text, indent=4) -> str
    render_regions(repo_root) -> {page: region}   # pure: reads, never writes
    write_regions(repo_root, pages=None) -> [changed pages]

Command line (from the repo root):

    python scripts/render_legal_landing.py            # write all six regions
    python scripts/render_legal_landing.py --check    # exit 1 if a region is stale
    python scripts/render_legal_landing.py landing/privacy.html ...  # only these

A missing source is an error naming the file; nothing is written in that case.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

REGION_BEGIN = "<!-- legal:begin -->"
REGION_END = "<!-- legal:end -->"

# page -> source markdown (posix paths relative to the repo root)
SOURCES = {
    "landing/privacy.html": "app/legal/privacy_policy.md",
    "landing/terms.html": "app/legal/terms_of_service.md",
    "landing/ar/privacy.html": "app/legal/privacy_policy_ar.md",
    "landing/ar/terms.html": "app/legal/terms_of_service_ar.md",
    "landing/support.html": "app/legal/support_contact.md",
    "landing/ar/support.html": "app/legal/support_contact_ar.md",
}

# Paragraph class per page: the support pages style their small contact block
# like the page's existing ".note" paragraph; the legal pages use plain <p>.
PARAGRAPH_CLASS = {
    "landing/support.html": "note",
    "landing/ar/support.html": "note",
}

# Indentation of the region's blocks inside <main> (matches the chrome).
REGION_INDENT = 4

_HEADING = re.compile(r"^(#{1,3})[ \t]+(.+?)[ \t]*#*[ \t]*$")
_LIST_ITEM = re.compile(r"^[ \t]*-[ \t]+(.*)$")
_LINK = re.compile(r"\[([^\]\n]+)\]\(([^)\s]+)\)")
_SAFE_HREF = re.compile(r"^(?:https?://|mailto:)[^\s<>\"']+$", re.IGNORECASE)
_BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*")
_EM = re.compile(r"(?<![*\w])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![*\w])")
# Lines outside the subset (adversary B6): (label, pattern) in the order they are checked.
OUTSIDE_SUBSET = (
    ("a horizontal rule", re.compile(r"^[ \t]*(?:[-*_][ \t]*){3,}$")),
    ("a numbered list item", re.compile(r"^[ \t]*[0-9]+[.)][ \t]")),
    ("a '*' or '+' list item", re.compile(r"^[ \t]*[*+][ \t]")),
    ("an indented '- ' list item", re.compile(r"^[ \t]+-[ \t]")),
    ("a '>' quote", re.compile(r"^[ \t]*>")),
    ("a '|' table row", re.compile(r"^[ \t]*\|")),
    ("a heading of four or more '#'", re.compile(r"^[ \t]*#{4,}")),
)


class LegalRenderError(Exception):
    """A source or page is missing, a page does not carry exactly one legal region,
    or a source line is outside the markdown subset."""


def _escape(text: str) -> str:
    return html.escape(text, quote=False)


def _emphasis(escaped: str) -> str:
    escaped = _BOLD.sub(r"<strong>\1</strong>", escaped)
    return _EM.sub(r"<em>\1</em>", escaped)


def _inline(text: str) -> str:
    """Escape ``text`` and apply bold, emphasis and safe links."""
    out = []
    pos = 0
    for match in _LINK.finditer(text):
        href = match.group(2)
        if not _SAFE_HREF.match(href):
            continue
        out.append(_emphasis(_escape(text[pos:match.start()])))
        label = _emphasis(_escape(match.group(1)))
        out.append(f'<a href="{html.escape(href, quote=True)}">{label}</a>')
        pos = match.end()
    out.append(_emphasis(_escape(text[pos:])))
    return "".join(out)


def _blocks(text: str):
    """Yield ("h", level, text) / ("p", None, text) / ("ul", None, [items])."""
    paragraph: list[str] = []
    items: list[str] = []

    def flush():
        nonlocal paragraph, items
        if paragraph:
            block = ("p", None, " ".join(line.strip() for line in paragraph))
            paragraph = []
            return block
        if items:
            block = ("ul", None, items)
            items = []
            return block
        return None

    for number, raw in enumerate(text.replace("\r\n", "\n").replace("\r", "\n").split("\n"), 1):
        line = raw.rstrip()
        if not line.strip():
            block = flush()
            if block:
                yield block
            continue
        for label, pattern in OUTSIDE_SUBSET:
            if pattern.match(line):
                raise LegalRenderError(f"line {number}: {label} is outside the markdown subset")
        if items and not _LIST_ITEM.match(line):
            raise LegalRenderError(f"line {number}: a non-item line directly after a list item (add a blank line)")
        heading = _HEADING.match(line)
        if heading:
            block = flush()
            if block:
                yield block
            yield ("h", len(heading.group(1)), heading.group(2))
            continue
        item = _LIST_ITEM.match(line)
        if item:
            if paragraph:
                yield flush()
            items.append(item.group(1).strip())
            continue
        paragraph.append(line)
    block = flush()
    if block:
        yield block


def render_markdown(text: str, indent: int = REGION_INDENT, paragraph_class: str = "") -> str:
    """Render the markdown subset to HTML; every line ends with a newline.

    ``paragraph_class`` is the class of body paragraphs (front-matter paragraphs
    are always ``subtitle``); empty means no class attribute.
    """
    pad = " " * indent
    lines: list[str] = []
    in_front_matter = False
    body_attr = f' class="{html.escape(paragraph_class, quote=True)}"' if paragraph_class else ""
    for kind, level, body in _blocks(text):
        if kind == "h":
            if level >= 2 and lines:
                lines.append("")
            in_front_matter = level == 1
            lines.append(f"{pad}<h{level}>{_inline(body)}</h{level}>")
        elif kind == "p":
            attr = ' class="subtitle"' if in_front_matter else body_attr
            lines.append(f"{pad}<p{attr}>{_inline(body)}</p>")
        else:
            lines.append(f"{pad}<ul>")
            lines.extend(f"{pad}  <li>{_inline(item)}</li>" for item in body)
            lines.append(f"{pad}</ul>")
    return "".join(line + "\n" for line in lines)


def _region_for(source_text: str, page: str) -> str:
    """The exact text between the end of the begin marker and the end marker."""
    body = render_markdown(source_text, paragraph_class=PARAGRAPH_CLASS.get(page, ""))
    return "\n" + body + " " * REGION_INDENT


def _read_source(repo_root: Path, rel: str) -> str:
    path = Path(repo_root) / rel
    if not path.is_file():
        raise LegalRenderError(f"source missing: {rel}")
    return path.read_text(encoding="utf-8-sig")


def render_regions(repo_root) -> dict:
    """{page: region} for the six pages; reads the sources and writes nothing."""
    missing = [src for src in SOURCES.values() if not (Path(repo_root) / src).is_file()]
    if missing:
        raise LegalRenderError("source missing: " + ", ".join(missing))
    return {page: _region_for(_read_source(repo_root, src), page) for page, src in SOURCES.items()}


def _split_page(page_text: str, page: str):
    """(head, region, tail) of a page; exactly one marker pair is required."""
    if page_text.count(REGION_BEGIN) != 1 or page_text.count(REGION_END) != 1:
        raise LegalRenderError(f"{page}: expected one {REGION_BEGIN} and one {REGION_END}")
    start = page_text.index(REGION_BEGIN) + len(REGION_BEGIN)
    end = page_text.index(REGION_END)
    if end < start:
        raise LegalRenderError(f"{page}: {REGION_END} precedes {REGION_BEGIN}")
    return page_text[:start], page_text[start:end], page_text[end:]


def _page_with_region(page_bytes: bytes, region: str, page: str) -> bytes:
    """The page with its region replaced, keeping the page's own line endings."""
    page_text = page_bytes.decode("utf-8")
    head, _old, tail = _split_page(page_text, page)
    newline = "\r\n" if "\r\n" in page_text else "\n"
    return (head + region.replace("\n", newline) + tail).encode("utf-8")


def write_regions(repo_root, pages=None) -> list:
    """Write the region of each page (all six by default); return the changed pages.

    Every requested region is rendered before any page is written, so a missing
    source or a page without markers writes nothing.
    """
    repo_root = Path(repo_root)
    wanted = list(SOURCES) if pages is None else list(pages)
    unknown = [p for p in wanted if p not in SOURCES]
    if unknown:
        raise LegalRenderError("unknown page(s): " + ", ".join(unknown))
    planned = []
    for page in wanted:
        region = _region_for(_read_source(repo_root, SOURCES[page]), page)
        path = repo_root / page
        if not path.is_file():
            raise LegalRenderError(f"page missing: {page}")
        before = path.read_bytes()
        after = _page_with_region(before, region, page)
        planned.append((path, page, before, after))
    changed = []
    for path, page, before, after in planned:
        if after != before:
            path.write_bytes(after)
            changed.append(page)
    return changed


def stale_regions(repo_root, pages=None) -> list:
    """Pages whose committed region differs from the render (line endings ignored)."""
    repo_root = Path(repo_root)
    wanted = list(SOURCES) if pages is None else list(pages)
    unknown = [p for p in wanted if p not in SOURCES]
    if unknown:
        raise LegalRenderError("unknown page(s): " + ", ".join(unknown))
    stale = []
    for page in wanted:
        region = _region_for(_read_source(repo_root, SOURCES[page]), page)
        if not (repo_root / page).is_file():
            raise LegalRenderError(f"page missing: {page}")
        page_text = (repo_root / page).read_bytes().decode("utf-8")
        _head, committed, _tail = _split_page(page_text, page)
        if committed.replace("\r\n", "\n") != region:
            stale.append(page)
    return stale


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("pages", nargs="*", help="pages to render (default: all six)")
    parser.add_argument("--check", action="store_true", help="report stale regions, write nothing")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args(argv)
    pages = args.pages or None
    try:
        if args.check:
            stale = stale_regions(args.repo_root, pages)
            for page in stale:
                print(f"stale: {page}")
            return 1 if stale else 0
        for page in write_regions(args.repo_root, pages):
            print(f"rendered: {page}")
    except LegalRenderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
