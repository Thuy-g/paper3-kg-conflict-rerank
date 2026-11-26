# Annotation codebook v0.1 (draft for the pilot)

Status: **draft**. Replaces v0 for the pilot; v0 is kept unchanged for history. After the pilot
(about 40 items, two independent annotators) this draft is revised and frozen as `codebook_v1.md`.
Every later change gets a new version and a reason in `CHANGELOG.md`. Protocol:
`docs/ANNOTATION_GUIDELINES.md`.

All examples are **invented** (fictional places and people), not taken from the annotation data.

## 0. Your task in one paragraph

Each item shows a **question**, a **reference answer** and **one passage** (title, date if known,
text). Decide how the passage relates to the reference answer **for the question as asked**.

**This is reference-relative annotation.** You judge the passage against the dataset's reference
answer. You do **not** check independently whether every fact is true in the world. The reference
answer is shown to annotators only; the methods being evaluated never see it.

| Field | Required | Values |
|---|---|---|
| `decision` | yes | `COMPATIBLE`, `CONTRADICTING`, `IRRELEVANT`, `UNKNOWN` |
| `answer_support` | yes | `yes`, `partial`, `no`, `unclear` (§4) |
| `reasons` | no (multi-label) | §5; separate several with `;` |
| `rationale` | for `CONTRADICTING` and `UNKNOWN` | one or two sentences |
| `confidence` | no | `high`, `medium`, `low` |
| `reason_note` | when a reason is `unknown` | free text, e.g. "numbers rounded" |
| `flags` | no (multi-label) | `passage_truncated`, `passage_unreadable`, `question_ambiguous`, `reference_unclear`, `reference_suspect`, `needs_domain_knowledge` |

## 1. Ground rules

1. **Use only what is shown:**
   - the question;
   - the reference answer;
   - the passage title, date and text.

   Do **not**:
   - search the web;
   - look at Wikidata or any other knowledge base;
   - ask an LLM;
   - open the project's data files or manifests;
   - discuss items with the other annotator before both of you have submitted.
2. **The reference answer is the anchor.**
   - In CONFLICTS, the dataset's annotators wrote it as the correct and up-to-date answer from the search results.
   - In 2WikiMultiHopQA, it is the dataset answer.
   - If it looks wrong, still label relative to it and add `reference_suspect`. If it looks unclear or
     incomplete, add `reference_unclear`.
   - Flagged items are kept, counted, and analysed with and without them. They are never dropped silently.
3. **Common sense and language understanding are fine.** Facts you would need to look up are not available.
4. **If what is shown is not enough to decide, choose `UNKNOWN` and say why.** Do not guess.
5. **Judge each passage on its own.** Other passages for the same question do not change this passage's
   label.
6. **Reasons explain why the passage looks different from the reference.** They never decide the decision
   on their own (§5).

## 2. Time, place and entity

- **Question scope.**
  - The time, place and entity stated in the question.
  - If the question gives no time, it is about the time of the benchmark snapshot. CONFLICTS was collected
    around spring 2025.
  - Relative words in the question ("this year", "current", "latest") refer to that snapshot, not to today.
