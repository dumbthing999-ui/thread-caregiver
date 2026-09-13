"""Spike A: Exact Provenance and Text Anchoring.

Evaluates whether every emitted nonclinical appointment field resolves to an
exact, verifiable, immutable text span in source documents.

Requirements Traced:
  - FR-01: Document ingest with exact quotation and character offsets.
  - FR-02: Strict provenance binding (every field must point to valid source span).
  - INV-01: Textual origin verification (citations establish provenance, not clinical truth).
  - INV-09: Exact quotation preservation with zero hallucinated offsets.
"""

from __future__ import annotations

import dataclasses
import hashlib
import pathlib
import unittest
from typing import Optional


class AnchorError(Exception):
    """Base error for source anchor resolution failures."""


class UnsupportedDocumentFormatError(AnchorError):
    """Raised when document is binary, scanned, or non-decodable."""


class SpanNotFoundError(AnchorError):
    """Raised when the quoted text does not exist in the source document."""


class AmbiguousSpanError(AnchorError):
    """Raised when quoted text appears multiple times without sufficient context."""


class ProvenanceMismatchError(AnchorError):
    """Raised when slice at [start_char:end_char] does not match the quote."""


@dataclasses.dataclass(frozen=True)
class SourceDocument:
    doc_id: str
    filename: str
    raw_content: str
    sha256_hash: str
    total_chars: int
    total_lines: int

    @classmethod
    def from_file(cls, doc_id: str, file_path: pathlib.Path) -> SourceDocument:
        # Check for binary / corrupted content first
        raw_bytes = file_path.read_bytes()
        # Binary magic check: check for null bytes or known non-text headers
        if b"\x00" in raw_bytes[:1024] or raw_bytes.startswith(b"\x89PNG") or raw_bytes.startswith(b"%PDF-corrupt"):
            raise UnsupportedDocumentFormatError(
                f"Document '{file_path.name}' contains binary/unsupported data; only plain UTF-8 text is supported."
            )
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UnsupportedDocumentFormatError(
                f"Document '{file_path.name}' cannot be decoded as UTF-8: {exc}"
            ) from exc

        hasher = hashlib.sha256()
        hasher.update(raw_bytes)
        lines = text.splitlines(keepends=True)

        return cls(
            doc_id=doc_id,
            filename=file_path.name,
            raw_content=text,
            sha256_hash=hasher.hexdigest(),
            total_chars=len(text),
            total_lines=len(lines),
        )


@dataclasses.dataclass(frozen=True)
class SourceSpan:
    span_id: str
    doc_id: str
    start_char: int
    end_char: int
    line_start: int
    col_start: int
    line_end: int
    col_end: int
    exact_quote: str
    page_index: int = 0

    def verify_against(self, doc: SourceDocument) -> bool:
        """Verify that the source document slice exactly matches the quote."""
        if self.doc_id != doc.doc_id:
            return False
        if self.start_char < 0 or self.end_char > doc.total_chars or self.start_char >= self.end_char:
            return False
        extracted = doc.raw_content[self.start_char:self.end_char]
        return extracted == self.exact_quote


class AnchorResolver:
    """Deterministic anchor resolver that maps exact quotations to character offsets."""

    @staticmethod
    def _compute_line_col(text: str, offset: int) -> tuple[int, int]:
        """Convert a character offset into 1-based (line_number, column_number)."""
        lines = text[:offset].splitlines(keepends=True)
        if not lines:
            return 1, 1
        line_num = len(lines)
        col_num = len(lines[-1]) + 1 if text[:offset].endswith(("\n", "\r")) else len(lines[-1]) + 1
        # If previous line ended with newline, we are at line_num + 1, col 1
        if text[:offset].endswith(("\n", "\r")):
            return line_num + 1, 1
        return line_num, len(lines[-1]) + 1

    @classmethod
    def resolve_anchor(
        cls,
        doc: SourceDocument,
        quote: str,
        span_id: str,
        context_prefix: Optional[str] = None,
        context_suffix: Optional[str] = None,
    ) -> SourceSpan:
        """Find the exact span in doc.raw_content matching quote.

        If quote appears multiple times, context_prefix and/or context_suffix must disambiguate.
        """
        if not quote:
            raise ValueError("Quote string cannot be empty.")

        content = doc.raw_content
        matches = []
        pos = 0
        while True:
            idx = content.find(quote, pos)
            if idx == -1:
                break
            matches.append(idx)
            pos = idx + 1

        if not matches:
            raise SpanNotFoundError(f"Quote '{quote[:40]}...' not found in document '{doc.doc_id}'.")

        # Disambiguate if multiple matches
        selected_idx = None
        if len(matches) == 1:
            selected_idx = matches[0]
        else:
            # Try to resolve with context
            filtered = []
            for idx in matches:
                prefix_ok = True
                suffix_ok = True
                if context_prefix:
                    p_start = max(0, idx - len(context_prefix))
                    prefix_ok = content[p_start:idx].endswith(context_prefix)
                if context_suffix:
                    s_end = min(len(content), idx + len(quote) + len(context_suffix))
                    suffix_ok = content[idx + len(quote):s_end].startswith(context_suffix)
                if prefix_ok and suffix_ok:
                    filtered.append(idx)
            if len(filtered) == 1:
                selected_idx = filtered[0]
            else:
                raise AmbiguousSpanError(
                    f"Quote '{quote}' found {len(matches)} times in doc '{doc.doc_id}' "
                    f"and context failed to uniquely identify a single occurrence (matches={len(filtered)})."
                )

        start_char = selected_idx
        end_char = selected_idx + len(quote)

        # Re-verify slice
        actual_slice = content[start_char:end_char]
        if actual_slice != quote:
            raise ProvenanceMismatchError(
                f"Slice mismatch: expected '{quote}', got '{actual_slice}' at [{start_char}:{end_char}]."
            )

        # Compute line/col
        l_start, c_start = cls._compute_line_col(content, start_char)
        l_end, c_end = cls._compute_line_col(content, end_char)

        return SourceSpan(
            span_id=span_id,
            doc_id=doc.doc_id,
            start_char=start_char,
            end_char=end_char,
            line_start=l_start,
            col_start=c_start,
            line_end=l_end,
            col_end=c_end,
            exact_quote=quote,
            page_index=0,
        )


