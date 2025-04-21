import requests
import pandas as pd
import ta
import time
from datetime import datetime
from flask import Flask
from threading import Thread

# CONFIGURACIÓN
API_KEY = "8e0049007fcf4a21aa59a904ea8af292"
INTERVAL = "2min"
TELEGRAM_TOKEN = "7099030025:AAE7LsZWHPRtUejJGcae0pDzonHwbDTL-no"
TELEGRAM_CHAT_ID = "5989911212"

ACTIVOS = [
    # Criptomonedas principales
    "BTC/USD", "ETH/USD", "XRP/USD", "SOL/USD", "BNB/USD",
    "DOGE/USD", "ADA/USD", "DOT/USD", "AVAX/USD", "LTC/USD",

    # Divisas principales
    "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD",
    "USD/CAD", "NZD/USD", "EUR/JPY", "GBP/JPY"
]

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot señales cripto y forex activo."

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=data)

def obtener_datos(symbol):
    symbol_encoded = symbol.replace("/", "%2F")
    url = f"https://api.twelvedata.com/time_series?symbol={symbol_encoded}&interval={INTERVAL}&outputsize=100&apikey={API_KEY}"
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
    if df is None or len(df) < 30:
        return

    df["ema9"] = ta.trend.EMAIndicator(df["close"], window=9).ema_indicator()
    df["ema21"] = ta.trend.EMAIndicator(df["close"], window=21).ema_indicator()
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    df["cci"] = ta.trend.CCIIndicator(df["high"], df["low"], df["close"], window=20).cci()

    u = df.iloc[-1]
    a = df.iloc[-2]

    mensaje = None

    # Señal de COMPRA (CALL)
    if u["rsi"] < 35 and u["cci"] < -100 and u["ema9"] > u["ema21"] and u["close"] > a["close"]:
        mensaje = (
            f"🟢 *SEÑAL CALL* - {symbol}\n"
            f"📉 RSI: {round(u['rsi'], 2)} | CCI: {round(u['cci'], 2)}\n"
            f"🔺 EMA9 > EMA21 | Precio subiendo\n"
            f"⏱️ *Expiración sugerida:* 2-3 min"
        )

    # Señal de VENTA (PUT)
    elif u["rsi"] > 65 and u["cci"] > 100 and u["ema9"] < u["ema21"] and u["close"] < a["close"]:
        mensaje = (
            f"🔴 *SEÑAL PUT* - {symbol}\n"
            f"📈 RSI: {round(u['rsi'], 2)} | CCI: {round(u['cci'], 2)}\n"
            f"🔻 EMA9 < EMA21 | Precio bajando\n"
            f"⏱️ *Expiración sugerida:* 2-3 min"
        )

    if mensaje:
        enviar_telegram(mensaje)
        print(f"✅ Señal enviada - {symbol}")
    else:
        print(f"❌ Sin señal clara - {symbol}")

def ejecutar_bot():
    while True:
        for symbol in ACTIVOS:
            analizar(symbol)
        print("⏳ Esperando 2 minutos...\n")
        time.sleep(120)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    ejecutar_bot()
