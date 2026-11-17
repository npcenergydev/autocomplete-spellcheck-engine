"""
Search Autocomplete and Spell Correction Engine Facade.

Integrates Trie indexing, Top-K bounded min-heap ranking, Levenshtein DP,
and state-space pruned spell correction into a unified API.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional, Any

from src.trie import Trie
from src.topk import top_k, select_word
from src.corrector import correct_trie
from src.loader import load_dictionary


@dataclass
class SuggestionResult:
    """
    Structured outcome of an autocomplete query.

    Supports direct iteration, indexing, and dictionary serialization
    while providing access to both prefix matches and spell-check fallbacks.
    """

    query: str
    suggestions: list[tuple[str, int]] = field(default_factory=list)
    corrections: list[tuple[str, int, int]] = field(default_factory=list)
    fell_back: bool = False

    def __iter__(self) -> Iterator[tuple[str, int]]:
        return iter(self.suggestions)

    def __len__(self) -> int:
        return len(self.suggestions)

    def __getitem__(self, index: int) -> tuple[str, int]:
        return self.suggestions[index]

    @property
    def did_you_mean(self) -> Optional[str]:
        """Return the best correction candidate, if available."""
        if self.corrections:
            return self.corrections[0][0]
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to JSON-friendly dictionary."""
        return {
            "query": self.query,
            "suggestions": [{"word": w, "freq": f} for w, f in self.suggestions],
            "corrections": [
                {"word": w, "dist": d, "freq": f} for w, d, f in self.corrections
            ],
            "did_you_mean": self.did_you_mean,
            "fell_back": self.fell_back,
        }


class AutocompleteEngine:
    """
    Facade class managing prefix autocomplete, Top-K ranking, and spell correction.
    """

    def __init__(
        self,
        dataset_path: Optional[str | Path] = None,
        max_words: Optional[int] = None,
    ) -> None:
        self.trie: Trie = Trie()
        self.dictionary: dict[str, int] = {}

        if dataset_path is not None:
            self.load(dataset_path, max_words=max_words)

    def load(
        self,
        dataset_path: str | Path = "data/words.txt",
        max_words: Optional[int] = None,
    ) -> None:
        """
        Load vocabulary dataset into the engine.

        Args:
            dataset_path: Path to dataset TSV.
            max_words: Optional ceiling on entries to ingest.
        """
        self.trie, self.dictionary = load_dictionary(dataset_path, max_words=max_words)

    def __len__(self) -> int:
        """Return the number of unique words loaded."""
        return len(self.trie)

    def suggest(
        self,
        prefix: str,
        k: int = 5,
        min_threshold: int = 1,
        max_dist: int = 2,
    ) -> SuggestionResult:
        """
        Produce top-K autocomplete suggestions for a given prefix.

        If fewer than `min_threshold` suggestions are found in the subtree,
        automatically triggers spell correction to suggest alternatives.

        Time Complexity:
            O(P + M log K) for prefix matching.
            If fallback triggers: bounded trie exploration within max_dist.

        Args:
            prefix: The prefix string typed so far.
            k: Maximum number of completions to return.
            min_threshold: Minimum completions before triggering spell-correction fallback.
            max_dist: Maximum edit distance for fallback corrections.

        Returns:
            SuggestionResult containing completions and any 'Did you mean' corrections.
        """
        cleaned = prefix.strip().lower()
        if not cleaned:
            return SuggestionResult(query=prefix)

        # 1. Retrieve top-k prefix completions
        completions = top_k(self.trie, cleaned, k=k)

        # 2. Check if fallback to spell correction is needed
        corrections: list[tuple[str, int, int]] = []
        fell_back = False

        if len(completions) < min_threshold:
            fell_back = True
            corrections = self.correct(cleaned, max_dist=max_dist, limit=k)

        return SuggestionResult(
            query=prefix,
            suggestions=completions,
            corrections=corrections,
            fell_back=fell_back,
        )

    def correct(
        self,
        word: str,
        max_dist: int = 2,
        limit: int = 5,
    ) -> list[tuple[str, int, int]]:
        """
        Find closest dictionary words within `max_dist` edit distance.

        Args:
            word: Target string to correct.
            max_dist: Maximum allowable edit distance (1 or 2).
            limit: Maximum candidate corrections to return.

        Returns:
            List of (word, distance, frequency) sorted by (dist, -freq, word).
        """
        cleaned = word.strip().lower()
        if not cleaned:
            return []
        return correct_trie(self.trie, cleaned, max_dist=max_dist, limit=limit)

    def select(self, word: str, delta: int = 1) -> int:
        """
        Register user selection of a word, boosting its frequency.

        Args:
            word: The selected word.
            delta: Increment amount (default 1).

        Returns:
            The new frequency of the word.
        """
        cleaned = word.strip().lower()
        new_freq = select_word(self.trie, cleaned, delta=delta)
        self.dictionary[cleaned] = new_freq
        return new_freq

    def add(self, word: str, freq: int = 1) -> None:
        """
        Add a new word to the engine's index.

        Args:
            word: The word to insert.
            freq: Initial frequency count.
        """
        cleaned = word.strip().lower()
        self.trie.insert(cleaned, freq=freq)
        self.dictionary[cleaned] = freq

    def remove(self, word: str) -> bool:
        """
        Remove a word from the engine's index.

        Args:
            word: The word to delete.

        Returns:
            True if word was found and deleted, False otherwise.
        """
        cleaned = word.strip().lower()
        deleted = self.trie.delete(cleaned)
        if deleted and cleaned in self.dictionary:
            del self.dictionary[cleaned]
        return deleted
