# ─────────────────────────────── Imports
import os, math, re, io
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation

# ─────────────────────────────── Setup
st.set_page_config(page_title="PHARMACY LOCATOR", layout="wide")

GOOGLE_STREET = "https://{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}"
GOOGLE_SATELLITE = "https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
ATTR = "Google Maps"
SUBDOMAINS = ["mt0", "mt1", "mt2", "mt3"]

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

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    φ1, φ2 = map(math.radians, [lat1, lat2])
    dφ, dλ = map(math.radians, [lat2 - lat1, lon2 - lon1])
    a = math.sin(dφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(dλ/2)**2
    return 2 * R * math.asin(math.sqrt(min(1, max(0, a))))

def gmaps_navigation_link(from_lat, from_lon, to_lat, to_lon):
    return f"https://www.google.com/maps/dir/{from_lat},{from_lon}/{to_lat},{to_lon}"

@st.cache_data
def load_db(path="GenericP.csv"):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower()
    df = df.rename(columns={
        "name": "name",
        "contact": "phone",
        "address": "address",
        "pin code": "pin",
        "latitude": "lat",
        "longitude": "lon"
    })
    df = df.dropna(subset=["lat", "lon"])
    df["pin"] = df["pin"].astype(str).str.split(".").str[0].str.zfill(6)
    return df

@st.cache_data
def unique_cities(df):
    return sorted(df["address"].apply(lambda a: str(a).split(",")[-1].strip().title()).unique())

@st.cache_data
def pin_centers(df):
    return df.groupby("pin")[["lat", "lon"]].mean().apply(tuple, axis=1).to_dict()

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

# ─────────────────────────────── Title
st.markdown("<h1 style='text-align:center; color:#015c68;'>PHARMACY LOCATOR</h1>", unsafe_allow_html=True)

# ─────────────────────────────── Load
df = load_db()
cities = unique_cities(df)
centres = pin_centers(df)

# ─────────────────────────────── Sidebar
with st.sidebar:
    st.header("🔍 Search Filters")
    if "search_triggered" not in st.session_state:
        st.session_state["search_triggered"] = False

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

    def trigger_search():
        st.session_state["search_triggered"] = True

    st.button("🔍 Search", on_click=trigger_search)
    if st.button("🔄 Clear All Filters"):
        for key in ["search_triggered"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# ─────────────────────────────── Logic
if st.session_state.get("search_triggered"):
    if city:
        rows = df[df["address"].str.contains(city, case=False, na=False)]
        if rows.empty:
            st.error("No pharmacies found. Try adjusting city name or filter options.")
        else:
            st.success(f"{len(rows)} pharmacies found in {city.title()}.")
            loc = (user_lat, user_lon) if user_lat is not None and user_lon is not None else None
            show_map(rows, user_location=loc, key="city")
            for _, row in rows.iterrows():
                nav = gmaps_navigation_link(user_lat, user_lon, row['lat'], row['lon']) if user_lat and user_lon else "#"
                st.markdown(f"🏪 [**{row['name']}**]({nav})", unsafe_allow_html=True)
                st.markdown(f"📍 {row['address']}")
                with st.expander("📞 Show Phone Number"):
                    st.markdown(f"📞 `{row['phone']}`")
                st.markdown("---")
            st.stop()

    elif pin or area:
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
        with st.spinner("Finding nearby pharmacies..."):
            df["distance_km"] = df.apply(lambda r: haversine(user_lat, user_lon, r["lat"], r["lon"]), axis=1)
            rows = df[df["distance_km"] <= radius_km].sort_values("distance_km")

        st.markdown(f"<h4 style='color:#015c68;'>🧾 {len(rows)} pharmacies found within {radius_km} km</h4>", unsafe_allow_html=True)
        if rows.empty:
            st.warning("No pharmacies found in this range.")
        else:
            show_map(rows, user_location=(user_lat, user_lon), key="radius")
            for _, row in rows.iterrows():
                nav = gmaps_navigation_link(user_lat, user_lon, row['lat'], row['lon']) if user_lat and user_lon else "#"
                st.markdown(f"🏪 [**{row['name']}**]({nav})", unsafe_allow_html=True)
                st.markdown(f"📍 {row['address']}")
                st.markdown(f"🛣️ Distance: `{row['distance_km']:.2f} km`")
                with st.expander("📞 Show Phone Number"):
                    st.markdown(f"`{row['phone']}`")
                st.markdown("---")

            dl1, dl2 = st.columns(2)
            pdf = pdf_bytes(rows)
            if pdf: dl1.download_button("Download PDF", pdf, "pharmacies.pdf", "application/pdf", key="pdf2")
            dl2.download_button("Download CSV", rows.to_csv(index=False).encode(), "pharmacies.csv", "text/csv", key="csv2")
