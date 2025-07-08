import streamlit as st
from PIL import Image
import base64

# ───────────────────────────────
# PAGE CONFIG
# ───────────────────────────────
st.set_page_config(
    page_title="GenericBro — Home",
    page_icon="🩺",
    layout="centered"
)

# ───────────────────────────────
# EMBEDDED CENTERED IMAGE
# ───────────────────────────────
def get_image_base64(image_path):
    with open(image_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

logo_base64 = get_image_base64("Logo.jpeg")

st.markdown(
    f"""
    <div style='text-align:center; margin-bottom: 1rem;'>
        <img src='data:image/jpeg;base64,{logo_base64}' width='160'/>
    </div>
    """,
    unsafe_allow_html=True
)

# ───────────────────────────────
# CUSTOM CSS
# ───────────────────────────────
st.markdown("""
    <style>
        .centered {
            text-align: center;
        }
        .title-big {
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        .subtitle {
            font-size: 1.2rem;
            font-weight: 500;
            color: #444;
        }
        .section-title {
            font-size: 1.5rem;
            margin-top: 2.5rem;
            font-weight: 600;
        }
        .footer {
            text-align: center;
            margin-top: 2rem;
            font-size: 0.9rem;
            color: #888;
        }
        hr {
            border: none;
            border-top: 1px solid #eee;
            margin: 2rem 0;
        }
    </style>
""", unsafe_allow_html=True)

# ───────────────────────────────
# HEADER TEXT
# ───────────────────────────────
st.markdown('<div class="centered title-big">GenericBro</div>', unsafe_allow_html=True)
st.markdown('<div class="centered subtitle">Affordable Healthcare at Your Fingertips</div>', unsafe_allow_html=True)
st.markdown('<div class="centered subtitle">Helping you find <b>generic alternatives</b> to branded medicines and <b>locate pharmacies</b> nearby.</div>', unsafe_allow_html=True)

st.markdown("<hr />", unsafe_allow_html=True)

# ───────────────────────────────
# FEATURES (Clickable)
# ───────────────────────────────
st.markdown('<div class="centered section-title">🔍 What can you do with GenericBro?</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.page_link("Generic Medicine Finder", label="💊 Generic Medicine Finder", icon="💊")
with col2:
    st.page_link("Pharmacy Locator", label="🗺️ Pharmacy Locator", icon="🗺️")
with col3:
    st.page_link("Prescription Reader", label="📄 Prescription Reader", icon="📄")

st.markdown("<hr />", unsafe_allow_html=True)

# ───────────────────────────────
# GET STARTED
# ───────────────────────────────
st.markdown('<div class="section-title">🚀 Get Started</div>', unsafe_allow_html=True)
st.markdown("Select a feature from the sidebar or click above to begin.\n")
st.markdown("- **Generic Medicine Finder**: Discover affordable alternatives.")
st.markdown("- **Pharmacy Locator**: Find nearby pharmacies with ease.")
st.markdown("- **Prescription Reader**: Upload a prescription to extract medicines and view alternatives.")

st.markdown("<hr />", unsafe_allow_html=True)

# ───────────────────────────────
# FOOTER
# ───────────────────────────────
st.markdown('''
    <div class="footer">
        Built with ❤️ by Team GenericBro. <br />
        Created by: <b>Nidhish</b>, <b>Gursidak</b>, <b>Varshini</b>, <b>Oindrila</b>, <b>Atharva</b>, <b>Poorvi</b>.
    </div>
''', unsafe_allow_html=True)
