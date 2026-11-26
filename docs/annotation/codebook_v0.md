# Annotation codebook v0 (draft)

Status: **draft for the pilot**. After the pilot (about 40 items, two independent annotators) it is
revised and frozen as `codebook_v1.md`. Every later change gets a new version and a reason in
`CHANGELOG.md`. Protocol (sampling, roles, agreement, adjudication): `docs/ANNOTATION_GUIDELINES.md`.

The examples below are **invented** (fictional places and people). They are not taken from the
annotation data.

## 0. Your task in one paragraph

Each item shows a **question**, a **reference answer**, and **one passage** (title, date if known,
text). Decide how the passage relates to the reference answer **for the question as asked**, and
record:

| Field | Required | Values |
|---|---|---|
| `decision` | yes | `COMPATIBLE`, `CONTRADICTING`, `IRRELEVANT`, `UNKNOWN` |
| `answer_support` | yes | `yes`, `partial`, `no`, `unclear` |
| `reasons` | no (multi-label) | see §5; separate several with `;` |
| `rationale` | for `CONTRADICTING` and `UNKNOWN` | one or two sentences |
| `confidence` | no | `high`, `medium`, `low` |
| `reason_note` | when a reason is `unknown` | free text, e.g. "numbers rounded" |
| `flags` | no (multi-label) | `passage_truncated`, `passage_unreadable`, `question_ambiguous`, `reference_unclear`, `reference_suspect`, `needs_domain_knowledge` |

## 1. Ground rules

1. **Use only what is shown:**
   - the question;
   - the reference answer;
   - the passage title and text;
   - the passage date.

   Do **not**:
   - search the web;
   - look at Wikidata or any other knowledge base;
   - ask an LLM;
   - open the project's data files or manifests;
   - discuss items with the other annotator before both of you have submitted.
2. **The reference answer is the anchor.**
   - It comes from the dataset. In CONFLICTS, the dataset's annotators wrote it as the correct and up-to-date
     answer from the search results. In 2WikiMultiHopQA, it is the dataset answer.
   - Do not replace it with your own belief. If it looks wrong or unclear, still label relative to it and add
     `reference_suspect` or `reference_unclear`.
3. **Common sense and language understanding are fine.** For example, "NYC" is New York City, and "five
   dozen" is 60. Facts you would need to look up are not available.
4. **If what is shown is not enough to decide, choose `UNKNOWN` and say why.** Do not guess.
5. **Judge each passage on its own.** Other passages for the same question may disagree; that does not
   change this passage's label.
6. **Reasons explain why the passage looks different from the reference.** They never decide the
   decision on their own: the same reason can go with different decisions (§5, §6).

## 2. Scope: which time, place and entity

- **Question scope.**
  - The time, place and entity stated in the question.
  - If the question gives no time, it is about the time the reference answer refers to (for CONFLICTS, when
    the dataset was built). Relative words in the question ("this year", "current") refer to that time.
- **Passage scope.**
  - The time and place stated in the passage.
  - Relative words in the passage ("currently", "this year", "now") refer to the passage date, if one is shown.
  - A passage with neither an explicit time nor a date is read as a general, present-time statement.

## 3. Procedure

**Step 1 — Can you read it?**
- If the passage is unreadable, or the part you would need is cut off → `UNKNOWN`.
- Add the flag `passage_unreadable` or `passage_truncated`.

**Step 2 — Does the passage bear on the asked fact?**
- The *asked fact* is:
  - the subject, relation and scope the question asks about;
  - plus, in multi-step questions, any **intermediate (bridge) fact** needed to get from the question to the
    answer.
- **No** → `IRRELEVANT`. The passage is about:
  - another topic;
  - another entity (including a different entity with the same name);
  - or another property of the right entity that is not needed for the answer.
- **Cannot tell** (for example, you cannot tell whether the passage's "Port Avalon" is the question's Port
  Avalon) → `UNKNOWN`.
- **Yes** → go to step 3.

