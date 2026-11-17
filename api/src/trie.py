"""
Trie (Prefix Tree) Data Structure Implementation.

Provides an efficient retrieval data structure for storing strings,
supporting fast prefix lookups, insertions, deletions with node pruning,
and subtree traversal.
"""

from __future__ import annotations
from typing import Iterator, Optional


class TrieNode:
    """
    A single node within the Trie.

    Attributes:
        children: Mapping from character (str) to child TrieNode.
        is_end: True if this node marks the end of a valid stored word.
        freq: Frequency or popularity count associated with the word.
        max_freq: Maximum frequency among all valid words in this node's subtree.
    """

    __slots__ = ("children", "is_end", "freq", "max_freq")

    def __init__(self, is_end: bool = False, freq: int = 0) -> None:
        self.children: dict[str, TrieNode] = {}
        self.is_end: bool = is_end
        self.freq: int = freq
        self.max_freq: int = freq

    def __repr__(self) -> str:
        return f"TrieNode(is_end={self.is_end}, freq={self.freq}, max_freq={self.max_freq}, children_count={len(self.children)})"


class Trie:
    """
    Prefix Tree (Trie) for dictionary string storage and prefix search.

    Supports insertion, search, prefix node retrieval, subtree traversal,
    and memory-pruning deletions.
    """

    def __init__(self) -> None:
        self.root: TrieNode = TrieNode()
        self._size: int = 0

    def __len__(self) -> int:
        """
        Return the total number of distinct words stored in the Trie.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        return self._size

    def insert(self, word: str, freq: int = 1) -> None:
        """
        Insert a word with its frequency into the Trie.

        If the word already exists, its frequency is updated to the new frequency.

        Time Complexity: O(L) where L is the length of the word.
        Space Complexity: O(L) auxiliary space in the worst case (if all nodes are newly created).

        Args:
            word: The string to insert.
            freq: Associated frequency count (must be >= 1).
        """
        current = self.root
        current.max_freq = max(current.max_freq, freq)
        for char in word:
            if char not in current.children:
                current.children[char] = TrieNode()
            current = current.children[char]
            current.max_freq = max(current.max_freq, freq)

        if not current.is_end:
            self._size += 1
            current.is_end = True

        current.freq = freq

    def search(self, word: str) -> Optional[int]:
        """
        Search for a word in the Trie.

        Time Complexity: O(L) where L is the length of the word.
        Space Complexity: O(1).

        Args:
            word: The string to search for.

        Returns:
            The integer frequency if the word is found and is marked as an end node,
            or None if the word is not in the Trie.
        """
        node = self.get_node(word)
        if node is not None and node.is_end:
            return node.freq
        return None

    def get_node(self, prefix: str) -> Optional[TrieNode]:
        """
        Traverse the Trie along the prefix characters and return the destination node.

        Time Complexity: O(P) where P is the length of the prefix.
        Space Complexity: O(1).

        Args:
            prefix: The prefix string to traverse.

        Returns:
            The TrieNode at the end of the prefix, or None if prefix not found.
        """
        current = self.root
        for char in prefix:
            if char not in current.children:
                return None
            current = current.children[char]
        return current

    def delete(self, word: str) -> bool:
        """
        Delete a word from the Trie, pruning unreachable empty nodes.

        Recursively unmarks is_end and removes child nodes that have no
        remaining children and are not the end of another word.

        Time Complexity: O(L) where L is the length of the word.
        Space Complexity: O(L) recursion stack space.

        Args:
            word: The string to delete.

        Returns:
            True if the word was found and deleted; False otherwise.
        """
        deleted = False

        def _delete_helper(node: TrieNode, word: str, index: int) -> bool:
            nonlocal deleted
            if index == len(word):
                if not node.is_end:
                    return False
                node.is_end = False
                node.freq = 0
                deleted = True
                self._size -= 1
                # If this node has no children, it can be pruned by parent
                return len(node.children) == 0

            char = word[index]
            if char not in node.children:
                return False

            should_prune_child = _delete_helper(node.children[char], word, index + 1)

            if should_prune_child:
                del node.children[char]

            # Recompute max_freq for this node
            child_max = (
                max((c.max_freq for c in node.children.values()), default=0)
                if node.children
                else 0
            )
            node.max_freq = max(node.freq, child_max)
            return len(node.children) == 0 and not node.is_end

            return False

        _delete_helper(self.root, word, 0)
        return deleted

    def iter_words(
        self, node: Optional[TrieNode], prefix: str = ""
    ) -> Iterator[tuple[str, int]]:
        """
        Depth-First Search (DFS) generator yielding all (word, freq) pairs in the subtree.

        Time Complexity: O(V) where V is the number of nodes in the subtree.
        Space Complexity: O(H) where H is the maximum depth (length of the longest word).

        Args:
            node: The starting TrieNode (typically returned by get_node).
            prefix: The prefix string accumulated down to `node`.

        Yields:
            Tuples of (completed_word, frequency).
        """
        if node is None:
            return

        # Stack contains (current_node, current_prefix_str)
        # Using an explicit DFS stack to ensure fast execution without deep recursion limits
        stack: list[tuple[TrieNode, str]] = [(node, prefix)]

        while stack:
            curr, curr_prefix = stack.pop()
            if curr.is_end:
                yield (curr_prefix, curr.freq)

            # Traverse children in reverse sorted order so pop() visits in alphabetical order
            for char in sorted(curr.children.keys(), reverse=True):
                stack.append((curr.children[char], curr_prefix + char))
