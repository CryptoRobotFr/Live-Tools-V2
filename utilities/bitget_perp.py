from typing import List
import ccxt.async_support as ccxt
import asyncio
import pandas as pd
import time
import itertools
from pydantic import BaseModel


class UsdtBalance(BaseModel):
    total: float
    free: float
    used: float


class Info(BaseModel):
    success: bool
    message: str


class Order(BaseModel):
    id: str
    pair: str
    type: str
    side: str
    price: float
    size: float
    reduce: bool
    filled: float
    remaining: float
    timestamp: int


class TriggerOrder(BaseModel):
    id: str
    pair: str
    type: str
    side: str
    price: float
    trigger_price: float
    size: float
    reduce: bool
    timestamp: int


class Position(BaseModel):
    pair: str
    side: str
    size: float
    usd_size: float
    entry_price: float
    current_price: float
    unrealizedPnl: float
    liquidation_price: float
    margin_mode: str
    leverage: float
    hedge_mode: bool
    open_timestamp: int
    take_profit_price: float
    stop_loss_price: float


class PerpBitget:
    def __init__(self, public_api=None, secret_api=None, password=None):
        bitget_auth_object = {
            "apiKey": public_api,
            "secret": secret_api,
            "password": password,
            "enableRateLimit": True,
            "rateLimit": 100,
            "options": {
                "defaultType": "future",
            },
        }
        if bitget_auth_object["secret"] == None:
            self._auth = False
            self._session = ccxt.bitget()
        else:
            self._auth = True
            self._session = ccxt.bitget(bitget_auth_object)

    async def load_markets(self):
        self.market = await self._session.load_markets()

    async def close(self):
        await self._session.close()

    def ext_pair_to_pair(self, ext_pair) -> str:
        return f"{ext_pair}:USDT"

    def pair_to_ext_pair(self, pair) -> str:
        return pair.replace(":USDT", "")
    
    def get_pair_info(self, ext_pair) -> str:
        pair = self.ext_pair_to_pair(ext_pair)
        if pair in self.market:
            return self.market[pair]
        else: 
            return None

    def amount_to_precision(self, pair: str, amount: float) -> float:
        pair = self.ext_pair_to_pair(pair)
        return self._session.amount_to_precision(pair, amount)

    def price_to_precision(self, pair: str, price: float) -> float:
        pair = self.ext_pair_to_pair(pair)
        return self._session.price_to_precision(pair, price)

    async def get_last_ohlcv(self, pair, timeframe, limit=1000) -> pd.DataFrame:
        pair = self.ext_pair_to_pair(pair)
        bitget_limit = 200
        ts_dict = {
            "1m": 1 * 60 * 1000,
            "5m": 5 * 60 * 1000,
            "15m": 15 * 60 * 1000,
            "1h": 60 * 60 * 1000,
            "2h": 2 * 60 * 60 * 1000,
            "4h": 4 * 60 * 60 * 1000,
            "1d": 24 * 60 * 60 * 1000,
        }
        end_ts = int(time.time() * 1000)
        start_ts = end_ts - ((limit) * ts_dict[timeframe])
        current_ts = start_ts
        tasks = []
        while current_ts < end_ts:
            req_end_ts = min(current_ts + (bitget_limit * ts_dict[timeframe]), end_ts)
            tasks.append(
                self._session.fetch_ohlcv(
                    pair,
                    timeframe,
                    params={
                        "limit": bitget_limit,
                        "startTime": str(current_ts),
                        "endTime": str(req_end_ts),
                    },
                )
            )
            current_ts += (bitget_limit * ts_dict[timeframe]) + 1
        ohlcv_unpack = await asyncio.gather(*tasks)
        ohlcv_list = list(itertools.chain.from_iterable(ohlcv_unpack))
        df = pd.DataFrame(
            ohlcv_list, columns=["date", "open", "high", "low", "close", "volume"]
        )
        df = df.set_index(df["date"])
        df.index = pd.to_datetime(df.index, unit="ms")
        df = df.sort_index()
        del df["date"]
        return df

    async def get_balance(self) -> UsdtBalance:
        resp = await self._session.fetch_balance()
        return UsdtBalance(
            total=resp["USDT"]["total"],
            free=resp["USDT"]["free"],
            used=resp["USDT"]["used"],
        )

    async def set_margin_mode_and_leverage(self, pair, margin_mode, leverage):
        if margin_mode not in ["crossed", "isolated"]:
            raise Exception("Margin mode must be either 'crossed' or 'isolated'")
        pair = self.ext_pair_to_pair(pair)
        try:
            await self._session.set_margin_mode(
                margin_mode,
                pair,
                params={"productType": "USDT-FUTURES", "marginCoin": "USDT"},
            )
        except Exception as e:
            pass
        try:
            if margin_mode == "isolated":
                tasks = []
                tasks.append(
                    self._session.set_leverage(
                        leverage,
                        pair,
                        params={
                            "productType": "USDT-FUTURES",
                            "marginCoin": "USDT",
                            "holdSide": "long",
                        },
                    )
                )
                tasks.append(
                    self._session.set_leverage(
                        leverage,
                        pair,
                        params={
                            "productType": "USDT-FUTURES",
                            "marginCoin": "USDT",
                            "holdSide": "short",
                        },
                    )
                )
                await asyncio.gather(*tasks)
            else:
                await self._session.set_leverage(
                    leverage,
                    pair,
                    params={"productType": "USDT-FUTURES", "marginCoin": "USDT"},
                )
        except Exception as e:
            pass

        return Info(
            success=True,
            message=f"Margin mode and leverage set to {margin_mode} and {leverage}x",
        )

    async def get_open_positions(self, pairs) -> List[Position]:
        pairs = [self.ext_pair_to_pair(pair) for pair in pairs]
        resp = await self._session.fetch_positions(
            symbols=pairs, params={"productType": "USDT-FUTURES", "marginCoin": "USDT"}
        )
        return_positions = []
        for position in resp:
            liquidation_price = 0
            take_profit_price = 0
            stop_loss_price = 0
            if position["liquidationPrice"]:
                liquidation_price = position["liquidationPrice"]
            if position["takeProfitPrice"]:
                take_profit_price = position["takeProfitPrice"]
            if position["stopLossPrice"]:
                stop_loss_price = position["stopLossPrice"]

            return_positions.append(
                Position(
                    pair=self.pair_to_ext_pair(position["symbol"]),
                    side=position["side"],
                    size=position["contracts"] * position["contractSize"],
                    usd_size=round(
                        (position["contracts"] * position["contractSize"])
                        * position["markPrice"],
                        2,
                    ),
                    entry_price=position["entryPrice"],
                    current_price=position["markPrice"],
                    unrealizedPnl=position["unrealizedPnl"],
                    liquidation_price=liquidation_price,
                    leverage=position["leverage"],
                    margin_mode=position["marginMode"],
                    hedge_mode=position["hedged"],
                    open_timestamp=position["timestamp"],
                    take_profit_price=take_profit_price,
                    stop_loss_price=stop_loss_price,
                )
            )
        return return_positions

    async def place_order(
        self,
        pair,
        side,
        price,
        size,
        type="limit",
        reduce=False,
        margin_mode="crossed",
        error=True,
    ) -> Order:
        try:
            pair = self.ext_pair_to_pair(pair)
            trade_side = "Open" if reduce is False else "Close"
            resp = await self._session.create_order(
                symbol=pair,
                type=type,
                side=side,
                amount=size,
                price=price,
                params={
                    "reduceOnly": reduce,
                    "tradeSide": trade_side,
                    # "marginMode": margin_mode,
                },
            )
            order_id = resp["id"]
            pair = self.pair_to_ext_pair(resp["symbol"])
            order = await self.get_order_by_id(order_id, pair)
            return order
        except Exception as e:
            if error:
                raise e
            else:
                print(e)
                return None

    async def place_trigger_order(
        self,
        pair,
        side,
        price,
        trigger_price,
        size,
        type="limit",
        reduce=False,
        margin_mode="crossed",
        error=True,
    ) -> Info:
        try:
            pair = self.ext_pair_to_pair(pair)
            trade_side = "Open" if reduce is False else "Close"
            trigger_order = await self._session.create_trigger_order(
                symbol=pair,
                type=type,
                side=side,
                amount=size,
                price=price,
                triggerPrice=trigger_price,
                params={
                    "reduceOnly": reduce,
                    "tradeSide": trade_side,
                    # "marginMode": margin_mode,
                },
            )
            resp = Info(success=True, message="Trigger Order set up")
            return resp
        except Exception as e:
            if error:
                raise e
            else:
                print(e)
                return None

    async def get_open_orders(self, pair) -> List[Order]:
        pair = self.ext_pair_to_pair(pair)
        resp = await self._session.fetch_open_orders(pair)
        return_orders = []
        for order in resp:
            return_orders.append(
                Order(
                    id=order["id"],
                    pair=self.pair_to_ext_pair(order["symbol"]),
                    type=order["type"],
                    side=order["side"],
                    price=order["price"],
                    size=order["amount"],
                    reduce=order["reduceOnly"],
                    filled=order["filled"],
                    remaining=order["remaining"],
                    timestamp=order["timestamp"],
                )
            )
        return return_orders

    async def get_open_trigger_orders(self, pair) -> List[TriggerOrder]:
        pair = self.ext_pair_to_pair(pair)
        resp = await self._session.fetch_open_orders(pair, params={"stop": True})
        # print(resp)
        return_orders = []
        for order in resp:
            reduce = True if order["info"]["tradeSide"] == "close" else False
            price = order["price"] if order["price"] else 0.0
            return_orders.append(
                TriggerOrder(
                    id=order["id"],
                    pair=self.pair_to_ext_pair(order["symbol"]),
                    type=order["type"],
                    side=order["side"],
                    price=price,
                    trigger_price=order["triggerPrice"],
                    size=order["amount"],
                    reduce=reduce,
                    timestamp=order["timestamp"],
                )
            )
        return return_orders

    async def get_order_by_id(self, order_id, pair) -> Order:
        pair = self.ext_pair_to_pair(pair)
        resp = await self._session.fetch_order(order_id, pair)
        return Order(
            id=resp["id"],
            pair=self.pair_to_ext_pair(resp["symbol"]),
            type=resp["type"],
            side=resp["side"],
            price=resp["price"],
            size=resp["amount"],
            reduce=resp["reduceOnly"],
            filled=resp["filled"],
            remaining=resp["remaining"],
            timestamp=resp["timestamp"],
        )

    async def cancel_orders(self, pair, ids=[]):
        try:
            pair = self.ext_pair_to_pair(pair)
            resp = await self._session.cancel_orders(
                ids=ids,
                symbol=pair,
            )
            return Info(success=True, message=f"{len(resp)} Orders cancelled")
        except Exception as e:
            return Info(success=False, message="Error or no orders to cancel")

    async def cancel_trigger_orders(self, pair, ids=[]):
        try:
            pair = self.ext_pair_to_pair(pair)
            resp = await self._session.cancel_orders(
                ids=ids, symbol=pair, params={"stop": True}
            )
            return Info(success=True, message=f"{len(resp)} Trigger Orders cancelled")
        except Exception as e:
            return Info(success=False, message="Error or no orders to cancel")