- **Passage scope.** Only what the passage itself establishes: explicit dates, years, periods, or time
  words.
  - **The passage date is not the time a fact holds.** An article dated 2024 about a 1990 event is about
    1990.
  - Use the passage date only to interpret explicit relative words in the passage ("currently", "this
    year", "so far", "last season"), and only when it plausibly is the writing date.
  - A date shown as "4 days ago", or no date, means: no usable date.
- **Missing time is unknown time.** If neither the passage nor a usable date shows when a claim holds, its
  time is **unknown**. Unknown time is **not** the same time as the question's.
  - Exception: facts that cannot change over time, such as a place of birth or the date of one past event.

## 3. Procedure

**Step 1 — Can you read it?**
- If the passage is unreadable, or the part you need is cut off → `UNKNOWN`.
- Add `passage_unreadable` or `passage_truncated`.

**Step 2 — Does the passage bear on the asked fact?**
- The *asked fact* is the subject, relation and scope the question asks about.
- In multi-step questions, it also covers any **intermediate (bridge) fact** needed to reach the answer.
  For example, for "Where was the director of film F born?", the fact "F was directed by D" is a bridge fact.
- **No** → `IRRELEVANT`. The passage is about another topic, another entity (including a different entity
  with the same name), or a property of the right entity that is not needed for the answer.
- **Cannot tell** (for example, you cannot tell whether the passage's "Port Avalon" is the question's) →
  `UNKNOWN`.
- **Yes** → step 3.

**Step 3 — Compare with the reference answer under the question scope.**

- **`COMPATIBLE`:** the passage can be true together with the reference answer. For example, it:
  - gives the reference value in any wording;
  - gives a coarser value that contains it;
  - gives a value explicitly for another time or place;
  - states the same relation in the other direction;
  - states a bridge fact that does not conflict;
  - gives another value for a relation that can clearly have several values.
- **`CONTRADICTING`** — only when **all three** hold:
  1. it is about the same asked fact (same entity and relation);
  2. it is about the **same scope**, established by what is shown (the passage states or clearly implies the
     question's time and place), or the fact cannot change over time;
  3. its value **cannot be true together with** the reference. This must follow from the nature of the fact
     — one value only (a birthplace, a count of the same thing at the same time, the date of one event, a
     superlative such as "highest" or "first", "the current X" when only one X can exist at a time) — or
     from the passage's own words ("the only", "sole"). A value that merely **differs** from the reference is
     not enough.
- **`UNKNOWN`:** the passage bears on the fact but one of these conditions cannot be decided from what is
  shown, for example because the time is unknown or the relation may have several values.

## 4. `answer_support` (usefulness, separate from compatibility)

| Value | Meaning |
|---|---|
| `yes` | The passage alone gives the reference answer for the question scope (any wording; for yes/no questions, the passage alone settles the reference yes/no). |
| `partial` | The passage gives part of what is needed: a bridge fact, a coarser value, a range containing the reference, one item of a list answer, or the reference with a hedge. |
| `no` | The passage does not support the reference answer. Always `no` for `CONTRADICTING` and `IRRELEVANT`; also for a `COMPATIBLE` value about another time or place. |
| `unclear` | You cannot tell (typically with `UNKNOWN`, e.g. truncated text). |

## 5. Reasons (auxiliary; multi-label; never decide the decision)

Leave `reasons` empty when the passage matches the reference in the same wording, or is simply
off-topic.

| Reason | Use when the passage differs from the reference because … |
|---|---|
| `alias` | it names the same entity with another current name or short form |
| `historical_identity` | it uses a former name of the same entity |
| `hierarchy` | it gives a broader or narrower item in a non-geographic part-whole relation, including a coarser date |
| `geographic_granularity` | it gives a larger or smaller place, or explicitly scopes the answer to another region |
| `temporal_scope` | its value holds, or may hold, for a different time |
| `entity_identity_mismatch` | it is about a different (but similar) entity |
| `homonym` | it is about a different entity with the same name |
| `inverse_relation` | it states the same relation in the other direction |
| `predicate_mismatch` | it gives a related but different property that looks like an answer. Decision is `IRRELEVANT` if that property is not needed, `COMPATIBLE` if it is a needed bridge fact |
| `counterfactual` | it states a different value for the same fact and scope, and no reason above explains it |
| `unknown` | none of the above fits; **describe it in `reason_note`** (e.g. rounding, units) |

## 6. Edge cases (v0.1 proposals; the pilot tests them)

- **E1. Older information.**
  - Different value with an explicit time that differs from the question's → `COMPATIBLE` +
    `temporal_scope`, `answer_support: no`.
  - Different value with **no** usable time → `UNKNOWN` (add `temporal_scope` if the passage suggests older
    information).
  - The passage asserts the different value **for the question's time** ("as of 2025 …", or "currently …" in
    a plausibly 2025-dated passage), and the fact has one value at a time → `CONTRADICTING`.
- **E2. Numbers.**
  - Consistent approximation ("about 1,100" for 1,098) → `COMPATIBLE`, reason `unknown`, note "rounding".
  - Explicitly different measure or region → `COMPATIBLE` + `geographic_granularity`.
  - Same measure and the same established time, different number → `CONTRADICTING`.
  - Same measure but unknown time, for a quantity that changes → `UNKNOWN`.
- **E3. Several answers, or an incomplete reference.**
  - The relation can clearly have several values → another value is `COMPATIBLE` (`answer_support: no`, or
    `partial` if it overlaps the reference); add `reference_unclear` if the reference looks incomplete.
  - You cannot tell whether several values are possible → `UNKNOWN`.
  - `CONTRADICTING` needs the exclusivity of step 3.
- **E4. Reported or hedged claims.**
  - Judge what the passage itself asserts.
  - "Estimates range from A to B" with the reference inside → `COMPATIBLE` (`partial`).
  - Claims only reported, never endorsed → `UNKNOWN`.
- **E5. Mixed values.**
  - The passage asserts a conflicting value as true for the same scope → `CONTRADICTING`.
  - It only lists disagreeing values → `UNKNOWN`.
- **E6. Cut-off text.** Judge the visible text. If the decisive part is missing → `UNKNOWN` +
  `passage_truncated`.
- **E7. Comparison and yes/no questions (2Wiki).** One side's fact is a bridge fact → `COMPATIBLE`
  (`partial`), unless what is shown makes the reference impossible.
- **E8. Similar-looking distractors.** Another person or work with the same or a similar name →
  `IRRELEVANT` + `homonym` or `entity_identity_mismatch`.

## 7. Worked examples (invented)

Question: *Who is the head of government of Port Avalon?* Reference: **Teo Brandt** (snapshot 2025).

| # | Passage (date) | decision | answer_support | reasons |
|---|---|---|---|---|
| 1 | "Teo Brandt has led the city since 2012." (2024-05-02) | COMPATIBLE | yes | — |
| 2 | "In 2010 the city was led by Mira Okonkwo." | COMPATIBLE | no | temporal_scope |
| 3 | "Mira Okonkwo leads the city government." (no date) | UNKNOWN | unclear | temporal_scope |
| 4 | "As of March 2025, Bram Ostler is head of government of Port Avalon." | CONTRADICTING | no | counterfactual |
| 5 | "Port Avalon (a racing yacht) was skippered by Rosa Fein." | IRRELEVANT | no | homonym |
| 6 | "Port Avalon's chief of police is Gil Moray." | IRRELEVANT | no | predicate_mismatch |

Question: *Where was the director of the film "Grey Harbour" born?* Reference: **Lowmarsh**.

| # | Passage | decision | answer_support | reasons |
|---|---|---|---|---|
| 7 | "Grey Harbour (1998) was directed by Ivo Sallis." | COMPATIBLE | partial | — (bridge fact) |
| 8 | "Ivo Sallis died in Northgate in 2019." | IRRELEVANT | no | predicate_mismatch |
| 9 | "Ivo Sallis was born in Avalon Province, the province around Lowmarsh." | COMPATIBLE | partial | geographic_granularity |
