# ───────────────────────────── Imports
import os, math, re, io
import streamlit as st
import pandas as pd
import pydeck as pdk
from streamlit_geolocation import streamlit_geolocation

# ───────────────────────────── Page config
st.set_page_config(page_title="PHARMACY LOCATOR", page_icon="⚕️", layout="wide")

# ───────────────────────────── Mapbox token (silent fallback)
try:
    MAPBOX_TOKEN = st.secrets["MAPBOX_API_KEY"]
except Exception:
    MAPBOX_TOKEN = os.getenv("MAPBOX_API_KEY", "")
if MAPBOX_TOKEN:
    pdk.settings.mapbox_api_key = MAPBOX_TOKEN

# ───────────────────────────── Helpers
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    φ1, φ2 = map(math.radians, [lat1, lat2])
    dφ, dλ = map(math.radians, [lat2 - lat1, lon2 - lon1])
    a = math.sin(dφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(dλ/2)**2
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
    return df.groupby("pin")[["lat","lon"]].mean().apply(tuple, axis=1).to_dict()

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
        ("BACKGROUND",(0,0),(-1,0),colors.Color(0.007, 0.537, 0.615)), # using #02899d
        ("TEXTCOLOR",(0,0),(-1,0),colors.whitesmoke),
        ("GRID",(0,0),(-1,-1),0.5,colors.grey),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),8),
        ("ALIGN",(0,0),(-1,-1),"LEFT")
    ]))
    doc.build([tbl]); buf.seek(0)
    return buf.read()

# ───────────────────────────── Map helper
PIN_ICON = "https://cdn-icons-png.flaticon.com/512/684/684908.png"  # red pin

def show_map(rows: pd.DataFrame, key="map"):
    style_choice = st.selectbox("Map style", ("Street", "Satellite"), key=f"{key}_style")
    style_url = ("mapbox://styles/mapbox/streets-v12"
                 if style_choice == "Street"
                 else "mapbox://styles/mapbox/satellite-streets-v12")

    rows = rows.copy()
    rows["icon_data"] = rows.apply(lambda _: {
        "url": PIN_ICON, "width": 128, "height": 128, "anchorY": 128
    }, axis=1)

    layer = pdk.Layer(
        "IconLayer",
        data=rows,
        get_icon="icon_data",
        get_size=3,
        size_scale=10,
        get_position="[lon, lat]",
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
        use_container_width=True
    )

# ───────────────────────────── CSS & title
st.markdown("""
<style>
:root {
  --primary: #02899d;
  --primary-dark: #015c68;
  --primary-light: #e6f3f4;
  --text-on-primary: #ffffff;
}
/* --- General & Layout --- */
[data-testid="stSidebar"], [data-testid="collapsedControl"] {
    display: none !important;
}
/* Style the main content columns for a "panel" look */
[data-testid="stHorizontalBlock"] > div:nth-child(2) > [data-testid="stVerticalBlock"] > div[data-stale="false"] {
    background-color: #fafdfd;
    border: 1px solid var(--primary-light);
    border-radius: 10px;
    padding: 1.5rem;
}
/* --- Typography --- */
h1 {
    text-align: center !important;
    font-size: 2.6rem !important;
    color: var(--primary-dark) !important;
    font-weight: 700 !important;
    letter-spacing: 1px;
    padding-bottom: 1rem;
}
h2, h3 { /* st.subheader, st.markdown("### ...") */
    color: var(--primary);
    border-bottom: 2px solid var(--primary-light);
    padding-bottom: 5px;
}
hr {
    border-top: 1.5px solid var(--primary-light);
    margin: 1.5rem 0;
}
p > strong { /* "Did you mean:" hint text */
    color: var(--primary-dark);
}
.or-divider {
    text-align: center;
    margin-top: 10px;
    font-weight: 500;
    color: var(--primary);
}
/* --- Widgets & Components --- */
[data-testid="stAlert"][data-baseweb="alert"][role="alert"] { /* Success */
    background-color: var(--primary-light);
    color: var(--primary-dark);
    border: 1px solid var(--primary);
    border-radius: 8px;
}
[data-testid="stDownloadButton"] button {
    background-color: var(--primary);
    color: var(--text-on-primary);
    border: 1px solid var(--primary);
    border-radius: 5px;
    font-weight: 600;
    transition: all 0.2s ease-in-out;
    width: 100%; /* Make download buttons fill their column */
}
[data-testid="stDownloadButton"] button:hover {
    background-color: var(--primary-dark);
    border-color: var(--primary-dark);
    transform: scale(1.02);
}

/* CORRECTED SLIDER STYLES */
/* Slider Active Track */
div[data-baseweb="slider"] > div:nth-child(2) > div:first-child {
    background: var(--primary) !important;
}
/* Slider Thumb */
div[data-baseweb="slider"] [role="slider"] {
    background-color: var(--primary) !important;
    border: 2px solid var(--primary) !important;
}

[data-testid="stSelectbox"] li[aria-selected="true"] {
    background-color: var(--primary-light);
}
[data-testid="stDataFrame"] {
    border: 1px solid #e0e0e0;
    border-radius: 5px;
}
</style>
""", unsafe_allow_html=True)
st.markdown("<h1>PHARMACY LOCATOR</h1>", unsafe_allow_html=True)

