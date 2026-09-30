#!/usr/bin/env python3
"""One-command reproduction of QPF BHU anomaly receipt (UNPUBLISHED DRAFT, fail-closed; published pin: 19b35f6).

Checks that receipt.json, RECEIPT.md and this script's REQUIRED map agree on
the locked status labels, and prints the status read from receipt.json. This
is a consistency check, not an independent Planck analysis.

Hash pin (checked FIRST, before either file is decoded, parsed or checked):
- PINNED_HASHES.sha256 (sha256sum format) holds the sha256 of receipt.json and
  RECEIPT.md. The raw bytes of both files must match or the run fails closed
  (exit 6). The manifest does not list itself (a file cannot contain its own
  hash) and does not cover reproduce.py, so a match only shows that the files
  agree with the manifest next to them. No anchor is published yet (anchor
  location: to be announced). Until an anchor is published, comparing the
  manifest's sha256 (printed on success) and `git rev-parse HEAD` with values
  you computed yourself authenticates NOTHING: it only records what you ran
  and catches a script that misreports its own hashes.
- This script does not scan for secrets. Secret scanning is done only at
  commit time, by gitleaks via scripts/pre-commit in clones that installed
  that hook (staged diff only), plus a manual-only CI workflow; see README.
- The script reads no environment variables and no configuration files. The
  Python interpreter still picks the stdout encoding from the environment
  (PYTHONIOENCODING, locale); the genuine output is ASCII, so it is
  byte-identical under any ASCII-compatible encoding, and characters stdout
  cannot encode are printed as backslash escapes. Interpreter-level variables
  such as PYTHONPATH are outside the script's control (`python3 -I` ignores
  them).

Fail-closed rules (STRANGER_RUN_003 repro gaps + hostile review 2026-09-29):
- a missing, unreadable or malformed receipt.json / RECEIPT.md prints an
  explicit FAILED / UNKNOWN line and exits nonzero (no raw traceback).
  Duplicate JSON keys and a missing or non-string REQUIRED cell are malformed.
- RECEIPT.md may carry only the verdict in receipt.json cells.overall. It is
  scanned for the verdict tokens NOT ESTABLISHED / ESTABLISHED / RULED OUT /
  FAILED / UNKNOWN after normalisation (see _views); any other token found,
  or any disguised word (non-ASCII letter inside a word, bidi control) fails.
  The scan is incomplete: README lists known inputs it misses.
- the printed HYPOTHESIS_STATUS is read from receipt.json cells.overall,
  never from a string literal in this script.

Exit codes:
  0 SAME STATUS
  1 STATUS MISMATCH (a receipt.json cell is a string but differs from REQUIRED)
  2 INHERITANCE LEAK (an inheritance flag is anything other than false)
  3 RECEIPT.md DRIFT, VERDICT CONFLICT or SUSPICIOUS TEXT
  4 INPUT MISSING / UNREADABLE / MALFORMED / TOO LARGE (> MAX_INPUT_BYTES),
    including a missing or malformed PINNED_HASHES.sha256
  5 unexpected internal error (still reported as FAILED)
  6 HASH MISMATCH (receipt.json or RECEIPT.md differs from PINNED_HASHES.sha256)
"""
import hashlib
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Input size cap. The genuine receipt.json is 599 bytes and RECEIPT.md 1874
# bytes; anything above 256 KiB is refused (exit 4) before any parsing.
MAX_INPUT_BYTES = 256 * 1024

# Hash pin. The manifest is a separate, unhashed file (self-reference trap:
# RECEIPT.md cannot contain its own hash). Format: one "<sha256>  <name>" line
# per pinned file, exactly as written by `sha256sum receipt.json RECEIPT.md`,
# so it can also be checked without Python:
# `sha256sum -c --strict PINNED_HASHES.sha256`.
MANIFEST_NAME = "PINNED_HASHES.sha256"
PINNED_FILES = ("receipt.json", "RECEIPT.md")
_MANIFEST_LINE_RE = re.compile(r"([0-9a-f]{64})  (\S+)")

DRAFT_LABEL = ("QPF BHU anomaly receipt: UNPUBLISHED DRAFT of reproduce.py "
               "(no commit hash or pin yet; published pin is still 19b35f6)")

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
_TAG_RE = re.compile(r"<[^<>]*>")  # linear: cannot rescan past another "<"
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


