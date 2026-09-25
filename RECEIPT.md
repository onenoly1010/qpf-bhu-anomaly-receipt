# QPF BHU anomaly receipt v1
# Pin: 2026-09-24
# Scope: anomaly layer only. Does not reopen S1–S7.

## Construction
WHICH_VERSION: Gaztañaga BHU lineage 2022–2026
FORK: BHU-2025-NEAR-FLAT | BHU-2025-STRONG-CURVATURE
PARENT_ENVELOPES:
  - QPF_BHU_ANOMALY_AUDIT_v1
  - QPF_BHU_PERTURBATION_COMPLETENESS_AUDIT_v1
  - QPF_PUBLIC_RECEIPT_PATH_v1

## Registered assumptions
- Model A freeze: Planck 2018 TTTEEE+lowE+lensing + BAO + Pantheon+ + BK18
- Forbidden tokens: similar / analogous / therefore we live inside
- Completeness before fit
- Datum ≠ prediction
- LQC k_L, DSI, EPRL: no inheritance

## Provenance cells
C(θ > 60°):
  CLASS: PRE-EXISTING DATUM
  NOTE: WMAP/Planck large-angle correlation hole predates BHU papers

θ_cut ≈ 65.9° ± 9.2°:
  CLASS: ACCOMMODATION
  REASON: angle sits on the known feature; not derived from r_S
           independently of C(θ) in the registered construction

C_2 / low quadrupole:
  CLASS: UNDERDETERMINED
  REASON: no registered W(ℓ) from bounce transfer + normalization

S1–S7 primordial chain:
  CLASS: LOCKED
  REASON: no hashed c_s²(ρ) through w → -1

DSI / parity:
  CLASS: OTHER_ROW
  REASON: Gaztañaga–Kumar direct-sum inflation is a separate
           WHICH_VERSION; author overlap is not inheritance

LQC k_L:
  CLASS: NO_IMPORT
  REASON: infrared scar k_L ~ a_B √ρ_c is a different mechanism

## Status
HYPOTHESIS: Our universe is the interior of a black hole.
STATUS: NOT ESTABLISHED
θ_cut: ACCOMMODATION
C_2: UNDERDETERMINED
P_R(k): UNCOMPUTED
CROSS_ROW: BHU isolated from LQC / LQG / DSI / EPRL

## What this package reproduces
The audit *logic and status line*, given the registered papers and
the frozen gates. It does not recompute Planck likelihoods.
A stranger who accepts the same assumptions must obtain the same
status labels. Disagreement must name which assumption they reject.
