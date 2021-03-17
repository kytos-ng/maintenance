"""Tests for the models module."""
import datetime
from unittest import TestCase
from unittest.mock import patch, MagicMock

import pytz
from napps.kytos.maintenance.models import MaintenanceWindow as MW, Status
from tests.helpers import get_controller_mock

TIME_FMT = "%Y-%m-%dT%H:%M:%S%z"


class TestMW(TestCase):
    """Test of the MaintenanceWindow class."""

    # pylint: disable=protected-access

    def setUp(self):
        """Initialize before tests are executed."""
        self.controller = get_controller_mock()
        self.start = datetime.datetime.now(pytz.utc)
        self.start += datetime.timedelta(days=1)
        self.end = self.start + datetime.timedelta(hours=6)
        self.items = [
            "01:23:45:67:89:ab:cd:ef"
        ]
        self.maintenance = MW(self.start, self.end, self.controller,
                              items=self.items)

    def test_as_dict(self):
        """Test as_dict method."""
        mw_dict = self.maintenance.as_dict()
        expected_dict = {
            'description': '',
            'start': self.start.strftime(TIME_FMT),
            'end': self.end.strftime(TIME_FMT),
            'id': self.maintenance.id,
            'items': self.items,
            'status': Status.PENDING
        }
        self.assertEqual(mw_dict, expected_dict)

    def test_update_start(self):
        """Test update start parameter."""
        start = datetime.datetime.now(pytz.utc).replace(microsecond=0)
        start += datetime.timedelta(hours=4)
        self.maintenance.update({'start': start.strftime(TIME_FMT)})
        self.assertEqual(self.maintenance.start, start)

    def test_update_items(self):
        """Test update items parameter."""
        items = ["09:87:65:43:21:fe:dc:ba"]
        self.maintenance.update({'items': items})
        self.assertEqual(self.maintenance.items, items)

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_start_mw_case_1(self, buffer_put_mock):
        """Test the method that starts a maintenance."""
        switch1 = MagicMock()
        self.controller.switches = {'01:23:45:67:89:ab:cd:ef': switch1}
        self.maintenance.start_mw()
        buffer_put_mock.assert_called_once()

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_start_mw_case_2(self, buffer_put_mock):
        """Test the method that starts a maintenance."""
        switch2 = MagicMock()
        uni1 = MagicMock()
        self.controller.switches = {'01:23:45:67:89:ab:cd:ef': switch2}
        self.maintenance._switches = ['01:23:45:67:89:ab:cd:ef',
                                      '01:23:45:67:65:ab:cd:ef']
        self.maintenance._unis = [uni1]
        self.maintenance.start_mw()
        self.assertEqual(buffer_put_mock.call_count, 2)

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_start_mw_case_3(self, buffer_put_mock):
        """Test the method that starts a maintenance."""
        uni1 = MagicMock()
        link1 = MagicMock()
        link2 = MagicMock()
        self.maintenance._switches = []
        self.maintenance._unis = [uni1]
        self.maintenance._links = [link1, link2]
        self.maintenance.start_mw()
        self.assertEqual(buffer_put_mock.call_count, 2)
        self.assertEqual(self.maintenance.status, Status.RUNNING)

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_end_mw_case_1(self, buffer_put_mock):
        """Test the method that starts a maintenance."""
        switch1 = MagicMock()
        self.controller.switches = {'01:23:45:67:89:ab:cd:ef': switch1}
        self.maintenance._switches = ['01:23:45:67:89:ab:cd:ef']
        self.maintenance.end_mw()
        buffer_put_mock.assert_called_once()

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_end_mw_case_2(self, buffer_put_mock):
        """Test the method that starts a maintenance."""
        switch2 = MagicMock()
        uni1 = MagicMock()
        self.controller.switches = {'01:23:45:67:89:ab:cd:ef': switch2}
        self.maintenance._switches = ['01:23:45:67:89:ab:cd:ef',
                                      '01:23:45:67:65:ab:cd:ef']
        self.maintenance._unis = [uni1]
        self.maintenance.end_mw()
        self.assertEqual(buffer_put_mock.call_count, 2)

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_end_mw_case_3(self, buffer_put_mock):
        """Test the method that starts a maintenance."""
        uni1 = MagicMock()
        link1 = MagicMock()
        link2 = MagicMock()
        self.maintenance._switches = []
        self.maintenance._unis = [uni1]
        self.maintenance._links = [link1, link2]
        self.maintenance.end_mw()
        self.assertEqual(buffer_put_mock.call_count, 2)
