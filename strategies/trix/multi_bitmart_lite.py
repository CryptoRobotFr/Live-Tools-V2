import sys
sys.path.append("./Live-Tools-V2")

import asyncio
import datetime
from utilities.bitmart_perp import PerpBitmart
from utilities.custom_indicators import Trix
from utilities.discord_logger import DiscordLogger
from secret import ACCOUNTS
import ta
import math
import copy
import json

MARGIN_MODE = "isolated" # isolated or cross
LEVERAGE = 2
ACCOUNT_NAME = "bitmart1"
SIDE = ["long"]
DISCORD_WEBHOOK = ""
PARAMS = {
    "1h": {
        "p1": {
            "BTC/USDT": {
                "trix_length": 19,
                "trix_signal_length": 15,
                "trix_signal_type": "sma",
                "long_ma_length": 500,
            },
            "ETH/USDT": {
                "trix_length": 21,
                "trix_signal_length": 9,
                "trix_signal_type": "ema",
                "long_ma_length": 500,
            },
        },
    },
    "2h": {
        "p1": {
            "BTC/USDT": {
                "trix_length": 7,
                "trix_signal_length": 11,
                "trix_signal_type": "ema",
                "long_ma_length": 300,
            },
            "ETH/USDT": {
                "trix_length": 21,
                "trix_signal_length": 47,
                "trix_signal_type": "sma",
                "long_ma_length": 300,
            },
        },
    },
    "4h": {
        "p1": {
            "BTC/USDT": {
                "trix_length": 11,
                "trix_signal_length": 45,
                "trix_signal_type": "ema",
                "long_ma_length": 200,
            },
            "ETH/USDT": {
                "trix_length": 19,
                "trix_signal_length": 7,
                "trix_signal_type": "ema",
                "long_ma_length": 200,
            },
        },
    },
}
RELATIVE_PATH = "./Live-Tools-V2/strategies/trix"

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def main():
    account = ACCOUNTS[ACCOUNT_NAME]

    margin_mode = MARGIN_MODE
    leverage = LEVERAGE
    exchange_leverage = math.ceil(leverage)
    params = PARAMS
    dl = DiscordLogger(DISCORD_WEBHOOK)
    exchange = PerpBitmart(
        public_api=account["public_api"],
        secret_api=account["secret_api"],
        uid=account["memo"],
    )
    print(f"--- Execution started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    # Read json position file, if not exist, create it
    try:
        with open(f"{RELATIVE_PATH}/positions_{ACCOUNT_NAME}.json", "r") as f:
            key_positions = json.load(f)
    except Exception as e:
        key_positions = {}
        with open(f"{RELATIVE_PATH}/positions_{ACCOUNT_NAME}.json", "w") as f:
            json.dump(key_positions, f)


    try:
        await exchange.load_markets()

        pair_list = []
        key_params = {}
        for tf in params.keys():
            for param in params[tf].keys():
                for pair in params[tf][param].keys():
                    if pair not in pair_list:
                        pair_list.append(pair)
                    key_params[f"{tf}-{param}-{pair}"] = params[tf][param][pair]
                    key_params[f"{tf}-{param}-{pair}"]["pair"] = pair
                    key_params[f"{tf}-{param}-{pair}"]["tf"] = tf

        key_params_copy = copy.deepcopy(key_params)
        for key_param in key_params_copy.keys():
            key_param_object = key_params_copy[key_param]
            info = exchange.get_pair_info(key_param_object["pair"])
            if info is None:
                await dl.send_now(f"Pair {key_param_object['pair']} not found, removing from params...", level="WARNING")
                del key_params[key_param]
                pair_list.remove(key_param_object["pair"])
        
        print(f"Getting data and indicators on {len(pair_list)} pairs...")
        tasks = []
        keys = []
        tf_pair_loaded = []
        for key_param in key_params.keys():
            key_param_object = key_params[key_param]
            # Check if param have a size
            if "size" not in key_param_object.keys():
                key_param_object["size"] = 1/len(key_params)
            if f"{key_param_object["pair"]}-{key_param_object["tf"]}" not in tf_pair_loaded:
                tf_pair_loaded.append(f"{key_param_object["pair"]}-{key_param_object["tf"]}")
                keys.append(f"{key_param_object["pair"]}-{key_param_object["tf"]}")

                tasks.append(exchange.get_last_ohlcv(key_param_object["pair"], key_param_object["tf"], 600))

        dfs = await asyncio.gather(*tasks)
        df_data = dict(zip(keys, dfs))
        df_list = {}

        for key_param in key_params.keys():
            key_param_object = key_params[key_param]
            df = df_data[f"{key_param_object["pair"]}-{key_param_object["tf"]}"]

            trix_obj = Trix(
                close=df["close"],
                trix_length=key_param_object["trix_length"],
                trix_signal_length=key_param_object["trix_signal_length"],
                trix_signal_type=key_param_object["trix_signal_type"],
            )
            df["trix"] = trix_obj.get_trix_pct_line()
            df["trix_signal"] = trix_obj.get_trix_signal_line()
            df["trix_hist"] = df["trix"] - df["trix_signal"]

            df["long_ma"] = ta.trend.ema_indicator(
                df["close"], window=key_param_object["long_ma_length"]
            )
            
            df_list[key_param] = df

        # print(df_list)
        # print(key_params)

        usdt_balance = await exchange.get_balance()
        usdt_balance = usdt_balance.total
        dl.log(f"Balance: {round(usdt_balance, 2)} USDT")

        positions = await exchange.get_open_positions(pair_list)
        long_exposition = sum([p.usd_size for p in positions if p.side == "long"])
        short_exposition = sum([p.usd_size for p in positions if p.side == "short"])
        unrealized_pnl = sum([p.unrealizedPnl for p in positions])
        dl.log(f"Unrealized PNL: {round(unrealized_pnl, 2)}$ | Long Exposition: {round(long_exposition, 2)}$ | Short Exposition: {round(short_exposition, 2)}$")
        dl.log(f"Current positions:")
        for position in positions:
            dl.log(f"{(position.side).upper()} {position.size} {position.pair} ~{position.usd_size}$ (+ {position.unrealizedPnl}$)")

        try:
            print(f"Setting {margin_mode} x{exchange_leverage} on {len(pair_list)} pairs...")
            tasks = [
                exchange.set_margin_mode_and_leverage(
                    pair, margin_mode, exchange_leverage
                )
                for pair in pair_list if pair not in [position.pair for position in positions]
            ]
            await asyncio.gather(*tasks)  # set leverage and margin mode for all pairs
        except Exception as e:
            print("error:",e)

        # --- Close positions ---
        key_positions_copy = copy.deepcopy(key_positions)
        for key_position in key_positions_copy:
            position_object = key_positions_copy[key_position]
            param_object = key_params[key_position]
            df = df_list[key_position]
            exchange_positions = [p for p in positions if (p.pair == param_object["pair"] and p.side == position_object["side"])]
            if len(exchange_positions) == 0:
                print(f"No position found for {param_object['pair']}, skipping...")
                continue
            exchange_position_size = sum([p.size for p in exchange_positions])
            row = df.iloc[-2]
            
            if position_object["side"] == "long":
                if row["trix_hist"] < 0:
                    close_size = min(position_object["size"], exchange_position_size)
                    try:
                        order = await exchange.place_order(
                            pair=param_object["pair"],
                            side="sell",
                            price=None,
                            size=close_size,
                            type="market",
                            reduce=True,
                            margin_mode=margin_mode,
                            leverage=math.ceil(leverage),
                            error=True,
                        )
                        if order is not None:
                            del key_positions[key_position]
                            dl.log(f"{key_position} Closed {order.size} {param_object['pair']} long")
                    except Exception as e:
                        await dl.send_now(f"{key_position} Error closing {param_object['pair']} long: {e}", level="ERROR")
                        continue
            elif position_object["side"] == "short":
                if row["trix_hist"] > 0:
                    close_size = min(position_object["size"], exchange_position_size)
                    try:
                        order = await exchange.place_order(
                            pair=param_object["pair"],
                            side="buy",
                            price=None,
                            size=close_size,
                            type="market",
                            reduce=True,
                            margin_mode=margin_mode,
                            leverage=math.ceil(leverage),
                            error=True,
                        )
                        if order is not None:
                            del key_positions[key_position]
                            dl.log(f"{key_position} Closed {order.size} {param_object['pair']} short")
                    except Exception as e:
                        await dl.send_now(f"{key_position} Error closing {param_object['pair']} short: {e}", level="ERROR")
                        continue

        # --- Open positions ---
        for key_param in key_params.keys():
            if key_param in key_positions.keys():
                continue
            param_object = key_params[key_param]
            df = df_list[key_param]
            row = df.iloc[-2]
            last_price = df["close"].iloc[-1]
            if row["trix_hist"] > 0 and row["close"] > row["long_ma"] and "long" in SIDE:
                open_size = (usdt_balance * param_object["size"]) / last_price * leverage
                try:
                    order = await exchange.place_order(
                        pair=param_object["pair"],
                        side="buy",
                        price=None,
                        size=open_size,
                        type="market",
                        reduce=False,
                        margin_mode=margin_mode,
                        leverage=math.ceil(leverage),
                        error=True,
                    )
                    if order is not None:
                        key_positions[key_param] = {
                            "side": "long",
                            "size": open_size,
                            "open_price": order.price,
                            "open_time": order.timestamp,
                        }
                        dl.log(f"{key_param} Opened {order.size} {param_object['pair']} long")
                except Exception as e:
                    await dl.send_now(f"{key_param} Error opening {param_object['pair']} long: {e}", level="ERROR")
                    continue
            elif row["trix_hist"] < 0 and row["close"] < row["long_ma"] and "short" in SIDE:
                open_size = (usdt_balance * param_object["size"]) / last_price * leverage
                try:
                    order = await exchange.place_order(
                        pair=param_object["pair"],
                        side="sell",
                        price=None,
                        size=open_size,
                        type="market",
                        reduce=False,
                        margin_mode=margin_mode,
                        leverage=math.ceil(leverage),
                        error=True,
                    )
                    if order is not None:
                        key_positions[key_param] = {
                            "side": "short",
                            "size": open_size,
                            "open_price": order.price,
                            "open_time": order.timestamp,
                        }
                        dl.log(f"{key_param} Opened {order.size} {param_object['pair']} short")
                except Exception as e:
                    await dl.send_now(f"{key_param} Error opening {param_object['pair']} short: {e}", level="ERROR")
                    continue

        # --- Save positions ---
        with open(f"{RELATIVE_PATH}/positions_{ACCOUNT_NAME}.json", "w") as f:
            json.dump(key_positions, f)
            

        await exchange.close()
        print(f"--- Execution finished at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")

        await dl.send_discord_message(level="INFO")

    except Exception as e:
        await exchange.close()
        raise e


if __name__ == "__main__":
    asyncio.run(main())
