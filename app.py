"""
Data Assistant for Power BI / Asystent danych dla Power BI.

Raport jakości danych, plan czyszczenia i gotowy kod Power Query.
Interfejs po angielsku i po polsku (przełącznik w panelu bocznym).

Uruchom w terminalu:
    streamlit run app.py
"""

import pandas as pd
import streamlit as st

from cleaning import apply_steps, steps_to_m, suggest_steps
from i18n import LANGUAGES, TEXTS, issues_count, t
from loading import load_file
from profiling import profile_dataframe

st.set_page_config(page_title="Data Assistant for Power BI", layout="wide")

# --- Wybór języka ----------------------------------------------------------------
lang = st.sidebar.radio(
    "Language / Język",
    options=list(LANGUAGES),          # ["en", "pl"]
    format_func=LANGUAGES.get,        # pokazujemy "English" / "Polski"
)

st.title(t("app_title", lang))
st.caption(t("app_caption", lang))

uploaded = st.file_uploader(t("choose_file", lang), type=["csv", "xlsx", "xls"])

if uploaded is None:
    st.info(t("no_file_hint", lang))
    st.stop()

# --- Wczytanie ----------------------------------------------------------------
try:
    result = load_file(uploaded.getvalue(), uploaded.name)
except Exception as e:  # pokazujemy błąd zrozumiale, zamiast "wywalać" aplikację
    st.error(t("load_error", lang, error=e))
    st.stop()

df = result.df
if result.file_type == "csv":
    sep_key = "sep_" + result.separator
    sep_name = t(sep_key, lang) if sep_key in TEXTS else result.separator
    st.success(t("loaded_csv", lang, encoding=result.encoding, separator=sep_name))
else:
    st.success(t("loaded_excel", lang))

with st.expander(t("preview_raw", lang)):
    st.dataframe(df.head(20), hide_index=True)

# --- Profilowanie ---------------------------------------------------------------
profile = profile_dataframe(df)

c1, c2, c3, c4 = st.columns(4)
c1.metric(t("metric_rows", lang), f"{profile.row_count:,}".replace(",", " "))
c2.metric(t("metric_columns", lang), profile.column_count)
c3.metric(t("metric_duplicates", lang), profile.duplicate_rows)
c4.metric(t("metric_issues", lang), profile.issue_count)

st.subheader(t("columns_header", lang))
summary = pd.DataFrame([
    {
        t("col_name", lang): c.name,
        t("col_type", lang): t("type_" + c.detected_type, lang),
        t("col_match", lang): f"{c.type_match_pct:.0%}",
        t("col_missing", lang): f"{c.missing_pct:.0%}",
        t("col_unique", lang): c.unique_count,
        t("col_issues", lang): len(c.issues),
        t("col_examples", lang): ", ".join(map(str, c.sample_values[:3])),
    }
    for c in profile.columns
])
st.dataframe(summary, hide_index=True)

st.subheader(t("issues_header", lang))
if profile.duplicate_rows:
    st.warning(t("duplicates_warning", lang, n=profile.duplicate_rows))

columns_with_issues = [c for c in profile.columns if c.issues]
if not columns_with_issues:
    st.success(t("no_issues", lang))
for col in columns_with_issues:
    with st.expander(f"{col.name} · {issues_count(len(col.issues), lang)}"):
        for issue in col.issues:
            st.markdown(f"- {issue.render(lang)}")

# --- Eksport raportu --------------------------------------------------------------
report = pd.DataFrame(
    [{t("report_col_column", lang): c.name,
      t("report_col_type", lang): t("type_" + c.detected_type, lang),
      t("report_col_issue", lang): issue.render(lang)}
     for c in profile.columns for issue in c.issues]
)
st.download_button(
    t("download_report", lang),
    report.to_csv(index=False, sep=";").encode("utf-8-sig"),  # utf-8-sig: Excel poprawnie pokaże polskie znaki
    file_name=t("report_file", lang),
    mime="text/csv",
)

# --- Plan czyszczenia -----------------------------------------------------------
st.divider()
st.header(t("plan_header", lang))
st.caption(t("plan_caption", lang))

steps = suggest_steps(df, profile)
chosen = []
for step in steps:
    if st.checkbox(step.label(lang), value=True, key=step.key):
        chosen.append(step)
    st.caption(step.reason(lang))

st.info(t("plan_outliers_note", lang))

# --- Podgląd przed i po -----------------------------------------------------------
cleaned = apply_steps(df, chosen)

st.subheader(t("preview_header", lang))
c1, c2 = st.columns(2)
c1.metric(t("rows_before", lang), len(df))
c2.metric(t("rows_after", lang), len(cleaned), delta=len(cleaned) - len(df))

tab_before, tab_after = st.tabs([t("tab_before", lang), t("tab_after", lang)])
with tab_before:
    st.dataframe(df.head(20), hide_index=True)
with tab_after:
    st.dataframe(cleaned.head(20), hide_index=True)

# --- Kod Power Query --------------------------------------------------------------
st.divider()
st.header(t("code_header", lang))
file_path = st.text_input(
    t("path_label", lang),
    value=t("path_default_folder", lang) + uploaded.name,
    help=t("path_help", lang),
    key="file_path",
)
m_code = steps_to_m(chosen, file_path, result.file_type, result.encoding, result.separator, lang)
st.code(m_code, language=None)
st.download_button(t("download_code", lang), m_code.encode("utf-8"),
                   file_name=t("code_file", lang), mime="text/plain")

with st.expander(t("howto_header", lang)):
    st.markdown(t("howto_body", lang))
