"""Tests for data_manager filtering, stats and compaction.

Run:  python -m pytest test_data_manager.py -q
or:   python test_data_manager.py
"""
import json
import os
import tempfile
import unittest

import data_manager


class DataManagerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cards = [
            {"id": 1, "topic_id": 1, "difficulty": "simple",
             "term": "A", "definition": "a"},
            {"id": 2, "topic_id": 1, "difficulty": "intermediate",
             "term": "B", "definition": "b"},
            {"id": 3, "topic_id": 2, "difficulty": "advanced",
             "term": "C", "definition": "c"},
        ]
        self.topics = [
            {"topic_id": 1, "topic": "T1"},
            {"topic_id": 2, "topic": "T2"},
        ]
        self.cards_file = os.path.join(self.tmp.name, 'cards.json')
        self.topics_file = os.path.join(self.tmp.name, 'topics.json')
        self.results_file = os.path.join(self.tmp.name, 'results.json')
        with open(self.cards_file, 'w') as f:
            json.dump(self.cards, f)
        with open(self.topics_file, 'w') as f:
            json.dump(self.topics, f)
        with open(self.results_file, 'w') as f:
            json.dump([], f)

        self._old = (data_manager.FLASHCARDS_FILE, data_manager.TOPICS_FILE,
                     data_manager.RESULTS_FILE)
        data_manager.FLASHCARDS_FILE = self.cards_file
        data_manager.TOPICS_FILE = self.topics_file
        data_manager.RESULTS_FILE = self.results_file

    def tearDown(self):
        (data_manager.FLASHCARDS_FILE, data_manager.TOPICS_FILE,
         data_manager.RESULTS_FILE) = self._old
        self.tmp.cleanup()

    def test_any_returns_all(self):
        self.assertEqual(len(data_manager.get_filtered_cards('any')), 3)

    def test_difficulty_filter(self):
        self.assertEqual([c['id'] for c in
                          data_manager.get_filtered_cards('simple')], [1])
        self.assertEqual([c['id'] for c in
                          data_manager.get_filtered_cards('intermediate')], [2])
        self.assertEqual([c['id'] for c in
                          data_manager.get_filtered_cards('advanced')], [3])

    def test_legacy_aliases(self):
        self.assertEqual([c['id'] for c in
                          data_manager.get_filtered_cards('medium')], [2])
        self.assertEqual([c['id'] for c in
                          data_manager.get_filtered_cards('hard')], [3])

    def test_topic_filter(self):
        got = data_manager.get_filtered_cards('any', topic_id=2)
        self.assertEqual([c['id'] for c in got], [3])
        got = data_manager.get_filtered_cards('simple', topic_id=2)
        self.assertEqual(got, [])

    def test_new_and_incorrect(self):
        self.assertEqual(len(data_manager.get_filtered_cards('new')), 3)
        data_manager.save_result(1, True)
        data_manager.save_result(2, False)
        self.assertEqual(sorted(c['id'] for c in
                                data_manager.get_filtered_cards('new')), [3])
        self.assertEqual([c['id'] for c in
                          data_manager.get_filtered_cards('incorrect')], [2])
        # Re-answering correctly removes it from incorrect.
        data_manager.save_result(2, True)
        self.assertEqual(data_manager.get_filtered_cards('incorrect'), [])

    def test_stats(self):
        data_manager.save_result(1, True)
        data_manager.save_result(2, False)
        s = data_manager.get_stats()
        self.assertEqual(s['overall']['answered'], 2)
        self.assertEqual(s['overall']['correct'], 1)
        self.assertEqual(s['by_topic'][0]['topic_id'], 1)

    def test_compact_keeps_latest(self):
        data_manager.save_result(1, False)
        data_manager.save_result(1, True)
        data_manager.save_result(1, False)
        compacted = data_manager.compact_results()
        ones = [r for r in compacted if r['id'] == 1]
        self.assertEqual(len(ones), 1)
        self.assertEqual(ones[0]['correct'], 0)


if __name__ == '__main__':
    unittest.main()
