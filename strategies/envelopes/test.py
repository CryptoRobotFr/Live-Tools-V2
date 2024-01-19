import sys
sys.path.append("./Live-Tools-V2")

import asyncio
from utilities.bitget_perp import PerpBitget
from secret import ACCOUNTS

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    account = ACCOUNTS["bitget1"]
    exchange = PerpBitget(
        public_api=account["public_api"],
        secret_api=account["secret_api"],
        password=account["password"],
    )
    try:
        await exchange.load_markets()
        resp = await exchange.get_balance()
        usdt_balance = resp.total
        print(usdt_balance)

        # await exchange.place_order("BTC/USDT", "buy", 37000, 0.001, "limit", False)
        # await exchange.place_order("BTC/USDT", "buy", 37000, 0.001, "limit", False)
        print(await exchange.place_order("BTC/USDT", "buy", None, 0.001, "market", False, "isolated"))
        # print(await exchange.get_open_orders("BTC/USDT"))
        # await exchange.place_order("BTC/USDT", "sell", 48000, 0.001, "limit", True)
        # print(await exchange.cancel_orders("BTC/USDT"))
        # print(await exchange.get_open_positions(["BTC/USDT", "ETH/USDT"]))
        # print(await exchange.set_margin_mode_and_leverage("ETH/USDT", "isolated", 3))
        # print(await exchange.get_last_ohlcv("BTC/USDT", "1h", 2000))
        # print(await exchange.place_trigger_order("BTC/USDT", "buy", 29000, 30000, 0.001, "limit", True))
        # print(await exchange.place_trigger_order("BTC/USDT", "sell", None, 50000, 0.001, "market", False))
        # print(await exchange.place_trigger_order("BTC/USDT", "sell", None, 50000, 0.001, "market", False))
        # print(await exchange.cancel_trigger_orders("BTC/USDT"))
        # print(await exchange.get_open_trigger_orders("BTC/USDT"))
        


        await exchange.close()
    except Exception as e:
        await exchange.close()
        raise e

if __name__ == '__main__':
    asyncio.run(main())