"""
Asystent danych dla Power BI - etap 1: wczytanie pliku i raport jakości danych.

Uruchom w terminalu:
    streamlit run app.py
"""

import pandas as pd
import streamlit as st

from loading import load_file
from profiling import profile_dataframe

st.set_page_config(page_title="Asystent danych dla Power BI", layout="wide")

st.title("Asystent danych dla Power BI")
st.caption("Wrzuć plik CSV lub Excel, a zobaczysz, co trzeba poprawić przed wczytaniem do Power BI.")

uploaded = st.file_uploader("Wybierz plik", type=["csv", "xlsx", "xls"])

if uploaded is None:
    st.info("Nie masz pliku pod ręką? Uruchom `python data/generate_test_data.py` "
            "i wrzuć `data/zamowienia_brudne.csv`.")
    st.stop()

# --- Wczytanie ----------------------------------------------------------------
try:
    result = load_file(uploaded.getvalue(), uploaded.name)
except Exception as e:  # pokazujemy błąd zrozumiale, zamiast "wywalać" aplikację
    st.error(f"Nie udało się wczytać pliku: {e}")
    st.stop()

df = result.df
if result.file_type == "csv":
    sep_name = {";": "średnik", ",": "przecinek", "\t": "tabulator", "|": "kreska"}.get(result.separator, result.separator)
    st.success(f"Wczytano plik CSV · kodowanie: **{result.encoding}** · separator: **{sep_name}**")
else:
    st.success("Wczytano plik Excel")

with st.expander("Podgląd danych (pierwsze 20 wierszy)"):
    st.dataframe(df.head(20), hide_index=True)

# --- Profilowanie ---------------------------------------------------------------
profile = profile_dataframe(df)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Wiersze", f"{profile.row_count:,}".replace(",", " "))
c2.metric("Kolumny", profile.column_count)
c3.metric("Zduplikowane wiersze", profile.duplicate_rows)
c4.metric("Wykryte problemy", profile.issue_count)

st.subheader("Kolumny")
summary = pd.DataFrame([
    {
        "Kolumna": c.name,
        "Wykryty typ": c.detected_type,
        "Zgodność z typem": f"{c.type_match_pct:.0%}",
        "Braki": f"{c.missing_pct:.0%}",
        "Unikalne": c.unique_count,
        "Problemy": len(c.issues),
        "Przykłady": ", ".join(map(str, c.sample_values[:3])),
    }
    for c in profile.columns
])
st.dataframe(summary, hide_index=True)

st.subheader("Szczegóły problemów")
if profile.duplicate_rows:
    st.warning(f"Tabela zawiera {profile.duplicate_rows} zduplikowanych wierszy.")

columns_with_issues = [c for c in profile.columns if c.issues]
if not columns_with_issues:
    st.success("Nie znaleziono problemów w kolumnach.")
for col in columns_with_issues:
    with st.expander(f"{col.name} · {len(col.issues)} problem(y)"):
        for issue in col.issues:
            st.markdown(f"- {issue}")

# --- Eksport raportu --------------------------------------------------------------
report = pd.DataFrame(
    [{"kolumna": c.name, "typ": c.detected_type, "problem": issue}
     for c in profile.columns for issue in c.issues]
)
st.download_button(
    "Pobierz raport jakości (CSV)",
    report.to_csv(index=False, sep=";").encode("utf-8-sig"),  # utf-8-sig: Excel poprawnie pokaże polskie znaki
    file_name="raport_jakosci.csv",
    mime="text/csv",
)
