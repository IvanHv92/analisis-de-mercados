import requests
import pandas as pd
import ta
import time
from datetime import datetime
from flask import Flask
from threading import Thread

# CONFIGURACIÓN
API_KEY = "8e0049007fcf4a21aa59a904ea8af292"
INTERVAL = "5min"
CRIPTOS = ["BTC/USD", "ETH/USD", "XRP/USD", "SOL/USD", "DOGE/USD", "ADA/USD"]

TELEGRAM_TOKEN = "7099030025:AAE7LsZWHPRtUejJGcae0pDzonHwbDTL-no"
TELEGRAM_CHAT_ID = "5989911212"

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot de señales cripto (RSI + CCI) activo."

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"❌ Error enviando mensaje a Telegram: {e}")

def obtener_datos(symbol):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={INTERVAL}&outputsize=100&apikey={API_KEY}"
    r = requests.get(url).json()
    if "values" not in r:
        print(f"❌ Error al obtener datos de {symbol}")
        return None
    df = pd.DataFrame(r["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime")
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    return df

def analizar(symbol):
    df = obtener_datos(symbol)
    if df is None:
        return

    df["rsi"] = ta.momentum.RSIIndicator(df["close"], 14).rsi()
    df["cci"] = ta.trend.CCIIndicator(df["high"], df["low"], df["close"], 20).cci()
    u = df.iloc[-1]

    rsi_val = round(u["rsi"], 2)
    cci_val = round(u["cci"], 2)

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Análisis {symbol}")
    print(f"RSI: {rsi_val}, CCI: {cci_val}")

    mensaje = None

    if rsi_val < 28 and cci_val < -120:
        mensaje = f"📊 Señal de COMPRA (CALL) en {symbol}\nRSI: {rsi_val} | CCI: {cci_val}\n⏱️ Reversa potencial al alza"
    elif rsi_val > 72 and cci_val > 120:
        mensaje = f"📊 Señal de VENTA (PUT) en {symbol}\nRSI: {rsi_val} | CCI: {cci_val}\n⏱️ Reversa potencial a la baja"

    if mensaje:
        print("✅ Señal enviada a Telegram")
        enviar_telegram(mensaje)
    else:
        print("❌ Sin señal clara")

def ejecutar_bot():
    while True:
        for cripto in CRIPTOS:
            analizar(cripto)
        print("⏳ Esperando 5 minutos...\n")
        time.sleep(300)

# Ejecutar Flask y el bot en paralelo
if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    ejecutar_bot()