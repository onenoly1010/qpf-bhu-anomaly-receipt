# qpf-bhu-anomaly-receipt

Receipt data: v1, pinned 2026-09-24 (`receipt.json` `version` / `pinned`; the
`RECEIPT_DATA:` line of the script's output repeats these two fields, and its
first line labels the script as this unpublished draft). The published
object is commit 19b35f6. This branch's `reproduce.py` is a later, unpublished
revision of the script only; it has no version or pin of its own.

Narrow public package. One negative result.

```
python3 reproduce.py
```

Expected stdout includes:

```
REPRODUCTION: SAME STATUS
HYPOTHESIS_STATUS: NOT ESTABLISHED
```

This package does **not** recompute Planck or Pantheon+.
It pins the audit:

- θ > 60° = PRE-EXISTING DATUM
- θ_cut = ACCOMMODATION
- C₂ = UNDERDETERMINED
- DSI = OTHER_ROW
- k_L = NO_IMPORT
- S1–S7 = LOCKED
- BHU = NOT ESTABLISHED

Getting the same labels shows only that `receipt.json`, `RECEIPT.md` and the
script's REQUIRED map agree with each other. It is a consistency check, not
independent verification of the audit. To disagree, file a challenge that
names which frozen assumption you reject.

## Fail-closed checks (UNPUBLISHED DRAFT of reproduce.py: no commit hash or pin yet; the published pin is still 19b35f6)

`reproduce.py` needs only the Python 3 standard library. It fails closed:
every failure prints `REPRODUCTION: FAILED` and `HYPOTHESIS_STATUS: UNKNOWN`
and exits nonzero. Output that the terminal encoding cannot represent is
printed as backslash escapes instead of raising (tested with UTF-8, ASCII and
cp1252 stdout). On success `HYPOTHESIS_STATUS` is
read from `receipt.json` `cells.overall`, not from a literal in the script.

### Hash pin (checked first)

`PINNED_HASHES.sha256` holds the sha256 of `receipt.json` and `RECEIPT.md`, in
the format written by `sha256sum`, so it can be checked without Python:

```
sha256sum -c PINNED_HASHES.sha256
```

Before anything is parsed, scanned or compared, `reproduce.py` reads the raw
bytes of both files and compares their sha256 with the manifest. A missing or
malformed manifest, or a missing pinned file, exits 4. A hash that differs
exits 6 (`HASH MISMATCH`). Either way nothing else is checked and no
`SAME STATUS` line is printed. On success the script prints both hashes and
the sha256 of the manifest itself.

Why a separate manifest file and not constants in `reproduce.py` or a line in
`RECEIPT.md`: `RECEIPT.md` cannot contain its own hash (changing the line
changes the hash), so the hashes have to live in a file that is not itself
hashed. A plain manifest can be checked with standard tools, and a new pin
changes one small file instead of the script. The limits are the same with
either choice: the manifest does not cover itself or `reproduce.py`, so anyone
who edits the files can also edit the manifest. The hash pin shows that the
files match the manifest in this directory. It does not show that the
manifest is the published one. Compare the manifest's sha256 (printed on
success) and the git commit with the published values.

### Secret scan (after the hash check)

Both pinned files are scanned before parsing. High-confidence secret patterns
exit 7 (`SECRET-LIKE CONTENT`) even when the hashes match. The pattern name and
line are printed, the value is not. These patterns are: PEM and OpenSSH
private-key blocks; AWS `AKIA`/`ASIA` key ids; GitHub
`ghp_`/`gho_`/`ghu_`/`ghs_`/`ghr_`/`github_pat_` tokens; Slack `xox*`; Stripe
`sk_live_`/`rk_live_`; `sk-` and `xai-` style API keys; Google `AIza` keys;
JWTs; Discord webhooks; Telegram bot tokens; `secret=`/`token:` style
assignments; and base64 runs of 56 or more characters.

Hash-like values are never blocked. Hex digits are a subset of the base64
alphabet, so a bare 64-hex sha256 would otherwise trip the long-base64 rule. A
run made only of hex digits (optionally `0x`) is therefore exempt from that
one rule and is handled like this:

- It passes silently when it is the exact whole value at an allowlisted
  `receipt.json` field: 64 hex at a key named `sha256` or `*_sha256`, or 40 hex
  at `commit`, `*_commit` or `git_sha`.
- Anywhere else (another field, a key name, any `RECEIPT.md` line) it prints
  `WARN: hash-like value, ...` and does not change the exit code.

A secret placed at an allowlisted field still exits 7. A private key written
as bare hex (for example a 64-hex wallet key) is indistinguishable from a
sha256, so it only warns.

| Exit | Meaning |
|---|---|
| 0 | `REPRODUCTION: SAME STATUS` |
| 1 | `STATUS MISMATCH`: a `receipt.json` cell is a string but differs from the script's REQUIRED map |
| 2 | `INHERITANCE LEAK`: an `inheritance` flag is anything other than `false` |
| 3 | `RECEIPT.md DRIFT`, `VERDICT CONFLICT` or `SUSPICIOUS TEXT` (see below) |
| 4 | Input missing, unreadable, too large or malformed: no file (including `PINNED_HASHES.sha256`), a malformed manifest, a file over 256 KiB (262144 bytes), bad UTF-8 or JSON, duplicate JSON key, missing top-level key, or a REQUIRED cell (including `cells.overall`) that is missing or not a string |
| 5 | Unexpected internal error (still printed as FAILED) |
| 6 | `HASH MISMATCH`: `receipt.json` or `RECEIPT.md` differs from `PINNED_HASHES.sha256` |
| 7 | `SECRET-LIKE CONTENT`: private key or provider token in `receipt.json` or `RECEIPT.md` |

