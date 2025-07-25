# bot.py
import time
import json
import logging
from datetime import datetime, timedelta

from binance.client import Client
from binance.exceptions import BinanceAPIException
import requests

import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET)

# حفظ الصفقات المفتوحة
POSITIONS_FILE = "positions.json"

def load_positions():
    try:
        with open(POSITIONS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_positions(data):
    with open(POSITIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": config.TELEGRAM_CHAT_ID, "text": text}
    try:
        requests.post(url, data=data)
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")

def get_balance(asset="USDT"):
    try:
        balance = client.get_asset_balance(asset)
        if balance:
            return float(balance['free'])
        return 0.0
    except Exception as e:
        logging.error(f"Error fetching balance: {e}")
        return 0.0

def can_open_new_position(positions):
    return len(positions) < config.MAX_CONCURRENT_POSITIONS

def get_price_change_1h(symbol):
    try:
        klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1HOUR, limit=2)
        if len(klines) < 2:
            return 0.0
        open_price = float(klines[0][1])
        close_price = float(klines[1][4])
        change = (close_price - open_price) / open_price
        return change
    except Exception as e:
        logging.error(f"Error getting price change for {symbol}: {e}")
        return 0.0

def get_volume_1h(symbol):
    try:
        klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1HOUR, limit=2)
        if len(klines) < 2:
            return 0.0
        volume1 = float(klines[0][5])
        volume2 = float(klines[1][5])
        if volume1 == 0:
            return 0.0
        return volume2 / volume1
    except Exception as e:
        logging.error(f"Error getting volume ratio for {symbol}: {e}")
        return 0.0

def buy_market(symbol, usdt_amount):
    try:
        price = float(client.get_symbol_ticker(symbol=symbol)['price'])
        quantity = round(usdt_amount / price, 6)  # 6 أرقام عشرية للكمية تقريبًا
        order = client.order_market_buy(symbol=symbol, quantity=quantity)
        logging.info(f"Bought {quantity} {symbol} at market price {price}")
        send_telegram_message(f"🚀 صفقة جديدة:\nعملة: {symbol}\nسعر الدخول: {price}$\nكمية: {quantity}")
        return price, quantity
    except BinanceAPIException as e:
        logging.error(f"Buy order failed: {e}")
        return None, None
    except Exception as e:
        logging.error(f"Buy error: {e}")
        return None, None

def sell_market(symbol, quantity):
    try:
        price = float(client.get_symbol_ticker(symbol=symbol)['price'])
        order = client.order_market_sell(symbol=symbol, quantity=quantity)
        logging.info(f"Sold {quantity} {symbol} at market price {price}")
        send_telegram_message(f"📤 تم إغلاق الصفقة\nعملة: {symbol}\nسعر الخروج: {price}$")
        return price
    except BinanceAPIException as e:
        logging.error(f"Sell order failed: {e}")
        return None
    except Exception as e:
        logging.error(f"Sell error: {e}")
        return None

def check_positions():
    positions = load_positions()
    to_remove = []
    for symbol, pos in positions.items():
        entry_price = pos['entry_price']
        quantity = pos['quantity']
        try:
            current_price = float(client.get_symbol_ticker(symbol=symbol)['price'])
        except Exception as e:
            logging.error(f"Error fetching current price for {symbol}: {e}")
            continue

        change = (current_price - entry_price) / entry_price
        if change >= config.TAKE_PROFIT_PERCENT:
            sell_price = sell_market(symbol, quantity)
            if sell_price:
                profit = (sell_price - entry_price) * quantity
                send_telegram_message(f"✅ تم جني الربح\nعملة: {symbol}\nالربح: +{round(change*100,2)}%")
                to_remove.append(symbol)
        elif change <= -config.STOP_LOSS_PERCENT:
            sell_price = sell_market(symbol, quantity)
            if sell_price:
                loss = (sell_price - entry_price) * quantity
                send_telegram_message(f"🔻 تم وقف الخسارة\nعملة: {symbol}\nالخسارة: {round(change*100,2)}%")
                to_remove.append(symbol)

    for symbol in to_remove:
        positions.pop(symbol, None)
    save_positions(positions)

def scan_and_trade():
    positions = load_positions()
    balance = get_balance("USDT")
    logging.info(f"Available USDT balance: {balance}")

    for symbol in config.WHITELIST:
        if not can_open_new_position(positions):
            logging.info("Max concurrent positions reached.")
            break
        if symbol in positions:
            continue

        change = get_price_change_1h(symbol)
        volume_ratio = get_volume_1h(symbol)
        if change > 0.05 and volume_ratio > 1.5 and balance > 10:
            # ندخل صفقة
            usdt_amount = balance * config.POSITION_SIZE_PERCENT
            entry_price, quantity = buy_market(symbol, usdt_amount)
            if entry_price and quantity:
                positions[symbol] = {
                    "entry_price": entry_price,
                    "quantity": quantity,
                    "timestamp": datetime.utcnow().isoformat()
                }
                balance -= usdt_amount
                save_positions(positions)
            time.sleep(1)  # لتجنب حظر API

def main():
    send_telegram_message("🤖 البوت بدأ العمل الآن.")
    while True:
        try:
            check_positions()
            scan_and_trade()
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
        time.sleep(config.SCAN_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
