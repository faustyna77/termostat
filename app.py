import streamlit as st
import pandas as pd
from influxdb_client import InfluxDBClient
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

import os
from dotenv import load_dotenv

# Ładowanie zmiennych środowiskowych



# ================================
# KONFIGURACJA STRONY
# ================================
st.set_page_config(page_title="🌡️ Monitoring temperatury", layout="wide")



st.title("🌡️ Termostat samochodowy - zdalne pomiary")
st.write("Copyright © 2025 Faustyna Misiura")

# ================================
# KONFIGURACJA INFLUXDB
# ================================
load_dotenv()
INFLUXDB_URL = st.secrets["INFLUXDB_URL"]
INFLUXDB_TOKEN = st.secrets["INFLUXDB_TOKEN"]
INFLUXDB_ORG = st.secrets["INFLUXDB_ORG"]
INFLUXDB_BUCKET = st.secrets["INFLUXDB_BUCKET"]



client = InfluxDBClient(
    url=INFLUXDB_URL,
    token=INFLUXDB_TOKEN,
    org=INFLUXDB_ORG
)
query_api = client.query_api()

# ================================
# FUNKCJA POBIERAJĄCA DANE
# ================================
def query_sensor_data(seconds=300, location="office", sensor="temp"):
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -{seconds}s)
      |> filter(fn: (r) => r["_measurement"] == "point")
      |> filter(fn: (r) => r["device"] == "ESP32")
      |> filter(fn: (r) => r["location"] == "{location}")
      |> filter(fn: (r) => r["sensor"] == "{sensor}")
      |> aggregateWindow(every: 10s, fn: mean, createEmpty: false)
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> keep(columns: ["_time", "temperature"])
    '''
    tables = query_api.query(query)
    data = []

    for table in tables:
        for record in table.records:
            data.append({
                "time": record.get_time(),
                "temperature": record.values.get("temperature"),
            })
    return data

# ================================
# INTERFEJS STREAMLIT
# ================================
st.sidebar.header("📍 Filtry")
location = st.sidebar.selectbox("Lokalizacja", ["office"])
sensor = st.sidebar.selectbox("Sensor", ["temp"])
seconds = st.sidebar.slider("Zakres czasu (sekundy)", 60, 1800, 300, step=60)

data = query_sensor_data(seconds, location, sensor)
df = pd.DataFrame(data)

if df.empty:
    st.warning("Brak danych w wybranym zakresie.")
else:
    df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_convert('Europe/Warsaw')

    df.set_index("time", inplace=True)

    st.subheader("📈 Wykres temperatury (°C)")
    fig = px.line(df, x=df.index, y="temperature", labels={"time": "Czas", "temperature": "Temperatura (°C)"})
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🧾 Ostatnie odczyty")
    st.dataframe(df.tail(10))
