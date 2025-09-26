import streamlit as st
import paho.mqtt.client as mqtt
import threading, os

# --------------------------
# Global safe log store (thread-safe)
# --------------------------
log_buffer = []
log_lock = threading.Lock()

def log(msg: str):
    """Thread-safe logging (only touches global buffer)."""
    global log_buffer
    with log_lock:
        log_buffer.append(msg)
    print(msg)

# --------------------------
# Session state init
# --------------------------
if "mqtt_logs" not in st.session_state:
    st.session_state.mqtt_logs = []
if "connected" not in st.session_state:
    st.session_state.connected = False
if "mqtt_client" not in st.session_state:
    st.session_state.mqtt_client = None
if "config" not in st.session_state:
    st.session_state.config = {
        "broker": "",
        "port": 8883,
        "username": "",
        "password": "",
        "topic": "sf6/test",
        "use_tls": True,
    }

# --------------------------
# MQTT callbacks
# --------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log("✅ Connected to broker")
        topic = st.session_state.config["topic"]
        client.subscribe(topic)
        log(f"📡 Subscribed to topic: {topic}")
        st.session_state.connected = True
    else:
        log(f"❌ Failed to connect. Return code: {rc} "
            "(5 = unauthorized / bad username or password)")

def on_disconnect(client, userdata, rc):
    log("🔌 Disconnected from broker")
    st.session_state.connected = False

def on_message(client, userdata, msg):
    log(f"📥 Message received on {msg.topic}: {msg.payload.decode()}")

# --------------------------
# MQTT worker
# --------------------------
def start_mqtt(config):
    try:
        client = mqtt.Client()
        if config["username"]:
            client.username_pw_set(config["username"], config["password"])
            log(f"🔑 Using username '{config['username']}'")
        if config["use_tls"]:
            cert_path = os.path.join(os.path.dirname(__file__), "baltimore.pem")
            client.tls_set(ca_certs=cert_path)
            log(f"🔐 Using TLS cert: {cert_path}")

        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message

        log(f"🔌 Attempting connect to {config['broker']}:{config['port']}")
        client.connect(config["broker"], config["port"], 60)
        client.loop_forever()
    except Exception as e:
        log(f"💥 start_mqtt exception: {e}")

def ensure_mqtt_running(config):
    if st.session_state.mqtt_client is None:
        t = threading.Thread(target=start_mqtt, args=(config,), daemon=True)
        t.start()
        st.session_state.mqtt_client = t
        log("🚀 MQTT thread started")

# --------------------------
# Streamlit UI
# --------------------------
st.title("SF₆ Gas Monitoring (HiveMQ Cloud Debug Mode)")

with st.sidebar:
    st.subheader("MQTT Settings")
    st.session_state.config["broker"] = st.text_input("Broker", st.session_state.config["broker"])
    st.session_state.config["port"] = st.number_input("Port", 0, 65535, st.session_state.config["port"])
    st.session_state.config["username"] = st.text_input("Username", st.session_state.config["username"])
    st.session_state.config["password"] = st.text_input("Password", st.session_state.config["password"], type="password")
    st.session_state.config["topic"] = st.text_input("Topic", st.session_state.config["topic"])
    st.session_state.config["use_tls"] = st.checkbox("Use TLS/SSL", st.session_state.config["use_tls"])

    if st.button("Connect"):
        ensure_mqtt_running(st.session_state.config)

# --------------------------
# Sync global logs into session state
# --------------------------
with log_lock:
    if log_buffer:
        st.session_state.mqtt_logs.extend(log_buffer)
        log_buffer.clear()

# --------------------------
# Status + Debug Log
# --------------------------
status = "✅ Connected" if st.session_state.connected else "⚠️ Not connected"
st.info(status)

st.subheader("MQTT Debug Log")
st.text_area("Log", value="\n".join(st.session_state.mqtt_logs), height=200)
