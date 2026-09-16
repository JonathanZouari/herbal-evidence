# Review request: Jonathan Zouari product/merge confirmation

This proposal branch (`proposal/chinese-herbal-oncology-support`) is ready for your product/merge review. This is **not** a request for clinical, evidence-methodology, TCM-practitioner, or dietetic sign-off -- the module cannot go live without those separate approvals as described in `evidence-and-safety.md`, and none of that has happened yet.

## What you're being asked to confirm

1. **Scope:** that `supportive_care_evidence` (Chinese-herbal branch) -- an evidence-education and symptom-oriented nutrition module, never a formula-recommendation or diagnosis engine -- is the right next area to propose, kept structurally separate from the existing app and from both sibling (unmerged) Ayurveda and homeopathy proposals.
2. **Safety boundaries:** that the allowed-states model, the intervention/identity non-equivalence taxonomy, the forbidden-claim list, and the quadruple-approval gate (triple for herb content, oncology-dietitian for nutrition, with no role able to substitute for another) in `evidence-and-safety.md` match your intent.
3. **The supplied-source audit, including the harder calls:** Essiac correctly kept non-TCM and blocked as a cancer treatment; PMC11734505's verified, unsafe, verbatim claim that surgery "inevitably leads to the consequences of tumor spread" recorded and explicitly refused rather than repeated; the Memorial Healthcare System spice page's overstated claims (piperine-pairing advice, "most powerful anti-cancer spice," one-clove-per-day dosing) identified and not reused; and PMC5073821 correctly treated as a use/belief survey, never as efficacy evidence for soursop, wheatgrass, or any other reported item.
4. **The herb-by-cancer evidence-card approach:** that the 21 cards correctly refuse to invent a mapping where no qualifying human evidence exists (e.g. `card-tcm-general-any-cancer`, `card-injectable-proprietary-chinese-medicines`), and correctly separate non-equivalent forms (American vs. Asian ginseng; PSK vs. culinary mushroom; food vs. extract for turmeric, ginger, and garlic).
5. **Interaction, toxicity, and adulteration protections:** the structural `avoid` handling for aristolochic-acid-associated ingredients and thunder-god-vine self-use, and the pharmacist-review routing for green tea/EGCG + bortezomib, ginseng, and concentrated spice extracts.
6. **Symptom-based nutrition and the deliberate absence of any cancer-specific diet.**
7. **The alternative-modality discovery screen** and why Wikipedia is used only as a taxonomy aid, never as evidence.
8. **Open items in `interview-decisions.md` (H2-002, H2-004, H2-007 through H2-011):** jurisdiction, reviewer identities, the Chinese-language search-access limitation, and several items (YIV-906 registry status, the five injectable proprietary medicines, animal/mineral patent medicines, and the HealthTree access status) that need dedicated follow-up before Phase 4.

## What is explicitly not being asked

- Not asking you to approve any patient-visible content -- none exists; every card and template is a draft fixture the test suite proves cannot pass the publish gate.
- Not asking for clinical, evidence-methodology, TCM-practitioner, or dietetic sign-off -- that requires the four credentialed roles described above, independent of this review.

## Validation

- `python3 scripts/validate_chinese_herbal_proposal.py` -> `OK: 21 cards, 8 diet templates, 30 sources validated`
- `python3 -m unittest discover -s backend/tests -v` -> 39/39 passed for this proposal's test module (full discovery run also includes only this branch's own tests, since the sibling proposals live on their own unmerged branches)
- `git diff --check` -> clean

## Next step if confirmed

Phase 2 (durable machine-readable contracts / additive database foundation) per `implementation-phases.md`, with its own review stop before Phase 3.
