# Annotation codebook and protocol changelog

Every change after a freeze needs: new version, date, what changed, why (which pilot or main items
led to it), affected items and how they are handled (re-annotated or kept).

| Version | Date | Status | Change | Reason | Commit |
|---|---|---|---|---|---|
| codebook v0 | 2026-11-04 | draft for pilot | first version | — | (this commit) |
| sample v1 | 2026-11-04 | frozen (pre-registered) | pilot 40, main 400, double 120; seed 20261104 | owner decision 2026-11-04 | d197d5d |
| tooling | 2026-11-04 | — | `sample_items.py` now refuses to overwrite existing sample files or the manifest and instead checks reproduction | protect pre-registration and work in progress; sampling logic unchanged, re-run reproduced identical items | (this commit) |
| codebook v0.1 | 2026-11-05 | draft for pilot (replaces v0; v0 kept) | (1) reference-relative annotation stated; (2) missing dates are unknown time, not the question's time; the passage date is not the validity time of a fact and is used only for explicit relative words; relative dates ("4 days ago") are unusable; (3) CONTRADICTING needs same fact, established same scope (or a time-invariant fact) and exclusivity — a value that only differs is not enough; (4) E1/E2/E3 rewritten accordingly; (5) bridge facts with another predicate are COMPATIBLE; predicate_mismatch only for look-alike answers; (6) answer_support clarified; (7) flagged references are kept and analysed with and without them | owner pre-pilot review 2026-11-05 | (this commit) |
| tooling | 2026-11-05 | — | passage dates shown in ISO form or empty ("NA" and relative dates are not dates); sheets rebuilt with `sample_items.py --rebuild-data`, which checks the items against the committed manifest first; manifest unchanged | 52.5% of main passages have no date | (this commit) |
| codebook v1 | — | to be frozen after the pilot | — | — | — |

Candidate topics to check in the pilot (from writing v0):
- whether `answer_support` and the IRRELEVANT definition (fact not asked) are applied consistently;
- E1 (older information with and without dates), the most frequent case in the Outdated stratum;
- whether frequent `unknown` reasons need new reason types (e.g. numeric rounding, date precision).
