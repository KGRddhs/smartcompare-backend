"""file_issues.py <bundle.md> <pr-number> [--dry]  -- files every === TITLE block of the bundle as a GitHub issue."""
import pathlib, re, subprocess, sys, tempfile
bundle = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
pr = sys.argv[2]
dry = "--dry" in sys.argv
blocks = re.split(r"^=== TITLE: ", bundle, flags=re.M)[1:]
here = pathlib.Path(__file__).parent
for blk in blocks:
    title, rest = blk.split("\n", 1)
    labels = ""
    if rest.startswith("=== LABELS: "):
        labels, rest = rest.split("\n", 1)
        labels = labels[len("=== LABELS: "):].strip()
    body = rest.strip().replace("#U13PR", "#" + pr) + "\n"
    print("ISSUE:", title.strip(), "| labels:", labels, "| chars:", len(body))
    if dry:
        continue
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(body); path = f.name
    args = [sys.executable, str(here / "issue_rest.py"), "create", title.strip(), path]
    if labels:
        args.append(labels)
    print(subprocess.run(args, capture_output=True, text=True, cwd=str(here)).stdout.strip())
