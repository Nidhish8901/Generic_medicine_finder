# ─────────────────────────────── Imports
import os, math, re, io
import streamlit as st
import pandas as pd
import pydeck as pdk
from streamlit_geolocation import streamlit_geolocation

# ─────────────────────────────── Page config  (must be FIRST Streamlit call!)
st.set_page_config(page_title="PHARMACY LOCATOR", page_icon=None, layout="wide")

# ─────────────────────────────── Mapbox token (silent fallback)
try:
    MAPBOX_TOKEN = st.secrets["MAPBOX_API_KEY"]          # .streamlit/secrets.toml
except Exception:
    MAPBOX_TOKEN = os.getenv("MAPBOX_API_KEY", "")       # environment var

if MAPBOX_TOKEN:
    pdk.settings.mapbox_api_key = MAPBOX_TOKEN
# (no banner if missing)

# ─────────────────────────────── Helpers
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    φ1, φ2 = map(math.radians, [lat1, lat2])
    dφ, dλ = map(math.radians, [lat2 - lat1, lon2 - lon1])
    a = math.sin(dφ / 2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(dλ / 2)**2
    return 2 * R * math.asin(math.sqrt(a))

@st.cache_data(show_spinner=False)
def load_db(path="Pharmacies.csv"):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower()
    df = df.rename(columns={
        "pharmacy name": "name",
        "address":       "address",
        "pincode":       "pin",
        "latitude":      "lat",
        "longitude":     "lon",
    })
    df["pin"] = df["pin"].astype(str).str.zfill(6)
    if "is_chain" not in df.columns:
        chain_kw = ("apollo","medplus","pharmeasy","1mg","netmeds",
                    "wellness","anjaney","dvs","guardian")
        df["is_chain"] = df["name"].str.lower().apply(
            lambda x: any(kw in x for kw in chain_kw)
        )
    else:
        df["is_chain"] = df["is_chain"].astype(bool, errors="ignore")
    return df

def guess_city(addr):
    m = re.search(r",\s*([^,]+)\s+\d{6}$", addr)
    return m.group(1).strip() if m else addr.split(",")[-1].strip()

@st.cache_data(show_spinner=False)
def unique_cities(df):
    return sorted(filter(None, df["address"].apply(guess_city).str.title().unique()))

@st.cache_data(show_spinner=False)
def pin_centers(df):
    return df.groupby("pin")[["lat","lon"]].mean().apply(tuple,axis=1).to_dict()

def pdf_bytes(df):
    try:
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    except ImportError:
        return None
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(letter))
    tbl = Table([df.columns.tolist()] + df.astype(str).values.tolist(), repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.lightgrey),
        ("GRID",(0,0),(-1,-1),0.5,colors.grey),
        ("FONTSIZE",(0,0),(-1,-1),8),
        ("ALIGN",(0,0),(-1,-1),"LEFT"),
    ]))
    doc.build([tbl]); buf.seek(0)
    return buf.read()

def show_map(rows, key="map"):
    style_choice = st.selectbox("Map style", ("Street","Satellite"), key=f"{key}_style")
    style_url = ("mapbox://styles/mapbox/streets-v12"
                 if style_choice == "Street"
                 else "mapbox://styles/mapbox/satellite-streets-v12")
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=rows,
        get_position="[lon, lat]",
        get_radius=120,
        get_fill_color=[200,30,60,140],
        pickable=True,
    )
    view = pdk.ViewState(latitude=rows["lat"].mean(),
                         longitude=rows["lon"].mean(),
                         zoom=12)
    st.pydeck_chart(
        pdk.Deck(map_style=style_url,
                 initial_view_state=view,
                 layers=[layer],
                 tooltip={"text": "{name}\n{address}"}),
        use_container_width=True,
    )

# ─────────────────────────────── Title & CSS
st.markdown("""
<style>
[data-testid="stSidebar"], [data-testid="collapsedControl"] {display:none!important;}
h1 {text-align:center!important;font-size:2.6rem!important;}
</style>
""", unsafe_allow_html=True)
st.markdown("<h1>PHARMACY LOCATOR</h1>", unsafe_allow_html=True)

