"""rotate_admin_key.py [--services web,price-warmer]

Generates a fresh ADMIN_API_KEY (48 random bytes, url-safe, 64 chars) and sets it on the
named Railway services through the CLI. The value is never printed, logged or written to
disk: only its sha256 prefix is shown, and the same prefix is re-read from Railway (names
and the hash of the value) to confirm the write. Run from the linked project directory.
"""
import hashlib
import secrets
import shutil
import subprocess
import sys

RAILWAY = shutil.which("railway") or shutil.which("railway.exe")
assert RAILWAY, "railway CLI not on PATH"

services = ["web", "price-warmer"]
for i, a in enumerate(sys.argv):
    if a == "--services":
        services = sys.argv[i + 1].split(",")

value = secrets.token_urlsafe(48)
assert len(value) >= 60 and "=" not in value
digest = hashlib.sha256(value.encode()).hexdigest()
print("new ADMIN_API_KEY sha256 prefix:", digest[:12], "length:", len(value))

for svc in services:
    p = subprocess.run(
        [RAILWAY, "variable", "set", "ADMIN_API_KEY", "--stdin", "-s", svc, "--skip-deploys"],
        input=value, capture_output=True, text=True,
    )
    out = (p.stdout + p.stderr).replace(value, "<redacted>")
    print(svc, "set rc", p.returncode, "|", out.strip()[:160].replace("\n", " "))
    if p.returncode != 0:
        sys.exit("set failed on " + svc)

for svc in services:
    p = subprocess.run([RAILWAY, "variables", "-s", svc, "--kv"], capture_output=True, text=True)
    got = None
    for line in p.stdout.splitlines():
        if line.startswith("ADMIN_API_KEY="):
            got = line[len("ADMIN_API_KEY="):].strip()
    ok = got is not None and hashlib.sha256(got.encode()).hexdigest() == digest
    print(svc, "readback matches:", ok)
    if not ok:
        sys.exit("readback mismatch on " + svc)
print("done; the value exists only in Railway")
