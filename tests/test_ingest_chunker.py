"""Unit tests for the medical-knowledge ingest chunker.

Focuses on the fact-safe overlap behavior added to keep a clinical fact that
straddles a chunk boundary whole in at least one chunk (what retrieval ranks on).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("pypdf")

_TOOL_PATH = Path(__file__).resolve().parents[1] / "tools" / "ingest_medical_knowledge.py"
_spec = importlib.util.spec_from_file_location("ingest_medical_knowledge", _TOOL_PATH)
ingest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ingest)  # type: ignore[union-attr]


def _pages(paragraphs_per_page):
    """Build (page_number, page_text) tuples from lists of paragraphs."""
    return [
        (i + 1, "\n\n".join(paras))
        for i, paras in enumerate(paragraphs_per_page)
    ]


def test_no_overlap_matches_prior_behavior():
    paras = [f"Paragraph number {i} " + "x" * 300 for i in range(6)]
    pages = _pages([paras])
    chunks = list(ingest.iter_chunks(pages, chunk_chars=1000, chunk_overlap=0))
    assert len(chunks) >= 2
    # Chunk indexes are sequential and pages are populated.
    assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))
    for c in chunks:
        assert c["page_start"] == 1 and c["page_end"] == 1
        assert len(c["chunk_text"]) <= 1000 + 320  # a single trailing paragraph may spill slightly


def test_overlap_carries_trailing_fact_into_next_chunk():
    # A distinctive "fact" paragraph sits right before a boundary; with overlap it
    # should appear in two consecutive chunks.
    fact = "CRITICAL DOSE potassium 20-40 mEq per liter threshold 3.3"
    paras = ["a" * 400, "b" * 400, fact, "c" * 400, "d" * 400, "e" * 400]
    pages = _pages([paras])
    no_overlap = list(ingest.iter_chunks(pages, chunk_chars=900, chunk_overlap=0))
    with_overlap = list(ingest.iter_chunks(pages, chunk_chars=900, chunk_overlap=120))

    def appearances(chunks):
        return sum(1 for c in chunks if fact in c["chunk_text"])

    assert appearances(no_overlap) == 1
    assert appearances(with_overlap) >= 2  # the fact is duplicated across the boundary


def test_overlap_does_not_stall_on_large_paragraph():
    # A single paragraph larger than the budget must still start a fresh chunk
    # rather than looping forever because the overlap keeps overflowing.
    big = "z" * 2000
    paras = ["a" * 400, "b" * 400, big, "c" * 400]
    pages = _pages([paras])
    chunks = list(ingest.iter_chunks(pages, chunk_chars=900, chunk_overlap=300))
    assert any(big in c["chunk_text"] for c in chunks)
    # Sequential, terminates, and produced a bounded number of chunks.
    assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))
    assert len(chunks) <= 6


def test_page_range_tracks_multi_page_chunks():
    pages = _pages([["p1 " + "x" * 300], ["p2 " + "y" * 300], ["p3 " + "z" * 300]])
    chunks = list(ingest.iter_chunks(pages, chunk_chars=5000, chunk_overlap=0))
    assert len(chunks) == 1
    assert chunks[0]["page_start"] == 1
    assert chunks[0]["page_end"] == 3
