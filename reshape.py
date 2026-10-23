"""
Pliki w "układzie szerokim" z nagłówkiem na kilka wierszy.

Przykład - plik GIOŚ z pomiarami PM10:

    Nr                1             2             ...
    Kod stacji        DsGlogWiStwo  DsJaworMOB    ...   <- wiersz z kluczami
    Wskaźnik          PM10          PM10          ...   <- wartość stała
    Jednostka         ug/m3         ug/m3         ...   <- wartość stała
    2019-01-01        13.71         13.15         ...   <- tu zaczynają się dane
    2019-01-02         8.28         11.26         ...

Ludziom wygodnie czyta się taką tabelę, ale Power BI potrzebuje układu
"długiego": jeden wiersz = jedna data, jedna stacja, jedna wartość.
Ten moduł:
1. rozpoznaje taki układ (detect_wide_layout),
2. odwraca tabelę w pandas (unpivot) - do podglądu,
3. generuje ten sam krok w języku M (wide_to_m) - dla Power BI.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd

from i18n import t

MAX_HEADER_ROWS = 20      # nagłówek dłuższy niż 20 wierszy uznajemy za nietypowy
MIN_VALUE_COLUMNS = 3     # układ szeroki ma sens dopiero przy kilku kolumnach z wartościami
DATE_TEXT = re.compile(r"^\d{1,2}[./]\d{1,2}[./]\d{4}$|^\d{4}-\d{2}-\d{2}")
# Liczba zapisana jako tekst z przecinkiem, np. "3,878" (tak GIOŚ zapisywał część plików do 2018 r.)
COMMA_NUMBER = re.compile(r"^-?\d+(,\d+)?$")


@dataclass
class WideLayout:
    data_start: int                  # numer wiersza, od którego zaczynają się dane
    key_row: int                     # wiersz z nazwami kolumn (np. kodami stacji)
    key_label: str                   # jego etykieta, np. "Kod stacji"
    keys: list[str]                  # same klucze, np. ["DsGlogWiStwo", ...]
    constants: dict[str, int] = field(default_factory=dict)  # etykieta -> wiersz, np. {"Wskaźnik": 2}
    decimal_comma: bool = False      # True, gdy wartości są tekstem z przecinkiem ("3,878")

    @property
    def header_rows(self) -> int:
        return self.data_start


def _is_date(value) -> bool:
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return True
    return isinstance(value, str) and bool(DATE_TEXT.match(value.strip()))


def _is_comma_number(value) -> bool:
    return isinstance(value, str) and bool(COMMA_NUMBER.match(value.strip()))


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and not pd.isna(value)


def detect_wide_layout(raw: pd.DataFrame | None) -> WideLayout | None:
    """Sprawdza, czy surowy arkusz ma nagłówek na kilka wierszy i kolumny z wartościami.

    Zasady (celowo proste i przewidywalne):
    - pierwsza kolumna: najpierw etykiety (tekst), potem daty - pierwsza data to początek danych,
    - wśród wierszy nagłówka szukamy takiego, w którym każda kolumna ma inną, niepustą wartość
      (to klucze, np. kody stacji),
    - wiersze nagłówka z jedną wartością we wszystkich kolumnach to stałe (np. "Wskaźnik: PM10"),
    - w części z danymi przeważają liczby.
    Jeśli któryś warunek nie jest spełniony, zwracamy None i plik traktujemy zwyczajnie.
    """
    if raw is None or raw.shape[1] < MIN_VALUE_COLUMNS + 1 or raw.shape[0] < 3:
        return None

    first_col = raw.iloc[:, 0].tolist()
    data_start = next((i for i, v in enumerate(first_col[:MAX_HEADER_ROWS + 1]) if _is_date(v)), None)
    if not data_start:   # None albo 0 (brak wierszy nagłówka)
        return None

    key_row, constants = None, {}
    for r in range(data_start):
        label = raw.iat[r, 0]
        values = raw.iloc[r, 1:]
        if not isinstance(label, str) or values.isna().any():
            continue
        if values.nunique() == 1:
            constants[label.strip()] = r
        elif key_row is None and values.map(lambda v: isinstance(v, str)).all() and values.is_unique:
            key_row = r
    if key_row is None:
        return None

    body = raw.iloc[data_start:, 1:].stack().dropna()   # tylko niepuste komórki
    if body.empty:
        return None
    numeric_share = body.map(_is_number).mean()
    comma_share = body.map(_is_comma_number).mean()
    if numeric_share + comma_share < 0.9:
        return None

    return WideLayout(
        data_start=data_start,
        key_row=key_row,
        key_label=str(raw.iat[key_row, 0]).strip(),
        keys=[str(k).strip() for k in raw.iloc[key_row, 1:]],
        constants=constants,
        decimal_comma=comma_share > numeric_share,
    )


def column_names(layout: WideLayout, lang: str) -> tuple[str, str]:
    """Nazwy kolumn po odwróceniu: (kolumna z datą, kolumna z wartością)."""
    return t("col_name_date", lang), t("col_name_value", lang)


def unpivot(raw: pd.DataFrame, layout: WideLayout, lang: str) -> pd.DataFrame:
    """Zamienia układ szeroki na długi (pandas, do podglądu w aplikacji).

    Puste komórki (brak pomiaru) są pomijane - dokładnie tak samo działa
    Table.UnpivotOtherColumns w Power Query, więc liczba wierszy się zgadza.
    """
    date_col, value_col = column_names(layout, lang)
    data = raw.iloc[layout.data_start:].copy()
    data.columns = [date_col] + layout.keys
    long = data.melt(id_vars=date_col, var_name=layout.key_label, value_name=value_col)
    long = long.dropna(subset=[value_col])
    for label, row in layout.constants.items():
        long[label] = str(raw.iat[row, 1])
    long[date_col] = pd.to_datetime(long[date_col], dayfirst=True, errors="coerce")
    if layout.decimal_comma:
        long[value_col] = long[value_col].astype(str).str.strip().str.replace(",", ".", regex=False)
    long[value_col] = pd.to_numeric(long[value_col], errors="coerce")
    long[layout.key_label] = long[layout.key_label].astype(str)
    return long.reset_index(drop=True)


def wide_to_m(layout: WideLayout, lang: str, source_name: str) -> list[tuple[str, str]]:
    """Kroki M, które robią w Power BI to samo co unpivot().

    Zwraca listę (nazwa kroku, wyrażenie). Wyrażenia odwołują się do kroku
    źródłowego po nazwie (source_name), a kolejne kroki - do poprzedniego.
    """
    from cleaning import m_name, m_text   # import tutaj, żeby uniknąć importu cyklicznego

    date_col, value_col = column_names(layout, lang)
    src = m_name(source_name)
    keys, body, renamed, unpivoted = (t("m_wide_keys", lang), t("m_wide_data", lang),
                                      t("m_wide_renamed", lang), t("m_wide_unpivoted", lang))
    steps = [
        # Klucze bierzemy z pliku (a nie wpisujemy na sztywno), więc ten sam kod
        # zadziała dla pliku z innego roku, nawet jeśli zmieni się lista stacji.
        (keys, f"List.Skip(Record.ToList({src}{{{layout.key_row}}}), 1)"),
        (body, f"Table.Skip({src}, {layout.data_start})"),
        (renamed, f"Table.RenameColumns({m_name(body)}, "
                  f"List.Zip({{Table.ColumnNames({m_name(body)}), {{{m_text(date_col)}}} & {m_name(keys)}}}))"),
        (unpivoted, f"Table.UnpivotOtherColumns({m_name(renamed)}, {{{m_text(date_col)}}}, "
                    f"{m_text(layout.key_label)}, {m_text(value_col)})"),
    ]
    prev = unpivoted
    for label, row in layout.constants.items():
        name = t("m_added", lang, col=label)
        steps.append((name, f"Table.AddColumn({m_name(prev)}, {m_text(label)}, "
                            f"each Text.From(Record.ToList({src}{{{row}}}){{1}}), type text)"))
        prev = name
    steps.append((t("m_types", lang),
                  f"Table.TransformColumnTypes({m_name(prev)}, {{{{{m_text(date_col)}, type date}}, "
                  f"{{{m_text(layout.key_label)}, type text}}, {{{m_text(value_col)}, type number}}}}"
                  # Tekst "3,878" zamieni się na liczbę tylko z polskimi ustawieniami regionalnymi.
                  + (', "pl-PL")' if layout.decimal_comma else ")")))
    return steps


# =============================================================================
# Słownik kodów (np. metadane stacji)
# =============================================================================
@dataclass
class LookupResult:
    total: int                      # ile różnych kodów jest w danych
    matched: int                    # ile znaleziono w słowniku
    old_code_mapping: dict          # stary kod -> aktualny kod
    unmatched: list[str]            # kody, których nie ma nigdzie


def check_codes(codes: pd.Series, current: pd.Series, old: pd.Series | None = None) -> LookupResult:
    """Sprawdza, które kody z danych występują w słowniku.

    Jeśli podamy kolumnę ze starymi kodami, kody nieznalezione wśród aktualnych
    próbujemy dopasować po starym kodzie (GIOŚ z czasem zmieniał kody stacji).
    """
    unique = set(codes.dropna().astype(str).str.strip())
    current_set = set(current.dropna().astype(str).str.strip())
    missing = sorted(unique - current_set)

    mapping = {}
    if old is not None:
        pairs = pd.DataFrame({"old": old, "new": current}).dropna()
        old_to_new = dict(zip(pairs["old"].astype(str).str.strip(), pairs["new"].astype(str).str.strip()))
        mapping = {code: old_to_new[code] for code in missing if code in old_to_new}

    unmatched = [code for code in missing if code not in mapping]
    return LookupResult(len(unique), len(unique) - len(missing), mapping, unmatched)
