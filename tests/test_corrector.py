"""
Unit tests for src/corrector.py.
"""

import pytest
from src.trie import Trie
from src.corrector import correct_trie, correct_brute_force


@pytest.fixture
def sample_trie_and_dict():
    words = [
        ("algorithm", 5000),
        ("algorithmic", 1000),
        ("algebra", 2000),
        ("database", 4000),
        ("datasheet", 800),
        ("data", 8000),
        ("date", 3000),
        ("kitten", 500),
        ("mitten", 600),
        ("sitting", 700),
        ("apple", 2500),
        ("apply", 2200),
        ("apron", 900),
    ]
    trie = Trie()
    for w, f in words:
        trie.insert(w, f)
    return trie, words


def test_correct_known_cases(sample_trie_and_dict):
    trie, _ = sample_trie_and_dict

    # "algoritm" -> "algorithm" (dist 1)
    results = correct_trie(trie, "algoritm", max_dist=1)
    words = [w for w, dist, freq in results]
    assert "algorithm" in words
    dist_map = {w: dist for w, dist, freq in results}
    assert dist_map["algorithm"] == 1

    # "kitten" with max_dist=1 should find "mitten" (dist 1), but not "sitting" (dist 3)
    results_kitten = correct_trie(trie, "kitten", max_dist=1)
    kitten_words = [w for w, dist, _ in results_kitten]
    assert "mitten" in kitten_words
    assert "sitting" not in kitten_words

    # "kitten" with max_dist=3 should find "sitting"
    results_kitten_3 = correct_trie(trie, "kitten", max_dist=3)
    kitten_words_3 = [w for w, dist, _ in results_kitten_3]
    assert "sitting" in kitten_words_3


def test_ranking_by_distance_then_frequency(sample_trie_and_dict):
    trie, _ = sample_trie_and_dict
    # "dat":
    # dist 0: none (not in dictionary)
    # dist 1: "data" (len 4, freq 8000), "date" (len 4, freq 3000)
    # dist 2: "database" (wait: len 8, "dat" vs "database" has dist 5)
    results = correct_trie(trie, "dat", max_dist=1)
    assert len(results) == 2
    # Both distance 1, "data" has higher frequency (8000 > 3000)
    assert results[0] == ("data", 1, 8000)
    assert results[1] == ("date", 1, 3000)


def test_agreement_with_brute_force(sample_trie_and_dict):
    trie, word_list = sample_trie_and_dict

    test_queries = [
        "algoritm",
        "dara",
        "aple",
        "kittin",
        "xyz",
        "data",
        "app",
    ]

    for q in test_queries:
        trie_matches = correct_trie(trie, q, max_dist=2)
        brute_matches = correct_brute_force(word_list, q, max_dist=2)
        assert trie_matches == brute_matches, f"Mismatch for query {q!r}"
