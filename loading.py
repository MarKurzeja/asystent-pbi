"""
Wczytywanie plików CSV i Excel.

Polskie pliki CSV często mają dwie pułapki:
1. kodowanie Windows-1250 (cp1250) zamiast UTF-8 -> "ą", "ł" zamieniają się w krzaczki,
2. średnik jako separator, bo przecinek jest separatorem dziesiętnym ("12,50").

Ten moduł sam wykrywa jedno i drugie, a wynik zwraca razem z informacją,
co wykrył - żeby użytkownik wiedział, co się stało z jego plikiem.
"""

import csv
import io
from dataclasses import dataclass

import pandas as pd
from charset_normalizer import from_bytes

# Kolejność ma znaczenie: najpierw próbujemy najczęstszych kodowań.
CANDIDATE_ENCODINGS = ["utf-8-sig", "cp1250", "iso-8859-2"]
CANDIDATE_SEPARATORS = [";", ",", "\t", "|"]


@dataclass
class LoadResult:
    """Wczytana tabela + informacje o tym, jak ją wczytaliśmy."""

    df: pd.DataFrame
    file_type: str          # "csv" albo "excel"
    encoding: str | None    # tylko dla CSV
    separator: str | None   # tylko dla CSV
    # Surowy arkusz Excela bez nagłówka - potrzebny, gdy nagłówek zajmuje kilka
    # wierszy (np. pliki GIOŚ). Wtedy reshape.py sam ustala, gdzie są dane.
    raw: pd.DataFrame | None = None
    sheet_name: str | None = None


def detect_encoding(raw: bytes) -> str:
    """Zwraca nazwę kodowania, w którym plik da się poprawnie odczytać."""
    for enc in CANDIDATE_ENCODINGS:
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    # Gdy żadne nie pasuje, pytamy bibliotekę, która zgaduje statystycznie.
    best = from_bytes(raw).best()
    return best.encoding if best else "utf-8"


def detect_separator(text: str) -> str:
    """Zgaduje separator na podstawie pierwszych linii pliku."""
    sample = "\n".join(text.splitlines()[:20])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="".join(CANDIDATE_SEPARATORS))
        return dialect.delimiter
    except csv.Error:
        # Plan B: wybieramy znak, który występuje najczęściej w pierwszej linii.
        first_line = text.splitlines()[0] if text else ""
        return max(CANDIDATE_SEPARATORS, key=first_line.count)


def load_file(raw: bytes, filename: str) -> LoadResult:
    """Wczytuje plik z bajtów (tak dostajemy go z formularza w Streamlit)."""
    name = filename.lower()

    if name.endswith((".xlsx", ".xls")):
        # Excel przechowuje typy i kodowanie sam, więc nic nie zgadujemy.
        # Wczytujemy pierwszy arkusz dwa razy: zwyczajnie (pierwszy wiersz = nagłówek)
        # i "na surowo", żeby móc rozpoznać nagłówek zajmujący kilka wierszy.
        book = pd.ExcelFile(io.BytesIO(raw))
        sheet = book.sheet_names[0]
        df = book.parse(sheet)
        # Nagłówki w Excelu bywają liczbami (np. 1, 2, 3) - zamieniamy je na tekst,
        # bo dalej traktujemy nazwy kolumn jak napisy.
        df.columns = [str(c) for c in df.columns]
        raw_sheet = book.parse(sheet, header=None)
        return LoadResult(df=df, file_type="excel", encoding=None, separator=None,
                          raw=raw_sheet, sheet_name=sheet)

    encoding = detect_encoding(raw)
    text = raw.decode(encoding)
    separator = detect_separator(text)

    # dtype=str: celowo wczytujemy wszystko jako tekst. Dzięki temu nic nie
    # zostanie "po cichu" przekonwertowane - typy wykrywamy sami w profilowaniu.
    df = pd.read_csv(io.StringIO(text), sep=separator, dtype=str, keep_default_na=False)

    # Puste napisy i same spacje traktujemy jako brak danych.
    df = df.replace(r"^\s*$", pd.NA, regex=True)
    return LoadResult(df=df, file_type="csv", encoding=encoding, separator=separator)
