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
    "GBP/JPY", "USD/BDT", "USD/MXN"
]

ULTIMAS_SENIALES = {}

# Función para enviar mensajes a Telegram
def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    requests.post(url, data=data)

# Función para guardar en CSV
def guardar_csv(fecha, par, tipo, estrategia, precio, expiracion):
    with open("senales_schaff.csv", "a", newline="") as f:
        csv.writer(f).writerow([fecha, par, tipo, estrategia, round(precio, 5), expiracion])

# Función para obtener los datos de cada par
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

# Cálculo de Schaff Trend Cycle
def schaff_trend_cycle(close, high, low, macd_len, fast_len, slow_len):
    macd = ta.trend.MACD(close, window_slow=slow_len, window_fast=fast_len, window_sign=9)
    stoch_k = ta.momentum.StochasticOscillator(
        high=high,
        low=low,
        close=macd.macd(),
        window=macd_len
    ).stoch()
    return stoch_k

# Análisis de señales
def analizar(symbol):
    df = obtener_datos(symbol)
    if df is None:
        return

    df["stc"] = schaff_trend_cycle(df["close"], df["high"], df["low"], macd_len=12, fast_len=28, slow_len=40)
    u = df.iloc[-1]
    a = df.iloc[-2]

    if pd.isna(a["stc"]) or pd.isna(u["stc"]):
        print(f"⚠️ Insuficiente información en {symbol}")
        return

    estrategia = ""
    tipo = ""

    # CORREGIDO: Entrada PUT si el STC cruza hacia ABAJO de 0.75
    if a["stc"] > 0.75 and u["stc"] < 0.75:
        estrategia = "Schaff Trend Cycle PUT"
        tipo = "PUT"
    # Entrada CALL si el STC cruza hacia ARRIBA de 0.25
    elif a["stc"] < 0.25 and u["stc"] > 0.25:
        estrategia = "Schaff Trend Cycle CALL"
        tipo = "CALL"

    if estrategia:
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mensaje = (
            f"📊 Señal {tipo} en {symbol} ({fecha}):\n"
            f"{estrategia}\n"
            f"⏱️ Expiración sugerida: 2 min\n"
            f"📈 Indicador STC: {round(u['stc'], 3)}"
        )
        enviar_telegram(mensaje)
        guardar_csv(fecha, symbol, tipo, estrategia, u["close"], "2 min")
        print(mensaje)
    else:
        print(f"[{symbol}] ❌ Sin señal clara")

# Función principal
def iniciar():
    while True:
        print("⏳ Analizando todos los pares con Schaff Trend Cycle...")
        for par in PARES:
            analizar(par)
        print("🕒 Esperando 60 segundos...\n")
        time.sleep(60)

# Flask para mantener activo
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot Schaff activo (STC cruzando 0.75 y 0.25)"

Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
iniciar()
