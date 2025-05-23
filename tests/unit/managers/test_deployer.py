"""Tests for the deployer module."""

from unittest.mock import MagicMock

from collections import Counter

from datetime import datetime, timedelta
from threading import Lock
import pytz
from kytos.core.common import EntityStatus
from kytos.lib.helpers import get_controller_mock
from napps.kytos.maintenance.models import MaintenanceWindow as MW

from napps.kytos.maintenance.managers.deployer import (
    MaintenanceDeployer,
)

class TestDeployer:
    """Test of the MaintenanceDeployer class."""
    def setup_method(self):
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

        self.deployer = MaintenanceDeployer(self.controller, Counter(), Counter(), Counter(), Lock())
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


        self.controller.links = {
            'link_1': self.link_1,
            'link_2': self.link_2,
            'link_3': self.link_3,
        }

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
        assert event.name == 'topology.interruption.start'
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
        assert event.name == 'topology.interruption.end'
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
        assert event.name == 'topology.interruption.start'
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
        assert event.name == 'topology.interruption.end'
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
        assert event.name == 'topology.interruption.start'
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
        assert event.name == 'topology.interruption.end'
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

    def test_dev_status(self):
        switch_1 = MagicMock(
            id = 'test-switch-1',
            interfaces = {},
        )
        switch_2 = MagicMock(
            id = 'test-switch-2',
            interfaces = {},
        )
        interface_1 = MagicMock(
            id = 'test-interface-1',
            switch = switch_1,
            link = None,
        )
        switch_1.interfaces[0] = interface_1
        interface_2 = MagicMock(
            id = 'test-interface-2',
            switch = switch_2,
            link = None,
        )
        switch_2.interfaces[0] = interface_2
        link = MagicMock(
            id = 'test-link',
            endpoint_a = interface_1,
            endpoint_b = interface_2,
        )

        # No active maintenances
        assert self.deployer.link_status_func(link) != EntityStatus.DOWN
        assert self.deployer.interface_status_func(interface_1) != EntityStatus.DOWN
        assert self.deployer.interface_status_func(interface_2) != EntityStatus.DOWN
        assert self.deployer.switch_status_func(switch_1) != EntityStatus.DOWN
        assert self.deployer.switch_status_func(switch_2) != EntityStatus.DOWN

        assert self.deployer.link_status_reason_func(link) == set()
        assert self.deployer.interface_status_reason_func(interface_1) == set()
        assert self.deployer.interface_status_reason_func(interface_2) == set()
        assert self.deployer.switch_status_reason_func(switch_1) == set()
        assert self.deployer.switch_status_reason_func(switch_2) == set()

        # Active switch maintenance
        self.deployer.maintenance_switches['test-switch-1'] = 1

        assert self.deployer.link_status_func(link) == EntityStatus.DOWN
        assert self.deployer.interface_status_func(interface_1) == EntityStatus.DOWN
        assert self.deployer.interface_status_func(interface_2) != EntityStatus.DOWN
        assert self.deployer.switch_status_func(switch_1) == EntityStatus.DOWN
        assert self.deployer.switch_status_func(switch_2) != EntityStatus.DOWN

        assert self.deployer.link_status_reason_func(link) == {'maintenance'}
        assert self.deployer.interface_status_reason_func(interface_1) == {'maintenance'}
        assert self.deployer.interface_status_reason_func(interface_2) == set()
        assert self.deployer.switch_status_reason_func(switch_1) == {'maintenance'}
        assert self.deployer.switch_status_reason_func(switch_2) == set()

        # Active interface maintenance
        self.deployer.maintenance_switches['test-switch-1'] = 0
        self.deployer.maintenance_interfaces['test-interface-1'] = 1

        assert self.deployer.link_status_func(link) == EntityStatus.DOWN
        assert self.deployer.interface_status_func(interface_1) == EntityStatus.DOWN
        assert self.deployer.interface_status_func(interface_2) != EntityStatus.DOWN
        assert self.deployer.switch_status_func(switch_1) != EntityStatus.DOWN
        assert self.deployer.switch_status_func(switch_2) != EntityStatus.DOWN

        assert self.deployer.link_status_reason_func(link) == {'maintenance'}
        assert self.deployer.interface_status_reason_func(interface_1) == {'maintenance'}
        assert self.deployer.interface_status_reason_func(interface_2) == set()
        assert self.deployer.switch_status_reason_func(switch_1) == set()
        assert self.deployer.switch_status_reason_func(switch_2) == set()

        # Active link maintenance
        self.deployer.maintenance_switches['test-switch-1'] = 0
        self.deployer.maintenance_interfaces['test-interface-1'] = 0
        self.deployer.maintenance_links['test-link'] = 1

        assert self.deployer.link_status_func(link) == EntityStatus.DOWN
        assert self.deployer.interface_status_func(interface_1) != EntityStatus.DOWN
        assert self.deployer.interface_status_func(interface_2) != EntityStatus.DOWN
        assert self.deployer.switch_status_func(switch_1) != EntityStatus.DOWN
        assert self.deployer.switch_status_func(switch_2) != EntityStatus.DOWN

        assert self.deployer.link_status_reason_func(link) == {'maintenance'}
        assert self.deployer.interface_status_reason_func(interface_1) == set()
        assert self.deployer.interface_status_reason_func(interface_2) == set()
        assert self.deployer.switch_status_reason_func(switch_1) == set()
        assert self.deployer.switch_status_reason_func(switch_2) == set()
