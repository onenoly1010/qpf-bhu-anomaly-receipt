#!/usr/bin/env python3
"""One-command reproduction of QPF BHU anomaly receipt (later pin, fail-closed).

Reproduces locked status labels from receipt.json.
Does not claim an independent Planck analysis.

Fail-closed rules (STRANGER_RUN_003 repro gaps + hostile review 2026-09-29):
- a missing, unreadable or malformed receipt.json / RECEIPT.md prints an
  explicit FAILED / UNKNOWN line and exits nonzero (no raw traceback).
  Duplicate JSON keys and a missing or non-string REQUIRED cell are malformed.
- RECEIPT.md may carry only the verdict in receipt.json cells.overall. It is
  scanned for the verdict tokens NOT ESTABLISHED / ESTABLISHED / RULED OUT /
  FAILED / UNKNOWN after normalisation (see _views); any other token found,
  or any disguised word (non-ASCII letter inside a word, bidi control) fails.
- the printed HYPOTHESIS_STATUS is read from receipt.json cells.overall,
  never from a string literal in this script.

Exit codes:
  0 SAME STATUS
  1 STATUS MISMATCH (a receipt.json cell is a string but differs from REQUIRED)
  2 INHERITANCE LEAK (an inheritance flag is anything other than false)
  3 RECEIPT.md DRIFT, VERDICT CONFLICT or SUSPICIOUS TEXT
  4 INPUT MISSING / UNREADABLE / MALFORMED
  5 unexpected internal error (still reported as FAILED)
"""
import html
import json
import re
import sys
import unicodedata
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

# Verdict token patterns, applied to the normalised views of RECEIPT.md.
# - Letter-only lookarounds instead of \b: "_", digits and punctuation do not
#   hide a token (_ESTABLISHED_, VERDICT_ESTABLISHED, 1ESTABLISHED all match).
# - The NOT / RULED separator is [ \t_-]+ only, so it cannot span a newline:
#   "NOT\nESTABLISHED" reads as a bare ESTABLISHED.
# - Leftmost-first alternation: "NOT ESTABLISHED" is consumed as one token.
# - Case-insensitive on purpose: fail closed on "Established", "established".
_L, _R = r"(?<![A-Za-z])", r"(?![A-Za-z])"
_SEP = r"[ \t_-]+"
VERDICT_RE = re.compile(
    _L + r"(?:(?P<NOT_ESTABLISHED>NOT" + _SEP + r"ESTABLISHED)"
    r"|(?P<ESTABLISHED>ESTABLISHED)"
    r"|(?P<RULED_OUT>RULED" + _SEP + r"OUT)"
    r"|(?P<FAILED>FAILED)"
    r"|(?P<UNKNOWN>UNKNOWN))" + _R,
    re.IGNORECASE,
)

# A negator directly before "NOT ESTABLISHED" ("NOT NOT ESTABLISHED",
# "no longer NOT ESTABLISHED") inverts it; reported as DOUBLE_NEGATION.
DOUBLE_NEG_RE = re.compile(
    _L + r"(?:NOT|NO|NEVER|LONGER|NOR|ISN'?T|WASN'?T|AIN'?T)" + _SEP
    + r"NOT" + _SEP + r"ESTABLISHED" + _R,
    re.IGNORECASE,
)

# ASCII-internal confusables (I/l/1/|, O/0) folded for one extra view, so
# "ESTABL1SHED" or "ESTABLlSHED" is still read as ESTABLISHED.
_ASCII_FOLD = str.maketrans({"l": "i", "1": "i", "|": "i", "!": "i", "0": "o"})
VERDICT_FOLDED_RE = re.compile(
    r"(?<![a-z])(?:(?P<NOT_ESTABLISHED>not" + _SEP + r"estabiished)"
    r"|(?P<ESTABLISHED>estabiished)"
    r"|(?P<RULED_OUT>ruied" + _SEP + r"out)"
    r"|(?P<FAILED>faiied)"
    r"|(?P<UNKNOWN>unknown))(?![a-z])"
)

# Bidi controls can reorder what is rendered (e.g. U+202E shows DEHSILBATSE as
# ESTABLISHED), so they are rejected outright rather than stripped.
_BIDI = set("\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e"
            "\u2066\u2067\u2068\u2069")
