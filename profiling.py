"""
Profilowanie danych: dla każdej kolumny sprawdzamy, co w niej jest
i jakie ma problemy. Tu NIE ma żadnego AI - to zwykła, przewidywalna logika.

Najważniejsza funkcja: profile_dataframe(df) -> DatasetProfile

Problemy zapisujemy jako Issue(klucz, parametry), a nie gotowy tekst.
Dzięki temu ten sam raport można pokazać po angielsku i po polsku (patrz i18n.py).
"""

import re
import unicodedata
from dataclasses import dataclass, field

import pandas as pd

from i18n import t

# --- Wzorce wartości ---------------------------------------------------------
# Każdy wzorzec to (identyfikator typu, wyrażenie regularne). Sprawdzamy,
# jaki procent wartości w kolumnie pasuje do danego wzorca.
# Spacja albo twarda spacja (separator tysięcy). Bez litery r przed cudzysłowem,
# żeby Python sam zamienił   na znak - pyarrow nie rozumie zapisu  .
THOUSANDS_SEP = "[  ]"

PATTERNS = {
    "integer": r"^-?\d{1,3}(" + THOUSANDS_SEP + r"?\d{3})*$|^-?\d+$",
    "decimal_comma": r"^-?\d{1,3}(" + THOUSANDS_SEP + r"?\d{3})*,\d+$|^-?\d+,\d+$",   # 1 234,56
    "decimal_dot": r"^-?\d+\.\d+$",                                         # 1234.56
    "date_dot": r"^\d{1,2}\.\d{1,2}\.\d{4}$",
    "date_iso": r"^\d{4}-\d{2}-\d{2}$",
    "date_slash": r"^\d{1,2}/\d{1,2}/\d{4}$",
    "postcode": r"^\d{2}-\d{3}$",
    "email": r"^[\w.+-]+@[\w-]+\.[\w.-]+$",
}
DATE_TYPES = {"date_dot", "date_iso", "date_slash"}
NUMBER_TYPES = {"integer", "decimal_comma", "decimal_dot"}

# Próg: od ilu % pasujących wartości uznajemy, że kolumna "jest" danego typu.
TYPE_THRESHOLD = 0.8

# Słowa i znaki, którymi ludzie w plikach oznaczają brak danych.
MISSING_PLACEHOLDERS = {"brak", "-", "--", "n/a", "null", "none", "nan", "b.d.", "bd", "?"}

NIP_WEIGHTS = (6, 5, 7, 2, 3, 4, 5, 6, 7)


@dataclass
class Issue:
    key: str                                    # klucz tekstu w i18n.py, np. "issue_spaces"
    params: dict = field(default_factory=dict)  # wartości do wstawienia w tekst

    def render(self, lang: str) -> str:
        params = dict(self.params)
        # Nazwy typów i listy formatów też tłumaczymy.
        if "type" in params:
            params["type"] = t("type_" + params["type"], lang)
        if self.key == "issue_mixed_dates":
            params["formats"] = ", ".join(t("type_" + f, lang) for f in params["formats"])
        return t(self.key, lang, **params)


@dataclass
class ColumnProfile:
    name: str
    detected_type: str             # identyfikator, np. "decimal_comma"
    type_match_pct: float          # jaki % niepustych wartości pasuje do typu
    missing_pct: float
    unique_count: int
    sample_values: list[str]
    issues: list[Issue] = field(default_factory=list)


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
def is_valid_nip(value: str) -> bool:
    """Sprawdza, czy NIP jest poprawny (długość i cyfra kontrolna).

    Akceptuje zapisy z myślnikami, spacjami i prefiksem PL, np. "123-456-32-18".
    """
    digits = re.sub(r"\D", "", str(value))  # zostawiamy same cyfry
    if len(digits) != 10:
        return False
    checksum = sum(int(d) * w for d, w in zip(digits, NIP_WEIGHTS)) % 11
    return checksum == int(digits[9])


