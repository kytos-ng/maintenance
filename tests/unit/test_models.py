"""Tests for the models module."""

from unittest import TestCase
from unittest.mock import patch, MagicMock, call

from collections import Counter

from apscheduler.jobstores.base import JobLookupError
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
import pytz
from kytos.lib.helpers import get_controller_mock
from napps.kytos.maintenance.models import MaintenanceDeployer
from napps.kytos.maintenance.models import MaintenanceWindow as MW, Status, Scheduler
from napps.kytos.maintenance.models import MaintenanceStart, MaintenanceEnd
TIME_FMT = "%Y-%m-%dT%H:%M:%S%z"


class TestMW(TestCase):
    """Test of the MaintenanceWindow class."""

    # pylint: disable=protected-access

    def setUp(self):
        """Initialize before tests are executed."""
        self.controller = get_controller_mock()
        self.start = datetime.now(pytz.utc)
        self.start += timedelta(days=1)
        self.end = self.start + timedelta(hours=6)
        self.switches = [
            "01:23:45:67:89:ab:cd:ef"
        ]
        self.maintenance = MW(
            start=self.start,
            end=self.end,
            switches=self.switches
        )

    def test_as_dict(self):
        """Test as_dict method."""
        mw_dict = self.maintenance.dict()
        expected_dict = {
            'description': '',
            'start': self.start,
            'end': self.end,
            'id': self.maintenance.id,
            'switches': self.switches,
            'interfaces': [],
            'links': [],
            'status': Status.PENDING,
            'inserted_at': None,
            'updated_at': None,
        }
        self.assertEqual(mw_dict, expected_dict)

    def test_start_in_past(self):
        start = datetime.now(pytz.utc) - timedelta(days=1)

        self.assertRaises(ValueError, MW,
            start=start,
            end=self.end,
            switches=self.switches,
        )

    def test_end_before_start(self):
        end = datetime.now(pytz.utc) - timedelta(days=1)

        self.assertRaises(ValueError, MW,
            start=self.start,
            end=end,
            switches=self.switches,
        )

    def test_items_empty(self):

        self.assertRaises(ValueError, MW,
            start=self.start,
            end=self.end,
        )

class TestDeployer(TestCase):
    """Test of the MaintenanceDeployer class."""
    def setUp(self):
        self.controller = get_controller_mock()
        self.start = datetime.now(pytz.utc)
        self.start += timedelta(days=1)
        self.end = self.start + timedelta(hours=6)
        self.switches = [
            "01:23:45:67:89:ab:cd:ef"
        ]
        self.maintenance = MW(
            start=self.start,
            end=self.end,
            switches=self.switches
        )

        self.deployer = MaintenanceDeployer(self.controller, Counter())

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_start_mw_case_1(self, buffer_put_mock):
        """Test the method that starts a maintenance."""
        maintenance = self.maintenance.copy(
            update = {
                'switches': [
                    '01:23:45:67:89:ab:cd:ef',
                    '01:23:45:67:65:ab:cd:ef'
                ],
                'interfaces': [],
                'links': [],
            }
        )
        self.deployer.start_mw(maintenance)
        buffer_put_mock.assert_called_once()

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_start_mw_case_2(self, buffer_put_mock):
        """Test the method that starts a maintenance."""
        interface_id = "interface_1"
        maintenance = self.maintenance.copy(
            update = {
                'switches': [
                    '01:23:45:67:89:ab:cd:ef',
                    '01:23:45:67:65:ab:cd:ef'
                ],
                'interfaces': [interface_id],
                'links': [],
            }
        )
        self.deployer.start_mw(maintenance)
        self.assertEqual(buffer_put_mock.call_count, 2)

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_start_mw_case_3(self, buffer_put_mock):
        """Test the method that starts a maintenance."""
        interface_id = "interface_1"
        link1 = "link_1"
        link2 = "link_2"
        maintenance = self.maintenance.copy(
            update = {
                'switches': [
                ],
                'interfaces': [interface_id],
                'links': [link1, link2],
            }
        )
        self.deployer.start_mw(maintenance)
        self.assertEqual(buffer_put_mock.call_count, 2)

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_end_mw_case_1(self, buffer_put_mock):
        """Test the method that ends a maintenance."""
        maintenance = self.maintenance.copy(
            update = {
                'switches': [
                    '01:23:45:67:89:ab:cd:ef',
                    '01:23:45:67:65:ab:cd:ef'
                ],
                'interfaces': [],
                'links': [],
                'status': Status.RUNNING,
            }
        )
        self.deployer.end_mw(maintenance)
        buffer_put_mock.assert_called_once()

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_end_mw_case_2(self, buffer_put_mock):
        """Test the method that ends a maintenance."""
        interface_id = "interface_1"
        maintenance = self.maintenance.copy(
            update = {
                'switches': [
                    '01:23:45:67:89:ab:cd:ef',
                    '01:23:45:67:65:ab:cd:ef'
                ],
                'interfaces': [interface_id],
                'links': [],
                'status': Status.RUNNING,
            }
        )
        self.deployer.end_mw(maintenance)
        self.assertEqual(buffer_put_mock.call_count, 2)

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_end_mw_case_3(self, buffer_put_mock):
        """Test the method that ends a maintenance."""
        interface_id = "interface_1"
        link1 = "link_1"
        link2 = "link_2"
        maintenance = self.maintenance.copy(
            update = {
                'switches': [
                ],
                'interfaces': [interface_id],
                'links': [link1, link2],
                'status': Status.RUNNING,
            }
        )
        self.deployer.end_mw(maintenance)
        self.assertEqual(buffer_put_mock.call_count, 2)

class TestScheduler(TestCase):
    """Test of the Scheduler Class"""
    
    def setUp(self) -> None:
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

        self.db_controller.get_windows.return_value = [
            pending_window,
            running_window,
            finished_window,
        ]
        self.scheduler.start()

        resultant_schedule_calls = self.task_scheduler.add_job.call_args_list
        self.assertEqual(resultant_schedule_calls, expected_schedule_calls)

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
            self.assertEqual(trigger.run_date, expected_trigger.run_date)
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

