"""
Etap 3: kroki czyszczenia danych i generowanie kodu Power Query (M).

Każdy krok ma dwie "twarze":
- wersję w pandas (apply_steps)  -> podgląd "przed i po" w aplikacji,
- wersję w języku M (steps_to_m) -> kod, który Power BI wykona na oryginalnym pliku.
Obie wersje robią dokładnie to samo, więc to, co widzisz w podglądzie,
dostaniesz potem w Power BI.
"""

from dataclasses import dataclass, field

import pandas as pd

from profiling import MISSING_PLACEHOLDERS, NUMBER_TYPES, DatasetProfile, _normalize_text

# Kolejność, w jakiej kroki są wykonywane (niezależnie od kolejności zaznaczania).
STEP_ORDER = ["trim", "puste", "warianty", "liczby", "daty", "nip", "duplikaty"]


@dataclass
class Step:
    kind: str                     # rodzaj kroku, np. "trim", "daty"
    label: str                    # krótki opis widoczny przy checkboxie
    reason: str                   # dlaczego ten krok jest proponowany
    columns: list[str] = field(default_factory=list)
    params: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        """Unikalny identyfikator kroku (potrzebny dla checkboxów w Streamlit)."""
        return self.kind + ":" + ",".join(self.columns)


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
    trim_cols = []
    for col in text_cols:
        values = df[col].dropna()
        if (values != values.str.strip()).any():
            trim_cols.append(col)
    if trim_cols:
        steps.append(Step("trim", "Usuń zbędne spacje na początku i końcu tekstu",
                          "Kolumny: " + ", ".join(trim_cols), trim_cols))

    # Puste komórki i "brak" -> null (zawsze proponujemy dla plików tekstowych)
    if text_cols:
        steps.append(Step("puste", "Zamień puste komórki i słowa typu „brak”, „-” na brak danych (null)",
                          "Power BI traktuje pusty tekst i słowo „brak” jak zwykłą wartość - "
                          "po zamianie na null poprawnie policzy średnie i sumy.", text_cols))

    for col in text_cols:
        info = by_name.get(col)
        if info is None:
            continue
        values = df[col].dropna().str.strip()
        values = values[~values.str.lower().isin(MISSING_PLACEHOLDERS)]

        # Warianty tej samej wartości ("Kraków" / "krakow" / "KRAKÓW")
        if info.detected_type == "tekst" and "nip" not in col.lower() and 0 < values.nunique() <= 200:
            mapping = {}
            for _, group in values.groupby(values.map(_normalize_text)):
                counts = group.value_counts()
                if len(counts) > 1:
                    canonical = counts.index[0]  # najczęstszy zapis wygrywa
                    mapping.update({v: canonical for v in counts.index[1:]})
            if mapping:
                example = ", ".join(f"„{k}” → „{v}”" for k, v in list(mapping.items())[:3])
                steps.append(Step("warianty", f"Ujednolić zapis wartości w kolumnie „{col}”",
                                  f"{len(mapping)} zamian, np. {example}. Wybieramy najczęstszy zapis.",
                                  [col], {"mapping": mapping}))

        # Liczby zapisane jako tekst
        if info.detected_type in NUMBER_TYPES:
            integer = info.detected_type == "liczba całkowita"
            culture = "en-US" if info.detected_type == "liczba (kropka)" else "pl-PL"
            label = "liczby całkowite" if integer else "liczby dziesiętne"
            steps.append(Step("liczby", f"Zamień „{col}” na {label}",
                              f"Wykryty format: {info.detected_type}. Usuwamy spacje tysięcy "
                              f"i konwertujemy z ustawieniami regionalnymi {culture}.",
                              [col], {"integer": integer, "culture": culture}))

        # Daty
        if info.detected_type.startswith("data"):
            steps.append(Step("daty", f"Zamień „{col}” na datę",
                              "Rozpoznajemy formaty dd.mm.rrrr, dd/mm/rrrr i rrrr-mm-dd "
                              "i zamieniamy wszystkie na jeden typ: data.", [col]))

        # NIP - zostawiamy same cyfry
        if "nip" in col.lower():
            steps.append(Step("nip", f"Ujednolić format NIP w kolumnie „{col}”",
                              "Usuwamy myślniki, spacje i prefiks PL - zostaje 10 cyfr. "
                              "Błędne numery (zła cyfra kontrolna) trzeba sprawdzić ręcznie.", [col]))

    # Duplikaty
    if profile.duplicate_rows:
        steps.append(Step("duplikaty", "Usuń zduplikowane wiersze",
                          f"W surowych danych jest {profile.duplicate_rows} duplikatów. "
                          "Usuwamy je na końcu, bo po czyszczeniu może ich być więcej."))

    # Pokazujemy kroki w tej samej kolejności, w jakiej będą wykonywane.
    return sorted(steps, key=lambda s: STEP_ORDER.index(s.kind))


# =============================================================================
# 2. WYKONANIE KROKÓW W PANDAS (podgląd)
# =============================================================================
def _parse_date(value):
    if pd.isna(value):
        return pd.NaT
    text = str(value).strip()
    if "." in text:
        fmt = "%d.%m.%Y"
    elif "/" in text:
        fmt = "%d/%m/%Y"
    else:
        fmt = "%Y-%m-%d"
    return pd.to_datetime(text, format=fmt, errors="coerce")


