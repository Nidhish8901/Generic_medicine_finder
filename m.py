import streamlit as st
import pandas as pd
import re

# ─────────────────────────────────────────────────────────────
# 1.  CONSTANTS
# ─────────────────────────────────────────────────────────────
COL_NAME, COL_FORMULATION, COL_DOSAGE = "Name", "Formulation", "Dosage"
COL_TYPE, COL_PRICE_GENERIC           = "Type", "Cost of generic"
COL_PRICE_BRAND, COL_SAVE_PCT         = "Cost of branded", "Savings"
COL_USES, COL_SIDE_EFF                = "Uses", "Side effects"

# ─────────────────────────────────────────────────────────────
# 2.  SESSION DEFAULTS
# ─────────────────────────────────────────────────────────────
st.session_state.setdefault("search_mode", "Medicine name")
st.session_state.setdefault("run_search",  False)
st.session_state.setdefault("detail_row",  None)

# ─────────────────────────────────────────────────────────────
# 3.  PAGE CONFIG & GLOBAL CSS
# ─────────────────────────────────────────────────────────────
st.set_page_config("Generic Medicine Finder", "💊", layout="wide")
st.title("💊 Generic Medicine Finder")

st.markdown("""
<style>
/* put a soft card around the first container */
section.main > div > div > div > div {
    border:1px solid #ccc;border-radius:18px;padding:24px;
    background:#fdfdfd;box-shadow:0 0 8px rgba(0,0,0,0.03);
}
/* general button look */
div.stButton > button{
  white-space:nowrap;padding:12px 20px;border:1px solid #bbb;
  border-radius:12px;background:#fafafa;font-size:15px;
  transition:.3s;height:56px;line-height:1.2;}
div.stButton > button:hover{
  background:#e6ffe6;box-shadow:0 0 8px #4CAF50;transform:scale(1.05);
  font-weight:600;}
div.stButton > button.active-btn{
  border:2px solid #4CAF50;background:#F1F8F6;}
th,td{padding:6px 4px;font-size:.9rem;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 4.  LOAD + CLEAN DATA
# ─────────────────────────────────────────────────────────────
@st.cache_data
def load_data(path="test.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()

    rename = {"uses":"Uses","indications":"Uses",
              "side effects":"Side effects","adverse effects":"Side effects"}
    df.rename(columns={c:rename[c.lower()] for c in df.columns if c.lower() in rename},
              inplace=True)

    df["_form_clean"]   = df[COL_FORMULATION].str.strip().str.lower()
    df["_dosage_clean"] = df[COL_DOSAGE].astype(str).str.strip().str.lower()
    df["_type_clean"]   = df[COL_TYPE].str.strip().str.lower()

    for col in (COL_PRICE_GENERIC, COL_PRICE_BRAND, COL_SAVE_PCT):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if COL_SAVE_PCT not in df.columns and {COL_PRICE_GENERIC, COL_PRICE_BRAND}.issubset(df.columns):
        df[COL_SAVE_PCT] = (
            100 * (df[COL_PRICE_BRAND] - df[COL_PRICE_GENERIC]) / df[COL_PRICE_BRAND]
        )
    return df

df = load_data()

# ─────────────────────────────────────────────────────────────
# 5.  HELPERS
# ─────────────────────────────────────────────────────────────
def bulletify(txt: str) -> str:
    if pd.isna(txt) or str(txt).strip() == "":
        return ""
    parts = re.split(r"[;,/\n]+", str(txt))
    return "\n".join(f"- {p.strip().capitalize()}" for p in parts if p.strip())

def tidy(d: pd.DataFrame) -> pd.DataFrame:
    d = d.drop(columns=[c for c in d.columns if c.startswith("_")], errors="ignore").copy()
    if COL_SAVE_PCT in d.columns:
        d[COL_SAVE_PCT] = d[COL_SAVE_PCT].round(1)
    return d.reset_index(drop=True)

def safe_sort(d: pd.DataFrame, col: str, asc: bool) -> pd.DataFrame:
    if col not in d:
        return d
    return (
        d.assign(_k=pd.to_numeric(d[col], errors="coerce"))
        .sort_values("_k", ascending=asc, na_position="last")
        .drop(columns="_k")
    )

def show_clickable_table(df_: pd.DataFrame, header: str | None = None, key_prefix="tbl"):
    if df_.empty:
        return
    if header:
        st.subheader(header)

    hdr = st.columns([3, 2, 2, 2, 2])
    hdr[0].markdown("**Name**")
    hdr[1].markdown("**Dosage**")
    hdr[2].markdown("**Generic ₹**")
    hdr[3].markdown("**Branded ₹**")
    hdr[4].markdown("**Savings %**")

    for i, row in df_.iterrows():
        c = st.columns([3, 2, 2, 2, 2])
        if c[0].button(row[COL_NAME], key=f"{key_prefix}_{i}"):
            st.session_state.detail_row = row.to_dict()
        c[1].write(row.get(COL_DOSAGE, "—"))
        c[2].write(row.get(COL_PRICE_GENERIC, "—"))
        c[3].write(row.get(COL_PRICE_BRAND, "—"))
        c[4].write(row.get(COL_SAVE_PCT, "—"))

# ─────────────────────────────────────────────────────────────
# 6.  SEARCH & FILTER UI
# ─────────────────────────────────────────────────────────────
with st.container():
    st.markdown("### 🔍 Search & Filters")
    st.markdown("---")

    # 6-A  Mode buttons (true side-by-side, tiny gap)
    mode_cols = st.columns([0.15, 0.15, 0.7])           # two narrow + spacer
    with mode_cols[0]:
        if st.button("💊 Name", key="mode_name"):
            st.session_state.search_mode = "Medicine name"
    with mode_cols[1]:
        if st.button("🧪 Formulation", key="mode_form"):
            st.session_state.search_mode = "Formulation"

    # highlight active via JS
    active_lbl = {"Medicine name": "💊 Name", "Formulation": "🧪 Formulation"}[
        st.session_state.search_mode
    ]
    st.markdown(
        f"""
    <script>
    const t=setInterval(()=>{{
        const b=[...parent.document.querySelectorAll('button')]
               .find(e=>e.innerText.trim().startsWith("{active_lbl}"));
        if(b){{b.classList.add('active-btn');clearInterval(t);}}
    }},100);
    </script>
    """,
        unsafe_allow_html=True,
    )

    # 6-B  Row 1 filters
    r1 = st.columns([1.2, 1, 1])
    types = sorted(df[COL_TYPE].dropna().unique())
    typ = r1[0].selectbox("📋 Therapeutic Type", ["All"] + types)
    base = df if typ == "All" else df[df["_type_clean"] == typ.lower()]

    dosages = sorted(df["_dosage_clean"].dropna().unique())
    dose = r1[1].selectbox("💉 Dosage Filter", ["All"] + dosages)

    sort_map = {
        "Generic price": COL_PRICE_GENERIC,
        "Branded price": COL_PRICE_BRAND,
        "Savings %": COL_SAVE_PCT,
    }
    sort_by = r1[2].selectbox("📊 Sort by", list(sort_map))

    # 6-C  Row 2 filters
    r2 = st.columns([1.2, 1, 1])
    mode = st.session_state.search_mode
    if mode == "Medicine name":
        names = sorted(base[COL_NAME].dropna().unique())
        picked = r2[0].selectbox("💊 Branded Medicine", ["— All in Type —"] + names)
        name_sel = picked != "— All in Type —"
    else:
        forms = sorted(df[COL_FORMULATION].dropna().unique())
        picked = r2[0].selectbox("🧪 Choose Formulation", ["— select —"] + forms)

    ascending = (
        r2[1].radio("⬇️ Order", ["Low → High", "High → Low"], horizontal=True)
        == "Low → High"
    )

    if r2[2].button("🔍 Search", key="search_btn"):
        st.session_state.run_search = True
        st.session_state.detail_row = None

# ─────────────────────────────────────────────────────────────
# 7.  DATA FILTERING
# ─────────────────────────────────────────────────────────────
if not st.session_state.run_search:
    st.info("Adjust filters, then click **Search** to view results.")
    st.stop()

if mode == "Medicine name":
    hits = base if not name_sel else base[base[COL_NAME] == picked]
else:
    if picked == "— select —":
        st.warning("Please choose a formulation.")
        st.stop()
    hits = base[base["_form_clean"] == picked.lower()]

if dose != "All":
    hits = hits[hits["_dosage_clean"] == dose]

if hits.empty:
    st.warning("No entries match your filters.")
    st.stop()

same = pd.DataFrame()
if mode == "Medicine name" and "name_sel" in locals() and name_sel:
    same = base[base["_form_clean"].isin(hits["_form_clean"].unique())]
    if dose != "All":
        same = same[same["_dosage_clean"] == dose]

hits_sorted = tidy(safe_sort(hits, sort_map[sort_by], ascending))
same_sorted = tidy(safe_sort(same, sort_map[sort_by], ascending))

# ─────────────────────────────────────────────────────────────
# 8.  DISPLAY RESULTS
# ─────────────────────────────────────────────────────────────
if mode == "Medicine name":
    if not "name_sel" in locals() or not name_sel:
        show_clickable_table(hits_sorted, "🔎 Medicines", "generic")
    else:
        st.subheader("🔎 Exact Match")
        st.markdown(
            f"<div style='font-size:22px;font-weight:600;'>Formulation – "
            f"{hits_sorted.at[0, COL_FORMULATION]}</div>",
            unsafe_allow_html=True,
        )
        show_clickable_table(hits_sorted, key_prefix="exact")
        st.subheader("🩺 All Medicines with the Same Formulation")
        show_clickable_table(same_sorted, key_prefix="same")
else:
    show_clickable_table(
        hits_sorted, f"🧪 Medicines with Formulation: **{picked}**", key_prefix="form"
    )

# ─────────────────────────────────────────────────────────────
# 9.  DETAIL PANE
# ─────────────────────────────────────────────────────────────
det = st.session_state.detail_row
if det:
    uses = bulletify(det.get(COL_USES, ""))
    side = bulletify(det.get(COL_SIDE_EFF, ""))
    if uses or side:
        st.markdown("---")
    if uses:
        st.markdown(f"#### 📋 Uses of **{det[COL_NAME]}**")
        st.markdown(uses)
    if side:
        st.markdown("#### ⚠️ Possible Side Effects")
        st.markdown(side)

st.caption(
    "Click a medicine name to view its details. Adjust filters and hit **Search**."
)
 