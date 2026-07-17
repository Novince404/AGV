from __future__ import annotations

import asyncio
import signal

from app.core.lifecycle import initialize_runtime
from app.scheduler.coordinator import coordinator


async def main() -> None:
    initialize_runtime()
    stopped = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_name, stopped.set)
        except NotImplementedError:
            pass
    await coordinator.start()
    try:
        await stopped.wait()
    finally:
        await coordinator.stop()


if __name__ == "__main__":
    asyncio.run(main())
