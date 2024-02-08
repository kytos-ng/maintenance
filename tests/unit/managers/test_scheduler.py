"""Tests for the scheduler module."""

from unittest.mock import  MagicMock, call

from apscheduler.jobstores.base import JobLookupError
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
import pytz


from napps.kytos.maintenance.models import MaintenanceWindow as MW
from napps.kytos.maintenance.managers.scheduler import (
    MaintenanceScheduler as Scheduler,
    MaintenanceStart,
    MaintenanceEnd,
)

class TestScheduler:
    """Test of the Scheduler Class"""
    
    def setup_method(self) -> None:
        self.maintenance_deployer = MagicMock()
        self.db_controller = MagicMock()
        self.task_scheduler = MagicMock()
        
        self.now = datetime.now(pytz.utc)

        self.window = MW.construct(
            id = 'Test Window',
            description = '',
            start = self.now + timedelta(hours=1),
            end = self.now + timedelta(hours=2),
            status = 'pending',
            switches = [],
            interfaces = [],
            links = [],
            updated_at = self.now - timedelta(days=1),
            inserted_at = self.now - timedelta(days=1),
        )

        self.scheduler = Scheduler(self.maintenance_deployer, self.db_controller, self.task_scheduler)

    def test_start(self):

        pending_window = self.window.copy(
            update={'id': 'pending window', 'status': 'pending'}
        )
        running_window = self.window.copy(
            update={'id': 'running window', 'status': 'running'}
        )
        finished_window = self.window.copy(
            update={'id': 'finished window', 'status': 'finished'}
        )

        expected_schedule_calls = [
            call(MaintenanceStart(self.scheduler, 'pending window'),
            'date', id='pending window-start',
            run_date = pending_window.start),
            call(MaintenanceEnd(self.scheduler, 'running window'),
            'date', id='running window-end',
            run_date = running_window.end),
        ]

        self.db_controller.get_unfinished_windows.return_value = [
            pending_window,
            running_window,
            finished_window,
        ]
        self.scheduler.start()

        resultant_schedule_calls = self.task_scheduler.add_job.call_args_list
        assert resultant_schedule_calls == expected_schedule_calls

        self.maintenance_deployer.start_mw.assert_called_once_with(running_window)

    def test_shutdown(self):
        pending_window = self.window.copy(
            update={'id': 'pending window', 'status': 'pending'}
        )
        running_window = self.window.copy(
            update={'id': 'running window', 'status': 'running'}
        )
        finished_window = self.window.copy(
            update={'id': 'finished window', 'status': 'finished'}
        )

        self.db_controller.get_windows.return_value = [
            pending_window,
            running_window,
            finished_window,
        ]

        remove_job_effects = {
            'pending window-start': False,
            'pending window-end': True,
            'running window-start': True,
            'running window-end': False,
            'finished window-start': True,
            'finished window-end': True,
        }

        def side_effect(job_id):
            effect = remove_job_effects[job_id]
            if effect:
                raise JobLookupError(job_id)
            else:
                return None

        self.task_scheduler.remove_job.side_effect = side_effect

        self.scheduler.shutdown()

        self.maintenance_deployer.end_mw.assert_called_once_with(running_window)

    def test_update(self):
        pending_window = self.window.copy(
            update={'id': 'pending window', 'status': 'pending'}
        )
        running_window = self.window.copy(
            update={'id': 'running window', 'status': 'running'}
        )
        finished_window = self.window.copy(
            update={'id': 'finished window', 'status': 'finished'}
        )

        modify_job_effects = {
            'pending window-start': (False, DateTrigger(pending_window.start)),
            'pending window-end': (True, DateTrigger(pending_window.end)),
            'running window-start': (True, DateTrigger(running_window.start)),
            'running window-end': (False, DateTrigger(running_window.end)),
            'finished window-start': (True, DateTrigger(finished_window.start)),
            'finished window-end': (True, DateTrigger(finished_window.end)),
        }

        def side_effect(job_id, trigger):
            throw, expected_trigger = modify_job_effects[job_id]
            assert trigger.run_date == expected_trigger.run_date
            if throw:
                raise JobLookupError(job_id)
            else:
                return None
        
        self.task_scheduler.modify_job.side_effect = side_effect

        self.scheduler.update(pending_window)
        self.scheduler.update(running_window)
        self.scheduler.update(finished_window)

    def test_maintenance_start(self):

        pending_window = self.window.copy(
            update={'id': 'pending window', 'status': 'pending'}
        )
        next_window = self.window.copy(
            update={'id': 'pending window', 'status': 'running'}
        )

        self.db_controller.start_window.return_value = next_window
        start = MaintenanceStart(self.scheduler, pending_window.id)
        start()
        self.maintenance_deployer.start_mw.assert_called_once_with(next_window)

        self.task_scheduler.add_job.assert_called_once_with(
            MaintenanceEnd(self.scheduler, pending_window.id),
            'date',
            id='pending window-end',
            run_date=pending_window.end
        )

    def test_maintenance_end(self):

        running_window = self.window.copy(
            update={'id': 'running window', 'status': 'running'}
        )
        next_window = self.window.copy(
            update={'id': 'running window', 'status': 'finished'}
        )

        self.db_controller.end_window.return_value = next_window
        end = MaintenanceEnd(self.scheduler, running_window.id)
        end()
        self.maintenance_deployer.end_mw.assert_called_once_with(next_window)