def _match_shares(values: pd.Series) -> dict[str, float]:
    """Dla każdego wzorca: jaki ułamek wartości do niego pasuje."""
    return {name: values.str.match(pattern).mean() for name, pattern in PATTERNS.items()}


def normalize_text(value: str) -> str:
    """'  KRAKÓW ' -> 'krakow'. Służy do wykrywania wariantów tej samej wartości."""
    value = value.strip().lower()
    value = value.replace("ł", "l")  # "ł" nie rozkłada się przez NFKD, więc ręcznie
    value = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def to_number(values: pd.Series, number_type: str) -> pd.Series:
    """Zamienia tekst na liczby zgodnie z wykrytym formatem."""
    cleaned = values.str.replace(THOUSANDS_SEP, "", regex=True)
    if number_type == "decimal_comma":
        cleaned = cleaned.str.replace(",", ".", regex=False)
    return pd.to_numeric(cleaned, errors="coerce")


def _examples(values: pd.Series, k: int = 3) -> str:
    return ", ".join(map(repr, values.unique()[:k]))


# --- Profil jednej kolumny ------------------------------------------------------
def _profile_native(series: pd.Series) -> ColumnProfile:
    """Kolumna, która już ma prawdziwy typ (liczby lub daty, np. z Excela).

    Tu nie ma czego rozpoznawać z tekstu - sprawdzamy tylko braki,
    wartości odstające i ujemne.
    """
    total = len(series)
    values = series.dropna()
    missing_pct = 1 - len(values) / total if total else 0.0
    issues: list[Issue] = []
    if pd.api.types.is_datetime64_any_dtype(series):
        detected = "date_native"
    else:
        detected = "number_native"
        if len(values) >= 8:
            q1, q3 = values.quantile([0.25, 0.75])
            iqr = q3 - q1
            outliers = values[(values < q1 - 3 * iqr) | (values > q3 + 3 * iqr)]
            if len(outliers):
                issues.append(Issue("issue_outliers", {"n": len(outliers), "example": f"{outliers.iloc[0]:g}"}))
        if (values < 0).any():
            issues.append(Issue("issue_negatives", {"n": int((values < 0).sum())}))
    samples = [str(v)[:10] if detected == "date_native" else f"{v:g}" for v in values.unique()[:5]]
    return ColumnProfile(series.name, detected, 1.0, missing_pct, int(values.nunique()), samples, issues)


