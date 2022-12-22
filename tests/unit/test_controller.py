"""Module to test MaintenanceController"""

from unittest import TestCase
from unittest.mock import MagicMock, patch, call

from datetime import datetime, timedelta
import pytz

from napps.kytos.maintenance.controllers import MaintenanceController
from napps.kytos.maintenance.models import MaintenanceWindow, MaintenanceWindows

class TestMaintenanceController(TestCase):
    """Test the MaintenanceController Class"""

    def setUp(self) -> None:
        self.controller = MaintenanceController(MagicMock())
        self.now = datetime.now(pytz.utc)
        self.window_dict = {
            'id': 'Test Window',
            'description': '',
            'start': self.now + timedelta(hours=1),
            'end': self.now + timedelta(hours=2),
            'status': 'pending',
            'switches': [],
            'interfaces': [],
            'links': [],
            'updated_at': self.now - timedelta(days=1),
            'inserted_at': self.now - timedelta(days=1),
        }
        self.window = MaintenanceWindow.construct(
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

    def test_bootstrap_indexes(self) -> None:
        """Check that the proper indexes were bootstrapped"""
        self.controller.bootstrap_indexes()
        windows = self.controller.windows
        expected_indexes = [
            call("maintenance.windows", [("id", 1)], unique=True),
        ]
        mock = self.controller.mongo.bootstrap_index
        indexes = mock.call_args_list
        self.assertEqual(indexes, expected_indexes)

    @patch('napps.kytos.maintenance.controllers.datetime')
    def test_insert_window(self, dt_class):
        """Test inserting a window."""
        now_func = dt_class.now
        now_func.return_value = self.now
        self.controller.insert_window(self.window)
        self.controller.windows.insert_one.assert_called_once_with(
            {
                **self.window_dict,
                'inserted_at': self.now,
                'updated_at': self.now,
            }
        )

    def test_update_window(self):
        """Test updating a window."""
        self.controller.update_window(self.window)
        dict_copy = self.window_dict.copy()
        del dict_copy['inserted_at']
        del dict_copy['updated_at']
        self.controller.windows.update_one.assert_called_once_with(
            {'id': self.window.id},
            [{
                '$set': {
                    **dict_copy,
                    'updated_at': '$$NOW',
                },
            }],
        )

    def test_get_window_1(self):
        """Test getting a window that exists."""
        mw_id = 'Test Window'
        self.controller.windows.find_one.return_value = self.window_dict
        result = self.controller.get_window(mw_id)
        self.assertEqual(result, self.window)

    def test_get_window_2(self):
        """Test getting a window that does not exist."""
        mw_id = 'Test Window'
        self.controller.windows.find_one.return_value = None
        result = self.controller.get_window(mw_id)
        self.assertEqual(result, None)

    def test_get_windows(self):
        """Test getting the set of windows."""
        self.controller.windows.find.return_value = [self.window_dict]
        expected = MaintenanceWindows.construct(__root__ = [self.window])
        result = self.controller.get_windows()
        self.assertEqual(result, expected)