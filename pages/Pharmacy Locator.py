import os, math, io
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation

st.set_page_config(page_title="Pharmacy Locator", layout="wide")

# ─────────────────────────────── Constants
GOOGLE_STREET = "https://{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}"
GOOGLE_SATELLITE = "https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
ATTR = "Google Maps"
SUBDOMAINS = ["mt0", "mt1", "mt2", "mt3"]

# ─────────────────────────────── Load Database
@st.cache_data
def load_db(path="GenericP.csv"):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower()
    
    # Rename for consistent reference
    df = df.rename(columns={
        "name": "name",
        "contact": "phone",
        "address": "address",
        "pin": "pin",
        "lat": "lat",
        "lon": "lon"
    })
    
    # Ensure 'lat' and 'lon' exist before dropping nulls
    if "lat" in df.columns and "lon" in df.columns:
        df = df.dropna(subset=["lat", "lon"])
    else:
        st.error("Missing 'lat' or 'lon' columns in the data.")
        st.stop()

    # Normalize pin
    df["pin"] = df["pin"].astype(str).str.split(".").str[0].str.zfill(6)
    return df

# ─────────────────────────────── Utilities
def unique_cities(df):
    return sorted(df["address"].apply(lambda a: str(a).split(",")[-1].strip().title()).unique())

def pin_centers(df):
    return df.groupby("pin")[["lat", "lon"]].mean().apply(tuple, axis=1).to_dict()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    φ1, φ2 = map(math.radians, [lat1, lat2])
    dφ, dλ = map(math.radians, [lat2 - lat1, lon2 - lon1])
    a = math.sin(dφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(dλ/2)**2
    return 2 * R * math.asin(math.sqrt(min(1, max(0, a))))

def gmaps_navigation_link(from_lat, from_lon, to_lat, to_lon):
    return f"https://www.google.com/maps/dir/{from_lat},{from_lon}/{to_lat},{to_lon}"

def show_map(rows: pd.DataFrame, user_location=None, highlight_name=None, key="map"):
    fmap = folium.Map(location=[0, 0], zoom_start=2, control_scale=True, tiles=None)
    folium.TileLayer(GOOGLE_STREET, name="Street View", attr=ATTR, subdomains=SUBDOMAINS).add_to(fmap)
    folium.TileLayer(GOOGLE_SATELLITE, name="Satellite View", attr=ATTR, subdomains=SUBDOMAINS).add_to(fmap)

    bounds = []
    if user_location:
        folium.Marker(
            location=user_location,
            tooltip="📍 You are here",
            icon=folium.Icon(color="red", icon="user", prefix="fa")
        ).add_to(fmap)
        bounds.append(user_location)

    for _, r in rows.iterrows():
        color = "orange" if highlight_name and r["name"] == highlight_name else "blue"
        bounds.append([r["lat"], r["lon"]])
        folium.Marker(
            location=[r["lat"], r["lon"]],
            tooltip=f"{r['name']}\n{r['address']}",
            icon=folium.Icon(icon="map-marker", prefix="fa", color=color, icon_color="white")
        ).add_to(fmap)

    if bounds:
        fmap.fit_bounds(bounds)

    folium.LayerControl(position="topright").add_to(fmap)
    return st_folium(fmap, height=500, use_container_width=True, key=key)

# ─────────────────────────────── UI START
st.markdown("<h1 style='text-align:center; color:#015c68;'>PHARMACY LOCATOR</h1>", unsafe_allow_html=True)

df = load_db()
cities = unique_cities(df)
centres = pin_centers(df)

# ─────────────────────────────── Sidebar
with st.sidebar:
    st.header("🔍 Search Filters")
    pin = st.text_input("Enter 6-digit PIN code", value="").strip()
    area = st.text_input("…or type an area / locality", value="").strip()
    city = st.text_input("…or start typing a city", value="").strip()

    if 1 <= len(city) < 50:
        hints = [c for c in cities if c.lower().startswith(city.lower()) and c.lower() != city.lower()][:5]
        if hints:
            st.markdown("*Did you mean:* " + ", ".join(hints))

    st.markdown("— or —", unsafe_allow_html=True)
    loc = streamlit_geolocation()
    user_lat, user_lon = (loc["latitude"], loc["longitude"]) if loc and loc.get("latitude") else (None, None)
    radius_km = st.slider("Search radius (km)", 1, 20, 5)

    if st.button("🔍 Search"):
        st.session_state["search_triggered"] = True
    if st.button("🔄 Clear All Filters"):
        for key in ["search_triggered"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# ─────────────────────────────── Search Handling
if st.session_state.get("search_triggered", False):
    rows = pd.DataFrame()

    if city:
        rows = df[df["address"].str.contains(city, case=False, na=False)]

    elif pin or area:
        if user_lat is None or user_lon is None:
            if pin in centres:
                user_lat, user_lon = centres[pin]
                st.success(f"Using PIN centroid {pin}: {user_lat:.4f},{user_lon:.4f}")
            elif area:
                area_rows = df[df["address"].str.contains(area, case=False, na=False)]
                if not area_rows.empty:
                    user_lat, user_lon = area_rows[["lat", "lon"]].mean()
                    st.success(f"Using centroid of {area.title()}.")
                else:
                    st.warning("Area not found.")
        if user_lat is not None and user_lon is not None:
            df["distance_km"] = df.apply(lambda r: haversine(user_lat, user_lon, r["lat"], r["lon"]), axis=1)
            rows = df[df["distance_km"] <= radius_km].sort_values("distance_km")

    if rows.empty:
        st.warning("No pharmacies found. Try adjusting filters or location.")
    else:
        st.success(f"{len(rows)} pharmacies found.")
        show_map(rows, user_location=(user_lat, user_lon), key="map")
        for _, row in rows.iterrows():
            nav = gmaps_navigation_link(user_lat, user_lon, row["lat"], row["lon"]) if user_lat and user_lon else "#"
            st.markdown(f"🏪 [**{row['name']}**]({nav})", unsafe_allow_html=True)
            st.markdown(f"📍 {row['address']}")
            if "phone" in row and pd.notna(row["phone"]):
                with st.expander("📞 Show phone number"):
                    st.markdown(f"`{row['phone']}`")
            if "distance_km" in row:
                st.markdown(f"🛣️ Distance: `{row['distance_km']:.2f} km`")
            st.markdown("---")
