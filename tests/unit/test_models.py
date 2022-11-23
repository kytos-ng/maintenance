"""Tests for the models module."""
import datetime
from unittest import TestCase
from unittest.mock import patch, MagicMock

from attrs import evolve
import pytz
from kytos.lib.helpers import get_controller_mock
from napps.kytos.maintenance.models import MaintenanceWindow as MW, Status
from napps.kytos.maintenance.main import converter

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
        self.maintenance = MW(self.start, self.end,
                              switches=self.switches)

    def test_as_dict(self):
        """Test as_dict method."""
        mw_dict = converter.unstructure(self.maintenance)
        expected_dict = {
            'description': '',
            'start': self.start.strftime(TIME_FMT),
            'end': self.end.strftime(TIME_FMT),
            'id': self.maintenance.id,
            'switches': self.switches,
            'interfaces': [],
            'links': [],
            'status': Status.PENDING
        }
        self.assertEqual(mw_dict, expected_dict)

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_start_mw_case_1(self, buffer_put_mock):
        """Test the method that starts a maintenance."""
        maintenance = evolve(
            self.maintenance,
            switches = [
                '01:23:45:67:89:ab:cd:ef',
                '01:23:45:67:65:ab:cd:ef'
            ],
            interfaces=[],
            links = [],
        )
        next_win = maintenance.start_mw(self.controller)
        buffer_put_mock.assert_called_once()
        self.assertEqual(next_win.status, Status.RUNNING)

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_start_mw_case_2(self, buffer_put_mock):
        """Test the method that starts a maintenance."""
        interface_id = MagicMock()
        maintenance = evolve(
            self.maintenance,
            switches = [
                '01:23:45:67:89:ab:cd:ef',
                '01:23:45:67:65:ab:cd:ef'
            ],
            interfaces=[interface_id],
            links = [],
        )
        next_win = maintenance.start_mw(self.controller)
        self.assertEqual(buffer_put_mock.call_count, 2)
        self.assertEqual(next_win.status, Status.RUNNING)

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_start_mw_case_3(self, buffer_put_mock):
        """Test the method that starts a maintenance."""
        interface_id = MagicMock()
        link1 = MagicMock()
        link2 = MagicMock()
        maintenance = evolve(
            self.maintenance,
            switches = [
            ],
            interfaces=[interface_id],
            links = [link1, link2],
        )
        next_win = maintenance.start_mw(self.controller)
        self.assertEqual(buffer_put_mock.call_count, 2)
        self.assertEqual(next_win.status, Status.RUNNING)

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_end_mw_case_1(self, buffer_put_mock):
        """Test the method that starts a maintenance."""
        maintenance = evolve(
            self.maintenance,
            switches = [
                '01:23:45:67:89:ab:cd:ef',
                '01:23:45:67:65:ab:cd:ef'
            ],
            interfaces=[],
            links = [],
            status = Status.RUNNING,
        )
        next_win = maintenance.end_mw(self.controller)
        buffer_put_mock.assert_called_once()
        self.assertEqual(next_win.status, Status.FINISHED)

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_end_mw_case_2(self, buffer_put_mock):
        """Test the method that starts a maintenance."""
        interface_id = MagicMock()
        maintenance = evolve(
            self.maintenance,
            switches = [
                '01:23:45:67:89:ab:cd:ef',
                '01:23:45:67:65:ab:cd:ef'
            ],
            interfaces=[interface_id],
            links = [],
            status = Status.RUNNING,
        )
        next_win = maintenance.end_mw(self.controller)
        self.assertEqual(buffer_put_mock.call_count, 2)
        self.assertEqual(next_win.status, Status.FINISHED)

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_end_mw_case_3(self, buffer_put_mock):
        """Test the method that starts a maintenance."""
        interface_id = MagicMock()
        link1 = MagicMock()
        link2 = MagicMock()
        maintenance = evolve(
            self.maintenance,
            switches = [
            ],
            interfaces=[interface_id],
            links = [link1, link2],
            status = Status.RUNNING,
        )
        next_win = maintenance.end_mw(self.controller)
        self.assertEqual(buffer_put_mock.call_count, 2)
        self.assertEqual(next_win.status, Status.FINISHED)
