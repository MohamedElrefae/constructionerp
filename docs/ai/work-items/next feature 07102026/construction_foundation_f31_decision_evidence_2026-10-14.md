# F31-D001 Owner Decision Evidence — Variation Order Arabic Label Amendment

Date: 2026-10-14  
Decision ref: owner-decision F31-D001 2026-10-14  
Source: construction_foundation_work_register_2026-10-12.md

## Owner decision

The owner directed restoring the definite article in the Arabic label for “Variation Order”:

- Source text: `Variation Order`
- Previous translation (v1.0): `أمر تغيير`
- Amended translation (v1.1): `أمر التغيير`
- Rationale: restore the definite form per F31-D001.

This is a terminology amendment only. It does not change workflow, approval authority, entitlement, or pricing.

## Historical v1.0 record

Legacy records describe batch acceptance for the v1.0 translation `أمر تغيير` under the historical pre-v4 workflow. That provenance was not independently verified in this amendment review. The v1.0 registry entry is retained unchanged; this amendment grants no new or retroactive v1.0 approval. See `legacy_batch_decisions.json` and `docs/translation/sign-off-1.0.md` for the recorded legacy disposition.

## Current bounded AI review

These three current reviews assess only the exact label `Variation Order` → `أمر التغيير`. They are AI reviews, not human review, legal advice, or Egyptian industry certification, and do not review any other translations. Times below are UTC.

- **AI-A1** (`GPT-6 Luna`, session `arabic_amendment_a1`, 2026-10-17 23:29:51 UTC): approve, confidence 0.78 (medium-high). Linguistic review found the definite construction label natural and more identifiable than the earlier form.
- **AI-A2** (`GPT-6 Luna`, session `arabic_amendment_a2`, 2026-10-17 23:29:58 UTC): approve, confidence 0.88. The definite article preserves the core document meaning; the label does not itself assert workflow, approval authority, entitlement, or pricing changes.
- **AI-A3** (`GPT-6 Luna`, session `arabic_amendment_a3`, 2026-10-18 00:13:53 UTC): approve, high confidence. This is a fresh structural review of the exact label.

### Preserved A3 revision trace

The same A3 session first requested revision at 2026-10-17 23:30:28 UTC: the earlier claim that normalization made the old and new labels equivalent was false, because the actual normalizer retains `ال`; migration/history behavior was also not proven by static review. At 23:32:10 UTC A3 approved an evidence-only correction, not a fresh translation approval. The fresh label approval above occurred later, on 2026-10-18 at 00:13:53 UTC. These distinct decisions are retained in `f31_review_evidence_2026-10-18.json`; none is represented as a site or test run.

## Normalization and migration limits

The old and new Arabic labels normalize differently: `أمر تغيير` → `امر تغيير`, while `أمر التغيير` → `امر التغيير`. This establishes only the output of the inspected normalizer. It does not establish endpoint search behavior, alias handling, or migration/history compatibility. No such behavior is claimed here.

## Glossary v2.2 candidate binding

The one-term glossary amendment now aligns the existing `Variation Order` entry with the F31-D001 label. It is scoped to that term: glossary schema remains v2, the term count remains 47, and no other term is changed. The exact one-term proposal and checksums are recorded at `construction/data/glossary/f31_variation_order_amendment_v2_2.json` (proposal SHA-256 `2b69cf50708881ccc867122313410af7f0d81120d8f25764dddc81e443ce4f60`).

- Prior glossary v2.1 SHA-256: `7afbef1ab892f466eb14471c99a9e76dde65b4f2e9d4a40a1405e34addc6894d`
- Candidate glossary v2.2 SHA-256: `9cbdb04120a3f6dec0d9e813b89980ba389ffad3974b4dbb36e08d9dfd8aaf81`
- The entry’s existing A1/A2 status fields remain `Approved`; the current exact-label AI-A1/A2 reviews are recorded above. This is not a human or legal certification.
- The proposal changes only the `Variation Order` Arabic value, its usage/reference provenance, its entry version, and glossary version-chain metadata; it preserves all other entries and the 47-term count.

Corrected-package review status is recorded in `f31_review_evidence_2026-10-18.json`; exact-label review alone does not certify site qualification or publication.

## Content binding

Source text: `Variation Order`  
Translated text: `أمر التغيير`
