#!/usr/bin/env python3
"""Stop hook: if a major source change has no matching docs change, remind Claude once.

"Major" = a new file under src/, or 40+ changed lines under src/ (tests excluded),
measured against the merge base with origin/main plus uncommitted work.
Docs = README.md, USAGE.md, CLAUDE.md, anything under docs/.
Silent when nothing major changed, when docs were touched, or when this exact set of
changes was already reminded about (so it never nags or loops).
"""

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

MAJOR_LINES = 40
DOC_FILES = ("README.md", "USAGE.md", "CLAUDE.md")


def git(*args: str) -> str:
    out = subprocess.run(["git", *args], capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else ""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        payload = {}
    if payload.get("stop_hook_active"):  # already continuing because of a hook: don't loop
        return 0

    base = git("merge-base", "HEAD", "origin/main").strip() or "HEAD"
    changed = set(git("diff", "--name-only", base).split())
    changed |= set(git("ls-files", "--others", "--exclude-standard").split())
    src = {f for f in changed if f.startswith("src/") and f.endswith(".py")}
    if not src:
        return 0
    docs = {f for f in changed if f in DOC_FILES or f.startswith("docs/")}
    if docs:
        return 0

    untracked = set(git("ls-files", "--others", "--exclude-standard").split())
    new_files = {
        f
        for f in src
        if f in untracked or f in set(git("diff", "--diff-filter=A", "--name-only", base).split())
    }
    lines = 0
    for row in git("diff", "--numstat", base, "--", "src").splitlines():
        added, removed, *_ = row.split("\t")
        lines += (int(added) if added.isdigit() else 0) + (int(removed) if removed.isdigit() else 0)
    if not new_files and lines < MAJOR_LINES:
        return 0

    key = hashlib.sha1("\n".join(sorted(src)).encode() + str(lines).encode()).hexdigest()[:12]
    marker = Path(tempfile.gettempdir()) / f"docs_check_{key}"
    if marker.exists():
        return 0
    marker.touch()

    reason = (
        "Source changed (" + ", ".join(sorted(src)[:6]) + (", …" if len(src) > 6 else "") + ") "
        "but no documentation did. Before finishing, check whether any of these need an update "
        "and edit them if so: README.md (features, layout), USAGE.md (API and options), "
        "CLAUDE.md (design rules and defaults), docs/guides/ (Chart Studio labels and steps). "
        "If nothing needs to change, say so in one line and stop."
    )
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
