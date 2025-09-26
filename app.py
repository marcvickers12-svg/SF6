import streamlit as st
import paho.mqtt.client as mqtt
import threading
from datetime import datetime
import plotly.graph_objects as go
import os

# ---------- Session State ----------
if "mqtt_client" not in st.session_state:
    st.session_state.mqtt_client = None
if "latest_value" not in st.session_state:
    st.session_state.latest_value = 0.0
if "connected" not in st.session_state:
    st.session_state.connected = False
if "config" not in st.session_state:
    st.session_state.config = {
        "broker": "broker.hivemq.com",
        "port": 1883,
        "topic": "sf6/test",
        "use_tls": False,
        "username": "",
        "password": ""
    }

# ---------- MQTT Handling ----------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        st.session_state.connected = True
        client.subscribe(st.session_state.config["topic"])
    else:
        st.session_state.connected = False

def on_message(client, userdata, msg):
    try:
        value = float(msg.payload.decode())
        st.session_state.latest_value = value
        log_to_csv("ZoneA", "Pressure", value)
    except:
        pass

def start_mqtt():
    cfg = st.session_state.config
    client = mqtt.Client()
    if cfg["username"]:
        client.username_pw_set(cfg["username"], cfg["password"])
    if cfg["use_tls"]:
        client.tls_set()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(cfg["broker"], cfg["port"], 60)
    client.loop_forever()

def ensure_mqtt_running():
    if st.session_state.mqtt_client is None:
        t = threading.Thread(target=start_mqtt, daemon=True)
        t.start()
        st.session_state.mqtt_client = t

# ---------- CSV Logging ----------
def log_to_csv(zone, sensor, value):
    date_str = datetime.now().strftime("%d-%m-%Y")
    filename = os.path.join("data", f"{zone}_{sensor}_{date_str}.csv".replace(" ", "_"))
    file_exists = os.path.exists(filename)
    with open(filename, "a") as f:
        if not file_exists:
            f.write("timestamp,value\n")
        ts = datetime.now().isoformat(timespec="seconds")
        f.write(f"{ts},{value}\n")

# ---------- Streamlit UI ----------
st.title("SF₆ Gas Monitoring (Simple Prototype)")

with st.sidebar:
    st.header("MQTT Settings")
    broker = st.text_input("Broker", st.session_state.config["broker"])
    port = st.number_input("Port", value=st.session_state.config["port"], step=1)
    topic = st.text_input("Topic", st.session_state.config["topic"])
    use_tls = st.checkbox("Use TLS/SSL", st.session_state.config["use_tls"])
    username = st.text_input("Username", st.session_state.config["username"])
    password = st.text_input("Password", st.session_state.config["password"], type="password")
    connect_btn = st.button("Connect")

    if connect_btn:
        st.session_state.config = {
            "broker": broker,
            "port": int(port),
            "topic": topic,
            "use_tls": use_tls,
            "username": username,
            "password": password
        }
        ensure_mqtt_running()
        st.success("MQTT client started")

# Show connection status
if st.session_state.connected:
    st.success(f"Connected to {st.session_state.config['broker']}:{st.session_state.config['port']}")
else:
    st.warning("Not connected")

# Gauge
fig = go.Figure(go.Indicator(
    mode="gauge+number",
    value=st.session_state.latest_value,
    title={'text': "Pressure (bar)"},
    gauge={'axis': {'range': [0, 20]},
           'bar': {'color': "green"},
           'steps': [
               {'range': [0, 5], 'color': "red"},
               {'range': [5, 10], 'color': "yellow"},
               {'range': [10, 15], 'color': "green"},
               {'range': [15, 20], 'color': "red"}
           ]}
))
st.plotly_chart(fig, use_container_width=True)
