"""Data layer for Flashcard Pro.

Single source of truth: flashcards.json (merged from flashcards1-8.json).
Difficulty taxonomy: simple / intermediate / advanced.
"""
import json
import os
from datetime import datetime

FLASHCARDS_FILE = 'flashcards.json'
TOPICS_FILE = 'topics.json'
RESULTS_FILE = 'results.json'

DIFFICULTIES = ['simple', 'intermediate', 'advanced']

# Legacy aliases from the old 90-card file / old code. Kept for
# backwards compatibility, normalized to the canonical taxonomy.
_DIFFICULTY_ALIASES = {'medium': 'intermediate', 'hard': 'advanced'}

# Auto-compact results.json once it grows past this many entries.
# Compaction keeps only the latest entry per card id.
MAX_RESULTS = 5000


def normalize_difficulty(value):
    """Map legacy values (medium/hard) to canonical ones."""
    v = (value or 'simple').lower()
    return _DIFFICULTY_ALIASES.get(v, v)


def load_json(filename, default=None):
    if default is None:
        default = []
    if not os.path.exists(filename):
        return default
    with open(filename, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default


def get_all_cards():
    """Return all flashcards from the merged file."""
    return load_json(FLASHCARDS_FILE, [])


def get_topics():
    return load_json(TOPICS_FILE, [])


def get_latest_status(results=None):
    """Map card_id -> latest correct (0/1), sorted by timestamp."""
    if results is None:
        results = load_json(RESULTS_FILE, [])
    latest = {}
    # Missing timestamp sorts first so real entries win.
    for r in sorted(results, key=lambda x: x.get('timestamp', '')):
        try:
            latest[int(r['id'])] = int(r['correct'])
        except (KeyError, ValueError, TypeError):
            continue
    return latest


def get_filtered_cards(mode='any', topic_id=None):
    """Filter cards by study mode and optional topic.

    mode: any | new | incorrect | simple | intermediate | advanced
    topic_id: int, str digit, or None/'all' for no topic filter.
    """
    cards = get_all_cards()
    mode = (mode or 'any').lower()
    mode = _DIFFICULTY_ALIASES.get(mode, mode)

    # Optional topic filter applies to every mode.
    if topic_id not in (None, '', 'all'):
        try:
            tid = int(topic_id)
            cards = [c for c in cards if c.get('topic_id') == tid]
        except (ValueError, TypeError):
            pass

    if mode == 'any':
        return cards

    if mode in DIFFICULTIES:
        return [c for c in cards
                if normalize_difficulty(c.get('difficulty')) == mode]

    results = load_json(RESULTS_FILE, [])
    latest_status = get_latest_status(results)
    answered_ids = set(latest_status.keys())

    if mode == 'new':
        return [c for c in cards if c.get('id') not in answered_ids]

    if mode == 'incorrect':
        return [c for c in cards if latest_status.get(c.get('id')) == 0]

    return cards


def save_result(card_id, correct):
    try:
        card_id = int(card_id)
    except (ValueError, TypeError):
        return None
    results = load_json(RESULTS_FILE, [])
    entry = {
        "id": card_id,
        "correct": 1 if correct else 0,
        "timestamp": datetime.now().isoformat()
    }
    results.append(entry)
    if len(results) > MAX_RESULTS:
        results = compact_results(results)
    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    return entry


def compact_results(results=None):
    """Keep only the latest entry per card id. Returns compacted list."""
    if results is None:
        results = load_json(RESULTS_FILE, [])
    latest_entry = {}
    for r in sorted(results, key=lambda x: x.get('timestamp', '')):
        try:
            latest_entry[int(r['id'])] = r
        except (KeyError, ValueError, TypeError):
            continue
    compacted = sorted(latest_entry.values(),
                       key=lambda x: x.get('timestamp', ''))
    if results is not None and len(results) != len(compacted):
        with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(compacted, f, indent=2)
    return compacted


def get_stats():
    """Accuracy breakdown overall, per topic and per difficulty.

    Uses latest attempt per card so re-answers update the score.
    """
    cards = get_all_cards()
    topics = get_topics()
    latest = get_latest_status()
    topic_name = {t['topic_id']: t['topic'] for t in topics}

    def summarize(subset):
        total = len(subset)
        answered = sum(1 for c in subset if c.get('id') in latest)
        correct = sum(1 for c in subset if latest.get(c.get('id')) == 1)
        incorrect = sum(1 for c in subset if latest.get(c.get('id')) == 0)
        new = total - answered
        acc = round(100 * correct / answered, 1) if answered else 0.0
        return {"total": total, "answered": answered, "correct": correct,
                "incorrect": incorrect, "new": new, "accuracy": acc}

    by_topic = []
    for t in topics:
        tid = t['topic_id']
        subset = [c for c in cards if c.get('topic_id') == tid]
        row = {"topic_id": tid, "topic": t['topic']}
        row.update(summarize(subset))
        by_topic.append(row)

    by_difficulty = []
    for d in DIFFICULTIES:
        subset = [c for c in cards
                  if normalize_difficulty(c.get('difficulty')) == d]
        row = {"difficulty": d}
        row.update(summarize(subset))
        by_difficulty.append(row)

    overall = summarize(cards)
    overall.update({"results_entries": len(load_json(RESULTS_FILE, []))})
    return {"overall": overall, "by_topic": by_topic,
            "by_difficulty": by_difficulty}
