"""
Profilowanie danych: dla każdej kolumny sprawdzamy, co w niej jest
i jakie ma problemy. Tu NIE ma żadnego AI - to zwykła, przewidywalna logika.

Najważniejsza funkcja: profile_dataframe(df) -> DatasetProfile
"""

import re
import unicodedata
from dataclasses import dataclass, field

import pandas as pd

# --- Wzorce wartości ---------------------------------------------------------
# Każdy wzorzec to (nazwa typu, wyrażenie regularne). Sprawdzamy, jaki procent
# wartości w kolumnie pasuje do danego wzorca.
PATTERNS = {
    "liczba całkowita": r"^-?\d{1,3}([  ]?\d{3})*$|^-?\d+$",
    "liczba (przecinek)": r"^-?\d{1,3}([  ]?\d{3})*,\d+$|^-?\d+,\d+$",   # 1 234,56
    "liczba (kropka)": r"^-?\d+\.\d+$",                                        # 1234.56
    "data dd.mm.rrrr": r"^\d{1,2}\.\d{1,2}\.\d{4}$",
    "data rrrr-mm-dd": r"^\d{4}-\d{2}-\d{2}$",
    "data dd/mm/rrrr": r"^\d{1,2}/\d{1,2}/\d{4}$",
    "kod pocztowy": r"^\d{2}-\d{3}$",
    "e-mail": r"^[\w.+-]+@[\w-]+\.[\w.-]+$",
}
DATE_TYPES = {k for k in PATTERNS if k.startswith("data")}
NUMBER_TYPES = {"liczba całkowita", "liczba (przecinek)", "liczba (kropka)"}

# Próg: od ilu % pasujących wartości uznajemy, że kolumna "jest" danego typu.
TYPE_THRESHOLD = 0.8
# Słowa i znaki, którymi ludzie w plikach oznaczają brak danych.
MISSING_PLACEHOLDERS = {"brak", "-", "--", "n/a", "null", "none", "nan", "b.d.", "bd", "?"}
@dataclass
class ColumnProfile:
    name: str
    detected_type: str
    type_match_pct: float          # jaki % niepustych wartości pasuje do typu
    missing_pct: float
    unique_count: int
    sample_values: list[str]
    issues: list[str] = field(default_factory=list)


@dataclass
class DatasetProfile:
    row_count: int
    column_count: int
    duplicate_rows: int
    columns: list[ColumnProfile]

    @property
    def issue_count(self) -> int:
        return sum(len(c.issues) for c in self.columns) + (1 if self.duplicate_rows else 0)


# --- Funkcje pomocnicze -------------------------------------------------------
def _match_shares(values: pd.Series) -> dict[str, float]:
    """Dla każdego wzorca: jaki ułamek wartości do niego pasuje."""
    return {
        name: values.str.match(pattern).mean()
        for name, pattern in PATTERNS.items()
    }


def _normalize_text(value: str) -> str:
    """'  KRAKÓW ' -> 'krakow'. Służy do wykrywania wariantów tej samej wartości."""
    value = value.strip().lower()
    value = value.replace("ł", "l")  # "ł" nie rozkłada się przez NFKD, więc ręcznie
    value = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def _to_number(values: pd.Series, number_type: str) -> pd.Series:
    """Zamienia tekst na liczby zgodnie z wykrytym formatem."""
    cleaned = values.str.replace(r"[  ]", "", regex=True)
    if number_type == "liczba (przecinek)":
        cleaned = cleaned.str.replace(",", ".", regex=False)
    return pd.to_numeric(cleaned, errors="coerce")