# ───────────────────────────── Data
df      = load_db()
cities  = unique_cities(df)
centres = pin_centers(df)

# ───────────────────────────── Query panel
_, panel, _ = st.columns([1, 2.5, 1])
with panel:
    st.subheader("Choose your location")
    c1, c2, c3 = st.columns(3)
    pin  = c1.text_input("Enter PIN").strip()
    area = c2.text_input("Area/locality").strip()
    city = c3.text_input("City").strip()

    if 1 <= len(city) < 50:
        hints = [c for c in cities if c.lower().startswith(city.lower()) and c.lower()!=city.lower()][:5]
        if hints:
            st.markdown("**Did you mean:** " + ", ".join(hints))

    c4, c5 = st.columns(2)
    type_choice = c4.radio("Pharmacy type", ("All","Chain only","Local only"), horizontal=True)

    c5.markdown("<p class='or-divider'>— or —</p>", unsafe_allow_html=True)
    with c5:
        loc = streamlit_geolocation()
        if loc and loc.get("latitude"):
            user_lat, user_lon = loc["latitude"], loc["longitude"]
        else:
            user_lat = user_lon = None

    radius_km = st.slider("Search radius (km)", 1, 20, 5, key="radius")

# ───────────────────────────── Results
st.markdown("<hr>", unsafe_allow_html=True)
_, res, _ = st.columns([1, 2.5, 1])
with res:

    def filter_type(rows):
        if type_choice == "Chain only":  return rows[rows["is_chain"]]
        if type_choice == "Local only":  return rows[~rows["is_chain"]]
        return rows

    # City mode
    if city:
        hits = filter_type(df[df["address"].str.contains(city, case=False, na=False)])
        if hits.empty:
            st.error("No matching pharmacies.")
        else:
            st.success(f"{len(hits)} pharmacies found in {city.title()}.")
            st.dataframe(hits.drop(columns=["lat","lon"]), use_container_width=True)
            show_map(hits, key="city")
            dl1, dl2 = st.columns(2)
            if (pdf := pdf_bytes(hits)):
                dl1.download_button("Download PDF", pdf, "pharmacies.pdf", "application/pdf")
            dl2.download_button("Download CSV", hits.to_csv(index=False).encode(),
                                "pharmacies.csv","text/csv")
        st.stop()

    # Fallback to PIN/area/GPS
    if user_lat is None and user_lon is None:
        if pin and pin in centres:
            user_lat, user_lon = centres[pin]
            st.success(f"Using centroid of PIN {pin}.")
        elif pin:
            st.warning("PIN not in database.")
        elif area:
            sub = df[df["address"].str.contains(area, case=False, na=False)]
            if not sub.empty:
                user_lat, user_lon = sub[["lat","lon"]].mean()
                st.success(f"Using centroid of {area.title()}.")
            else:
                st.warning("Area not in database.")
        else:
            st.info("Enter a location or enable GPS to begin.")

    if user_lat is not None and user_lon is not None:
        df["distance_km"] = df.apply(lambda r:
            haversine(user_lat, user_lon, r["lat"], r["lon"]), axis=1)
        hits = filter_type(df[df["distance_km"] <= radius_km]).sort_values("distance_km")
        st.markdown(f"### {len(hits)} pharmacies within {radius_km} km")
        if hits.empty:
            st.warning("No pharmacies in this radius.")
        else:
            st.dataframe(hits.drop(columns=["lat","lon"]).round({"distance_km":2}),
                         use_container_width=True)
            show_map(hits, key="radius")
            dl1, dl2 = st.columns(2)
            if (pdf := pdf_bytes(hits)):
                dl1.download_button("Download PDF", pdf, "pharmacies.pdf", "application/pdf", key="pdf2")
            dl2.download_button("Download CSV", hits.to_csv(index=False).encode(),
                                "pharmacies.csv", "text/csv", key="csv2")