**Step 3 — Compare with the reference answer under the question scope.**
- **Consistent → `COMPATIBLE`.** The passage gives the reference value in any wording, or something that can
  be true together with it:
  - a coarser value that contains it;
  - a value for a different, explicitly stated time or place;
  - the same relation stated in the other direction;
  - a bridge fact that does not conflict.
- **Conflicting → `CONTRADICTING`.** For the question scope, or as a general/present statement, the passage
  asserts something that cannot hold together with the reference answer.
- **Cannot decide → `UNKNOWN`.** The passage bears on the fact, but the decision depends on something not
  shown. Examples: the time scope matters but is unclear, or two numbers may measure different things.

**Step 4 — `answer_support`.**

| Value | Meaning |
|---|---|
| `yes` | The passage alone gives the reference answer for the question scope (any wording). |
| `partial` | The passage gives part of what is needed: a bridge fact, a coarser value, or a range that contains the reference. |
| `no` | The passage does not support the reference answer. Always `no` for `CONTRADICTING` and `IRRELEVANT`. |
| `unclear` | You cannot tell (usually together with `UNKNOWN`). |

**Step 5 — The rest.**
- Add `reasons` (zero, one or several).
- Add `confidence`.
- Write a `rationale` (required for `CONTRADICTING` and `UNKNOWN`).
- Add `flags` if needed.

## 4. Decisions

| Decision | Meaning | Typical `answer_support` |
|---|---|---|
| `COMPATIBLE` | Bears on the asked fact and can be true together with the reference answer under the question scope. | `yes` or `partial`; `no` for a consistent fact about another explicitly stated time or place |
| `CONTRADICTING` | Bears on the asked fact and, read for the question scope or as a general statement, cannot be true together with the reference answer. | `no` |
| `IRRELEVANT` | Does not bear on the asked fact. | `no` |
| `UNKNOWN` | What is shown is not enough to choose one of the above. | `unclear` (or `no`) |

## 5. Reasons (auxiliary; multi-label; never decide the decision)

Leave `reasons` empty when the passage matches the reference in the same wording, or is simply
off-topic.

| Reason | Use when the passage differs from the reference because … | Example (invented) |
|---|---|---|
| `alias` | it names the same entity with another current name or a short form | "Avalon City" for Port Avalon |
| `historical_identity` | it uses a former name of the same entity | "Kingsbridge" (name until 1902) for Port Avalon |
| `hierarchy` | it gives a broader or narrower item in a non-geographic part-whole relation, including a coarser date | "1950" for "12 May 1950"; "the Merrow Navy" for "the Merrow Navy's 3rd fleet" |
| `geographic_granularity` | it gives a larger or smaller place, or explicitly scopes the answer to another region | "Avalon Province" for Port Avalon; "highest point of the *eastern* region" |
| `temporal_scope` | its value holds for a different time, shown by an explicit time or by the passage date | "In 2019 the mayor was Ivo Sallis" for a 2025 question |
| `entity_identity_mismatch` | it is about a different (but similar) entity | another club in the same city |
| `homonym` | it is about a different entity with the same name | Port Avalon the yacht vs. Port Avalon the city |
| `inverse_relation` | it states the same relation in the other direction | "Alma is the child of Oren" for "Who is Alma's father?" |
| `predicate_mismatch` | it gives a related but different property | place of death for a place-of-birth question |
| `counterfactual` | it states a different value for the same fact and scope, and no reason above explains it | "Port Avalon's mayor in 2010 was Bram Ostler" when the reference says Mira Okonkwo |
| `unknown` | there is a surface difference, but none of the above fits; **describe it in `reason_note`** | rounded numbers, different units |

The same reason can go with different decisions:

- `temporal_scope` + `COMPATIBLE`: "In 2019 the mayor of Port Avalon was Ivo Sallis." The value is
  explicitly scoped to 2019; the question asks about 2025.
- `temporal_scope` + `CONTRADICTING`: the passage is dated 2019 and says "Ivo Sallis has been mayor since
  2015 and remains in office until 2030". It asserts that Sallis is mayor at the question's time.
