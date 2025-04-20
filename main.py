import requests
import pandas as pd
import ta
import time
from datetime import datetime

# CONFIGURACIÓN
API_KEY = "8e0049007fcf4a21aa59a904ea8af292"
INTERVAL = "5min"
CRIPTOS = ["BTC/USD", "ETH/USD", "XRP/USD", "SOL/USD", "DOGE/USD", "ADA/USD"]

TELEGRAM_TOKEN = "7099030025:AAE7LsZWHPRtUejJGcae0pDzonHwbDTL-no"
TELEGRAM_CHAT_ID = "5989911212"

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"❌ Error enviando mensaje a Telegram: {e}")

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
    df["cci"] = ta.trend.CCIIndicator(df["high"], df["low"], df["close"], 20).cci()
    df["ema50"] = ta.trend.EMAIndicator(df["close"], 50).ema_indicator()

    u = df.iloc[-1]     # Última vela
    a = df.iloc[-2]     # Vela anterior

    rsi_val = round(u["rsi"], 2)
    cci_val = round(u["cci"], 2)
    ema50 = u["ema50"]

    mensaje = None

    # Señal estricta CALL
    if (
        rsi_val < 30 and
        cci_val < -100 and
        u["close"] > ema50 and
        a["close"] < a["ema50"]
    ):
        mensaje = (
            f"📊 Señal de COMPRA (CALL) en {symbol}\n"
            f"RSI: {rsi_val} | CCI: {cci_val}\n"
            f"EMA50 cruzada al alza\n⏱️ Entrada confiable"
        )

    # Señal estricta PUT
    elif (
        rsi_val > 70 and
        cci_val > 100 and
        u["close"] < ema50 and
        a["close"] > a["ema50"]
    ):
        mensaje = (
            f"📊 Señal de VENTA (PUT) en {symbol}\n"
            f"RSI: {rsi_val} | CCI: {cci_val}\n"
            f"EMA50 cruzada a la baja\n⏱️ Entrada confiable"
        )

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Análisis {symbol}")
    print(f"RSI: {rsi_val}, CCI: {cci_val}")

    if mensaje:
        print("✅ Señal enviada a Telegram")
        enviar_telegram(mensaje)
    else:
        print("❌ Sin señal clara")

def ejecutar_bot():
    while True:
        for cripto in CRIPTOS:
            analizar(cripto)
        print("⏳ Esperando 5 minutos...\n")
        time.sleep(300)

# EJECUCIÓN
ejecutar_bot()