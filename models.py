"""Models used by the maintenance NApp.

This module define models for the maintenance window itself and the
scheduler.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import NewType, Optional
from uuid import uuid4

import pytz

# pylint: disable=no-name-in-module
from pydantic import (
    BaseModel,
    Field,
    RootModel,
    ValidationInfo,
    field_validator,
    model_validator,
)

# pylint: enable=no-name-in-module

TIME_FMT = "%Y-%m-%dT%H:%M:%S%z"


class Status(str, Enum):
    """Maintenance windows status."""

    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"


MaintenanceID = NewType("MaintenanceID", str)


class MaintenanceWindow(BaseModel):
    """Class for structure of maintenance windows."""

    start: datetime
    end: Optional[datetime] = Field(default=datetime.max.replace(tzinfo=timezone.utc))
    switches: list[str] = Field(default_factory=list)
    interfaces: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    id: MaintenanceID = Field(default_factory=lambda: MaintenanceID(uuid4().hex))
    description: str = Field(default="")
    status: Status = Field(default=Status.PENDING)
    inserted_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    # pylint: disable=no-self-argument

    @field_validator("start", "end", mode="before")
    @classmethod
    def convert_time(cls, time):
        """Convert time strings using TIME_FMT"""
        if isinstance(time, str):
            time = datetime.strptime(time, TIME_FMT)
        return time

    @field_validator("start")
    @classmethod
    def check_start_in_past(cls, start_time):
        """Check if the start is set to occur before now."""
        if start_time < datetime.now(pytz.utc):
            raise ValueError("Start in the past not allowed")
        return start_time

    @field_validator("end")
    @classmethod
    def check_end_before_start(cls, end_time, values: ValidationInfo):
        """Check if the end is set to occur before the start."""
        if end_time is None:
            end_time = cls.model_fields["end"].get_default()
        if "start" in values.data and end_time <= values.data["start"]:
            raise ValueError("End before start not allowed")
        return end_time

    @model_validator(mode="after")
    def check_items_empty(self):
        """Check if no items are in the maintenance window."""
        no_items = all(
            map(
                lambda key: key not in self.model_dump()
                or len(self.model_dump()[key]) == 0,
                ["switches", "links", "interfaces"],
            )
        )
        if no_items:
            raise ValueError("At least one item must be provided")
        return self

    # pylint: enable=no-self-argument

    def __str__(self) -> str:
        return f"'{self.id}'<{self.start} to {self.end}>"

    class Config:
        """Config for encoding MaintenanceWindow class"""

        json_encoders = {
            datetime: lambda v: v.strftime(TIME_FMT),
        }


class MaintenanceWindows(RootModel):
    """List of Maintenance Windows for json conversion."""

    root: list[MaintenanceWindow]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def __len__(self):
        return len(self.root)

    class Config:
        """Config for encoding MaintenanceWindows class"""

        json_encoders = {
            datetime: lambda v: v.strftime(TIME_FMT),
        }


class OverlapError(Exception):
    """
    Exception for when a Maintenance Windows execution
    period overlaps with one or more windows.
    """

    new_window: MaintenanceWindow
    interfering: MaintenanceWindows

    def __init__(self, new_window: MaintenanceWindow, interfering: MaintenanceWindows):
        self.new_window = new_window
        self.interfering = interfering

    def __str__(self):
        return (
            f"Maintenance Window {self.new_window} "
            + "interferes with the following windows: "
            + "["
            + ", ".join([f"{window}" for window in self.interfering])
            + "]"
        )
