# Annotation codebook and protocol changelog

Every change after a freeze needs: new version, date, what changed, why (which pilot or main items
led to it), affected items and how they are handled (re-annotated or kept).

| Version | Date | Status | Change | Reason | Commit |
|---|---|---|---|---|---|
| codebook v0 | 2026-11-04 | draft for pilot | first version | — | (this commit) |
| sample v1 | 2026-11-04 | frozen (pre-registered) | pilot 40, main 400, double 120; seed 20261104 | owner decision 2026-11-04 | d197d5d |
| tooling | 2026-11-04 | — | `sample_items.py` now refuses to overwrite existing sample files or the manifest and instead checks reproduction | protect pre-registration and work in progress; sampling logic unchanged, re-run reproduced identical items | (this commit) |
| codebook v1 | — | to be frozen after the pilot | — | — | — |

Candidate topics to check in the pilot (from writing v0):
- whether `answer_support` and the IRRELEVANT definition (fact not asked) are applied consistently;
- E1 (older information with and without dates), the most frequent case in the Outdated stratum;
- whether frequent `unknown` reasons need new reason types (e.g. numeric rounding, date precision).
