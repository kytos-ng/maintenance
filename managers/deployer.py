"""Module for handling the deployment of maintenance windows."""
from collections import Counter
from dataclasses import dataclass
from itertools import chain

from kytos.core.common import EntityStatus
from kytos.core.controller import Controller
from kytos.core.events import KytosEvent
from kytos.core.switch import Switch
from kytos.core.interface import Interface
from kytos.core.link import Link

from ..models import MaintenanceWindow


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
            f'topology.interruption.{operation}',
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

        tot_switches = list(filter(
            self.switch_not_in_maintenance,
            explicit_switches
        ))

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

        tot_interfaces = list(
            filter(
                self.interface_not_in_maintenance,
                chain(implicit_interfaces, explicit_interfaces)
            )
        )

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

        tot_links = list(
            filter(
                self.link_not_in_maintenance,
                chain(implicit_links, explicit_links)
            )
        )

        affected_switch_ids = frozenset(
            map(
                lambda switch: switch.id,
                tot_switches
            )
        )

        affected_interface_ids = frozenset(
            map(
                lambda interface: interface.id,
                tot_interfaces
            )
        )

        affected_link_ids = frozenset(
            map(
                lambda link: link.id,
                tot_links
            )
        )
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

    def switch_not_in_maintenance(self, dev: Switch) -> bool:
        """Checks if a switch is not undergoing maintenance"""
        return not self.maintenance_switches[dev.id]

    def interface_not_in_maintenance(self, dev: Interface) -> bool:
        """Checks if a interface is not undergoing maintenance"""
        return (
            not self.maintenance_interfaces[dev.id] and
            self.switch_not_in_maintenance(dev.switch)
        )

    def link_not_in_maintenance(self, dev: Link) -> bool:
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

    def switch_status_func(self, dev: Switch) -> EntityStatus:
        """Checks if a given device is undergoing maintenance"""
        if self.switch_not_in_maintenance(dev):
            return EntityStatus.UP
        return EntityStatus.DOWN

    def switch_status_reason_func(self, dev: Switch) -> frozenset:
        """Checks if a given device is undergoing maintenance"""
        if self.switch_not_in_maintenance(dev):
            return frozenset()
        return frozenset({'maintenance'})

    def interface_status_func(self, dev: Interface) -> EntityStatus:
        """Checks if a given device is undergoing maintenance"""
        if self.interface_not_in_maintenance(dev):
            return EntityStatus.UP
        return EntityStatus.DOWN

    def interface_status_reason_func(self, dev: Interface) -> frozenset:
        """Checks if a given device is undergoing maintenance"""
        if self.interface_not_in_maintenance(dev):
            return frozenset()
        return frozenset({'maintenance'})

    def link_status_func(self, dev: Link) -> EntityStatus:
        """Checks if a given device is undergoing maintenance"""
        if self.link_not_in_maintenance(dev):
            return EntityStatus.UP
        return EntityStatus.DOWN

    def link_status_reason_func(self, dev: Link) -> frozenset:
        """Checks if a given device is undergoing maintenance"""
        if self.link_not_in_maintenance(dev):
            return frozenset()
        return frozenset({'maintenance'})