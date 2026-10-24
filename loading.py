"""
Loading CSV and Excel files.

Polish CSV files have two common traps:
1. Windows-1250 (cp1250) encoding instead of UTF-8 -> "ą", "ł" turn into garbage,
2. a semicolon separator, because the comma is the decimal separator ("12,50").

Both are detected automatically and reported back, so the user knows how the file was read.
"""

import csv
import io
from dataclasses import dataclass

import pandas as pd
from charset_normalizer import from_bytes

# Order matters: the most common encodings are tried first.
CANDIDATE_ENCODINGS = ["utf-8-sig", "cp1250", "iso-8859-2"]
CANDIDATE_SEPARATORS = [";", ",", "\t", "|"]


@dataclass
class LoadResult:
    """Loaded table plus details of how it was read."""

    df: pd.DataFrame
    file_type: str          # "csv" or "excel"
    encoding: str | None    # CSV only
    separator: str | None   # CSV only
    # Raw Excel sheet without a header - needed when the header spans several
    # rows (e.g. GIOŚ files); reshape.py then finds where the data starts.
    raw: pd.DataFrame | None = None
    sheet_name: str | None = None


def detect_encoding(raw: bytes) -> str:
    """Returns an encoding that decodes the file without errors."""
    for enc in CANDIDATE_ENCODINGS:
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    # Fall back to statistical detection.
    best = from_bytes(raw).best()
    return best.encoding if best else "utf-8"


def detect_separator(text: str) -> str:
    """Detects the separator from the first lines of the file."""
    sample = "\n".join(text.splitlines()[:20])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="".join(CANDIDATE_SEPARATORS))
        return dialect.delimiter
    except csv.Error:
        # Fallback: the candidate that appears most often in the first line.
        first_line = text.splitlines()[0] if text else ""
        return max(CANDIDATE_SEPARATORS, key=first_line.count)


def load_file(raw: bytes, filename: str) -> LoadResult:
    """Loads a file from bytes (as received from the Streamlit uploader)."""
    name = filename.lower()

    if name.endswith((".xlsx", ".xls")):
        # Excel stores types and encoding itself, so nothing needs guessing.
        # The first sheet is read twice: normally (first row = header) and raw,
        # to detect headers that span several rows.
        book = pd.ExcelFile(io.BytesIO(raw))
        sheet = book.sheet_names[0]
        df = book.parse(sheet)
        # Excel headers can be numbers (e.g. 1, 2, 3) - convert them to strings,
        # because column names are treated as text downstream.
        df.columns = [str(c) for c in df.columns]
        raw_sheet = book.parse(sheet, header=None)
        return LoadResult(df=df, file_type="excel", encoding=None, separator=None,
                          raw=raw_sheet, sheet_name=sheet)

    encoding = detect_encoding(raw)
    text = raw.decode(encoding)
    separator = detect_separator(text)

    # dtype=str: read everything as text on purpose, so nothing is silently
    # converted - types are detected later, in profiling.
    df = pd.read_csv(io.StringIO(text), sep=separator, dtype=str, keep_default_na=False)

    # Treat empty and whitespace-only strings as missing.
    df = df.replace(r"^\s*$", pd.NA, regex=True)
    return LoadResult(df=df, file_type="csv", encoding=encoding, separator=separator)
