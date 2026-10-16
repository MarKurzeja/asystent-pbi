"""
Kroki czyszczenia danych i generowanie kodu Power Query (M).

Każdy krok ma dwie "twarze":
- wersję w pandas (apply_steps)  -> podgląd "przed i po" w aplikacji,
- wersję w języku M (steps_to_m) -> kod, który Power BI wykona na oryginalnym pliku.
Obie wersje robią dokładnie to samo, więc to, co widzisz w podglądzie,
dostaniesz potem w Power BI.
"""

from dataclasses import dataclass, field

import pandas as pd

from i18n import t
from profiling import (MISSING_PLACEHOLDERS, NUMBER_TYPES, THOUSANDS_SEP,
                       DatasetProfile, normalize_text, to_number)

# Kolejność, w jakiej kroki są wykonywane (niezależnie od kolejności zaznaczania).
STEP_ORDER = ["trim", "nulls", "variants", "numbers", "dates", "nip", "duplicates"]


@dataclass
class Step:
    kind: str                                   # rodzaj kroku, np. "trim", "dates"
    columns: list[str] = field(default_factory=list)
    params: dict = field(default_factory=dict)  # ustawienia kroku, np. mapa zamian

    @property
    def key(self) -> str:
        """Unikalny identyfikator kroku (potrzebny dla checkboxów w Streamlit)."""
        return self.kind + ":" + ",".join(self.columns)

    # --- Opisy kroków w wybranym języku ---
    def label(self, lang: str) -> str:
        col = self.columns[0] if self.columns else ""
        if self.kind == "numbers":
            key = "step_numbers_int_label" if self.params["integer"] else "step_numbers_dec_label"
            return t(key, lang, col=col)
        return t(f"step_{self.kind}_label", lang, col=col)

    def reason(self, lang: str) -> str:
        p = self.params
        if self.kind == "trim":
            return t("step_trim_reason", lang, columns=", ".join(self.columns))
        if self.kind == "variants":
            examples = ", ".join(f"„{k}” → „{v}”" for k, v in list(p["mapping"].items())[:3])
            return t("step_variants_reason", lang, n=len(p["mapping"]), examples=examples)
        if self.kind == "numbers":
            return t("step_numbers_reason", lang, type=t("type_" + p["type"], lang), culture=p["culture"])
        if self.kind == "duplicates":
            return t("step_duplicates_reason", lang, n=p["n"])
        return t(f"step_{self.kind}_reason", lang)


def _text_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if pd.api.types.is_string_dtype(df[c])]


# =============================================================================
# 1. PROPONOWANIE KROKÓW
# =============================================================================
def suggest_steps(df: pd.DataFrame, profile: DatasetProfile) -> list[Step]:
    """Na podstawie profilu danych proponuje listę kroków czyszczenia."""
    steps: list[Step] = []
    text_cols = _text_columns(df)
    by_name = {c.name: c for c in profile.columns}

    # Zbędne spacje
    trim_cols = [col for col in text_cols
                 if (df[col].dropna() != df[col].dropna().str.strip()).any()]
    if trim_cols:
        steps.append(Step("trim", trim_cols))

    # Puste komórki i "brak" -> null (zawsze proponujemy dla plików tekstowych)
    if text_cols:
        steps.append(Step("nulls", text_cols))

    for col in text_cols:
        info = by_name.get(col)
        if info is None:
            continue
        values = df[col].dropna().str.strip()
        values = values[~values.str.lower().isin(MISSING_PLACEHOLDERS)]

        # Warianty tej samej wartości ("Kraków" / "krakow" / "KRAKÓW")
        if info.detected_type == "text" and "nip" not in col.lower() and 0 < values.nunique() <= 200:
            mapping = {}
            for _, group in values.groupby(values.map(normalize_text)):
                counts = group.value_counts()
                if len(counts) > 1:
                    canonical = counts.index[0]  # najczęstszy zapis wygrywa
                    mapping.update({v: canonical for v in counts.index[1:]})
            if mapping:
                steps.append(Step("variants", [col], {"mapping": mapping}))

        # Liczby zapisane jako tekst
        if info.detected_type in NUMBER_TYPES:
            steps.append(Step("numbers", [col], {
                "type": info.detected_type,
                "integer": info.detected_type == "integer",
                "culture": "en-US" if info.detected_type == "decimal_dot" else "pl-PL",
            }))

        # Daty
        if info.detected_type.startswith("date"):
            steps.append(Step("dates", [col]))

        # NIP - zostawiamy same cyfry
        if "nip" in col.lower():
            steps.append(Step("nip", [col]))

    # Duplikaty
    if profile.duplicate_rows:
        steps.append(Step("duplicates", params={"n": profile.duplicate_rows}))

    # Pokazujemy kroki w tej samej kolejności, w jakiej będą wykonywane.
    return sorted(steps, key=lambda s: STEP_ORDER.index(s.kind))


