# Spec — Flashcard Pro (DP-600)

## 1. Purpose

Single-user study tool for DP-600 / Microsoft Fabric. Active recall with self-grading, topic + difficulty filtering, review of new/missed cards, and a stats dashboard. No login, no external services.

## 2. User Flow

1. `GET /` → mode + topic picker (`index.html`), with overall progress summary.
2. `POST /start {mode, topic_id}` → `get_filtered_cards(mode, topic_id)` → shuffle ids → `session{quiz_stack, current_index, mode, topic_id}` → 302 `/quiz`.
   - Empty result → re-render `index.html` with `error="No cards found for this selection!"`.
3. `GET /quiz` → resolve `stack[idx]` via `get_all_cards()`, topic via `get_topics()` (fallback `Undefined`) → `quiz.html` with `card, topic, progress="n/m"`.
   - Empty stack or `idx >= len` → `index.html` with `message="Session Complete!"`.
   - Unknown IDs (stale results) are skipped by advancing `current_index`.
4. `POST /answer {card_id, answer: yes|no}` → validate int, `save_result()` → `current_index += 1` → 302 `/quiz`. Invalid `card_id` redirects without saving.
5. `GET /end` → clear session stack → 302 `/`.
6. `GET /stats` → `get_stats()` → `stats.html` (overall + by-topic + by-difficulty).

Self-grading is honor-based.

## 3. Routes

| Method | Path | Input | Output |
|--------|------|-------|--------|
| GET | `/` | — | `index.html` (mode + topic selects, stats summary) |
| POST | `/start` | `mode`, `topic_id` (all or 1-8) | 302 `/quiz` or `index.html`+error |
| GET | `/quiz` | session `quiz_stack`, `current_index` | `quiz.html` or `index.html`+message |
| POST | `/answer` | `card_id:int`, `answer: yes\|no` | 302 `/quiz` |
| GET | `/end` | — | 302 `/` (session cleared) |
| GET | `/stats` | — | `stats.html` |
| GET | `/favicon.ico` | — | `static/favicon.ico` |

Run: `python app.py` (port `PORT` default 8001, debug only if `FLASK_DEBUG=1`). `SECRET_KEY` from env, fallback dev key.

## 4. Data Model

- `topics.json`: `[{topic_id: 1-8, topic: str}]`.
- `flashcards.json`: merged 202 cards `[{id, topic_id, difficulty: simple|intermediate|advanced, term, definition}]`. `flashcards1-8.json` kept as per-topic sources.
- `results.json`: `[{id:int, correct: 0|1, timestamp: ISO}]`, append-only with auto-compaction.
- `load_json(path, default=[])` returns default on missing/corrupt file. `normalize_difficulty()` maps `medium→intermediate`, `hard→advanced`.

## 5. Filtering (`get_filtered_cards(mode, topic_id=None)`)

Topic filter applies first (if `topic_id` is a valid int). Then:

- `any` (or unknown): all (topic-filtered) cards.
- `simple|intermediate|advanced` (+ legacy `medium|hard`): normalized difficulty match.
- `new`: id never appears in `results.json`.
- `incorrect`: latest timestamped result for id is `0`.

Latest status: sort results by `timestamp`, overwrite `latest[id]`; malformed rows skipped.

## 6. Stats (`get_stats()`)

For overall, each topic, each difficulty: `{total, answered, correct, incorrect, new, accuracy%}` where answered/correct use latest attempt per card. Overall adds `results_entries` (raw log length).

## 7. Compaction

`compact_results()` keeps only the latest entry per card id, rewrites `results.json`, returns compacted list. `save_result()` calls it automatically when entries exceed `MAX_RESULTS=5000`. Invalid `card_id` returns `None` without writing.

## 8. UI Spec

- `index.html`: 560px card, mode select (any/new/incorrect + difficulties from backend), topic select (All + 8), Start button, error/message alerts, `Answered x/y · z%` + Stats link.
- `quiz.html`: progress + difficulty + topic header, term H2, hidden definition revealed by button (`.revealed`), Yes/No buttons, End session / Stats links.
- `stats.html`: overall summary card, by-topic table (Topic/Total/Done/Correct/Acc.), by-difficulty table.

## 9. Non-Functional / Security

- Local JSON, no locking; fine for single user (<300 cards).
- Client-side signed-cookie session; stale IDs skipped.
- `SECRET_KEY` via env; debug off by default; Jinja autoescape; no auth.
- Tests: `test_data_manager.py` (unittest, 7 tests) — run `python -m unittest test_data_manager -v`.

## 10. Changelog (this iteration)

- Merged `flashcards1-8.json` → `flashcards.json` (202 cards); deleted stray 90-card file.
- Fixed difficulty taxonomy to `simple/intermediate/advanced` (+ legacy aliases).
- Added topic filter, `/stats`, `/end`, stale-ID skip, `card_id` validation.
- Added `get_stats()`, `compact_results()`, auto-compact at 5000 entries.
- Hardened config (`SECRET_KEY`/`FLASK_DEBUG`/`PORT` env), added `requirements.txt` + tests.
