import logging
import psycopg2
from src.config import settings

logger = logging.getLogger("init_db")

def init_db():
    conn = None
    try:
        logger.info(f"Connecting to database: {settings.db_url}")
        conn = psycopg2.connect(settings.db_url)
        conn.autocommit = True
        with conn.cursor() as cur:
            # Enable timescaledb
            cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
            
            # 1. binance_ohlcv
            cur.execute("""
            CREATE TABLE IF NOT EXISTS binance_ohlcv (
                time TIMESTAMPTZ NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                open DOUBLE PRECISION NOT NULL,
                high DOUBLE PRECISION NOT NULL,
                low DOUBLE PRECISION NOT NULL,
                close DOUBLE PRECISION NOT NULL,
                volume DOUBLE PRECISION NOT NULL
            );
            """)
            try:
                cur.execute("SELECT create_hypertable('binance_ohlcv', 'time', if_not_exists => TRUE);")
            except Exception as e:
                logger.warning(f"Failed to create hypertable for binance_ohlcv: {e}")

            # 2. binance_funding_rates
            cur.execute("""
            CREATE TABLE IF NOT EXISTS binance_funding_rates (
                time TIMESTAMPTZ NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                funding_rate DOUBLE PRECISION NOT NULL
            );
            """)
            try:
                cur.execute("SELECT create_hypertable('binance_funding_rates', 'time', if_not_exists => TRUE);")
            except Exception as e:
                logger.warning(f"Failed to create hypertable for binance_funding_rates: {e}")

            # 3. binance_open_interest
            cur.execute("""
            CREATE TABLE IF NOT EXISTS binance_open_interest (
                time TIMESTAMPTZ NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                open_interest DOUBLE PRECISION NOT NULL
            );
            """)
            try:
                cur.execute("SELECT create_hypertable('binance_open_interest', 'time', if_not_exists => TRUE);")
            except Exception as e:
                logger.warning(f"Failed to create hypertable for binance_open_interest: {e}")

            # 4. binance_liquidations
            cur.execute("""
            CREATE TABLE IF NOT EXISTS binance_liquidations (
                time TIMESTAMPTZ NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                side VARCHAR(10) NOT NULL,
                qty DOUBLE PRECISION NOT NULL,
                price DOUBLE PRECISION NOT NULL
            );
            """)
            try:
                cur.execute("SELECT create_hypertable('binance_liquidations', 'time', if_not_exists => TRUE);")
            except Exception as e:
                logger.warning(f"Failed to create hypertable for binance_liquidations: {e}")

            # 5. portfolio_states
            cur.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_states (
                time TIMESTAMPTZ NOT NULL,
                core_btc_qty DOUBLE PRECISION NOT NULL,
                trading_btc_qty DOUBLE PRECISION NOT NULL,
                reserve_usdt DOUBLE PRECISION NOT NULL,
                total_portfolio_val_usdt DOUBLE PRECISION NOT NULL,
                active_regime INTEGER NOT NULL,
                regime_confidence DOUBLE PRECISION NOT NULL
            );
            """)
            try:
                cur.execute("SELECT create_hypertable('portfolio_states', 'time', if_not_exists => TRUE);")
            except Exception as e:
                logger.warning(f"Failed to create hypertable for portfolio_states: {e}")

            # 6. trade_history
            cur.execute("""
            CREATE TABLE IF NOT EXISTS trade_history (
                time TIMESTAMPTZ NOT NULL,
                order_id VARCHAR(50) NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                side VARCHAR(10) NOT NULL,
                price DOUBLE PRECISION NOT NULL,
                qty DOUBLE PRECISION NOT NULL,
                fees DOUBLE PRECISION NOT NULL,
                slippage DOUBLE PRECISION NOT NULL,
                realized_pnl DOUBLE PRECISION NOT NULL
            );
            """)
            try:
                cur.execute("SELECT create_hypertable('trade_history', 'time', if_not_exists => TRUE);")
            except Exception as e:
                logger.warning(f"Failed to create hypertable for trade_history: {e}")

            # 7. trade_lots (FIFO tracking, relational)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS trade_lots (
                id SERIAL PRIMARY KEY,
                qty DOUBLE PRECISION NOT NULL,
                purchase_price DOUBLE PRECISION NOT NULL,
                purchase_time TIMESTAMPTZ NOT NULL,
                regime_tag VARCHAR(50) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'active'
            );
            """)

            # 8. tax_records (FIFO consumption matching for tax reporting)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS tax_records (
                id SERIAL PRIMARY KEY,
                sell_time TIMESTAMPTZ NOT NULL,
                sell_price DOUBLE PRECISION NOT NULL,
                sell_qty DOUBLE PRECISION NOT NULL,
                lot_purchase_time TIMESTAMPTZ NOT NULL,
                lot_purchase_price DOUBLE PRECISION NOT NULL,
                realized_pnl_usd DOUBLE PRECISION NOT NULL,
                holding_period_days INTEGER NOT NULL,
                order_id VARCHAR(50) NOT NULL
            );
            """)

            logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database schema: {e}")
        raise e
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    from src.utils.logging import setup_logging
    setup_logging()
    init_db()
