"""Tests for embedding utilities."""

import numpy as np
import pytest

from arcana_mcp.embeddings import EMBED_DIM, _cosine_sim, _pack_embedding, _unpack_embedding


def test_pack_unpack_roundtrip():
    original = np.random.randn(EMBED_DIM).astype(np.float32)
    packed = _pack_embedding(original)
    unpacked = _unpack_embedding(packed)
    np.testing.assert_array_almost_equal(original, unpacked)


def test_packed_size():
    emb = np.zeros(EMBED_DIM, dtype=np.float32)
    packed = _pack_embedding(emb)
    assert len(packed) == EMBED_DIM * 4  # float32 = 4 bytes


def test_cosine_sim_identical():
    a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    assert _cosine_sim(a, a) == pytest.approx(1.0)


def test_cosine_sim_orthogonal():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([0.0, 1.0], dtype=np.float32)
    assert _cosine_sim(a, b) == pytest.approx(0.0)


def test_cosine_sim_opposite():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([-1.0, 0.0], dtype=np.float32)
    assert _cosine_sim(a, b) == pytest.approx(-1.0)


def test_cosine_sim_zero_vector():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.zeros(2, dtype=np.float32)
    assert _cosine_sim(a, b) == 0.0
