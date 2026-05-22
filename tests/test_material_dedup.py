"""Tests for material library deduplication utilities."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add the material-library-extraction source directory to the path
_ML_SRC = Path(__file__).resolve().parent.parent / "src" / "material-library-extraction"
sys.path.insert(0, str(_ML_SRC))

from extract_material_library import _union_find_clusters  # noqa: E402


class TestUnionFindClusters:
    """Tests for _union_find_clusters."""

    def test_no_pairs_returns_singletons(self):
        clusters = _union_find_clusters(3, [])
        flat = sorted(sorted(c) for c in clusters)
        assert flat == [[0], [1], [2]]

    def test_single_pair_merged(self):
        clusters = _union_find_clusters(3, [(0, 1)])
        flat = sorted(sorted(c) for c in clusters)
        assert [2] in flat
        merged = next(c for c in flat if len(c) == 2)
        assert sorted(merged) == [0, 1]

    def test_transitivity_abc(self):
        """A-B and B-C above threshold → A, B, C all in one group."""
        clusters = _union_find_clusters(3, [(0, 1), (1, 2)])
        assert len(clusters) == 1
        assert sorted(clusters[0]) == [0, 1, 2]

    def test_two_independent_pairs(self):
        clusters = _union_find_clusters(4, [(0, 1), (2, 3)])
        flat = sorted(sorted(c) for c in clusters)
        assert flat == [[0, 1], [2, 3]]

    def test_all_connected(self):
        clusters = _union_find_clusters(4, [(0, 1), (1, 2), (2, 3)])
        assert len(clusters) == 1
        assert sorted(clusters[0]) == [0, 1, 2, 3]
