# Annotator 2 — quick start (about one page)

Thank you for helping. Status: **A2 is not yet confirmed (TBD)**. This page is what A2 will receive.

## What you do

1. Read `codebook_v0.1.md` (about 20 minutes). It defines the four decisions, `answer_support`,
   the reasons and the edge cases. Keep it open while you work.
2. **Pilot (40 items).**
   - Fill in `pilot_A2.csv` (a spreadsheet you receive from the project owner).
   - Then send it back.
   - You will discuss disagreements only **after** both annotators have submitted.
3. **Main set (120 items).** After the codebook is frozen as v1, fill in `main_A2.csv` the same way.

## How to fill in the sheet

- Leave the first six columns as they are (`item_id`, `question`, `reference_answer`,
  `passage_title`, `passage_date`, `passage_text`).
- `decision`: one of `COMPATIBLE`, `CONTRADICTING`, `IRRELEVANT`, `UNKNOWN`.
- `answer_support`: one of `yes`, `partial`, `no`, `unclear`.
- `reasons` and `flags`: zero or more values separated by `;` (e.g. `alias;temporal_scope`).
- `rationale`: one or two sentences, **required** for `CONTRADICTING` and `UNKNOWN`.
- `confidence`: `high`, `medium` or `low` (optional).
- Save the file as CSV (UTF-8). Do not reorder or delete rows.

## Rules that matter most

- **Work independently.** Do not talk about items with annotator 1 or anyone else until both have
  submitted.
- **Use only what the sheet shows.** No web search, no Wikidata, no LLM or chatbot of any kind, and no
  project files.
- **When the information shown is not enough, choose `UNKNOWN` and explain.** Do not guess.
  - A missing date does **not** mean "the same time as the question".
  - A value that only differs from the reference is **not** automatically `CONTRADICTING` (codebook §3).
- **Judge against the reference answer.** If it looks wrong or unclear, still label relative to it and add
  `reference_suspect` or `reference_unclear`.
- **Rough time:** about 1.5–2 minutes per item. Take breaks; consistency matters more than speed.
