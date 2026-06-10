import os
import pandas as pd
import numpy as np
import duckdb
from typing import Dict, Any, List
from src.backtest.harness import BacktestHarness
from src.backtest.benchmarks import (
    run_passive_hodl,
    run_weekly_dca,
    run_core_plus_weekly_dca,
    run_fixed_grid_backtest
)
from src.backtest.download_data import download_historical_data

def run_abas_backtest(
    df_data: pd.DataFrame,
    initial_usdt: float = 100000.0,
    initial_core_btc: float = 0.0,
    tax_rate: float = 0.20,
    maker_fee: float = 0.0002,
    taker_fee: float = 0.0010,
    slippage: float = 0.0005
) -> Dict[str, Any]:
    """
    Runs the backtest harness for the active ABAS v2 strategy.
    """
    harness = BacktestHarness(
        initial_usdt=initial_usdt,
        initial_core_btc=initial_core_btc,
        tax_rate=tax_rate,
        maker_fee=maker_fee,
        taker_fee=taker_fee,
        slippage=slippage
    )
    
    # Precompute features to mock database queries
    df_features = harness.orchestrator.features_engine.calculate_anchors_and_features(df_data)
    
    def mock_compute_latest_features(limit=500):
        conn = None
        try:
            from src.utils.db import get_connection, release_connection
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM binance_ohlcv")
                count = cur.fetchone()[0]
                if count == 0:
                    return None
                row_idx = min(count - 1, len(df_features) - 1)
                row = df_features.iloc[row_idx]
                return row.to_dict()
        except Exception:
            return None
        finally:
            if conn:
                release_connection(conn)
                
    harness.orchestrator.features_engine.compute_latest_features = mock_compute_latest_features
    
    results = harness.run(df_data)
    return results

def run_sensitivity_analysis(
    df_data: pd.DataFrame,
    initial_usdt: float = 100000.0,
    initial_core_btc: float = 0.0
) -> List[Dict[str, Any]]:
    """
    Sweeps fees, slippage, and tax parameters to test strategy robustness.
    """
    fees_options = [0.0005, 0.0010, 0.0015]  # Taker fees (maker assumes 1/5th)
    slippage_options = [0.0002, 0.0005, 0.0010]
    tax_options = [0.0, 0.20, 0.35]
    
    sweep_results = []
    
    print("\nRunning Sensitivity Sweep...")
    for fee in fees_options:
        for slip in slippage_options:
            for tax in tax_options:
                maker_f = fee * 0.20
                res = run_abas_backtest(
                    df_data=df_data,
                    initial_usdt=initial_usdt,
                    initial_core_btc=initial_core_btc,
                    tax_rate=tax,
                    maker_fee=maker_f,
                    taker_fee=fee,
                    slippage=slip
                )
                sweep_results.append({
                    "taker_fee": fee,
                    "slippage": slip,
                    "tax_rate": tax,
                    "pre_tax_total_btc": res["pre_tax_total_btc"],
                    "after_tax_total_btc": res["after_tax_total_btc"],
                    "outperformance_btc": res["after_tax_outperformance_btc"]
                })
    return sweep_results

