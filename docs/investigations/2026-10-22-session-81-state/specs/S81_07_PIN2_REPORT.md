# S81-07 PIN2 report (M-11)

HEAD before 110b3331be8d07cdc17f6c71640caf3266f0dba1 ; HEAD after 1c3fc375cffad0d8b7227cd296c21a5aee1a2229 ; branch feature/s81-07-meas-claude-gate

## diff --stat
 tests/test_s81_s07_meas_harness.py | 26 ++++++++++++++++++--------
 1 file changed, 18 insertions(+), 8 deletions(-)

## [pyt] lines
(see below)
[pyt] tag=s07q-rows start=2026-11-12 16:43:42 end=2026-11-12 16:43:47 elapsed=5s bound=600s status=OK rc=0 (2 passed: test_p05_sdk_hazards, test_p10_credential_profile_control)
[pyt] tag=s07q-file start=2026-11-12 16:46:51 end=2026-11-12 16:48:28 elapsed=97s bound=600s status=OK rc=0 (187 passed, 1 warning)

## local evidence (evidence_posix_branch.py, outside the repo)
anthropic 1.12.1 os.name nt
posix configs/default.json exists True same-bytes-as-windows-copy True
posix credentials/default.json exists True same-bytes-as-windows-copy True
posix active_config exists True same-bytes-as-windows-copy True
posix config {'authentication': {'type': 'user_oauth'}}
posix active_config default
sys.platform patched -> linux | _config_dir() = C:\Users\SYNACK~1\AppData\Local\Temp\tmp__hed4mr\.config\anthropic
_config_dir() == <tmp>/.config/anthropic : True
active_config pointer via SDK: default
NOTE: the POSIX permission branch (os.chmod 0o700 / 0o600) cannot run on Windows (os.name == 'nt').

## ruff E9,F63,F7,F82: All checks passed (rc=0). Byte check: 0 added bytes >127; file has 0 bytes >127, LF only (committed blob 0 CR).

## helper after
```python
def _fake_profile(tmp_path, monkeypatch, token):
    # The SDK's profile folder: %APPDATA%/Anthropic on Windows, ~/.config/anthropic on Linux and macOS
    # (M-11). The same fake profile is written at both; on POSIX the SDK refuses a credentials file that
    # group or others can read or write, so the folders get 0o700 and the files 0o600.
    for base in (tmp_path / "Anthropic", tmp_path / ".config" / "anthropic"):
        made = [base, base / "configs", base / "credentials"]
        if base.parent != tmp_path:
            made.insert(0, base.parent)
        (base / "configs").mkdir(parents=True)
        (base / "credentials").mkdir(parents=True)
        files = [base / "configs" / "default.json", base / "credentials" / "default.json", base / "active_config"]
        files[0].write_text(json.dumps({"authentication": {"type": "user_oauth"}}), encoding="utf-8")
        files[1].write_text(json.dumps({"type": "oauth_token", "access_token": token}), encoding="utf-8")
        files[2].write_text("default", encoding="utf-8")
        if os.name == "posix":
            for folder in made:
                os.chmod(folder, 0o700)
            for f in files:
                os.chmod(f, 0o600)
    for name in ("APPDATA", "HOME", "USERPROFILE", "XDG_CONFIG_HOME"):
        monkeypatch.setenv(name, str(tmp_path))
    for name in list(os.environ):
        if name.startswith("ANTHROPIC_"):
            monkeypatch.delenv(name, raising=False)


```
