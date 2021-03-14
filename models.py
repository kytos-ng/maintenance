"""Models used by the maintenance NApp.

This module define models for the maintenance window itself and the
scheduler.
"""
import datetime
from uuid import uuid4

import pytz
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler

from kytos.core import KytosEvent, log
from kytos.core.interface import TAG, UNI
from kytos.core.link import Link

TIME_FMT = "%Y-%m-%dT%H:%M:%S%z"


class MaintenanceWindow:
    """Class to store a maintenance window."""

    def __init__(self, start, end, controller, **kwargs):
        """Create an instance of MaintenanceWindow.

        Args:
            start(datetime): when the maintenance will begin
            end(datetime): when the maintenance will finish
            items: list of items that will be maintained;
                each item can be either a switch, a link or a client interface
        """
        # pylint: disable=invalid-name
        self.controller = controller
        items = kwargs.get('items')
        if items is None:
            items = list()
        mw_id = kwargs.get('mw_id')
        self.id = mw_id if mw_id else uuid4().hex
        self.description = kwargs.get('description')
        self.start = start
        self.end = end
        self._switches = list()
        self._links = list()
        self._unis = list()
        self.items = items

    @property
    def items(self):
        """Items getter."""
        return self._switches + self._links + self._unis

    @items.setter
    def items(self, items):
        """Items setter."""
        self._switches = list()
        self._unis = list()
        self._links = list()
        for i in items:
            if isinstance(i, UNI):
                self._unis.append(i)
            elif isinstance(i, Link):
                self._links.append(i)
            else:
                self._switches.append(i)

    def as_dict(self):
        """Return this maintenance window as a dictionary."""
        mw_dict = dict()
        mw_dict['id'] = self.id
        mw_dict['description'] = self.description if self.description else ''
        mw_dict['start'] = self.start.strftime(TIME_FMT)
        mw_dict['end'] = self.end.strftime(TIME_FMT)
        mw_dict['items'] = []
        for i in self.items:
            try:
                mw_dict['items'].append(i.as_dict())
            except (AttributeError, TypeError):
                mw_dict['items'].append(i)
        return mw_dict

    @classmethod
    def from_dict(cls, mw_dict, controller):
        """Create a maintenance window from a dictionary of attributes."""
        mw_id = mw_dict.get('id')

        start = cls.str_to_datetime(mw_dict['start'])
        end = cls.str_to_datetime(mw_dict['end'])
        items = mw_dict['items']
        description = mw_dict.get('description')
        return cls(start, end, controller, items=items, mw_id=mw_id,
                   description=description)

    def update(self, mw_dict):
        """Update a maintenance window with the data from a dictionary."""
        try:
            start = self.str_to_datetime(mw_dict['start'])
        except KeyError:
            start = self.start
        try:
            end = self.str_to_datetime(mw_dict['end'])
        except KeyError:
            end = self.end
        now = datetime.datetime.now(pytz.utc)
        if start < now:
            raise ValueError('Start in the past not allowed.')
        if end < start:
            raise ValueError('End before start not allowed.')
        self.start = start
        self.end = end
        if 'items' in mw_dict:
            self.items = mw_dict['items']
        if 'description' in mw_dict:
            self.description = mw_dict['description']

    @staticmethod
    def intf_from_dict(intf_id, controller):
        """Get the Interface instance with intf_id."""
        intf = controller.get_interface_by_id(intf_id)
        return intf

    @staticmethod
    def uni_from_dict(uni_dict, controller):
        """Create UNI instance from a dictionary."""
        intf = MaintenanceWindow.intf_from_dict(uni_dict['interface_id'],
                                                controller)
        tag = TAG.from_dict(uni_dict['tag'])
        if intf and tag:
            return UNI(intf, tag)
        return None

    @staticmethod
    def link_from_dict(link_dict, controller):
        """Create a link instance from a dictionary."""
        endpoint_a = controller.get_interface_by_id(
            link_dict['endpoint_a']['id'])
        endpoint_b = controller.get_interface_by_id(
            link_dict['endpoint_b']['id'])

        link = Link(endpoint_a, endpoint_b)
        if 'metadata' in link_dict:
            link.extend_metadata(link_dict['metadata'])
        s_vlan = link.get_metadata('s_vlan')
        if s_vlan:
            tag = TAG.from_dict(s_vlan)
            link.update_metadata('s_vlan', tag)
        return link

    @staticmethod
    def str_to_datetime(str_date):
        """Convert a string representing a date and time to datetime."""
        date = datetime.datetime.strptime(str_date, TIME_FMT)
        return date.astimezone(pytz.utc)

    def maintenance_event(self, operation):
        """Create events to start/end a maintenance."""
        if self._switches:
            switches = []
            for dpid in self._switches:
                switch = self.controller.switches.get(dpid, None)
                if switch:
                    switches.append(switch)
            event = KytosEvent(name=f'kytos/maintenance.{operation}_switch',
                               content={'switches': switches})
            self.controller.buffers.app.put(event)
        if self._unis:
            event = KytosEvent(name=f'kytos/maintenance.{operation}_uni',
                               content={'unis': self._unis})
            self.controller.buffers.app.put(event)
        if self._links:
            event = KytosEvent(name=f'kytos/maintenance.{operation}_link',
                               content={'links': self._links})
            self.controller.buffers.app.put(event)

    def start_mw(self):
        """Actions taken when a maintenance window starts."""
        self.maintenance_event('start')

    def end_mw(self):
        """Actions taken when a maintenance window finishes."""
        self.maintenance_event('end')


class Scheduler:
    """Scheduler for a maintenance window."""

    def __init__(self):
        """Initialize a new scheduler."""
        self.scheduler = BackgroundScheduler(timezone=pytz.utc)
        self.scheduler.start()

    def add(self, maintenance):
        """Add jobs to start and end a maintenance window."""
        self.scheduler.add_job(maintenance.start_mw, 'date',
                               id=f'{maintenance.id}-start',
                               run_date=maintenance.start)
        self.scheduler.add_job(maintenance.end_mw, 'date',
                               id=f'{maintenance.id}-end',
                               run_date=maintenance.end)

    def remove(self, maintenance):
        """Remove jobs that start and end a maintenance window."""
        try:
            self.scheduler.remove_job(f'{maintenance.id}-start')
        except JobLookupError:
            log.info(f'Job to start {maintenance.id} already removed.')
        try:
            self.scheduler.remove_job(f'{maintenance.id}-end')
        except JobLookupError:
            log.info(f'Job to end {maintenance.id} already removed.')
