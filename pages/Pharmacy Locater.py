# ─────────────────────────────── Imports
import os, math, re, io
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation

# ─────────────────────────────── Streamlit Setup
st.set_page_config(page_title="PHARMACY LOCATOR", layout="wide")

# ─────────────────────────────── Google Maps URLs
GOOGLE_STREET = "https://{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}"
GOOGLE_SATELLITE = "https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
ATTR = "Google Maps"
SUBDOMAINS = ["mt0", "mt1", "mt2", "mt3"]

# ─────────────────────────────── Map Utilities
def show_map(rows: pd.DataFrame, key="map"):
    fmap = folium.Map(
        location=[rows["lat"].mean(), rows["lon"].mean()],
        zoom_start=13,
        control_scale=True,
        tiles=None
    )

    folium.TileLayer(GOOGLE_STREET, name="Street View", attr=ATTR, subdomains=SUBDOMAINS).add_to(fmap)
    folium.TileLayer(GOOGLE_SATELLITE, name="Satellite View", attr=ATTR, subdomains=SUBDOMAINS).add_to(fmap)

    for _, r in rows.iterrows():
        folium.Marker(
            location=[r["lat"], r["lon"]],
            tooltip=f"{r['name']}\n{r['address']}",
            icon=folium.Icon(icon="map-marker", prefix="fa", color="blue", icon_color="white")
        ).add_to(fmap)

    folium.LayerControl(position="topright").add_to(fmap)
    st_folium(fmap, height=400, use_container_width=True, key=key)

    st.markdown("""
    <style>
    div[data-testid="stVerticalBlock"] > div:has(.folium-map) + div {
        margin-top: -40px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────── Haversine & Load
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    φ1, φ2 = map(math.radians, [lat1, lat2])
    dφ, dλ = map(math.radians, [lat2 - lat1, lon2 - lon1])
    a = math.sin(dφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(dλ/2)**2
    return 2 * R * math.asin(math.sqrt(a))

@st.cache_data
def load_db(path="Pharmacies.csv"):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower()
    df = df.rename(columns={
        "pharmacy name": "name", "address": "address", "pincode": "pin",
        "latitude": "lat", "longitude": "lon"
    })
    df["pin"] = df["pin"].astype(str).str.zfill(6)
    chains = ("apollo", "medplus", "pharmeasy", "1mg", "netmeds", "wellness", "anjaney", "dvs", "guardian")
    df["is_chain"] = df["name"].str.lower().apply(lambda x: any(c in x for c in chains))
    return df

@st.cache_data
def unique_cities(df): return sorted(df["address"].apply(lambda a: a.split(",")[-1].strip().title()).unique())
@st.cache_data
def pin_centers(df): return df.groupby("pin")[["lat", "lon"]].mean().apply(tuple, axis=1).to_dict()

def pdf_bytes(df):
    try:
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.lib import colors
    except ImportError:
        return None
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(letter))
    tbl = Table([df.columns.tolist()] + df.astype(str).values.tolist(), repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("ALIGN", (0,0), (-1,-1), "LEFT")
    ]))
    doc.build([tbl])
    buf.seek(0)
    return buf.read()

# ─────────────────────────────── Styling
st.markdown("""
<style>
[data-testid="stSidebar"], [data-testid="collapsedControl"] { display:none !important; }
h1 { text-align:center!important; font-size:2.6rem!important; color:#015c68!important; }
</style>
""", unsafe_allow_html=True)
st.markdown("<h1>PHARMACY LOCATOR</h1>", unsafe_allow_html=True)

# ─────────────────────────────── Load
df = load_db()
cities = unique_cities(df)
centres = pin_centers(df)

# ─────────────────────────────── UI
_, panel, _ = st.columns([1,2.5,1])
with panel:
    st.subheader("Choose your location")
    c1, c2, c3 = st.columns(3)
    pin  = c1.text_input("Enter 6-digit PIN code").strip()
    area = c2.text_input("…or type an area / locality").strip()
    city = c3.text_input("…or start typing a city").strip()

    if 1 <= len(city) < 50:
        hints = [c for c in cities if c.lower().startswith(city.lower()) and c.lower() != city.lower()][:5]
        if hints: st.markdown("**Did you mean:** " + ", ".join(hints))

    c4, c5 = st.columns(2)
    type_choice = c4.radio("Pharmacy type", ("All", "Chain only", "Local only"), horizontal=True)

    c5.markdown("— or —", unsafe_allow_html=True)
    loc = streamlit_geolocation()
    user_lat, user_lon = (loc["latitude"], loc["longitude"]) if loc and loc.get("latitude") else (None, None)
    radius_km = st.slider("Search radius (km)", 1, 20, 5)

# ─────────────────────────────── Results
def apply_type_filter(rows):
    if type_choice == "Chain only": return rows[rows["is_chain"]]
    if type_choice == "Local only": return rows[~rows["is_chain"]]
    return rows

_, results_col, _ = st.columns([1,2.5,1])
with results_col:
    if city:
        rows = df[df["address"].str.contains(city, case=False, na=False)]
        rows = apply_type_filter(rows)
        if rows.empty:
            st.error("No matching pharmacies.")
        else:
            st.success(f"{len(rows)} pharmacies found in {city.title()}.")
            st.dataframe(rows.drop(columns=["lat", "lon"]), use_container_width=True)
            show_map(rows, key="city")
            dl1, dl2 = st.columns(2)
            pdf = pdf_bytes(rows)
            if pdf: dl1.download_button("Download PDF", pdf, "pharmacies.pdf", "application/pdf")
            dl2.download_button("Download CSV", rows.to_csv(index=False).encode(), "pharmacies.csv", "text/csv")
        st.stop()

    if user_lat is None or user_lon is None:
        if pin in centres:
            user_lat, user_lon = centres[pin]
            st.success(f"Using PIN centroid {pin}: {user_lat:.4f},{user_lon:.4f}")
        elif area:
            rows = df[df["address"].str.contains(area, case=False, na=False)]
            if not rows.empty:
                user_lat, user_lon = rows[["lat", "lon"]].mean()
                st.success(f"Using centroid of {area.title()}.")
            else:
                st.warning("Area not found.")
        else:
            st.info("Enter city / PIN / locality or enable GPS.")

    if user_lat is not None and user_lon is not None:
        df["distance_km"] = df.apply(lambda r: haversine(user_lat, user_lon, r["lat"], r["lon"]), axis=1)
        rows = df[df["distance_km"] <= radius_km]
        rows = apply_type_filter(rows).sort_values("distance_km")
        st.markdown(f"### {len(rows)} pharmacies within {radius_km} km")
        if rows.empty:
            st.warning("No pharmacies found in this range.")
        else:
            st.dataframe(rows.drop(columns=["lat","lon"]).round({"distance_km": 2}), use_container_width=True)
            show_map(rows, key="radius")
            dl1, dl2 = st.columns(2)
            pdf = pdf_bytes(rows)
            if pdf: dl1.download_button("Download PDF", pdf, "pharmacies.pdf", "application/pdf", key="pdf2")
            dl2.download_button("Download CSV", rows.to_csv(index=False).encode(), "pharmacies.csv", "text/csv", key="csv2")
