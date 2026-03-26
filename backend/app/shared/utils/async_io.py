import asyncio
from typing import Any, Callable

import nest_asyncio

nest_asyncio.apply()


async def run_async(func: Callable[..., Any]):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, func)


def run_concurrently(*coros_or_futures):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(asyncio.gather(*coros_or_futures, return_exceptions=True))
