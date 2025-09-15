import telebot
import MetaTrader5 as mt5
import pandas as pd
import time
from datetime import datetime
import threading
import os

# Configuration from Environment Variables (Render par secure rakhne ke liye)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8308327816:AAGXlx_nDEy63AsZKVKEza5iItmCpauRkPE')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '5969642968')
MT5_ACCOUNT = int(os.environ.get('MT5_ACCOUNT', '232128229'))
MT5_PASSWORD = os.environ.get('MT5_PASSWORD', '@Mardan115')
MT5_SERVER = os.environ.get('MT5_SERVER', 'Exness-MT5Server')

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def initialize_mt5():
    """Initialize MT5 connection"""
    try:
        if not mt5.initialize():
            error_msg = f"MT5 initialization failed. Error: {mt5.last_error()}"
            bot.send_message(TELEGRAM_CHAT_ID, error_msg)
            return False
        
        authorized = mt5.login(login=MT5_ACCOUNT, password=MT5_PASSWORD, server=MT5_SERVER)
        if not authorized:
            error_msg = f"MT5 login failed. Error: {mt5.last_error()}"
            bot.send_message(TELEGRAM_CHAT_ID, error_msg)
            return False
        
        bot.send_message(TELEGRAM_CHAT_ID, "✅ MT5 Connection Successful!")
        return True
    except Exception as e:
        bot.send_message(TELEGRAM_CHAT_ID, f"MT5 Connection Error: {str(e)}")
        return False

def trading_job():
    """Main trading function that runs continuously"""
    while True:
        try:
            now = datetime.now().time()
            
            # Check for London session (2:00 PM IST)
            if now.hour == 14 and now.minute == 0:
                send_daily_analysis("London")
                time.sleep(60)
            
            # Check for New York session (6:30 PM IST)
            elif now.hour == 18 and now.minute == 30:
                send_daily_analysis("New York")
                time.sleep(60)
            
            time.sleep(30)  # Check every 30 seconds
                
        except Exception as e:
            bot.send_message(TELEGRAM_CHAT_ID, f"Trading Job Error: {str(e)}")
            time.sleep(60)

def send_daily_analysis(session_name):
    """Send analysis for trading session"""
    try:
        if not initialize_mt5():
            return
        
        analysis = f"🏛 {session_name.upper()} SESSION ANALYSIS\n\n"
        analysis += generate_trading_analysis("XAUUSD") + "\n\n"
        analysis += generate_trading_analysis("BTCUSD")
        
        bot.send_message(TELEGRAM_CHAT_ID, analysis)
        
    except Exception as e:
        bot.send_message(TELEGRAM_CHAT_ID, f"Analysis Error: {str(e)}")

# (Yaha wohi generate_trading_analysis() function add karein jo maine pichle message mein diya tha)

if _name_ == "_main_":
    bot.send_message(TELEGRAM_CHAT_ID, "🤖 Trading Bot Started on Render!")
    trading_thread = threading.Thread(target=trading_job)
    trading_thread.daemon = True
    trading_thread.start()
    
    # Keep the main thread alive
    while True:
        time.sleep(3600)  # Sleep for 1 hour
