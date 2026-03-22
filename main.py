from kiteconnect import KiteConnect
import pandas as pd
from datetime import datetime, timedelta
import requests
import os

# ==============================
# 🔑 ENV VARIABLES
# ==============================

API_KEY = os.getenv("API_KEY")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# ==============================
# 📩 TELEGRAM
# ==============================

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=data)

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
    return 100 - (100 / (1 + rs))

# ==============================
# 🔍 ANALYSIS
# ==============================

def analyze_index(symbol, token):
    try:
        ltp = kite.ltp(f"NSE:{symbol}")
        price = ltp[f"NSE:{symbol}"]["last_price"]

        to_date = datetime.now()
        from_date = to_date - timedelta(days=5)

        data = kite.historical_data(token, from_date, to_date, "5minute")
        df = pd.DataFrame(data)

        if df.empty:
            return None

        df["volume"] = df["volume"].replace(0, 1).fillna(1)

        df["rsi"] = calculate_rsi(df)
        rsi = df["rsi"].iloc[-1]

        df["vwap"] = (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum()
        vwap = df["vwap"].iloc[-1]

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

        message = f"{symbol} | Price: {price} | RSI: {round(rsi,2)} | Score: {score} | Reasons: {','.join(reasons)}"

        print(message)

        return message, score

    except Exception as e:
        print("Error:", e)
        return None

# ==============================
# 🚀 RUN ONCE
# ==============================

def run_once():
    print("🔄 Running scheduled scan...")

    instruments = kite.instruments("NSE")

    nifty_token = next(i["instrument_token"] for i in instruments if i["tradingsymbol"] == "NIFTY 50")
    banknifty_token = next(i["instrument_token"] for i in instruments if i["tradingsymbol"] == "NIFTY BANK")

    results = [
        ("NIFTY 50", analyze_index("NIFTY 50", nifty_token)),
        ("NIFTY BANK", analyze_index("NIFTY BANK", banknifty_token)),
    ]

    for symbol, result in results:
        if result:
            message, score = result

            if score >= 3 or score <= -3:
                send_telegram(message)

# ==============================
# ▶️ START
# ==============================

if __name__ == "__main__":
    run_once()
