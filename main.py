"""Main module of kytos/maintenance Kytos Network Application.

This NApp creates maintenance windows, allowing the maintenance of network
devices (a switch, a board, a link) without receiving alerts.
"""
import datetime

import pytz
from flask import jsonify, request
from napps.kytos.maintenance.models import MaintenanceWindow as MW
from napps.kytos.maintenance.models import Scheduler, Status
from werkzeug.exceptions import BadRequest, NotFound, UnsupportedMediaType

from kytos.core import KytosNApp, rest


class Main(KytosNApp):
    """Main class of kytos/maintenance NApp.

    This class is the entry point for this napp.
    """

    def setup(self):
        """Replace the '__init__' method for the KytosNApp subclass.

        The setup method is automatically called by the controller when your
        application is loaded.

        So, if you have any setup routine, insert it here.
        """
        self.maintenances = {}
        self.scheduler = Scheduler()

    def execute(self):
        """Run after the setup method execution.

        You can also use this method in loop mode if you add to the above setup
        method a line like the following example:

            self.execute_as_loop(30)  # 30-second interval.
        """

    def shutdown(self):
        """Run when your napp is unloaded.

        If you have some cleanup procedure, insert it here.
        """

    @rest('/', methods=['GET'])
    @rest('/<mw_id>', methods=['GET'])
    def get_mw(self, mw_id=None):
        """Return one or all maintenance windows."""
        if mw_id is None:
            return jsonify(
                [maintenance.as_dict()
                 for maintenance in self.maintenances.values()]), 200
        try:
            return jsonify(self.maintenances[mw_id].as_dict()), 200
        except KeyError:
            raise NotFound(f'Maintenance with id {mw_id} not found')

    @rest('/', methods=['POST'])
    def create_mw(self):
        """Create a new maintenance window."""
        now = datetime.datetime.now(pytz.utc)
        data = request.get_json()
        if not data:
            raise UnsupportedMediaType('The request does not have a json.')
        try:
            maintenance = MW.from_dict(data, self.controller)
        except ValueError as err:
            raise BadRequest(f'{err}')
        if maintenance is None:
            raise BadRequest('One or more items are invalid')
        if maintenance.start < now:
            raise BadRequest('Start in the past not allowed')
        if maintenance.end <= maintenance.start:
            raise BadRequest('End before start not allowed')
        self.scheduler.add(maintenance)
        self.maintenances[maintenance.id] = maintenance
        return jsonify({'mw_id': maintenance.id}), 201

    @rest('/<mw_id>', methods=['PATCH'])
    def update_mw(self, mw_id):
        """Update a maintenance window."""
        data = request.get_json()
        if not data:
            raise UnsupportedMediaType('The request does not have a json.')
        try:
            maintenance = self.maintenances[mw_id]
        except KeyError:
            raise NotFound(f'Maintenance with id {mw_id} not found')
        if maintenance.status == Status.RUNNING:
            raise BadRequest('Updating a running maintenance is not allowed')
        try:
            maintenance.update(data)
        except ValueError as error:
            raise BadRequest(f'{error}')
        self.scheduler.remove(maintenance)
        self.scheduler.add(maintenance)
        return jsonify({'response': f'Maintenance {mw_id} updated'}), 200

    @rest('/<mw_id>', methods=['DELETE'])
    def remove_mw(self, mw_id):
        """Delete a maintenance window."""
        try:
            maintenance = self.maintenances[mw_id]
        except KeyError:
            raise NotFound(f'Maintenance with id {mw_id} not found')
        if maintenance.status == Status.RUNNING:
            raise BadRequest('Deleting a running maintenance is not allowed')
        self.scheduler.remove(maintenance)
        del self.maintenances[mw_id]
        return jsonify({'response': f'Maintenance with id {mw_id} '
                                    f'successfully removed'}), 200

    @rest('/<mw_id>/end', methods=['PATCH'])
    def end_mw(self, mw_id):
        """Finish a maintenance window right now."""
        try:
            maintenance = self.maintenances[mw_id]
        except KeyError:
            raise NotFound(f'Maintenance with id {mw_id} not found')
        now = datetime.datetime.now(pytz.utc)
        if now < maintenance.start:
            raise BadRequest(f'Maintenance window {mw_id} has not yet '
                             'started.')
        if now > maintenance.end:
            raise BadRequest(f'Maintenance window {mw_id} has already '
                             'finished.')
        self.scheduler.remove(maintenance)
        maintenance.end_mw()
        return jsonify({'response': f'Maintenance window {mw_id} '
                                    f'finished.'}), 200

    @rest('/<mw_id>/extend', methods=['PATCH'])
    def extend_mw(self, mw_id):
        """Extend a running maintenance window."""
        data = request.get_json()
        if not data:
            raise UnsupportedMediaType('The request does not have a json')
        try:
            maintenance = self.maintenances[mw_id]
        except KeyError:
            raise NotFound(f'Maintenance with id {mw_id} not found')
        if 'minutes' not in data:
            raise BadRequest('Minutes of extension must be sent')
        now = datetime.datetime.now(pytz.utc)
        if now < maintenance.start:
            raise BadRequest(f'Maintenance window {mw_id} has not yet '
                             'started')
        if now > maintenance.end:
            raise BadRequest(f'Maintenance window {mw_id} has already '
                             'finished')
        try:
            maintenance.end = maintenance.end + \
                datetime.timedelta(minutes=data['minutes'])
        except TypeError:
            raise BadRequest('Minutes of extension must be integer')
        self.scheduler.remove(maintenance)
        self.scheduler.add(maintenance)
        return jsonify({'response': f'Maintenance {mw_id} extended'}), 200
