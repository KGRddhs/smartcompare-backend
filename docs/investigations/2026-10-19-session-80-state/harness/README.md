# Session-80 harness copies (2026-10-20)

Copied from the session-80 scratchpad before the 21:30 shutdown, because each session gets a new scratchpad.

- pyt.py: the bounded pytest runner (`python pyt.py --bound <s> --tag <tag> --log <file> --cwd <worktree> -- <pytest args>`; read --help).
- stall_monitor.py and harvest.py: set SESSION to the new session id first; list running run ids one per line in active_workflows.txt beside it.
- pr_rest.py: create / status / merge over the GitHub REST API (gh dies on this box's TLS path).
- pr_body.py: PR body helper.

Copy this folder into the new session's scratchpad (e.g. <scratchpad>/harness/) and pass that pyt path to the workflow scripts.