- `temporal_scope` + `UNKNOWN`: "Ivo Sallis was mayor for many years" (no dates, no passage date). You
  cannot tell whether it covers the question's time.
- `homonym` + `IRRELEVANT`: the passage is clearly about the yacht named Port Avalon.
- `homonym` + `UNKNOWN`: you cannot tell which Port Avalon the passage means.

## 6. Edge cases (v0 proposals; the pilot tests them)

- **E1. Older information.**
  - With a date or explicit time that differs from the question's time, an older value is `COMPATIBLE` +
    `temporal_scope` (`answer_support: no`). It is true for its own time and says nothing about the question's
    time.
  - Without any date or time, a different value is a general statement → `CONTRADICTING`. Add
    `temporal_scope` only if the passage itself shows that the information is older.
- **E2. Numbers.**
  - A stated approximation that is consistent with the reference ("about 1,100" for 1,098) → `COMPATIBLE`,
    reason `unknown`, note "rounding".
  - A number for an explicitly different measure or region (metro area vs. city) → `COMPATIBLE` +
    `geographic_granularity`.
  - If you cannot tell whether two numbers measure the same thing → `UNKNOWN`.
- **E3. Several valid answers.**
  - A passage giving one of the answers in the reference → `COMPATIBLE` (`partial`).
  - A passage that explicitly scopes its different answer to another region or group → `COMPATIBLE` +
    `geographic_granularity`.
  - The same different answer stated without that scope → `CONTRADICTING`.
- **E4. Reported or hedged claims.**
  - Judge what the passage itself asserts.
  - "Some say X, but in fact Y" → judge Y.
  - "Estimates range from A to B" with the reference inside → `COMPATIBLE` (`partial`).
  - Claims only reported, never endorsed → `UNKNOWN`.
- **E5. Mixed values.**
  - The passage asserts a conflicting value as true → `CONTRADICTING`.
  - It only lists disagreeing values without taking a side → `UNKNOWN`.
- **E6. Cut-off text.** Judge the visible text. If the decisive part is missing → `UNKNOWN` +
  `passage_truncated`.
- **E7. Comparison and yes/no questions (2Wiki).**
  - A passage giving one side's fact (one person's birth date) bears on the asked fact → `COMPATIBLE`
    (`partial`), unless it makes the reference impossible.
  - That usually needs both sides; with only one side visible, you normally cannot see a conflict.
- **E8. Similar-looking 2Wiki distractors.** Another person or work with the same or a similar name →
  `IRRELEVANT` + `homonym` or `entity_identity_mismatch`.

## 7. Worked examples (invented)

Question: *Who was the head of government of Port Avalon in 2010?* Reference: **Mira Okonkwo**.

| # | Passage (date) | decision | answer_support | reasons |
|---|---|---|---|---|
| 1 | "Mira Okonkwo led the city government from 2005 to 2012." (2013) | COMPATIBLE | yes | — |
| 2 | "Ms. Okonkwo, then head of the Avalon City council, opened the harbour in 2010." | COMPATIBLE | yes | alias |
| 3 | "From 2012 the head of government of Port Avalon was Teo Brandt." | COMPATIBLE | no | temporal_scope |
| 4 | "In 2010 the head of government of Port Avalon was Bram Ostler." | CONTRADICTING | no | counterfactual |
| 5 | "Port Avalon (a racing yacht) was skippered by Rosa Fein in 2010." | IRRELEVANT | no | homonym |
| 6 | "Alma Verdan, born in Port Avalon, studied mosses." | IRRELEVANT | no | — |
| 7 | "Ivo Sallis led Port Avalon's government for many years." (no date shown) | UNKNOWN | unclear | temporal_scope |
| 8 | "In 2010 Port Avalon's chief of police was Gil Moray." | IRRELEVANT | no | predicate_mismatch |
| 9 | "Port Avalon is the capital of Avalon Province." | IRRELEVANT | no | — (no surface resemblance to an answer) |
