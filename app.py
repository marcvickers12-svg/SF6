import streamlit as st
import paho.mqtt.client as mqtt
import ssl
import threading
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
        "username": "",
        "password": "",
        "tls_cert": "baltimore.pem",
    }

if "mqtt_logs" not in st.session_state:
    st.session_state.mqtt_logs = []

if "connected" not in st.session_state:
    st.session_state.connected = False

if "latest_value" not in st.session_state:
    st.session_state.latest_value = 0.0

if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=["time", "value"])

# Prevent Altair "empty dataframe" warnings
if st.session_state.history.empty:
    st.session_state.history = pd.DataFrame([{"time": pd.Timestamp.now(), "value": 0.0}])

# ------------------------------
# Logging helper
# ------------------------------
def log(msg):
    print(msg)
    st.session_state.mqtt_logs.append(msg)

# ------------------------------
# MQTT Callbacks
# ------------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log("✅ Connected to broker!")
        st.session_state.connected = True
        client.subscribe(userdata["topic"])
        log(f"📡 Subscribed to {userdata['topic']}")
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
def start_mqtt(config):
    try:
        client = mqtt.Client(protocol=mqtt.MQTTv311, userdata=config)
        if config["username"]:
            client.username_pw_set(config["username"], config["password"])
            log(f"🔑 Using username '{config['username']}'")

        client.tls_set(
            ca_certs=config["tls_cert"],
            certfile=None,
            keyfile=None,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLSv1_2,
            ciphers=None,
        )

        client.on_connect = on_connect
        client.on_message = on_message

        log(f"🔌 Attempting connect to {config['broker']}:{config['port']}")
        client.connect(config["broker"], config["port"], 60)
        log("⏳ Waiting for broker response...")

        client.loop_forever()
    except Exception as e:
        log(f"💥 start_mqtt exception: {type(e).__name__}: {e}")

# ------------------------------
# Sidebar: Broker Login Panel
# ------------------------------
st.sidebar.header("🔧 MQTT Settings")

st.session_state.config["broker"] = st.sidebar.text_input(
    "Broker URL", st.session_state.config["broker"]
)
st.session_state.config["port"] = st.sidebar.number_input(
    "Port", value=st.session_state.config["port"], step=1
)
st.session_state.config["topic"] = st.sidebar.text_input(
    "Topic", st.session_state.config["topic"]
)
st.session_state.config["username"] = st.sidebar.text_input(
    "Username", st.session_state.config["username"]
)
st.session_state.config["password"] = st.sidebar.text_input(
    "Password", st.session_state.config["password"], type="password"
)

# Reconnect button
if st.sidebar.button("🔄 Reconnect"):
    st.session_state.connected = False
    cfg_copy = dict(st.session_state.config)  # safe copy for thread
    threading.Thread(target=start_mqtt, args=(cfg_copy,), daemon=True).start()
    log("🚀 MQTT reconnect triggered")

# ------------------------------
# Main UI
# ------------------------------
st.title("SF₆ Gas Monitoring (HiveMQ Cloud Debug Mode)")

if st.session_state.connected:
    st.success("Connected to MQTT broker")
else:
    st.warning("Not connected")

st.subheader("MQTT Debug Log")
st.text_area("Log", "\n".join(st.session_state.mqtt_logs), height=200)

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

st.subheader("History")
st.line_chart(st.session_state.history, x="time", y="value")
