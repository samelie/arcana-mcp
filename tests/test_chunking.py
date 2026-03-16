"""Tests for text chunking utilities."""

from arcana_mcp.chunking import MAX_CHUNK, _auto_uri, _chunk_markdown, _chunk_plaintext, _chunk_text


def test_markdown_splits_on_headers():
    text = "# Header 1\nContent 1\n\n## Header 2\nContent 2"
    chunks = _chunk_markdown(text)
    assert len(chunks) >= 2
    assert "Header 1" in chunks[0]
    assert "Header 2" in chunks[1]


def test_plaintext_splits_on_paragraphs():
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    chunks = _chunk_plaintext(text)
    assert len(chunks) >= 1
    assert "Paragraph one" in chunks[0]


def test_empty_input_returns_empty():
    assert _chunk_markdown("") == []
    assert _chunk_plaintext("") == []
    assert _chunk_text("") == []


def test_whitespace_only_returns_empty():
    assert _chunk_markdown("   \n\n  ") == []
    assert _chunk_plaintext("   \n\n  ") == []


def test_oversized_chunk_gets_split():
    # Use paragraphs so plaintext chunker can find split points
    text = "# Big Section\n" + ("\n\n".join(["x" * 500] * 20))
    chunks = _chunk_markdown(text)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= MAX_CHUNK + 600  # allow slack for header + split boundaries


def test_chunk_text_dispatches_by_extension():
    md_text = "# Heading\nBody"
    assert _chunk_text(md_text, "test.md") == _chunk_markdown(md_text)
    assert _chunk_text(md_text, "test.txt") == _chunk_plaintext(md_text)


def test_auto_uri():
    assert _auto_uri("/some/path/file.md") == "arcana://file.md"
    assert _auto_uri("relative/overview.py") == "arcana://overview.py"
