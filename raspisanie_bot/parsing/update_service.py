import asyncio
import logging

from async_utils import CancelableTimer
from .database import DatabaseFinder, UniversalHandler
from .parsers import TimetableUpdater
from .. import config


class UpdateService:
    def __init__(self):
        self.LOG = logging.getLogger(type(self).__name__)
        self.updater = None
        self._do_force_update = False
        self._task = None
        self.timer = CancelableTimer()

    async def run(self):
        self.updater = TimetableUpdater(DatabaseFinder, UniversalHandler)
        self.LOG.info("Starting first update...")
        force = True

        while True:
            try:
                await self.updater.update_timetable(config.TIMETABLE_URL, force=force)
                await self.updater.process_pending()
            except asyncio.CancelledError:
                break

            except Exception:
                self.LOG.exception("Update failed")
                delay = 30

            else:
                delay = config.UPDATE_INTERVAL

            if self._do_force_update:
                self._do_force_update = False
                self.LOG.info("Re-running force update")
                force = True
                continue

            self.LOG.info("Sleeping for %s seconds", delay)
            canceled = not await self.timer.sleep(delay)

            if canceled and not self._do_force_update:
                break

            self._do_force_update = False
            force = canceled
            if force:
                self.LOG.info("Starting force update", delay)
            else:
                self.LOG.info("Starting by timer")

        self.LOG.info("Stopping update service")
        await self.updater.close()

    def force_update(self):
        self._do_force_update = True
        if self._task is not None:
            self.timer.cancel()

    def stop(self, cancel_current=True):
        self.timer.cancel()
        if cancel_current and self._task is not None:
            self._task.cancel()

    def start(self):
        self._task = asyncio.get_event_loop().create_task(self.run(), name=type(self).__name__)
        return self._task
