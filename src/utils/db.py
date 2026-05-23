import logging
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from src.config import settings

logger = logging.getLogger("db_pool")
_pool = None

def get_db_pool() -> SimpleConnectionPool:
    global _pool
    if _pool is None:
        try:
            logger.info("Initializing TimescaleDB connection pool...")
            _pool = SimpleConnectionPool(
                minconn=1,
                maxconn=20,
                dsn=settings.db_url
            )
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise e
    return _pool

def get_connection():
    """
    Retrieves a connection from the pool.
    """
    return get_db_pool().getconn()

def release_connection(conn):
    """
    Returns a connection to the pool.
    """
    if conn:
        get_db_pool().putconn(conn)
