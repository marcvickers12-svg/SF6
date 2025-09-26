import streamlit as st
import paho.mqtt.client as mqtt
import ssl
import threading
import time
import pandas as pd
import plotly.graph_objects as go

# ------------------------------
# Initialize session state
# ------------------------------
if "config" not in st.session_state:
    st.session_state.config = {
        "broker": "988df3573bd749bf8e37087a285287d0.s1.eu.hivemq.cloud",
        "port": 8883,
        "topic": "sf6/pressure",
        "username": "Elimpus",  # replace with your HiveMQ username
        "password": "YOUR_PASSWORD",  # replace with your HiveMQ password
        "tls_cert": "baltimore.pem",  # must be in repo
    }

if "mqtt_logs" not in st.session_state:
    st.session_state.mqtt_logs = []

if "connected" not in st.session_state:
    st.session_state.connected = False

if "latest_value" not in st.session_state:
    st.session_state.latest_value = 0.0

if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=["time", "value"])

# ------------------------------
# Logging helper
# ------------------------------
def log(msg):
    print(msg)  # goes to console
    st.session_state.mqtt_logs.append(msg)

# ------------------------------
# MQTT Callbacks
# ------------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log("✅ Connected to broker!")
        st.session_state.connected = True
        client.subscribe(st.session_state.config["topic"])
        log(f"📡 Subscribed to {st.session_state.config['topic']}")
    else:
        log(f"❌ Connection failed with code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = float(msg.payload.decode())
        st.session_state.latest_value = payload
        new_row = pd.DataFrame([{
            "time": pd.Timestamp.now(),
            "value": payload
        }])
        st.session_state.history = pd.concat(
            [st.session_state.history, new_row], ignore_index=True
        )
        log(f"📥 Message received: {payload}")
    except Exception as e:
        log(f"⚠️ Error parsing message: {e}")

# ------------------------------
# MQTT Thread Function
# ------------------------------
def start_mqtt():
    cfg = st.session_state.config
    try:
        client = mqtt.Client(protocol=mqtt.MQTTv311)
        client.username_pw_set(cfg["username"], cfg["password"])

        log(f"🔑 Using username '{cfg['username']}'")
        log(f"📜 Using TLS cert: {cfg['tls_cert']}")

        client.tls_set(
            ca_certs=cfg["tls_cert"],
            certfile=None,
            keyfile=None,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLSv1_2,
            ciphers=None,
        )

        client.on_connect = on_connect
        client.on_message = on_message

        log(f"🔌 Attempting connect to {cfg['broker']}:{cfg['port']}")
        client.connect(cfg["broker"], cfg["port"], 60)
        log("⏳ Waiting for broker response...")

        client.loop_forever()
    except Exception as e:
        log(f"💥 start_mqtt exception: {type(e).__name__}: {e}")

# ------------------------------
# UI Layout
# ------------------------------
st.title("SF₆ Gas Monitoring (HiveMQ Cloud Debug Mode)")

# Connection status
if st.session_state.connected:
    st.success("Connected to MQTT broker")
else:
    st.warning("Not connected")

# Debug log
st.subheader("MQTT Debug Log")
st.text_area("Log", "\n".join(st.session_state.mqtt_logs), height=200)

# Gauge display
st.subheader("Pressure (bar)")
gauge = go.Figure(
    go.Indicator(
        mode="gauge+number",
        value=st.session_state.latest_value,
        title={"text": "Gas Pressure"},
        gauge={
            "axis": {"range": [0, 10]},
            "bar": {"color": "blue"},
            "steps": [
                {"range": [0, 2], "color": "red"},
                {"range": [2, 4], "color": "yellow"},
                {"range": [4, 8], "color": "green"},
                {"range": [8, 10], "color": "orange"},
            ],
        },
    )
)
st.plotly_chart(gauge, use_container_width=True)

# Historical chart
st.subheader("History")
st.line_chart(st.session_state.history, x="time", y="value")

# ------------------------------
# Start MQTT Thread (only once)
# ------------------------------
if "mqtt_thread_started" not in st.session_state:
    st.session_state.mqtt_thread_started = True
    threading.Thread(target=start_mqtt, daemon=True).start()
    log("🚀 MQTT thread started")
