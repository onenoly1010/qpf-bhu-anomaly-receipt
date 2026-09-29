# qpf-bhu-anomaly-receipt v1

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

Independent reproduction means: run the command, get the same labels,
or file a challenge that names which frozen assumption you reject.

## Fail-closed checks (later pin, not 19b35f6)

`reproduce.py` needs only the Python 3 standard library. It fails closed:
every failure prints `REPRODUCTION: FAILED` and `HYPOTHESIS_STATUS: UNKNOWN`
(never a bare traceback) and exits nonzero. On success `HYPOTHESIS_STATUS` is
read from `receipt.json` `cells.overall`, not from a literal in the script.

| Exit | Meaning |
|---|---|
| 0 | `REPRODUCTION: SAME STATUS` |
| 1 | `STATUS MISMATCH`: a `receipt.json` cell is a string but differs from the script's REQUIRED map |
| 2 | `INHERITANCE LEAK`: an `inheritance` flag is anything other than `false` |
| 3 | `RECEIPT.md DRIFT`, `VERDICT CONFLICT` or `SUSPICIOUS TEXT` (see below) |
| 4 | Input missing, unreadable or malformed: no file, bad UTF-8 or JSON, duplicate JSON key, missing top-level key, or a REQUIRED cell (including `cells.overall`) that is missing or not a string |
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
  diacritics are removed. A second pass also removes HTML tags and the
  characters `*`, `_`, `~` and backtick, and a third folds l/1/| to I and 0
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
- extra, unknown cells in `receipt.json`;
- the other files in this package (README.md, CHALLENGE.md).

Ordinary prose such as "well-established" or "unknown" in `RECEIPT.md` fails
closed (exit 3), and so would real words in a non-Latin script.

### Regression tests

The tests need `pytest`, which is not part of the standard library:

```
python3 -m pip install pytest
python3 -m pytest -v tests/
```

They run `reproduce.py` on temporary copies; the real files are not modified.

Not claimed: stranger has already run this; USED; VALUED; DEPENDENT.
