import datetime
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

    margin_mode = "isolated"  # isolated or crossed
    exchange_leverage = 3

    tf = "1h"
    size_leverage = 3
    sl = 0.3
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
        "ADA/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.09, 0.12, 0.15],
            "size": 0.1,
        },
        "AVAX/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.09, 0.12, 0.15],
            "size": 0.1,
        },
        "EGLD/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.1, 0.15, 0.2],
            "size": 0.05,
        },
        "KSM/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.1, 0.15, 0.2],
            "size": 0.05,
        },
        "OCEAN/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.1, 0.15, 0.2],
            "size": 0.05,
        },
        "REN/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.1, 0.15, 0.2],
            "size": 0.05,
        },
        "ACH/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.1, 0.15, 0.2],
            "size": 0.05,
        },
        "APE/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.1, 0.15, 0.2],
            "size": 0.05,
        },
        "CRV/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.1, 0.15, 0.2],
            "size": 0.05,
        },
        "DOGE/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.1, 0.15, 0.2],
            "size": 0.05,
        },
        "ENJ/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.1, 0.15, 0.2],
            "size": 0.05,
        },
        "FET/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.1, 0.15, 0.2],
            "size": 0.05,
        },
        "ICP/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.1, 0.15, 0.2],
            "size": 0.05,
        },
        "IMX/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.1, 0.15, 0.2],
            "size": 0.05,
        },
        "LDO/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.1, 0.15, 0.2],
            "size": 0.05,
        },
        "MAGIC/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.1, 0.15, 0.2],
            "size": 0.05,
        },
        "REEF/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.1, 0.15, 0.2],
            "size": 0.05,
        },
        "SAND/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.1, 0.15, 0.2],
            "size": 0.05,
        },
        "TRX/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.1, 0.15, 0.2],
            "size": 0.05,
        },
        "XTZ/USDT": {
            "src": "close",
            "ma_base_window": 5,
            "envelopes": [0.07, 0.1, 0.15, 0.2],
            "size": 0.05,
        },
    }

    exchange = PerpBitget(
        public_api=account["public_api"],
        secret_api=account["secret_api"],
        password=account["password"],
    )
    invert_side = {"long": "sell", "short": "buy"}
    print(f"--- Execution started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    try:
        await exchange.load_markets()

        for pair in params.copy():
            info = exchange.get_pair_info(pair)
            if info is None:
                print(f"Pair {pair} not found, removing from params...")
                del params[pair]

        pairs = list(params.keys())

        try:
            print(f"Setting {margin_mode} x{exchange_leverage} on {len(pairs)} pairs...")
            tasks = [
                exchange.set_margin_mode_and_leverage(
                    pair, margin_mode, exchange_leverage
                )
                for pair in pairs
            ]
            await asyncio.gather(*tasks)  # set leverage and margin mode for all pairs
        except Exception as e:
            print(e)

        print(f"Getting data and indicators on {len(pairs)} pairs...")
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

            df["ma_base"] = ta.trend.sma_indicator(
                close=src, window=current_params["ma_base_window"]
            )
            high_envelopes = [
                round(1 / (1 - e) - 1, 3) for e in current_params["envelopes"]
            ]
            for i in range(1, len(current_params["envelopes"]) + 1):
                df[f"ma_high_{i}"] = df["ma_base"] * (1 + high_envelopes[i - 1])
                df[f"ma_low_{i}"] = df["ma_base"] * (
                    1 - current_params["envelopes"][i - 1]
                )

            df_list[pair] = df

        

        usdt_balance = await exchange.get_balance()
        usdt_balance = usdt_balance.total
        print(f"Balance: {round(usdt_balance, 2)} USDT")

        tasks = [exchange.get_open_trigger_orders(pair) for pair in pairs]
        print(f"Getting open trigger orders...")
        trigger_orders = await asyncio.gather(*tasks)
        trigger_order_list = dict(
            zip(pairs, trigger_orders)
        )  # Get all open trigger orders by pair

        tasks = []
        for pair in df_list:
            params[pair]["canceled_orders_buy"] = len(
                [
                    order
                    for order in trigger_order_list[pair]
                    if (order.side == "buy" and order.reduce is False)
                ]
            )
            params[pair]["canceled_orders_sell"] = len(
                [
                    order
                    for order in trigger_order_list[pair]
                    if (order.side == "sell" and order.reduce is False)
                ]
            )
            tasks.append(
                exchange.cancel_trigger_orders(
                    pair, [order.id for order in trigger_order_list[pair]]
                )
            )
        print(f"Canceling trigger orders...")
        await asyncio.gather(*tasks)  # Cancel all trigger orders

        tasks = [exchange.get_open_orders(pair) for pair in pairs]
        print(f"Getting open orders...")
        orders = await asyncio.gather(*tasks)
        order_list = dict(zip(pairs, orders))  # Get all open orders by pair

        tasks = []
        for pair in df_list:
            params[pair]["canceled_orders_buy"] = params[pair][
                "canceled_orders_buy"
            ] + len(
                [
                    order
                    for order in order_list[pair]
                    if (order.side == "buy" and order.reduce is False)
                ]
            )
            params[pair]["canceled_orders_sell"] = params[pair][
                "canceled_orders_sell"
            ] + len(
                [
                    order
                    for order in order_list[pair]
                    if (order.side == "sell" and order.reduce is False)
                ]
            )
            tasks.append(
                exchange.cancel_orders(pair, [order.id for order in order_list[pair]])
            )

        print(f"Canceling limit orders...")
        await asyncio.gather(*tasks)  # Cancel all orders

        print(f"Getting live positions...")
        positions = await exchange.get_open_positions(pairs)
        tasks_close = []
        tasks_open = []
        for position in positions:
            print(
                f"Current position on {position.pair} {position.side} - {position.size} ~ {position.usd_size} $"
            )
            row = df_list[position.pair].iloc[-2]
            tasks_close.append(
                exchange.place_order(
                    pair=position.pair,
                    side=invert_side[position.side],
                    price=row["ma_base"],
                    size=position.size,
                    type="limit",
                    reduce=True,
                    margin_mode=margin_mode,
                )
            )
            if position.side == "long":
                sl_side = "sell"
                sl_price = exchange.price_to_precision(position.pair, position.entry_price * (1 - sl))
            elif position.side == "short":
                sl_side = "buy"
                sl_price = exchange.price_to_precision(position.pair, position.entry_price * (1 + sl))
            tasks_close.append(
                exchange.place_trigger_order(
                    pair=position.pair,
                    side=sl_side,
                    trigger_price=sl_price,
                    price=None,
                    size=position.size,
                    type="market",
                    reduce=True,
                    margin_mode=margin_mode,
                    error=False,
                )
            )
            for i in range(
                len(params[position.pair]["envelopes"])
                - params[position.pair]["canceled_orders_buy"],
                len(params[position.pair]["envelopes"]),
            ):
                tasks_open.append(
                    exchange.place_trigger_order(
                        pair=position.pair,
                        side="buy",
                        price=exchange.price_to_precision(
                            position.pair, row[f"ma_low_{i+1}"]
                        ),
                        trigger_price=exchange.price_to_precision(
                            position.pair, row[f"ma_low_{i+1}"] * 1.005
                        ),
                        size=(
                            (params[position.pair]["size"] * usdt_balance)
                            / len(params[position.pair]["envelopes"])
                            * size_leverage
                        )
                        / row[f"ma_low_{i+1}"],
                        type="limit",
                        reduce=False,
                        margin_mode=margin_mode,
                        error=False,
                    )
                )
            for i in range(
                len(params[position.pair]["envelopes"])
                - params[position.pair]["canceled_orders_sell"],
                len(params[position.pair]["envelopes"]),
            ):
                tasks_open.append(
                    exchange.place_trigger_order(
                        pair=position.pair,
                        side="sell",
                        trigger_price=exchange.price_to_precision(
                            position.pair, row[f"ma_high_{i+1}"] * 0.995
                        ),
                        price=exchange.price_to_precision(
                            position.pair, row[f"ma_high_{i+1}"]
                        ),
                        size=(
                            (params[position.pair]["size"] * usdt_balance)
                            / len(params[position.pair]["envelopes"])
                            * size_leverage
                        )
                        / row[f"ma_high_{i+1}"],
                        type="limit",
                        reduce=False,
                        margin_mode=margin_mode,
                        error=False,
                    )
                )
            

        print(f"Placing {len(tasks_close)} close SL / limit order...")
        await asyncio.gather(*tasks_close)  # Limit orders when in positions

        pairs_not_in_position = [
            pair
            for pair in pairs
            if pair not in [position.pair for position in positions]
        ]
        for pair in pairs_not_in_position:
            row = df_list[pair].iloc[-2]
            for i in range(len(params[pair]["envelopes"])):
                tasks_open.append(
                    exchange.place_trigger_order(
                        pair=pair,
                        side="buy",
                        price=exchange.price_to_precision(pair, row[f"ma_low_{i+1}"]),
                        trigger_price=exchange.price_to_precision(
                            pair, row[f"ma_low_{i+1}"] * 1.005
                        ),
                        size=(
                            (params[pair]["size"] * usdt_balance)
                            / len(params[pair]["envelopes"])
                            * size_leverage
                        )
                        / row[f"ma_low_{i+1}"],
                        type="limit",
                        reduce=False,
                        margin_mode=margin_mode,
                        error=False,
                    )
                )
                tasks_open.append(
                    exchange.place_trigger_order(
                        pair=pair,
                        side="sell",
                        trigger_price=exchange.price_to_precision(
                            pair, row[f"ma_high_{i+1}"] * 0.995
                        ),
                        price=exchange.price_to_precision(pair, row[f"ma_high_{i+1}"]),
                        size=(
                            (params[pair]["size"] * usdt_balance)
                            / len(params[pair]["envelopes"])
                            * size_leverage
                        )
                        / row[f"ma_high_{i+1}"],
                        type="limit",
                        reduce=False,
                        margin_mode=margin_mode,
                        error=False,
                    )
                )

        print(f"Placing {len(tasks_open)} open limit order...")
        await asyncio.gather(*tasks_open)  # Limit orders when not in positions

        await exchange.close()
        print(f"--- Execution finished at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    except Exception as e:
        await exchange.close()
        raise e


if __name__ == "__main__":
    asyncio.run(main())
