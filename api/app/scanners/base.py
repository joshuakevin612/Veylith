"""CONTRACT 1 - the scanner interface.

Owned by Dev B, consumed by Dev A's worker. Changing anything in this file is a
contract change: agree on it first and ship it as its own small PR.

The scanners package must never import the database, GitHub client or FastAPI.
"""

import hashlib
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel

ScannerName = Literal["secrets", "deps", "sast"]
Severity = Literal["critical", "high", "medium", "low"]


class Finding(BaseModel):
    scanner: ScannerName
    rule_id: str
    severity: Severity
    title: str
    file_path: str  # relative to the repo root, forward slashes
    line: int | None
    snippet: str  # secrets must already be redacted here
    remediation: str
    fingerprint: str


class Scanner(Protocol):
    name: ScannerName

    def scan(self, repo_dir: Path) -> list[Finding]: ...


def make_fingerprint(scanner: str, rule_id: str, file_path: str, snippet: str) -> str:
    """Stable id for 'the same problem' across scans (ignores line number and spacing)."""
    normalised = " ".join(snippet.split())
    raw = "\x1f".join([scanner, rule_id, file_path, normalised])
    return hashlib.sha256(raw.encode()).hexdigest()
