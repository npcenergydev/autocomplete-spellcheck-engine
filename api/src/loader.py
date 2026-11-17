"""
Dataset Loader Module.

Parses frequency-weighted wordlist datasets into Trie and dictionary structures.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional
from src.trie import Trie


def load_dictionary(
    filepath: str | Path = "data/words.txt",
    max_words: Optional[int] = None,
) -> tuple[Trie, dict[str, int]]:
    """
    Load a tab-delimited wordlist file into a Trie and a plain Python dict.

    File format: Each line contains 'word<TAB>frequency'.

    Args:
        filepath: Path to the dataset TSV file.
        max_words: Optional upper bound on number of lines to load.

    Returns:
        A tuple of (trie, word_to_freq_dict).

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If line format is invalid.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Dictionary file not found at {path.resolve()}")

    trie = Trie()
    dictionary: dict[str, int] = {}

    count = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) != 2:
                # Fallback to space split if tab is not found
                parts = line.rsplit(maxsplit=1)
                if len(parts) != 2:
                    continue

            word = parts[0].strip().lower()
            try:
                freq = int(parts[1].strip())
            except ValueError:
                freq = 1

            trie.insert(word, freq)
            dictionary[word] = freq
            count += 1

            if max_words is not None and count >= max_words:
                break

    return trie, dictionary
