"""Models used by the maintenance NApp.

This module define models for the maintenance window itself and the
scheduler.
"""
import datetime
from enum import IntEnum
from typing import Any, Optional, Union
from uuid import uuid4

import pytz
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from pydantic import BaseModel, Field, conlist

from kytos.core import KytosEvent, log
from kytos.core.interface import TAG, UNI
from kytos.core.link import Link

TIME_FMT = "%Y-%m-%dT%H:%M:%S%z"


class Status(IntEnum):
    """Maintenance windows status."""

    PENDING = 0
    RUNNING = 1
    FINISHED = 2


class MaintenanceWindow(BaseModel):
    """Class to store a maintenance window."""

    items: conlist(Union[UNI, Link, str], min_items=1)
    id: str = Field(default_factory=lambda: uuid4().hex)
    description: Optional[str]
    start: datetime.datetime
    end: datetime.datetime
    status: Status = Status.PENDING
    controller: Any = Field(..., exclude=True)

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda dt: dt.strftime(TIME_FMT)
        }

    def as_dict(self):
        """Return this maintenance window as a dictionary."""
        return self.dict(exclude_none=True)

    @classmethod
    def from_dict(cls, mw_dict, controller):
        """Create a maintenance window from a dictionary of attributes."""
        return cls(controller=controller, **mw_dict)

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
        if 'items' in mw_dict:
            if not mw_dict['items']:
                raise ValueError('At least one item must be provided')
            self.items = mw_dict['items']
        self.start = start
        self.end = end
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
        switches = []
        unis = []
        links = []
        for item in self.items:
            if isinstance(item, UNI):
                unis.append(UNI)
            elif isinstance(item, Link):
                links.append(item)
            else:
                switch = self.controller.switches.get(item, None)
                if switch:
                    switches.append(switch)
        if switches:
            event = KytosEvent(name=f'kytos/maintenance.{operation}_switch',
                               content={'switches': switches})
            self.controller.buffers.app.put(event)
        if unis:
            event = KytosEvent(name=f'kytos/maintenance.{operation}_uni',
                               content={'unis': unis})
            self.controller.buffers.app.put(event)
        if links:
            event = KytosEvent(name=f'kytos/maintenance.{operation}_link',
                               content={'links': links})
            self.controller.buffers.app.put(event)

    def start_mw(self):
        """Actions taken when a maintenance window starts."""
        self.status = Status.RUNNING
        self.maintenance_event('start')

    def end_mw(self):
        """Actions taken when a maintenance window finishes."""
        self.status = Status.FINISHED
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
