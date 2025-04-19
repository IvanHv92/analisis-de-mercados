import requests
import pandas as pd
import ta
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

API_KEY = "8e0049007fcf4a21aa59a904ea8af292"
INTERVAL = "1min"
TELEGRAM_TOKEN = "7099030025:AAE7LsZWHPRtUejJGcae0pDzonHwbDTL-no"
TELEGRAM_CHAT_ID = "5989911212"

SYMBOLS = [
    "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "NZD/USD",
    "EUR/JPY", "GBP/JPY", "EUR/GBP", "USD/CAD", "AUD/JPY", "EUR/CHF",
    "GBP/CHF", "CAD/JPY", "NZD/JPY", "USD/SGD", "EUR/CAD", "EUR/AUD",
    "GBP/AUD", "AUD/CAD", "NZD/CAD", "AUD/NZD", "CHF/JPY", "USD/HKD",
    "USD/TRY", "EUR/TRY", "GBP/NZD", "EUR/NZD", "USD/MXN", "USD/ZAR"
]

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Error enviando mensaje Telegram: {e}")

def fetch_data(symbol):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol.replace('/', '')}&interval={INTERVAL}&outputsize=100&apikey={API_KEY}&format=JSON"
    try:
        response = requests.get(url)
        data = response.json()
        if "values" not in data:
            print(f"[{symbol}] Respuesta sin 'values': {data}")
            return None
        df = pd.DataFrame(data["values"])
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("datetime")
        df.set_index("datetime", inplace=True)
        df = df.astype(float)
        return df
    except Exception as e:
        print(f"Error al obtener datos de {symbol}: {e}")
        return None

def check_signal(df):
    df["ema9"] = ta.trend.ema_indicator(df["close"], window=9)
    df["ema21"] = ta.trend.ema_indicator(df["close"], window=21)
    df["rsi"] = ta.momentum.rsi(df["close"], window=14)
    df["macd_hist"] = ta.trend.macd_diff(df["close"])
    df["adx"] = ta.trend.adx(df["high"], df["low"], df["close"], window=14)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    ema_bullish = last["ema9"] > last["ema21"] and prev["ema9"] <= prev["ema21"]
    ema_bearish = last["ema9"] < last["ema21"] and prev["ema9"] >= prev["ema21"]
    rsi_buy = last["rsi"] < 30
    rsi_sell = last["rsi"] > 70
    macd_buy = last["macd_hist"] > 0 and prev["macd_hist"] < 0
    macd_sell = last["macd_hist"] < 0 and prev["macd_hist"] > 0
    adx_strong = last["adx"] > 25
    volatility_ok = (last["high"] - last["low"]) / last["close"] < 0.03
    vela_bullish = last["close"] > last["open"] and last["low"] < prev["low"]
    vela_bearish = last["close"] < last["open"] and last["high"] > prev["high"]

    if ema_bullish and rsi_buy and macd_buy and adx_strong and volatility_ok and vela_bullish:
        return "CALL"
    elif ema_bearish and rsi_sell and macd_sell and adx_strong and volatility_ok and vela_bearish:
        return "PUT"
    else:
        return None

def analyze_pair(symbol):
    df = fetch_data(symbol)
    if df is not None:
        signal = check_signal(df)
        if signal:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            message = f"SEÑAL {signal} en {symbol} - Expiración: 5 minutos\nHora: {timestamp}"
            print(message)
            send_telegram_message(message)

def run_bot():
    while True:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Iniciando análisis...")
        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(analyze_pair, SYMBOLS)
        time.sleep(60)

if __name__ == "__main__":
    run_bot()