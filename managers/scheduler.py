"""Module for handling the scheduled execution of maintenance windows."""
import pytz
from dataclasses import dataclass

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import BaseScheduler


from .deployer import MaintenanceDeployer
from ..controllers import MaintenanceController
from ..models import (
    MaintenanceID,
    MaintenanceWindow,
    MaintenanceWindows,
    OverlapError,
    Status,
)

from kytos.core import log

@dataclass
class MaintenanceStart:
    """
    Callable used for starting maintenance windows
    """
    maintenance_scheduler: 'MaintenanceScheduler'
    mw_id: MaintenanceID

    def __call__(self):
        self.maintenance_scheduler.start_maintenance(self.mw_id)


@dataclass
class MaintenanceEnd:
    """
    Callable used for ending maintenance windows
    """
    maintenance_scheduler: 'MaintenanceScheduler'
    mw_id: MaintenanceID

    def __call__(self):
        self.maintenance_scheduler.end_maintenance(self.mw_id)

@dataclass
class MaintenanceScheduler:
    """Class for scheduling maintenance windows."""
    deployer: MaintenanceDeployer
    db_controller: MaintenanceController
    scheduler: BaseScheduler

    @classmethod
    def new_scheduler(cls, deployer: MaintenanceDeployer):
        """
        Creates a new scheduler from the given MaintenanceDeployer
        """
        scheduler = BackgroundScheduler(timezone=pytz.utc)
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
        windows = self.db_controller.get_unfinished_windows()
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
