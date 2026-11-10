"""Run the scanners on a local folder:  uv run python -m app.scanners <folder>"""

import json
import sys
from pathlib import Path

from app.scanners import run_scan


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python -m app.scanners <folder>", file=sys.stderr)
        return 2
    repo_dir = Path(sys.argv[1])
    if not repo_dir.is_dir():
        print(f"not a folder: {repo_dir}", file=sys.stderr)
        return 2
    findings = run_scan(repo_dir)
    print(json.dumps([f.model_dump() for f in findings], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
