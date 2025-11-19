import time
from datetime import datetime

import requests
import pandas as pd
import ta

print("✅ Iniciando script main.py...")

# =========================
# CONFIGURACIÓN
# =========================

# Tu API Key de Twelve Data
API_KEY = "8e0049007fcf4a21aa59a904ea8af292"

# Opcional: si quieres señales por Telegram, pon aquí tus datos.
# Si los dejas vacíos, el bot SOLO imprimirá las señales en consola.
TELEGRAM_TOKEN = ""  # ej. "123456789:ABCDEF..."
CHAT_ID = ""         # ej. "123456789"

# Lista de pares a analizar (los que me mandaste en las capturas)
SYMBOLS = [
    "USD/IDR", "USD/INR", "USD/JPY", "USD/MXN", "USD/NGN",
    "USD/PHP", "USD/PKR", "USD/TRY", "USD/ZAR",

    "NZD/JPY", "NZD/USD", "USD/ARS", "USD/BDT", "USD/BRL",
    "USD/CAD", "USD/CHF", "USD/COP", "USD/DZD", "USD/EGP",

    "EUR/JPY", "EUR/NZD", "EUR/SGD", "EUR/USD",
    "GBP/AUD", "GBP/CAD", "GBP/CHF", "GBP/JPY",
    "GBP/NZD", "GBP/USD",

    "AUD/CHF", "AUD/JPY", "AUD/NZD", "AUD/USD",
    "CAD/CHF", "CAD/JPY", "CHF/JPY",
    "EUR/AUD", "EUR/CHF", "EUR/GBP"
]

INTERVAL = "5min"     # velas de 5 minutos
OUTPUTSIZE = 200      # velas a descargar en cada análisis


# =========================
# FUNCIONES
# =========================

def get_candles(symbol: str) -> pd.DataFrame:
    """
    Descarga velas de Twelve Data para un símbolo (5 minutos).
    """
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": INTERVAL,
        "outputsize": OUTPUTSIZE,
        "apikey": API_KEY,
    }

    r = requests.get(url, params=params, timeout=10)
    data = r.json()

    # Manejo de errores de Twelve Data
    if isinstance(data, dict) and data.get("status") == "error":
        msg = data.get("message", "Error desconocido")
        raise ValueError(f"Error Twelve Data {symbol}: {msg}")

    values = data["values"]
    df = pd.DataFrame(values)

    # Convertir tipos
    df["datetime"] = pd.to_datetime(df["datetime"])
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)

    # Ordenar de más viejo a más nuevo
    df = df.sort_values("datetime").reset_index(drop=True)
    return df


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega EMAs 10/20/50 y Bandas de Bollinger (20, 2).
    """
    close = df["close"]

    # EMAs
    df["ema10"] = close.ewm(span=10, adjust=False).mean()
    df["ema20"] = close.ewm(span=20, adjust=False).mean()
    df["ema50"] = close.ewm(span=50, adjust=False).mean()

    # Bollinger (20 periodos, 2 desviaciones)
    bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
    df["bb_mid"] = bb.bollinger_mavg()
    df["bb_up"] = bb.bollinger_hband()
    df["bb_low"] = bb.bollinger_lband()

    return df


def check_signal(df: pd.DataFrame):
    """
    Usa la última vela para decidir si hay señal CALL o PUT
    con EMAs 10/20/50 y Bollinger.
    """
    last = df.iloc[-1]

    ema10 = last["ema10"]
    ema20 = last["ema20"]
    ema50 = last["ema50"]

    o = last["open"]
    c = last["close"]
    h = last["high"]
    l = last["low"]

    bb_mid = last["bb_mid"]
    bb_up = last["bb_up"]
    bb_low = last["bb_low"]

    rango = h - l
    if rango <= 0:
        return None

    mitad_rango = l + rango / 2

    # ======= TENDENCIA ALCISTA → SOLO CALL =======
    # EMAs alineadas hacia arriba: 10 > 20 > 50
    if ema10 > ema20 > ema50:
        # Retroceso a banda media o baja
        if bb_low * 0.998 <= c <= bb_mid * 1.002:
            # cuerpo cerrando en mitad superior de la vela
            # mecha inferior más grande que la superior
            if c > mitad_rango and (c - l) > (h - c):
                return "CALL"

    # ======= TENDENCIA BAJISTA → SOLO PUT =======
    # EMAs alineadas hacia abajo: 10 < 20 < 50
    if ema10 < ema20 < ema50:
        # Retroceso a banda media o alta
        if bb_mid * 0.998 <= c <= bb_up * 1.002:
            # cuerpo cerrando en mitad inferior
            # mecha superior más grande que la inferior
            if c < mitad_rango and (h - c) > (c - l):
                return "PUT"

    return None


def send_telegram_message(text: str):
    """
    Envía mensaje a Telegram si TELEGRAM_TOKEN y CHAT_ID están configurados.
    Si no, solo imprime el mensaje en consola.
    """
    print(text)  # siempre imprimimos en consola

    if not TELEGRAM_TOKEN or not CHAT_ID:
        return  # no intentamos mandar a Telegram si faltan datos

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error enviando Telegram: {e}")


def analyze_symbol(symbol: str):
    try:
        df = get_candles(symbol)
        df = add_indicators(df)
        signal = check_signal(df)

        if signal:
            last = df.iloc[-1]
            dt = last["datetime"]

            bloque = (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 BOT EMAs 10/20/50 + Bollinger\n"
                f"📈 PAR: {symbol}\n"
                f"🎯 TIPO: {signal}\n"
                f"🕒 Vela 5m analizada: {dt} (UTC)\n"
                f"💰 Precio actual: {last['close']:.5f}\n"
                "📌 Condición: tendencia fuerte + retroceso + rechazo\n"
                "👉 Entrar AL CIERRE de esta vela (faltando ~1 min).\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            )

            send_telegram_message(bloque)

    except Exception as e:
        print(f"Error analizando {symbol}: {e}")


# =========================
# LOOP PRINCIPAL
# =========================

def main_loop():
    print("🚀 Bot iniciado. Analizando velas de 5 minutos...")
    contador_debug = 0
    while True:
        # Hora UTC
        now = datetime.utcnow()
        minute = now.minute
        second = now.second

        # Mensaje de "sigo vivo" cada ~60 iteraciones aprox.
        if contador_debug % 60 == 0:
            print(f"Sigo vivo... {now} (UTC)")
            contador_debug = 0
        contador_debug += 1

        # Revisar 1 minuto antes de que cierre la vela de 5m:
        # velas cierran : 00,05,10,15,...
        # revisamos cuando minuto % 5 == 4 (04,09,14,19,24,...)
        if minute % 5 == 4 and second < 5:
            print(f"\n=== Análisis {now} UTC ===")
            for symbol in SYMBOLS:
                analyze_symbol(symbol)

            # Esperar 60s para no repetir análisis en el mismo minuto
            time.sleep(60)

        # Pausa pequeña
        time.sleep(1)


if __name__ == "__main__":
    try:
        main_loop()
    except Exception as e:
        print(f"❌ Error crítico en main_loop: {e}")