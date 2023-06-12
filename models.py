"""Models used by the maintenance NApp.

This module define models for the maintenance window itself and the
scheduler.
"""
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from itertools import chain
from typing import NewType, Optional
from uuid import uuid4

import pytz
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import BaseScheduler
# pylint: disable=no-name-in-module
from pydantic import BaseModel, Field, root_validator, validator

# pylint: enable=no-name-in-module
from kytos.core import KytosEvent, log
from kytos.core.common import EntityStatus
from kytos.core.controller import Controller
from kytos.core.interface import Interface
from kytos.core.link import Link
from kytos.core.switch import Switch

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

    # pylint: disable=no-self-argument

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

    # pylint: enable=no-self-argument

    def __str__(self) -> str:
        return f"'{self.id}'<{self.start} to {self.end}>"

    class Config:
        """Config for encoding MaintenanceWindow class"""
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
        """Config for encoding MaintenanceWindows class"""
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
class MaintenanceDeployer:
    """Class for deploying maintenances"""
    controller: Controller
    maintenance_switches: Counter
    maintenance_interfaces: Counter
    maintenance_links: Counter

    @classmethod
    def new_deployer(cls, controller: Controller):
        """
        Creates a new MaintenanceDeployer from the given Kytos Controller
        """
        instance = cls(controller, Counter(), Counter(), Counter())
        Switch.register_status_func(
            'maintenance_status',
            instance.switch_status_func
        )
        Switch.register_status_reason_func(
            'maintenance_status',
            instance.switch_status_reason_func
        )
        Interface.register_status_func(
            'maintenance_status',
            instance.interface_status_func
        )
        Interface.register_status_reason_func(
            'maintenance_status',
            instance.interface_status_reason_func
        )
        Link.register_status_func(
            'maintenance_status',
            instance.link_status_func
        )
        Link.register_status_reason_func(
            'maintenance_status',
            instance.link_status_reason_func
        )

        return instance

    def _maintenance_event(self, window_devices: dict, operation: str):
        """Create events to start/end a maintenance."""
        event = KytosEvent(
            f'kytos/topology.interruption.{operation}',
            content={
                'type': 'maintenance',
                **window_devices
            }
        )
        self.controller.buffers.app.put(event)

    def _get_affected_ids(
        self,
        window: MaintenanceWindow
    ) -> dict[str, list[str]]:
        explicit_switches = filter(
            lambda switch: switch is not None,
            map(
                self.controller.switches.get,
                window.switches
            )
        )

        tot_switches = list(explicit_switches)

        implicit_interfaces = chain.from_iterable(
            map(
                lambda switch: switch.interfaces.values(),
                tot_switches
            )
        )

        explicit_interfaces = filter(
            lambda interface: interface is not None,
            map(
                self.controller.get_interface_by_id,
                window.interfaces
            )
        )

        tot_interfaces = list(chain(implicit_interfaces, explicit_interfaces))

        implicit_links = filter(
            lambda link: link is not None,
            map(
                lambda interface: interface.link,
                tot_interfaces
            )
        )

        explicit_links = filter(
            lambda link: link is not None,
            map(
                self.controller.napps[('kytos', 'topology')].links.get,
                window.links
            )
        )

        tot_links = list(chain(implicit_links, explicit_links))

        affected_switch_ids = list(set(map(
            lambda switch: switch.id,
            filter(
                self.switch_not_in_maintenance,
                tot_switches
            )
        )))

        affected_interface_ids = list(set(map(
            lambda interface: interface.id,
            filter(
                self.interface_not_in_maintenance,
                tot_interfaces
            )
        )))

        affected_link_ids = list(set(map(
            lambda link: link.id,
            filter(
                self.link_not_in_maintenance,
                tot_links
            )
        )))

        return {
            'switches': affected_switch_ids,
            'interfaces': affected_interface_ids,
            'links': affected_link_ids,
        }

    def start_mw(self, window: MaintenanceWindow):
        """Actions taken when a maintenance window starts."""
        affected_ids = self._get_affected_ids(window)

        self.maintenance_switches.update(window.switches)
        self.maintenance_interfaces.update(window.interfaces)
        self.maintenance_links.update(window.links)

        self._maintenance_event(
            affected_ids,
            'start'
        )

    def end_mw(self, window: MaintenanceWindow):
        """Actions taken when a maintenance window finishes."""

        self.maintenance_switches.subtract(window.switches)
        self.maintenance_interfaces.subtract(window.interfaces)
        self.maintenance_links.subtract(window.links)

        affected_ids = self._get_affected_ids(window)

        self._maintenance_event(
            affected_ids,
            'end'
        )

    def switch_not_in_maintenance(self, dev: Switch):
        """Checks if a switch is not undergoing maintenance"""
        return not self.maintenance_switches[dev.id]

    def interface_not_in_maintenance(self, dev: Interface):
        """Checks if a interface is not undergoing maintenance"""
        return (
            not self.maintenance_interfaces[dev.id] and
            self.switch_not_in_maintenance(dev.switch)
        )

    def link_not_in_maintenance(self, dev: Link):
        """Checks if a link is not undergoing maintenance"""
        return (
            not self.maintenance_links[dev.id] and
            all(
                map(
                    self.interface_not_in_maintenance,
                    (dev.endpoint_a, dev.endpoint_b)
                )
            )
        )

    def switch_status_func(self, dev: Switch):
        """Checks if a given device is undergoing maintenance"""
        if self.switch_not_in_maintenance(dev):
            return EntityStatus.UP
        return EntityStatus.DOWN

    def switch_status_reason_func(self, dev: Switch):
        """Checks if a given device is undergoing maintenance"""
        if self.switch_not_in_maintenance(dev):
            return frozenset()
        return frozenset({'maintenance'})

    def interface_status_func(self, dev: Interface):
        """Checks if a given device is undergoing maintenance"""
        if self.interface_not_in_maintenance(dev):
            return EntityStatus.UP
        return EntityStatus.DOWN

    def interface_status_reason_func(self, dev: Interface):
        """Checks if a given device is undergoing maintenance"""
        if self.interface_not_in_maintenance(dev):
            return frozenset()
        return frozenset({'maintenance'})

    def link_status_func(self, dev: Link):
        """Checks if a given device is undergoing maintenance"""
        if self.link_not_in_maintenance(dev):
            return EntityStatus.UP
        return EntityStatus.DOWN

    def link_status_reason_func(self, dev: Link):
        """Checks if a given device is undergoing maintenance"""
        if self.link_not_in_maintenance(dev):
            return frozenset()
        return frozenset({'maintenance'})


