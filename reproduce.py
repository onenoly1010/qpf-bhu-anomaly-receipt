#!/usr/bin/env python3
"""One-command reproduction of QPF BHU anomaly receipt v1.

Reproduces locked status labels from receipt.json.
Does not claim an independent Planck analysis.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
receipt = json.loads((ROOT / "receipt.json").read_text())

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

MARKDOWN_MUST_CONTAIN = (
    "PRE-EXISTING DATUM",
    "ACCOMMODATION",
    "UNDERDETERMINED",
    "LOCKED",
    "OTHER_ROW",
    "NO_IMPORT",
    "NOT ESTABLISHED",
)

cells = receipt["cells"]
failed = [k for k, v in REQUIRED.items() if cells.get(k) != v]
inherit = receipt.get("inheritance", {})
leaks = [k for k, allowed in inherit.items() if allowed]

print("QPF BHU anomaly receipt", receipt["version"], receipt["pinned"])
print("WHICH_VERSION:", receipt["which_version"])
print("---")
for k, v in REQUIRED.items():
    got = cells.get(k)
    mark = "OK" if got == v else "FAIL"
    print(f"  [{mark}] {k}: {got}")
print("---")
md = (ROOT / "RECEIPT.md").read_text()
md_missing = [s for s in MARKDOWN_MUST_CONTAIN if s not in md]

if leaks:
    print("INHERITANCE LEAK:", leaks)
    raise SystemExit(2)
if failed:
    print("STATUS MISMATCH:", failed)
    raise SystemExit(1)
if md_missing:
    print("RECEIPT.md DRIFT:", md_missing)
    raise SystemExit(3)
print("REPRODUCTION: SAME STATUS")
print("HYPOTHESIS_STATUS: NOT ESTABLISHED")
print("NOTE: audit labels only; Planck likelihood not recomputed.")
