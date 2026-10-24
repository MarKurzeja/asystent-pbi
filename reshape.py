"""
Wide-layout files with a multi-row header.

Example - a GIOŚ file with PM10 measurements:

    Nr                1             2             ...
    Kod stacji        DsGlogWiStwo  DsJaworMOB    ...   <- key row
    Wskaźnik          PM10          PM10          ...   <- constant
    Jednostka         ug/m3         ug/m3         ...   <- constant
    2019-01-01        13.71         13.15         ...   <- data starts here
    2019-01-02         8.28         11.26         ...

This layout is easy for people to read, but Power BI needs a long format:
one row = one date, one station, one value. This module:
1. detects the layout (detect_wide_layout),
2. unpivots the table in pandas (unpivot) - for the preview,
3. generates the same step in M (wide_to_m) - for Power BI.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd

from i18n import t

MAX_HEADER_ROWS = 20      # headers longer than 20 rows are treated as unusual
MIN_VALUE_COLUMNS = 3     # a wide layout needs several value columns
DATE_TEXT = re.compile(r"^\d{1,2}[./]\d{1,2}[./]\d{4}$|^\d{4}-\d{2}-\d{2}")
# Number stored as text with a decimal comma, e.g. "3,878" (some GIOŚ files up to 2018)
COMMA_NUMBER = re.compile(r"^-?\d+(,\d+)?$")


@dataclass
class WideLayout:
    data_start: int                  # row where the data starts
    key_row: int                     # row with column keys (e.g. station codes)
    key_label: str                   # its label, e.g. "Kod stacji"
    keys: list[str]                  # the keys, e.g. ["DsGlogWiStwo", ...]
    constants: dict[str, int] = field(default_factory=dict)  # label -> row, e.g. {"Wskaźnik": 2}
    decimal_comma: bool = False      # True when values are text with a decimal comma ("3,878")

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
    """Detects a raw sheet with a multi-row header and value columns.

    Rules (deliberately simple and predictable):
    - first column: labels (text) first, then dates - the first date marks the start of data,
    - one header row has a distinct, non-empty value in every column (the keys, e.g. station codes),
    - header rows with a single value across all columns are constants (e.g. "Wskaźnik: PM10"),
    - the data body is mostly numeric.
    If any rule fails, None is returned and the file is treated as a normal table.
    """
    if raw is None or raw.shape[1] < MIN_VALUE_COLUMNS + 1 or raw.shape[0] < 3:
        return None

    first_col = raw.iloc[:, 0].tolist()
    data_start = next((i for i, v in enumerate(first_col[:MAX_HEADER_ROWS + 1]) if _is_date(v)), None)
    if not data_start:   # None or 0 (no header rows)
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

    body = raw.iloc[data_start:, 1:].stack().dropna()   # non-empty cells only
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
    """Column names after unpivoting: (date column, value column)."""
    return t("col_name_date", lang), t("col_name_value", lang)


def unpivot(raw: pd.DataFrame, layout: WideLayout, lang: str) -> pd.DataFrame:
    """Unpivots a wide table into long format (pandas, for the in-app preview).

    Empty cells (no measurement) are dropped - exactly like Table.UnpivotOtherColumns
    in Power Query, so row counts match.
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
    """M steps that do in Power BI what unpivot() does in pandas.

    Returns a list of (step name, expression). The first expressions refer to the
    source step by name (source_name), later ones to the previous step.
    """
    from cleaning import m_name, m_text   # local import avoids a circular import

    date_col, value_col = column_names(layout, lang)
    src = m_name(source_name)
    keys, body, renamed, unpivoted = (t("m_wide_keys", lang), t("m_wide_data", lang),
                                      t("m_wide_renamed", lang), t("m_wide_unpivoted", lang))
    steps = [
        # Keys are read from the file (not hard-coded), so the same code works for
        # other years even if the list of stations changes.
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
                  # "3,878" converts to a number only with the Polish locale.
                  + (', "pl-PL")' if layout.decimal_comma else ")")))
    return steps


# =============================================================================
# Code dictionary (e.g. station metadata)
# =============================================================================
@dataclass
class LookupResult:
    total: int                      # distinct codes in the data
    matched: int                    # codes found in the dictionary
    old_code_mapping: dict          # old code -> current code
    unmatched: list[str]            # codes found nowhere


def check_codes(codes: pd.Series, current: pd.Series, old: pd.Series | None = None) -> LookupResult:
    """Checks which codes in the data exist in the dictionary.

    If an old-code column is given, codes missing from the current ones are matched
    through it (GIOŚ has renamed stations over the years).
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
