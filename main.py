import requests, pandas as pd, ta, time, csv
from datetime import datetime
from flask import Flask
from threading import Thread

# CONFIGURACIÓN
API_KEY = "8e0049007fcf4a21aa59a904ea8af292"
INTERVAL = "5min"  # Velas de 5 minutos
TELEGRAM_TOKEN = "7099030025:AAE7LsZWHPRtUejJGcae0pDzonHwbDTL-no"
TELEGRAM_CHAT_ID = "5989911212"

PARES = [
    "EURUSD", "EURCAD", "EURCHF", "EURGBP", "EURJPY",
    "AUDCAD", "AUDCHF", "AUDUSD", "AUDJPY",
    "USDCHF", "USDJPY", "USDINR", "USDCAD",
    "GBPJPY", "USDBDT", "USDMXN",
    "CADJPY", "GBPCAD", "CADCHF", "NZDCAD", "EURAUD"
]

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    requests.post(url, data=data)

def guardar_csv(fecha, par, tipo, estrategia, precio, expiracion):
    with open("senales_multicriterio.csv", "a", newline="") as f:
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
    df["open"] = df["open"].astype(float)
    return df

def analizar(symbol):
    df = obtener_datos(symbol)
    if df is None:
        return

    # Indicadores
    df["ema9"] = ta.trend.ema_indicator(df["close"], window=9)
    df["ema21"] = ta.trend.ema_indicator(df["close"], window=21)
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    df["macd_line"] = ta.trend.macd(df["close"], window_slow=26, window_fast=12)
    df["macd_signal"] = ta.trend.macd_signal(df["close"], window_slow=26, window_fast=12)
    df["adx"] = ta.trend.adx(df["high"], df["low"], df["close"], window=14)

    u = df.iloc[-1]
    a = df.iloc[-2]

    estrategia = ""
    tipo = ""

    # Reglas
    cruce_ema_call = a["ema9"] < a["ema21"] and u["ema9"] > u["ema21"]
    cruce_ema_put = a["ema9"] > a["ema21"] and u["ema9"] < u["ema21"]

    rsi_oversold = u["rsi"] < 30
    rsi_overbought = u["rsi"] > 70

    macd_call = a["macd_line"] < a["macd_signal"] and u["macd_line"] > u["macd_signal"]
    macd_put = a["macd_line"] > a["macd_signal"] and u["macd_line"] < u["macd_signal"]

    adx_fuerte = u["adx"] > 25
    volatilidad_ok = (u["high"] - u["low"]) / u["close"] < 0.03

    vela_rechazo_call = u["close"] > u["open"] and u["low"] < a["low"]
    vela_rechazo_put = u["close"] < u["open"] and u["high"] > a["high"]

    if all([cruce_ema_call, rsi_oversold, macd_call, adx_fuerte, volatilidad_ok, vela_rechazo_call]):
        estrategia = "MULTI-INDICADORES CALL"
        tipo = "CALL"
    elif all([cruce_ema_put, rsi_overbought, macd_put, adx_fuerte, volatilidad_ok, vela_rechazo_put]):
        estrategia = "MULTI-INDICADORES PUT"
        tipo = "PUT"

    if estrategia:
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        symbol_display = symbol[:3] + "/" + symbol[3:]
        mensaje = (
            f"📊 Señal {tipo} en {symbol_display} ({fecha}):\n"
            f"{estrategia}\n"
            f"⏱️ Expiración sugerida: 5 minutos\n"
            f"📈 Confirmada por: EMA + RSI + MACD + ADX + Vela"
        )
        enviar_telegram(mensaje)
        guardar_csv(fecha, symbol_display, tipo, estrategia, u["close"], "5 min")
        print(mensaje)
    else:
        print(f"[{symbol}] ❌ Sin señal clara")

def iniciar():
    while True:
        print("⏳ Analizando todos los pares...")
        for par in PARES:
            analizar(par)
        print("🕒 Esperando 5 minutos...\n")
        time.sleep(300)  # 5 minutos

# Flask para mantener activo en Render
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot activo con estrategia MULTI-INDICADOR (EMA + RSI + MACD + ADX + vela) [5min]"

Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
iniciar()