@dataclass
class Scheduler:
    """Class for scheduling maintenance windows."""
    deployer: MaintenanceDeployer
    db_controller: 'MaintenanceController'
    scheduler: BaseScheduler

    @classmethod
    def new_scheduler(cls, deployer: MaintenanceDeployer):
        """
        Creates a new scheduler from the given MaintenanceDeployer
        """
        scheduler = BackgroundScheduler(timezone=pytz.utc)
        # pylint: disable=import-outside-toplevel
        from napps.kytos.maintenance.controllers import MaintenanceController

        # pylint: enable=import-outside-toplevel
        db_controller = MaintenanceController()
        db_controller.bootstrap_indexes()
        instance = cls(deployer, db_controller, scheduler)
        return instance

    def start(self):
        """
        Begin running the scheduler.
        """
        self.db_controller.prepare_start()

        # Populate the scheduler with all pending tasks
        windows = self.db_controller.get_windows()
        for window in windows:
            if window.status == Status.RUNNING:
                self.deployer.start_mw(window)
            self._schedule(window)

        # Start the scheduler
        self.scheduler.start()

    def shutdown(self):
        """
        Stop running the scheduler.
        """
        windows = self.db_controller.get_windows()

        # Depopulate the scheduler
        for window in windows:
            self._unschedule(window)

        self.scheduler.remove_all_jobs()
        self.scheduler.shutdown()

    def start_maintenance(self, mw_id: MaintenanceID):
        """Begins executing the maintenance window
        """
        # Get Maintenance from DB and Update
        window = self.db_controller.start_window(mw_id)

        # Activate Running
        self.deployer.start_mw(window)

        # Schedule next task
        self._schedule(window)

    def end_maintenance(self, mw_id: MaintenanceID):
        """Ends execution of the maintenance window
        """
        # Get Maintenance from DB
        window = self.db_controller.end_window(mw_id)

        # Set to Ending
        self.deployer.end_mw(window)

    def end_maintenance_early(self, mw_id: MaintenanceID):
        """Ends execution of the maintenance window early
        """
        # Get Maintenance from DB
        window = self.db_controller.end_window(mw_id)

        # Unschedule tasks
        self._unschedule(window)

    def add(self, window: MaintenanceWindow, force=False):
        """Add jobs to start and end a maintenance window."""

        if force is False:
            overlapping_windows = self.db_controller.check_overlap(window)
            if overlapping_windows:
                raise OverlapError(window, overlapping_windows)

        # Add window to DB
        self.db_controller.insert_window(window)

        # Schedule next task
        self._schedule(window)

    def update(self, window: MaintenanceWindow):
        """Update an existing Maintenance Window."""

        # Update window
        self.db_controller.update_window(window)

        # Reschedule any pending tasks
        self._reschedule(window)

    def remove(self, mw_id: MaintenanceID):
        """Remove jobs that start and end a maintenance window."""
        # Get Maintenance from DB
        window = self.db_controller.get_window(mw_id)

        # Remove from schedule
        self._unschedule(window)

        # Remove from DB
        self.db_controller.remove_window(mw_id)

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
            self.deployer.end_mw(window)

    def get_maintenance(self, mw_id: MaintenanceID) -> MaintenanceWindow:
        """Get a single maintenance by id"""
        return self.db_controller.get_window(mw_id)

    def list_maintenances(self) -> MaintenanceWindows:
        """Returns a list of all maintenances"""
        return self.db_controller.get_windows()