# --- Profil jednej kolumny ------------------------------------------------------
def profile_column(series: pd.Series) -> ColumnProfile:
    total = len(series)
    non_null = series.dropna().astype(str)
    missing_pct = 1 - len(non_null) / total if total else 0.0
    issues: list[str] = []
    
    # 0. Brak danych zapisany słowem ("brak", "-", "n/a"...)
    is_placeholder = non_null.str.strip().str.lower().isin(MISSING_PLACEHOLDERS)
    if is_placeholder.any():
        examples = ", ".join(map(repr, non_null[is_placeholder].unique()[:3]))
        issues.append(f"{is_placeholder.sum()} wartości oznacza brak danych zapisany słowem, np.: {examples}")
        non_null = non_null[~is_placeholder]  # dalej analizujemy już bez nich
    

    if non_null.empty:
        return ColumnProfile(series.name, "pusta", 0.0, missing_pct, 0, [], ["Kolumna jest całkowicie pusta"])

    stripped = non_null.str.strip()

    # 1. Spacje na początku lub końcu
    n_spaces = (stripped != non_null).sum()
    if n_spaces:
        issues.append(f"{n_spaces} wartości ma zbędne spacje na początku lub końcu")

    # 2. Wykrywanie typu
    # Patrzymy na "rodziny" typów: kolumna z "12" i "12,50" to nadal kolumna
    # liczbowa, a z "05.03.2024" i "2024-03-05" - nadal kolumna z datami.
    shares = _match_shares(stripped)
    families = {
        "liczba": NUMBER_TYPES,
        "data": DATE_TYPES,
        "kod pocztowy": {"kod pocztowy"},
        "e-mail": {"e-mail"},
    }
    family_masks = {
        fam: stripped.str.match("|".join(f"(?:{PATTERNS[t]})" for t in types))
        for fam, types in families.items()
    }
    best_family = max(family_masks, key=lambda f: family_masks[f].mean())
    best_mask = family_masks[best_family]
    best_share = best_mask.mean()

    if best_share < TYPE_THRESHOLD:
        detected_type, best_share = "tekst", 1.0
    elif best_family == "liczba":
        if shares["liczba (przecinek)"] > 0:
            detected_type = "liczba (przecinek)"
        elif shares["liczba (kropka)"] > 0:
            detected_type = "liczba (kropka)"
        else:
            detected_type = "liczba całkowita"
        if shares["liczba (przecinek)"] > 0 and shares["liczba (kropka)"] > 0:
            issues.append("Liczby zapisane raz z przecinkiem, raz z kropką")
    elif best_family == "data":
        formats_used = sorted(t for t in DATE_TYPES if shares[t] > 0)
        detected_type = formats_used[0] if len(formats_used) == 1 else "data (mieszane formaty)"
        if len(formats_used) > 1:
            issues.append("Daty w kilku formatach: " + ", ".join(formats_used))
    else:
        detected_type = best_family
    type_match_pct = best_share

    # 3. Wartości niepasujące do wykrytego typu
    if detected_type != "tekst" and best_share < 1:
        bad = stripped[~best_mask]
        examples = ", ".join(map(repr, bad.unique()[:3]))
        issues.append(f"{len(bad)} wartości nie pasuje do typu „{detected_type}”, np.: {examples}")

    # 4. Liczby zapisane jako tekst z przecinkiem - Power BI ich sam nie rozpozna
    if detected_type == "liczba (przecinek)":
        issues.append("Liczby z przecinkiem dziesiętnym - wymagają konwersji (ustawienia regionalne pl-PL)")

    # 5. Wartości odstające (metoda IQR) dla kolumn liczbowych
    if detected_type in NUMBER_TYPES:
        nums = _to_number(stripped, detected_type).dropna()
        if len(nums) >= 8:
            q1, q3 = nums.quantile([0.25, 0.75])
            iqr = q3 - q1
            outliers = nums[(nums < q1 - 3 * iqr) | (nums > q3 + 3 * iqr)]
            if len(outliers):
                issues.append(f"{len(outliers)} wartości odstających, np.: {outliers.iloc[0]:g}")
        if (nums < 0).any():
            issues.append(f"{(nums < 0).sum()} wartości ujemnych - sprawdź, czy to możliwe")

    # 6. Warianty tej samej wartości ("Kraków", "krakow", "KRAKÓW ")
    if detected_type == "tekst" and stripped.nunique() <= 200:
        groups = non_null.groupby(non_null.map(_normalize_text)).unique()
        variants = [list(v) for v in groups if len(v) > 1]
        if variants:
            example = " / ".join(map(repr, variants[0][:4]))
            issues.append(f"{len(variants)} grup wartości zapisanych na kilka sposobów, np.: {example}")

    return ColumnProfile(
        name=series.name,
        detected_type=detected_type,
        type_match_pct=type_match_pct,
        missing_pct=missing_pct,
        unique_count=stripped.nunique(),
        sample_values=list(stripped.unique()[:5]),
        issues=issues,
    )


# --- Profil całej tabeli ------------------------------------------------------
def profile_dataframe(df: pd.DataFrame) -> DatasetProfile:
    columns = [profile_column(df[col]) for col in df.columns]
    for col in columns:
        if col.missing_pct > 0:
            col.issues.insert(0, f"{col.missing_pct:.0%} braków danych")
    return DatasetProfile(
        row_count=len(df),
        column_count=len(df.columns),
        duplicate_rows=int(df.duplicated().sum()),
        columns=columns,
    )
