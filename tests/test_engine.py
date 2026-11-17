"""
Unit and integration tests for src/engine.py and src/loader.py.
"""

import pytest
from src.engine import AutocompleteEngine, SuggestionResult
from src.loader import load_dictionary


def test_loader_basic(tmp_path):
    tsv_file = tmp_path / "words.txt"
    tsv_file.write_text("apple\t100\napplication\t200\nbanana\t50\n", encoding="utf-8")

    trie, dictionary = load_dictionary(tsv_file)
    assert len(trie) == 3
    assert len(dictionary) == 3
    assert dictionary["apple"] == 100
    assert dictionary["application"] == 200
    assert dictionary["banana"] == 50
    assert trie.search("banana") == 50

    # Test max_words cap
    trie2, dict2 = load_dictionary(tsv_file, max_words=2)
    assert len(trie2) == 2
    assert len(dict2) == 2


def test_engine_crud_operations():
    engine = AutocompleteEngine()
    engine.add("algorithm", freq=50)
    engine.add("algebra", freq=30)
    assert len(engine) == 2

    # Suggestion
    res = engine.suggest("alg", k=5)
    assert len(res) == 2
    words = [w for w, _ in res]
    assert words == ["algorithm", "algebra"]

    # Select boosts frequency
    engine.select("algebra", delta=100)
    assert engine.dictionary["algebra"] == 130
    res_boosted = engine.suggest("alg", k=5)
    assert res_boosted[0][0] == "algebra"

    # Remove
    assert engine.remove("algebra") is True
    assert len(engine) == 1
    assert "algebra" not in engine.dictionary
    assert engine.suggest("algebra").suggestions == []
    assert engine.remove("nonexistent") is False


def test_engine_fallback_to_correction():
    engine = AutocompleteEngine()
    engine.add("algorithm", freq=500)
    engine.add("database", freq=400)

    # Prefix with typos: "algoritm" has no prefix matches
    res = engine.suggest("algoritm", k=5, min_threshold=1)
    assert res.fell_back is True
    assert len(res.suggestions) == 0
    assert len(res.corrections) >= 1
    assert res.did_you_mean == "algorithm"
    assert res.corrections[0][0] == "algorithm"
    assert res.corrections[0][1] == 1  # edit distance 1


def test_suggestion_result_structure():
    res = SuggestionResult(
        query="test",
        suggestions=[("test", 10), ("testing", 5)],
        corrections=[("best", 1, 8)],
        fell_back=False,
    )
    assert len(res) == 2
    assert res[0] == ("test", 10)
    assert [w for w, f in res] == ["test", "testing"]
    assert res.did_you_mean == "best"

    d = res.to_dict()
    assert d["query"] == "test"
    assert len(d["suggestions"]) == 2
    assert d["did_you_mean"] == "best"
    assert d["fell_back"] is False


def test_engine_with_real_words_file():
    # Test loading real data/words.txt
    engine = AutocompleteEngine("data/words.txt", max_words=1000)
    assert len(engine) == 1000
    res = engine.suggest("data", k=5)
    assert len(res.suggestions) > 0
    data_words = [w for w, _ in res.suggestions]
    assert any("data" in w for w in data_words)
