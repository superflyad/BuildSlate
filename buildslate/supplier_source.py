"""Screen controlled supplier document bytes before a release cites them.

Signatures and archive integrity detect mislabeled files. They do not establish
the document's issuer or validate the engineering claims inside it.
"""

from __future__ import annotations

import hashlib
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError

SUPPORTED_SUFFIXES = frozenset({".pdf", ".step", ".stp", ".zip"})
MAX_ARCHIVE_FILES = 10_000
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 500_000_000


def source_format_error(path: Path) -> str | None:
    """Reject obvious filename/content mismatches and damaged ZIP archives."""
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        return "source format must be PDF, STEP, or ZIP"
    if suffix == ".zip":
        try:
            with zipfile.ZipFile(path) as archive:
                files = [item for item in archive.infolist() if not item.is_dir()]
                if not files or len(files) > MAX_ARCHIVE_FILES:
                    return "source ZIP has no files or too many files"
                if (
                    sum(item.file_size for item in files)
                    > MAX_ARCHIVE_UNCOMPRESSED_BYTES
                ):
                    return "source ZIP exceeds the inspection size limit"
                if archive.testzip() is not None:
                    return "source ZIP has a damaged member"
        except (OSError, zipfile.BadZipFile, RuntimeError, ValueError):
            return "source ZIP is unreadable"
        return None
    data = path.read_bytes()
    if suffix == ".pdf":
        tail = data[-1024:]
        if (
            not data.startswith(b"%PDF-")
            or b"startxref" not in tail
            or b"%%EOF" not in tail
        ):
            return "source PDF signature or trailer is missing"
        try:
            reader = PdfReader(BytesIO(data), strict=True)
            if reader.is_encrypted or len(reader.pages) < 1:
                return "source PDF must have a readable page without a password"
            for page in reader.pages:
                if page.mediabox.width <= 0 or page.mediabox.height <= 0:
                    return "source PDF has a page with invalid dimensions"
        except (PdfReadError, OSError, TypeError, ValueError, KeyError):
            return "source PDF cannot be parsed"
    elif not data.lstrip(b"\xef\xbb\xbf\r\n\t ").startswith(
        b"ISO-10303-21;"
    ) or not data.rstrip().endswith(b"END-ISO-10303-21;"):
        return "source STEP header or terminator is missing"
    return None


def controlled_source_error(root: Path, directory: Path, record: Any) -> str | None:
    """Check a source record's path, digest, and basic file format."""
    if not isinstance(record, dict) or not isinstance(record.get("path"), str):
        return "missing controlled source path"
    if not record["path"].strip():
        return "missing controlled source path"
    if not isinstance(record.get("sha256"), str) or not record["sha256"].strip():
        return "missing source SHA-256"
    allowed = (root / directory).resolve()
    target = (root / record["path"]).resolve()
    if not target.is_relative_to(allowed) or target == allowed:
        return "source is outside the controlled directory"
    if not target.is_file():
        return "source file is missing"
    if hashlib.sha256(target.read_bytes()).hexdigest() != record["sha256"].lower():
        return "source hash mismatch"
    return source_format_error(target)
