"""Local embedding helpers using fastembed (ONNX-based, no PyTorch)."""

import logging
import os
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding

logger = logging.getLogger("arcana-mcp")

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384

_model: TextEmbedding | None = None


def _get_model() -> TextEmbedding:
    global _model
    if _model is None:
        cache = os.environ.get("ARCANA_MODEL_CACHE", str(Path.home() / ".arcana" / "models"))
        _model = TextEmbedding(
            model_name=EMBED_MODEL,
            cache_dir=cache,
            lazy_load=True,
        )
    return _model


def _embed_texts(texts: list[str]) -> list[np.ndarray]:
    """Batch embed texts locally via fastembed."""
    if not texts:
        return []
    model = _get_model()
    return [np.array(e, dtype=np.float32) for e in model.embed(texts)]


def _pack_embedding(emb: np.ndarray) -> bytes:
    return emb.tobytes()


def _unpack_embedding(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    return float(dot / norm) if norm > 0 else 0.0
