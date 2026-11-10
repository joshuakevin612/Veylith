from pathlib import Path

from app.scanners.base import Finding, Scanner

# Dev B registers each scanner here as it is built (secrets, deps, sast).
SCANNERS: list[Scanner] = []


def run_scan(repo_dir: Path) -> list[Finding]:
    """Run every registered scanner over an extracted repository folder."""
    findings: list[Finding] = []
    for scanner in SCANNERS:
        findings.extend(scanner.scan(repo_dir))
    return findings


__all__ = ["Finding", "run_scan"]
