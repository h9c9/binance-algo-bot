import time
from binance_weighted_algo import BinanceWeightedAlgoTrader

API_KEY = "wQO0PGPi9yLWoLwg0ETK4TM7Qy7AxZRevC4XO3EK44l"
SECRET_KEY ="vQdSmkkGhbK2oozLFyDER7NcOkiJBD1k9r8Das"

if __name__ == "__main__":
    bot = BinanceWeightedAlgoTrader(API_KEY, SECRET_KEY)
    print("Started Binance Algo Trader Runner!")

    while True:
        print("="*45)
        print("Executing trading logic at", time.strftime("%Y-%m-%d %H:%M:%S"))
        bot.run()
        print("Waiting 30 seconds for next run...\n")
        time.sleep(30)
