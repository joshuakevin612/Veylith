from pathlib import Path

from app.scanners import run_scan
from app.scanners.base import make_fingerprint


def test_run_scan_on_empty_folder(tmp_path: Path) -> None:
    assert run_scan(tmp_path) == []


def test_fingerprint_ignores_whitespace_but_not_rule() -> None:
    a = make_fingerprint("sast", "py-eval", "app.py", "eval( x )")
    b = make_fingerprint("sast", "py-eval", "app.py", "eval(  x )")
    c = make_fingerprint("sast", "py-exec", "app.py", "eval( x )")
    assert a == b
    assert a != c
