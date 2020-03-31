from unittest import TestCase
from unittest.mock import patch
from datetime import datetime, timedelta
import json
from tests.helpers import get_controller_mock
from napps.kytos.maintenance.main import Main
from napps.kytos.maintenance.models import MaintenanceWindow as MW

TIME_FMT = "%Y-%m-%dT%H:%M:%S"


class TestMain(TestCase):
    """Test the Main class of this NApp."""

    def setUp(self):
        """Initialization before tests are executed."""
        self.server_name_url = \
            'http://localhost:8181/api/kytos/maintenance'
        self.napp = Main(get_controller_mock())
        self.api = self.get_app_test_client(self.napp)

    @staticmethod
    def get_app_test_client(napp):
        """Return a flask api test client."""
        napp.controller.api_server.register_napp_endpoints(napp)
        return napp.controller.api_server.app.test_client()

    @patch('napps.kytos.maintenance.models.MaintenanceWindow.as_dict')
    def test_get_mw_case_1(self, mw_as_dict_mock):
        """Test get all maintenance windows, empty list"""
        url = f'{self.server_name_url}'
        response = self.api.get(url)
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(current_data, [])
        mw_as_dict_mock.assert_not_called()

    @patch('napps.kytos.maintenance.models.MaintenanceWindow.as_dict')
    def test_get_mw_case_2(self, mw_as_dict_mock):
        """Test get all maintenance windows"""
        start1 = datetime.now() + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        start2 = datetime.now() + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.napp.maintenances = {
            '1234': MW(start1, end1, items=[
                '00:00:00:00:00:00:12:23'
            ]),
            '4567': MW(start2, end2, items=[
                '12:34:56:78:90:ab:cd:ef'
            ])
        }
        mw_dict = [
            {
                'id': '1234',
                'start': start1.strftime(TIME_FMT),
                'end': end1.strftime(TIME_FMT),
                'items': [
                    '00:00:00:00:00:00:12:23'
                ]
            },
            {
                'id': '4567',
                'start': start2.strftime(TIME_FMT),
                'end': end2.strftime(TIME_FMT),
                'items': [
                    '12:34:56:78:90:ab:cd:ef'
                ]
            }
        ]
        mw_as_dict_mock.side_effect = mw_dict
        url = f'{self.server_name_url}'
        response = self.api.get(url)
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(current_data, mw_dict)
        self.assertEqual(mw_as_dict_mock.call_count, 2)

    @patch('napps.kytos.maintenance.models.MaintenanceWindow.as_dict')
    def test_get_mw_case_3(self, mw_as_dict_mock):
        """Test get non-existent id"""
        start1 = datetime.now() + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        start2 = datetime.now() + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.napp.maintenances = {
            '1234': MW(start1, end1, items=[
                '00:00:00:00:00:00:12:23'
            ]),
            '4567': MW(start2, end2, items=[
                '12:34:56:78:90:ab:cd:ef'
            ])
        }
        url = f'{self.server_name_url}/2345'
        response = self.api.get(url)
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(current_data, {'response': 'Maintenance with id 2345 '
                                                    'not found'})
        mw_as_dict_mock.assert_not_called()

    @patch('napps.kytos.maintenance.models.MaintenanceWindow.as_dict')
    def test_get_mw_case_4(self, mw_as_dict_mock):
        """Test get existent id"""
        start1 = datetime.now() + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        start2 = datetime.now() + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.napp.maintenances = {
            '1234': MW(start1, end1, items=[
                '00:00:00:00:00:00:12:23'
            ]),
            '4567': MW(start2, end2, items=[
                '12:34:56:78:90:ab:cd:ef'
            ])
        }
        mw_dict = {
            'id': '4567',
            'start': start2.strftime(TIME_FMT),
            'end': end2.strftime(TIME_FMT),
            'items': [
                '12:34:56:78:90:ab:cd:ef'
            ]
        }
        mw_as_dict_mock.return_value = mw_dict
        url = f'{self.server_name_url}/4567'
        response = self.api.get(url)
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(current_data, mw_dict)
        mw_as_dict_mock.assert_called_once()