def generate_report(
    df_data: pd.DataFrame,
    abas_res: Dict[str, Any],
    hodl_btc: float,
    dca_btc: float,
    core_dca_btc: float,
    fixed_grid_res: Dict[str, Any],
    sweep_results: List[Dict[str, Any]],
    output_report_path: str = "artifacts/backtest_report.md"
):
    """
    Generates a formatted markdown report.
    """
    os.makedirs(os.path.dirname(output_report_path), exist_ok=True)
    
    total_days = len(df_data) / 24.0
    start_time = df_data.iloc[0]["time"]
    end_time = df_data.iloc[-1]["time"]
    
    hodl_perf = (abas_res["after_tax_total_btc"] - hodl_btc) / hodl_btc * 100
    dca_perf = (abas_res["after_tax_total_btc"] - dca_btc) / dca_btc * 100
    fixed_grid_perf = (abas_res["after_tax_total_btc"] - fixed_grid_res["after_tax_total_btc"]) / fixed_grid_res["after_tax_total_btc"] * 100
    
    report_content = f"""# ABAS v2 Backtest & Performance Report

- **Backtest Period**: {start_time} to {end_time} ({total_days:.1f} days)
- **Initial Portfolio**: ${abas_res['initial_portfolio_usdt']:.2f}

## Headline Performance Comparison

| Strategy | Final BTC Quantity | Outperformance vs HODL (%) |
|---|---|---|
| **ABAS v2 (Adaptive, After-Tax)** | **{abas_res['after_tax_total_btc']:.6f} BTC** | **{hodl_perf:+.2f}%** |
| Passive HODL (Benchmark) | {hodl_btc:.6f} BTC | 0.00% |
| Weekly DCA | {dca_btc:.6f} BTC | {((dca_btc - hodl_btc)/hodl_btc * 100):+.2f}% |
| Core + Weekly DCA | {core_dca_btc:.6f} BTC | {((core_dca_btc - hodl_btc)/hodl_btc * 100):+.2f}% |
| Fixed 5% Grid (After-Tax) | {fixed_grid_res['after_tax_total_btc']:.6f} BTC | {((fixed_grid_res['after_tax_total_btc'] - hodl_btc)/hodl_btc * 100):+.2f}% |

## Active Strategy Detailed Metrics (ABAS v2)

- **Total Realized P&L**: ${abas_res['total_realized_pnl_usdt']:.2f}
- **Accrued Tax Liability**: ${abas_res['tax_liability_usdt']:.2f}
- **Final Reserve Cash**: ${abas_res['final_usdt_cash']:.2f}
- **Final Core Cold Storage BTC**: {abas_res['final_core_btc']:.6f} BTC
- **Final Exchange Trading BTC**: {abas_res['final_trading_btc']:.6f} BTC
- **Pre-Tax Final Total BTC**: {abas_res['pre_tax_total_btc']:.6f} BTC (Outperformance: {abas_res['pre_tax_pct_change']:+.2f}%)

## Parameter Sensitivity Sweep (ABAS v2 After-Tax)

| Taker Fee (%) | Slippage (%) | Tax Rate (%) | Final BTC Qty | Outperformance (BTC) |
|---|---|---|---|---|
"""
    
    for r in sweep_results:
        report_content += f"| {r['taker_fee']*100:.2f}% | {r['slippage']*100:.3f}% | {r['tax_rate']*100:.1f}% | {r['after_tax_total_btc']:.6f} | {r['outperformance_btc']:+.6f} |\n"
        
    with open(output_report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"Backtest report successfully generated at {output_report_path}")

def main():
    data_path = "data/btc_1h_binance.parquet"
    if not os.path.exists(data_path):
        print(f"Data file {data_path} not found. Downloading recent 6 months of data...")
        import datetime
        end_dt = datetime.datetime.now(datetime.timezone.utc)
        start_dt = end_dt - datetime.timedelta(days=180)
        download_historical_data(
            symbol="BTC/USDT",
            timeframe="1h",
            start_str=start_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
            end_str=end_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
            output_path=data_path
        )
        
    # Read Parquet using DuckDB
    print(f"Querying {data_path} via DuckDB...")
    duckdb_conn = duckdb.connect()
    df_data = duckdb_conn.execute(f"SELECT * FROM '{data_path}'").df()
    print(f"Loaded {len(df_data)} hourly records.")
    
    # Run strategies
    print("\nRunning Active ABAS v2 Strategy...")
    abas_res = run_abas_backtest(df_data)
    
    print("\nRunning Benchmark Strategies...")
    initial_usdt = abas_res["initial_portfolio_usdt"]
    initial_core_btc = 0.0
    
    hodl_btc = run_passive_hodl(df_data, initial_usdt, initial_core_btc)
    dca_btc = run_weekly_dca(df_data, initial_usdt, initial_core_btc)
    core_dca_btc = run_core_plus_weekly_dca(df_data, initial_usdt, initial_core_btc)
    
    print("\nRunning Fixed 5% Grid Strategy...")
    fixed_grid_res = run_fixed_grid_backtest(df_data)
    
    # Run sweep
    sweep_results = run_sensitivity_analysis(df_data)
    
    # Generate Report
    generate_report(df_data, abas_res, hodl_btc, dca_btc, core_dca_btc, fixed_grid_res, sweep_results)

if __name__ == "__main__":
    main()