# =============================================================================
# 2. WYKONANIE KROKÓW W PANDAS (podgląd)
# =============================================================================
DATE_FORMATS = {".": "%d.%m.%Y", "/": "%d/%m/%Y", "-": "%Y-%m-%d"}


def _parse_dates(s: pd.Series) -> pd.Series:
    """Rozpoznaje format każdej daty po znaku, który ją dzieli (. / -)."""
    text = s.str.strip()
    result = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    for sep, fmt in DATE_FORMATS.items():
        mask = text.str.contains(sep, regex=False, na=False)
        result[mask] = pd.to_datetime(text[mask], format=fmt, errors="coerce")
    return result


def apply_steps(df: pd.DataFrame, steps: list[Step]) -> pd.DataFrame:
    """Wykonuje kroki na kopii danych i zwraca wyczyszczoną tabelę."""
    out = df.copy()
    for step in sorted(steps, key=lambda s: STEP_ORDER.index(s.kind)):
        for col in step.columns:
            s = out[col]
            if step.kind == "trim":
                out[col] = s.str.strip()
            elif step.kind == "nulls":
                is_missing = s.str.strip().str.lower().isin(MISSING_PLACEHOLDERS | {""})
                out[col] = s.mask(is_missing)
            elif step.kind == "variants":
                out[col] = s.replace(step.params["mapping"])
            elif step.kind == "numbers":
                numbers = to_number(s, step.params["type"])
                out[col] = numbers.astype("Int64") if step.params["integer"] else numbers
            elif step.kind == "dates":
                out[col] = _parse_dates(s)
            elif step.kind == "nip":
                out[col] = s.str.replace(r"\D", "", regex=True)
        if step.kind == "duplicates":
            out = out.drop_duplicates().reset_index(drop=True)
    return out


# =============================================================================
# 3. GENEROWANIE KODU POWER QUERY (M)
# =============================================================================
ENCODING_CODES = {"utf-8-sig": 65001, "utf-8": 65001, "cp1250": 1250, "iso-8859-2": 28592}


def m_text(value: str) -> str:
    """Tekst w języku M: w cudzysłowie, a cudzysłów w środku podwajamy."""
    return '"' + str(value).replace('"', '""') + '"'


def m_name(value: str) -> str:
    """Nazwa kroku w M. Zapis #"..." pozwala na spacje i polskie znaki."""
    return "#" + m_text(value)


def m_list(values) -> str:
    return "{" + ", ".join(m_text(v) for v in values) + "}"


