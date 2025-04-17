import requests, pandas as pd, ta, time, csv
from datetime import datetime
from flask import Flask
from threading import Thread

# CONFIGURACIÓN
API_KEY = "8e0049007fcf4a21aa59a904ea8af292"
INTERVAL = "1min"
TELEGRAM_TOKEN = "7099030025:AAE7LsZWHPRtUejJGcae0pDzonHwbDTL-no"
TELEGRAM_CHAT_ID = "5989911212"

# Pares a analizar
PARES = ["EUR/USD", "USD/JPY", "GBP/USD", "USD/CAD", "AUD/USD"]
ULTIMAS_SENIALES = {}

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    requests.post(url, data=data)

def guardar_csv(fecha, par, tipo, estrategias, precio, expiracion):
    with open("senales_ema_macd_rsi.csv", "a", newline="") as f:
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
    if df is None: return

    # Indicadores técnicos
    df["ema5"] = ta.trend.EMAIndicator(df["close"], 5).ema_indicator()
    df["ema10"] = ta.trend.EMAIndicator(df["close"], 10).ema_indicator()
    df["ema20"] = ta.trend.EMAIndicator(df["close"], 20).ema_indicator()

    macd = ta.trend.MACD(df["close"], window_slow=13, window_fast=5, window_sign=3)
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"] = macd.macd_diff()

    df["rsi"] = ta.momentum.RSIIndicator(df["close"], 7).rsi()

    u = df.iloc[-1]
    a = df.iloc[-2]
    estrategias = []

    # --- FILTRO DE VOLATILIDAD ---
    rango = (u["high"] - u["low"]) / u["close"]
    if rango > 0.02:
        print(f"[{symbol}] ⚠️ Alta volatilidad. Señal ignorada")
        return

    # --- Triple EMA + MACD + RSI CALL ---
    if u["ema5"] > u["ema10"] > u["ema20"] and (u["ema5"] - u["ema20"]) > 0.02:
        if a["macd"] < a["macd_signal"] and u["macd"] > u["macd_signal"] and u["macd_hist"] > a["macd_hist"] and u["rsi"] > 55:
            estrategias.append("Triple EMA + MACD + RSI CALL")

    # --- Triple EMA + MACD + RSI PUT ---
    elif u["ema5"] < u["ema10"] < u["ema20"] and (u["ema20"] - u["ema5"]) > 0.02:
        if a["macd"] > a["macd_signal"] and u["macd"] < u["macd_signal"] and u["macd_hist"] < a["macd_hist"] and u["rsi"] < 45:
            estrategias.append("Triple EMA + MACD + RSI PUT")

    if estrategias:
        tipo = "CALL" if "CALL" in estrategias[0] else "PUT"
        clave = f"{symbol}_{tipo}"
        if ULTIMAS_SENIALES.get(symbol) == clave:
            print(f"[{symbol}] ⛔ Señal repetida")
            return
        ULTIMAS_SENIALES[symbol] = clave

        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mensaje = (
            f"✅ Señal {tipo} en {symbol}\n"
            + "\n".join(estrategias) +
            f"\n⏱️ Expiración sugerida: 2 min\n"
            f"🕒 {fecha}"
        )
        enviar_telegram(mensaje)
        guardar_csv(fecha, symbol, tipo, ", ".join(estrategias), u["close"], "2 min")
        print(mensaje)
    else:
        print(f"[{symbol}] ❌ Sin señal clara")

def iniciar():
    while True:
        print("⏳ Analizando pares...")
        for par in PARES:
            analizar(par)
        print("⏱️ Esperando 1 minuto...\n")
        time.sleep(60)

# Flask keep-alive para Render
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot activo: Triple EMA + MACD + RSI | 1min velas | 2min expiración | filtro de volatilidad"

Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
iniciar()