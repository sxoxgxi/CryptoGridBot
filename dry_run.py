import asyncio
import time
from threading import Thread

import ccxt.pro as ccxtpro
import dotenv

dotenv.load_dotenv()

api_key = dotenv.get_key(".env", "API_KEY")
api_secret = dotenv.get_key(".env", "API_SECRET")

INITIAL_PRICE = float(input("Enter the initial price: "))
INITIAL_BALANCE = float(input("Enter the initial balance (USDT): "))
INITIAL_COIN = float(input("Enter the initial coin balance: "))
TRAILING_STOP_PERCENT = (
    float(input("Enter the trailing stop percentage (e.g. 3 for 3%): ")) / 100
)
TRADE_PERCENTAGE = float(input("Enter the trade percentage (e.g. 20 for 20%): ")) / 100
PRICE_CHANGE_PERCENT = (
    float(input("Enter the price change percentage (e.g. 0.1 for 0.1%): ")) / 100
)
RUN_TIME = int(input("Enter the run time in minutes: ")) * 60
COIN = input("Enter the coin symbol (e.g. BTC): ").upper()

wallet = {"usdt": INITIAL_BALANCE, "coin": INITIAL_COIN}
initial_funds = INITIAL_BALANCE


class GridBot:
    def __init__(self, initial_price, trailing_stop_percent):
        self.current_price = initial_price
        self.wallet = wallet
        self.trailing_stop_percent = trailing_stop_percent
        self.buy_levels = []
        self.sell_levels = []
        self.trail_stop_price = None
        self.buy_count = 0
        self.sell_count = 0
        self.updated_levels = False
        self.start_time = time.time()

    def update_price(self, new_price):
        self.current_price = new_price
        if not self.updated_levels:
            self.update_grid_levels()

            print("\n-------------------- Grid Levels --------------------")
            print(f"{'Buy Levels':<15} | {'Sell Levels':<15}")
            print("-" * 53)

            for buy, sell in zip(self.buy_levels, self.sell_levels):
                print(f"{buy:<15} | {sell:<15}")

            print("\nTrailing Stop Price:", self.trail_stop_price)
            print("-----------------------------------------------------\n")
            self.updated_levels = True

        self.check_grid()

        elapsed_time = time.time() - self.start_time
        if elapsed_time >= RUN_TIME:
            print("\n Time limit reached. Stopping the bot.")
            exit(0)

    def update_grid_levels(self):
        grid_distance = self.current_price * PRICE_CHANGE_PERCENT

        self.buy_levels = [
            float(format(self.current_price - (i + 1) * grid_distance, ".4f"))
            for i in range(5)
        ]

        self.sell_levels = [
            float(format(self.current_price + (i + 1) * grid_distance, ".4f"))
            for i in range(5)
        ]

        if self.trail_stop_price is None or self.current_price > self.trail_stop_price:
            self.trail_stop_price = self.current_price * (
                1 - self.trailing_stop_percent
            )

    def check_grid(self):
        for level in self.buy_levels:
            if self.current_price <= level:
                self.buy(level)
                self.buy_levels.remove(level)
                break

        for level in self.sell_levels:
            if self.current_price >= level:
                self.sell(level)
                self.sell_levels.remove(level)
                break

        if (
            self.trail_stop_price is not None
            and self.current_price <= self.trail_stop_price
        ):
            print(
                f"\nTrailing Stop Triggered! Selling at {self.current_price:.4f} USDT"
            )
            self.sell(self.current_price, trail_stop=True)
            self.trail_stop_price = None

    def buy(self, price):
        amount_to_buy = self.wallet["usdt"] * TRADE_PERCENTAGE
        if amount_to_buy > 0:
            amount = amount_to_buy / price
            self.wallet["usdt"] -= amount_to_buy
            self.wallet["coin"] += amount
            self.buy_count += 1
            print(f"\nBought {amount:.4f} {COIN} at {price:.4f} USDT")
        else:
            return

    def sell(self, price, trail_stop=False):
        amount_to_sell = (
            self.wallet["coin"]
            if trail_stop
            else self.wallet["coin"] * TRADE_PERCENTAGE
        )
        if amount_to_sell > 0:
            amount = self.wallet["coin"]
            self.wallet["coin"] -= amount_to_sell
            usdt_received = amount_to_sell * price
            self.wallet["usdt"] += usdt_received
            self.sell_count += 1
            print(f"\nSold {amount:.4f} {COIN} at {price:.4f} USDT")
        else:
            return

    def calculate_pnl(self):
        total_funds = self.wallet["usdt"] + (self.wallet["coin"] * self.current_price)
        return total_funds - initial_funds


async def start_websocket():
    exchange = ccxtpro.bitget()
    symbol = f"{COIN}/USDT"

    try:
        while time.time() - bot.start_time < RUN_TIME:
            ticker = await exchange.watch_ticker(symbol)
            price = float(ticker["last"])
            bot.update_price(price)
            pnl = bot.calculate_pnl()

            print(
                f"Current Price: {price:.4f} USDT | "
                f"Wallet: [USDT: {wallet['usdt']:.3f}, {COIN}: {wallet['coin']:.3f}] | "
                f"Buy/Sell: {bot.buy_count}/{bot.sell_count} | "
                f"PnL: {pnl:.4f} USDT",
                end="\r",
            )
    except Exception as e:
        print(f"\nError in WebSocket: {e}")
    finally:
        await exchange.close()


def main():
    global bot
    bot = GridBot(INITIAL_PRICE, TRAILING_STOP_PERCENT)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    websocket_thread = Thread(target=loop.run_until_complete, args=(start_websocket(),))
    websocket_thread.start()

    try:
        while time.time() - bot.start_time < RUN_TIME:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nBot stopped.")


if __name__ == "__main__":
    main()
