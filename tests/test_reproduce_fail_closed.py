"""Regression tests: reproduce.py must fail closed (STRANGER_RUN_003 repro gaps).

Every test works on a copy of the package in a pytest tmp dir; the real
receipt.json / RECEIPT.md / reproduce.py / PINNED_HASHES.sha256 are never
modified.

Hash pin: the parser/verdict tests below deliberately edit receipt.json or
RECEIPT.md. So that they keep testing the parser (and not just the hash pin),
run() / run_env() re-pin the tmp copy's PINNED_HASHES.sha256 to the edited
files before running. The hash pin itself is tested with run_raw(), which
never re-pins.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
FILES = ("reproduce.py", "receipt.json", "RECEIPT.md", "PINNED_HASHES.sha256")
MANIFEST = "PINNED_HASHES.sha256"
PINNED = ("receipt.json", "RECEIPT.md")
REQUIRED_OVERALL_LINE = '    "overall": "NOT_ESTABLISHED",\n'


@pytest.fixture
def pkg(tmp_path):
    d = tmp_path / "pkg"
    d.mkdir()
    for name in FILES:
        shutil.copy2(REPO / name, d / name)
    return d


def repin(pkg_dir):
    """Rewrite the tmp copy's manifest to match its current files (missing
    files keep their old line, so a missing-file test still sees the pin)."""
    mp = pkg_dir / MANIFEST
    old = {}
    if mp.exists():
        for line in mp.read_text(encoding="utf-8").splitlines():
            if "  " in line:
                h, n = line.split("  ", 1)
                old[n] = h
    lines = []
    for n in PINNED:
        f = pkg_dir / n
        h = hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else old.get(n, "0" * 64)
        lines.append(f"{h}  {n}\n")
    mp.write_text("".join(lines), encoding="utf-8")


def run_raw(pkg_dir, **env):
    """Run WITHOUT re-pinning: exercises the hash pin itself."""
    e = dict(os.environ)
    e.update(env)
    p = subprocess.run(
        [sys.executable, str(pkg_dir / "reproduce.py")],
        cwd=pkg_dir, capture_output=True, text=True, timeout=60, env=e,
    )
    return p.returncode, p.stdout, p.stderr


def run(pkg_dir):
    repin(pkg_dir)
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


# --- Round 3 (hostile review round 2) --------------------------------------
import os
import time

MAX_INPUT_BYTES = 256 * 1024  # must match reproduce.py


def run_env(pkg_dir, **env):
    repin(pkg_dir)
    e = dict(os.environ)
    e.update(env)
    t0 = time.monotonic()
    p = subprocess.run(
        [sys.executable, str(pkg_dir / "reproduce.py")],
        cwd=pkg_dir, capture_output=True, timeout=60, env=e,
    )
    return p.returncode, p.stdout, p.stderr, time.monotonic() - t0


def _dup_nonascii_key(d):
    rj = d / "receipt.json"
    src = rj.read_text(encoding="utf-8")
    rj.write_text(src.replace('"C2"', '"\u0416": 1, "\u0416": 2, "C2"', 1), encoding="utf-8")


def _nonascii_inheritance_key(d):
    rj = d / "receipt.json"
    data = json.loads(rj.read_text(encoding="utf-8"))
    data["inheritance"]["\u0416leak"] = True
    rj.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _nonascii_mismatch_value(d):
    rj = d / "receipt.json"
    data = json.loads(rj.read_text(encoding="utf-8"))
    data["cells"]["C2"] = "\u0416MISMATCH"
    rj.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


ENCODING_CASES = {
    "dup_nonascii_key": (_dup_nonascii_key, 4, b"duplicate key"),
    "nonascii_inheritance_key": (_nonascii_inheritance_key, 2, b"INHERITANCE LEAK"),
    "nonascii_mismatch_value": (_nonascii_mismatch_value, 1, b"STATUS MISMATCH"),
}


@pytest.mark.parametrize("encoding", ["ascii", "cp1252"])
@pytest.mark.parametrize("case", list(ENCODING_CASES), ids=list(ENCODING_CASES))
def test_8_non_utf8_stdout_never_tracebacks(pkg, encoding, case):
    mutate, want_code, want_line = ENCODING_CASES[case]
    mutate(pkg)
    code, out, err, _ = run_env(pkg, PYTHONIOENCODING=encoding)
    assert b"Traceback" not in out + err
    assert err == b""
    assert code == want_code, out
    assert want_line in out
    assert b"REPRODUCTION: FAILED" in out
    assert b"HYPOTHESIS_STATUS: UNKNOWN" in out


@pytest.mark.parametrize("encoding", ["ascii", "cp1252"])
def test_8b_genuine_output_identical_under_non_utf8_stdout(pkg, encoding):
    code_u, out_u, _, _ = run_env(pkg, PYTHONIOENCODING="utf-8")
    code_e, out_e, err_e, _ = run_env(pkg, PYTHONIOENCODING=encoding)
    assert code_u == code_e == 0
    assert err_e == b""
    assert out_e == out_u
    assert b"HYPOTHESIS_STATUS: NOT ESTABLISHED" in out_e


@pytest.mark.parametrize("name,pad", [("RECEIPT.md", "<" * (1024 * 1024)),
                                      ("RECEIPT.md", " " * (MAX_INPUT_BYTES + 1)),
                                      ("receipt.json", " " * (MAX_INPUT_BYTES + 1))],
                         ids=["md_1MiB_lt", "md_just_over_cap", "json_just_over_cap"])
def test_9_oversize_input_exits_4_fast(pkg, name, pad):
    p = pkg / name
    p.write_text(p.read_text(encoding="utf-8") + pad, encoding="utf-8")
    code, out, err, dt = run_env(pkg)
    assert b"Traceback" not in out + err
    assert code == 4, out
    assert f"INPUT TOO LARGE: {name}".encode() in out
    assert b"REPRODUCTION: FAILED" in out
    assert dt < 5, dt


def test_9b_pathological_lt_under_cap_completes_fast(pkg):
    md = pkg / "RECEIPT.md"
    md.write_text(md.read_text(encoding="utf-8") + "<" * 250_000, encoding="utf-8")
    assert md.stat().st_size <= MAX_INPUT_BYTES
    code, out, err, dt = run_env(pkg)
    assert b"Traceback" not in out + err
    assert code == 0, out
    assert dt < 5, dt


def test_9c_file_exactly_at_cap_is_accepted(pkg):
    md = pkg / "RECEIPT.md"
    size = md.stat().st_size
    md.write_bytes(md.read_bytes() + b"\n" * (MAX_INPUT_BYTES - size))
    assert md.stat().st_size == MAX_INPUT_BYTES
    code, out, err, _ = run_env(pkg)
    assert code == 0, out


def test_9d_cap_constant_matches_script():
    src = (REPO / "reproduce.py").read_text(encoding="utf-8")
    assert "MAX_INPUT_BYTES = 256 * 1024" in src


# --- Round 5: hash pin, draft header ----------------------------------------

DRAFT_HEADER = ("QPF BHU anomaly receipt: UNPUBLISHED DRAFT of reproduce.py "
                "(no commit hash or pin yet; published pin is still 19b35f6)")


def read_manifest(pkg_dir):
    out = {}
    for line in (pkg_dir / MANIFEST).read_text(encoding="utf-8").splitlines():
        h, n = line.split("  ", 1)
        out[n] = h
    return out


def assert_failed_closed(code, out, err, want_code, want_msg):
    assert code == want_code, out + err
    assert_no_traceback(out, err)
    assert want_msg in out, out
    assert "REPRODUCTION: FAILED" in out
    assert "HYPOTHESIS_STATUS: UNKNOWN" in out
    assert "SAME STATUS" not in out
    assert "NOT ESTABLISHED" not in out
    assert "[OK]" not in out  # nothing parsed / checked before the failure


def test_10_committed_manifest_pins_the_genuine_files():
    pins = read_manifest(REPO)
    assert sorted(pins) == sorted(PINNED)
    for n in PINNED:
        assert pins[n] == hashlib.sha256((REPO / n).read_bytes()).hexdigest(), n


def test_10b_genuine_files_pass_without_repin(pkg):
    code, out, err = run_raw(pkg)
    assert code == 0, out + err
    lines = out.splitlines()
    assert lines[0] == DRAFT_HEADER
    assert "RECEIPT_DATA: v1 2026-09-24" in lines
    pins = read_manifest(pkg)
    for n in PINNED:
        assert f"HASH_PIN: OK {n} sha256 {pins[n]}" in lines
    msha = hashlib.sha256((pkg / MANIFEST).read_bytes()).hexdigest()
    assert any(l.startswith(f"HASH_PIN: {MANIFEST} sha256 {msha}") for l in lines)
    assert "WARN" not in out
    assert "REPRODUCTION: SAME STATUS" in out
    assert "HYPOTHESIS_STATUS: NOT ESTABLISHED" in out


def test_10c_header_is_ascii_and_verdict_free():
    src = (REPO / "reproduce.py").read_text(encoding="utf-8")
    assert DRAFT_HEADER.isascii()
    assert "ESTABLISHED" not in DRAFT_HEADER.upper()
    assert 'print("QPF BHU anomaly receipt", receipt["version"]' not in src


@pytest.mark.parametrize("name", ["receipt.json", "RECEIPT.md"])
@pytest.mark.parametrize("where", ["first", "middle", "last"])
def test_11_one_byte_change_is_hash_mismatch_exit_6(pkg, name, where):
    p = pkg / name
    data = bytearray(p.read_bytes())
    i = {"first": 0, "middle": len(data) // 2, "last": len(data) - 1}[where]
    data[i] ^= 0x01
    p.write_bytes(bytes(data))
    code, out, err = run_raw(pkg)
    assert_failed_closed(code, out, err, 6, f"HASH MISMATCH: {name} sha256 ")


def test_11b_hash_check_precedes_parsing(pkg):
    # Invalid JSON and invalid UTF-8: the hash mismatch must be reported first,
    # i.e. the changed file is refused before it is decoded or parsed.
    (pkg / "receipt.json").write_bytes(b"{not json \xff\xfe")
    code, out, err = run_raw(pkg)
    assert_failed_closed(code, out, err, 6, "HASH MISMATCH: receipt.json")
    assert "INPUT MALFORMED" not in out and "INPUT UNREADABLE" not in out


def test_12_missing_manifest_exits_4(pkg):
    (pkg / MANIFEST).unlink()
    code, out, err = run_raw(pkg)
    assert_failed_closed(code, out, err, 4, f"INPUT MISSING: {MANIFEST}")


def _good_lines(pkg_dir):
    return (pkg_dir / MANIFEST).read_text(encoding="utf-8").splitlines()


@pytest.mark.parametrize("mutate", [
    lambda L: [],
    lambda L: L[:1],
    lambda L: L + L[:1],
    lambda L: [L[0].upper().replace("RECEIPT.JSON", "receipt.json"), L[1]],
    lambda L: [L[0].replace("  ", " ", 1), L[1]],
    lambda L: L + ["0" * 64 + "  reproduce.py"],
    lambda L: L + ["# comment"],
    lambda L: [L[0][1:], L[1]],
], ids=["empty", "one_line", "duplicate", "uppercase_hex", "single_space",
        "extra_file", "comment", "short_hash"])
def test_12b_malformed_manifest_exits_4(pkg, mutate):
    (pkg / MANIFEST).write_text("\n".join(mutate(_good_lines(pkg))) + "\n",
                                encoding="utf-8")
    code, out, err = run_raw(pkg)
    assert_failed_closed(code, out, err, 4, "INPUT M")


@pytest.mark.parametrize("name", ["receipt.json", "RECEIPT.md"])
def test_13_missing_pinned_file_exits_4(pkg, name):
    (pkg / name).unlink()
    code, out, err = run_raw(pkg)
    assert_failed_closed(code, out, err, 4, f"INPUT MISSING: {name}")


# The 15 Round-4 known bypasses. (a) appended to a pinned RECEIPT.md without a
# manifest update -> hash mismatch. (b) with the manifest re-pinned, the parser
# still misses them: recorded as strict xfail, i.e. STILL OPEN.
C = lambda cp: chr(cp)  # noqa: E731
BYPASSES = [
    "Verdict: EST<!-- a>b -->ABLISHED",
    "Verdict: EST<span title='>'>ABLISHED</span>",
    "Verdict: EST[ABLISHED](http://x)",
    "Verdict: EST![ABLISHED](x.png)",
    "Verdict: ESTAB" + C(0x01) + "LISHED",
    "Verdict: ESTAB" + C(0x7F) + "LISHED",
    "Verdict: ESTAB" + C(0x00) + "LISHED",
    "Verdict: ESTAB" + C(0x08) + "LISHED",
    "Verdict: ESTAB" + C(0x1B) + "LISHED",
    "Verdict: ESTAB" + C(0x0903) + "LISHED",
    "Verdict: ESTAB" + C(0x2800) + "LISHED",
    "Verdict: 'NOT ESTABLISHED' is false.",
    "Verdict: coESTABLISHEDnstruction",
    "Verdict: PREESTABLISHED",
    "Verdict: ESTABLISHEDly",
]
BYPASS_IDS = ["html_comment", "span_attr", "md_link", "md_image", "U+0001",
              "U+007F", "U+0000", "U+0008", "U+001B", "U+0903", "U+2800",
              "quoted_negation", "coESTABLISHEDnstruction", "PREESTABLISHED",
              "ESTABLISHEDly"]


@pytest.mark.parametrize("text", BYPASSES, ids=BYPASS_IDS)
def test_14a_known_bypass_without_repin_is_hash_mismatch(pkg, text):
    append_md(pkg, "\n" + text + "\n")
    code, out, err = run_raw(pkg)
    assert_failed_closed(code, out, err, 6, "HASH MISMATCH: RECEIPT.md")


@pytest.mark.xfail(strict=True, reason="STILL OPEN: verdict parser misses this "
                   "bypass when the manifest is re-pinned (see README Known bypasses)")
@pytest.mark.parametrize("text", BYPASSES, ids=BYPASS_IDS)
def test_14b_known_bypass_with_repin_parser_still_misses(pkg, text):
    append_md(pkg, "\n" + text + "\n")
    code, out, err = run(pkg)
    assert code != 0 and "SAME STATUS" not in out, out


# --- Round 6: no secret scanner in reproduce.py; no environment dependence --
# Secret scanning moved to the commit layer (gitleaks, scripts/pre-commit).
# Fake secret-shaped strings are assembled at runtime so this file carries no
# literal that gitleaks' default rules would flag.

import ast

FAKE_TOKEN = "gh" + "p_" + "aB3dE6gH9jK2mN5pQ8sT1vW4yZ7bC0eF3hJ6"
FAKE_PEM_HEADER = "-----BEGIN " + "RSA PRIVATE KEY-----"
HEX64 = "9f" * 16 + "0a" * 16

SCRIPT_SRC = (REPO / "reproduce.py").read_text(encoding="utf-8")
SCRIPT_AST = ast.parse(SCRIPT_SRC)


def _fail_codes(tree):
    codes = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "fail"):
            assert isinstance(node.args[0], ast.Constant), ast.dump(node)
            codes.add(node.args[0].value)
    return codes


def test_16_reproduce_py_has_no_secret_scan_code_path():
    # exit codes: fail() is only ever called with 1, 2, 3, 4 or 6 (5 is the
    # internal-error path in main); there is no exit 7.
    assert _fail_codes(SCRIPT_AST) == {1, 2, 3, 4, 6}
    assert "fail(7" not in SCRIPT_SRC.replace(" ", "")
    # no scanner identifiers
    names = set()
    for node in ast.walk(SCRIPT_AST):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    bad = [n for n in names if any(w in n.lower() for w in
           ("secret", "warn", "hex_run", "hash_field", "allowlist", "pure_hex"))]
    assert bad == []
    # no scanner strings / patterns outside the module docstring
    doc = ast.get_docstring(SCRIPT_AST, clean=False)
    consts = [n.value for n in ast.walk(SCRIPT_AST)
              if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value != doc]
    for needle in ("SECRET", "WARN", "PRIVATE KEY", "AKIA", "ghp", "xox", "sk_live",
                   "AIza", "BEGIN"):
        assert not any(needle.lower() in c.lower() for c in consts), needle
    # no environment access, no config file
    assert not names & {"environ", "environb", "getenv", "getenvb", "putenv"}
    assert not any(isinstance(n, (ast.Import, ast.ImportFrom)) and
                   any(a.name in ("os", "configparser", "argparse") for a in n.names)
                   for n in ast.walk(SCRIPT_AST))


@pytest.mark.parametrize("extra,where", [
    ("ci credential " + FAKE_TOKEN, "RECEIPT.md"),
    (FAKE_PEM_HEADER, "RECEIPT.md"),
    ("source tarball sha: " + HEX64, "RECEIPT.md"),
    (FAKE_TOKEN, "receipt.json"),
    (HEX64, "receipt.json"),
], ids=["token_md", "pem_md", "hex64_md", "token_json", "hex64_json"])
def test_16b_secret_shaped_content_is_not_inspected_by_reproduce_py(pkg, extra, where):
    """reproduce.py no longer scans for secrets: with the manifest re-pinned,
    content the Round-5 scanner blocked (exit 7) or warned on is judged only by
    the hash pin and the status checks. Output never contains WARN or 'secret'
    and differs from the genuine run only in the three HASH_PIN hash values."""
    _, genuine, _ = run(pkg)
    if where == "RECEIPT.md":
        append_md(pkg, "\n" + extra + "\n")
    else:
        p = pkg / "receipt.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        d["note"] = extra
        p.write_text(json.dumps(d, indent=2), encoding="utf-8")
    code, out, err = run(pkg)
    assert code == 0, out + err
    assert "warn" not in (out + err).lower() and "secret" not in (out + err).lower()
    g = [l for l in genuine.splitlines() if not l.startswith("HASH_PIN:")]
    o = [l for l in out.splitlines() if not l.startswith("HASH_PIN:")]
    assert o == g


def test_16c_failure_outputs_never_mention_warn_or_secret(pkg):
    outs = []
    for mutate in (lambda: None,
                   lambda: append_md(pkg, "\n" + FAKE_TOKEN + "\n"),  # no repin: 6
                   lambda: (pkg / MANIFEST).unlink()):                # 4
        mutate()
        code, out, err = run_raw(pkg)
        assert code in (0, 1, 2, 3, 4, 5, 6)
        outs.append(out + err)
    assert all("warn" not in o.lower() and "secret" not in o.lower() for o in outs)


ENV_SETS = {
    "PYTHONIOENCODING_ascii": {"PYTHONIOENCODING": "ascii"},
    "PYTHONIOENCODING_cp1252": {"PYTHONIOENCODING": "cp1252"},
    "PYTHONIOENCODING_latin1": {"PYTHONIOENCODING": "latin-1"},
    "LANG_C": {"LANG": "C", "LC_ALL": "C"},
    "LC_ALL_C.UTF-8": {"LC_ALL": "C.UTF-8"},
    "PYTHONUTF8_1": {"PYTHONUTF8": "1"},
    "PYTHONUTF8_0": {"PYTHONUTF8": "0"},
    "PYTHONHASHSEED_0": {"PYTHONHASHSEED": "0"},
    "PYTHONHASHSEED_12345": {"PYTHONHASHSEED": "12345"},
    "TZ": {"TZ": "Pacific/Kiritimati"},
    "CI": {"CI": "true", "GITHUB_ACTIONS": "true"},
    "GITLEAKS": {"GITLEAKS_CONFIG": "/nonexistent.toml", "GITLEAKS_CONFIG_TOML": "x"},
    "TERM": {"TERM": "dumb", "NO_COLOR": "1", "COLUMNS": "20"},
    "HOME": {"HOME": "/nonexistent"},
    "made_up_flags": {"QPF_SKIP_HASH": "1", "SKIP_HASH_PIN": "1",
                      "SKIP_SECRET_SCAN": "1", "REPRODUCE_DEBUG": "1",
                      "QPF_ALLOW_UNPINNED": "1"},
}


def _run_bytes(pkg_dir, env):
    e = dict(os.environ)
    e.update(env)
    p = subprocess.run([sys.executable, str(pkg_dir / "reproduce.py")],
                       cwd=pkg_dir, capture_output=True, timeout=60, env=e)
    return p.returncode, p.stdout, p.stderr


@pytest.mark.parametrize("name", list(ENV_SETS))
@pytest.mark.parametrize("case", ["genuine", "hash_mismatch"])
def test_17_environment_variables_do_not_change_output(pkg, name, case):
    if case == "hash_mismatch":
        md = pkg / "RECEIPT.md"
        b = bytearray(md.read_bytes())
        b[len(b) // 2] ^= 0x01
        md.write_bytes(bytes(b))
    base = _run_bytes(pkg, {})
    got = _run_bytes(pkg, ENV_SETS[name])
    assert got[0] == base[0] == (0 if case == "genuine" else 6)
    assert got[1] == base[1]
    assert got[2] == base[2] == b""