def steps_to_m(steps: list[Step], file_path: str, file_type: str,
               encoding: str | None, separator: str | None, lang: str = "pl") -> str:
    """Zamienia listę kroków na gotowe zapytanie Power Query.

    Parametr lang decyduje o języku nazw kroków widocznych w Power BI
    (panel Applied Steps), np. "Bez duplikatów" albo "Removed duplicates".
    """
    lines: list[tuple[str, str]] = []   # (nazwa kroku, wyrażenie)

    # --- Źródło ---
    source, headers = t("m_source", lang), t("m_headers", lang)
    if file_type == "excel":
        lines.append((source, f"Excel.Workbook(File.Contents({m_text(file_path)}), null, true){{0}}[Data]"))
    else:
        delimiter = '"#(tab)"' if separator == "\t" else m_text(separator)
        code = ENCODING_CODES.get(encoding, 65001)
        lines.append((source, f"Csv.Document(File.Contents({m_text(file_path)}), "
                              f"[Delimiter={delimiter}, Encoding={code}, QuoteStyle=QuoteStyle.Csv])"))
    lines.append((headers, f"Table.PromoteHeaders({m_name(source)}, [PromoteAllScalars=true])"))
    prev = headers

    def add(name: str, expr: str) -> None:
        nonlocal prev
        lines.append((name, expr.replace("PREV", m_name(prev))))
        prev = name

    # --- Kroki czyszczenia ---
    for step in sorted(steps, key=lambda s: STEP_ORDER.index(s.kind)):
        col = step.columns[0] if step.columns else ""

        if step.kind == "trim":
            pairs = ", ".join(f"{{{m_text(c)}, each if _ is text then Text.Trim(_) else _}}" for c in step.columns)
            add(t("m_trim", lang), f"Table.TransformColumns(PREV, {{{pairs}}})")

        elif step.kind == "nulls":
            placeholders = m_list(sorted(MISSING_PLACEHOLDERS | {""}))
            add(t("m_nulls", lang),
                f"Table.TransformColumns(PREV, List.Transform({m_list(step.columns)}, (col) => "
                f"{{col, (x) => if x is text and List.Contains({placeholders}, Text.Lower(Text.Trim(x))) "
                f"then null else x}}))")

        elif step.kind == "variants":
            map_name = t("m_map", lang, col=col)
            mapping = ", ".join(f"{m_name(k)} = {m_text(v)}" for k, v in step.params["mapping"].items())
            lines.append((map_name, f"[{mapping}]"))
            add(t("m_unified", lang, col=col),
                f"Table.TransformColumns(PREV, {{{{{m_text(col)}, "
                f"each if _ is text then Record.FieldOrDefault({m_name(map_name)}, _, _) else _}}}})")

        elif step.kind == "numbers":
            m_type = "Int64.Type" if step.params["integer"] else "type number"
            add(t("m_no_spaces", lang, col=col),
                f'Table.TransformColumns(PREV, {{{{{m_text(col)}, '
                f'each if _ is text then Text.Remove(_, {{" ", "#(00A0)"}}) else _}}}})')
            add(t("m_number", lang, col=col),
                f"Table.TransformColumnTypes(PREV, {{{{{m_text(col)}, {m_type}}}}}, {m_text(step.params['culture'])})")

        elif step.kind == "dates":
            add(t("m_date", lang, col=col),
                f'Table.TransformColumns(PREV, {{{{{m_text(col)}, each if _ is text then ('
                f'if Text.Contains(_, ".") then Date.FromText(_, [Format="d.M.yyyy"]) '
                f'else if Text.Contains(_, "/") then Date.FromText(_, [Format="d/M/yyyy"]) '
                f'else Date.FromText(_, [Format="yyyy-MM-dd"])) else _, type date}}}})')

        elif step.kind == "nip":
            add(t("m_nip", lang, col=col),
                f'Table.TransformColumns(PREV, {{{{{m_text(col)}, '
                f'each if _ is text then Text.Select(_, {{"0".."9"}}) else _, type text}}}})')

        elif step.kind == "duplicates":
            add(t("m_distinct", lang), "Table.Distinct(PREV)")

    # --- Składanie całości ---
    body = ",\n".join(f"    {m_name(name)} = {expr}" for name, expr in lines)
    return f"let\n{body}\nin\n    {m_name(prev)}"
