"""Regression tests: reproduce.py must fail closed (STRANGER_RUN_003 repro gaps).

Every test works on a copy of the package in a pytest tmp dir; the real
receipt.json / RECEIPT.md / reproduce.py are never modified.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
FILES = ("reproduce.py", "receipt.json", "RECEIPT.md")
REQUIRED_OVERALL_LINE = '    "overall": "NOT_ESTABLISHED",\n'


@pytest.fixture
def pkg(tmp_path):
    d = tmp_path / "pkg"
    d.mkdir()
    for name in FILES:
        shutil.copy2(REPO / name, d / name)
    return d


def run(pkg_dir):
    p = subprocess.run(
        [sys.executable, str(pkg_dir / "reproduce.py")],
        cwd=pkg_dir, capture_output=True, text=True, timeout=60,
    )
    return p.returncode, p.stdout, p.stderr


def set_overall(pkg_dir, value):
    rj = pkg_dir / "receipt.json"
    data = json.loads(rj.read_text(encoding="utf-8"))
    data["cells"]["overall"] = value
    rj.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def set_required_overall(pkg_dir, value):
    rp = pkg_dir / "reproduce.py"
    src = rp.read_text(encoding="utf-8")
    assert src.count(REQUIRED_OVERALL_LINE) == 1, "REQUIRED map layout changed"
    rp.write_text(
        src.replace(REQUIRED_OVERALL_LINE, f'    "overall": "{value}",\n'),
        encoding="utf-8",
    )


def assert_no_traceback(out, err):
    assert "Traceback (most recent call last)" not in out + err


def test_genuine_receipt_passes(pkg):
    """Baseline: unmodified package data still reproduces."""
    code, out, err = run(pkg)
    assert code == 0, out + err
    assert "REPRODUCTION: SAME STATUS" in out
    assert "HYPOTHESIS_STATUS: NOT ESTABLISHED" in out


def test_1_missing_receipt_json_fails_explicitly(pkg):
    (pkg / "receipt.json").unlink()
    code, out, err = run(pkg)
    assert code != 0
    assert_no_traceback(out, err)
    assert "INPUT MISSING: receipt.json" in out
    assert "REPRODUCTION: FAILED" in out
    assert "HYPOTHESIS_STATUS: UNKNOWN" in out
    assert "SAME STATUS" not in out


def test_2_opposing_verdict_in_receipt_md_fails(pkg):
    md = pkg / "RECEIPT.md"
    md.write_text(md.read_text(encoding="utf-8") + "Overall verdict: ESTABLISHED\n",
                  encoding="utf-8")
    code, out, err = run(pkg)
    assert code != 0
    assert_no_traceback(out, err)
    assert "RECEIPT.md VERDICT CONFLICT" in out
    assert "REPRODUCTION: FAILED" in out
    assert "SAME STATUS" not in out
    assert "HYPOTHESIS_STATUS: NOT ESTABLISHED" not in out


def test_3_overall_changed_only_in_receipt_json_is_status_mismatch(pkg):
    set_overall(pkg, "ESTABLISHED")
    code, out, err = run(pkg)
    assert code == 1
    assert_no_traceback(out, err)
    assert "STATUS MISMATCH: ['overall']" in out
    assert "SAME STATUS" not in out


def test_4_hypothesis_status_comes_from_receipt_json_not_a_literal(pkg):
    # The script must not carry the verdict as a printable literal.
    assert "HYPOTHESIS_STATUS: NOT ESTABLISHED" not in (pkg / "reproduce.py").read_text()

    # (a) flip overall in BOTH receipt.json and the REQUIRED map: RECEIPT.md
    # still says NOT ESTABLISHED, so it must fail, and must never print the
    # old literal verdict.
    set_overall(pkg, "ESTABLISHED")
    set_required_overall(pkg, "ESTABLISHED")
    code, out, err = run(pkg)
    assert_no_traceback(out, err)
    assert "NOT ESTABLISHED" not in out
    assert code == 3
    assert "REPRODUCTION: FAILED" in out
    assert "HYPOTHESIS_STATUS: UNKNOWN" in out

    # (b) make RECEIPT.md agree too: the printed status must be the flipped
    # value read from cells.overall.
    md = pkg / "RECEIPT.md"
    md.write_text(md.read_text(encoding="utf-8").replace(
        "STATUS: NOT ESTABLISHED", "STATUS: ESTABLISHED"), encoding="utf-8")
    code, out, err = run(pkg)
    assert code == 0, out + err
    assert "HYPOTHESIS_STATUS: ESTABLISHED" in out
    assert "NOT ESTABLISHED" not in out
