"""MaintenanceController."""

# pylint: disable=invalid-name
import os
from typing import Optional

from bson.codec_options import CodecOptions
import pymongo
from pymongo.errors import AutoReconnect
from tenacity import retry_if_exception_type, stop_after_attempt, wait_random
from werkzeug.exceptions import BadRequest

from kytos.core import log
from kytos.core.db import Mongo
from kytos.core.retry import before_sleep, for_all_methods, retries
from napps.kytos.maintenance.models import MaintenanceWindow, MaintenanceID, Status


@for_all_methods(
    retries,
    stop=stop_after_attempt(
        int(os.environ.get("MONGO_AUTO_RETRY_STOP_AFTER_ATTEMPT", 3))
    ),
    wait=wait_random(
        min=int(os.environ.get("MONGO_AUTO_RETRY_WAIT_RANDOM_MIN", 0.1)),
        max=int(os.environ.get("MONGO_AUTO_RETRY_WAIT_RANDOM_MAX", 1)),
    ),
    before_sleep=before_sleep,
    retry=retry_if_exception_type((AutoReconnect,)),
)
class MaintenanceController:
    """MaintenanceController."""

    def __init__(self, get_mongo=lambda: Mongo()) -> None:
        """Constructor of MaintenanceController."""
        self.mongo = get_mongo()
        self.db_client = self.mongo.client
        self.db = self.db_client[self.mongo.db_name]
        self.windows = self.db['maintenance.windows'].with_options(
            codec_options=CodecOptions(
                tz_aware=True,
            )
        )

    def bootstrap_indexes(self) -> None:
        """Bootstrap all maintenance related indexes."""
        unique_index_tuples = [
            ("maintenance.windows", [("id", pymongo.ASCENDING)]),
        ]
        for collection, keys in unique_index_tuples:
            if self.mongo.bootstrap_index(collection, keys, unique=True):
                log.info(
                    f"Created DB unique index {keys}, collection: {collection})"
                )

    def insert_window(self, window: MaintenanceWindow):
        old_window = self.windows.find_one_and_update(
            {'id': window.id},
            {
                '$setOnInsert': {
                    **window.dict(exclude=['inserted_at', 'updated_at']),
                    'inserted_at': '$$NOW',
                    'updated_at': '$$NOW',
                },
            },
            {'_id': False},
            upsert = True,
        )
        if old_window is not None:
            raise BadRequest('Window with given ID already exists')


    def update_window(self, window: MaintenanceWindow):
        self.windows.update_one(
            {'id': window.id},
            {
                '$set': {
                    **window.dict(exclude=['inserted_at', 'updated_at']),
                    'updated_at': '$$NOW',
                },
            },
            {'_id': False},
        )

    def get_window(self, mw_id: MaintenanceID) -> Optional[MaintenanceWindow]:
        window = self.windows.find_one(
            {'id': mw_id},
            {'_id': False},
        )
        if window is None:
            return None
        else:
            return MaintenanceWindow.construct(**window)

    def start_window(self, mw_id: MaintenanceID) -> MaintenanceWindow:
        window = self.windows.find_one_and_update(
            {'id': mw_id},
            {
                '$set': {
                    'status': Status.RUNNING,
                    'last_modified': '$$NOW',
                },
            },
            {'_id': False},
        )
        return MaintenanceWindow.construct(**window)

    def end_window(self, mw_id: MaintenanceID) -> MaintenanceWindow:
        window = self.windows.find_one_and_update(
            {'id': mw_id},
            {
                '$set': {
                    'status': Status.FINISHED,
                    'last_modified': '$$NOW',
                },
            },
            {'_id': False},
        )
        return MaintenanceWindow.construct(**window)

    def get_windows(self) -> list[MaintenanceWindow]:
        windows = self.windows.find(projection={'_id': False})
        return list(windows)

    def remove_window(self, mw_id: MaintenanceID):
        self.windows.delete_one({'id': mw_id})