def read_capped_bytes(p):
    """Read at most MAX_INPUT_BYTES raw bytes; larger files fail closed (exit 4)."""
    try:
        with open(p, "rb") as f:
            data = f.read(MAX_INPUT_BYTES + 1)
    except OSError as e:
        fail(4, f"INPUT UNREADABLE: {p.name} ({type(e).__name__}: {e})")
    if len(data) > MAX_INPUT_BYTES:
        fail(4, f"INPUT TOO LARGE: {p.name} exceeds {MAX_INPUT_BYTES} bytes")
    return data


def decode_text(p, data):
    """UTF-8 decode with universal newlines, as the pre-hash-pin reader did."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        fail(4, f"INPUT UNREADABLE: {p.name} ({type(e).__name__}: {e})")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def load_manifest(root):
    """Parse PINNED_HASHES.sha256 strictly: exactly one line per pinned file."""
    mp = root / MANIFEST_NAME
    if not mp.is_file():
        fail(4, f"INPUT MISSING: {MANIFEST_NAME} (hash pin) not found at {mp}")
    raw = read_capped_bytes(mp)
    lines = [l for l in decode_text(mp, raw).split("\n") if l != ""]
    pins = {}
    for n, line in enumerate(lines, 1):
        m = _MANIFEST_LINE_RE.fullmatch(line)
        if not m or m.group(2) not in PINNED_FILES or m.group(2) in pins:
            fail(4, f"INPUT MALFORMED: {MANIFEST_NAME} line {n} is not "
                    f"'<64 lowercase hex>  <receipt.json|RECEIPT.md>' (or is a duplicate)")
        pins[m.group(2)] = m.group(1)
    for name in PINNED_FILES:
        if name not in pins:
            fail(4, f"INPUT MALFORMED: {MANIFEST_NAME} has no hash for {name}")
    return pins, hashlib.sha256(raw).hexdigest()


def load_inputs(root):
    rj = root / "receipt.json"
    rm = root / "RECEIPT.md"
    # 1. hash pin: manifest, raw bytes, sha256 -- before any parsing
    pins, manifest_sha = load_manifest(root)
    raw = {}
    for p in (rj, rm):
        if not p.is_file():
            fail(4, f"INPUT MISSING: {p.name} not found at {p}")
        raw[p.name] = read_capped_bytes(p)
    for name in PINNED_FILES:
        got = hashlib.sha256(raw[name]).hexdigest()
        if got != pins[name]:
            fail(6, f"HASH MISMATCH: {name} sha256 {got} != pinned {pins[name]} "
                    f"({MANIFEST_NAME}); file changed since it was pinned")
    # 2. decode and parse, only after both hashes matched
    rj_text = decode_text(rj, raw["receipt.json"])
    md = decode_text(rm, raw["RECEIPT.md"])
    try:
        receipt = json.loads(rj_text, object_pairs_hook=_no_duplicate_keys)
    except json.JSONDecodeError as e:
        fail(4, f"INPUT MALFORMED: receipt.json is not valid JSON ({e})")
    except DuplicateKey as e:
        fail(4, f"INPUT MALFORMED: receipt.json has duplicate key '{e}'")
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
    return receipt, md, pins, manifest_sha


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
    receipt, md, pins, manifest_sha = load_inputs(root)
    cells = receipt["cells"]
    inherit = receipt.get("inheritance", {})

    print(DRAFT_LABEL)
    print("RECEIPT_DATA:", receipt["version"], receipt["pinned"])
    print("WHICH_VERSION:", receipt["which_version"])
    for name in PINNED_FILES:
        print(f"HASH_PIN: OK {name} sha256 {pins[name]}")
    print(f"HASH_PIN: {MANIFEST_NAME} sha256 {manifest_sha} "
          "(not self-verifying; no published anchor yet, anchor location: to be "
          "announced; matching a value you computed yourself authenticates nothing)")
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


def _safe_streams():
    """Never let an unencodable character turn a status line into a traceback.

    Under a UTF-8 stdout nothing changes; under e.g. PYTHONIOENCODING=ascii or
    cp1252, characters the encoding lacks are printed as backslash escapes.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError, OSError):
            pass


def main(root=ROOT):
    _safe_streams()
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
