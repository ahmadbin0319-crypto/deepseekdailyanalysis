import telebot
import pandas as pd
import time
from datetime import datetime
import threading
import os
import requests
import json
import logging
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration from Environment Variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8308327816:AAGXlx_nDEy63AsZKVKEza5iItmCpauRkPE')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '5969642968')
TWELVE_DATA_API_KEY = os.environ.get('TWELVE_DATA_API_KEY', 'demo')  # Free API key ke liye signup karo

# Validate required environment variables
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    logger.error("Missing required environment variables: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

class MarketDataAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.twelvedata.com"
    
    def get_real_time_price(self, symbol):
        """Real-time price data get karta hai"""
        try:
            url = f"{self.base_url}/price?symbol={symbol}&apikey={self.api_key}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if 'price' in data:
                return float(data['price'])
            else:
                logger.error(f"Price data not found for {symbol}: {data}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {str(e)}")
            return None
    
    def get_historical_data(self, symbol, interval='1day', output_size=100):
        """Historical price data get karta hai indicators ke liye"""
        try:
            url = f"{self.base_url}/time_series?symbol={symbol}&interval={interval}&outputsize={output_size}&apikey={self.api_key}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if 'values' in data:
                df = pd.DataFrame(data['values'])
                df['datetime'] = pd.to_datetime(df['datetime'])
                df['close'] = pd.to_numeric(df['close'])
                df['open'] = pd.to_numeric(df['open'])
                df['high'] = pd.to_numeric(df['high'])
                df['low'] = pd.to_numeric(df['low'])
                df['volume'] = pd.to_numeric(df['volume'])
                return df
            else:
                logger.error(f"Historical data not found for {symbol}: {data}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return None

# Initialize market data API
market_api = MarketDataAPI(TWELVE_DATA_API_KEY)

def trading_job():
    """Main trading function that runs continuously"""
    logger.info("Trading job started")
    
    while True:
        try:
            now = datetime.now()
            current_time = now.time()
            
            # Log every hour to know the bot is running
            if current_time.minute == 0:
                logger.info(f"Bot is running at {now.strftime('%H:%M')}")
            
            # Check for London session (2:00 PM IST)
            if current_time.hour == 14 and current_time.minute == 0:
                logger.info("London session analysis triggered")
                send_daily_analysis("London")
                time.sleep(60)  # Prevent multiple triggers
            
            # Check for New York session (6:30 PM IST)
            elif current_time.hour == 18 and current_time.minute == 30:
                logger.info("New York session analysis triggered")
                send_daily_analysis("New York")
                time.sleep(60)  # Prevent multiple triggers
            
            time.sleep(30)  # Check every 30 seconds
                
        except Exception as e:
            error_msg = f"Trading Job Error: {str(e)}"
            logger.error(error_msg)
            try:
                bot.send_message(TELEGRAM_CHAT_ID, error_msg)
            except:
                pass  # Avoid infinite error loop
            time.sleep(60)

def calculate_rsi(prices, period=14):
    """Calculate RSI indicator"""
    try:
        deltas = prices.diff()
        gains = deltas.where(deltas > 0, 0)
        losses = -deltas.where(deltas < 0, 0)
        
        avg_gain = gains.rolling(window=period, min_periods=1).mean()
        avg_loss = losses.rolling(window=period, min_periods=1).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    except Exception as e:
        logger.error(f"RSI calculation error: {str(e)}")
        return pd.Series([50] * len(prices))  # Return neutral RSI on error

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD indicator"""
    try:
        exp1 = prices.ewm(span=fast, adjust=False).mean()
        exp2 = prices.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        return macd, signal_line, histogram
    except Exception as e:
        logger.error(f"MACD calculation error: {str(e)}")
        return None, None, None

def generate_trading_analysis(symbol):
    """Generate trading analysis for a symbol using real market data"""
    try:
        # Get real-time price
        current_price = market_api.get_real_time_price(symbol)
        if current_price is None:
            return f"❌ Real-time price not available for {symbol}"
        
        # Get historical data for indicators
        historical_data = market_api.get_historical_data(symbol)
        if historical_data is None:
            return f"❌ Historical data not available for {symbol}"
        
        # Calculate indicators
        prices = historical_data['close']
        historical_data['sma_20'] = prices.rolling(window=20, min_periods=1).mean()
        historical_data['sma_50'] = prices.rolling(window=50, min_periods=1).mean()
        historical_data['rsi'] = calculate_rsi(prices, 14)
        
        macd, signal_line, histogram = calculate_macd(prices)
        
        current_sma_20 = historical_data['sma_20'].iloc[-1]
        current_sma_50 = historical_data['sma_50'].iloc[-1]
        current_rsi = historical_data['rsi'].iloc[-1]
        
        # Generate signal based on multiple indicators
        signals = []
        
        # Price vs SMA
        if current_price > current_sma_20 and current_price > current_sma_50:
            signals.append("Price above both SMAs (Bullish)")
        elif current_price < current_sma_20 and current_price < current_sma_50:
            signals.append("Price below both SMAs (Bearish)")
        else:
            signals.append("Price between SMAs (Neutral)")
        
        # RSI
        if current_rsi > 70:
            signals.append("RSI Overbought (>70)")
        elif current_rsi < 30:
            signals.append("RSI Oversold (<30)")
        else:
            signals.append("RSI Neutral")
        
        # MACD
        if macd is not None and len(macd) > 1:
            if macd.iloc[-1] > signal_line.iloc[-1] and macd.iloc[-2] <= signal_line.iloc[-2]:
                signals.append("MACD Bullish Crossover")
            elif macd.iloc[-1] < signal_line.iloc[-1] and macd.iloc[-2] >= signal_line.iloc[-2]:
                signals.append("MACD Bearish Crossover")
        
        # Overall signal
        bullish_count = sum(1 for s in signals if 'Bullish' in s or 'Oversold' in s)
        bearish_count = sum(1 for s in signals if 'Bearish' in s or 'Overbought' in s)
        
        if bullish_count > bearish_count:
            overall_signal = "🟢 BUY"
        elif bearish_count > bullish_count:
            overall_signal = "🔴 SELL"
        else:
            overall_signal = "🟡 NEUTRAL"
        
        analysis = f"{symbol} Analysis:\n"
        analysis += f"Current Price: ${current_price:.2f}\n"
        analysis += f"SMA 20: ${current_sma_20:.2f}\n"
        analysis += f"SMA 50: ${current_sma_50:.2f}\n"
        analysis += f"RSI: {current_rsi:.2f}\n"
        
        if macd is not None:
            analysis += f"MACD: {macd.iloc[-1]:.4f}\n"
        
        analysis += f"Signal: {overall_signal}\n\n"
        analysis += "Signals:\n" + "\n".join([f"• {s}" for s in signals])
        
        return analysis
        
    except Exception as e:
        error_msg = f"Error analyzing {symbol}: {str(e)}"
        logger.error(error_msg)
        return error_msg

def send_daily_analysis(session_name):
    """Send analysis for trading session"""
    try:
        analysis = f"🏛 {session_name.upper()} SESSION ANALYSIS\n\n"
        analysis += generate_trading_analysis("XAU/USD") + "\n\n"
        analysis += generate_trading_analysis("BTC/USD")
        
        bot.send_message(TELEGRAM_CHAT_ID, analysis)
        logger.info(f"Analysis sent for {session_name} session")
        
    except Exception as e:
        error_msg = f"Analysis Error: {str(e)}"
        logger.error(error_msg)
        try:
            bot.send_message(TELEGRAM_CHAT_ID, error_msg)
        except:
            pass  # Avoid infinite error loop

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Handle start and help commands"""
    welcome_text = """
🤖 Real Trading Bot Help

Commands:
/price [symbol] - Get current price of a symbol
/analysis [symbol] - Get technical analysis of a symbol
/status - Check bot status

Examples:
/price BTC/USD
/analysis XAU/USD
"""
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['price'])
def send_price(message):
    """Get current price of a symbol"""
    try:
        command_parts = message.text.split()
        if len(command_parts) < 2:
            bot.reply_to(message, "Please specify a symbol. Example: /price BTC/USD")
            return
        
        symbol = command_parts[1].upper()
        price = market_api.get_real_time_price(symbol)
        
        if price is not None:
            bot.reply_to(message, f"💰 {symbol} Current Price: ${price:.2f}")
        else:
            bot.reply_to(message, f"❌ Could not fetch price for {symbol}")
            
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

@bot.message_handler(commands=['analysis'])
def send_analysis(message):
    """Get technical analysis of a symbol"""
    try:
        command_parts = message.text.split()
        if len(command_parts) < 2:
            bot.reply_to(message, "Please specify a symbol. Example: /analysis XAU/USD")
            return
        
        symbol = command_parts[1].upper()
        analysis = generate_trading_analysis(symbol)
        bot.reply_to(message, analysis)
            
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

@bot.message_handler(commands=['status'])
def send_status(message):
    """Check bot status"""
    status_text = f"""
🤖 Trading Bot Status

✅ Bot is running
🕒 Last check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📊 Using Twelve Data API
"""
    bot.reply_to(message, status_text)

def run_bot():
    """Run the Telegram bot"""
    logger.info("Starting Telegram bot polling...")
    bot.infinity_polling()

if __name__ == "__main__":
    try:
        startup_msg = "🤖 Real Trading Bot Started with Live Market Data!"
        bot.send_message(TELEGRAM_CHAT_ID, startup_msg)
        logger.info(startup_msg)
        
        # Start trading job in background thread
        trading_thread = threading.Thread(target=trading_job)
        trading_thread.daemon = True
        trading_thread.start()
        
        # Start Telegram bot polling in main thread
        run_bot()
            
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
