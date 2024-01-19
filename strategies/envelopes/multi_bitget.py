import sys

sys.path.append("./Live-Tools-V2")

import asyncio
from utilities.bitget_perp import PerpBitget
from secret import ACCOUNTS
import ta

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    account = ACCOUNTS["bitget1"]
    
    margin_mode = "isolated" # isolated or crossed
    exchange_leverage = 2
    
    tf = "1h"
    size_leverage = 2
    params = {
        "BTC/USDT": {
            "src": "close",
            "ma_base_window": 7,
            "envelopes": [0.07, 0.1, 0.15],
            "size": 0.1,
        },
        "ETH/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.1, 0.15],
            "size": 0.1,
        },
    }
    
    exchange = PerpBitget(
        public_api=account["public_api"],
        secret_api=account["secret_api"],
        password=account["password"],
    )
    pairs = list(params.keys())
    try:
        await exchange.load_markets()
        
        try:
            tasks = [exchange.set_margin_mode_and_leverage(pair, margin_mode, exchange_leverage) for pair in pairs]
            await asyncio.gather(*tasks) # set leverage and margin mode for all pairs
        except Exception as e:
            print(e)
        
        tasks = [exchange.get_last_ohlcv(pair, tf, 50) for pair in pairs]
        dfs = await asyncio.gather(*tasks)
        df_list = dict(zip(pairs, dfs))
        
        for pair in df_list:
            current_params = params[pair]
            df = df_list[pair]
            if current_params["src"] == "close":
                src = df["close"]
            elif current_params["src"] == "ohlc4":
                src = (df["close"] + df["high"] + df["low"] + df["open"]) / 4
                
            df['ma_base'] = ta.trend.sma_indicator(close=src, window=current_params["ma_base_window"]).shift(1)
            high_envelopes = [round(1/(1-e)-1, 3) for e in current_params["envelopes"]]
            for i in range(1, len(current_params["envelopes"]) + 1):
                df[f'ma_high_{i}'] = df['ma_base'] * (1 + high_envelopes[i-1])
                df[f'ma_low_{i}'] = df['ma_base'] * (1 - current_params["envelopes"][i-1])
                
            df_list[pair] = df
        
        print("Data and indicators loaded 100%")
        
        usdt_balance = await exchange.get_balance()
        usdt_balance = usdt_balance.total
        print(f"Balance: {round(usdt_balance, 2)} USDT")
        
        tasks = [exchange.get_open_trigger_orders(pair) for pair in pairs]
        trigger_orders = await asyncio.gather(*tasks)
        trigger_order_list = dict(zip(pairs, trigger_orders))  # Get all open trigger orders by pair
        
        tasks = []
        for pair in df_list:
            params[pair]["canceled_orders"] = len(trigger_order_list[pair])
            tasks.append(exchange.cancel_trigger_orders(pair, [order.id for order in trigger_order_list[pair]]))
            
        await asyncio.gather(*tasks) # Cancel all trigger orders
        
        tasks = [exchange.get_open_orders(pair) for pair in pairs]
        orders = await asyncio.gather(*tasks)
        order_list = dict(zip(pairs, orders)) # Get all open orders by pair
        
        tasks = []
        for pair in df_list:
            params[pair]["canceled_orders"] += len(order_list[pair])
            tasks.append(exchange.cancel_orders(pair, [order.id for order in order_list[pair]]))
            
        await asyncio.gather(*tasks) # Cancel all orders
        
        positions = await exchange.get_open_positions(pairs)
        for position in positions:
            print(f"Current position on {position.pair} {position.side} - {position.size} ~ {position.usd_size} $")
        
        # print(ids_to_cancel)
        # print(await exchange.cancel_trigger_orders)

        # await exchange.place_order("BTC/USDT", "buy", 37000, 0.001, "limit", False)
        # print(await exchange.place_order("BTC/USDT", "buy", None, 0.001, "market", False))
        # print(await exchange.get_open_orders("BTC/USDT"))
        # print(await exchange.cancel_orders("BTC/USDT"))
        # print(await exchange.get_open_positions(["BTC/USDT", "ETH/USDT"]))
        # print(await exchange.set_margin_mode_and_leverage("ETH/USDT", "isolated", 3))
        # print(await exchange.get_last_ohlcv("BTC/USDT", "1h", 2000))

        await exchange.close()
    except Exception as e:
        await exchange.close()
        raise e


if __name__ == "__main__":
    asyncio.run(main())
