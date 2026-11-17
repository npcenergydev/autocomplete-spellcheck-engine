"""
Unit tests for src/edit_distance.py.
"""

import pytest
from src.edit_distance import (
    levenshtein_distance,
    levenshtein_two_rows,
    levenshtein_matrix,
    print_dp_table,
)


@pytest.mark.parametrize(
    "s1, s2, expected",
    [
        ("kitten", "sitting", 3),
        ("algoritm", "algorithm", 1),
        ("rosettacode", "raisethysword", 8),
        ("", "", 0),
        ("", "abc", 3),
        ("hello", "", 5),
        ("same", "same", 0),
        ("sunday", "saturday", 3),
        ("distance", "editing", 5),
    ],
)
def test_levenshtein_distance_cases(s1, s2, expected):
    dist_full = levenshtein_distance(s1, s2)
    dist_two = levenshtein_two_rows(s1, s2)
    assert dist_full == expected
    assert dist_two == expected


def test_levenshtein_matrix_dimensions():
    s1, s2 = "abc", "defg"
    matrix = levenshtein_matrix(s1, s2)
    assert len(matrix) == 4  # len(s1) + 1
    assert len(matrix[0]) == 5  # len(s2) + 1
    assert matrix[0][0] == 0
    assert matrix[3][4] == 4


def test_print_dp_table_output():
    table_str = print_dp_table("cat", "hat", print_output=False)
    assert "#" in table_str
    assert "c" in table_str
    assert "h" in table_str
    assert "1" in table_str
