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

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    requests.post(url, data=data)

def guardar_csv(fecha, par, tipo, precio, expiracion):
    with open("senales_schaff.csv", "a", newline="") as f:
        csv.writer(f).writerow([fecha, par, tipo, round(precio, 5), expiracion])

def obtener_datos(symbol):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={INTERVAL}&outputsize=200&apikey={API_KEY}"
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

def calcular_schaff(df):
    macd = ta.trend.MACD(df["close"], window_slow=40, window_fast=28, window_sign=9)
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    
    stoch = ta.momentum.StochasticOscillator(high=df["high"], low=df["low"], close=df["macd"], window=12)
    df["schaff"] = stoch.stoch_signal()
    return df

def analizar(symbol):
    df = obtener_datos(symbol)
    if df is None:
        return
    
    try:
        df = calcular_schaff(df)
    except Exception as e:
        print(f"⚠️ Error al calcular Schaff en {symbol}: {e}")
        return

    u = df.iloc[-1]
    a = df.iloc[-2]

    if u["schaff"] < 25 and a["schaff"] > u["schaff"]:
        tipo = "CALL"
    elif u["schaff"] > 75 and a["schaff"] < u["schaff"]:
        tipo = "PUT"
    else:
        print(f"[{symbol}] ❌ Sin cruce en zonas extremas")
        return

    ahora = datetime.now()
    fecha = ahora.strftime("%Y-%m-%d %H:%M:%S")
    expiracion = "2 min"
    mensaje = (
        f"📊 Señal {tipo} en {symbol} ({fecha}):\n"
        f"Schaff Trend Cycle = {round(u['schaff'], 2)}\n"
        f"⏱️ Expiración sugerida: {expiracion}\n"
        f"📈 Confirmación por cruce en zona {'baja' if tipo=='CALL' else 'alta'}"
    )

    enviar_telegram(mensaje)
    guardar_csv(fecha, symbol, tipo, u["close"], expiracion)
    print(mensaje)

def iniciar():
    while True:
        print("⏳ Analizando todos los pares...")
        for par in PARES:
            analizar(par)
        print("🕒 Esperando 1 minuto...\n")
        time.sleep(60)

app = Flask('')

@app.route('/')
def home():
    return "✅ Bot activo con Schaff Trend Cycle (30s velas, exp 2min)"

Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
iniciar()