class TestSpikeAAnchors(unittest.TestCase):
    """Test suite for Spike A: Exact Provenance and Text Anchoring."""

    def setUp(self):
        self.fixtures_dir = pathlib.Path(__file__).parent.parent / "fixtures"
        self.v1_path = self.fixtures_dir / "s01_v1.txt"
        self.v2_path = self.fixtures_dir / "s01_v2.txt"
        self.unsupported_path = self.fixtures_dir / "unsupported_format.bin"

    def test_document_ingestion_and_hashing(self):
        doc = SourceDocument.from_file("doc-s01-v1", self.v1_path)
        self.assertEqual(doc.doc_id, "doc-s01-v1")
        self.assertGreater(doc.total_chars, 0)
        self.assertGreater(doc.total_lines, 0)
        self.assertEqual(len(doc.sha256_hash), 64)

    def test_exact_anchor_resolution_v1(self):
        doc = SourceDocument.from_file("doc-s01-v1", self.v1_path)
        quote = "Thursday at 10:00"
        span = AnchorResolver.resolve_anchor(doc, quote, span_id="span-appt-v1")

        self.assertEqual(span.exact_quote, quote)
        self.assertTrue(span.verify_against(doc))
        self.assertEqual(doc.raw_content[span.start_char:span.end_char], quote)

    def test_exact_anchor_resolution_v2(self):
        doc = SourceDocument.from_file("doc-s01-v2", self.v2_path)
        quote = "Friday at 14:00"
        span = AnchorResolver.resolve_anchor(doc, quote, span_id="span-appt-v2")

        self.assertEqual(span.exact_quote, quote)
        self.assertTrue(span.verify_against(doc))
        self.assertEqual(doc.raw_content[span.start_char:span.end_char], quote)

    def test_unsupported_format_rejection(self):
        """Negative test: binary/corrupted files must be visibly rejected."""
        with self.assertRaises(UnsupportedDocumentFormatError) as ctx:
            SourceDocument.from_file("doc-corrupt", self.unsupported_path)
        self.assertIn("binary/unsupported data", str(ctx.exception))

    def test_missing_span_rejection(self):
        """Negative test: quotes not present in source must raise SpanNotFoundError."""
        doc = SourceDocument.from_file("doc-s01-v1", self.v1_path)
        with self.assertRaises(SpanNotFoundError):
            AnchorResolver.resolve_anchor(doc, "Wednesday at 09:00", span_id="span-nonexistent")

    def test_ambiguous_span_rejection_and_disambiguation(self):
        """Negative test: repeated strings must raise AmbiguousSpanError unless context given."""
        doc = SourceDocument.from_file("doc-s01-v1", self.v1_path)
        # "appointment" occurs multiple times in s01_v1.txt
        with self.assertRaises(AmbiguousSpanError):
            AnchorResolver.resolve_anchor(doc, "appointment", span_id="span-repeated")

        # Disambiguated with prefix
        span = AnchorResolver.resolve_anchor(
            doc,
            "appointment",
            span_id="span-repeated-resolved",
            context_prefix="Follow-up ",
        )
        self.assertTrue(span.verify_against(doc))
        self.assertEqual(doc.raw_content[span.start_char:span.end_char], "appointment")

    def test_altered_span_rejection(self):
        """Negative test: subtle paraphrase or normalization mismatch must be caught."""
        doc = SourceDocument.from_file("doc-s01-v1", self.v1_path)
        # Attempting to search for "Thursday at 10am" instead of "Thursday at 10:00"
        with self.assertRaises(SpanNotFoundError):
            AnchorResolver.resolve_anchor(doc, "Thursday at 10am", span_id="span-altered")


if __name__ == "__main__":
    unittest.main()
