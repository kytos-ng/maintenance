"""Tests for the models module."""
import datetime
from unittest import TestCase
from unittest.mock import patch, MagicMock

from attrs import evolve
import pytz
from kytos.lib.helpers import get_controller_mock
from napps.kytos.maintenance.models import MaintenanceWindow as MW, Status

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
        self.switches = [
            "01:23:45:67:89:ab:cd:ef"
        ]
        self.maintenance = MW(start = self.start, end = self.end,
                              switches = self.switches)

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
        maintenance.start_mw(self.controller)
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
        maintenance.start_mw(self.controller)
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
        maintenance.start_mw(self.controller)
        self.assertEqual(buffer_put_mock.call_count, 2)

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_end_mw_case_1(self, buffer_put_mock):
        """Test the method that starts a maintenance."""
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
        maintenance.end_mw(self.controller)
        buffer_put_mock.assert_called_once()

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_end_mw_case_2(self, buffer_put_mock):
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
                'status': Status.RUNNING,
            }
        )
        maintenance.end_mw(self.controller)
        self.assertEqual(buffer_put_mock.call_count, 2)

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_end_mw_case_3(self, buffer_put_mock):
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
                'status': Status.RUNNING,
            }
        )
        maintenance.end_mw(self.controller)
        self.assertEqual(buffer_put_mock.call_count, 2)
