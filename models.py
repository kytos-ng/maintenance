"""Models used by the maintenance NApp.

This module define models for the maintenance window itself and the
scheduler.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import NewType, Optional
from uuid import uuid4

import pytz
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import BaseScheduler
from pydantic import BaseModel, Field, root_validator, validator

from kytos.core import KytosEvent, log
from kytos.core.controller import Controller

TIME_FMT = "%Y-%m-%dT%H:%M:%S%z"


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
    switches: list[str] = Field(default_factory=list)
    interfaces: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    id: MaintenanceID = Field(
        default_factory=lambda: MaintenanceID(uuid4().hex)
    )
    description: str = Field(default='')
    status: Status = Field(default=Status.PENDING)
    inserted_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    @validator('start', 'end', pre=True)
    def convert_time(cls, time):
        """Convert time strings using TIME_FMT"""
        if isinstance(time, str):
            time = datetime.strptime(time, TIME_FMT)
        return time

    @validator('start')
    def check_start_in_past(cls, start_time):
        """Check if the start is set to occur before now."""
        if start_time < datetime.now(pytz.utc):
            raise ValueError('Start in the past not allowed')
        return start_time

    @validator('end')
    def check_end_before_start(cls, end_time, values):
        """Check if the end is set to occur before the start."""
        if 'start' in values and end_time <= values['start']:
            raise ValueError('End before start not allowed')
        return end_time

    @root_validator
    def check_items_empty(cls, values):
        """Check if no items are in the maintenance window."""
        no_items = all(
            map(
                lambda key: key not in values or len(values[key]) == 0,
                ['switches', 'links', 'interfaces']
            )
        )
        if no_items:
            raise ValueError('At least one item must be provided')
        return values

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

    def end_mw(self, controller: Controller):
        """Actions taken when a maintenance window finishes."""
        self.maintenance_event('end', controller)

    def __str__(self) -> str:
        return f"'{self.id}'<{self.start} to {self.end}>"

    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime(TIME_FMT),
        }


class MaintenanceWindows(BaseModel):
    """List of Maintenance Windows for json conversion."""
    __root__: list[MaintenanceWindow]

    def __iter__(self):
        return iter(self.__root__)

    def __getitem__(self, item):
        return self.__root__[item]

    def __len__(self):
        return len(self.__root__)

    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime(TIME_FMT),
        }


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


class OverlapError(Exception):
    """
    Exception for when a Maintenance Windows execution
    period overlaps with one or more windows.
    """
    new_window: MaintenanceWindow
    interfering: MaintenanceWindows

    def __init__(
                self,
                new_window: MaintenanceWindow,
                interfering: MaintenanceWindows
            ):
        self.new_window = new_window
        self.interfering = interfering

    def __str__(self):
        return f"Maintenance Window {self.new_window} " +\
            "interferes with the following windows: " +\
            '[' +\
            ', '.join([
                f"{window}"
                for window in self.interfering
            ]) +\
            ']'


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
        self.db.prepare_start()

        # Populate the scheduler with all pending tasks
        windows = self.db.get_windows()
        for window in windows:
            if window.status == Status.PENDING:
                window.start_mw(self.controller)
            self._schedule(window)

        # Start the scheduler
        self.scheduler.start()

    def shutdown(self):
        """
        Stop running the scheduler.
        """
        windows = self.db.get_windows()

        # Depopulate the scheduler
        for window in windows:
            self._unschedule(window)

        self.scheduler.remove_all_jobs()
        self.scheduler.shutdown()

    def start_maintenance(self, mw_id: MaintenanceID):
        """Begins executing the maintenance window
        """
        # Get Maintenance from DB and Update
        window = self.db.start_window(mw_id)

        # Activate Running
        window.start_mw(self.controller)

        # Schedule next task
        self._schedule(window)

    def end_maintenance(self, mw_id: MaintenanceID):
        """Ends execution of the maintenance window
        """
        # Get Maintenance from DB
        window = self.db.end_window(mw_id)

        # Set to Ending
        window.end_mw(self.controller)

    def end_maintenance_early(self, mw_id: MaintenanceID):
        """Ends execution of the maintenance window early
        """
        # Get Maintenance from DB
        window = self.db.end_window(mw_id)

        # Unschedule tasks
        self._unschedule(window)

    def add(self, window: MaintenanceWindow, force=False):
        """Add jobs to start and end a maintenance window."""

        if force is False:
            overlapping_windows = self.db.check_overlap(window)
            if overlapping_windows:
                raise OverlapError(window, overlapping_windows)

        # Add window to DB
        self.db.insert_window(window)

        # Schedule next task
        self._schedule(window)

    def update(self, window: MaintenanceWindow):
        """Update an existing Maintenance Window."""

        # Update window
        self.db.update_window(window)

        # Reschedule any pending tasks
        self._reschedule(window)

    def remove(self, mw_id: MaintenanceID):
        """Remove jobs that start and end a maintenance window."""
        # Get Maintenance from DB
        window = self.db.get_window(mw_id)

        # Remove from schedule
        self._unschedule(window)

        # Remove from DB
        self.db.remove_window(mw_id)

    def _schedule(self, window: MaintenanceWindow):
        log.info(f'Scheduling "{window.id}"')
        if window.status == Status.PENDING:
            self.scheduler.add_job(
                MaintenanceStart(self, window.id),
                'date',
                id=f'{window.id}-start',
                run_date=window.start
            )
            log.info(f'Scheduled "{window.id}" start at {window.start}')
        if window.status == Status.RUNNING:
            self.scheduler.add_job(
                MaintenanceEnd(self, window.id),
                'date',
                id=f'{window.id}-end',
                run_date=window.end
            )
            log.info(f'Scheduled "{window.id}" end at {window.end}')

    def _reschedule(self, window: MaintenanceWindow):
        log.info(f'Rescheduling "{window.id}"')
        try:
            self.scheduler.remove_job(
                f'{window.id}-start',
            )
            self.scheduler.add_job(
                MaintenanceStart(self, window.id),
                'date',
                id=f'{window.id}-start',
                run_date=window.start
            )
            log.info(f'Rescheduled "{window.id}" start to {window.start}')
        except JobLookupError:
            log.info(f'Could not reschedule "{window.id}" start, no start job')
        try:
            self.scheduler.remove_job(
                f'{window.id}-end',
            )
            self.scheduler.add_job(
                MaintenanceEnd(self, window.id),
                'date',
                id=f'{window.id}-end',
                run_date=window.end
            )
            log.info(f'Rescheduled "{window.id}" end to {window.end}')
        except JobLookupError:
            log.info(f'Could not reschedule "{window.id}" end, no end job')

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
            log.info(f'Job to start "{window.id}" already removed.')
        try:
            self.scheduler.remove_job(f'{window.id}-end')
        except JobLookupError:
            ended = True
            log.info(f'Job to end "{window.id}" already removed.')
        if started and not ended:
            window.end_mw(self.controller)

    def get_maintenance(self, mw_id: MaintenanceID) -> MaintenanceWindow:
        """Get a single maintenance by id"""
        return self.db.get_window(mw_id)

    def list_maintenances(self) -> MaintenanceWindows:
        """Returns a list of all maintenances"""
        return self.db.get_windows()
