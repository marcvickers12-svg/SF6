import streamlit as st
import paho.mqtt.client as mqtt
import threading
from datetime import datetime
import plotly.graph_objects as go
import os
import sys

# ---------- Globals for logs ----------
mqtt_logs_global = []  # keep logs outside session_state

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
        "port": 8883,
        "topic": "sf6/test",
        "use_tls": True,
        "username": "",
        "password": ""
    }

# ---------- Logging Helper ----------
def log(msg):
    print(msg, file=sys.stderr)  # also prints to terminal
    mqtt_logs_global.append(msg)

# ---------- MQTT Callbacks ----------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        st.session_state.connected = True
        log("✅ on_connect: Connected successfully")
        client.subscribe(userdata["topic"])
        log(f"📡 Subscribed to {userdata['topic']}")
    else:
        st.session_state.connected = False
        log(f"❌ on_connect: Failed with return code {rc}")

def on_disconnect(client, userdata, rc):
    st.session_state.connected = False
    log(f"⚡ on_disconnect: Disconnected with return code {rc}")

def on_message(client, userdata, msg):
    try:
        value = float(msg.payload.decode())
        st.session_state.latest_value = value
        log(f"📩 on_message: {msg.topic} = {value}")
        log_to_csv("ZoneA", "Pressure", value)
    except Exception as e:
        log(f"⚠️ on_message error: {e}")

# ---------- MQTT Thread ----------
def start_mqtt(config):
    try:
        client = mqtt.Client(userdata=config)  # pass config into callbacks
        client.enable_logger()

        if config["username"]:
            client.username_pw_set(config["username"], config["password"])
            log(f"🔑 Using username '{config['username']}'")

        if config["use_tls"]:
            cert_path = os.path.join(os.path.dirname(__file__), "baltimore.pem")
            log(f"🔐 Using TLS cert: {cert_path}")
            client.tls_set(ca_certs=cert_path)

        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message

        log(f"🔌 Attempting connect to {config['broker']}:{config['port']}")
        client.connect(config["broker"], config["port"], 60)
        client.loop_forever()

    except Exception as e:
        log(f"💥 start_mqtt exception: {e}")
        st.session_state.connected = False

def ensure_mqtt_running(config):
    if st.session_state.mqtt_client is None:
        t = threading.Thread(target=start_mqtt, args=(config,), daemon=True)
        t.start()
        st.session_state.mqtt_client = t
        log("🚀 MQTT thread started")

# ---------- CSV Logging ----------
def log_to_csv(zone, sensor, value):
    date_str = datetime.now().strftime("%d-%m-%Y")
    filename = os.path.join("data", f"{zone}_{sensor}_{date_str}.csv".replace(" ", "_"))
    os.makedirs("data", exist_ok=True)
    file_exists = os.path.exists(filename)
    with open(filename, "a") as f:
        if not file_exists:
            f.write("timestamp,value\n")
        ts = datetime.now().isoformat(timespec="seconds")
        f.write(f"{ts},{value}\n")

# ---------- Streamlit UI ----------
st.title("SF₆ Gas Monitoring (HiveMQ Cloud Debug Mode)")

with st.sidebar:
    st.header("MQTT Settings")
    broker = st.text_input("Broker", st.session_state.config["broker"])
    port = st.number_input("Port", value=st.session_state.config["port"], step=1)
    topic = st.text_input("Topic", st.session_state.config["topic"])
    username = st.text_input("Username", st.session_state.config["username"])
    password = st.text_input("Password", st.session_state.config["password"], type="password")
    connect_btn = st.button("Connect")

    if connect_btn:
        st.session_state.config = {
            "broker": broker,
            "port": int(port),
            "topic": topic,
            "use_tls": True,
            "username": username,
            "password": password
        }
        ensure_mqtt_running(st.session_state.config)
        st.success("MQTT client started")

# Show connection status + debug logs
if st.session_state.connected:
    st.success(f"Connected to {st.session_state.config['broker']}:{st.session_state.config['port']}")
else:
    st.warning("Not connected")

if mqtt_logs_global:
    st.text_area("MQTT Debug Log", "\n".join(mqtt_logs_global[-50:]), height=250)

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
