"""
Unit tests for src/topk.py.
"""

import pytest
from src.trie import Trie
from src.topk import top_k, select_word, Candidate


def test_candidate_comparator():
    # Lower freq is smaller (worse)
    c1 = Candidate("alpha", 10)
    c2 = Candidate("beta", 20)
    assert c1 < c2

    # Equal freq: lexicographically larger word is smaller (worse)
    c_apple = Candidate("apple", 50)
    c_zebra = Candidate("zebra", 50)
    assert c_zebra < c_apple  # zebra is worse rank, evicted first
    assert not (c_apple < c_zebra)


def test_top_k_ordering():
    trie = Trie()
    entries = [
        ("app", 10),
        ("apple", 50),
        ("application", 40),
        ("apply", 30),
        ("applet", 20),
        ("apricot", 100),
    ]
    for w, f in entries:
        trie.insert(w, f)

    # Top 3 for "app"
    results = top_k(trie, "app", k=3)
    assert len(results) == 3
    assert results == [
        ("apple", 50),
        ("application", 40),
        ("apply", 30),
    ]

    # Non-existent prefix
    assert top_k(trie, "xyz", k=5) == []

    # k=0
    assert top_k(trie, "app", k=0) == []


def test_top_k_tie_breaking():
    trie = Trie()
    entries = [
        ("cat", 100),
        ("car", 100),
        ("cab", 100),
        ("can", 100),
        ("card", 50),
    ]
    for w, f in entries:
        trie.insert(w, f)

    # All frequency 100 should be tie-broken alphabetically
    results = top_k(trie, "ca", k=4)
    words = [w for w, _ in results]
    assert words == ["cab", "can", "car", "cat"]


def test_select_word_ranking_change():
    trie = Trie()
    trie.insert("python", 10)
    trie.insert("pytorch", 12)

    # Initially "pytorch" ranks above "python"
    res1 = top_k(trie, "py", k=2)
    assert res1[0][0] == "pytorch"
    assert res1[1][0] == "python"

    # Boost "python" by 5
    new_freq = select_word(trie, "python", delta=5)
    assert new_freq == 15

    # Now "python" ranks above "pytorch"
    res2 = top_k(trie, "py", k=2)
    assert res2[0][0] == "python"
    assert res2[0][1] == 15
    assert res2[1][0] == "pytorch"
    assert res2[1][1] == 12

    # Select word that doesn't exist yet
    new_freq2 = select_word(trie, "pyspark", delta=7)
    assert new_freq2 == 7
    assert trie.search("pyspark") == 7
