from uuid import uuid4
import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc
from kytos.core import log
from kytos.core.interface import TAG, UNI
from kytos.core.link import Link

TIME_FMT = "%Y-%m-%dT%H:%M:%S"

class MaintenanceWindow:
    """Class to store a maintenance window."""

    def __init__(self, start, end, items=None, id=None):
        """Create an instance of MaintenanceWindow

        Args:
            start(datetime): when the maintenance will begin
            end(datetime): when the maintenance will finish
            items: list of items that will be maintained;
                each item can be either a switch, a link or a client interface
        """
        if items is None:
            items = list()
        self.id = id if id else uuid4().hex
        self.start = start
        self.end = end
        self.items = items

    def as_dict(self):
        """Return this maintenance window as a dictionary"""
        mw_dict = dict()
        mw_dict['id'] = self.id
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
        """Create a maintenance window from a dictionary of attributes"""
        id = mw_dict.get('id')
        start = datetime.datetime.strptime(mw_dict['start'], TIME_FMT)
        end = datetime.datetime.strptime(mw_dict['end'], TIME_FMT)
        items = list()
        for i in mw_dict['items']:
            try:
                item = cls.uni_from_dict(i, controller)
            except KeyError:
                item = cls.link_from_dict(i, controller)
            except TypeError:
                item = i
            if item is None:
                return None
            items.append(item)
        return cls(start, end, items, id)

    def update(self, mw_dict, controller):
        if 'start' in mw_dict:
            self.start = datetime.datetime.strptime(mw_dict['start'], TIME_FMT)
        if 'end' in mw_dict:
            self.end = datetime.datetime.strptime(mw_dict['end'], TIME_FMT)
        if 'items' in mw_dict:
            items = list()
            for i in mw_dict['items']:
                try:
                    item = self.uni_from_dict(i, controller)
                except KeyError:
                    item = self.link_from_dict(i, controller)
                except TypeError:
                    item = i
                if item:
                    items.append(item)
            self.items = items

    @staticmethod
    def intf_from_dict(intf_id, controller):
        intf = controller.get_interface_by_id(intf_id)
        return intf

    @staticmethod
    def uni_from_dict(uni_dict, controller):
        intf = MaintenanceWindow.intf_from_dict(uni_dict['interface_id'],
                                                controller)
        tag = TAG.from_dict(uni_dict['tag'])
        if intf and tag:
            return UNI(intf, tag)
        return None

    @staticmethod
    def link_from_dict(link_dict, controller):
        endpoint_a = controller.get_interface_by_id(link_dict['endpoint_a']['id'])
        endpoint_b = controller.get_interface_by_id(link_dict['endpoint_b']['id'])

        link = Link(endpoint_a, endpoint_b)
        if 'metadata' in link_dict:
            link.extend_metadata(link_dict['metadata'])
        s_vlan = link.get_metadata('s_vlan')
        if s_vlan:
            tag = TAG.from_dict(s_vlan)
            link.update_metadata('s_vlan', tag)
        return link

    def start_mw(self):
        pass

    def end_mw(self):
        pass


class Scheduler:
    """Scheduler for a maintenance window"""

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone=utc)
        self.scheduler.start()

    def add(self, mw):
        self.scheduler.add_job(mw.start_mw, 'date', id=f'{mw.id}-start',
                               run_date=mw.start)
        self.scheduler.add_job(mw.end_mw, 'date', id=f'{mw.id}-end',
                               run_date=mw.end)

    def remove(self, mw):
        self.scheduler.remove_job(f'{mw.id}-start')
        self.scheduler.remove_job(f'{mw.id}-end')
