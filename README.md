# qpf-bhu-anomaly-receipt

Receipt data: v1, pinned 2026-09-24 (`receipt.json` `version` / `pinned`; the
first line of the script's output repeats these two fields). The published
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

| Exit | Meaning |
|---|---|
| 0 | `REPRODUCTION: SAME STATUS` |
| 1 | `STATUS MISMATCH`: a `receipt.json` cell is a string but differs from the script's REQUIRED map |
| 2 | `INHERITANCE LEAK`: an `inheritance` flag is anything other than `false` |
| 3 | `RECEIPT.md DRIFT`, `VERDICT CONFLICT` or `SUSPICIOUS TEXT` (see below) |
| 4 | Input missing, unreadable, too large or malformed: no file, a file over 256 KiB (262144 bytes), bad UTF-8 or JSON, duplicate JSON key, missing top-level key, or a REQUIRED cell (including `cells.overall`) that is missing or not a string |
| 5 | Unexpected internal error (still printed as FAILED) |

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
- a coordinated edit of `receipt.json`, the script's REQUIRED map and
  `RECEIPT.md` together, which reproduces as the edited status;
- `cells.overall` set to FAILED or UNKNOWN (with matching REQUIRED map and
  `RECEIPT.md`) is accepted and prints `REPRODUCTION: SAME STATUS`, exit 0;
- edits to `reproduce.py` itself (REQUIRED map, patterns, removed checks):
  the script cannot detect them;
- extra, unknown cells in `receipt.json`;
- the other files in this package (README.md, CHALLENGE.md);
- any physics: Planck, Pantheon+ and likelihoods are not recomputed;
- identity of what ran: no git commit, tag or file-hash check, so exit 0 does
  not show that these are the published 19b35f6 files;
- symlinks are followed, and JSON NaN / Infinity values are accepted. Before
  this revision there was no input size cap either.

Known bypasses: each of these still exits 0 with `REPRODUCTION: SAME STATUS`
and `HYPOTHESIS_STATUS: NOT ESTABLISHED`, even though the rendered
`RECEIPT.md` text reads as ESTABLISHED (each verified on a copy of this
revision):

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

Not claimed: stranger has already run this; USED; VALUED; DEPENDENT.
