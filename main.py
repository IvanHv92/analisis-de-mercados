import requests, pandas as pd, ta, time, csv
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
    "AUD/CAD", "AUD/CHF", "AUD/USD", "AUD/JPY", "CAD/CHF",
    "USD/CHF", "USD/JPY", "USD/INR", "USD/CAD", "CAD/JPY",
    "GBP/JPY", "GBP/AUD", "EUR/AUD", "USD/BDT", "USD/EGP", "USD/MXN"
]

ULTIMAS_SENIALES = {}

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    requests.post(url, data=data)

def guardar_csv(fecha, par, tipo, estrategias, precio, expiracion):
    with open("senales_final.csv", "a", newline="") as f:
        csv.writer(f).writerow([fecha, par, tipo, estrategias, round(precio, 5), expiracion])

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
    df["ema9"] = ta.trend.EMAIndicator(df["close"], 9).ema_indicator()
    df["ema20"] = ta.trend.EMAIndicator(df["close"], 20).ema_indicator()
    df["ema50"] = ta.trend.EMAIndicator(df["close"], 50).ema_indicator()

    u = df.iloc[-1]
    a = df.iloc[-2]
    estrategias = []

    # EMA 9 cruza EMA 20 y ambas por encima o debajo de EMA 50
    if a["ema9"] < a["ema20"] and u["ema9"] > u["ema20"] and u["ema9"] > u["ema50"] and u["ema20"] > u["ema50"] and u["rsi"] > 50:
        estrategias.append("Triple EMA + RSI CALL")
    if a["ema9"] > a["ema20"] and u["ema9"] < u["ema20"] and u["ema9"] < u["ema50"] and u["ema20"] < u["ema50"] and u["rsi"] < 50:
        estrategias.append("Triple EMA + RSI PUT")

    if len(estrategias) >= 1:
        tipo = "CALL" if "CALL" in estrategias[0] else "PUT"
        fuerza = len(estrategias)
        expiracion = "5 min"
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        estrellas = "⭐" * fuerza
        mensaje = (
            f"📊 Señal {tipo} en {symbol} ({fecha}):\n"
            + "\n".join(estrategias) +
            f"\n⏱️ Expiración sugerida: {expiracion}\n"
            f"📈 Confianza: {estrellas}"
        )
        enviar_telegram(mensaje)
        guardar_csv(fecha, symbol, tipo, ", ".join(estrategias), u["close"], expiracion)
        print(mensaje)
    else:
        print(f"[{symbol}] ❌ Sin señal clara")

def iniciar():
    while True:
        print("⏳ Analizando todos los pares...")
        for par in PARES:
            analizar(par)
        print("🕒 Esperando 2 minutos...\n")
        time.sleep(120)

app = Flask('')

@app.route('/')
def home():
    return "✅ Bot activo con estrategia Triple EMA + RSI (cada 2 min)"

Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
iniciar()