_TAG_RE = re.compile(r"<[^>]*>")
_WORD_RE = re.compile(r"[^\W\d_]{2,}")  # runs of 2+ Unicode letters


def _skeleton(text):
    """HTML-unescape, NFKC, drop format (Cf) chars, drop diacritics."""
    t = unicodedata.normalize("NFKC", html.unescape(text))
    t = "".join(c for c in t if unicodedata.category(c) != "Cf")
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if unicodedata.category(c) not in ("Mn", "Me"))
    return unicodedata.normalize("NFKC", t)


def _views(md):
    """Views of RECEIPT.md that are each scanned for verdict tokens.

    base:     skeleton text (fullwidth -> ASCII, zero-width/soft-hyphen removed,
              E+U+0301 -> E, &#69; -> E).
    stripped: base minus HTML tags and the markdown emphasis characters * _ ~ `
              so EST**ABL**ISHED or EST<b></b>ABLISHED is seen as rendered.
    A token found in ANY view counts, so adding a view can only fail closed.
    """
    base = _skeleton(md)
    stripped = re.sub(r"[*_~`]", "", _TAG_RE.sub("", base))
    return base, stripped


def suspicious_text(md):
    """Return a reason string if RECEIPT.md contains disguised text, else None.

    Chosen rule (instead of an always-incomplete confusables table): after the
    skeleton transform every word of 2+ letters must be pure ASCII. Lookalike
    letters (Cyrillic, Greek, Cherokee, ...) inside a word therefore fail
    closed whatever script they come from. Stand-alone symbols such as the
    Greek theta/rho used in the genuine receipt are single letters and pass.
    """
    bidi = sorted({f"U+{ord(c):04X}" for c in md if c in _BIDI})
    if bidi:
        return f"bidi control character(s) {bidi}"
    bad = []
    for m in _WORD_RE.finditer(_skeleton(md)):
        if not m.group().isascii() and ascii(m.group()) not in bad:
            bad.append(ascii(m.group()))
    if bad:
        return f"non-ASCII letter inside word(s) {bad[:5]}"
    return None


class ReproFailure(Exception):
    def __init__(self, code, line):
        super().__init__(line)
        self.code = code
        self.line = line


def fail(code, line):
    raise ReproFailure(code, line)


def display(verdict):
    return verdict.replace("_", " ")


class DuplicateKey(Exception):
    pass


def _no_duplicate_keys(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise DuplicateKey(k)
        out[k] = v
    return out


def load_inputs(root):
    rj = root / "receipt.json"
    rm = root / "RECEIPT.md"
    for p in (rj, rm):
        if not p.is_file():
            fail(4, f"INPUT MISSING: {p.name} not found at {p}")
    try:
        receipt = json.loads(rj.read_text(encoding="utf-8"),
                             object_pairs_hook=_no_duplicate_keys)
    except (OSError, UnicodeDecodeError) as e:
        fail(4, f"INPUT UNREADABLE: receipt.json ({type(e).__name__}: {e})")
    except json.JSONDecodeError as e:
        fail(4, f"INPUT MALFORMED: receipt.json is not valid JSON ({e})")
    except DuplicateKey as e:
        fail(4, f"INPUT MALFORMED: receipt.json has duplicate key '{e}'")
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
    for k in REQUIRED:
        if not isinstance(receipt["cells"].get(k), str):
            fail(4, f"INPUT MALFORMED: receipt.json cells.{k} is missing or not a string")
    inherit = receipt.get("inheritance", {})
    if not isinstance(inherit, dict):
        fail(4, "INPUT MALFORMED: receipt.json 'inheritance' is not an object")
    return receipt, md


def md_verdicts(md):
    found = []
    base, stripped = _views(md)
    scans = [(VERDICT_RE, base), (VERDICT_RE, stripped),
             (VERDICT_FOLDED_RE, base.lower().translate(_ASCII_FOLD)),
             (VERDICT_FOLDED_RE, stripped.lower().translate(_ASCII_FOLD))]
    for rx, text in scans:
        for m in rx.finditer(text):
            if m.lastgroup not in found:
                found.append(m.lastgroup)
    if any(DOUBLE_NEG_RE.search(v) for v in (base, stripped)):
        found.append("DOUBLE_NEGATION")
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

    reason = suspicious_text(md)
    if reason:
        fail(3, f"RECEIPT.md SUSPICIOUS TEXT: {reason}")

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
