from typing import List
import ccxt.async_support as ccxt
import asyncio

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
    amount: float
    filled: float
    remaining: float
    timestamp: int

class Position(BaseModel):
    pair: str
    side: str
    amount: float
    entry_price: float
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

    async def fetch_balance(self) -> UsdtBalance:
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
            await self._session.set_margin_mode(margin_mode, pair, params={"productType": "USDT-FUTURES", "marginCoin": "USDT"})
        except Exception as e:
            pass
        try:
            if margin_mode == "isolated":
                tasks = []
                tasks.append(self._session.set_leverage(leverage, pair, params={"productType": "USDT-FUTURES", "marginCoin": "USDT", "holdSide": "long"}))
                tasks.append(self._session.set_leverage(leverage, pair, params={"productType": "USDT-FUTURES", "marginCoin": "USDT", "holdSide": "short"}))
                await asyncio.gather(*tasks)
            else:
                await self._session.set_leverage(leverage, pair, params={"productType": "USDT-FUTURES", "marginCoin": "USDT"})
        except Exception as e:
            pass
        
        return Info(success=True, message=f"Margin mode and leverage set to {margin_mode} and {leverage}x")
    
    async def get_open_positions(self, pairs) -> List[Position]:
        pairs = [self.ext_pair_to_pair(pair) for pair in pairs]
        resp = await self._session.fetch_positions(symbols=pairs, params={"productType": "USDT-FUTURES", "marginCoin": "USDT"})
        return_positions = []
        for position in resp:
            liquidation_price = 0
            take_profit_price = 0
            stop_loss_price = 0
            if position["liquidationPrice"]: liquidation_price = position["liquidationPrice"]
            if position["takeProfitPrice"]: take_profit_price = position["takeProfitPrice"]
            if position["stopLossPrice"]: stop_loss_price = position["stopLossPrice"]
                
            return_positions.append(Position(
                pair=self.pair_to_ext_pair(position["symbol"]),
                side=position["side"],
                amount=position["contracts"] * position["contractSize"],
                entry_price=position["entryPrice"],
                unrealizedPnl=position["unrealizedPnl"],
                liquidation_price=liquidation_price,
                leverage=position["leverage"],
                margin_mode=position["marginMode"],
                hedge_mode=position["hedged"],
                open_timestamp=position["timestamp"],
                take_profit_price=take_profit_price,
                stop_loss_price=stop_loss_price,
            ))
        return return_positions
    
    async def place_order(self, pair, side, price, amount, type="limit", reduce=False) -> Order:
        pair = self.ext_pair_to_pair(pair)
        resp = await self._session.create_order(pair, type, side, amount, price, params={"reduceOnly": reduce})
        order_id = resp["id"]
        pair = self.pair_to_ext_pair(resp["symbol"])
        order = await self.get_order_by_id(order_id, pair)
        return order
    
    async def get_open_orders(self, pair) -> List[Order]:
        pair = self.ext_pair_to_pair(pair)
        resp = await self._session.fetch_open_orders(pair)
        return_orders = []
        for order in resp:
            return_orders.append(Order(
                id=order["id"],
                pair=self.pair_to_ext_pair(order["symbol"]),
                type=order["type"],
                side=order["side"],
                price=order["price"],
                amount=order["amount"],
                filled=order["filled"],
                remaining=order["remaining"],
                timestamp=order["timestamp"],
            ))
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
            amount=resp["amount"],
            filled=resp["filled"],
            remaining=resp["remaining"],
            timestamp=resp["timestamp"],
        )
    
    async def cancel_orders(self, pair):
        try:
            pair = self.ext_pair_to_pair(pair)
            resp = await self._session.cancel_all_orders(pair)
            return Info(success=True, message=f"{len(resp["data"]["successList"])} orders cancelled")
        except Exception as e:
            return Info(success=False, message="Error or no orders to cancel")
            
