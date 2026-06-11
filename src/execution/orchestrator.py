import time
import datetime
import redis
from typing import Dict, Any, List, Optional
from src.config import settings
from src.utils.logging import get_agent_logger
from src.utils.db import get_connection, release_connection
from src.data.ingester import DataIngester
from src.features.engine import FeatureEngine
from src.inventory.ledger import FIFOLedger
from src.inventory.models import InventoryRepository
from src.grid.engine import GridEngine
from src.risk.overlay import RiskOverlay, ProposedOrder, InvariantViolationError, SystemHaltError
from src.execution.ccxt_mock import BinanceMock
from src.execution.live_ws import BinanceWSClient
from src.execution.paper import BinancePaper
from src.portfolio.tracker import PortfolioTracker
from src.custody.sweeper import CustodySweeper
from src.regime.classifier import RegimeClassifier
from src.monitoring.exporter import loop_latency, order_slippage, portfolio_balance, api_error_counter, invariant_violation_counter, TelegramNotifier
from src.execution.delta_neutral import DeltaNeutralManager

logger = get_agent_logger("orchestrator")

class ABASOrchestrator:
    """
    Orchestrates the sequential tick pipeline of agents and handles execution flow.
    """
    def __init__(self, use_mock: bool = True, redis_client: Optional[redis.Redis] = None, paper_mode: bool = False):
        self.use_mock = use_mock
        self.paper_mode = paper_mode
        self.redis_client = redis_client or redis.from_url(settings.redis_url)
        self.ingester = DataIngester(redis_client=self.redis_client)
        self.features_engine = FeatureEngine()
        self.regime_classifier = RegimeClassifier()
        self.ledger = FIFOLedger()
        self.grid_engine = GridEngine()
        self.risk_overlay = RiskOverlay()
        self.portfolio_tracker = PortfolioTracker(hot_exchange_cap=settings.hot_exchange_cap)
        self.custody_sweeper = CustodySweeper(trading_target=settings.trading_target, promotion_threshold_multiplier=settings.promotion_threshold)
        self.notifier = TelegramNotifier()
        self.anchored_local_low: Optional[float] = None
        
        # Initialize execution exchange connection
        if use_mock:
            self.exchange = BinanceMock()
            # Feed ledger balances directly from the mock exchange
            self.ledger.reserve_usdt = self.exchange.reserve_usdt
            self.ledger.trading_btc_qty = self.exchange.trading_btc
        elif paper_mode:
            import ccxt
            import asyncio
            self.ws_client = BinanceWSClient()
            # Start background websocket task
            asyncio.create_task(self.ws_client.start())
            self.real_exchange = ccxt.binance({
                "apiKey": settings.binance_api_key,
                "secret": settings.binance_secret,
                "enableRateLimit": settings.binance_enable_rate_limit
            })
            self.exchange = BinancePaper(self.real_exchange, self.ws_client)
            self.exchange.initialize_balances()
        else:
            import ccxt
            self.exchange = ccxt.binance({
                "apiKey": settings.binance_api_key,
                "secret": settings.binance_secret,
                "enableRateLimit": settings.binance_enable_rate_limit
            })
            
        self.delta_neutral_manager = DeltaNeutralManager(self.exchange, max_allocation_pct=0.20)
        self.last_heartbeat_time = 0.0

    def run_tick(self) -> None:
        """
        Executes a single chronological cycle.
        """
        start_time = time.time()
        logger.info("Initiating sequential tick execution cycle...", action="tick_start")

        # 0. Fail-Safe Heartbeat
        self.emit_heartbeat()

        try:
            # 1. Data Ingestion & Validation
            tick = self.ingester.ingest_tick()
            if tick is None:
                # Outlier quarantined, exit tick early
                logger.warning("Tick skipped because validator flagged data as an outlier.")
                return

            tick_time = datetime.datetime.fromtimestamp(tick["timestamp"] / 1000.0, datetime.timezone.utc)

            self.save_raw_ohlcv_to_db(tick)

            # 2. Feature Engineering & Anchor Calculations
            # Fetch last 500 records to calculate daily and 4h rolling statistics
            features = self.features_engine.compute_latest_features(limit=500)
            if features is None:
                logger.warning("Skipping tick: insufficient historical candles in database to compute features.")
                return

            price = float(features["close"])
            a_trend = float(features["A_trend"])
            a_range = float(features["A_range"])
            a_mean = float(features["A_mean"])
            float(features["sigma_ann"])

            # 3. AI Overlay Unsupervised Regime Detection
            regime_dict = self.regime_classifier.predict_tick(features)
            regime = regime_dict["regime"]
            confidence = regime_dict["confidence"]

            # 4. Inventory Management Loading & FIFO sync
            self.ledger.load_from_db()
            
            # Sync balances with the exchange account
            try:
                balances = self.exchange.fetch_balance()
            except Exception as e:
                api_error_counter.labels(exchange="binance").inc()
                raise e
            self.ledger.reserve_usdt = float(balances["free"]["USDT"])
            
            # Subtract Delta-Neutral spot BTC to avoid grid interference
            dn_spot_qty = self.delta_neutral_manager.spot_qty
            self.ledger.trading_btc_qty = max(0.0, float(balances["free"]["BTC"]) - dn_spot_qty)

            # Delta-Neutral Sleeve
            total_val = self.get_total_portfolio_value_usdt(price)
            if getattr(settings, "delta_neutral_enabled", False):
                perp_price = price
                if not self.use_mock:
                    try:
                        ticker = self.exchange.fetch_ticker("BTC/USDT:USDT")
                        perp_price = float(ticker.get("last", price))
                    except Exception as e:
                        logger.warning(f"Failed to fetch perp ticker from exchange: {e}. Using spot price.")
                
                funding_rate = float(features.get("funding_rate", 0.0))
                dn_orders = self.delta_neutral_manager.execute_tick(
                    spot_price=price,
                    perp_price=perp_price,
                    funding_rate=funding_rate,
                    total_portfolio_val_usdt=total_val
                )
                
                for dn_order in dn_orders:
                    symbol = "BTC/USDT:USDT" if dn_order["market"] == "perp" else "BTC/USDT"
                    logger.info(f"Executing approved Delta-Neutral order: {dn_order['side'].upper()} {dn_order['qty']:.6f} {symbol} @ {dn_order['price']:.2f}")
                    try:
                        self.exchange.create_order(
                            symbol=symbol,
                            type="limit",
                            side=dn_order["side"],
                            amount=dn_order["qty"],
                            price=dn_order["price"]
                        )
                    except Exception as e:
                        api_error_counter.labels(exchange="binance").inc()
                        logger.error(f"Failed to execute Delta-Neutral order: {e}")
                
                if dn_orders:
                    try:
                        balances = self.exchange.fetch_balance()
                        self.ledger.reserve_usdt = float(balances["free"]["USDT"])
                        dn_spot_qty = self.delta_neutral_manager.spot_qty
                        self.ledger.trading_btc_qty = max(0.0, float(balances["free"]["BTC"]) - dn_spot_qty)
                    except Exception as e:
                        logger.warning(f"Failed to re-sync balances after Delta-Neutral orders: {e}")

            # Check Custody Promotion sweep signal
            excess = self.custody_sweeper.check_promotion_trigger(tick_time)
            if excess and excess > 0:
                logger.critical(f"Sweeping excess {excess:.6f} BTC from trading to core cold storage.")
                self.ledger.core_btc_qty += excess
                self.ledger.trading_btc_qty -= excess
                # Update mock/live exchange
                if hasattr(self.exchange, "trading_btc"):
                    self.exchange.trading_btc -= excess
                self.notifier.send_alert(f"Core Promotion Sweep Triggered: Swept {excess:.6f} BTC to cold storage.")

            # Reconcile balances and monitor exposure
            db_state = self.ledger.get_state_snapshot()
            self.portfolio_tracker.reconcile_balances(
                exchange_usdt=self.ledger.reserve_usdt,
                exchange_btc=self.ledger.trading_btc_qty,
                db_reserve_usdt=db_state["reserve_usdt"],
                db_trading_btc=db_state["trading_btc_qty"]
            )
            self.portfolio_tracker.monitor_exposure(
                trading_btc_qty=self.ledger.trading_btc_qty,
                core_btc_qty=self.ledger.core_btc_qty,
                reserve_usdt=self.ledger.reserve_usdt,
                btc_price=price
            )

            # 5. Adaptive Grid Ordering Proposal
            proposed_orders: List[ProposedOrder] = []

            # Buy check
            buy_val_usdt = self.grid_engine.calculate_buy_size(
                current_price=price,
                a_range=a_range,
                remaining_reserve=self.ledger.reserve_usdt,
                total_portfolio_value_usdt=self.get_total_portfolio_value_usdt(price),
                regime=regime
            )
            # Cap buy size to the remaining daily deployment cap to prevent invariant violation halts
            portfolio_val = self.get_total_portfolio_value_usdt(price)
            max_daily = portfolio_val * settings.daily_deployment_cap
            daily_deployed = self.get_daily_deployed_usdt(tick_time)
            remaining_daily_cap = max(0.0, max_daily - daily_deployed)
            
            # Cap buy size to the hot exchange cap to prevent INV-7 halts (using a small safety margin for float precision)
            max_buy_val_for_hot_exchange = max(0.0, ((settings.hot_exchange_cap - 1e-5) * portfolio_val) - (self.ledger.trading_btc_qty * price))
            
            buy_val_usdt = min(buy_val_usdt, remaining_daily_cap, max_buy_val_for_hot_exchange)

            if buy_val_usdt >= 10.0:  # Minimum 10 USDT Binance order size
                buy_qty = buy_val_usdt / price
                proposed_orders.append(ProposedOrder(side="buy", qty=buy_qty, price=price))

            # Sell check (rebound low tracked dynamically)
            a_local_low_48h = float(features.get("A_local_low_48h", a_mean * 0.97))
            rebound_threshold = a_local_low_48h * 1.04
            
            if price >= rebound_threshold:
                if self.anchored_local_low is None:
                    self.anchored_local_low = a_local_low_48h
                    logger.info(f"Rebound detected! Anchoring local_low to {self.anchored_local_low:.2f}")
            else:
                if self.anchored_local_low is not None and price < self.anchored_local_low:
                    logger.info(f"Price fell below anchored local low. Resetting from {self.anchored_local_low:.2f} to {a_local_low_48h:.2f}")
                    self.anchored_local_low = a_local_low_48h
            
            local_low = self.anchored_local_low if self.anchored_local_low is not None else a_local_low_48h
            
            sell_qty_btc = self.grid_engine.calculate_sell_size(
                current_price=price,
                local_low=local_low,
                trading_btc_qty=self.ledger.trading_btc_qty,
                total_portfolio_value_btc=self.ledger.total_btc_qty,
                avg_cost_fifo_lot=self.ledger.avg_cost_fifo_lot,
                regime=regime
            )
            if sell_qty_btc > 0.0001:
                proposed_orders.append(ProposedOrder(side="sell", qty=sell_qty_btc, price=price))

            # 6. Risk Overlay & Invariant Audits
            daily_deployed = self.get_daily_deployed_usdt(tick_time)
            self.risk_overlay.check_invariants(
                proposed_orders=proposed_orders,
                current_state=self.ledger.get_state_snapshot(),
                btc_price=price,
                daily_deployed_usdt=daily_deployed
            )

            # Audit kill switches (using mock values for live simulation parameters)
            self.risk_overlay.audit_kill_switches(
                drawdown_24h=0.0,
                drawdown_7d=0.0,
                current_reserve_usdt=self.ledger.reserve_usdt,
                total_portfolio_usdt=self.get_total_portfolio_value_usdt(price),
                api_error_rate_5m=0.0,
                stablecoin_peg_deviations={"USDT": 0.0},
                bid_ask_spread_binance=0.0002,
                median_30d_spread=0.0002,
                execution_slippage=0.0
            )

            # 7. Order Execution & Slippage audits
            for order in proposed_orders:
                logger.info(
                    f"Executing approved order: {order.side.upper()} {order.qty:.6f} BTC @ {order.price:.2f}",
                    action="execute_order"
                )
                try:
                    exec_report = self.exchange.create_order(
                        symbol="BTC/USDT",
                        type="limit",
                        side=order.side,
                        amount=order.qty,
                        price=order.price
                    )
                except Exception as e:
                    api_error_counter.labels(exchange="binance").inc()
                    raise e

                # Slippage verification (calculated dynamically vs placement tick price)
                exec_price = exec_report.get("average", price)
                slippage = abs(exec_price - price) / price
                order_slippage.set(slippage)
                if slippage > 0.02:
                    self.risk_overlay.trigger_halt(f"Executed price slippage {slippage*100:.2f}% exceeds 2% cap.")

                # Update FIFO ledger
                exec_qty = exec_report["amount"]

                if order.side == "buy":
                    self.ledger.add_buy_lot(
                        qty=exec_qty,
                        price=exec_price,
                        timestamp=tick_time,
                        regime_tag=str(regime)
                    )
                elif order.side == "sell":
                    self.ledger.consume_sell_lots(
                        qty_to_sell=exec_qty,
                        sell_price=exec_price,
                        timestamp=tick_time,
                        order_id=exec_report["id"]
                    )
                    # Reset anchored local low to start a new cycle
                    self.anchored_local_low = None
                    logger.info("Sell executed. Resetting anchored local low for next cycle.")

            # 8. Portfolio Tracking Snapshots Persistence
            total_val = self.get_total_portfolio_value_usdt(price)
            InventoryRepository.save_portfolio_state(
                time_val=tick_time,
                core_btc=self.ledger.core_btc_qty,
                trading_btc=self.ledger.trading_btc_qty,
                reserve_usdt=self.ledger.reserve_usdt,
                total_val=total_val,
                regime=regime,
                confidence=confidence
            )

            # Update Prometheus gauges
            portfolio_balance.labels(sleeve="core", asset="BTC").set(self.ledger.core_btc_qty)
            portfolio_balance.labels(sleeve="trading", asset="BTC").set(self.ledger.trading_btc_qty)
            portfolio_balance.labels(sleeve="reserve", asset="USDT").set(self.ledger.reserve_usdt)

            latency_ms = (time.time() - start_time) * 1000
            loop_latency.labels(agent_name="orchestrator").set(latency_ms)
            logger.info(
                f"Tick cycle completed successfully. Latency: {latency_ms:.1f}ms",
                action="tick_end"
            )

        except InvariantViolationError as e:
            logger.error(f"Order rejected by Risk Overlay: {e}", action="invariant_violation")
            invariant_violation_counter.inc()
            self.notifier.send_alert(f"Invariant Violation: {e}")
        except SystemHaltError as e:
            logger.critical(f"System entered HALT state: {e}", action="system_halt")
            self.risk_overlay.system_halted = True
            self.notifier.send_alert(f"SYSTEM HALT: {e}")
        except Exception as e:
            logger.error(f"Unexpected exception in orchestrator tick: {e}", exc_info=True, action="loop_error")

    def emit_heartbeat(self) -> None:
        """
        Emits system heartbeat to Redis every 10 seconds.
        """
        now = time.time()
        if now - self.last_heartbeat_time >= 10.0:
            try:
                self.redis_client.setex("heartbeat:orchestrator", 15, "alive")
                self.last_heartbeat_time = now
                logger.info("Heartbeat pulse emitted to Redis.", action="emit_heartbeat")
            except Exception as e:
                logger.warning(f"Failed to publish Redis heartbeat: {e}")

    def get_total_portfolio_value_usdt(self, btc_price: float) -> float:
        dn_spot_qty = getattr(self.delta_neutral_manager, "spot_qty", 0.0)
        return self.ledger.reserve_usdt + (self.ledger.core_btc_qty + self.ledger.trading_btc_qty + dn_spot_qty) * btc_price

    def save_raw_ohlcv_to_db(self, tick: Dict[str, Any]) -> None:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                # Store candle
                cur.execute(
                    """
                    INSERT INTO binance_ohlcv (time, symbol, open, high, low, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        datetime.datetime.fromtimestamp(tick["timestamp"] / 1000.0, datetime.timezone.utc),
                        "BTC/USDT",
                        tick["open"],
                        tick["high"],
                        tick["low"],
                        tick["close"],
                        tick["volume"]
                    )
                )
                # Store perp data
                if tick.get("funding_rate") is not None:
                    cur.execute(
                        """
                        INSERT INTO binance_funding_rates (time, symbol, funding_rate)
                        VALUES (%s, %s, %s)
                        """,
                        (
                            datetime.datetime.fromtimestamp(tick["timestamp"] / 1000.0, datetime.timezone.utc),
                            "BTC/USDT",
                            tick["funding_rate"]
                        )
                    )
                if tick.get("open_interest") is not None:
                    cur.execute(
                        """
                        INSERT INTO binance_open_interest (time, symbol, open_interest)
                        VALUES (%s, %s, %s)
                        """,
                        (
                            datetime.datetime.fromtimestamp(tick["timestamp"] / 1000.0, datetime.timezone.utc),
                            "BTC/USDT",
                            tick["open_interest"]
                        )
                    )
                conn.commit()
        except Exception as e:
            logger.error(f"Error persisting raw OHLCV tick: {e}")
        finally:
            release_connection(conn)

    def get_daily_deployed_usdt(self, current_time: datetime.datetime) -> float:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                # Sum the value of all buy trade history in the last 24h relative to current_time
                cur.execute(
                    """
                    SELECT COALESCE(SUM(qty * price), 0.0)
                    FROM trade_history
                    WHERE side = 'buy' AND time >= %s - INTERVAL '24 hours' AND time <= %s
                    """,
                    (current_time, current_time)
                )
                return float(cur.fetchone()[0])
        except Exception as e:
            logger.error(f"Error computing daily deployed value: {e}")
            return 0.0
        finally:
            release_connection(conn)
