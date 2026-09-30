# qpf-bhu-anomaly-receipt

Receipt data: v1, pinned 2026-09-24 (`receipt.json` `version` / `pinned`; the
`RECEIPT_DATA:` line of the script's output repeats these two fields, and its
first line labels the script as this unpublished draft). The published
object is commit 19b35f6. This branch is a later, unpublished revision: it
changes `reproduce.py` and adds `PINNED_HASHES.sha256`, tests, a pre-commit
hook and an optional CI workflow. `receipt.json` and `RECEIPT.md` are
byte-identical to 19b35f6. None of this revision has a version, pin or
published anchor yet.

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
sha256sum -c --strict PINNED_HASHES.sha256
```

`reproduce.py` first reads the manifest, which must contain exactly one
`<64 lowercase hex>  <name>` line for each of the two files and nothing else.
Then it reads the raw bytes of both files (a file over 256 KiB is refused
before hashing) and compares their sha256 with the manifest. Only after both
match are the files decoded, parsed and checked. A missing or malformed
manifest, or a missing pinned file, exits 4. A hash that differs exits 6
(`HASH MISMATCH`). Either way nothing else is checked and no `SAME STATUS`
line is printed. On success the script prints both hashes and the sha256 of
the manifest itself.

Why a separate manifest file and not constants in `reproduce.py` or a line in
`RECEIPT.md`: `RECEIPT.md` cannot contain its own hash (changing the line
changes the hash), so the hashes have to live in a file that is not itself
hashed. A plain manifest can be checked with standard tools, and a new pin
changes one small file instead of the script. The limits are the same with
either choice: the manifest does not cover itself or `reproduce.py`, so anyone
who edits the files can also edit the manifest. The hash pin shows that the
files match the manifest in this directory. It does not show that the
manifest is the published one.

### Anchor: none published yet

No anchor for this revision has been published. There is no official
manifest sha256 or commit id to compare against yet. Compute them yourself:

```
sha256sum -c --strict PINNED_HASHES.sha256
sha256sum PINNED_HASHES.sha256
git rev-parse HEAD
git status --porcelain
```

`git status --porcelain` should print nothing, so that the files you ran are
the ones in that commit. The manifest sha256 is also printed on the last
`HASH_PIN:` line of a successful run. The real values will be published in
registry issue #894. Status: PENDING. Nothing will be published there until
OINIO authorizes it. Until then, compare against values you computed yourself
or obtain later from that issue.

### Secret scanning (not done by `reproduce.py`)

`reproduce.py` does not scan for secrets and has no warning path. It reads no
environment variables and no configuration files, so a local run and a
stranger's untouched run of the same files check the same things. Python
still picks the stdout encoding; the genuine output is ASCII, and the tests
show it is byte-identical under the environment settings they try. Secret
scanning happens when a commit is made, with
[gitleaks](https://github.com/gitleaks/gitleaks) (tested with 8.30.1) and its
default ruleset:

- `scripts/pre-commit` runs `gitleaks git --pre-commit --staged` on the staged
  changes. It uses no custom config, allowlist or baseline, and it ignores
  inline `gitleaks:allow` comments. It refuses the commit if gitleaks is
  missing or if a `.gitleaks.toml` or `.gitleaksignore` file exists. Install
  it in a clone from the repository root:

  ```
  cp scripts/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
  ```

- `.github/workflows/gitleaks.yml` (optional CI) scans the full history with
  the same default rules. It runs only on GitHub, after a push or pull
  request.

Limits: git does not install hooks for you, so each clone must copy the hook
in, and `git commit --no-verify` skips it. The default rules can miss
secrets. For example, a bare 64-hex private key with no identifying keyword
is not flagged.

| Exit | Meaning |
|---|---|
| 0 | `REPRODUCTION: SAME STATUS` |
| 1 | `STATUS MISMATCH`: a `receipt.json` cell is a string but differs from the script's REQUIRED map |
| 2 | `INHERITANCE LEAK`: an `inheritance` flag is anything other than `false` |
| 3 | `RECEIPT.md DRIFT`, `VERDICT CONFLICT` or `SUSPICIOUS TEXT` (see below) |
| 4 | Input missing, unreadable, too large or malformed: no file (including `PINNED_HASHES.sha256`), a malformed manifest, a file over 256 KiB (262144 bytes), bad UTF-8 or JSON, duplicate JSON key, missing top-level key, or a REQUIRED cell (including `cells.overall`) that is missing or not a string |
| 5 | Unexpected internal error (still printed as FAILED) |
| 6 | `HASH MISMATCH`: `receipt.json` or `RECEIPT.md` differs from `PINNED_HASHES.sha256` |

What `RECEIPT.md` is checked for (exit 3; only after the hash pin passes):

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
  exits 0 once the manifest matches (see "Known bypasses"). A third pass
  folds l, 1, | and ! to I and 0 to O. A token found in any pass counts;
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
- symlinks are followed, and JSON NaN / Infinity values are accepted. The
  published 19b35f6 script has no input size cap either;
- secrets: `reproduce.py` does not scan for them (see "Secret scanning");
- the Python interpreter itself: variables such as `PYTHONPATH` can change
  which modules Python imports. `python3 -I reproduce.py` ignores them.

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

Known over-rejection: the `RECEIPT.md` verdict scan fails closed (exit 3) on
ordinary text such as "well-established", "unknown", "not yet established",
"failed to converge", Greek or other non-ASCII letters inside words (ΛCDM, Ωm,
Δχ², μK), and names with non-decomposable letters (Møller, Weiß, Łukasz).
Cosmology prose added to `RECEIPT.md` (with the manifest re-pinned) will
therefore often exit 3.

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
