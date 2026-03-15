"""Text chunking utilities."""

import re
from pathlib import Path

MAX_CHUNK = 2000  # chars
TEXT_EXTS = {".md", ".txt", ".py", ".ts", ".js", ".json", ".yaml", ".yml", ".toml", ".rst", ".sh", ".css", ".html", ".vue", ".jsx", ".tsx", ".sql", ".go", ".rs", ".c", ".h", ".cpp", ".hpp"}


def _chunk_markdown(text: str) -> list[str]:
    sections = re.split(r'(?m)^(#{1,4}\s)', text)
    chunks = []
    current = ""
    for i, part in enumerate(sections):
        if re.match(r'^#{1,4}\s', part):
            if current.strip():
                chunks.extend(_split_large(current))
            current = part
        else:
            current += part
    if current.strip():
        chunks.extend(_split_large(current))
    return chunks if chunks else [text[:MAX_CHUNK]] if text.strip() else []


def _chunk_plaintext(text: str) -> list[str]:
    paragraphs = re.split(r'\n\n+', text)
    chunks = []
    current = ""
    for p in paragraphs:
        if len(current) + len(p) > MAX_CHUNK and current:
            chunks.append(current.strip())
            current = p
        else:
            current = current + "\n\n" + p if current else p
    if current.strip():
        chunks.append(current.strip())
    return chunks if chunks else [text[:MAX_CHUNK]] if text.strip() else []


def _split_large(text: str) -> list[str]:
    if len(text) <= MAX_CHUNK:
        return [text.strip()] if text.strip() else []
    return _chunk_plaintext(text)


def _chunk_text(text: str, path: str = "") -> list[str]:
    if path.endswith(".md") or path.endswith(".rst"):
        return _chunk_markdown(text)
    return _chunk_plaintext(text)


def _auto_uri(path: str) -> str:
    return "arcana://" + Path(path).name
