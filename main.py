import requests, pandas as pd, ta, time, csv
from datetime import datetime
from flask import Flask
from threading import Thread

API_KEY = "8e0049007fcf4a21aa59a904ea8af292"
INTERVAL = "1min"
TELEGRAM_TOKEN = "7099030025:AAE7LsZWHPRtUejJGcae0pDzonHwbDTL-no"
TELEGRAM_CHAT_ID = "5989911212"

PARES = [
    "EUR/USD", "EUR/CAD", "EUR/CHF", "EUR/GBP", "EUR/JPY",
    "AUD/CAD", "AUD/CHF", "AUD/USD", "AUD/JPY",
    "USD/CHF", "USD/JPY", "USD/INR", "USD/CAD",
    "GBP/JPY", "USD/BDT", "USD/MXN", "CAD/JPY", "GBP/CAD",
    "CAD/CHF", "NZD/CAD", "EUR/AUD"
]

ULTIMAS_SENIALES = {}

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    requests.post(url, data=data)

def guardar_csv(fecha, par, tipo, estrategias, precio):
    with open("senales_cci.csv", "a", newline="") as f:
        csv.writer(f).writerow([fecha, par, tipo, estrategias, round(precio, 5)])

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

    cci1 = ta.trend.CCIIndicator(df["high"], df["low"], df["close"], window=20)
    cci2 = ta.trend.CCIIndicator(df["high"], df["low"], df["close"], window=50)
    cci3 = ta.trend.CCIIndicator(df["high"], df["low"], df["close"], window=100)

    df["cci20"] = cci1.cci()
    df["cci50"] = cci2.cci()
    df["cci100"] = cci3.cci()

    u = df.iloc[-1]
    estrategias = []

    if u["cci20"] > 100 and u["cci50"] > 100 and u["cci100"] > 100:
        estrategias.append("Triple CCI CALL")
    elif u["cci20"] < -100 and u["cci50"] < -100 and u["cci100"] < -100:
        estrategias.append("Triple CCI PUT")

    if estrategias:
        tipo = "CALL" if "CALL" in estrategias[0] else "PUT"
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mensaje = (
            f"📊 Señal {tipo} en {symbol} ({fecha}):
"
            + "
".join(estrategias) +
            f"
⏱️ Expiración sugerida: 5 min
📈 Confianza: ⭐"
        )
        enviar_telegram(mensaje)
        guardar_csv(fecha, symbol, tipo, ", ".join(estrategias), u["close"])
        print(mensaje)
    else:
        print(f"[{symbol}] ❌ Sin señal clara")

def iniciar():
    while True:
        print("⏳ Analizando todos los pares con CCI...")
        for par in PARES:
            analizar(par)
        print("🕒 Esperando 1 minuto...
")
        time.sleep(60)

app = Flask('')

@app.route('/')
def home():
    return "✅ Bot activo con estrategia: Triple CCI (cada 1 min)"

Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
iniciar()