# ─────────────────────────────── Load data
df       = load_db()
cities   = unique_cities(df)
centres  = pin_centers(df)

# ─────────────────────────────── UI panel
_, panel, _ = st.columns([1,2,1])
with panel:
    st.subheader("Choose your location")
    pin  = st.text_input("Enter 6-digit PIN code").strip()
    area = st.text_input("…or type an area / locality").strip()
    city = st.text_input("…or start typing a city").strip()

    if 1 <= len(city) < 50:
        hints = [c for c in cities
                 if c.lower().startswith(city.lower()) and c.lower()!=city.lower()][:5]
        if hints:
            st.markdown("**Did you mean:**")
            st.markdown("\n".join(f"- {h}" for h in hints))

    type_choice = st.radio("Pharmacy type", ("All","Chain only","Local only"), horizontal=True)

    st.markdown("**— or —**")
    loc = streamlit_geolocation()
    if loc and loc.get("latitude"):
        user_lat, user_lon = loc["latitude"], loc["longitude"]
        st.success(f"GPS acquired: {user_lat:.4f},{user_lon:.4f}")
    else:
        user_lat = user_lon = None
    radius_km = st.slider("Search radius (km)", 1, 20, 5)

# ─────────────────────────────── Search logic
def apply_type_filter(df_rows):
    if type_choice == "Chain only":
        return df_rows[df_rows["is_chain"]]
    if type_choice == "Local only":
        return df_rows[~df_rows["is_chain"]]
    return df_rows

# 1) City search
if city:
    rows = df[df["address"].str.contains(city, case=False, na=False)]
    rows = apply_type_filter(rows)
    if rows.empty:
        st.error("No matching pharmacies.")
    else:
        st.success(f"{len(rows)} pharmacies found.")
        st.dataframe(rows.drop(columns=["lat","lon"]), use_container_width=True)
        show_map(rows, key="city")
        fmt = st.selectbox("Download as", ("CSV","PDF"))
        if fmt=="CSV":
            st.download_button("Download CSV", rows.to_csv(index=False).encode(),
                               "pharmacies.csv", "text/csv")
        else:
            pdf = pdf_bytes(rows)
            if pdf:
                st.download_button("Download PDF", pdf,
                                   "pharmacies.pdf","application/pdf")
            else:
                st.info("Install `reportlab` for PDF export.")
    st.stop()

# 2) Fallback: PIN / area / GPS
if user_lat is None and user_lon is None:
    if pin and pin in centres:
        user_lat, user_lon = centres[pin]
        st.success(f"Using centroid of PIN {pin}: {user_lat:.4f},{user_lon:.4f}")
    elif pin:
        st.warning("PIN not in database.")
    elif area:
        rows_area = df[df["address"].str.contains(area, case=False, na=False)]
        if not rows_area.empty:
            user_lat, user_lon = rows_area[["lat","lon"]].mean()
            st.success(f"Using centroid of {area.title()}.")
        else:
            st.warning("Area not in database.")
    else:
        st.info("Enter a PIN, area, city or enable GPS to begin.")

# 3) Radius results
if user_lat is not None and user_lon is not None:
    df["distance_km"] = df.apply(
        lambda r: haversine(user_lat,user_lon,r["lat"],r["lon"]), axis=1)
    rows = df[df["distance_km"] <= radius_km]
    rows = apply_type_filter(rows).sort_values("distance_km").reset_index(drop=True)

    st.write(f"### {len(rows)} pharmacies within {radius_km} km")
    if rows.empty:
        st.warning("No pharmacies in this radius.")
    else:
        st.dataframe(rows.drop(columns=["lat","lon"])
                         .round({"distance_km":2}), use_container_width=True)
        show_map(rows, key="radius")

        fmt = st.selectbox("Download as", ("CSV","PDF"), key="dl2")
        if fmt=="CSV":
            st.download_button("Download CSV", rows.to_csv(index=False).encode(),
                               "pharmacies.csv","text/csv", key="csv2")
        else:
            pdf = pdf_bytes(rows)
            if pdf:
                st.download_button("Download PDF", pdf,
                                   "pharmacies.pdf","application/pdf", key="pdf2")
            else:
                st.info("Install `reportlab` for PDF export.")