def apply_steps(df: pd.DataFrame, steps: list[Step]) -> pd.DataFrame:
    """Wykonuje kroki na kopii danych i zwraca wyczyszczoną tabelę."""
    out = df.copy()
    for step in sorted(steps, key=lambda s: STEP_ORDER.index(s.kind)):
        for col in step.columns:
            s = out[col]
            if step.kind == "trim":
                out[col] = s.str.strip()
            elif step.kind == "puste":
                is_missing = s.str.strip().str.lower().isin(MISSING_PLACEHOLDERS | {""})
                out[col] = s.mask(is_missing)
            elif step.kind == "warianty":
                out[col] = s.replace(step.params["mapping"])
            elif step.kind == "liczby":
                cleaned = s.str.replace("[ \u00a0]", "", regex=True)
                if step.params["culture"] == "pl-PL":
                    cleaned = cleaned.str.replace(",", ".", regex=False)
                numbers = pd.to_numeric(cleaned, errors="coerce")
                out[col] = numbers.astype("Int64") if step.params["integer"] else numbers
            elif step.kind == "daty":
                out[col] = pd.to_datetime(s.map(_parse_date))
            elif step.kind == "nip":
                out[col] = s.str.replace(r"\D", "", regex=True)
        if step.kind == "duplikaty":
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
               encoding: str | None, separator: str | None) -> str:
    """Zamienia listę kroków na gotowe zapytanie Power Query."""
    lines: list[tuple[str, str]] = []   # (nazwa kroku, wyrażenie)

    # --- Źródło ---
    if file_type == "excel":
        lines.append(("Źródło", f"Excel.Workbook(File.Contents({m_text(file_path)}), null, true){{0}}[Data]"))
    else:
        delimiter = '"#(tab)"' if separator == "\t" else m_text(separator)
        code = ENCODING_CODES.get(encoding, 65001)
        lines.append(("Źródło", f"Csv.Document(File.Contents({m_text(file_path)}), "
                                f"[Delimiter={delimiter}, Encoding={code}, QuoteStyle=QuoteStyle.Csv])"))
    lines.append(("Nagłówki", f"Table.PromoteHeaders({m_name('Źródło')}, [PromoteAllScalars=true])"))
    prev = "Nagłówki"

    def add(name: str, expr: str) -> None:
        nonlocal prev
        lines.append((name, expr.replace("PREV", m_name(prev))))
        prev = name

    # --- Kroki czyszczenia ---
    for step in sorted(steps, key=lambda s: STEP_ORDER.index(s.kind)):
        if step.kind == "trim":
            pairs = ", ".join(f"{{{m_text(c)}, each if _ is text then Text.Trim(_) else _}}" for c in step.columns)
            add("Usunięte spacje", f"Table.TransformColumns(PREV, {{{pairs}}})")

        elif step.kind == "puste":
            placeholders = m_list(sorted(MISSING_PLACEHOLDERS | {""}))
            add("Puste na null",
                f"Table.TransformColumns(PREV, List.Transform({m_list(step.columns)}, (kolumna) => "
                f"{{kolumna, (x) => if x is text and List.Contains({placeholders}, Text.Lower(Text.Trim(x))) "
                f"then null else x}}))")

        elif step.kind == "warianty":
            col = step.columns[0]
            mapping = ", ".join(f"{m_name(k)} = {m_text(v)}" for k, v in step.params["mapping"].items())
            lines.append((f"Mapa: {col}", f"[{mapping}]"))
            add(f"Ujednolicone: {col}",
                f"Table.TransformColumns(PREV, {{{{{m_text(col)}, "
                f"each if _ is text then Record.FieldOrDefault({m_name('Mapa: ' + col)}, _, _) else _}}}})")

        elif step.kind == "liczby":
            col = step.columns[0]
            m_type = "Int64.Type" if step.params["integer"] else "type number"
            add(f"Bez spacji: {col}",
                f'Table.TransformColumns(PREV, {{{{{m_text(col)}, '
                f'each if _ is text then Text.Remove(_, {{" ", "#(00A0)"}}) else _}}}})')
            add(f"Liczba: {col}",
                f"Table.TransformColumnTypes(PREV, {{{{{m_text(col)}, {m_type}}}}}, {m_text(step.params['culture'])})")

        elif step.kind == "daty":
            col = step.columns[0]
            add(f"Data: {col}",
                f'Table.TransformColumns(PREV, {{{{{m_text(col)}, each if _ is text then ('
                f'if Text.Contains(_, ".") then Date.FromText(_, [Format="d.M.yyyy"]) '
                f'else if Text.Contains(_, "/") then Date.FromText(_, [Format="d/M/yyyy"]) '
                f'else Date.FromText(_, [Format="yyyy-MM-dd"])) else _, type date}}}})')

        elif step.kind == "nip":
            col = step.columns[0]
            add(f"NIP: {col}",
                f'Table.TransformColumns(PREV, {{{{{m_text(col)}, '
                f'each if _ is text then Text.Select(_, {{"0".."9"}}) else _, type text}}}})')

        elif step.kind == "duplikaty":
            add("Bez duplikatów", "Table.Distinct(PREV)")

    # --- Składanie całości ---
    body = ",\n".join(f"    {m_name(name)} = {expr}" for name, expr in lines)
    return f"let\n{body}\nin\n    {m_name(prev)}"