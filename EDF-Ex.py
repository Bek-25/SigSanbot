import pandas as pd
import yfinance as yf
import datetime as dt
import requests
import os

# --- Конфигурация ---
symbol = 'EURUSD=X'
period = '5d'
interval = '1m'

TELEGRAM_TOKEN = '7999172973:AAF3noQjIyQ5Ns1KxYpWqWildCLz14cx1EU'
TELEGRAM_CHAT_ID = '6511621637'

EXCEL_FILE = 'signals_log.xlsx'

# --- Загрузка данных ---
data = yf.download(symbol, period=period, interval=interval)
data.dropna(inplace=True)

# --- Добавление индикаторов ---
def add_indicators(df):
    df['EMA_5'] = df['Close'].ewm(span=5, adjust=False).mean()
    df['EMA_15'] = df['Close'].ewm(span=15, adjust=False).mean()
    window = 20
    df['Donchian_High'] = df['High'].rolling(window).max()
    df['Donchian_Low'] = df['Low'].rolling(window).min()
    df['Donchian_Mid'] = (df['Donchian_High'] + df['Donchian_Low']) / 2
    df['Fractal_Low'] = df['Low'][(df['Low'].shift(1) > df['Low']) & (df['Low'].shift(-1) > df['Low'])]
    df['Fractal_High'] = df['High'][(df['High'].shift(1) < df['High']) & (df['High'].shift(-1) < df['High'])]
    return df

df = add_indicators(data)

# --- Логика сигнала ---
def check_signals(df):
    df = df.dropna()
    if len(df) < 3:
        return None  # Недостаточно данных

    last = df.iloc[-1]
    prev = df.iloc[-2]

    ema_cross_buy = float(prev['EMA_5']) < float(prev['EMA_15']) and float(last['EMA_5']) > float(last['EMA_15'])
    ema_cross_sell = float(prev['EMA_5']) > float(prev['EMA_15']) and float(last['EMA_5']) < float(last['EMA_15'])
    donchian_breakout_up = float(last['Close']) > float(last['Donchian_Mid'])
    donchian_breakout_down = float(last['Close']) < float(last['Donchian_Mid'])
    fractal_low = not pd.isna(df['Fractal_Low'].iloc[-3])
    fractal_high = not pd.isna(df['Fractal_High'].iloc[-3])

    signal = None

    if ema_cross_buy and donchian_breakout_up and fractal_low:
        signal = (
            "Fractal показал нижнюю границу, от которой цена не опустилась. "
            "Произошло пересечение EMA 5 и EMA 15 снизу вверх. "
            "Цена выше средней линии Donchian. \n💹 СИГНАЛ: ПОКУПКА."
        )
    elif ema_cross_sell and donchian_breakout_down and fractal_high:
        signal = (
            "Fractal показал верхнюю границу, от которой цена не поднялась. "
            "Произошло пересечение EMA 5 и EMA 15 сверху вниз. "
            "Цена ниже средней линии Donchian. \n📉 СИГНАЛ: ПРОДАЖА."
        )

    return signal


# --- Сохранение в Excel ---
def save_to_excel(signal_text, symbol):
    time_now = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_row = pd.DataFrame([{
        'Время': time_now,
        'Символ': symbol,
        'Сигнал': signal_text
    }])
    if os.path.exists(EXCEL_FILE):
        old_data = pd.read_excel(EXCEL_FILE)
        updated_data = pd.concat([old_data, new_row], ignore_index=True)
    else:
        updated_data = new_row
    updated_data.to_excel(EXCEL_FILE, index=False)

# --- Отправка в Telegram ---
def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("✅ Сообщение отправлено в Telegram")
        else:
            print("⚠️ Ошибка при отправке:", response.text)
    except Exception as e:
        print("⚠️ Ошибка:", e)

# --- Основной блок ---
signal = check_signals(df)
if signal:
    message = f"{signal}\nСимвол: {symbol}\nВремя: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    send_to_telegram(message)
    save_to_excel(signal, symbol)
else:
    print("❌ Сигнал не обнаружен")
    send_to_telegram("✅ Бот работает. Пока сигнала нет❌.")
    

