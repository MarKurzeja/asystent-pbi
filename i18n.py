"""
Tłumaczenia interfejsu (angielski / polski).

Każdy tekst ma klucz, np. "app_title", i wersję w dwóch językach.
Funkcja t("app_title", "en") zwraca tekst w wybranym języku.
Teksty mogą mieć "dziury" w nawiasach klamrowych, np. {n},
które wypełniamy wartościami: t("rows_removed", "pl", n=6).
"""

LANGUAGES = {"en": "English", "pl": "Polski"}

TEXTS: dict[str, dict[str, str]] = {
    # --- Aplikacja ---------------------------------------------------------
    "app_title": {"en": "Data Assistant for Power BI", "pl": "Asystent danych dla Power BI"},
    "app_caption": {
        "en": "Upload a CSV or Excel file to see what needs fixing before you load it into Power BI. "
              "Built with Polish data formats in mind.",
        "pl": "Wrzuć plik CSV lub Excel, a zobaczysz, co trzeba poprawić przed wczytaniem do Power BI.",
    },
    "language": {"en": "Language", "pl": "Język"},
    "choose_file": {"en": "Choose a file", "pl": "Wybierz plik"},
    "no_file_hint": {
        "en": "No file at hand? Run `python data/generate_test_data.py` and upload `data/zamowienia_brudne.csv`.",
        "pl": "Nie masz pliku pod ręką? Uruchom `python data/generate_test_data.py` i wrzuć `data/zamowienia_brudne.csv`.",
    },
    "load_error": {"en": "Could not read the file: {error}", "pl": "Nie udało się wczytać pliku: {error}"},
    "loaded_csv": {
        "en": "CSV file loaded · encoding: **{encoding}** · separator: **{separator}**",
        "pl": "Wczytano plik CSV · kodowanie: **{encoding}** · separator: **{separator}**",
    },
    "loaded_excel": {"en": "Excel file loaded", "pl": "Wczytano plik Excel"},
    "sep_;": {"en": "semicolon", "pl": "średnik"},
    "sep_,": {"en": "comma", "pl": "przecinek"},
    "sep_\t": {"en": "tab", "pl": "tabulator"},
    "sep_|": {"en": "pipe", "pl": "kreska"},
    "preview_raw": {"en": "Data preview (first 20 rows)", "pl": "Podgląd danych (pierwsze 20 wierszy)"},

    # --- Raport jakości -------------------------------------------------------
    "metric_rows": {"en": "Rows", "pl": "Wiersze"},
    "metric_columns": {"en": "Columns", "pl": "Kolumny"},
    "metric_duplicates": {"en": "Duplicate rows", "pl": "Zduplikowane wiersze"},
    "metric_issues": {"en": "Issues found", "pl": "Wykryte problemy"},
    "columns_header": {"en": "Columns", "pl": "Kolumny"},
    "col_name": {"en": "Column", "pl": "Kolumna"},
    "col_type": {"en": "Detected type", "pl": "Wykryty typ"},
    "col_match": {"en": "Type match", "pl": "Zgodność z typem"},
    "col_missing": {"en": "Missing", "pl": "Braki"},
    "col_unique": {"en": "Unique", "pl": "Unikalne"},
    "col_issues": {"en": "Issues", "pl": "Problemy"},
    "col_examples": {"en": "Examples", "pl": "Przykłady"},
    "issues_header": {"en": "Issue details", "pl": "Szczegóły problemów"},
    "duplicates_warning": {
        "en": "The table contains {n} duplicate rows.",
        "pl": "Tabela zawiera {n} zduplikowanych wierszy.",
    },
    "no_issues": {"en": "No column issues found.", "pl": "Nie znaleziono problemów w kolumnach."},
    "download_report": {"en": "Download quality report (CSV)", "pl": "Pobierz raport jakości (CSV)"},
    "report_file": {"en": "quality_report.csv", "pl": "raport_jakosci.csv"},
    "report_col_column": {"en": "column", "pl": "kolumna"},
    "report_col_type": {"en": "type", "pl": "typ"},
    "report_col_issue": {"en": "issue", "pl": "problem"},

    # --- Typy danych ------------------------------------------------------------
    "type_integer": {"en": "integer", "pl": "liczba całkowita"},
    "type_decimal_comma": {"en": "decimal (comma)", "pl": "liczba (przecinek)"},
    "type_decimal_dot": {"en": "decimal (dot)", "pl": "liczba (kropka)"},
    "type_date_dot": {"en": "date dd.mm.yyyy", "pl": "data dd.mm.rrrr"},
    "type_date_iso": {"en": "date yyyy-mm-dd", "pl": "data rrrr-mm-dd"},
    "type_date_slash": {"en": "date dd/mm/yyyy", "pl": "data dd/mm/rrrr"},
    "type_date_mixed": {"en": "date (mixed formats)", "pl": "data (mieszane formaty)"},
    "type_postcode": {"en": "Polish postcode", "pl": "kod pocztowy"},
    "type_email": {"en": "e-mail", "pl": "e-mail"},
    "type_text": {"en": "text", "pl": "tekst"},
    "type_empty": {"en": "empty", "pl": "pusta"},

    # --- Komunikaty o problemach ----------------------------------------------
    # Formuła "Opis: liczba" omija polską odmianę ("1 wartość ma" / "5 wartości ma").
    "issue_missing": {"en": "Missing values: {pct}", "pl": "Braki danych: {pct}"},
    "issue_placeholders": {
        "en": "Missing data written as a word: {n} (e.g. {examples})",
        "pl": "Brak danych zapisany słowem: {n} (np. {examples})",
    },
    "issue_empty_column": {"en": "The column is completely empty", "pl": "Kolumna jest całkowicie pusta"},
    "issue_spaces": {"en": "Leading or trailing spaces: {n}", "pl": "Zbędne spacje na początku lub końcu: {n}"},
    "issue_mixed_separators": {
        "en": "Numbers written with both a comma and a dot as the decimal separator",
        "pl": "Liczby zapisane raz z przecinkiem, raz z kropką",
    },
    "issue_mixed_dates": {"en": "Dates in several formats: {formats}", "pl": "Daty w kilku formatach: {formats}"},
    "issue_type_mismatch": {
        "en": "Values not matching the type „{type}”: {n} (e.g. {examples})",
        "pl": "Wartości niepasujące do typu „{type}”: {n} (np. {examples})",
    },
    "issue_comma_decimal": {
        "en": "Decimal comma - needs conversion with Polish regional settings (pl-PL)",
        "pl": "Liczby z przecinkiem dziesiętnym - wymagają konwersji (ustawienia regionalne pl-PL)",
    },
    "issue_outliers": {"en": "Outliers: {n} (e.g. {example})", "pl": "Wartości odstające: {n} (np. {example})"},
    "issue_negatives": {
        "en": "Negative values: {n} - check whether they are possible",
        "pl": "Wartości ujemne: {n} - sprawdź, czy to możliwe",
    },
    "issue_variants": {
        "en": "Groups of values written in several ways: {n} (e.g. {examples})",
        "pl": "Grupy wartości zapisanych na kilka sposobów: {n} (np. {examples})",
    },
    "issue_nip_invalid": {
        "en": "Invalid NIP (Polish tax ID) numbers - wrong check digit or length: {n} (e.g. {examples})",
        "pl": "Niepoprawne numery NIP (zła cyfra kontrolna lub długość): {n} (np. {examples})",
    },
    "issue_nip_formats": {
        "en": "Different NIP formats ({n}): {formats}",
        "pl": "Różne formaty zapisu NIP ({n}): {formats}",
    },

    # --- Plan czyszczenia -------------------------------------------------------
    "plan_header": {"en": "Cleaning plan", "pl": "Plan czyszczenia"},
    "plan_caption": {
        "en": "Select the steps you want to apply. The preview and the Power Query code update automatically.",
        "pl": "Zaznacz kroki, które chcesz wykonać. Podgląd i kod Power Query zmienią się automatycznie.",
    },
    "plan_outliers_note": {
        "en": "Outliers (e.g. an order for 400 items) are deliberately not removed automatically - "
              "it may be an error or a genuine large order. That decision belongs to the analyst.",
        "pl": "Wartości odstające (np. zamówienie na 400 sztuk) celowo nie są usuwane automatycznie - "
              "to może być błąd albo prawdziwe duże zamówienie. Taką decyzję podejmuje analityk.",
    },
    "step_trim_label": {"en": "Remove leading and trailing spaces", "pl": "Usuń zbędne spacje na początku i końcu tekstu"},
    "step_trim_reason": {"en": "Columns: {columns}", "pl": "Kolumny: {columns}"},
    "step_nulls_label": {
        "en": "Turn blank cells and words like „brak”, „-”, „n/a” into missing values (null)",
        "pl": "Zamień puste komórki i słowa typu „brak”, „-” na brak danych (null)",
    },
    "step_nulls_reason": {
        "en": "Power BI treats empty text and the word „brak” as a normal value - "
              "as null they are correctly skipped in averages and totals.",
        "pl": "Power BI traktuje pusty tekst i słowo „brak” jak zwykłą wartość - "
              "po zamianie na null poprawnie policzy średnie i sumy.",
    },
    "step_variants_label": {"en": "Unify spelling in column „{col}”", "pl": "Ujednolić zapis wartości w kolumnie „{col}”"},
    "step_variants_reason": {
        "en": "{n} replacements, e.g. {examples}. The most frequent spelling wins.",
        "pl": "{n} zamian, np. {examples}. Wybieramy najczęstszy zapis.",
    },
    "step_numbers_int_label": {"en": "Convert „{col}” to whole numbers", "pl": "Zamień „{col}” na liczby całkowite"},
    "step_numbers_dec_label": {"en": "Convert „{col}” to decimal numbers", "pl": "Zamień „{col}” na liczby dziesiętne"},
    "step_numbers_reason": {
        "en": "Detected format: {type}. Thousands separators are removed and the text is converted using {culture} settings.",
        "pl": "Wykryty format: {type}. Usuwamy spacje tysięcy i konwertujemy z ustawieniami regionalnymi {culture}.",
    },
    "step_dates_label": {"en": "Convert „{col}” to a date", "pl": "Zamień „{col}” na datę"},
    "step_dates_reason": {
        "en": "Formats dd.mm.yyyy, dd/mm/yyyy and yyyy-mm-dd are recognised and converted to a single date type.",
        "pl": "Rozpoznajemy formaty dd.mm.rrrr, dd/mm/rrrr i rrrr-mm-dd i zamieniamy wszystkie na jeden typ: data.",
    },
    "step_nip_label": {"en": "Standardise the NIP format in „{col}”", "pl": "Ujednolić format NIP w kolumnie „{col}”"},
    "step_nip_reason": {
        "en": "Dashes, spaces and the PL prefix are removed, leaving 10 digits. "
              "Invalid numbers (wrong check digit) need to be reviewed manually.",
        "pl": "Usuwamy myślniki, spacje i prefiks PL - zostaje 10 cyfr. "
              "Błędne numery (zła cyfra kontrolna) trzeba sprawdzić ręcznie.",
    },
    "step_duplicates_label": {"en": "Remove duplicate rows", "pl": "Usuń zduplikowane wiersze"},
    "step_duplicates_reason": {
        "en": "The raw data contains {n} duplicates. They are removed last, because cleaning can reveal more.",
        "pl": "W surowych danych jest {n} duplikatów. Usuwamy je na końcu, bo po czyszczeniu może ich być więcej.",
    },

    # --- Podgląd -----------------------------------------------------------------
    "preview_header": {"en": "Preview: before and after", "pl": "Podgląd: przed i po"},
    "rows_before": {"en": "Rows before", "pl": "Wiersze przed"},
    "rows_after": {"en": "Rows after", "pl": "Wiersze po"},
    "tab_before": {"en": "Before cleaning", "pl": "Przed czyszczeniem"},
    "tab_after": {"en": "After cleaning", "pl": "Po czyszczeniu"},

    # --- Kod Power Query ----------------------------------------------------------
    "code_header": {"en": "Power Query code", "pl": "Kod Power Query"},
    "path_label": {"en": "File path on the computer running Power BI", "pl": "Ścieżka do pliku na komputerze z Power BI"},
    "path_help": {
        "en": "Power BI needs to know where to load the original file from. Enter a Windows path.",
        "pl": "Power BI musi wiedzieć, skąd wczytać oryginalny plik. Wpisz ścieżkę z Windowsa.",
    },
    "path_default_folder": {"en": "C:\\data\\", "pl": "C:\\dane\\"},
    "download_code": {"en": "Download code (.pq)", "pl": "Pobierz kod (.pq)"},
    "code_file": {"en": "cleaning.pq", "pl": "czyszczenie.pq"},
    "howto_header": {"en": "How to use this code in Power BI", "pl": "Jak użyć tego kodu w Power BI"},
    "howto_body": {
        "en": "1. In Power BI Desktop: **Get data → Blank query**.\n"
              "2. In the Power Query editor: **Advanced Editor**.\n"
              "3. Delete everything there and paste the code from this page.\n"
              "4. Click **Done**, then **Close & Apply**.\n\n"
              "When a new file with the same problems arrives, replace it and click **Refresh** - "
              "the cleaning runs automatically.",
        "pl": "1. W Power BI Desktop: **Pobierz dane → Pusta kwerenda** (Blank query).\n"
              "2. W edytorze Power Query: **Edytor zaawansowany** (Advanced Editor).\n"
              "3. Usuń wszystko, co tam jest, i wklej kod z tej strony.\n"
              "4. Kliknij **Gotowe**, a potem **Zamknij i zastosuj**.\n\n"
              "Gdy przyjdzie nowy plik z tymi samymi błędami, podmień go i kliknij **Odśwież** - "
              "czyszczenie wykona się samo.",
    },

    # --- Nazwy kroków w kodzie M --------------------------------------------------
    "m_source": {"en": "Source", "pl": "Źródło"},
    "m_headers": {"en": "Promoted headers", "pl": "Nagłówki"},
    "m_trim": {"en": "Trimmed text", "pl": "Usunięte spacje"},
    "m_nulls": {"en": "Blanks to null", "pl": "Puste na null"},
    "m_map": {"en": "Map: {col}", "pl": "Mapa: {col}"},
    "m_unified": {"en": "Unified: {col}", "pl": "Ujednolicone: {col}"},
    "m_no_spaces": {"en": "No spaces: {col}", "pl": "Bez spacji: {col}"},
    "m_number": {"en": "Number: {col}", "pl": "Liczba: {col}"},
    "m_date": {"en": "Date: {col}", "pl": "Data: {col}"},
    "m_nip": {"en": "NIP: {col}", "pl": "NIP: {col}"},
    "m_distinct": {"en": "Removed duplicates", "pl": "Bez duplikatów"},
    "m_old_codes": {"en": "Old codes: {col}", "pl": "Stare kody: {col}"},
    "m_recoded": {"en": "Recoded: {col}", "pl": "Nowe kody: {col}"},
    "m_wide_keys": {"en": "Column keys", "pl": "Klucze kolumn"},
    "m_wide_data": {"en": "Data rows", "pl": "Wiersze danych"},
    "m_wide_renamed": {"en": "Renamed columns", "pl": "Nazwy kolumn"},
    "m_wide_unpivoted": {"en": "Unpivoted", "pl": "Odwrócona tabela"},
    "m_added": {"en": "Added: {col}", "pl": "Dodano: {col}"},
    "m_types": {"en": "Changed types", "pl": "Typy danych"},

    # --- Typy natywne (kolumny, które już mają typ, np. z Excela) ---------------
    "type_number_native": {"en": "number", "pl": "liczba"},
    "type_date_native": {"en": "date", "pl": "data"},

    # --- Układ szeroki (unpivot) ---------------------------------------------------
    "col_name_date": {"en": "Date", "pl": "Data"},
    "col_name_value": {"en": "Value", "pl": "Wartość"},
    "wide_detected": {
        "en": "**Wide layout detected:** the header takes {header_rows} rows and there are {n} value columns "
              "(one column per „{key}”). Power BI works best with a long table: one row per date and „{key}”.",
        "pl": "**Wykryto układ szeroki:** nagłówek zajmuje {header_rows} wierszy, a wartości są w {n} kolumnach "
              "(osobna kolumna dla każdego „{key}”). Power BI najlepiej działa z tabelą długą: "
              "jeden wiersz na datę i „{key}”.",
    },
    "wide_unpivot_label": {
        "en": "Unpivot the table (one row per date and „{key}”)",
        "pl": "Odwróć tabelę (jeden wiersz na datę i „{key}”)",
    },
    "wide_unpivot_note": {
        "en": "Empty cells (no measurement) are skipped - Power Query's unpivot does the same, so the row counts match. "
              "Constant header rows are kept as columns: {constants}.",
        "pl": "Puste komórki (brak pomiaru) są pomijane - tak samo działa odwracanie tabeli w Power Query, "
              "więc liczba wierszy się zgadza. Stałe wiersze nagłówka zostają jako kolumny: {constants}.",
    },

    # --- Słownik kodów -------------------------------------------------------------
    "dict_header": {"en": "Check codes against a dictionary (optional)", "pl": "Sprawdź kody w słowniku (opcjonalnie)"},
    "dict_caption": {
        "en": "Upload a reference file (e.g. station metadata) to check that every code in your data can be matched. "
              "Codes that don't match will silently disappear when you filter by city or region in Power BI.",
        "pl": "Wgraj plik słownikowy (np. metadane stacji), żeby sprawdzić, czy każdy kod z danych da się dopasować. "
              "Kody bez dopasowania po cichu „znikną” przy filtrowaniu po mieście czy regionie w Power BI.",
    },
    "dict_upload": {"en": "Dictionary file", "pl": "Plik słownika"},
    "dict_sheet": {"en": "Sheet", "pl": "Arkusz"},
    "dict_data_col": {"en": "Column with codes in your data", "pl": "Kolumna z kodami w danych"},
    "dict_key_col": {"en": "Column with current codes in the dictionary", "pl": "Kolumna z aktualnymi kodami w słowniku"},
    "dict_old_col": {"en": "Column with old codes (optional)", "pl": "Kolumna ze starymi kodami (opcjonalnie)"},
    "dict_none": {"en": "— none —", "pl": "— brak —"},
    "dict_codes": {"en": "Codes in data", "pl": "Kody w danych"},
    "dict_matched": {"en": "Found in dictionary", "pl": "Znalezione w słowniku"},
    "dict_via_old": {"en": "Matched by old code", "pl": "Dopasowane po starym kodzie"},
    "dict_unmatched": {"en": "Not found", "pl": "Nieznalezione"},
    "dict_unmatched_list": {
        "en": "Codes not found anywhere in the dictionary: {examples}. Rows with these codes will not match "
              "any entry in Power BI - check them manually or label them as unknown.",
        "pl": "Kody, których nie ma w słowniku: {examples}. Wiersze z tymi kodami nie połączą się "
              "z żadnym wpisem w Power BI - sprawdź je ręcznie albo oznacz jako nieznane.",
    },
    "dict_all_ok": {"en": "Every code in the data matches the dictionary.", "pl": "Wszystkie kody z danych są w słowniku."},
    "step_recode_label": {
        "en": "Replace old codes with current ones in „{col}”",
        "pl": "Zamień stare kody na aktualne w kolumnie „{col}”",
    },
    "step_recode_reason": {
        "en": "{n} codes appear in the dictionary only as old codes, e.g. {examples}.",
        "pl": "{n} kodów występuje w słowniku tylko jako stare kody, np. {examples}.",
    },
}


def t(key: str, lang: str, /, **params) -> str:
    """Zwraca tekst w wybranym języku i wstawia parametry w miejsca {nazwa}."""
    text = TEXTS[key][lang]
    return text.format(**params) if params else text


def issues_count(n: int, lang: str) -> str:
    """'1 issue' / '3 issues' albo polska odmiana: 1 problem, 2 problemy, 5 problemów."""
    if lang == "en":
        return f"{n} issue" if n == 1 else f"{n} issues"
    if n == 1:
        return "1 problem"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return f"{n} problemy"
    return f"{n} problemów"
