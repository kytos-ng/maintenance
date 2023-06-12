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

        self.deployer = MaintenanceDeployer(self.controller, Counter(), Counter(), Counter())
        # Initialize Switches
        self.controller.switches = {
            '01:23:45:67:89:ab:cd:ef': MagicMock(
                id='01:23:45:67:89:ab:cd:ef',
                interfaces = {},
            ),
            '01:23:45:67:65:ab:cd:ef': MagicMock(
                id='01:23:45:67:65:ab:cd:ef',
                interfaces = {},
            ),
            '01:23:45:67:66:ab:cd:ef': MagicMock(
                id='01:23:45:67:66:ab:cd:ef',
                interfaces = {},
            ),
        }
        # Initialize Interfaces
        self.controller.switches['01:23:45:67:89:ab:cd:ef'].interfaces = {
            0: MagicMock(
                id = '01:23:45:67:89:ab:cd:ef:0',
                switch = self.controller.switches['01:23:45:67:89:ab:cd:ef'],
                link = None,
            ),
            1: MagicMock(
                id = '01:23:45:67:89:ab:cd:ef:1',
                switch = self.controller.switches['01:23:45:67:89:ab:cd:ef'],
                link = None,
            ),
            2: MagicMock(
                id = '01:23:45:67:89:ab:cd:ef:2',
                switch = self.controller.switches['01:23:45:67:89:ab:cd:ef'],
                link = None,
            ),
        }

        self.controller.switches['01:23:45:67:65:ab:cd:ef'].interfaces = {
            0: MagicMock(
                id = '01:23:45:67:65:ab:cd:ef:0',
                switch = self.controller.switches['01:23:45:67:65:ab:cd:ef'],
                link = None,
            ),
            1: MagicMock(
                id = '01:23:45:67:65:ab:cd:ef:1',
                switch = self.controller.switches['01:23:45:67:65:ab:cd:ef'],
                link = None,
            ),
            2: MagicMock(
                id = '01:23:45:67:65:ab:cd:ef:2',
                switch = self.controller.switches['01:23:45:67:65:ab:cd:ef'],
                link = None,
            ),
        }

        self.controller.switches['01:23:45:67:66:ab:cd:ef'].interfaces = {
            0: MagicMock(
                id = '01:23:45:67:66:ab:cd:ef:0',
                switch = self.controller.switches['01:23:45:67:66:ab:cd:ef'],
                link = None,
            ),
            1: MagicMock(
                id = '01:23:45:67:66:ab:cd:ef:1',
                switch = self.controller.switches['01:23:45:67:66:ab:cd:ef'],
                link = None,
            ),
            2: MagicMock(
                id = '01:23:45:67:66:ab:cd:ef:2',
                switch = self.controller.switches['01:23:45:67:66:ab:cd:ef'],
                link = None,
            ),
        }

        # Initialize Links
        self.link_1 = MagicMock(
            id = 'link_1',
            endpoint_a = self.controller.switches['01:23:45:67:89:ab:cd:ef'].interfaces[0],
            endpoint_b = self.controller.switches['01:23:45:67:65:ab:cd:ef'].interfaces[0],
        )
        self.controller.switches['01:23:45:67:89:ab:cd:ef'].interfaces[0].link = self.link_1
        self.controller.switches['01:23:45:67:65:ab:cd:ef'].interfaces[0].link = self.link_1

        self.link_2 = MagicMock(
            id = 'link_2',
            endpoint_a = self.controller.switches['01:23:45:67:89:ab:cd:ef'].interfaces[1],
            endpoint_b = self.controller.switches['01:23:45:67:66:ab:cd:ef'].interfaces[0],
        )
        self.controller.switches['01:23:45:67:89:ab:cd:ef'].interfaces[1].link = self.link_2
        self.controller.switches['01:23:45:67:66:ab:cd:ef'].interfaces[0].link = self.link_2

        self.link_3 = MagicMock(
            id = 'link_3',
            endpoint_a = self.controller.switches['01:23:45:67:66:ab:cd:ef'].interfaces[1],
            endpoint_b = self.controller.switches['01:23:45:67:66:ab:cd:ef'].interfaces[2],
        )
        self.controller.switches['01:23:45:67:66:ab:cd:ef'].interfaces[1].link = self.link_3
        self.controller.switches['01:23:45:67:66:ab:cd:ef'].interfaces[2].link = self.link_3


        self.controller.napps[('kytos', 'topology')] = MagicMock(
            links = {
                'link_1': self.link_1,
                'link_2': self.link_2,
                'link_3': self.link_3,
            }
        )

    def test_mw_case_1(self):
        """Test deploying a maintenance window to switches."""
        buffer_put_mock = MagicMock()
        self.controller.buffers.app.put = buffer_put_mock
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
        args, kwargs = buffer_put_mock.call_args
        event = args[0]
        assert event.name == 'kytos/topology.interruption.start'
        assert event.content['type'] == 'maintenance'
        assert sorted(event.content['switches']) == [
            '01:23:45:67:65:ab:cd:ef',
            '01:23:45:67:89:ab:cd:ef',
        ]
        assert sorted(event.content['interfaces']) == [
            '01:23:45:67:65:ab:cd:ef:0',
            '01:23:45:67:65:ab:cd:ef:1',
            '01:23:45:67:65:ab:cd:ef:2',
            '01:23:45:67:89:ab:cd:ef:0',
            '01:23:45:67:89:ab:cd:ef:1',
            '01:23:45:67:89:ab:cd:ef:2',
        ]
        assert sorted(event.content['links']) == [
            'link_1',
            'link_2',
        ]

        # Check whats in maintenance
        # Switches
        assert not self.deployer.switch_not_in_maintenance(self.controller.switches['01:23:45:67:89:ab:cd:ef'])
        assert not self.deployer.switch_not_in_maintenance(self.controller.switches['01:23:45:67:65:ab:cd:ef'])
        assert     self.deployer.switch_not_in_maintenance(self.controller.switches['01:23:45:67:66:ab:cd:ef'])
        # Interfaces
        for interface in self.controller.switches['01:23:45:67:89:ab:cd:ef'].interfaces.values():
            assert not self.deployer.interface_not_in_maintenance(interface)
        for interface in self.controller.switches['01:23:45:67:65:ab:cd:ef'].interfaces.values():
            assert not self.deployer.interface_not_in_maintenance(interface)
        for interface in self.controller.switches['01:23:45:67:66:ab:cd:ef'].interfaces.values():
            assert     self.deployer.interface_not_in_maintenance(interface)
        # Links
        assert not self.deployer.link_not_in_maintenance(self.link_1)
        assert not self.deployer.link_not_in_maintenance(self.link_2)
        assert     self.deployer.link_not_in_maintenance(self.link_3)

        self.deployer.end_mw(maintenance)
        args, kwargs = buffer_put_mock.call_args
        event = args[0]
        assert event.name == 'kytos/topology.interruption.end'
        assert event.content['type'] == 'maintenance'
        assert sorted(event.content['switches']) == [
            '01:23:45:67:65:ab:cd:ef',
            '01:23:45:67:89:ab:cd:ef',
        ]
        assert sorted(event.content['interfaces']) == [
            '01:23:45:67:65:ab:cd:ef:0',
            '01:23:45:67:65:ab:cd:ef:1',
            '01:23:45:67:65:ab:cd:ef:2',
            '01:23:45:67:89:ab:cd:ef:0',
            '01:23:45:67:89:ab:cd:ef:1',
            '01:23:45:67:89:ab:cd:ef:2',
        ]
        assert sorted(event.content['links']) == [
            'link_1',
            'link_2',
        ]
        # Check whats in maintenance
        # Switches
        assert     self.deployer.switch_not_in_maintenance(self.controller.switches['01:23:45:67:89:ab:cd:ef'])
        assert     self.deployer.switch_not_in_maintenance(self.controller.switches['01:23:45:67:65:ab:cd:ef'])
        assert     self.deployer.switch_not_in_maintenance(self.controller.switches['01:23:45:67:66:ab:cd:ef'])
        # Interfaces
        for interface in self.controller.switches['01:23:45:67:89:ab:cd:ef'].interfaces.values():
            assert     self.deployer.interface_not_in_maintenance(interface)
        for interface in self.controller.switches['01:23:45:67:65:ab:cd:ef'].interfaces.values():
            assert     self.deployer.interface_not_in_maintenance(interface)
        for interface in self.controller.switches['01:23:45:67:66:ab:cd:ef'].interfaces.values():
            assert     self.deployer.interface_not_in_maintenance(interface)
        # Links
        assert     self.deployer.link_not_in_maintenance(self.link_1)
        assert     self.deployer.link_not_in_maintenance(self.link_2)
        assert     self.deployer.link_not_in_maintenance(self.link_3)

    def test_mw_case_2(self):
        """Test deploying a maintenance window to interfaces."""
        buffer_put_mock = MagicMock()
        self.controller.buffers.app.put = buffer_put_mock
        
        maintenance = self.maintenance.copy(
            update = {
                'switches': [],
                'interfaces': [
                    '01:23:45:67:65:ab:cd:ef:0',
                    '01:23:45:67:89:ab:cd:ef:0',
                    '01:23:45:67:89:ab:cd:ef:1',
                ],
                'links': [],
            }
        )
        self.deployer.start_mw(maintenance)
        args, kwargs = buffer_put_mock.call_args
        event = args[0]
        assert event.name == 'kytos/topology.interruption.start'
        assert event.content['type'] == 'maintenance'
        assert sorted(event.content['switches']) == []
        assert sorted(event.content['interfaces']) == [
            '01:23:45:67:65:ab:cd:ef:0',
            '01:23:45:67:89:ab:cd:ef:0',
            '01:23:45:67:89:ab:cd:ef:1',
        ]
        assert sorted(event.content['links']) == [
            'link_1',
            'link_2',
        ]

        # Check whats in maintenance
        # Switches
        assert     self.deployer.switch_not_in_maintenance(self.controller.switches['01:23:45:67:89:ab:cd:ef'])
        assert     self.deployer.switch_not_in_maintenance(self.controller.switches['01:23:45:67:65:ab:cd:ef'])
        assert     self.deployer.switch_not_in_maintenance(self.controller.switches['01:23:45:67:66:ab:cd:ef'])
        # Interfaces

        assert not self.deployer.interface_not_in_maintenance(self.controller.switches['01:23:45:67:89:ab:cd:ef'].interfaces[0])
        assert not self.deployer.interface_not_in_maintenance(self.controller.switches['01:23:45:67:89:ab:cd:ef'].interfaces[1])
        assert     self.deployer.interface_not_in_maintenance(self.controller.switches['01:23:45:67:89:ab:cd:ef'].interfaces[2])

        assert not self.deployer.interface_not_in_maintenance(self.controller.switches['01:23:45:67:65:ab:cd:ef'].interfaces[0])
        assert     self.deployer.interface_not_in_maintenance(self.controller.switches['01:23:45:67:65:ab:cd:ef'].interfaces[1])
        assert     self.deployer.interface_not_in_maintenance(self.controller.switches['01:23:45:67:65:ab:cd:ef'].interfaces[2])

        for interface in self.controller.switches['01:23:45:67:66:ab:cd:ef'].interfaces.values():
            assert     self.deployer.interface_not_in_maintenance(interface)

        # Links
        assert not self.deployer.link_not_in_maintenance(self.link_1)
        assert not self.deployer.link_not_in_maintenance(self.link_2)
        assert     self.deployer.link_not_in_maintenance(self.link_3)

        self.deployer.end_mw(maintenance)
        args, kwargs = buffer_put_mock.call_args
        event = args[0]
        assert event.name == 'kytos/topology.interruption.end'
        assert event.content['type'] == 'maintenance'
        assert sorted(event.content['switches']) == []
        assert sorted(event.content['switches']) == []
        assert sorted(event.content['interfaces']) == [
            '01:23:45:67:65:ab:cd:ef:0',
            '01:23:45:67:89:ab:cd:ef:0',
            '01:23:45:67:89:ab:cd:ef:1',
        ]
        assert sorted(event.content['links']) == [
            'link_1',
            'link_2',
        ]
        # Check whats in maintenance
        # Switches
        assert     self.deployer.switch_not_in_maintenance(self.controller.switches['01:23:45:67:89:ab:cd:ef'])
        assert     self.deployer.switch_not_in_maintenance(self.controller.switches['01:23:45:67:65:ab:cd:ef'])
        assert     self.deployer.switch_not_in_maintenance(self.controller.switches['01:23:45:67:66:ab:cd:ef'])
        # Interfaces
        for interface in self.controller.switches['01:23:45:67:89:ab:cd:ef'].interfaces.values():
            assert     self.deployer.interface_not_in_maintenance(interface)
        for interface in self.controller.switches['01:23:45:67:65:ab:cd:ef'].interfaces.values():
            assert     self.deployer.interface_not_in_maintenance(interface)
        for interface in self.controller.switches['01:23:45:67:66:ab:cd:ef'].interfaces.values():
            assert     self.deployer.interface_not_in_maintenance(interface)
        # Links
        assert     self.deployer.link_not_in_maintenance(self.link_1)
        assert     self.deployer.link_not_in_maintenance(self.link_2)
        assert     self.deployer.link_not_in_maintenance(self.link_3)

    def test_mw_case_3(self):
        """Test deploying a maintenance window to links."""
        buffer_put_mock = MagicMock()
        self.controller.buffers.app.put = buffer_put_mock
        maintenance = self.maintenance.copy(
            update = {
                'switches': [],
                'interfaces': [],
                'links': ['link_1', 'link_2'],
            }
        )
        self.deployer.start_mw(maintenance)
        args, kwargs = buffer_put_mock.call_args
        event = args[0]
        assert event.name == 'kytos/topology.interruption.start'
        assert event.content['type'] == 'maintenance'
        assert sorted(event.content['switches']) == []
        assert sorted(event.content['interfaces']) == []
        assert sorted(event.content['links']) == [
            'link_1',
            'link_2',
        ]

        # Check whats in maintenance
        # Switches
        assert     self.deployer.switch_not_in_maintenance(self.controller.switches['01:23:45:67:89:ab:cd:ef'])
        assert     self.deployer.switch_not_in_maintenance(self.controller.switches['01:23:45:67:65:ab:cd:ef'])
        assert     self.deployer.switch_not_in_maintenance(self.controller.switches['01:23:45:67:66:ab:cd:ef'])
        # Interfaces
        for interface in self.controller.switches['01:23:45:67:89:ab:cd:ef'].interfaces.values():
            assert     self.deployer.interface_not_in_maintenance(interface)
        for interface in self.controller.switches['01:23:45:67:65:ab:cd:ef'].interfaces.values():
            assert     self.deployer.interface_not_in_maintenance(interface)
        for interface in self.controller.switches['01:23:45:67:66:ab:cd:ef'].interfaces.values():
            assert     self.deployer.interface_not_in_maintenance(interface)
        # Links
        assert not self.deployer.link_not_in_maintenance(self.link_1)
        assert not self.deployer.link_not_in_maintenance(self.link_2)
        assert     self.deployer.link_not_in_maintenance(self.link_3)

        self.deployer.end_mw(maintenance)
        args, kwargs = buffer_put_mock.call_args
        event = args[0]
        assert event.name == 'kytos/topology.interruption.end'
        assert event.content['type'] == 'maintenance'
        assert sorted(event.content['switches']) == []
        assert sorted(event.content['interfaces']) == []
        assert sorted(event.content['links']) == [
            'link_1',
            'link_2',
        ]
        # Check whats in maintenance
        # Switches
        assert     self.deployer.switch_not_in_maintenance(self.controller.switches['01:23:45:67:89:ab:cd:ef'])
        assert     self.deployer.switch_not_in_maintenance(self.controller.switches['01:23:45:67:65:ab:cd:ef'])
        assert     self.deployer.switch_not_in_maintenance(self.controller.switches['01:23:45:67:66:ab:cd:ef'])
        # Interfaces
        for interface in self.controller.switches['01:23:45:67:89:ab:cd:ef'].interfaces.values():
            assert     self.deployer.interface_not_in_maintenance(interface)
        for interface in self.controller.switches['01:23:45:67:65:ab:cd:ef'].interfaces.values():
            assert     self.deployer.interface_not_in_maintenance(interface)
        for interface in self.controller.switches['01:23:45:67:66:ab:cd:ef'].interfaces.values():
            assert     self.deployer.interface_not_in_maintenance(interface)
        # Links
        assert     self.deployer.link_not_in_maintenance(self.link_1)
        assert     self.deployer.link_not_in_maintenance(self.link_2)
        assert     self.deployer.link_not_in_maintenance(self.link_3)


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

