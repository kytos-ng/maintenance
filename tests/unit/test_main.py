"""Tests for the main madule."""

from unittest import TestCase
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import json

import pytz

from tests.helpers import get_controller_mock
from napps.kytos.maintenance.main import Main
from napps.kytos.maintenance.models import MaintenanceWindow as MW

TIME_FMT = "%Y-%m-%dT%H:%M:%S"


class TestMain(TestCase):
    """Test the Main class of this NApp."""

    # pylint: disable=too-many-public-methods

    def setUp(self):
        """Initialize before tests are executed."""
        self.server_name_url = \
            'http://localhost:8181/api/kytos/maintenance'
        self.controller = get_controller_mock()
        self.napp = Main(self.controller)
        self.api = self.get_app_test_client(self.napp)

    @staticmethod
    def get_app_test_client(napp):
        """Return a flask api test client."""
        napp.controller.api_server.register_napp_endpoints(napp)
        return napp.controller.api_server.app.test_client()

    @patch('napps.kytos.maintenance.models.Scheduler.add')
    @patch('napps.kytos.maintenance.models.MaintenanceWindow.from_dict')
    def test_create_mw_case_1(self, from_dict_mock, sched_add_mock):
        """Test a successful case of the REST to create."""
        url = f'{self.server_name_url}'
        start = datetime.now(pytz.utc) + timedelta(days=1)
        end = start + timedelta(hours=2)
        from_dict_mock.return_value.id = '1234'
        from_dict_mock.return_value.start = start
        from_dict_mock.return_value.end = end
        from_dict_mock.return_value.items = [
            "00:00:00:00:00:00:02",
            MagicMock(interface=MagicMock(), tag=MagicMock())
        ]
        payload = {
            "start": start.strftime(TIME_FMT),
            "end": end.strftime(TIME_FMT),
            "items": [
                {
                    "interface_id": "00:00:00:00:00:00:00:03:3",
                    "tag": {
                        "tag_type": "VLAN",
                        "value": 241
                    }
                },
                "00:00:00:00:00:00:02"
            ]
        }
        response = self.api.post(url, data=json.dumps(payload),
                                 content_type='application/json')
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(current_data, {'mw_id': '1234'})
        sched_add_mock.assert_called_once_with(from_dict_mock.return_value)

    @patch('napps.kytos.maintenance.models.Scheduler.add')
    @patch('napps.kytos.maintenance.models.MaintenanceWindow.from_dict')
    def test_create_mw_case_2(self, from_dict_mock, sched_add_mock):
        """Test a fail case of the REST to create a maintenance window."""
        url = f'{self.server_name_url}'
        start = datetime.now(pytz.utc) + timedelta(days=1)
        end = start + timedelta(hours=2)
        from_dict_mock.return_value = None
        payload = {
            "start": start.strftime(TIME_FMT),
            "end": end.strftime(TIME_FMT),
            "items": [
                {
                    "interface_id": "00:00:00:00:00:00:00:03:3",
                    "tag": {
                        "tag_type": "VLAN",
                        "value": 241
                    }
                },
                "00:00:00:00:00:00:02"
            ]
        }
        response = self.api.post(url, data=json.dumps(payload),
                                 content_type='application/json')
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(current_data, 'One or more items are invalid')
        sched_add_mock.assert_not_called()

    @patch('napps.kytos.maintenance.models.Scheduler.add')
    @patch('napps.kytos.maintenance.models.MaintenanceWindow.from_dict')
    def test_create_mw_case_3(self, from_dict_mock, sched_add_mock):
        """Test a fail case of the REST to create a maintenance window."""
        url = f'{self.server_name_url}'
        start = datetime.now(pytz.utc) - timedelta(days=1)
        end = start + timedelta(hours=2)
        from_dict_mock.return_value.id = '1234'
        from_dict_mock.return_value.start = start
        from_dict_mock.return_value.end = end
        from_dict_mock.return_value.items = [
            "00:00:00:00:00:00:02",
            MagicMock(interface=MagicMock(), tag=MagicMock())
        ]
        payload = {
            "start": start.strftime(TIME_FMT),
            "end": end.strftime(TIME_FMT),
            "items": [
                {
                    "interface_id": "00:00:00:00:00:00:00:03:3",
                    "tag": {
                        "tag_type": "VLAN",
                        "value": 241
                    }
                },
                "00:00:00:00:00:00:02"
            ]
        }
        response = self.api.post(url, data=json.dumps(payload),
                                 content_type='application/json')
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(current_data, 'Start in the past not allowed')
        sched_add_mock.assert_not_called()

    @patch('napps.kytos.maintenance.models.Scheduler.add')
    @patch('napps.kytos.maintenance.models.MaintenanceWindow.from_dict')
    def test_create_mw_case_4(self, from_dict_mock, sched_add_mock):
        """Test a fail case of the REST to create a maintenance window."""
        url = f'{self.server_name_url}'
        start = datetime.now(pytz.utc) + timedelta(days=1)
        end = start - timedelta(hours=2)
        from_dict_mock.return_value.id = '1234'
        from_dict_mock.return_value.start = start
        from_dict_mock.return_value.end = end
        from_dict_mock.return_value.items = [
            "00:00:00:00:00:00:02",
            MagicMock(interface=MagicMock(), tag=MagicMock())
        ]
        payload = {
            "start": start.strftime(TIME_FMT),
            "end": end.strftime(TIME_FMT),
            "items": [
                {
                    "interface_id": "00:00:00:00:00:00:00:03:3",
                    "tag": {
                        "tag_type": "VLAN",
                        "value": 241
                    }
                },
                "00:00:00:00:00:00:02"
            ]
        }
        response = self.api.post(url, data=json.dumps(payload),
                                 content_type='application/json')
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(current_data, 'End before start not allowed')
        sched_add_mock.assert_not_called()

    @patch('napps.kytos.maintenance.models.MaintenanceWindow.as_dict')
    def test_get_mw_case_1(self, mw_as_dict_mock):
        """Test get all maintenance windows, empty list."""
        url = f'{self.server_name_url}'
        response = self.api.get(url)
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(current_data, [])
        mw_as_dict_mock.assert_not_called()

    @patch('napps.kytos.maintenance.models.MaintenanceWindow.as_dict')
    def test_get_mw_case_2(self, mw_as_dict_mock):
        """Test get all maintenance windows."""
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        start2 = datetime.now(pytz.utc) + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.napp.maintenances = {
            '1234': MW(start1, end1, self.controller, items=[
                '00:00:00:00:00:00:12:23'
            ]),
            '4567': MW(start2, end2, self.controller, items=[
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
        """Test get non-existent id."""
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        start2 = datetime.now(pytz.utc) + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.napp.maintenances = {
            '1234': MW(start1, end1, self.controller, items=[
                '00:00:00:00:00:00:12:23'
            ]),
            '4567': MW(start2, end2, self.controller, items=[
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
        """Test get existent id."""
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        start2 = datetime.now(pytz.utc) + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.napp.maintenances = {
            '1234': MW(start1, end1, self.controller, items=[
                '00:00:00:00:00:00:12:23'
            ]),
            '4567': MW(start2, end2, self.controller, items=[
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

    def test_remove_mw_case_1(self):
        """Test remove non-existent id."""
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        start2 = datetime.now(pytz.utc) + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.napp.maintenances = {
            '1234': MW(start1, end1, self.controller, items=[
                '00:00:00:00:00:00:12:23'
            ]),
            '4567': MW(start2, end2, self.controller, items=[
                '12:34:56:78:90:ab:cd:ef'
            ])
        }
        url = f'{self.server_name_url}/2345'
        response = self.api.delete(url)
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(current_data, {'response': 'Maintenance with id 2345 '
                                                    'not found'})

    @patch('napps.kytos.maintenance.models.Scheduler.remove')
    def test_remove_mw_case_2(self, sched_remove_mock):
        """Test remove existent id."""
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        start2 = datetime.now(pytz.utc) + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.napp.maintenances = {
            '1234': MW(start1, end1, self.controller, items=[
                '00:00:00:00:00:00:12:23'
            ]),
            '4567': MW(start2, end2, self.controller, items=[
                '12:34:56:78:90:ab:cd:ef'
            ])
        }
        url = f'{self.server_name_url}/1234'
        response = self.api.delete(url)
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(current_data, {'response': 'Maintenance with id 1234 '
                                                    'successfully removed'})
        sched_remove_mock.assert_called_once()
        self.assertEqual(len(self.napp.maintenances), 1)

    def test_update_mw_case_1(self):
        """Test update non-existent id."""
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        start2 = datetime.now(pytz.utc) + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.napp.maintenances = {
            '1234': MW(start1, end1, self.controller, items=[
                '00:00:00:00:00:00:12:23'
            ]),
            '4567': MW(start2, end2, self.controller, items=[
                '12:34:56:78:90:ab:cd:ef'
            ])
        }
        payload = {
            "start": start1.strftime(TIME_FMT),
        }
        url = f'{self.server_name_url}/2345'
        response = self.api.patch(url, data=json.dumps(payload),
                                  content_type='application/json')
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(current_data, {'response': 'Maintenance with id 2345 '
                                                    'not found'})

    def test_update_mw_case_2(self):
        """Test update no data."""
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        start2 = datetime.now(pytz.utc) + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.napp.maintenances = {
            '1234': MW(start1, end1, self.controller, items=[
                '00:00:00:00:00:00:12:23'
            ]),
            '4567': MW(start2, end2, self.controller, items=[
                '12:34:56:78:90:ab:cd:ef'
            ])
        }
        payload = {
            "start": start1.strftime(TIME_FMT),
        }
        url = f'{self.server_name_url}/1234'
        response = self.api.patch(url, data=json.dumps(payload),
                                  content_type='text/plain')
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 415)
        self.assertEqual(current_data,
                         'Bad request: The request do not have a json.')

    @patch('napps.kytos.maintenance.models.Scheduler.add')
    @patch('napps.kytos.maintenance.models.Scheduler.remove')
    @patch('napps.kytos.maintenance.models.MaintenanceWindow.update')
    def test_update_mw_case_3(self, mw_update_mock, sched_remove_mock,
                              sched_add_mock):
        """Test successful update."""
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        start2 = datetime.now(pytz.utc) + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.napp.maintenances = {
            '1234': MW(start1, end1, self.controller, items=[
                '00:00:00:00:00:00:12:23'
            ]),
            '4567': MW(start2, end2, self.controller, items=[
                '12:34:56:78:90:ab:cd:ef'
            ])
        }
        start_new = datetime.utcnow() + timedelta(days=1, hours=3)
        payload = {
            "start": start_new.strftime(TIME_FMT),
        }
        url = f'{self.server_name_url}/1234'
        response = self.api.patch(url, data=json.dumps(payload),
                                  content_type='application/json')
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(current_data,
                         {'response': 'Maintenance 1234 updated'})
        mw_update_mock.assert_called_once_with(payload)
        sched_add_mock.assert_called_once()
        sched_remove_mock.assert_called_once()

    @patch('napps.kytos.maintenance.models.MaintenanceWindow.update')
    def test_update_mw_case_4(self, mw_update_mock):
        """Test successful update."""
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        start2 = datetime.now(pytz.utc) + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.napp.maintenances = {
            '1234': MW(start1, end1, self.controller, items=[
                '00:00:00:00:00:00:12:23'
            ]),
            '4567': MW(start2, end2, self.controller, items=[
                '12:34:56:78:90:ab:cd:ef'
            ])
        }
        start_new = datetime.utcnow() - timedelta(days=1, hours=3)
        payload = {
            "start": start_new.strftime(TIME_FMT),
        }
        mw_update_mock.side_effect = ValueError('Start in the past not '
                                                'allowed.')
        url = f'{self.server_name_url}/1234'
        response = self.api.patch(url, data=json.dumps(payload),
                                  content_type='application/json')
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(current_data, 'Start in the past not allowed.')
        mw_update_mock.assert_called_once_with(payload)

    @patch('napps.kytos.maintenance.models.MaintenanceWindow.update')
    def test_update_mw_case_5(self, mw_update_mock):
        """Test successful update."""
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        start2 = datetime.now(pytz.utc) + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.napp.maintenances = {
            '1234': MW(start1, end1, self.controller, items=[
                '00:00:00:00:00:00:12:23'
            ]),
            '4567': MW(start2, end2, self.controller, items=[
                '12:34:56:78:90:ab:cd:ef'
            ])
        }
        start_new = datetime.utcnow() + timedelta(days=1, hours=3)
        end_new = start_new - timedelta(hours=5)
        payload = {
            "start": start_new.strftime(TIME_FMT),
            "end": end_new.strftime(TIME_FMT)
        }
        mw_update_mock.side_effect = ValueError('End before start not '
                                                'allowed.')
        url = f'{self.server_name_url}/1234'
        response = self.api.patch(url, data=json.dumps(payload),
                                  content_type='application/json')
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(current_data, 'End before start not allowed.')
        mw_update_mock.assert_called_once_with(payload)

    def test_end_mw_case_1(self):
        """Test method that finishes the maintenance now."""
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        start2 = datetime.now(pytz.utc) + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.napp.maintenances = {
            '1234': MW(start1, end1, self.controller, items=[
                '00:00:00:00:00:00:12:23'
            ]),
            '4567': MW(start2, end2, self.controller, items=[
                '12:34:56:78:90:ab:cd:ef'
            ])
        }
        url = f'{self.server_name_url}/2345/end'
        response = self.api.patch(url)
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(current_data,
                         {'response': 'Maintenance with id 2345 not found'})

    @patch('napps.kytos.maintenance.models.MaintenanceWindow.end_mw')
    def test_end_mw_case_2(self, end_mw_mock):
        """Test method that finishes the maintenance now."""
        start1 = datetime.now(pytz.utc) - timedelta(hours=1)
        end1 = start1 + timedelta(hours=6)
        start2 = datetime.now(pytz.utc) + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.napp.maintenances = {
            '1234': MW(start1, end1, self.controller, items=[
                '00:00:00:00:00:00:12:23'
            ]),
            '4567': MW(start2, end2, self.controller, items=[
                '12:34:56:78:90:ab:cd:ef'
            ])
        }
        url = f'{self.server_name_url}/1234/end'
        response = self.api.patch(url)
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(current_data,
                         {'response': 'Maintenance window 1234 finished.'})
        end_mw_mock.assert_called_once()

    def test_end_mw_case_3(self):
        """Test method that finishes the maintenance now."""
        start1 = datetime.now(pytz.utc) + timedelta(hours=1)
        end1 = start1 + timedelta(hours=6)
        start2 = datetime.now(pytz.utc) + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.napp.maintenances = {
            '1234': MW(start1, end1, self.controller, items=[
                '00:00:00:00:00:00:12:23'
            ]),
            '4567': MW(start2, end2, self.controller, items=[
                '12:34:56:78:90:ab:cd:ef'
            ])
        }
        url = f'{self.server_name_url}/1234/end'
        response = self.api.patch(url)
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(current_data,
                         {'response': 'Maintenance window 1234 has not yet '
                                      'started.'})

    def test_end_mw_case_4(self):
        """Test method that finishes the maintenance now."""
        start1 = datetime.now(pytz.utc) - timedelta(hours=5)
        end1 = start1 + timedelta(hours=4)
        start2 = datetime.now(pytz.utc) + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.napp.maintenances = {
            '1234': MW(start1, end1, self.controller, items=[
                '00:00:00:00:00:00:12:23'
            ]),
            '4567': MW(start2, end2, self.controller, items=[
                '12:34:56:78:90:ab:cd:ef'
            ])
        }
        url = f'{self.server_name_url}/1234/end'
        response = self.api.patch(url)
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(current_data,
                         {'response': 'Maintenance window 1234 has already '
                                      'finished.'})