What `RECEIPT.md` is checked for (exit 3):

- the non-verdict labels (PRE-EXISTING DATUM, ACCOMMODATION, UNDERDETERMINED,
  LOCKED, OTHER_ROW, NO_IMPORT) are present;
- a line `STATUS: <cells.overall>` exists (underscores shown as spaces);
- the only verdict tokens present are the one in `cells.overall`. The tokens
  are NOT ESTABLISHED, ESTABLISHED, RULED OUT, FAILED and UNKNOWN. They are
  matched case-insensitively, with letter-only boundaries (so `_ESTABLISHED_`
  and `1ESTABLISHED` count), after HTML entities are decoded, NFKC is
  applied, and format characters (zero-width, soft hyphen, BOM) and
  diacritics are removed. A second pass also removes simple HTML tags
  (`<...>` with no `<` or `>` inside) and the characters `*`, `_`, `~` and
  backtick. Comments or attributes containing `>` are not fully removed and
  markdown links are not handled, so a verdict split that way is missed and
  exits 0 (see "Not checked"). A third pass folds l/1/| to I and 0
  to O. A token found in any pass counts;
- `NOT` only negates when it is on the same line and separated from
  ESTABLISHED by spaces, tabs, `_` or `-`. A negator directly before
  NOT ESTABLISHED (for example `NOT NOT ESTABLISHED`) also fails;
- no word of two or more letters contains a non-ASCII letter (lookalikes such
  as Cyrillic `Е`), and no bidi control characters are present.

Not checked:

- other wording that asserts a verdict (for example "confirmed", "proven");
- a coordinated edit of `receipt.json`, the script's REQUIRED map,
  `RECEIPT.md` and `PINNED_HASHES.sha256` together, which reproduces as the
  edited status;
- `cells.overall` set to FAILED or UNKNOWN (with matching REQUIRED map and
  `RECEIPT.md`) is accepted and prints `REPRODUCTION: SAME STATUS`, exit 0;
- edits to `reproduce.py` itself (REQUIRED map, patterns, removed checks,
  hash check): the script cannot detect them, and neither `reproduce.py` nor
  the manifest is hashed;
- extra, unknown cells in `receipt.json`;
- the other files in this package (README.md, CHALLENGE.md);
- any physics: Planck, Pantheon+ and likelihoods are not recomputed;
- identity of what ran: no git commit or tag check. The hash pin only shows
  that the files match the manifest next to them, so exit 0 does not show that
  these are the published 19b35f6 files. Note that the published pin 19b35f6
  has no manifest at all;
- symlinks are followed, and JSON NaN / Infinity values are accepted. Before
  this revision there was no input size cap either.

Known bypasses: the verdict parser still misses every input below. Each was
tested on a copy of this revision in two ways. Appended to a pinned
`RECEIPT.md` without updating `PINNED_HASHES.sha256`, each now exits 6
(`HASH MISMATCH`) and prints no `SAME STATUS`. That closes tampering with a
file after it was pinned. With the manifest updated to match (for example an
author writing it into a newly pinned version), each still exits 0 with
`REPRODUCTION: SAME STATUS` and `HYPOTHESIS_STATUS: NOT ESTABLISHED`, even
though the rendered `RECEIPT.md` text reads as ESTABLISHED. These bypasses are
STILL OPEN; the hash pin does not fix the parser:

- a verdict split by an HTML comment or by a tag attribute that contains `>`,
  e.g. `EST<!-- a>b -->ABLISHED` or `EST<span title='>'>ABLISHED</span>`;
- a verdict split by a markdown link or image, e.g. `EST[ABLISHED](http://x)`
  or `EST![ABLISHED](x.png)`;
- control characters inside the word (e.g. U+0000, U+0001, U+0008, U+001B,
  U+007F), or U+0903 or U+2800 inside the word;
- semantic negation, e.g. `'NOT ESTABLISHED' is false.`;
- verdict tokens glued inside a longer word, e.g. `PREESTABLISHED`,
  `ESTABLISHEDly`, `coESTABLISHEDnstruction`.

Exit 0 is not independent verification, and a run by the author, maintainer
or another insider is not an outside reproduction.

Known over-rejection: the scan fails closed (exit 3) on ordinary text such as
"well-established", "unknown", "not yet established", "failed to converge",
Greek or other non-ASCII letters inside words (ΛCDM, Ωm, Δχ², μK), and names
with non-decomposable letters (Møller, Weiß, Łukasz). Cosmology prose added to
`RECEIPT.md` will therefore often exit 3.

### Regression tests

The tests need `pytest`, which is not part of the standard library:

```
python3 -m pip install pytest
python3 -m pytest -v tests/
```

They run `reproduce.py` on temporary copies; the real files are not modified.
Tests that edit `receipt.json` or `RECEIPT.md` to exercise the parser re-pin
the temporary copy's manifest first. The hash-pin tests do not. The known
bypasses above are recorded as strict `xfail` tests (reported as `xfailed`),
so a parser fix that closes one will show up as an unexpected pass.

Not claimed: stranger has already run this; USED; VALUED; DEPENDENT.
