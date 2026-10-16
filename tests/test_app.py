"""
Testy automatyczne. Uruchom w terminalu:
    python -m pytest

Każdy test sprawdza jedną rzecz. Jeśli po zmianie w kodzie któryś test
przestanie przechodzić, od razu wiesz, co się zepsuło.
"""

import sys
from pathlib import Path

import pandas as pd

# Pozwala zaimportować moduły z głównego folderu projektu.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cleaning import apply_steps, steps_to_m, suggest_steps  # noqa: E402
from i18n import TEXTS, issues_count  # noqa: E402
from loading import load_file  # noqa: E402
from profiling import is_valid_nip, profile_column, profile_dataframe  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data" / "zamowienia_brudne.csv"


# --- NIP ---------------------------------------------------------------------
def test_valid_nip_in_different_formats():
    assert is_valid_nip("5260250274")
    assert is_valid_nip("526-025-02-74")
    assert is_valid_nip("PL5260250274")


def test_invalid_nip():
    assert not is_valid_nip("5260250275")   # zła cyfra kontrolna
    assert not is_valid_nip("123")          # za krótki


# --- Tłumaczenia ----------------------------------------------------------------
def test_every_text_has_both_languages():
    for key, versions in TEXTS.items():
        assert set(versions) == {"en", "pl"}, key


def test_polish_plural():
    assert issues_count(1, "pl") == "1 problem"
    assert issues_count(3, "pl") == "3 problemy"
    assert issues_count(5, "pl") == "5 problemów"
    assert issues_count(12, "pl") == "12 problemów"
    assert issues_count(22, "pl") == "22 problemy"
    assert issues_count(1, "en") == "1 issue"
    assert issues_count(2, "en") == "2 issues"


# --- Wykrywanie typów -------------------------------------------------------------
def test_detects_polish_decimal_comma():
    col = profile_column(pd.Series(["1 234,56", "12,50", "7,00"], name="kwota"))
    assert col.detected_type == "decimal_comma"


def test_detects_mixed_date_formats():
    col = profile_column(pd.Series(["05.03.2025", "2025-03-06", "07/03/2025"], name="data"))
    assert col.detected_type == "date_mixed"


def test_placeholder_words_are_not_type_errors():
    col = profile_column(pd.Series(["10,00", "brak", "20,00", "-"], name="kwota"))
    assert col.type_match_pct == 1.0
    assert any(i.key == "issue_placeholders" for i in col.issues)


# --- Cały proces na pliku testowym ------------------------------------------------
def _load():
    result = load_file(DATA.read_bytes(), DATA.name)
    return result, profile_dataframe(result.df)


def test_polish_csv_is_detected():
    result, _ = _load()
    assert result.encoding == "cp1250"
    assert result.separator == ";"


def test_cleaning_removes_duplicates_and_fixes_types():
    result, profile = _load()
    cleaned = apply_steps(result.df, suggest_steps(result.df, profile))
    assert len(cleaned) == len(result.df) - profile.duplicate_rows
    assert pd.api.types.is_datetime64_any_dtype(cleaned["data_zamowienia"])
    assert pd.api.types.is_float_dtype(cleaned["kwota_brutto"])
    assert cleaned["data_zamowienia"].notna().all()
    assert set(cleaned["miasto"].dropna()) <= {"Kraków", "Warszawa", "Gdańsk", "Wrocław", "Łódź", "Poznań"}


def test_power_query_code_in_both_languages():
    result, profile = _load()
    steps = suggest_steps(result.df, profile)
    m_pl = steps_to_m(steps, "C:\\dane\\plik.csv", "csv", result.encoding, result.separator, "pl")
    m_en = steps_to_m(steps, "C:\\data\\file.csv", "csv", result.encoding, result.separator, "en")
    assert m_pl.startswith("let") and m_pl.rstrip().endswith('#"Bez duplikatów"')
    assert m_en.rstrip().endswith('#"Removed duplicates"')
    assert "Encoding=1250" in m_en