def profile_column(series: pd.Series) -> ColumnProfile:
    if pd.api.types.is_datetime64_any_dtype(series) or (
            pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)):
        return _profile_native(series)

    total = len(series)
    non_null = series.dropna().astype(str)
    missing_pct = 1 - len(non_null) / total if total else 0.0
    issues: list[Issue] = []

    # 0. Brak danych zapisany słowem ("brak", "-", "n/a"...)
    is_placeholder = non_null.str.strip().str.lower().isin(MISSING_PLACEHOLDERS)
    if is_placeholder.any():
        issues.append(Issue("issue_placeholders",
                            {"n": int(is_placeholder.sum()), "examples": _examples(non_null[is_placeholder])}))
        non_null = non_null[~is_placeholder]  # dalej analizujemy już bez nich

    if non_null.empty:
        return ColumnProfile(series.name, "empty", 0.0, missing_pct, 0, [], [Issue("issue_empty_column")])

    stripped = non_null.str.strip()

    # 1. Spacje na początku lub końcu
    n_spaces = int((stripped != non_null).sum())
    if n_spaces:
        issues.append(Issue("issue_spaces", {"n": n_spaces}))

    # 2. Wykrywanie typu
    # Patrzymy na "rodziny" typów: kolumna z "12" i "12,50" to nadal kolumna
    # liczbowa, a z "05.03.2024" i "2024-03-05" - nadal kolumna z datami.
    shares = _match_shares(stripped)
    families = {"number": NUMBER_TYPES, "date": DATE_TYPES, "postcode": {"postcode"}, "email": {"email"}}
    family_masks = {
        fam: stripped.str.match("|".join(f"(?:{PATTERNS[t_]})" for t_ in types))
        for fam, types in families.items()
    }
    best_family = max(family_masks, key=lambda f: family_masks[f].mean())
    best_mask = family_masks[best_family]
    best_share = float(best_mask.mean())

    if best_share < TYPE_THRESHOLD:
        detected_type, best_share = "text", 1.0
    elif best_family == "number":
        if shares["decimal_comma"] > 0:
            detected_type = "decimal_comma"
        elif shares["decimal_dot"] > 0:
            detected_type = "decimal_dot"
        else:
            detected_type = "integer"
        if shares["decimal_comma"] > 0 and shares["decimal_dot"] > 0:
            issues.append(Issue("issue_mixed_separators"))
    elif best_family == "date":
        formats_used = sorted(t_ for t_ in DATE_TYPES if shares[t_] > 0)
        detected_type = formats_used[0] if len(formats_used) == 1 else "date_mixed"
        if len(formats_used) > 1:
            issues.append(Issue("issue_mixed_dates", {"formats": formats_used}))
    else:
        detected_type = best_family

    # 3. Wartości niepasujące do wykrytego typu
    if detected_type != "text" and best_share < 1:
        bad = stripped[~best_mask]
        issues.append(Issue("issue_type_mismatch",
                            {"type": detected_type, "n": len(bad), "examples": _examples(bad)}))

    # 4. Liczby zapisane jako tekst z przecinkiem - Power BI ich sam nie rozpozna
    if detected_type == "decimal_comma":
        issues.append(Issue("issue_comma_decimal"))

    # 5. Wartości odstające (metoda IQR) dla kolumn liczbowych
    if detected_type in NUMBER_TYPES:
        nums = to_number(stripped, detected_type).dropna()
        if len(nums) >= 8:
            q1, q3 = nums.quantile([0.25, 0.75])
            iqr = q3 - q1
            outliers = nums[(nums < q1 - 3 * iqr) | (nums > q3 + 3 * iqr)]
            if len(outliers):
                issues.append(Issue("issue_outliers", {"n": len(outliers), "example": f"{outliers.iloc[0]:g}"}))
        if (nums < 0).any():
            issues.append(Issue("issue_negatives", {"n": int((nums < 0).sum())}))

    # 6. Warianty tej samej wartości ("Kraków", "krakow", "KRAKÓW ")
    if detected_type == "text" and stripped.nunique() <= 200:
        groups = non_null.groupby(non_null.map(normalize_text)).unique()
        variants = [list(v) for v in groups if len(v) > 1]
        if variants:
            examples = " / ".join(map(repr, variants[0][:4]))
            issues.append(Issue("issue_variants", {"n": len(variants), "examples": examples}))

    # 7. NIP - sprawdzamy cyfrę kontrolną (w kolumnach, które mają "nip" w nazwie)
    if "nip" in str(series.name).lower():
        invalid = stripped[~stripped.map(is_valid_nip)]
        if len(invalid):
            issues.append(Issue("issue_nip_invalid", {"n": len(invalid), "examples": _examples(invalid)}))
        formats = stripped.str.replace(r"\d", "9", regex=True).unique()
        if len(formats) > 1:
            issues.append(Issue("issue_nip_formats", {"n": len(formats), "formats": ", ".join(sorted(formats))}))

    return ColumnProfile(
        name=series.name,
        detected_type=detected_type,
        type_match_pct=best_share,
        missing_pct=missing_pct,
        unique_count=int(stripped.nunique()),
        sample_values=list(stripped.unique()[:5]),
        issues=issues,
    )


# --- Profil całej tabeli ------------------------------------------------------
def profile_dataframe(df: pd.DataFrame) -> DatasetProfile:
    columns = [profile_column(df[col]) for col in df.columns]
    for col in columns:
        if col.missing_pct > 0:
            col.issues.insert(0, Issue("issue_missing", {"pct": f"{col.missing_pct:.0%}"}))
    return DatasetProfile(
        row_count=len(df),
        column_count=len(df.columns),
        duplicate_rows=int(df.duplicated().sum()),
        columns=columns,
    )
