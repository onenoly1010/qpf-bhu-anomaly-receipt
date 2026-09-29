#!/usr/bin/env python3
"""One-command reproduction of QPF BHU anomaly receipt (later pin, fail-closed).

Reproduces locked status labels from receipt.json.
Does not claim an independent Planck analysis.

Fail-closed rules (STRANGER_RUN_003 repro gaps):
- a missing or unreadable receipt.json / RECEIPT.md prints an explicit
  FAILED / UNKNOWN line and exits nonzero (no raw traceback);
- RECEIPT.md must carry exactly one verdict: the one in receipt.json
  cells.overall. Any opposing verdict token anywhere in RECEIPT.md fails;
- the printed HYPOTHESIS_STATUS is read from receipt.json cells.overall,
  never from a string literal in this script.

Exit codes:
  0 SAME STATUS
  1 STATUS MISMATCH (receipt.json cells differ from REQUIRED)
  2 INHERITANCE LEAK
  3 RECEIPT.md DRIFT or VERDICT CONFLICT
  4 INPUT MISSING / UNREADABLE / MALFORMED
  5 unexpected internal error (still reported as FAILED)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

REQUIRED = {
    "C_theta_gt_60": "PRE-EXISTING_DATUM",
    "theta_cut": "ACCOMMODATION",
    "C2": "UNDERDETERMINED",
    "S1_S7": "LOCKED",
    "P_R": "UNCOMPUTED",
    "DSI": "OTHER_ROW",
    "k_L": "NO_IMPORT",
    "overall": "NOT_ESTABLISHED",
}

# Non-verdict labels that must appear in RECEIPT.md. The verdict itself is
# checked separately (exclusively) against receipt.json cells.overall.
MARKDOWN_MUST_CONTAIN = (
    "PRE-EXISTING DATUM",
    "ACCOMMODATION",
    "UNDERDETERMINED",
    "LOCKED",
    "OTHER_ROW",
    "NO_IMPORT",
)

# Canonical verdict vocabulary (receipt.json form).
VERDICTS = ("NOT_ESTABLISHED", "ESTABLISHED", "RULED_OUT", "FAILED", "UNKNOWN")

# Leftmost-first alternation: "NOT ESTABLISHED" is consumed as one token, so a
# bare "ESTABLISHED" only matches when it is NOT part of "NOT ESTABLISHED".
# Case-insensitive on purpose: fail closed on "Established", "established", ...
VERDICT_RE = re.compile(
    r"\b(?:(?P<NOT_ESTABLISHED>NOT[\s_-]+ESTABLISHED)"
    r"|(?P<ESTABLISHED>ESTABLISHED)"
    r"|(?P<RULED_OUT>RULED[\s_-]+OUT)"
    r"|(?P<FAILED>FAILED)"
    r"|(?P<UNKNOWN>UNKNOWN))\b",
    re.IGNORECASE,
)


class ReproFailure(Exception):
    def __init__(self, code, line):
        super().__init__(line)
        self.code = code
        self.line = line


def fail(code, line):
    raise ReproFailure(code, line)


def display(verdict):
    return verdict.replace("_", " ")


def load_inputs(root):
    rj = root / "receipt.json"
    rm = root / "RECEIPT.md"
    for p in (rj, rm):
        if not p.is_file():
            fail(4, f"INPUT MISSING: {p.name} not found at {p}")
    try:
        receipt = json.loads(rj.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as e:
        fail(4, f"INPUT UNREADABLE: receipt.json ({type(e).__name__}: {e})")
    except json.JSONDecodeError as e:
        fail(4, f"INPUT MALFORMED: receipt.json is not valid JSON ({e})")
    try:
        md = rm.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        fail(4, f"INPUT UNREADABLE: RECEIPT.md ({type(e).__name__}: {e})")
    if not isinstance(receipt, dict):
        fail(4, "INPUT MALFORMED: receipt.json top level is not an object")
    for key in ("version", "pinned", "which_version", "cells"):
        if key not in receipt:
            fail(4, f"INPUT MALFORMED: receipt.json missing key '{key}'")
    if not isinstance(receipt["cells"], dict):
        fail(4, "INPUT MALFORMED: receipt.json 'cells' is not an object")
    inherit = receipt.get("inheritance", {})
    if not isinstance(inherit, dict):
        fail(4, "INPUT MALFORMED: receipt.json 'inheritance' is not an object")
    return receipt, md


def md_verdicts(md):
    found = []
    for m in VERDICT_RE.finditer(md):
        tok = m.lastgroup
        if tok not in found:
            found.append(tok)
    return found


def run(root):
    receipt, md = load_inputs(root)
    cells = receipt["cells"]
    inherit = receipt.get("inheritance", {})

    print("QPF BHU anomaly receipt", receipt["version"], receipt["pinned"])
    print("WHICH_VERSION:", receipt["which_version"])
    print("---")
    failed = []
    for k, v in REQUIRED.items():
        got = cells.get(k)
        ok = got == v
        if not ok:
            failed.append(k)
        print(f"  [{'OK' if ok else 'FAIL'}] {k}: {got}")
    print("---")

    leaks = [k for k, allowed in inherit.items() if allowed is not False]
    if leaks:
        fail(2, f"INHERITANCE LEAK: {leaks}")
    if failed:
        fail(1, f"STATUS MISMATCH: {failed}")

    overall = cells.get("overall")
    if overall not in VERDICTS:
        fail(4, f"INPUT MALFORMED: cells.overall={overall!r} is not one of {list(VERDICTS)}")

    md_missing = [s for s in MARKDOWN_MUST_CONTAIN if s not in md]
    if md_missing:
        fail(3, f"RECEIPT.md DRIFT: {md_missing}")

    # Verdict tokens are reported in canonical underscore form.
    found = md_verdicts(md)
    if found != [overall]:
        fail(3, f"RECEIPT.md VERDICT CONFLICT: receipt.json cells.overall={overall}; "
                f"verdict tokens in RECEIPT.md={found} (must be exactly [{overall}])")
    status_line = re.compile(
        r"^STATUS:[ \t]*" + re.escape(display(overall)) + r"[ \t]*$", re.MULTILINE
    )
    if not status_line.search(md):
        fail(3, f"RECEIPT.md DRIFT: no 'STATUS: <cells.overall>' line for {overall}")

    print("REPRODUCTION: SAME STATUS")
    print("HYPOTHESIS_STATUS:", display(overall))
    print("NOTE: audit labels only; Planck likelihood not recomputed.")
    return 0


def main(root=ROOT):
    try:
        return run(Path(root))
    except ReproFailure as e:
        print(e.line)
        code = e.code
    except Exception as e:  # fail closed: never let a traceback be the only signal
        print(f"INTERNAL ERROR: {type(e).__name__}: {e}")
        code = 5
    print("REPRODUCTION: FAILED")
    print("HYPOTHESIS_STATUS: UNKNOWN")
    return code


if __name__ == "__main__":
    sys.exit(main())
