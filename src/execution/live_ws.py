import asyncio
import aiohttp
import json
from typing import Dict, Any, List, Optional
from src.utils.logging import get_agent_logger

logger = get_agent_logger("binance_ws")

class BinanceWSClient:
    """
    Asynchronous WebSocket client for Binance public market streams.
    Subscribes to ticker and top depth levels using aiohttp.
    """
    def __init__(self, symbol: str = "BTCUSDT"):
        self.symbol = symbol.lower()
        self.url = f"wss://stream.binance.com:9443/ws/{self.symbol}@ticker/{self.symbol}@depth5"
        self.bid_price = 0.0
        self.ask_price = 0.0
        self.bids: List[List[float]] = [] # [[price, qty], ...]
        self.asks: List[List[float]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._connect_loop())
        logger.info("Binance WS stream loop started.")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Binance WS stream loop stopped.")

    async def _connect_loop(self) -> None:
        while self._running:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(self.url) as ws:
                        logger.info("Connected to Binance WebSocket stream.")
                        async for msg in ws:
                            if not self._running:
                                break
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                self._handle_message(data)
                            elif msg.type == aiohttp.WSMsgType.CLOSED:
                                break
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

    def _handle_message(self, data: Dict[str, Any]) -> None:
        # Check if depth update
        if "bids" in data and "asks" in data:
            self.bids = [[float(p), float(q)] for p, q in data["bids"]]
            self.asks = [[float(p), float(q)] for p, q in data["asks"]]
            if len(self.bids) > 0:
                self.bid_price = self.bids[0][0]
            if len(self.asks) > 0:
                self.ask_price = self.asks[0][0]
        # Check if ticker update
        elif "b" in data and "a" in data:
            self.bid_price = float(data["b"])
            self.ask_price = float(data["a"])
            
    def get_mid_price(self) -> float:
        if self.bid_price > 0 and self.ask_price > 0:
            return (self.bid_price + self.ask_price) / 2.0
        return 0.0
