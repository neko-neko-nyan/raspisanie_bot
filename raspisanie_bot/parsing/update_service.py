import asyncio
import logging

from async_utils import CancelableTimer
from . import TimetableUpdater, DatabaseFinder, UniversalHandler
from .. import config


class UpdateService:
    def __init__(self):
        self.LOG = logging.getLogger(type(self).__name__)
        self.updater = None
        self._stopping = False
        self._task = None
        self.timer = CancelableTimer()

    async def run(self):
        if self._stopping:
            raise RuntimeError("Cannot reuse UpdateService after stopping")

        self.updater = TimetableUpdater(DatabaseFinder, UniversalHandler)
        self.LOG.info("Starting first update...")
        force = True

        while not self._stopping:
            try:
                await self.updater.update_timetable(config.TIMETABLE_URL, force=force)
                await self.updater.process_pending()
            except asyncio.CancelledError:
                self._stopping = True
                break

            except Exception:
                self.LOG.exception("Update failed")
                delay = 30

            else:
                delay = config.UPDATE_INTERVAL

            if self._stopping:
                break

            self.LOG.info("Sleeping for %s seconds", delay)
            canceled = not await self.timer.sleep(delay)
            if self._stopping:
                break

            force = canceled
            if canceled:
                self.LOG.info("Starting force update", delay)
            else:
                self.LOG.info("Starting by timer")

        self.LOG.info("Stopping update service")
        await self.updater.close()

    def stop(self, cancel_current=False):
        self._stopping = True
        self.timer.cancel()
        if cancel_current and self._task is not None:
            self._task.cancel()

    def start(self):
        self._task = asyncio.get_event_loop().create_task(self.run(), name=type(self).__name__)
        return self._task
