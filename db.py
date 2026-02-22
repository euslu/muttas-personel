import os
import asyncpg

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            _pool = await asyncpg.create_pool(dsn=database_url)
        else:
            _pool = await asyncpg.create_pool(
                host=os.environ["DB_HOST"],
                port=int(os.environ["DB_PORT"]),
                database=os.environ["DB_NAME"],
                user=os.environ["DB_USER"],
                password=os.environ["DB_PASSWORD"],
            )
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
