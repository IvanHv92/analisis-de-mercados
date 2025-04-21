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
TELEGRAM_TOKEN = "7099030025:AAE7LsZWHPRtUejJGcae0pDzonHwbDTL-no"
TELEGRAM_CHAT_ID = "5989911212"

ACTIVOS = [
    # Metales
    "XAU/USD", "XAG/USD", "COPPER/USD",

    # Criptomonedas
    "BTC/USD", "ETH/USD", "XRP/USD", "SOL/USD", "DOGE/USD", "ADA/USD",
    "DOT/USD", "LTC/USD", "TRUMP/USD", "AVAX/USD", "SHIB/USD", "BNB/USD",
    "MATIC/USD", "UNI/USD", "LINK/USD", "XLM/USD", "NEAR/USD",

    # Divisas
    "EUR/AUD", "EUR/USD", "AUD/USD", "USD/CAD", "USD/MXN",
    "USD/CHF", "GBP/USD", "NZD/USD", "USD/JPY", "GBP/JPY",

    # Acciones
    "BA", "GME", "AAPL", "NFLX", "TSLA", "META",
    "MSFT", "AMC", "AMZN", "GOOGL", "MRNA", "NVDA",

    # Token TRUMP
    "TRUMP/USD"
]

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot RSI + CCI activo con reversas confirmadas y potenciales."

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"❌ Error enviando mensaje a Telegram: {e}")

def obtener_datos(symbol):
    safe_symbol = symbol.replace("/", "%2F")
    url = f"https://api.twelvedata.com/time_series?symbol={safe_symbol}&interval={INTERVAL}&outputsize=100&apikey={API_KEY}"
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
    a = df.iloc[-2]
    rsi_val = round(u["rsi"], 2)
    cci_val = round(u["cci"], 2)

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Análisis {symbol}")
    print(f"RSI: {rsi_val}, CCI: {cci_val}")

    mensaje = None
    ultimos = df.tail(5)
    sobreventa = ultimos[(ultimos["rsi"] < 30) & (ultimos["cci"] < -100)]
    sobrecompra = ultimos[(ultimos["rsi"] > 70) & (ultimos["cci"] > 100)]

    if not sobreventa.empty:
        if u["rsi"] > 40 and u["cci"] > 0 and u["close"] > a["close"]:
            mensaje = (
                f"🟩 *NUEVA SEÑAL (CALL)* - 🚀 *COMPRA*\n\n"
                f"🔹 *Activo:* {symbol}\n"
                f"📊 RSI: {rsi_val}\n"
                f"📊 CCI: {cci_val}\n\n"
                f"🔁 *Subida fuerte tras sobreventa reciente*\n"
                f"⏱️ *Expiración sugerida:* 5 min"
            )
    elif not sobrecompra.empty:
        if u["rsi"] < 60 and u["cci"] < 0 and u["close"] < a["close"]:
            mensaje = (
                f"🟥 *NUEVA SEÑAL (PUT)* - 🔥 *VENTA*\n\n"
                f"🔹 *Activo:* {symbol}\n"
                f"📊 RSI: {rsi_val}\n"
                f"📊 CCI: {cci_val}\n\n"
                f"🔻 *Bajada fuerte tras sobrecompra reciente*\n"
                f"⏱️ *Expiración sugerida:* 5 min"
            )
    elif u["rsi"] < 30 and u["cci"] < -100:
        mensaje = (
            f"🟨 *POSIBLE REVERSA (CALL)* - 👀 *VIGILANCIA*\n\n"
            f"🔹 *Activo:* {symbol}\n"
            f"📊 RSI: {rsi_val}\n"
            f"📊 CCI: {cci_val}\n\n"
            f"⚠️ *Sobreventa detectada, esperando confirmación*"
        )
    elif u["rsi"] > 70 and u["cci"] > 100:
        mensaje = (
            f"🟨 *POSIBLE REVERSA (PUT)* - 👀 *VIGILANCIA*\n\n"
            f"🔹 *Activo:* {symbol}\n"
            f"📊 RSI: {rsi_val}\n"
            f"📊 CCI: {cci_val}\n\n"
            f"⚠️ *Sobrecompra detectada, esperando confirmación*"
        )

    if mensaje:
        enviar_telegram(mensaje)
        print("✅ Señal enviada")
    else:
        print("❌ Sin señal clara")

def ejecutar_bot():
    while True:
        for activo in ACTIVOS:
            analizar(activo)
        print("⏳ Esperando 5 minutos...\n")
        time.sleep(300)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    ejecutar_bot()
