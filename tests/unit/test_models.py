"""Tests for the models module."""
import pytest

from datetime import datetime, timedelta, timezone
import pytz
from kytos.lib.helpers import get_controller_mock
from napps.kytos.maintenance.models import MaintenanceWindow as MW, Status

TIME_FMT = "%Y-%m-%dT%H:%M:%S%z"


class TestMW:
    """Test of the MaintenanceWindow class."""

    # pylint: disable=protected-access

    def setup_method(self):
        """Initialize before tests are executed."""
        self.controller = get_controller_mock()
        self.start = datetime.now(pytz.utc)
        self.start += timedelta(days=1)
        self.end = self.start + timedelta(hours=6)
        self.switches = [
            "01:23:45:67:89:ab:cd:ef"
        ]
        self.maintenance = MW(
            start=self.start,
            end=self.end,
            switches=self.switches
        )

    def test_as_dict(self):
        """Test as_dict method."""
        mw_dict = self.maintenance.model_dump()
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
        assert mw_dict == expected_dict

    def test_start_in_past(self):
        start = datetime.now(pytz.utc) - timedelta(days=1)

        pytest.raises(ValueError, MW,
            start=start,
            end=self.end,
            switches=self.switches,
        )

    def test_end_before_start(self):
        end = datetime.now(pytz.utc) - timedelta(days=1)

        pytest.raises(ValueError, MW,
            start=self.start,
            end=end,
            switches=self.switches,
        )

    def test_items_empty(self):

        pytest.raises(ValueError, MW,
            start=self.start,
            end=self.end,
        )

    def test_no_end(self):
        """Test MW without end time."""
        window = MW.model_validate(
            {"start": self.start, "switches": self.switches}
        )
        assert window.end == datetime.max.replace(tzinfo=timezone.utc)
