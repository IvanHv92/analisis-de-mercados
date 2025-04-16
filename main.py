import requests, pandas as pd, ta, time
from datetime import datetime
from flask import Flask
from threading import Thread

# CONFIGURACIÓN
API_KEY = "8e0049007fcf4a21aa59a904ea8af292"
INTERVAL = "5min"
TELEGRAM_TOKEN = "7099030025:AAE7LsZWHPRtUejJGcae0pDzonHwbDTL-no"
TELEGRAM_CHAT_ID = "5989911212"

PARES = [
    "EUR/USD", "EUR/CAD", "EUR/CHF", "EUR/GBP", "EUR/JPY",
    "AUD/CAD", "AUD/CHF", "AUD/USD", "AUD/JPY",
    "USD/CHF", "USD/JPY", "USD/INR", "USD/CAD",
    "GBP/JPY", "USD/BDT", "USD/EGP", "USD/MXN"
]

# Enviar mensaje a Telegram
def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    requests.post(url, data=data)

# Obtener datos del par
def obtener_datos(symbol):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={INTERVAL}&outputsize=30&apikey={API_KEY}"
    r = requests.get(url).json()
    if "values" not in r:
        return None
    df = pd.DataFrame(r["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime")
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    return df

# Analizar volatilidad
def analizar_volatilidad():
    seguros = []
    volatiles = []

    for par in PARES:
        df = obtener_datos(par)
        if df is None:
            continue

        u = df.iloc[-1]
        rango = (u["high"] - u["low"]) / u["close"]

        if rango > 0.04:
            volatiles.append(f"❌ {par} (Rango: {round(rango * 100, 2)}%)")
        else:
            seguros.append(f"✅ {par} (Rango: {round(rango * 100, 2)}%)")

    mensaje = "📊 *Análisis de Volatilidad (cada 30 min)*\n\n"
    mensaje += "🟢 Mercados seguros:\n" + ("\n".join(seguros) if seguros else "Ninguno") + "\n\n"
    mensaje += "🔴 Mercados volátiles:\n" + ("\n".join(volatiles) if volatiles else "Ninguno")
    enviar_telegram(mensaje)
    print(mensaje)

# Bucle cada 30 minutos
def iniciar():
    while True:
        print("🔍 Ejecutando análisis de volatilidad...")
        analizar_volatilidad()
        print("🕒 Esperando 30 minutos...\n")
        time.sleep(1800)

# Flask para mantener activo
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot de análisis de volatilidad activo (cada 30 min)"

Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
iniciar()
