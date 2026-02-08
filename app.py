import streamlit as st
import pandas as pd
from datetime import date, timedelta
import requests
import google.generativeai as genai
import math

# ────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────
GEMINI_API_KEY = "AIzaSyABsHVJR1UtMU47TkOTgucH66RTPHyINnc"
NASA_API_KEY = "H2O9femdc2ceEYVYxz5xsSi27LAWWXC51h1Yrjqn"

genai.configure(api_key=GEMINI_API_KEY)

st.set_page_config(
    page_title="ECLIPTICA • NASA NEOs",
    page_icon="🌍☄️",
    layout="wide"
)

# ────────────────────────────────────────────────
# SESSION STATE
# ────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "page" not in st.session_state:
    st.session_state.page = "home"

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "user" not in st.session_state:
    st.session_state.user = ""

def nav_to(page):
    st.session_state.page = page

# ────────────────────────────────────────────────
# LOGIN PAGE (ANY USERNAME/PASSWORD)
# ────────────────────────────────────────────────
def login_page():
    st.markdown("""
    <style>
    .main { background-color: #000814; }
    .login-box {
        max-width: 420px;
        margin: auto;
        margin-top: 120px;
        padding: 30px;
        border-radius: 20px;
        background: #0d1b2a;
        box-shadow: 0 0 25px #00d4ff55;
        text-align: center;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="login-box">
        <h1>🌌 NEO Sentinel</h1>
        <p>Secure Access Portal</p>
    </div>
    """, unsafe_allow_html=True)

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("🚀 Login"):
        if username.strip() != "" and password.strip() != "":
            st.session_state.logged_in = True
            st.session_state.user = username
            st.success("Access Granted 🚀")
            st.rerun()
        else:
            st.error("Please enter both username and password")

# ────────────────────────────────────────────────
# DATA FETCHING
# ────────────────────────────────────────────────
@st.cache_data(ttl=1800)
def fetch_neo_data(api_key, start_date, end_date):
    url = "https://api.nasa.gov/neo/rest/v1/feed"
    params = {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "api_key": api_key
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        rows = []

        for dt, objs in data["near_earth_objects"].items():
            for obj in objs:
                ca = obj["close_approach_data"][0]
                diam = obj["estimated_diameter"]["kilometers"]
                rows.append({
                    "name": obj["name"],
                    "date": dt,
                    "hazardous": obj["is_potentially_hazardous_asteroid"],
                    "velocity_kmh": round(float(ca["relative_velocity"]["kilometers_per_hour"]), 1),
                    "miss_distance_km": round(float(ca["miss_distance"]["kilometers"]), 0),
                    "diameter_max_km": round(diam["estimated_diameter_max"], 3)
                })

        return pd.DataFrame(rows).sort_values("miss_distance_km")
    except:
        return pd.DataFrame()

# ────────────────────────────────────────────────
# MAIN APP
# ────────────────────────────────────────────────
if not st.session_state.logged_in:
    login_page()

else:
    # GLOBAL STYLES
    st.markdown("""
    <style>
        .main { background-color: #000814; color: #e0f7ff; }
        h1, h2, h3 { color: #88ddff !important; }
        .stButton>button {
            width: 100%;
            border-radius: 20px;
            background-color: #1a2233;
            color: white;
            border: 1px solid #224466;
        }
        .stButton>button:hover {
            border-color: #00d4ff;
            color: #00d4ff;
        }
    </style>
    """, unsafe_allow_html=True)

    st.caption(f"👋 Welcome, {st.session_state.user}")

    # ───────────────── HOME ─────────────────
    if st.session_state.page == "home":
        st.title("☄️ ECLIPTICA: NEO Terminal")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📊 Risk Score Analysis"):
                nav_to("risk")
        with col2:
            if st.button("🗺️ 2D Orbit Tracker"):
                nav_to("orbit")
        with col3:
            if st.button("🌌 3D Solar System"):
                nav_to("solar")

        today = date.today()
        df = fetch_neo_data(NASA_API_KEY, today - timedelta(days=3), today)

        if not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Objects Detected", len(df))
            c2.metric("Hazardous Count", int(df["hazardous"].sum()))
            c3.metric("Closest Approach", f"{df['miss_distance_km'].min():,.0f} km")
            st.dataframe(df, use_container_width=True)

        st.divider()
        st.subheader("🤖 Astro-AI Assistant")

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Ask about space..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("assistant"):
                model = genai.GenerativeModel("gemini-3-flash-preview")
                res = model.generate_content(prompt)
                st.markdown(res.text)
                st.session_state.chat_history.append({"role": "assistant", "content": res.text})

    # ───────────────── RISK ─────────────────
    elif st.session_state.page == "risk":
        st.title("⚠️ Risk Engine")
        if st.button("← Back"):
            nav_to("home")

        today = date.today()
        df = fetch_neo_data(NASA_API_KEY, today - timedelta(days=3), today)

        if not df.empty:
            name = st.selectbox("Select Asteroid", df["name"])
            target = df[df["name"] == name].iloc[0]

            raw = (target["diameter_max_km"] ** 2) / (target["miss_distance_km"] / 1_000_000 + 1)
            risk = round(min(10, math.log10(raw + 1) * 5), 2)

            st.metric("Risk Index", f"{risk}/10")
            st.progress(risk / 10)

    # ───────────────── ORBIT ─────────────────
    elif st.session_state.page == "orbit":
        st.title("📡 2D Orbit Tracker")
        if st.button("← Back"):
            nav_to("home")
        st.info("2D orbit visualization coming soon.")

    # ───────────────── SOLAR ─────────────────
    elif st.session_state.page == "solar":
        st.title("🌌 3D Solar System")
        if st.button("← Back"):
            nav_to("home")
        st.info("3D engine loaded.")
