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
    assert code == 4
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
    assert code == 3
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


# --- Round 2 (hostile review 2026-09-29) -----------------------------------

def append_md(pkg_dir, text):
    md = pkg_dir / "RECEIPT.md"
    md.write_text(md.read_text(encoding="utf-8") + text, encoding="utf-8")


def assert_md_rejected(pkg_dir):
    code, out, err = run(pkg_dir)
    assert_no_traceback(out, err)
    assert code == 3, out
    assert "REPRODUCTION: FAILED" in out
    assert "HYPOTHESIS_STATUS: UNKNOWN" in out
    assert "SAME STATUS" not in out
    return out


DISGUISED = {
    # \b treated "_" and digits as word chars; letter-only lookarounds now.
    "md_italic_underscore": "\n_ESTABLISHED_\n",
    "md_bold_underscore": "\n__ESTABLISHED__\n",
    "underscore_joined": "\nVERDICT_ESTABLISHED\n",
    "digit_joined": "\n1ESTABLISHED\n",
    # lookalike letters (non-ASCII letter inside a word -> SUSPICIOUS TEXT)
    "cyrillic_E": "\nVerdict: \u0415STABLISHED\n",
    "cyrillic_E_A": "\nVerdict: \u0415ST\u0410BLISHED\n",
    "greek_Epsilon": "\nVerdict: \u0395STABLISHED\n",
    "cherokee_lookalike_in_word": "\nVerdict: ESTABLISH\u13ACD\n",
    # NFKC folds these to ASCII
    "fullwidth": "\nVerdict: \uff25\uff33\uff34\uff21\uff22\uff2c\uff29\uff33\uff28\uff25\uff24\n",
    # format (Cf) chars are stripped before scanning
    "zwsp_split": "\nVerdict: ESTAB\u200bLISHED\n",
    "zwnj_split": "\nVerdict: ESTAB\u200cLISHED\n",
    "zwj_split": "\nVerdict: ESTAB\u200dLISHED\n",
    "word_joiner_split": "\nVerdict: ESTAB\u2060LISHED\n",
    "bom_split": "\nVerdict: ESTAB\ufeffLISHED\n",
    "soft_hyphen_split": "\nVerdict: ESTAB\u00adLISHED\n",
    "zwsp_entity_split": "\nVerdict: ESTAB&#x200B;LISHED\n",
    # diacritics / combining marks are dropped
    "combining_acute": "\n\u0045\u0301STABLISHED\n",
    # NOT separator may not span a newline
    "not_newline": "\nThis is NOT\nESTABLISHED\n",
    "not_blank_line": "\nThis is NOT\n\nESTABLISHED\n",
    # rendered-view tricks
    "intraword_emphasis": "\nVerdict: EST**ABL**ISHED\n",
    "intraword_html_tag": "\nVerdict: EST<b></b>ABLISHED\n",
    "html_entity_letter": "\nVerdict: &#69;STABLISHED\n",
    # ASCII-internal confusables
    "digit_one_for_I": "\nVerdict: ESTABL1SHED\n",
    "lower_l_for_I": "\nVerdict: ESTABLlSHED\n",
    # bidi override renders DEHSILBATSE as ESTABLISHED
    "bidi_override": "\nVerdict: \u202eDEHSILBATSE\u202c\n",
    # negated negation
    "double_negation": "\nBHU is NOT NOT ESTABLISHED\n",
    "no_longer_not": "\nBHU is no longer NOT ESTABLISHED\n",
}


@pytest.mark.parametrize("text", list(DISGUISED.values()), ids=list(DISGUISED))
def test_5_disguised_opposing_verdict_fails_closed(pkg, text):
    append_md(pkg, text)
    out = assert_md_rejected(pkg)
    assert ("VERDICT CONFLICT" in out) or ("SUSPICIOUS TEXT" in out)


EQUIVALENT = {
    "canonical_underscore": "\nsee NOT_ESTABLISHED\n",
    "hyphen": "\nsee NOT-ESTABLISHED\n",
    "nbsp": "\nsee NOT\u00a0ESTABLISHED\n",
    "tab": "\nsee NOT\tESTABLISHED\n",
    "bold_whole_phrase": "\n**NOT ESTABLISHED**\n",
}


@pytest.mark.parametrize("text", list(EQUIVALENT.values()), ids=list(EQUIVALENT))
def test_5b_same_verdict_restated_still_passes(pkg, text):
    append_md(pkg, text)
    code, out, err = run(pkg)
    assert code == 0, out + err
    assert "HYPOTHESIS_STATUS: NOT ESTABLISHED" in out


BAD_OVERALL = {
    "missing": "__DELETE__",
    "null": None,
    "int": 0,
    "list": ["NOT_ESTABLISHED"],
    "dict": {"v": "NOT_ESTABLISHED"},
}


@pytest.mark.parametrize("value", list(BAD_OVERALL.values()), ids=list(BAD_OVERALL))
def test_6_missing_or_non_string_overall_is_malformed_exit_4(pkg, value):
    rj = pkg / "receipt.json"
    data = json.loads(rj.read_text(encoding="utf-8"))
    if value == "__DELETE__":
        del data["cells"]["overall"]
    else:
        data["cells"]["overall"] = value
    rj.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    code, out, err = run(pkg)
    assert_no_traceback(out, err)
    assert code == 4, out
    assert "INPUT MALFORMED: receipt.json cells.overall is missing or not a string" in out
    assert "HYPOTHESIS_STATUS: UNKNOWN" in out


@pytest.mark.parametrize("first,last", [("ESTABLISHED", "NOT_ESTABLISHED"),
                                        ("NOT_ESTABLISHED", "ESTABLISHED")])
def test_7_duplicate_json_key_is_malformed_exit_4(pkg, first, last):
    rj = pkg / "receipt.json"
    src = rj.read_text(encoding="utf-8")
    assert src.count('"overall": "NOT_ESTABLISHED"') == 1
    rj.write_text(src.replace('"overall": "NOT_ESTABLISHED"',
                              f'"overall": "{first}", "overall": "{last}"'),
                  encoding="utf-8")
    code, out, err = run(pkg)
    assert_no_traceback(out, err)
    assert code == 4, out
    assert "duplicate key 'overall'" in out
