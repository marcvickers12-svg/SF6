# SF₆ Gas Monitoring Dashboard (Streamlit)

A simple SCADA-style dashboard for monitoring SF₆ gas pressure and density,
powered by MQTT and Streamlit.

## 🚀 Features
- MQTT client (paho-mqtt)
- Live gauge with digital readout (Plotly)
- CSV logging (per day, per sensor)
- Configurable broker/port/topic via sidebar

## 🛠️ Installation

```bash
git clone https://github.com/<your-username>/sf6-streamlit-dashboard.git
cd sf6-streamlit-dashboard
pip install -r requirements.txt
streamlit run app.py
```

## ☁️ Deploy on Streamlit Cloud
1. Push this repo to GitHub.  
2. Go to [Streamlit Cloud](https://streamlit.io/cloud).  
3. Connect your repo and deploy.  
