from kiteconnect import KiteConnect
import pandas as pd
import time
from datetime import datetime, timedelta
import requests
import os

# ==============================
# 🔑 CONFIG (SECURE)
# ==============================

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# ==============================
# 📩 TELEGRAM
# ==============================

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message}
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram Error:", e)

# ==============================
# 📊 LOG
# ==============================

def log(msg):
    print(f"{datetime.now()} - {msg}")

# ==============================
# 📊 RSI
# ==============================

def calculate_rsi(df, period=14):
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# ==============================
# 🌍 GLOBAL SENTIMENT (BASIC)
# ==============================

def get_global_sentiment():
    return {"US": "→", "Europe": "→", "Asia": "→"}

# ==============================
# 🔍 ANALYZE INDEX
# ==============================

def analyze_index(symbol, token):
    try:
        log(f"Analyzing {symbol}")

        ltp = kite.ltp(f"NSE:{symbol}")
        price = ltp[f"NSE:{symbol}"]["last_price"]

        to_date = datetime.now()
        from_date = to_date - timedelta(days=5)

        data = kite.historical_data(token, from_date, to_date, "5minute")
        df = pd.DataFrame(data)

        if df.empty or "volume" not in df.columns:
            log(f"No valid data for {symbol}")
            return None

        df["volume"] = df["volume"].replace(0, 1).fillna(1)

        # Indicators
        df["rsi"] = calculate_rsi(df)
        rsi = df["rsi"].iloc[-1]

        df["vwap"] = (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum()
        vwap = df["vwap"].iloc[-1]

        orb_high = df["high"].iloc[:3].max()
        orb_low = df["low"].iloc[:3].min()

        trend_15m = "UP" if df["close"].iloc[-1] > df["close"].iloc[-5] else "DOWN"
        trend_1h = "UP" if df["close"].iloc[-1] > df["close"].iloc[-12] else "DOWN"

        # ==============================
        # 🎯 SCORING SYSTEM
        # ==============================

        score = 0
        reasons = []

        if rsi < 35:
            score += 2
            reasons.append("RSI Oversold")
        elif rsi > 65:
            score -= 2
            reasons.append("RSI Overbought")

        if price > vwap:
            score += 1
            reasons.append("Above VWAP")
        else:
            score -= 1
            reasons.append("Below VWAP")

        recent = df["close"].iloc[-3:]
        if recent.is_monotonic_increasing:
            score += 1
            reasons.append("Momentum Up")
        elif recent.is_monotonic_decreasing:
            score -= 1
            reasons.append("Momentum Down")

        global_data = get_global_sentiment()

        # ==============================
        # 📩 MESSAGE
        # ==============================

        message = (
            f"{symbol}\n"
            f"Price: {price}\n"
            f"RSI: {round(rsi,2)}\n"
            f"VWAP: {round(vwap,2)}\n"
            f"ORB: {round(orb_high,2)}/{round(orb_low,2)}\n"
            f"Trend: {trend_15m}/{trend_1h}\n"
            f"Score: {score}\n"
            f"Reasons: {', '.join(reasons)}\n"
            f"Global: {global_data}"
        )

        log(message)
        return message, score

    except Exception as e:
        log(f"Error in {symbol}: {e}")
        return None

# ==============================
# 🚀 MAIN LOOP
# ==============================

def run_bot():
    log("Starting AI Bot...")

    instruments = kite.instruments("NSE")

    nifty_token = next(i["instrument_token"] for i in instruments if i["tradingsymbol"] == "NIFTY 50")
    banknifty_token = next(i["instrument_token"] for i in instruments if i["tradingsymbol"] == "NIFTY BANK")

    last_sent = {"NIFTY 50": None, "NIFTY BANK": None}

    while True:
        for symbol, token in [("NIFTY 50", nifty_token), ("NIFTY BANK", banknifty_token)]:
            result = analyze_index(symbol, token)

            if result:
                message, score = result

                if score >= 3 or score <= -3:
                    if last_sent[symbol] != message:
                        send_telegram(message)
                        last_sent[symbol] = message

        log("Waiting 60 sec...\n")
        time.sleep(60)

# ==============================
# ▶️ START
# ==============================

if __name__ == "__main__":
    run_bot()
