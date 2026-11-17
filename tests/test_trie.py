"""
Unit tests for src/trie.py.
"""

import pytest
from src.trie import Trie, TrieNode


def test_trie_node_initialization():
    node = TrieNode()
    assert node.children == {}
    assert not node.is_end
    assert node.freq == 0


def test_trie_insert_and_search():
    trie = Trie()
    assert len(trie) == 0

    trie.insert("apple", 100)
    assert len(trie) == 1
    assert trie.search("apple") == 100
    assert trie.search("app") is None
    assert trie.search("appl") is None
    assert trie.search("banana") is None

    # Overwrite frequency
    trie.insert("apple", 250)
    assert len(trie) == 1
    assert trie.search("apple") == 250

    # Insert prefix as valid word
    trie.insert("app", 80)
    assert len(trie) == 2
    assert trie.search("app") == 80
    assert trie.search("apple") == 250


def test_trie_get_node():
    trie = Trie()
    trie.insert("cat", 10)
    trie.insert("car", 20)
    trie.insert("card", 30)

    c_node = trie.get_node("c")
    assert c_node is not None
    assert "a" in c_node.children

    ca_node = trie.get_node("ca")
    assert ca_node is not None
    assert set(ca_node.children.keys()) == {"t", "r"}

    card_node = trie.get_node("card")
    assert card_node is not None
    assert card_node.is_end
    assert card_node.freq == 30

    assert trie.get_node("dog") is None
    assert trie.get_node("cards") is None


def test_trie_delete_and_pruning():
    trie = Trie()
    trie.insert("car", 10)
    trie.insert("cart", 20)
    assert len(trie) == 2

    # Deleting "car" should unmark "car" but preserve "cart"
    assert trie.delete("car") is True
    assert len(trie) == 1
    assert trie.search("car") is None
    assert trie.search("cart") == 20

    # Now deleting "cart" should completely prune 'c' -> 'a' -> 'r' -> 't'
    assert trie.delete("cart") is True
    assert len(trie) == 0
    assert trie.search("cart") is None
    assert len(trie.root.children) == 0

    # Deleting non-existent word returns False
    assert trie.delete("nonexistent") is False


def test_trie_iter_words():
    trie = Trie()
    words = [
        ("algorithm", 50),
        ("algorithmic", 30),
        ("algebra", 20),
        ("database", 40),
    ]
    for w, f in words:
        trie.insert(w, f)

    alg_node = trie.get_node("alg")
    results = dict(trie.iter_words(alg_node, "alg"))
    assert results == {
        "algorithm": 50,
        "algorithmic": 30,
        "algebra": 20,
    }

    none_results = list(trie.iter_words(None, ""))
    assert none_results == []
