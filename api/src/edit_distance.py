"""
Levenshtein Edit Distance Algorithms.

Implements classic 2D Dynamic Programming, space-optimized two-row DP,
and visual DP table formatting for educational reports and verification.
"""

from __future__ import annotations


def levenshtein_matrix(s1: str, s2: str) -> list[list[int]]:
    """
    Compute the complete (m+1) x (n+1) Levenshtein DP table.

    Operations supported:
    - Insertion (cost 1)
    - Deletion (cost 1)
    - Substitution (cost 1 if mismatched, 0 if matched)

    Recurrence:
        D[0][j] = j
        D[i][0] = i
        D[i][j] = min(
            D[i-1][j] + 1,                     # Deletion
            D[i][j-1] + 1,                     # Insertion
            D[i-1][j-1] + (0 if s1[i-1] == s2[j-1] else 1) # Substitution / Match
        )

    Time Complexity: O(m * n) where m = len(s1), n = len(s2).
    Space Complexity: O(m * n) to retain the entire matrix.

    Args:
        s1: Source string (rows).
        s2: Target string (columns).

    Returns:
        The (len(s1) + 1) x (len(s2) + 1) dynamic programming matrix.
    """
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        c1 = s1[i - 1]
        for j in range(1, n + 1):
            c2 = s2[j - 1]
            cost = 0 if c1 == c2 else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,       # Deletion
                dp[i][j - 1] + 1,       # Insertion
                dp[i - 1][j - 1] + cost # Match / Substitution
            )

    return dp


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Compute the Levenshtein distance using standard full-table DP.

    Time Complexity: O(m * n)
    Space Complexity: O(m * n)

    Args:
        s1: Source string.
        s2: Target string.

    Returns:
        The minimum edit distance between s1 and s2.
    """
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)

    dp = levenshtein_matrix(s1, s2)
    return dp[len(s1)][len(s2)]


def levenshtein_two_rows(s1: str, s2: str) -> int:
    """
    Space-optimized Levenshtein distance using two alternating rows.

    Maintains only the previous and current rows during iteration,
    ensuring O(min(m, n)) auxiliary space.

    Time Complexity: O(m * n)
    Space Complexity: O(min(m, n))

    Args:
        s1: Source string.
        s2: Target string.

    Returns:
        The minimum edit distance between s1 and s2.
    """
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)

    # Ensure s2 is the shorter string for minimum auxiliary space
    if len(s1) < len(s2):
        s1, s2 = s2, s1

    n = len(s2)
    prev = list(range(n + 1))
    curr = [0] * (n + 1)

    for i, c1 in enumerate(s1, start=1):
        curr[0] = i
        for j, c2 in enumerate(s2, start=1):
            cost = 0 if c1 == c2 else 1
            curr[j] = min(
                prev[j] + 1,       # Deletion
                curr[j - 1] + 1,   # Insertion
                prev[j - 1] + cost # Match / Substitution
            )
        prev, curr = curr, prev

    return prev[n]


def print_dp_table(s1: str, s2: str, print_output: bool = True) -> str:
    """
    Generate and optionally display a formatted Levenshtein DP matrix.

    Useful for algorithm visualization, academic reports, and debugging.

    Args:
        s1: Source string (vertical / row labels).
        s2: Target string (horizontal / column labels).
        print_output: If True, prints the rendered table to stdout.

    Returns:
        Formatted multi-line string representing the DP matrix.
    """
    dp = levenshtein_matrix(s1, s2)
    col_labels = ["#"] + list(s2)
    row_labels = ["#"] + list(s1)

    # Column width calculation for uniform padding
    max_val = max(max(row) for row in dp)
    col_width = max(len(str(max_val)), max(len(c) for c in col_labels)) + 2

    lines: list[str] = []
    header = " " * (col_width + 2) + "".join(f"{c:>{col_width}}" for c in col_labels)
    lines.append(header)
    lines.append(" " * (col_width + 2) + "-" * (col_width * len(col_labels)))

    for i, r_label in enumerate(row_labels):
        row_str = f"{r_label:>{col_width}} |" + "".join(
            f"{dp[i][j]:>{col_width}}" for j in range(len(col_labels))
        )
        lines.append(row_str)

    result = "\n".join(lines)
    if print_output:
        print(result)
    return result
