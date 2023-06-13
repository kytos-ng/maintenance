"""MaintenanceController."""

# pylint: disable=invalid-name
from datetime import datetime
import os
import pytz
from typing import Optional

from bson.codec_options import CodecOptions
import pymongo
from pymongo.errors import AutoReconnect, DuplicateKeyError
from tenacity import retry_if_exception_type, stop_after_attempt, wait_random

from kytos.core import log
from kytos.core.db import Mongo
from kytos.core.retry import before_sleep, for_all_methods, retries
from napps.kytos.maintenance.models import (
    MaintenanceWindow,
    MaintenanceWindows,
    MaintenanceID,
    Status,
)


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
        now = datetime.now(pytz.utc)
        try:
            self.windows.insert_one({
                        **window.dict(exclude={'inserted_at', 'updated_at'}),
                        'inserted_at': now,
                        'updated_at': now,
            })
        except DuplicateKeyError as err:
            raise ValueError(f'Window with id: {window.id} already exists') from err

    def update_window(self, window: MaintenanceWindow):
        self.windows.update_one(
            {'id': window.id},
            [{
                '$set': {
                    **window.dict(exclude={'inserted_at', 'updated_at'}),
                    'updated_at': '$$NOW',
                },
            }],
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
            [{
                '$set': {
                    'status': Status.RUNNING,
                    'last_modified': '$$NOW',
                },
            }],
            {'_id': False},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        return MaintenanceWindow.construct(**window)

    def end_window(self, mw_id: MaintenanceID) -> MaintenanceWindow:
        window = self.windows.find_one_and_update(
            {'id': mw_id},
            [{
                '$set': {
                    'status': Status.FINISHED,
                    'last_modified': '$$NOW',
                },
            }],
            {'_id': False},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        return MaintenanceWindow.construct(**window)

    def check_overlap(self, window):
        # If two time periods are overlapping,
        # then the start of one time period must occur in the other time period
        windows = self.windows.find(
            {
                '$or': [
                    {'$and': [
                        {'start': {'$lte': window.start}},
                        {'end': {'$gt': window.start}},
                    ]},
                    {'$and': [
                        {'start': {'$gte': window.start}},
                        {'start': {'$lt': window.end}},
                    ]}
                ]
            },
            {'_id': False}
        )
        return MaintenanceWindows.construct(
            __root__ = [MaintenanceWindow.construct(**window) for window in windows]
        )

    def get_windows(self) -> MaintenanceWindows:
        windows = self.windows.find(projection={'_id': False})
        return MaintenanceWindows.construct(
            __root__ = [MaintenanceWindow.construct(**window) for window in windows]
        )

    def remove_window(self, mw_id: MaintenanceID):
        self.windows.delete_one({'id': mw_id})

    def prepare_start(self):
        now = datetime.now(pytz.utc)
        self.windows.update_many(
            {'$and': [
                {'status': {'$eq': Status.PENDING}},
                {'start': {'$lte': now}},
            ]},
            {
                '$set': {
                    'status': Status.RUNNING,
                    'last_modified': now,
                },
            }
        )
        self.windows.update_many(
            {'$and': [
                {'status': {'$eq': Status.RUNNING}},
                {'end': {'$lte': now}},
            ]},
            {
                '$set': {
                    'status': Status.FINISHED,
                    'last_modified': now,
                },
            }
        )
