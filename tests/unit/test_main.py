"""Tests for the main madule."""

from unittest import TestCase
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import json

import pytz

from kytos.lib.helpers import get_controller_mock
from napps.kytos.maintenance.main import Main
from napps.kytos.maintenance.models import MaintenanceWindow as MW
from napps.kytos.maintenance.models import MaintenanceWindows

TIME_FMT = "%Y-%m-%dT%H:%M:%S%z"


class TestMain(TestCase):
    """Test the Main class of this NApp."""

    # pylint: disable=too-many-public-methods

    def setUp(self):
        """Initialize before tests are executed."""
        self.server_name_url = \
            'http://localhost:8181/api/kytos/maintenance/v1'
        self.controller = get_controller_mock()
        self.scheduler = MagicMock()
        with patch('napps.kytos.maintenance.models.Scheduler.new_scheduler') as new_scheduler:
            new_scheduler.return_value = self.scheduler
            self.napp = Main(self.controller)
        self.api = self.get_app_test_client(self.napp)
        self.maxDiff = None

    @staticmethod
    def get_app_test_client(napp):
        """Return a flask api test client."""
        napp.controller.api_server.register_napp_endpoints(napp)
        return napp.controller.api_server.app.test_client()

    def test_create_mw_case_1(self):
        """Test a successful case of the REST to create."""
        url = f'{self.server_name_url}'
        start = datetime.now(pytz.utc) + timedelta(days=1)
        end = start + timedelta(hours=2)
        payload = {
            'id': '1234',
            "start": start.strftime(TIME_FMT),
            "end": end.strftime(TIME_FMT),
            "switches": [
                "00:00:00:00:00:00:02",
            ],
            'interfaces': [
                "00:00:00:00:00:00:00:03:3",
            ],
        }
        response = self.api.post(url, data=json.dumps(payload),
                                 content_type='application/json')
        current_data = json.loads(response.data)
        self.scheduler.add.assert_called_once_with(
            MW.construct(
                id = '1234',
                start = start.replace(microsecond=0),
                end = end.replace(microsecond=0),
                switches = ['00:00:00:00:00:00:02'],
                interfaces = ['00:00:00:00:00:00:00:03:3']
            ),
            force = False
        )
        self.assertEqual(current_data, {'mw_id': '1234'})
        self.assertEqual(response.status_code, 201)

    def test_create_mw_case_2(self):
        """Test a fail case of the REST to create a maintenance window."""
        url = f'{self.server_name_url}'
        start = datetime.now(pytz.utc) + timedelta(days=1)
        end = start + timedelta(hours=2)
        payload = {
            "switches": [
                "00:00:00:00:00:00:02",
            ],
            'interfaces': [
                "00:00:00:00:00:00:00:03:3",
            ],
        }
        response = self.api.post(url, data=json.dumps(payload),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.scheduler.add.assert_not_called()

    def test_create_mw_case_3(self):
        """Test a fail case of the REST to create a maintenance window."""
        url = f'{self.server_name_url}'
        start = datetime.now(pytz.utc) - timedelta(days=1)
        end = start + timedelta(hours=2)
        payload = {
            "start": start.strftime(TIME_FMT),
            "end": end.strftime(TIME_FMT),
            "switches": [
                "00:00:00:00:00:00:02",
            ],
            'interfaces': [
                "00:00:00:00:00:00:00:03:3",
            ],
        }
        response = self.api.post(url, data=json.dumps(payload),
                                 content_type='application/json')
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(current_data['description'],
                         'Start in the past not allowed')
        self.scheduler.add.assert_not_called()

    def test_create_mw_case_4(self):
        """Test a fail case of the REST to create a maintenance window."""
        url = f'{self.server_name_url}'
        start = datetime.now(pytz.utc) + timedelta(days=1)
        end = start - timedelta(hours=2)
        payload = {
            "start": start.strftime(TIME_FMT),
            "end": end.strftime(TIME_FMT),
            "start": start.strftime(TIME_FMT),
            "end": end.strftime(TIME_FMT),
            "switches": [
                "00:00:00:00:00:00:02",
            ],
            'interfaces': [
                "00:00:00:00:00:00:00:03:3",
            ],
        }
        response = self.api.post(url, data=json.dumps(payload),
                                 content_type='application/json')
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(current_data['description'],
                         'End before start not allowed')
        self.scheduler.add.assert_not_called()

    def test_get_mw_case_1(self):
        """Test get all maintenance windows, empty list."""
        self.scheduler.list_maintenances.return_value = MaintenanceWindows.construct(__root__ = [])
        url = f'{self.server_name_url}'
        response = self.api.get(url)
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(current_data, [])
        self.scheduler.list_maintenances.assert_called_once()

    def test_get_mw_case_2(self):
        """Test get all maintenance windows."""
        now = datetime.now(pytz.utc)
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        start2 = datetime.now(pytz.utc) + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.scheduler.list_maintenances.return_value = MaintenanceWindows.construct(
            __root__ = [
            MW.construct(
                id = '1234',
                start = start1.replace(microsecond=0),
                end = end1.replace(microsecond=0),
                switches = [
                    '00:00:00:00:00:00:12:23'
                ],
                description = '',
                links = [],
                interfaces = [],
                status = 'pending',
                updated_at = now.replace(microsecond=0),
                inserted_at = now.replace(microsecond=0),
            ),
            MW.construct(
                id = '4567',
                start = start2.replace(microsecond=0),
                end = end2.replace(microsecond=0),
                switches = [
                    '12:34:56:78:90:ab:cd:ef'
                ],
                description = '',
                links = [],
                interfaces = [],
                status = 'pending',
                updated_at = now.replace(microsecond=0),
                inserted_at = now.replace(microsecond=0),
            ),
        ])
        mw_dict = [
            {
                'id': '1234',
                'start': start1.strftime(TIME_FMT),
                'end': end1.strftime(TIME_FMT),
                'switches': [
                    '00:00:00:00:00:00:12:23'
                ],
                'description': '',
                'links': [],
                'interfaces': [],
                'status': 'pending',
                'updated_at': now.strftime(TIME_FMT),
                'inserted_at': now.strftime(TIME_FMT),
            },
            {
                'id': '4567',
                'start': start2.strftime(TIME_FMT),
                'end': end2.strftime(TIME_FMT),
                'switches': [
                    '12:34:56:78:90:ab:cd:ef'
                ],
                'description': '',
                'links': [],
                'interfaces': [],
                'status': 'pending',
                'updated_at': now.strftime(TIME_FMT),
                'inserted_at': now.strftime(TIME_FMT),
            }
        ]

        url = f'{self.server_name_url}'
        response = self.api.get(url)
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(current_data, mw_dict)
        self.scheduler.list_maintenances.assert_called_once()

    def test_get_mw_case_3(self):
        """Test get non-existent id."""
        self.scheduler.get_maintenance.return_value = None
        url = f'{self.server_name_url}/2345'
        response = self.api.get(url)
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(current_data['description'],
                         'Maintenance with id 2345 not found')
        self.scheduler.get_maintenance.assert_called_once_with('2345')

    def test_get_mw_case_4(self):
        """Test get existent id."""
        now = datetime.now(pytz.utc)
        start2 = datetime.now(pytz.utc) + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.scheduler.get_maintenance.return_value = MW.construct(
            id = '4567',
            start = start2.replace(microsecond=0),
            end = end2.replace(microsecond=0),
            switches = [
                '12:34:56:78:90:ab:cd:ef'
            ],
            updated_at = now.replace(microsecond=0),
            inserted_at = now.replace(microsecond=0),
        )
        mw_dict = {
            'id': '4567',
            'start': start2.strftime(TIME_FMT),
            'end': end2.strftime(TIME_FMT),
            'switches': [
                '12:34:56:78:90:ab:cd:ef'
            ],
            'description': '',
            'links': [],
            'interfaces': [],
            'status': 'pending',
            'updated_at': now.strftime(TIME_FMT),
            'inserted_at': now.strftime(TIME_FMT),
        }
        url = f'{self.server_name_url}/4567'
        response = self.api.get(url)
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(current_data, mw_dict)
        self.scheduler.get_maintenance.assert_called_once_with('4567')

    def test_remove_mw_case_1(self):
        """Test remove non-existent id."""
        self.scheduler.get_maintenance.return_value = None
        url = f'{self.server_name_url}/2345'
        response = self.api.delete(url)
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(current_data['description'],
                         'Maintenance with id 2345 not found')
        self.scheduler.get_maintenance.assert_called_once_with('2345')
        self.scheduler.remove.assert_not_called()

    def test_remove_mw_case_2(self):
        """Test remove existent id."""
        start1 = datetime.now(pytz.utc) + timedelta(hours=1)
        end1 = start1 + timedelta(hours=6)
        self.scheduler.get_maintenance.return_value = MW.construct(
            id = '1234',
            start = start1.replace(microsecond=0),
            end = end1.replace(microsecond=0),
            switches = [
                '00:00:00:00:00:00:12:23'
            ],
        )
        url = f'{self.server_name_url}/1234'
        response = self.api.delete(url)
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(current_data, {'response': 'Maintenance with id 1234 '
                                                    'successfully removed'})
        self.scheduler.get_maintenance.assert_called_once_with('1234')
        self.scheduler.remove.assert_called_once_with('1234')

    def test_remove_mw_case_3(self):
        """Test remove existent id."""
        start1 = datetime.now(pytz.utc) - timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        self.scheduler.get_maintenance.return_value = MW.construct(
            id = '1234',
            start = start1.replace(microsecond=0),
            end = end1.replace(microsecond=0),
            switches = [
                '00:00:00:00:00:00:12:23'
            ],
            status = 'running',
        )
        url = f'{self.server_name_url}/1234'
        response = self.api.delete(url)
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(current_data['description'],
                         'Deleting a running maintenance is not allowed')
        self.scheduler.get_maintenance.assert_called_once_with('1234')
        self.scheduler.remove.assert_not_called()

    def test_update_mw_case_1(self):
        """Test update non-existent id."""
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        self.scheduler.get_maintenance.return_value = None
        payload = {
            "start": start1.strftime(TIME_FMT),
        }
        url = f'{self.server_name_url}/2345'
        response = self.api.patch(url, data=json.dumps(payload),
                                  content_type='application/json')
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(current_data['description'],
                         'Maintenance with id 2345 not found')
        self.scheduler.update.assert_not_called()

    def test_update_mw_case_2(self):
        """Test update no data."""
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        payload = {
            "start": start1.strftime(TIME_FMT),
        }
        url = f'{self.server_name_url}/1234'
        response = self.api.patch(url, data=json.dumps(payload),
                                  content_type='text/plain')
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 415)
        self.assertEqual(current_data['description'],
                         'The request does not have a json')
        self.scheduler.update.assert_not_called()

    def test_update_mw_case_3(self):
        """Test successful update."""
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        self.scheduler.get_maintenance.return_value = MW.construct(
            id = '1234',
            start = start1.replace(microsecond=0),
            end = end1.replace(microsecond=0),
            switches = [
                '00:00:00:00:00:00:12:23'
            ],
        )
        start_new = datetime.now(pytz.utc) + timedelta(days=1, hours=3)
        payload = {
            "start": start_new.strftime(TIME_FMT),
        }
        url = f'{self.server_name_url}/1234'
        response = self.api.patch(url, data=json.dumps(payload),
                                  content_type='application/json')
        current_data = json.loads(response.data)
        self.assertEqual(current_data,
                         {'response': 'Maintenance 1234 updated'})
        self.assertEqual(response.status_code, 200)
        self.scheduler.get_maintenance.assert_called_once_with('1234')
        self.scheduler.update.assert_called_once_with(
            MW.construct(
                id = '1234',
                start = start_new.replace(microsecond=0),
                end = end1.replace(microsecond=0),
                switches = [
                    '00:00:00:00:00:00:12:23'
                ],
            )
        )

    def test_update_mw_case_4(self):
        """Test successful update."""
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        self.scheduler.get_maintenance.return_value = MW.construct(
            id = '1234',
            start = start1.replace(microsecond=0),
            end = end1.replace(microsecond=0),
            switches = [
                '00:00:00:00:00:00:12:23'
            ],
        )
        start_new = datetime.now(pytz.utc) - timedelta(days=1, hours=3)
        payload = {
            "start": start_new.strftime(TIME_FMT),
        }
        url = f'{self.server_name_url}/1234'
        response = self.api.patch(url, data=json.dumps(payload),
                                  content_type='application/json')
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(current_data['description'],
                         'Start in the past not allowed')
        self.scheduler.get_maintenance.assert_called_once_with('1234')
        self.scheduler.update.assert_not_called()

    def test_update_mw_case_5(self):
        """Test successful update."""
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        self.scheduler.get_maintenance.return_value = MW.construct(
            id = '1234',
            start = start1.replace(microsecond=0),
            end = end1.replace(microsecond=0),
            switches = [
                '00:00:00:00:00:00:12:23'
            ],
        )
        start_new = datetime.now(pytz.utc) + timedelta(days=1, hours=3)
        end_new = start_new - timedelta(hours=5)
        payload = {
            "start": start_new.strftime(TIME_FMT),
            "end": end_new.strftime(TIME_FMT)
        }
        url = f'{self.server_name_url}/1234'
        response = self.api.patch(url, data=json.dumps(payload),
                                  content_type='application/json')
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(current_data['description'],
                         'End before start not allowed')
        self.scheduler.get_maintenance.assert_called_once_with('1234')
        self.scheduler.update.assert_not_called()

    def test_update_mw_case_6(self):
        """Test successful update."""
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        self.scheduler.get_maintenance.return_value = MW.construct(
            id = '1234',
            start = start1.replace(microsecond=0),
            end = end1.replace(microsecond=0),
            switches = [
                '00:00:00:00:00:00:12:23'
            ],
        )
        start_new = datetime.now(pytz.utc) + timedelta(days=1, hours=3)
        payload = {
            "start": start_new.strftime(TIME_FMT),
            "switches": [],
            'interfaces': [],
            'links': [],
        }

        url = f'{self.server_name_url}/1234'
        response = self.api.patch(url, data=json.dumps(payload),
                                  content_type='application/json')
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(current_data['description'],
                         'At least one item must be provided')
        self.scheduler.get_maintenance.assert_called_once_with('1234')
        self.scheduler.update.assert_not_called()

    
    def test_update_mw_case_7(self):
        """Test successful update."""
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        self.scheduler.get_maintenance.return_value = MW.construct(
            id = '1234',
            start = start1.replace(microsecond=0),
            end = end1.replace(microsecond=0),
            switches = [
                '00:00:00:00:00:00:12:23'
            ],
        )
        payload = {
            'status': 'running',
        }
        url = f'{self.server_name_url}/1234'
        response = self.api.patch(url, data=json.dumps(payload),
                                  content_type='application/json')
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(current_data['description'],
                         'Updating a maintenance status is not allowed')
        self.scheduler.update.assert_not_called()

    def test_end_mw_case_1(self):
        """Test method that finishes the maintenance now."""
        self.scheduler.get_maintenance.return_value = None
        url = f'{self.server_name_url}/2345/end'
        response = self.api.patch(url)
        current_data = json.loads(response.data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(current_data['description'],
                         'Maintenance with id 2345 not found')

    def test_end_mw_case_2(self):
        """Test method that finishes the maintenance now."""
        start1 = datetime.now(pytz.utc) - timedelta(hours=1)
        end1 = start1 + timedelta(hours=6)
        self.scheduler.get_maintenance.return_value = MW.construct(
            id = '1234',
            start = start1.replace(microsecond=0),
            end = end1.replace(microsecond=0),
            switches = [
                '00:00:00:00:00:00:12:23'
            ],
            status = 'running',
        )
        url = f'{self.server_name_url}/1234/end'
        response = self.api.patch(url)
        current_data = json.loads(response.data)
        self.scheduler.get.asssert_called_once_with('1234')
        self.scheduler.end_maintenance_early.assert_called_once_with('1234')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(current_data,
                         {'response': 'Maintenance window 1234 finished'})

    def test_end_mw_case_3(self):
        """Test method that finishes the maintenance now."""
        start1 = datetime.now(pytz.utc) + timedelta(hours=1)
        end1 = start1 + timedelta(hours=6)
        self.scheduler.get_maintenance.return_value = MW.construct(
            id = '1234',
            start = start1.replace(microsecond=0),
            end = end1.replace(microsecond=0),
            switches = [
                '00:00:00:00:00:00:12:23'
            ],
            status = 'pending',
        )
        url = f'{self.server_name_url}/1234/end'
        response = self.api.patch(url)
        current_data = json.loads(response.data)
        self.scheduler.get.asssert_called_once_with('1234')
        self.scheduler.end_maintenance_early.assert_not_called()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(current_data['description'],
                         'Maintenance window 1234 has not yet started')

    def test_end_mw_case_4(self):
        """Test method that finishes the maintenance now."""
        start1 = datetime.now(pytz.utc) - timedelta(hours=5)
        end1 = start1 + timedelta(hours=4)
        self.scheduler.get_maintenance.return_value = MW.construct(
            id = '1234',
            start = start1.replace(microsecond=0),
            end = end1.replace(microsecond=0),
            switches = [
                '00:00:00:00:00:00:12:23'
            ],
            status = 'finished',
        )
        url = f'{self.server_name_url}/1234/end'
        response = self.api.patch(url)
        current_data = json.loads(response.data)
        self.scheduler.get.asssert_called_once_with('1234')
        self.scheduler.end_maintenance_early.assert_not_called()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(current_data['description'],
                         'Maintenance window 1234 has already finished')

    def test_extend_case_1(self):
        """Test successful extension."""
        start1 = datetime.now(pytz.utc) - timedelta(hours=3)
        end1 = start1 + timedelta(hours=4)
        self.scheduler.get_maintenance.return_value = MW.construct(
            id = '1234',
            start = start1.replace(microsecond=0),
            end = end1.replace(microsecond=0),
            switches = [
                '00:00:00:00:00:00:12:23'
            ],
            status = 'running',
        )
        url = f'{self.server_name_url}/1234/extend'
        payload = {
            'minutes': 45
        }
        response = self.api.patch(url, data=json.dumps(payload),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.scheduler.get_maintenance.called_with('1234')
        self.scheduler.update.assert_called_with(MW.construct(
            id = '1234',
            start = start1.replace(microsecond=0),
            end = end1.replace(microsecond=0) + timedelta(minutes=45),
            switches = [
                '00:00:00:00:00:00:12:23'
            ],
            status = 'running',
        ))

    def test_extend_case_2(self):
        """Test no payload error."""
        url = f'{self.server_name_url}/1234/extend'
        response = self.api.patch(url)
        self.assertEqual(response.status_code, 415)
        current_data = json.loads(response.data)
        self.assertEqual(current_data['description'],
                         'The request does not have a json')
        self.scheduler.update.assert_not_called()

    def test_extend_case_3(self):
        """Test payload without minutes."""
        url = f'{self.server_name_url}/1234/extend'
        payload = {
            'seconds': 240
        }
        response = self.api.patch(url, data=json.dumps(payload),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        current_data = json.loads(response.data)
        self.assertEqual(current_data['description'],
                         'Minutes of extension must be sent')
        self.scheduler.update.assert_not_called()

    def test_extend_case_4(self):
        """Test no integer extension minutes."""
        url = f'{self.server_name_url}/1234/extend'
        payload = {
            'minutes': '240'
        }
        response = self.api.patch(url, data=json.dumps(payload),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        current_data = json.loads(response.data)
        self.assertEqual(current_data['description'],
                         'Minutes of extension must be integer')
        self.scheduler.update.assert_not_called()

    def test_extend_case_5(self):
        """Test maintenance did not start."""
        start1 = datetime.now(pytz.utc) + timedelta(hours=3)
        end1 = start1 + timedelta(hours=4)
        self.scheduler.get_maintenance.return_value = MW.construct(
            id = '1234',
            start = start1.replace(microsecond=0),
            end = end1.replace(microsecond=0),
            switches = [
                '00:00:00:00:00:00:12:23'
            ],
            status = 'pending',
        )
        url = f'{self.server_name_url}/1234/extend'
        payload = {
            'minutes': 240
        }
        response = self.api.patch(url, data=json.dumps(payload),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        current_data = json.loads(response.data)
        self.assertEqual(current_data['description'],
                         'Maintenance window 1234 has not yet started')
        self.scheduler.get_maintenance.assert_called_once_with('1234')
        self.scheduler.update.assert_not_called()

    def test_extend_case_6(self):
        """Test maintenance already finished."""
        start1 = datetime.now(pytz.utc) - timedelta(hours=3)
        end1 = start1 + timedelta(hours=2)
        self.scheduler.get_maintenance.return_value = MW.construct(
            id = '1234',
            start = start1.replace(microsecond=0),
            end = end1.replace(microsecond=0),
            switches = [
                '00:00:00:00:00:00:12:23'
            ],
            status = 'finished',
        )
        url = f'{self.server_name_url}/1234/extend'
        payload = {
            'minutes': 240
        }
        response = self.api.patch(url, data=json.dumps(payload),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        current_data = json.loads(response.data)
        self.assertEqual(current_data['description'],
                         'Maintenance window 1234 has already finished')
        self.scheduler.get_maintenance.assert_called_once_with('1234')
        self.scheduler.update.assert_not_called()

    def test_extend_case_7(self):
        """Test no maintenace found."""
        self.scheduler.get_maintenance.return_value = None
        url = f'{self.server_name_url}/1235/extend'
        payload = {
            'minutes': 240
        }
        response = self.api.patch(url, data=json.dumps(payload),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 404)
        current_data = json.loads(response.data)
        self.assertEqual(current_data['description'],
                         'Maintenance with id 1235 not found')
        self.scheduler.get_maintenance.assert_called_once_with('1235')
        self.scheduler.update.assert_not_called()
