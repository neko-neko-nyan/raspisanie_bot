import asyncio


class CancelableTimer:
    def __init__(self):
        self._futures = set()

    @staticmethod
    def _set_result_unless_cancelled(fut):
        if not fut.cancelled():
            fut.set_result(None)

    async def sleep(self, delay: float) -> bool:
        """
        Coroutine that completes after a given time (in seconds).
        May be canceled from another coroutine by calling `cancel()`.
        Returns false if sleeping was canceled, true elsewhere.
        :param delay: Delay time in seconds
        :return: false if sleeping was canceled, true elsewhere
        """
        if delay <= 0:
            await asyncio.sleep(0)
            return True

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        h = loop.call_later(delay, self._set_result_unless_cancelled, future)
        self._futures.add(future)

        try:
            await future
            return True

        except asyncio.CancelledError:
            return False

        finally:
            h.cancel()
            self._futures.remove(future)

    def cancel(self):
        """
        Cancel all `sleep()` coroutines on this object.
        """
        for future in self._futures:
            future.cancel()
