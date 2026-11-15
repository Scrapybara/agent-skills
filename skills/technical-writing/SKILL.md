---
name: technical-writing
description: >
  Writes or rewrites any prose (specs, docs, PR descriptions, replies, commit messages) with one
  Diátaxis mode per section, then applies Google developer style, ISO 24495-1 plain language,
  ASD-STE100 sentence limits, and Global English disambiguation. Describes the final state only,
  never the path to it. Use when someone asks to make text clearer, to rewrite a document, or
  whenever a document or reply must be clear on the first read.
license: MIT
metadata:
  author: scrapybara
  version: "1.0.0"
---

# Technical writing

Write text that a tired engineer understands on the first read. Follow the five steps in order.

## 1. Pick one Diátaxis mode per section

Diátaxis is a sorting rule, not a heavy process. Each section answers one kind of question, and the reader can tell which from the first line.

- **Reference**: facts for lookup. Describe. State facts, options, limits, and errors with no opinion and no instruction.
- **Explanation**: the why. Design decisions, constraints, and alternatives. Opinion lives here and nowhere else.
- **How-to**: steps to a goal that a competent reader already has. Action only, no background.

A document is usually one mode throughout: a spec is reference, a design note is explanation, and a runbook is a how-to. A chat reply often needs more than one mode, so give each mode its own section (a heading or a paragraph break) and keep each section pure. The failure to avoid is a paragraph that states a fact, argues for it, and tells the reader what to do in the same breath.

## 2. Apply Google developer style

- Address the reader as "you" in the present tense.
- Use active voice with a named actor: "the worker retries", not "retries are performed".
- Write instructions as commands: "Run the migration." Put the condition before the instruction: "To rebuild the image, run…".
- Put the common case first and the exceptions after.
- Write headings in sentence case, and make each heading carry the point. Use numbered lists for sequences and bullets for parallel facts.
- Put code in code font and UI elements in bold. Use serial commas. Do not write "simply", "easy", or "click here".

## 3. Apply ISO 24495-1 plain language

- Put the reader first: include what they need to act, and nothing else.
- Organize the text so that the reader can find things: the answer or verdict opens the text, and detail follows.
- Write so that the reader can understand: use everyday words, the real symbol or file name, and one term per thing across the whole text.
- Make the text usable: every paragraph or bullet states a claim and its consequence together.

## 4. Apply STE sentence limits

- Write one instruction per sentence. Write one thought per sentence everywhere else.
- Keep instructions under about 20 words. Keep other sentences under about 25 words.
- Keep articles: "remove the backup file", not "remove backup file".
- Use one word per action, the same way every time: "start", never "start" in one place and "initiate" in another.
- Avoid "-ing" forms where a finite verb works.

## 5. Apply Global English disambiguation

- Keep "only" and "not" next to the word they change.
- Break noun strings longer than three words: "the script that checks the import budget", not "the import budget check script".
- Make every "it", "this", and "they" point at one noun. Repeat the noun when in doubt. Never point "this" at a whole clause.
- Give every clause its verb. Repeat the article in a series when the items are separate things.
- Say what "and" or "or" joins when a sentence can group two ways.
- Use periods, not semicolons. Start a new sentence instead of using an em dash. Do not use slashes, "(s)", idioms, or Latin abbreviations.

## Describe the final state, never the path to it

Write the thing as it is now. Do not write the history of how it got there.

- Do not layer decisions: no "A, superseded by B", no "previously", no "we tried X". Write B.
- Do not refer to who got it wrong or what failed before. The failure is not part of the final state.
- Do not hedge about the future: no "we will soon", no "for now".
- In a spec, do not keep a decision log or a supersession trail. A spec states the design that holds at this commit. If the reader needs the rationale, move it to an explanation document.
- In a reply, answer the question as it stands. Do not narrate the investigation unless the reader asked for the evidence.

## Check before sending

1. Is each section one mode, with a break where modes meet?
2. Is every instruction a command with its condition in front?
3. Does any sentence carry two thoughts? Split it.
4. Can any word go without a loss of meaning? Cut it.
5. Does every "only", "it", and "this" attach to one obvious word?
6. Does each thing have exactly one name throughout?
7. Does any sentence describe the past instead of the final state? Rewrite it.
