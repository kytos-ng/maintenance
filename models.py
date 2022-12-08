"""Models used by the maintenance NApp.

This module define models for the maintenance window itself and the
scheduler.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import NewType
from uuid import uuid4

import pytz
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import BaseScheduler
from pydantic import BaseModel, Field

from kytos.core import KytosEvent, log
from kytos.core.controller import Controller


class Status(str, Enum):
    """Maintenance windows status."""

    PENDING = 'pending'
    RUNNING = 'running'
    FINISHED = 'finished'


MaintenanceID = NewType('MaintenanceID', str)


class MaintenanceWindow(BaseModel):
    """Class for structure of maintenance windows.
    """
    start: datetime
    end: datetime
    switches: list[str] = Field(default_factory = list)
    interfaces: list[str] = Field(default_factory = list)
    links: list[str] = Field(default_factory = list)
    id: MaintenanceID = Field(
        default_factory = lambda: MaintenanceID(uuid4().hex)
    )
    description: str = Field(default = '')
    status: Status = Field(default=Status.PENDING)

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
        return self.copy(update = {'status': Status.RUNNING})

    def end_mw(self, controller: Controller):
        """Actions taken when a maintenance window finishes."""
        self.maintenance_event('end', controller)
        return self.copy(update = {'status': Status.FINISHED})


@dataclass
class MaintenanceStart:
    """
    Callable used for starting maintenance windows
    """
    maintenance_scheduler: 'Scheduler'
    mw_id: MaintenanceID

    def __call__(self):
        self.maintenance_scheduler.start_maintenance(self.mw_id)


@dataclass
class MaintenanceEnd:
    """
    Callable used for ending maintenance windows
    """
    maintenance_scheduler: 'Scheduler'
    mw_id: MaintenanceID

    def __call__(self):
        self.maintenance_scheduler.end_maintenance(self.mw_id)


@dataclass
class Scheduler:
    """Scheduler for a maintenance window."""
    controller: Controller
    db: 'MaintenanceController'
    scheduler: BaseScheduler

    @classmethod
    def new_scheduler(cls, controller: Controller):
        """
        Creates a new scheduler from the given kytos controller
        """
        scheduler = BackgroundScheduler(timezone=pytz.utc)
        from napps.kytos.maintenance.controllers import MaintenanceController
        db = MaintenanceController()
        db.bootstrap_indexes()
        instance = cls(controller, db, scheduler)
        return instance

    def start(self):
        """
        Begin running the scheduler.
        """
        # Populate the scheduler with all pending tasks
        windows = self.db.get_windows()
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
        windows = self.db.get_windows()

        # Depopulate the scheduler
        for window in windows:
            self._unschedule(window)

    def start_maintenance(self, mw_id: MaintenanceID):
        """Begins executing the maintenance window
        """
        # Get Maintenance from DB
        window = self.db.get_window(mw_id)

        # Set to Running
        next_win = window.start_mw(self.controller)

        # Update DB
        self.db.update_window(next_win)

    def end_maintenance(self, mw_id: MaintenanceID):
        """Ends execution of the maintenance window
        """
        # Get Maintenance from DB
        window = self.db.get_window(mw_id)

        # Set to Ending
        next_win = window.end_mw(self.controller)

        # Update DB
        self.db.update_window(next_win)

    def end_maintenance_early(self, mw_id: MaintenanceID):
        """Ends execution of the maintenance window early
        """
        # Get Maintenance from DB
        window = self.db.get_window(mw_id)

        # Set to Ending
        next_win = self._unschedule(window)

        # Update DB
        self.db.update_window(next_win)

    def add(self, window: MaintenanceWindow):
        """Add jobs to start and end a maintenance window."""

        # Add window to DB
        self.db.add_window(window)

        # Schedule window
        self._schedule(window)

    def remove(self, mw_id: MaintenanceID):
        """Remove jobs that start and end a maintenance window."""
        # Get Maintenance from DB
        window = self.db.get_window(mw_id)

        # Remove from schedule
        self._unschedule(window)

        # Remove from DB
        self.db.remove_window(mw_id)

    def _schedule(self, window: MaintenanceWindow):
        if window.status is Status.PENDING:
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
        if window.status is Status.RUNNING:
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
        return self.db.get_window(mw_id)

    def list_maintenances(self):
        """Returns a list of all maintenances"""
        return self.db.get_windows()
