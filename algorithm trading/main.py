import datetime as dt
import matplotlib.pyplot as plt
import yfinance as yf

plt.style.use("dark_background")
#define moving_average as ma_(suffix)
ma_1 = 30
ma_2 = 100

start = dt.datetime.now() - dt.timedelta(days=365 * 3)
end = dt.datetime.now()

data_meta = yf.download('META', start=start, end=end)
print(data_meta)

data_meta[f'SMA_{ma_1}'] = data_meta['Close'].rolling(window=ma_1).mean()
data_meta[f'SMA_{ma_2}'] = data_meta['Close'].rolling(window=ma_2).mean()

data_meta = data_meta.iloc[ma_2:]

plt.figure(figsize=(12,6))
plt.plot(data_meta['Close'], label="Share Price META", color="lightgray")
plt.plot(data_meta[f'SMA_{ma_1}'], label=f"SMA_{ma_1}", color="orange")
plt.plot(data_meta[f'SMA_{ma_2}'], label=f"SMA_{ma_2}", color="purple")
plt.legend(loc="upper left")
plt.show()

buy_signals = []
sell_signals = []
trigger = 0

for x in range(len(data_meta)):
    if data_meta[f'SMA_{ma_1}'].iloc[x] > data_meta[f'SMA_{ma_2}'].iloc[x] and trigger != 1:
        buy_signals.append(data_meta['Close'].iloc[x])
        sell_signals.append(float('nan'))
        trigger = 1
    elif data_meta[f'SMA_{ma_1}'].iloc[x] < data_meta[f'SMA_{ma_2}'].iloc[x]  and trigger != -1:
        buy_signals.append(float('nan'))
        sell_signals.append(data_meta['Close'].iloc[x])
        trigger = -1
    else:
        buy_signals.append(float('nan'))
        sell_signals.append(float('nan'))

data_meta['Buy Signals'] = buy_signals
data_meta['sell signals'] = sell_signals

print(data_meta)

plt.figure(figsize=(12,6))
plt.plot(data_meta['Close'], label="Share Price META", alpha=0.5)
plt.plot(data_meta[f'SMA_{ma_1}'], label=f"SMA_{ma_1}", color="orange", linestyle="--")
plt.plot(data_meta[f'SMA_{ma_2}'], label=f"SMA_{ma_2}", color="pink", linestyle="--")
plt.scatter(data_meta.index, data_meta['Buy Signals'], label="Buy Signal", marker="^", color="#00ff00", lw=3)
plt.scatter(data_meta.index, data_meta['Buy Signals'], label="Sell Signal", marker="v", color="#ff0000", lw=3)
plt.legend(loc="upper left")
plt.show()
