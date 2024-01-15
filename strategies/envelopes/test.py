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
        resp = await exchange.fetch_balance()
        usdt_balance = resp.total
        print(usdt_balance)

        # await exchange.place_order("BTC/USDT", "buy", 37000, 0.001, "limit", False)
        # print(await exchange.place_order("BTC/USDT", "buy", None, 0.001, "market", False))
        # print(await exchange.get_open_orders("BTC/USDT"))
        # print(await exchange.cancel_orders("BTC/USDT"))
        # print(await exchange.get_open_positions(["BTC/USDT", "ETH/USDT"]))
        # print(await exchange.set_margin_mode_and_leverage("ETH/USDT", "isolated", 3))
        


        await exchange.close()
    except Exception as e:
        await exchange.close()
        raise e

if __name__ == '__main__':
    asyncio.run(main())