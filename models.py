"""Models used by the maintenance NApp.

This module define models for the maintenance window itself and the
scheduler.
"""
from datetime import datetime
from enum import Enum
from typing import NewType
from uuid import uuid4

import pytz
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import BaseScheduler
from attrs import define, evolve, field
from bson.codec_options import CodecOptions
from cattrs import Converter
from pymongo import MongoClient
from pymongo.collection import Collection

from kytos.core import KytosEvent, log
from kytos.core.controller import Controller

TIME_FMT = "%Y-%m-%dT%H:%M:%S%z"

converter = Converter()
converter.register_structure_hook(datetime, lambda ts, cl: ts)


class Status(str, Enum):
    """Maintenance windows status."""

    PENDING = 'pending'
    RUNNING = 'running'
    FINISHED = 'finished'


MaintenanceID = NewType('MaintenanceID', str)


@define(frozen=True)
class MaintenanceWindow:
    """Class for structure of maintenance windows.
    """
    start: datetime
    end: datetime
    switches: list[str] = field(factory = list)
    interfaces: list[str] = field(factory = list)
    links: list[str] = field(factory = list)
    id: MaintenanceID = field(factory = lambda: MaintenanceID(uuid4().hex))
    description: str = field(default='')
    status: Status = field(default=Status.PENDING)

    def maintenance_event(self, operation, controller: Controller):
        """Create events to start/end a maintenance."""
        if self.switches:
            event = KytosEvent(
                name=f'kytos/maintenance.{operation}_switch',
                content={'switches': self.switches}
            )
            controller.buffers.app.put(event)
        if self.interfaces:
            event = KytosEvent(
                name=f'kytos/maintenance.{operation}_interface',
                content={'unis': self.interfaces}
            )
            controller.buffers.app.put(event)
        if self.links:
            event = KytosEvent(
                name=f'kytos/maintenance.{operation}_link',
                content={'links': self.links}
            )
            controller.buffers.app.put(event)

    def start_mw(self, controller: Controller):
        """Actions taken when a maintenance window starts."""
        self.maintenance_event('start', controller)
        return evolve(self, status=Status.RUNNING)

    def end_mw(self, controller: Controller):
        """Actions taken when a maintenance window finishes."""
        self.maintenance_event('end', controller)
        return evolve(self, status=Status.FINISHED)


@define
class MaintenanceStart:
    """
    Callable used for starting maintenance windows
    """
    maintenance_scheduler: 'Scheduler'
    id: MaintenanceID

    def __call__(self):
        self.maintenance_scheduler.start_maintenance(self.id)


@define
class MaintenanceEnd:
    """
    Callable used for ending maintenance windows
    """
    maintenance_scheduler: 'Scheduler'
    id: MaintenanceID

    def __call__(self):
        self.maintenance_scheduler.end_maintenance(self.id)


@define
class Scheduler:
    """Scheduler for a maintenance window."""
    controller: Controller
    db_client: MongoClient
    windows: Collection
    scheduler: BaseScheduler

    @classmethod
    def new_scheduler(cls, controller: Controller):
        """
        Creates a new scheduler from the given kytos controller
        """
        db_client = controller.db_client
        database = controller.db
        scheduler = BackgroundScheduler(timezone=pytz.utc)
        windows = database['maintenance.windows'].with_options(
            codec_options=CodecOptions(
                tz_aware=True,
            )
        )
        windows.create_index('id')
        instance = cls(controller, db_client, windows, scheduler)
        return instance

    def start(self):
        """
        Begin running the scheduler.
        """
        # Populate the scheduler with all pending tasks
        windows = self._db_list_windows()
        for window in windows:
            self._schedule(window)

        # Start the scheduler
        self.scheduler.start()

    def shutdown(self):
        """
        Stop running the scheduler.
        """
        self.scheduler.remove_all_jobs()
        self.scheduler.shutdown()
        windows = self._db_list_windows()

        # Depopulate the scheduler
        for window in windows:
            self._unschedule(window)

    def start_maintenance(self, mw_id: MaintenanceID):
        """Begins executing the maintenance window
        """
        # Get Maintenance from DB
        window = self._db_get_window(mw_id)

        # Set to Running
        next_win = window.start_mw(self.controller)

        # Update DB
        self._db_update_window(next_win)

    def end_maintenance(self, mw_id: MaintenanceID):
        """Ends execution of the maintenance window
        """
        # Get Maintenance from DB
        window = self._db_get_window(mw_id)

        # Set to Ending
        next_win = window.end_mw(self.controller)

        # Update DB
        self._db_update_window(next_win)

    def end_maintenance_early(self, mw_id: MaintenanceID):
        """Ends execution of the maintenance window early
        """
        # Get Maintenance from DB
        window = self._db_get_window(mw_id)

        # Set to Ending
        next_win = self._unschedule(window)

        # Update DB
        self._db_update_window(next_win)

    def add(self, window: MaintenanceWindow):
        """Add jobs to start and end a maintenance window."""

        # Add window to DB
        self.windows.insert_one(converter.unstructure(window))

        # Schedule window
        self._schedule(window)

    def remove(self, mw_id: MaintenanceID):
        """Remove jobs that start and end a maintenance window."""
        # Get Maintenance from DB
        window = self._db_get_window(mw_id)

        # Remove from schedule
        self._unschedule(window)

        # Remove from DB
        self.windows.delete_one({'id': mw_id})

    def _db_get_window(self, mw_id: MaintenanceID):
        window = self.windows.find_one(
            {'id': mw_id},
            projection = {'_id': False}
        )
        if window is not None:
            window: MaintenanceWindow = converter.structure(
                window,
                MaintenanceWindow
            )
        return window

    def _db_update_window(self, window: MaintenanceWindow):
        self.windows.update_one(
            {'id': window.id},
            {'$set': converter.unstructure(window)}
        )

    def _db_list_windows(self) -> list[MaintenanceWindow]:
        windows = self.windows.find(projection={'_id': False})
        return list(
            map(
                lambda win: converter.structure(win, MaintenanceWindow),
                windows
            )
        )

    def _schedule(self, window: MaintenanceWindow):
        match window:
            case MaintenanceWindow(status=Status.PENDING):
                self.scheduler.add_job(
                    MaintenanceStart(self, window.id),
                    'date',
                    id=f'{window.id}-start',
                    run_date=window.start
                )
                self.scheduler.add_job(
                    MaintenanceEnd(self, window.id),
                    'date',
                    id=f'{window.id}-end',
                    run_date=window.end
                )
            case MaintenanceWindow(status=Status.RUNNING):
                window.start_mw(self.controller)
                self.scheduler.add_job(
                    MaintenanceEnd(self, window.id),
                    'date',
                    id=f'{window.id}-end',
                    run_date=window.end
                )

    def _unschedule(self, window: MaintenanceWindow):
        """Remove maintenance events from scheduler.
        Does not update DB, due to being
        primarily for shutdown startup cases.
        """
        started = False
        ended = False
        try:
            self.scheduler.remove_job(f'{window.id}-start')
        except JobLookupError:
            started = True
            log.info(f'Job to start {window.id} already removed.')
        try:
            self.scheduler.remove_job(f'{window.id}-end')
        except JobLookupError:
            ended = True
            log.info(f'Job to end {window.id} already removed.')
        if started and not ended:
            window = window.end_mw(self.controller)
        return window

    def get_maintenance(self, mw_id: MaintenanceID):
        """Get a single maintenance by id"""
        return self._db_get_window(mw_id)

    def list_maintenances(self):
        """Returns a list of all maintenances"""
        return self._db_list_windows()
