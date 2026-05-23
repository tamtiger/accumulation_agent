import os
import time
import datetime
import logging
import pandas as pd
from typing import Dict, Any, Optional
from src.config import settings
from src.utils.db import get_connection, release_connection
from src.utils.init_db import init_db
from src.execution.orchestrator import ABASOrchestrator

logger = logging.getLogger("backtest_harness")

class BacktestHarness:
    """
    Executes a historical cycle-by-cycle backtest by feeding data to the orchestrator tick-by-tick.
    Models trading fees, slippage, and tax drag on realized P&L.
    """
    def __init__(
        self,
        initial_usdt: float = 100000.0,
        initial_core_btc: float = 0.0,
        tax_rate: float = 0.20,  # 20% capital gains tax
        maker_fee: float = 0.0002,
        taker_fee: float = 0.0010,
        slippage: float = 0.0005
    ):
        self.initial_usdt = initial_usdt
        self.initial_core_btc = initial_core_btc
        self.tax_rate = tax_rate
        
        # Reset database tables to ensure clean state
        self._reset_database()
        
        # Initialize orchestrator in mock mode
        self.orchestrator = ABASOrchestrator(use_mock=True)
        
        # Override mock exchange parameters to match backtest settings
        self.orchestrator.exchange.reserve_usdt = initial_usdt
        self.orchestrator.exchange.maker_fee = maker_fee
        self.orchestrator.exchange.taker_fee = taker_fee
        self.orchestrator.exchange.slippage_mean = slippage
        
        # Set ledger sleeves
        self.orchestrator.ledger.reserve_usdt = initial_usdt
        self.orchestrator.ledger.core_btc_qty = initial_core_btc
        self.orchestrator.ledger.trading_btc_qty = self.orchestrator.exchange.trading_btc

    def _reset_database(self) -> None:
        """
        Clears all trading database tables before running backtest.
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE binance_ohlcv CASCADE;")
                cur.execute("TRUNCATE TABLE binance_funding_rates CASCADE;")
                cur.execute("TRUNCATE TABLE binance_open_interest CASCADE;")
                cur.execute("TRUNCATE TABLE binance_liquidations CASCADE;")
                cur.execute("TRUNCATE TABLE portfolio_states CASCADE;")
                cur.execute("TRUNCATE TABLE trade_history CASCADE;")
                cur.execute("TRUNCATE TABLE trade_lots CASCADE;")
                conn.commit()
            logger.info("Database truncated for backtest run.")
        except Exception as e:
            logger.warning(f"Failed to truncate tables (may not exist yet): {e}")
            # Recreate schemas
            init_db()
        finally:
            release_connection(conn)

    def run(self, df_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Runs the backtest tick-by-tick over the input DataFrame.
        Expected columns: ['time', 'open', 'high', 'low', 'close', 'volume']
        Optional columns: ['funding_rate', 'open_interest', 'liquidations']
        """
        total_ticks = len(df_data)
        logger.info(f"Starting backtest simulation over {total_ticks} periods...")
        
        if total_ticks == 0:
            return {}

        start_price = float(df_data.iloc[0]["close"])
        final_price = float(df_data.iloc[-1]["close"])

        # 1. HODL Benchmark Calculation
        # Benchmark: convert entire initial portfolio into BTC on Day 1
        initial_value_usdt = self.initial_usdt + self.initial_core_btc * start_price
        hodl_btc_qty = initial_value_usdt / start_price

        # 2. Sequential simulation loop
        for index, row in df_data.iterrows():
            # Format tick dictionary
            # Datetime conversions
            time_val = pd.to_datetime(row["time"])
            ms_timestamp = int(time_val.timestamp() * 1000)

            tick = {
                "timestamp": ms_timestamp,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
                "funding_rate": float(row["funding_rate"]) if "funding_rate" in row else 0.0,
                "open_interest": float(row["open_interest"]) if "open_interest" in row else 0.0,
                "liquidations": float(row["liquidations"]) if "liquidations" in row else 0.0
            }

            # Seed database with the raw data so the feature engine can compute indices correctly
            self.orchestrator.save_raw_ohlcv_to_db(tick)

            # Skip actual live CCXT fetch, inject simulated tick into our mock engine
            # We mock the CCXT fetch methods on the orchestrator ingester to return this tick
            def fetch_mock():
                return tick
            self.orchestrator.ingester.fetch_latest_tick = fetch_mock

            # Run orchestrator tick
            self.orchestrator.run_tick()

        # 3. Calculate Final Performance & Tax Drag
        # Extract total realized P&L in USDT from database to compute tax liability
        total_realized_pnl_usdt = self._get_total_realized_pnl()
        tax_liability_usdt = max(0.0, total_realized_pnl_usdt * self.tax_rate)

        # Final portfolio evaluation
        final_usdt = self.orchestrator.ledger.reserve_usdt
        final_core_btc = self.orchestrator.ledger.core_btc_qty
        final_trading_btc = self.orchestrator.ledger.trading_btc_qty
        final_total_btc = final_core_btc + final_trading_btc

        # Pre-tax final total portfolio value in BTC terms
        # (Converting cash reserve to BTC at the final price)
        pre_tax_total_btc = final_total_btc + (final_usdt / final_price)

        # After-tax final total portfolio value in BTC terms
        # (Subtracting tax liability from reserve cash before converting to BTC)
        after_tax_usdt = final_usdt - tax_liability_usdt
        after_tax_total_btc = final_total_btc + (after_tax_usdt / final_price)

        # Yield calculations
        pre_tax_outperformance = pre_tax_total_btc - hodl_btc_qty
        after_tax_outperformance = after_tax_total_btc - hodl_btc_qty

        metrics = {
            "initial_portfolio_usdt": initial_value_usdt,
            "hodl_benchmark_btc": hodl_btc_qty,
            "final_usdt_cash": final_usdt,
            "final_core_btc": final_core_btc,
            "final_trading_btc": final_trading_btc,
            "pre_tax_total_btc": pre_tax_total_btc,
            "after_tax_total_btc": after_tax_total_btc,
            "total_realized_pnl_usdt": total_realized_pnl_usdt,
            "tax_liability_usdt": tax_liability_usdt,
            "pre_tax_outperformance_btc": pre_tax_outperformance,
            "after_tax_outperformance_btc": after_tax_outperformance,
            "pre_tax_pct_change": (pre_tax_total_btc / hodl_btc_qty - 1.0) * 100,
            "after_tax_pct_change": (after_tax_total_btc / hodl_btc_qty - 1.0) * 100
        }

        self._print_summary(metrics)
        return metrics

    def _get_total_realized_pnl(self) -> float:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COALESCE(SUM(realized_pnl), 0.0) FROM trade_history")
                return float(cur.fetchone()[0])
        except Exception:
            return 0.0
        finally:
            release_connection(conn)

    def _print_summary(self, metrics: Dict[str, Any]) -> None:
        print("\n" + "="*50)
        print("          ABAS v2 BACKTEST SUMMARY REPORT          ")
        print("="*50)
        print(f"Initial Value (USDT):           ${metrics['initial_portfolio_usdt']:.2f}")
        print(f"HODL Benchmark (BTC):           {metrics['hodl_benchmark_btc']:.6f} BTC")
        print(f"Final USDT Cash:                ${metrics['final_usdt_cash']:.2f}")
        print(f"Final Core BTC:                 {metrics['final_core_btc']:.6f} BTC")
        print(f"Final Trading BTC:              {metrics['final_trading_btc']:.6f} BTC")
        print(f"Total Realized P&L (USDT):      ${metrics['total_realized_pnl_usdt']:.2f}")
        print(f"Tax Liability (USDT):           ${metrics['tax_liability_usdt']:.2f}")
        print("-"*50)
        print(f"PRE-TAX Final Qty (BTC):        {metrics['pre_tax_total_btc']:.6f} BTC")
        print(f"PRE-TAX Outperformance (BTC):   {metrics['pre_tax_outperformance_btc']:.6f} BTC ({metrics['pre_tax_pct_change']:.2f}%)")
        print("-"*50)
        print(f"AFTER-TAX Final Qty (BTC):      {metrics['after_tax_total_btc']:.6f} BTC")
        print(f"AFTER-TAX Outperformance (BTC):  {metrics['after_tax_outperformance_btc']:.6f} BTC ({metrics['after_tax_pct_change']:.2f}%)")
        print("="*50 + "\n")
