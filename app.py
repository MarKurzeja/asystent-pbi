"""
Data Assistant for Power BI - Streamlit app.

Data quality report, cleaning plan and ready-to-use Power Query code.
English and Polish interface (switch in the sidebar).

Run:
    streamlit run app.py
"""

import pandas as pd
import streamlit as st

from cleaning import STEP_ORDER, Step, apply_steps, steps_to_m, suggest_steps
from i18n import LANGUAGES, TEXTS, issues_count, t
from loading import load_file
from profiling import profile_dataframe
from reshape import check_codes, detect_wide_layout, unpivot

st.set_page_config(page_title="Data Assistant for Power BI", layout="wide")

# --- Language -----------------------------------------------------------------
lang = st.sidebar.radio(
    "Language / Język",
    options=list(LANGUAGES),          # ["en", "pl"]
    format_func=LANGUAGES.get,        # shows "English" / "Polski"
)

st.title(t("app_title", lang))
st.caption(t("app_caption", lang))

uploaded = st.file_uploader(t("choose_file", lang), type=["csv", "xlsx", "xls"])

if uploaded is None:
    st.info(t("no_file_hint", lang))
    st.stop()

# --- Loading ------------------------------------------------------------------
try:
    result = load_file(uploaded.getvalue(), uploaded.name)
except Exception as e:  # show a readable message instead of crashing
    st.error(t("load_error", lang, error=e))
    st.stop()

df = result.df
if result.file_type == "csv":
    sep_key = "sep_" + result.separator
    sep_name = t(sep_key, lang) if sep_key in TEXTS else result.separator
    st.success(t("loaded_csv", lang, encoding=result.encoding, separator=sep_name))
else:
    st.success(t("loaded_excel", lang))

# --- Wide layout (multi-row header, e.g. GIOŚ files) --------------------------
layout = detect_wide_layout(result.raw) if result.file_type == "excel" else None
use_unpivot = False
if layout is not None:
    st.info(t("wide_detected", lang, header_rows=layout.header_rows, n=len(layout.keys), key=layout.key_label))
    use_unpivot = st.checkbox(t("wide_unpivot_label", lang, key=layout.key_label), value=True, key="unpivot")
    if use_unpivot:
        st.caption(t("wide_unpivot_note", lang, constants=", ".join(layout.constants) or "-"))
        df = unpivot(result.raw, layout, lang)

with st.expander(t("preview_raw", lang)):
    st.dataframe(df.head(20), hide_index=True)

# --- Profiling ----------------------------------------------------------------
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

# --- Report export ------------------------------------------------------------
report = pd.DataFrame(
    [{t("report_col_column", lang): c.name,
      t("report_col_type", lang): t("type_" + c.detected_type, lang),
      t("report_col_issue", lang): issue.render(lang)}
     for c in profile.columns for issue in c.issues]
)
st.download_button(
    t("download_report", lang),
    report.to_csv(index=False, sep=";").encode("utf-8-sig"),  # utf-8-sig: Excel displays Polish characters correctly
    file_name=t("report_file", lang),
    mime="text/csv",
)

# --- Cleaning plan ------------------------------------------------------------
st.divider()
st.header(t("plan_header", lang))
st.caption(t("plan_caption", lang))

steps = suggest_steps(df, profile)

# --- Code dictionary (optional) -----------------------------------------------
with st.expander(t("dict_header", lang)):
    st.caption(t("dict_caption", lang))
    dict_file = st.file_uploader(t("dict_upload", lang), type=["xlsx", "xls", "csv"], key="dict_file")
    if dict_file is not None:
        if dict_file.name.lower().endswith((".xlsx", ".xls")):
            book = pd.ExcelFile(dict_file)
            sheet = st.selectbox(t("dict_sheet", lang), book.sheet_names)
            dictionary = book.parse(sheet)
        else:
            dictionary = load_file(dict_file.getvalue(), dict_file.name).df

        text_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])
                     and not pd.api.types.is_datetime64_any_dtype(df[c])]
        dict_cols = list(dictionary.columns)
        default_data = text_cols.index(layout.key_label) if use_unpivot and layout.key_label in text_cols else 0
        data_col = st.selectbox(t("dict_data_col", lang), text_cols, index=default_data)
        key_col = st.selectbox(t("dict_key_col", lang), dict_cols,
                               index=dict_cols.index(data_col) if data_col in dict_cols else 0)
        none = t("dict_none", lang)
        old_options = [none] + [c for c in dict_cols if c != key_col]
        old_default = next((i for i, c in enumerate(old_options) if "stary" in str(c).lower() or "old" in str(c).lower()), 0)
        old_col = st.selectbox(t("dict_old_col", lang), old_options, index=old_default)

        lookup = check_codes(df[data_col], dictionary[key_col],
                             None if old_col == none else dictionary[old_col])
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(t("dict_codes", lang), lookup.total)
        m2.metric(t("dict_matched", lang), lookup.matched)
        m3.metric(t("dict_via_old", lang), len(lookup.old_code_mapping))
        m4.metric(t("dict_unmatched", lang), len(lookup.unmatched))
        if lookup.unmatched:
            st.warning(t("dict_unmatched_list", lang, examples=", ".join(lookup.unmatched[:15])))
        elif not lookup.old_code_mapping:
            st.success(t("dict_all_ok", lang))
        if lookup.old_code_mapping:
            steps.append(Step("recode", [data_col], {"mapping": lookup.old_code_mapping}))
            steps.sort(key=lambda s_: STEP_ORDER.index(s_.kind))
chosen = []
for step in steps:
    if st.checkbox(step.label(lang), value=True, key=step.key):
        chosen.append(step)
    st.caption(step.reason(lang))

st.info(t("plan_outliers_note", lang))

# --- Before/after preview -----------------------------------------------------
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

# --- Power Query code ---------------------------------------------------------
st.divider()
st.header(t("code_header", lang))
file_path = st.text_input(
    t("path_label", lang),
    value=t("path_default_folder", lang) + uploaded.name,
    help=t("path_help", lang),
    key="file_path",
)
m_code = steps_to_m(chosen, file_path, result.file_type, result.encoding, result.separator, lang,
                    sheet_name=result.sheet_name, layout=layout if use_unpivot else None)
st.code(m_code, language=None)
st.download_button(t("download_code", lang), m_code.encode("utf-8"),
                   file_name=t("code_file", lang), mime="text/plain")

with st.expander(t("howto_header", lang)):
    st.markdown(t("howto_body", lang))
