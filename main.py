import requests, pandas as pd, ta, time, csv
from datetime import datetime
from flask import Flask
from threading import Thread

# CONFIGURACIÓN
API_KEY = "8e0049007fcf4a21aa59a904ea8af292"
INTERVAL = "1min"
TELEGRAM_TOKEN = "7099030025:AAE7LsZWHPRtUejJGcae0pDzonHwbDTL-no"
TELEGRAM_CHAT_ID = "5989911212"

PARES = [
    "EUR/USD", "EUR/CAD", "EUR/CHF", "EUR/GBP", "EUR/JPY",
    "AUD/CAD", "AUD/CHF", "AUD/USD", "AUD/JPY",
    "USD/CHF", "USD/JPY", "USD/INR", "USD/CAD",
    "GBP/JPY", "USD/BDT", "USD/MXN", "EUR/NZD", "GBP/CHF",
    "CAD/JPY", "GBP/CAD", "CAD/CHF", "NZD/CAD", "EUR/AUD"
]

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    requests.post(url, data=data)

def guardar_csv(fecha, par, tipo, estrategia, precio, expiracion):
    with open("senales_cci_rsi.csv", "a", newline="") as f:
        csv.writer(f).writerow([fecha, par, tipo, estrategia, round(precio, 5), expiracion])

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

    # Indicadores CCI y RSI
    df["cci"] = ta.trend.CCIIndicator(high=df["high"], low=df["low"], close=df["close"], window=20).cci()
    df["rsi"] = ta.momentum.RSIIndicator(close=df["close"], window=14).rsi()

    u = df.iloc[-1]
    a = df.iloc[-2]

    estrategia = ""
    tipo = ""

    # Condiciones para señales
    if a["cci"] > 100 and u["cci"] < 100 and u["rsi"] < 70:
        estrategia = "CCI + RSI PUT"
        tipo = "PUT"
    elif a["cci"] < -100 and u["cci"] > -100 and u["rsi"] > 30:
        estrategia = "CCI + RSI CALL"
        tipo = "CALL"

    if estrategia:
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mensaje = (
            f"📊 Señal {tipo} en {symbol} ({fecha}):\n"
            f"{estrategia}\n"
            f"⏱️ Expiración sugerida: 2 min\n"
            f"📈 Confianza: ⭐⭐"
        )
        enviar_telegram(mensaje)
        guardar_csv(fecha, symbol, tipo, estrategia, u["close"], "2 min")
        print(mensaje)
    else:
        print(f"[{symbol}] ❌ Sin señal clara")

def iniciar():
    while True:
        print("⏳ Analizando todos los pares...")
        for par in PARES:
            analizar(par)
        print("🕒 Esperando 1 minuto...\n")
        time.sleep(60)

# Flask para mantener activo en Render
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot activo con estrategia: CCI + RSI (1min, expiración 2min)"

Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
iniciar()
