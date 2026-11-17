"""
Top-K Prefix Ranking Module.

Utilizes a bounded min-heap of size K via Python's heapq to efficiently
extract the most frequent completions for a given prefix in O(P + M log K) time.
"""

from __future__ import annotations
import heapq
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.trie import Trie, TrieNode


class Candidate:
    """
    Candidate completion entry for min-heap management.

    Designed for a min-heap where the element considered 'smallest'
    is the lowest priority (lowest frequency, or lexicographically
    larger for tie-breaking) so it is popped first when heap size exceeds K.
    """

    __slots__ = ("word", "freq")

    def __init__(self, word: str, freq: int) -> None:
        self.word: str = word
        self.freq: int = freq

    def __lt__(self, other: Candidate) -> bool:
        # Min-heap ordering: 'smaller' means worse ranking (evicted first).
        if self.freq != other.freq:
            return self.freq < other.freq
        # For equal frequencies, lexicographically larger word is worse rank.
        return self.word > other.word

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Candidate):
            return False
        return self.freq == other.freq and self.word == other.word

    def __repr__(self) -> str:
        return f"Candidate({self.word!r}, {self.freq})"


def top_k(trie: Trie, prefix: str, k: int = 5) -> list[tuple[str, int]]:
    """
    Retrieve the top-K completions for a prefix ranked by frequency desc, ties alphabetical.

    Uses a min-heap of size at most K during DFS traversal over the subtree, with
    branch-and-bound pruning based on node.max_freq. If a child node's maximum possible
    frequency is less than the worst candidate in the full heap (heap[0]), that entire
    branch is pruned from exploration.

    Time Complexity:
        O(P + M_eff log K), where:
        - P is length of prefix to find the subtree root.
        - M_eff is the effective number of visited nodes after pruning (M_eff << M).
        - K is the requested number of top results.
        Sorting the final K results takes O(K log K).

    Space Complexity:
        O(H + K) auxiliary space, where:
        - H is maximum depth of the trie subtree (DFS traversal).
        - K is the bounded heap size.

    Args:
        trie: The Trie containing the vocabulary.
        prefix: Prefix string to search.
        k: Maximum number of completions to return (k >= 1).

    Returns:
        List of (word, frequency) tuples, ordered by:
        1. Frequency descending.
        2. Word alphabetical ascending on frequency tie.
    """
    if k <= 0:
        return []

    node = trie.get_node(prefix)
    if node is None:
        return []

    heap: list[Candidate] = []

    # DFS stack holds (current_node, current_prefix)
    stack: list[tuple[TrieNode, str]] = [(node, prefix)]

    while stack:
        curr, curr_prefix = stack.pop()

        # Branch-and-bound pruning: if heap is full and max possible frequency
        # in this subtree cannot enter top-k, prune exploration immediately.
        if len(heap) == k and curr.max_freq < heap[0].freq:
            continue

        if curr.is_end:
            candidate = Candidate(curr_prefix, curr.freq)
            if len(heap) < k:
                heapq.heappush(heap, candidate)
            elif heap[0] < candidate:
                heapq.heappushpop(heap, candidate)

        # Sort children by max_freq ascending so popping from stack visits
        # the highest max_freq branches first, filling the heap rapidly.
        sorted_children = sorted(
            curr.children.items(),
            key=lambda item: item[1].max_freq,
        )
        for char, child in sorted_children:
            if len(heap) < k or child.max_freq >= heap[0].freq:
                stack.append((child, curr_prefix + char))

    # Sort final candidates: frequency descending (-freq), word alphabetical (word)
    heap.sort(key=lambda c: (-c.freq, c.word))
    return [(c.word, c.freq) for c in heap]


def select_word(trie: Trie, word: str, delta: int = 1) -> int:
    """
    Increment the frequency of a word in the Trie (e.g., when selected by user).

    If the word exists, its frequency is increased by `delta`.
    If the word does not exist, it is inserted with frequency `delta`.
    Updates subtree max_freq along the prefix path.

    Time Complexity: O(L) where L is the length of the word.
    Space Complexity: O(1) if word exists, O(L) if newly inserted.

    Args:
        trie: The Trie instance.
        word: The word selected.
        delta: Amount to increment frequency by (default 1).

    Returns:
        The new frequency of the word.
    """
    node = trie.get_node(word)
    if node is not None and node.is_end:
        new_freq = node.freq + delta
        trie.insert(word, freq=new_freq)
        return new_freq

    # Not found or not an end-of-word node
    trie.insert(word, freq=delta)
    return delta

