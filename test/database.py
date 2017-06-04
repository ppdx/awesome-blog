import asyncio
from pprint import pprint

import aioodbc

loop = asyncio.get_event_loop()


async def test_example():
    dsn = 'DRIVER={SQLite3 ODBC Driver};Database=../database/sqlite.db'

    async with aioodbc.create_pool(dsn=dsn, loop=loop) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT * FROM users;')
                val = await cur.fetchall()
                pprint(val)


loop.run_until_complete(test_example())
