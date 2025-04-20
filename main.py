import requests
import pandas as pd
import ta
import time
from datetime import datetime

# CONFIGURACIÓN
API_KEY = "8e0049007fcf4a21aa59a904ea8af292"
INTERVAL = "5min"
CRIPTOS = ["BTC/USD", "ETH/USD", "XRP/USD", "SOL/USD", "DOGE/USD", "ADA/USD"]

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
    return df

def analizar(symbol):
    df = obtener_datos(symbol)
    if df is None:
        return

    df["rsi"] = ta.momentum.RSIIndicator(df["close"], 14).rsi()
    df["cci"] = ta.trend.CCIIndicator(df["close"], df["close"], df["close"], 20).cci()
    u = df.iloc[-1]

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Análisis {symbol}")
    print(f"RSI: {round(u['rsi'], 2)}, CCI: {round(u['cci'], 2)}")

    if u["rsi"] < 30 and u["cci"] < -100:
        print("✅ Señal CALL (posible reversa al alza)")
    elif u["rsi"] > 70 and u["cci"] > 100:
        print("✅ Señal PUT (posible reversa a la baja)")
    else:
        print("❌ Sin señal clara")

def ejecutar_bot():
    while True:
        for cripto in CRIPTOS:
            analizar(cripto)
        print("⏳ Esperando 5 minutos...\n")
        time.sleep(300)  # 5 minutos

ejecutar_bot()