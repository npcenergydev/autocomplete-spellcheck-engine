"""
Spell Correction Module using Trie-Based Levenshtein Backtracking Search.

Performs pruned state-space search over the Trie by propagating dynamic
programming rows down trie branches, pruning entire subtrees when min(row) > max_dist.
Includes a brute-force validator for testing and benchmarking.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Iterable, Optional
from src.edit_distance import levenshtein_two_rows

if TYPE_CHECKING:
    from src.trie import Trie, TrieNode


def correct_trie(
    trie: Trie,
    target: str,
    max_dist: int = 2,
    limit: Optional[int] = None,
) -> list[tuple[str, int, int]]:
    """
    Find all words in the Trie within `max_dist` edit distance of `target`.

    Traverses the Trie in DFS order carrying a single DP row per node.
    Prunes the exploration branch whenever min(row) > max_dist, as no descendant
    in that subtree can ever achieve an edit distance <= max_dist.

    Time Complexity:
        Significantly faster than O(N * |target|) brute force.
        Empirically explores O(K^(max_dist)) nodes instead of full dictionary N.
    Space Complexity:
        O(H * |target|) recursion stack, where H is the max tree depth.

    Args:
        trie: The Trie index.
        target: The potentially misspelled query string.
        max_dist: Maximum allowable edit distance (typically 1 or 2).
        limit: Optional maximum number of suggestions to return.

    Returns:
        List of tuples: (word, distance, frequency), ranked by:
        1. Distance ascending (closest matches first).
        2. Frequency descending (-frequency, most popular first).
        3. Word alphabetical ascending for deterministic tie-breaking.
    """
    target = target.lower()
    target_len = len(target)
    results: list[tuple[str, int, int]] = []

    # Initial DP row corresponding to empty prefix ""
    # row[j] is distance between "" and target[:j], which is j
    initial_row = list(range(target_len + 1))

    # Check if empty string itself is in trie
    if trie.root.is_end and target_len <= max_dist:
        results.append(("", target_len, trie.root.freq))

    def _dfs(node: TrieNode, char: str, prev_row: list[int], current_word: str) -> None:
        # Build the current DP row for this node
        # current_row[0] is distance between current_word and ""
        current_row = [prev_row[0] + 1]

        # Populate the rest of the row against target
        for col in range(1, target_len + 1):
            insert_or_del = min(
                current_row[col - 1] + 1,  # Insertion
                prev_row[col] + 1,          # Deletion
            )
            cost = 0 if target[col - 1] == char else 1
            replace_or_match = prev_row[col - 1] + cost
            current_row.append(min(insert_or_del, replace_or_match))

        # Check if the word at this node qualifies
        dist = current_row[-1]
        if node.is_end and dist <= max_dist:
            results.append((current_word, dist, node.freq))

        # Pruning condition: if every value in current_row exceeds max_dist,
        # no descendant can ever reach an edit distance <= max_dist.
        if min(current_row) > max_dist:
            return

        # Recurse into children
        for next_char, child_node in node.children.items():
            _dfs(child_node, next_char, current_row, current_word + next_char)

    for char, child in trie.root.children.items():
        _dfs(child, char, initial_row, char)

    # Rank by: (distance ascending, frequency descending, word ascending)
    results.sort(key=lambda item: (item[1], -item[2], item[0]))

    if limit is not None and limit > 0:
        return results[:limit]
    return results


def correct_brute_force(
    dictionary: Iterable[tuple[str, int]],
    target: str,
    max_dist: int = 2,
    limit: Optional[int] = None,
) -> list[tuple[str, int, int]]:
    """
    Linear scan brute-force spell correction across all dictionary entries.

    Used for validating correctness of the trie-based search and for benchmarking.

    Time Complexity: O(N * |target| * L_avg) where N is vocabulary size.
    Space Complexity: O(1) auxiliary space beyond the output list.

    Args:
        dictionary: Iterable of (word, freq) entries.
        target: Target query string.
        max_dist: Maximum allowable edit distance.
        limit: Optional maximum number of suggestions.

    Returns:
        List of tuples: (word, distance, frequency) sorted by (dist, -freq, word).
    """
    target = target.lower()
    results: list[tuple[str, int, int]] = []

    for word, freq in dictionary:
        # Quick length difference filter (optimization for brute force)
        if abs(len(word) - len(target)) > max_dist:
            continue

        dist = levenshtein_two_rows(target, word)
        if dist <= max_dist:
            results.append((word, dist, freq))

    # Rank by: (distance ascending, frequency descending, word ascending)
    results.sort(key=lambda item: (item[1], -item[2], item[0]))

    if limit is not None and limit > 0:
        return results[:limit]
    return results
