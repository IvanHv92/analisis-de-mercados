import requests, pandas as pd, ta, time, csv
from datetime import datetime
from flask import Flask
from threading import Thread

# CONFIGURACIÓN
API_KEY = "8e0049007fcf4a21aa59a904ea8af292"
INTERVAL = "1min"  # Equivalente a 30 segundos en algunos proveedores si se duplica frecuencia
TELEGRAM_TOKEN = "7099030025:AAE7LsZWHPRtUejJGcae0pDzonHwbDTL-no"
TELEGRAM_CHAT_ID = "5989911212"

PARES = [
    "EUR/USD", "EUR/CAD", "EUR/CHF", "EUR/GBP", "EUR/JPY",
    "AUD/CAD", "AUD/CHF", "AUD/USD", "AUD/JPY",
    "USD/CHF", "USD/JPY", "USD/INR", "USD/CAD",
    "GBP/JPY", "USD/BDT", "USD/MXN"
]

ULTIMAS_SENIALES = {}

# STC personalizado
class SchaffTrendCycle:
    def __init__(self, close, length=10, fast=23, slow=50):
        self.macd = ta.trend.MACD(close, window_slow=slow, window_fast=fast)
        self.stoch = ta.momentum.StochasticOscillator(self.macd.macd(), self.macd.macd(), window=length)

    def stc(self):
        return self.stoch.stoch_signal()

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    requests.post(url, data=data)

def guardar_csv(fecha, par, tipo, estrategias, precio, expiracion):
    with open("senales_stc.csv", "a", newline="") as f:
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

    # Filtro de consolidación y velas extremas
    u = df.iloc[-1]
    if ((u["high"] - u["low"]) / u["close"]) > 0.02:
        print(f"⚠️ Ignorado {symbol} por volatilidad excesiva")
        return

    ahora = datetime.now()
    if symbol in ULTIMAS_SENIALES and (ahora - ULTIMAS_SENIALES[symbol]).total_seconds() < 120:
        print(f"⛔ Ignorada por antimartingala en {symbol}")
        return

    df["ema9"] = ta.trend.EMAIndicator(df["close"], 9).ema_indicator()
    df["ema21"] = ta.trend.EMAIndicator(df["close"], 21).ema_indicator()

    adx = ta.trend.ADXIndicator(high=df["high"], low=df["low"], close=df["close"])
    df["adx"] = adx.adx()
    df["+di"] = adx.adx_pos()
    df["-di"] = adx.adx_neg()

    stc = SchaffTrendCycle(df["close"], 12, 28, 40)
    df["stc"] = stc.stc()

    u = df.iloc[-1]
    a = df.iloc[-2]

    estrategias = []

    # 1. STC
    if a["stc"] < 0.25 and u["stc"] > 0.25:
        estrategias.append("STC CALL")
    elif a["stc"] > 0.75 and u["stc"] < 0.75:
        estrategias.append("STC PUT")

    # 2. EMA
    if a["ema9"] < a["ema21"] and u["ema9"] > u["ema21"]:
        estrategias.append("Cruce EMA CALL")
    elif a["ema9"] > a["ema21"] and u["ema9"] < u["ema21"]:
        estrategias.append("Cruce EMA PUT")

    # 3. ADX
    if u["adx"] > 20:
        if u["+di"] > u["-di"]:
            estrategias.append("ADX Fuerza CALL")
        else:
            estrategias.append("ADX Fuerza PUT")

    if len(estrategias) >= 3:
        tipo = "CALL" if "CALL" in " ".join(estrategias) else "PUT"
        fecha = ahora.strftime("%Y-%m-%d %H:%M:%S")
        mensaje = (
            f"📊 Señal {tipo} en {symbol} ({fecha}):\n"
            + "\n".join(estrategias) +
            "\n⏱️ Expiración sugerida: 2 minutos\n"
            f"📈 Confianza: ⭐⭐⭐"
        )
        enviar_telegram(mensaje)
        guardar_csv(fecha, symbol, tipo, ", ".join(estrategias), u["close"], "2 min")
        print(mensaje)
        ULTIMAS_SENIALES[symbol] = ahora
    else:
        print(f"[{symbol}] ❌ Señal insuficiente")

def iniciar():
    while True:
        print("⏳ Analizando pares con STC + EMA + ADX...")
        for par in PARES:
            analizar(par)
        print("🕒 Esperando 1 minuto...\n")
        time.sleep(60)

app = Flask('')

@app.route('/')
def home():
    return "✅ Bot STC+EMA+ADX activo (1min velas / 2min expiración)"

Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
iniciar()
