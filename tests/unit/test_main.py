"""Tests for the main madule."""
import asyncio
from unittest.mock import patch, call, MagicMock
from datetime import datetime, timedelta

import pytz
import pytest

from kytos.lib.helpers import get_controller_mock, get_test_client
from napps.kytos.maintenance.main import Main
from napps.kytos.maintenance.models import MaintenanceWindow as MW
from napps.kytos.maintenance.models import MaintenanceWindows

TIME_FMT = "%Y-%m-%dT%H:%M:%S%z"


class TestMain:
    """Test the Main class of this NApp."""

    # pylint: disable=too-many-public-methods

    def setup_method(self):
        """Initialize before tests are executed."""
        self.controller = get_controller_mock()
        self.controller.switches = MagicMock()
        self.scheduler = MagicMock()
        new_sched = (
            "napps.kytos.maintenance.managers.MaintenanceScheduler.new_scheduler"
        )
        with patch(new_sched) as new_scheduler:
            new_scheduler.return_value = self.scheduler
            self.napp = Main(self.controller)
        self.api = get_test_client(self.controller, self.napp)
        self.maxDiff = None
        self.base_endpoint = "kytos/maintenance/v1"

    async def test_create_mw_case_1(self):
        """Test a successful case of the REST to create."""
        self.napp.controller.loop = asyncio.get_running_loop()
        url = f"{self.base_endpoint}"
        start = datetime.now(pytz.utc) + timedelta(days=1)
        end = start + timedelta(hours=2)
        self.controller.switches = MagicMock()
        self.controller.get_interface_by_id = MagicMock()
        self.controller.links = MagicMock()
        switches = {"00:00:00:00:00:00:00:02": 1, "00:00:00:00:00:00:00:03": 2}
        interfaces = {"00:00:00:00:00:00:00:03:3": 1, "00:00:00:00:00:00:00:02:1": 2}
        links = {
            "cf0f4071be426b3f745027f5d22bc61f8312ae86293c9b28e7e66015607a9260": 1,
            "4d42dc0852278accac7d9df15418f6d921db160b13d674029a87cef1b5f67f30": 2,
        }
        self.controller.switches.get.side_effect = switches.get
        get_interface_side_effect = lambda interface_id: interfaces.get(interface_id)
        self.controller.get_interface_by_id.side_effect = get_interface_side_effect
        self.controller.links.get.side_effect = links.get
        payload = {
            "start": start.strftime(TIME_FMT),
            "end": end.strftime(TIME_FMT),
            "switches": ["00:00:00:00:00:00:00:02", "00:00:00:00:00:00:00:03"],
            "interfaces": ["00:00:00:00:00:00:00:03:3", "00:00:00:00:00:00:00:02:1"],
            "links": [
                "cf0f4071be426b3f745027f5d22bc61f8312ae86293c9b28e7e66015607a9260",
                "4d42dc0852278accac7d9df15418f6d921db160b13d674029a87cef1b5f67f30",
            ],
        }
        response = await self.api.post(url, json=payload)
        current_data = response.json()
        assert response.status_code == 201, current_data
        switch_calls = [
            call("00:00:00:00:00:00:00:02"),
            call("00:00:00:00:00:00:00:03"),
        ]
        self.controller.switches.get.assert_has_calls(switch_calls)
        interface_calls = [
            call("00:00:00:00:00:00:00:03:3"),
            call("00:00:00:00:00:00:00:02:1"),
        ]
        self.controller.get_interface_by_id.assert_has_calls(interface_calls)
        link_calls = [
            call("cf0f4071be426b3f745027f5d22bc61f8312ae86293c9b28e7e66015607a9260"),
            call("4d42dc0852278accac7d9df15418f6d921db160b13d674029a87cef1b5f67f30"),
        ]
        self.controller.links.get.assert_has_calls(
            link_calls
        )
        args, kwargs = self.scheduler.add.call_args
        window: MW = args[0]

        assert window.start == start.replace(microsecond=0)
        assert window.end == end.replace(microsecond=0)
        assert window.switches == ["00:00:00:00:00:00:00:02", "00:00:00:00:00:00:00:03"]
        assert window.interfaces == [
            "00:00:00:00:00:00:00:03:3",
            "00:00:00:00:00:00:00:02:1",
        ]
        assert window.links == [
            "cf0f4071be426b3f745027f5d22bc61f8312ae86293c9b28e7e66015607a9260",
            "4d42dc0852278accac7d9df15418f6d921db160b13d674029a87cef1b5f67f30",
        ]

        assert current_data == {"mw_id": window.id}

    async def test_create_mw_case_2(self):
        """Test a successful case of the REST to create."""
        self.napp.controller.loop = asyncio.get_running_loop()
        url = f"{self.base_endpoint}"
        start = datetime.now(pytz.utc) + timedelta(days=1)
        end = start + timedelta(hours=2)
        self.controller.switches = MagicMock()
        switches = {"00:00:00:00:00:00:00:01": 1}
        self.controller.switches.get.side_effect = switches.get
        payload = {
            "start": start.strftime(TIME_FMT),
            "end": end.strftime(TIME_FMT),
            "switches": [
                "00:00:00:00:00:00:00:01",
            ],
        }
        response = await self.api.post(url, json=payload)
        current_data = response.json()
        assert response.status_code == 201, current_data
        self.controller.switches.get.assert_called_with("00:00:00:00:00:00:00:01")
        args, kwargs = self.scheduler.add.call_args
        window: MW = args[0]

        assert window.start == start.replace(microsecond=0)
        assert window.end == end.replace(microsecond=0)
        assert window.switches == ["00:00:00:00:00:00:00:01"]
        assert window.interfaces == []
        assert window.links == []

        assert current_data == {"mw_id": window.id}

    async def test_create_mw_case_3(self):
        """Test a successful case of the REST to create."""
        self.napp.controller.loop = asyncio.get_running_loop()
        url = f"{self.base_endpoint}"
        start = datetime.now(pytz.utc) + timedelta(days=1)
        end = start + timedelta(hours=2)
        self.controller.get_interface_by_id = MagicMock()
        interfaces = {"00:00:00:00:00:00:00:01:1": 1}
        get_interface_side_effect = lambda interface_id: interfaces.get(interface_id)
        self.controller.get_interface_by_id.side_effect = get_interface_side_effect
        payload = {
            "id": "some_mw",
            "description": "some_mw",
            "start": start.strftime(TIME_FMT),
            "end": end.strftime(TIME_FMT),
            "interfaces": [
                "00:00:00:00:00:00:00:01:1",
            ],
        }
        response = await self.api.post(url, json=payload)
        current_data = response.json()
        assert response.status_code == 201, current_data
        self.controller.get_interface_by_id.assert_called_with(
            "00:00:00:00:00:00:00:01:1"
        )
        assert response.status_code == 201, current_data
        args, kwargs = self.scheduler.add.call_args
        response = await self.api.get(f"{url}/some_mw")
        window: MW = args[0]

        assert window.start == start.replace(microsecond=0)
        assert window.end == end.replace(microsecond=0)
        assert window.switches == []
        assert window.interfaces == ["00:00:00:00:00:00:00:01:1"]
        assert window.links == []

        assert current_data == {"mw_id": "some_mw"}

    async def test_create_mw_case_4(self):
        """Test a successful case of the REST to create."""
        self.napp.controller.loop = asyncio.get_running_loop()
        url = f"{self.base_endpoint}"
        start = datetime.now(pytz.utc) + timedelta(days=1)
        end = start + timedelta(hours=2)
        self.controller.links = MagicMock()
        links = {"cf0f4071be426b3f745027f5d22bc61f8312ae86293c9b28e7e66015607a9260": 1}
        self.controller.links.get.side_effect = links.get
        payload = {
            "start": start.strftime(TIME_FMT),
            "end": end.strftime(TIME_FMT),
            "links": [
                "cf0f4071be426b3f745027f5d22bc61f8312ae86293c9b28e7e66015607a9260",
            ],
        }
        response = await self.api.post(url, json=payload)
        current_data = response.json()
        assert response.status_code == 201, current_data
        self.controller.links.get.assert_called_with(
            "cf0f4071be426b3f745027f5d22bc61f8312ae86293c9b28e7e66015607a9260"
        )
        assert response.status_code == 201, current_data
        args, kwargs = self.scheduler.add.call_args
        window: MW = args[0]

        assert window.start == start.replace(microsecond=0)
        assert window.end == end.replace(microsecond=0)
        assert window.switches == []
        assert window.interfaces == []
        assert window.links == [
            "cf0f4071be426b3f745027f5d22bc61f8312ae86293c9b28e7e66015607a9260"
        ]

        assert current_data == {"mw_id": window.id}

    async def test_create_mw_case_5(self):
        """Test a fail case of the REST to create a maintenance window."""
        self.napp.controller.loop = asyncio.get_running_loop()
        url = f"{self.base_endpoint}"
        payload = {
            "switches": [
                "00:00:00:00:00:00:02",
            ],
            "interfaces": [
                "00:00:00:00:00:00:00:03:3",
            ],
        }
        response = await self.api.post(url, json=payload)
        assert response.status_code == 400
        self.scheduler.add.assert_not_called()

    async def test_create_mw_case_6(self):
        """Test a fail case of the REST to create a maintenance window."""
        self.napp.controller.loop = asyncio.get_running_loop()
        url = f"{self.base_endpoint}"
        start = datetime.now(pytz.utc) - timedelta(days=1)
        end = start + timedelta(hours=2)
        payload = {
            "start": start.strftime(TIME_FMT),
            "end": end.strftime(TIME_FMT),
            "switches": [
                "00:00:00:00:00:00:02",
            ],
            "interfaces": [
                "00:00:00:00:00:00:00:03:3",
            ],
        }
        response = await self.api.post(url, json=payload)
        current_data = response.json()
        assert response.status_code == 400
        assert current_data["description"] == "start: Value error, Start in the past not allowed"
        self.scheduler.add.assert_not_called()

    async def test_create_mw_case_7(self):
        """Test a fail case of the REST to create a maintenance window."""
        self.napp.controller.loop = asyncio.get_running_loop()
        url = f"{self.base_endpoint}"
        start = datetime.now(pytz.utc) + timedelta(days=1)
        end = start - timedelta(hours=2)
        payload = {
            "start": start.strftime(TIME_FMT),
            "end": end.strftime(TIME_FMT),
            "switches": [
                "00:00:00:00:00:00:02",
            ],
            "interfaces": [
                "00:00:00:00:00:00:00:03:3",
            ],
        }
        response = await self.api.post(url, json=payload)
        current_data = response.json()

        assert response.status_code == 400
        assert current_data["description"] == "end: Value error, End before start not allowed"
        self.scheduler.add.assert_not_called()

    @pytest.mark.skip(reason="Future feature")
    async def test_create_mw_case_8(self):
        """Test a fail case of the REST to create a maintenance window."""
        self.napp.controller.loop = asyncio.get_running_loop()
        url = f"{self.base_endpoint}"
        start = datetime.now(pytz.utc) + timedelta(days=1)
        end = start + timedelta(hours=2)
        payload = {
            "id": "1234",
            "start": start.strftime(TIME_FMT),
            "end": end.strftime(TIME_FMT),
            "switches": [
                "00:00:00:00:00:00:02",
            ],
            "interfaces": [
                "00:00:00:00:00:00:00:03:3",
            ],
        }
        response = await self.api.post(url, json=payload)
        current_data = response.json()

        assert response.status_code == 400
        assert current_data["description"] == "Setting a maintenance id is not allowed"
        self.scheduler.add.assert_not_called()

    async def test_create_mw_case_9(self):
        """Test a fail case of the REST to create a maintenance window."""
        self.napp.controller.loop = asyncio.get_running_loop()
        url = f"{self.base_endpoint}"
        start = datetime.now(pytz.utc) + timedelta(days=1)
        end = start + timedelta(hours=2)
        payload = {
            "status": "fun",
            "start": start.strftime(TIME_FMT),
            "end": end.strftime(TIME_FMT),
            "switches": [
                "00:00:00:00:00:00:02",
            ],
            "interfaces": [
                "00:00:00:00:00:00:00:03:3",
            ],
        }
        response = await self.api.post(url, json=payload)
        current_data = response.json()

        assert response.status_code == 400
        assert (
            current_data["description"] == "Setting a maintenance status is not allowed"
        )
        self.scheduler.add.assert_not_called()

    async def test_get_mw_case_1(self):
        """Test get all maintenance windows, empty list."""
        self.scheduler.list_maintenances.return_value = MaintenanceWindows.model_construct(
            root=[]
        )
        url = f"{self.base_endpoint}"
        response = await self.api.get(url)
        current_data = response.json()
        assert response.status_code == 200
        assert current_data == []
        self.scheduler.list_maintenances.assert_called_once()

    async def test_get_mw_case_2(self):
        """Test get all maintenance windows."""
        now = datetime.now(pytz.utc)
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        start2 = datetime.now(pytz.utc) + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.scheduler.list_maintenances.return_value = MaintenanceWindows.model_construct(
            root=[
                MW.model_construct(
                    id="1234",
                    start=start1.replace(microsecond=0),
                    end=end1.replace(microsecond=0),
                    switches=["00:00:00:00:00:00:12:23"],
                    description="",
                    links=[],
                    interfaces=[],
                    status="pending",
                    updated_at=now.replace(microsecond=0),
                    inserted_at=now.replace(microsecond=0),
                ),
                MW.model_construct(
                    id="4567",
                    start=start2.replace(microsecond=0),
                    end=end2.replace(microsecond=0),
                    switches=["12:34:56:78:90:ab:cd:ef"],
                    description="",
                    links=[],
                    interfaces=[],
                    status="pending",
                    updated_at=now.replace(microsecond=0),
                    inserted_at=now.replace(microsecond=0),
                ),
            ]
        )
        mw_dict = [
            {
                "id": "1234",
                "start": start1.strftime(TIME_FMT),
                "end": end1.strftime(TIME_FMT),
                "switches": ["00:00:00:00:00:00:12:23"],
                "description": "",
                "links": [],
                "interfaces": [],
                "status": "pending",
                "updated_at": now.strftime(TIME_FMT),
                "inserted_at": now.strftime(TIME_FMT),
            },
            {
                "id": "4567",
                "start": start2.strftime(TIME_FMT),
                "end": end2.strftime(TIME_FMT),
                "switches": ["12:34:56:78:90:ab:cd:ef"],
                "description": "",
                "links": [],
                "interfaces": [],
                "status": "pending",
                "updated_at": now.strftime(TIME_FMT),
                "inserted_at": now.strftime(TIME_FMT),
            },
        ]

        url = f"{self.base_endpoint}"
        response = await self.api.get(url)
        current_data = response.json()
        assert response.status_code == 200
        assert current_data == mw_dict
        self.scheduler.list_maintenances.assert_called_once()

    async def test_get_mw_case_3(self):
        """Test get non-existent id."""
        self.scheduler.get_maintenance.return_value = None
        url = f"{self.base_endpoint}/2345"
        response = await self.api.get(url)
        current_data = response.json()
        assert response.status_code == 404
        assert current_data["description"] == "Maintenance with id 2345 not found"
        self.scheduler.get_maintenance.assert_called_once_with("2345")

    async def test_get_mw_case_4(self):
        """Test get existent id."""
        now = datetime.now(pytz.utc)
        start2 = datetime.now(pytz.utc) + timedelta(hours=5)
        end2 = start2 + timedelta(hours=1, minutes=30)
        self.scheduler.get_maintenance.return_value = MW.model_construct(
            id="4567",
            start=start2.replace(microsecond=0),
            end=end2.replace(microsecond=0),
            switches=["12:34:56:78:90:ab:cd:ef"],
            updated_at=now.replace(microsecond=0),
            inserted_at=now.replace(microsecond=0),
        )
        mw_dict = {
            "id": "4567",
            "start": start2.strftime(TIME_FMT),
            "end": end2.strftime(TIME_FMT),
            "switches": ["12:34:56:78:90:ab:cd:ef"],
            "description": "",
            "links": [],
            "interfaces": [],
            "status": "pending",
            "updated_at": now.strftime(TIME_FMT),
            "inserted_at": now.strftime(TIME_FMT),
        }
        url = f"{self.base_endpoint}/4567"
        response = await self.api.get(url)
        current_data = response.json()
        assert response.status_code == 200
        assert current_data == mw_dict
        self.scheduler.get_maintenance.assert_called_once_with("4567")

    async def test_remove_mw_case_1(self):
        """Test remove non-existent id."""
        self.scheduler.get_maintenance.return_value = None
        url = f"{self.base_endpoint}/2345"
        response = await self.api.delete(url)
        current_data = response.json()
        assert response.status_code == 404
        assert current_data["description"] == "Maintenance with id 2345 not found"
        self.scheduler.get_maintenance.assert_called_once_with("2345")
        self.scheduler.remove.assert_not_called()

    async def test_remove_mw_case_2(self):
        """Test remove existent id."""
        start1 = datetime.now(pytz.utc) + timedelta(hours=1)
        end1 = start1 + timedelta(hours=6)
        self.scheduler.get_maintenance.return_value = MW.model_construct(
            id="1234",
            start=start1.replace(microsecond=0),
            end=end1.replace(microsecond=0),
            switches=["00:00:00:00:00:00:12:23"],
        )
        url = f"{self.base_endpoint}/1234"
        response = await self.api.delete(url)
        current_data = response.json()
        assert response.status_code == 200
        assert current_data == {
            "response": "Maintenance with id 1234 " "successfully removed"
        }
        self.scheduler.get_maintenance.assert_called_once_with("1234")
        self.scheduler.remove.assert_called_once_with("1234")

    async def test_remove_mw_case_3(self):
        """Test remove existent id."""
        start1 = datetime.now(pytz.utc) - timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        self.scheduler.get_maintenance.return_value = MW.model_construct(
            id="1234",
            start=start1.replace(microsecond=0),
            end=end1.replace(microsecond=0),
            switches=["00:00:00:00:00:00:12:23"],
            status="running",
        )
        url = f"{self.base_endpoint}/1234"
        response = await self.api.delete(url)
        current_data = response.json()
        assert response.status_code == 400
        assert (
            current_data["description"]
            == "Deleting a running maintenance is not allowed"
        )
        self.scheduler.get_maintenance.assert_called_once_with("1234")
        self.scheduler.remove.assert_not_called()

    async def test_update_mw_case_1(self):
        """Test update non-existent id."""
        self.napp.controller.loop = asyncio.get_running_loop()
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        self.scheduler.get_maintenance.return_value = None
        payload = {
            "start": start1.strftime(TIME_FMT),
        }
        url = f"{self.base_endpoint}/2345"
        response = await self.api.patch(url, json=payload)
        current_data = response.json()
        assert response.status_code == 404
        assert current_data["description"] == "Maintenance with id 2345 not found"
        self.scheduler.update.assert_not_called()

    async def test_update_mw_case_2(self):
        """Test update missing required field."""
        self.napp.controller.loop = asyncio.get_running_loop()
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        payload = {
            "end": start1.strftime(TIME_FMT),
        }
        url = f"{self.base_endpoint}/1234"
        response = await self.api.patch(url, json=payload)
        current_data = response.json()
        assert response.status_code == 400
        assert "Field required" in current_data["description"]

    async def test_update_mw_case_3(self):
        """Test successful update."""
        self.napp.controller.loop = asyncio.get_running_loop()
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        self.scheduler.get_maintenance.return_value = MW.model_construct(
            id="1234",
            start=start1.replace(microsecond=0),
            end=end1.replace(microsecond=0),
            switches=["00:00:00:00:00:00:12:23"],
        )
        start_new = datetime.now(pytz.utc) + timedelta(days=1, hours=3)
        payload = {
            "start": start_new.strftime(TIME_FMT),
        }
        url = f"{self.base_endpoint}/1234"
        response = await self.api.patch(url, json=payload)
        current_data = response.json()
        assert current_data == {"response": "Maintenance 1234 updated"}
        assert response.status_code == 200
        self.scheduler.get_maintenance.assert_called_once_with("1234")
        self.scheduler.update.assert_called_once_with(
            MW.model_construct(
                id="1234",
                start=start_new.replace(microsecond=0),
                end=end1.replace(microsecond=0),
                switches=["00:00:00:00:00:00:12:23"],
            )
        )

    async def test_update_mw_case_4(self):
        """Test successful update."""
        self.napp.controller.loop = asyncio.get_running_loop()
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        self.scheduler.get_maintenance.return_value = MW.model_construct(
            id="1234",
            start=start1.replace(microsecond=0),
            end=end1.replace(microsecond=0),
            switches=["00:00:00:00:00:00:12:23"],
        )
        start_new = datetime.now(pytz.utc) - timedelta(days=1, hours=3)
        payload = {
            "start": start_new.strftime(TIME_FMT),
        }
        url = f"{self.base_endpoint}/1234"
        response = await self.api.patch(url, json=payload)
        current_data = response.json()
        assert response.status_code == 400
        assert current_data["description"] == "start: Value error, Start in the past not allowed"
        self.scheduler.get_maintenance.assert_called_once_with("1234")
        self.scheduler.update.assert_not_called()

    async def test_update_mw_case_5(self):
        """Test successful update."""
        self.napp.controller.loop = asyncio.get_running_loop()
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        self.scheduler.get_maintenance.return_value = MW.model_construct(
            id="1234",
            start=start1.replace(microsecond=0),
            end=end1.replace(microsecond=0),
            switches=["00:00:00:00:00:00:12:23"],
        )
        start_new = datetime.now(pytz.utc) + timedelta(days=1, hours=3)
        end_new = start_new - timedelta(hours=5)
        payload = {
            "start": start_new.strftime(TIME_FMT),
            "end": end_new.strftime(TIME_FMT),
        }
        url = f"{self.base_endpoint}/1234"
        response = await self.api.patch(url, json=payload)
        current_data = response.json()
        assert response.status_code == 400
        assert current_data["description"] == "end: Value error, End before start not allowed"
        self.scheduler.get_maintenance.assert_called_once_with("1234")
        self.scheduler.update.assert_not_called()

    async def test_update_mw_case_6(self):
        """Test successful update."""
        self.napp.controller.loop = asyncio.get_running_loop()
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        self.scheduler.get_maintenance.return_value = MW.model_construct(
            id="1234",
            start=start1.replace(microsecond=0),
            end=end1.replace(microsecond=0),
            switches=["00:00:00:00:00:00:12:23"],
        )
        start_new = datetime.now(pytz.utc) + timedelta(days=1, hours=3)
        payload = {
            "start": start_new.strftime(TIME_FMT),
            "switches": [],
            "interfaces": [],
            "links": [],
        }

        url = f"{self.base_endpoint}/1234"
        response = await self.api.patch(url, json=payload)
        current_data = response.json()
        assert response.status_code == 400
        assert (
            current_data["description"]
            == ": Value error, At least one item must be provided"
        )
        self.scheduler.get_maintenance.assert_called_once_with("1234")
        self.scheduler.update.assert_not_called()

    async def test_update_mw_case_7(self):
        """Test successful update."""
        self.napp.controller.loop = asyncio.get_running_loop()
        start1 = datetime.now(pytz.utc) + timedelta(days=1)
        end1 = start1 + timedelta(hours=6)
        self.scheduler.get_maintenance.return_value = MW.model_construct(
            id="1234",
            start=start1.replace(microsecond=0),
            end=end1.replace(microsecond=0),
            switches=["00:00:00:00:00:00:12:23"],
        )
        payload = {
            "status": "running",
        }
        url = f"{self.base_endpoint}/1234"
        response = await self.api.patch(url, json=payload)
        current_data = response.json()
        assert response.status_code == 400
        assert (
            current_data["description"]
            == "Updating a maintenance status is not allowed"
        )
        self.scheduler.update.assert_not_called()

    async def test_end_mw_case_1(self):
        """Test method that finishes the maintenance now."""
        self.scheduler.get_maintenance.return_value = None
        url = f"{self.base_endpoint}/2345/end"
        response = await self.api.patch(url)
        current_data = response.json()
        assert response.status_code == 404
        assert current_data["description"] == "Maintenance with id 2345 not found"

    async def test_end_mw_case_2(self):
        """Test method that finishes the maintenance now."""
        start1 = datetime.now(pytz.utc) - timedelta(hours=1)
        end1 = start1 + timedelta(hours=6)
        self.scheduler.get_maintenance.return_value = MW.model_construct(
            id="1234",
            start=start1.replace(microsecond=0),
            end=end1.replace(microsecond=0),
            switches=["00:00:00:00:00:00:12:23"],
            status="running",
        )
        url = f"{self.base_endpoint}/1234/end"
        response = await self.api.patch(url)
        current_data = response.json()
        self.scheduler.get.asssert_called_once_with("1234")
        self.scheduler.end_maintenance_early.assert_called_once_with("1234")
        assert response.status_code == 200
        assert current_data == {"response": "Maintenance window 1234 finished"}

    async def test_end_mw_case_3(self):
        """Test method that finishes the maintenance now."""
        start1 = datetime.now(pytz.utc) + timedelta(hours=1)
        end1 = start1 + timedelta(hours=6)
        self.scheduler.get_maintenance.return_value = MW.model_construct(
            id="1234",
            start=start1.replace(microsecond=0),
            end=end1.replace(microsecond=0),
            switches=["00:00:00:00:00:00:12:23"],
            status="pending",
        )
        url = f"{self.base_endpoint}/1234/end"
        response = await self.api.patch(url)
        current_data = response.json()
        self.scheduler.get.asssert_called_once_with("1234")
        self.scheduler.end_maintenance_early.assert_not_called()
        assert response.status_code == 400
        assert (
            current_data["description"] == "Maintenance window 1234 has not yet started"
        )

    async def test_end_mw_case_4(self):
        """Test method that finishes the maintenance now."""
        start1 = datetime.now(pytz.utc) - timedelta(hours=5)
        end1 = start1 + timedelta(hours=4)
        self.scheduler.get_maintenance.return_value = MW.model_construct(
            id="1234",
            start=start1.replace(microsecond=0),
            end=end1.replace(microsecond=0),
            switches=["00:00:00:00:00:00:12:23"],
            status="finished",
        )
        url = f"{self.base_endpoint}/1234/end"
        response = await self.api.patch(url)
        current_data = response.json()
        self.scheduler.get.asssert_called_once_with("1234")
        self.scheduler.end_maintenance_early.assert_not_called()
        assert response.status_code == 400
        assert (
            current_data["description"]
            == "Maintenance window 1234 has already finished"
        )

    async def test_extend_case_1(self):
        """Test successful extension."""
        self.napp.controller.loop = asyncio.get_running_loop()
        start1 = datetime.now(pytz.utc) - timedelta(hours=3)
        end1 = start1 + timedelta(hours=4)
        self.scheduler.get_maintenance.return_value = MW.model_construct(
            id="1234",
            start=start1.replace(microsecond=0),
            end=end1.replace(microsecond=0),
            switches=["00:00:00:00:00:00:12:23"],
            status="running",
        )
        url = f"{self.base_endpoint}/1234/extend"
        payload = {"minutes": 45}
        response = await self.api.patch(url, json=payload)
        assert response.status_code == 200
        self.scheduler.get_maintenance.called_with("1234")
        self.scheduler.update.assert_called_with(
            MW.model_construct(
                id="1234",
                start=start1.replace(microsecond=0),
                end=end1.replace(microsecond=0) + timedelta(minutes=45),
                switches=["00:00:00:00:00:00:12:23"],
                status="running",
            )
        )

    async def test_extend_case_2(self):
        """Test no payload error."""
        self.napp.controller.loop = asyncio.get_running_loop()
        url = f"{self.base_endpoint}/1234/extend"
        response = await self.api.patch(url)
        assert response.status_code == 400
        current_data = response.json()
        assert "Invalid json" in current_data["description"]
        self.scheduler.update.assert_not_called()

    async def test_extend_case_3(self):
        """Test payload without minutes."""
        self.napp.controller.loop = asyncio.get_running_loop()
        url = f"{self.base_endpoint}/1234/extend"
        payload = {"seconds": 240}
        response = await self.api.patch(url, json=payload)
        assert response.status_code == 400
        current_data = response.json()
        assert current_data["description"] == "Minutes of extension must be sent"
        self.scheduler.update.assert_not_called()

    async def test_extend_case_4(self):
        """Test no integer extension minutes."""
        self.napp.controller.loop = asyncio.get_running_loop()
        url = f"{self.base_endpoint}/1234/extend"
        payload = {"minutes": "240"}
        response = await self.api.patch(url, json=payload)
        assert response.status_code == 400
        current_data = response.json()
        assert current_data["description"] == "Minutes of extension must be integer"
        self.scheduler.update.assert_not_called()

    async def test_extend_case_5(self):
        """Test maintenance did not start."""
        self.napp.controller.loop = asyncio.get_running_loop()
        start1 = datetime.now(pytz.utc) + timedelta(hours=3)
        end1 = start1 + timedelta(hours=4)
        self.scheduler.get_maintenance.return_value = MW.model_construct(
            id="1234",
            start=start1.replace(microsecond=0),
            end=end1.replace(microsecond=0),
            switches=["00:00:00:00:00:00:12:23"],
            status="pending",
        )
        url = f"{self.base_endpoint}/1234/extend"
        payload = {"minutes": 240}
        response = await self.api.patch(url, json=payload)
        assert response.status_code == 400
        current_data = response.json()
        assert (
            current_data["description"] == "Maintenance window 1234 has not yet started"
        )
        self.scheduler.get_maintenance.assert_called_once_with("1234")
        self.scheduler.update.assert_not_called()

    async def test_extend_case_6(self):
        """Test maintenance already finished."""
        self.napp.controller.loop = asyncio.get_running_loop()
        start1 = datetime.now(pytz.utc) - timedelta(hours=3)
        end1 = start1 + timedelta(hours=2)
        self.scheduler.get_maintenance.return_value = MW.model_construct(
            id="1234",
            start=start1.replace(microsecond=0),
            end=end1.replace(microsecond=0),
            switches=["00:00:00:00:00:00:12:23"],
            status="finished",
        )
        url = f"{self.base_endpoint}/1234/extend"
        payload = {"minutes": 240}
        response = await self.api.patch(url, json=payload)
        assert response.status_code == 400
        current_data = response.json()
        assert (
            current_data["description"]
            == "Maintenance window 1234 has already finished"
        )
        self.scheduler.get_maintenance.assert_called_once_with("1234")
        self.scheduler.update.assert_not_called()

    async def test_extend_case_7(self):
        """Test no maintenace found."""
        self.napp.controller.loop = asyncio.get_running_loop()
        self.scheduler.get_maintenance.return_value = None
        url = f"{self.base_endpoint}/1235/extend"
        payload = {"minutes": 240}
        response = await self.api.patch(url, json=payload)
        assert response.status_code == 404
        current_data = response.json()
        assert current_data["description"] == "Maintenance with id 1235 not found"
        self.scheduler.get_maintenance.assert_called_once_with("1235")
        self.scheduler.update.assert_not_called()
