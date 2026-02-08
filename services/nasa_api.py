# services/nasa_api.py
import requests
import pandas as pd
import streamlit as st
from datetime import date, timedelta

# Cache data for 1 hour so you don't hit API limits while testing
@st.cache_data(ttl=3600)
def fetch_asteroid_data(api_key, start_date, end_date):
    """
    Fetches Near Earth Objects from NASA NeoWs API.
    """
    url = "https://api.nasa.gov/neo/rest/v1/feed"
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "api_key": api_key
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Parse nested JSON into a flat list for easy display
        asteroids = []
        for day in data['near_earth_objects']:
            for neo in data['near_earth_objects'][day]:
                asteroids.append({
                    "id": neo['id'],
                    "name": neo['name'],
                    "date": neo['close_approach_data'][0]['close_approach_date'],
                    "velocity_kmh": float(neo['close_approach_data'][0]['relative_velocity']['kilometers_per_hour']),
                    "miss_distance_km": float(neo['close_approach_data'][0]['miss_distance']['kilometers']),
                    "diameter_max_m": neo['estimated_diameter']['meters']['estimated_diameter_max'],
                    "is_hazardous": neo['is_potentially_hazardous_asteroid']
                })
        
        return pd.DataFrame(asteroids)

    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to NASA API: {e}")
        return pd.DataFrame()