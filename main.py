"""Main module of kytos/maintenance Kytos Network Application.

This NApp creates maintenance windows, allowing the maintenance of network
devices (a switch, a board, a link) without receiving alerts.
"""
import datetime

import pytz
from flask import jsonify, request

from kytos.core import KytosNApp, rest
from napps.kytos.maintenance.models import MaintenanceWindow as MW
from napps.kytos.maintenance.models import Scheduler


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
        pass

    def shutdown(self):
        """Run when your napp is unloaded.

        If you have some cleanup procedure, insert it here.
        """
        pass

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
            return jsonify({'response': f'Maintenance with id {mw_id} not '
                                        f'found'}), 404

    @rest('/', methods=['POST'])
    def create_mw(self):
        """Create a new maintenance window."""
        now = datetime.datetime.now(pytz.utc)
        data = request.get_json()
        if not data:
            return jsonify("Bad request: The request do not have a json."), 415
        maintenance = MW.from_dict(data, self.controller)
        if maintenance is None:
            return jsonify('One or more items are invalid'), 400
        if maintenance.start < now:
            return jsonify('Start in the past not allowed'), 400
        if maintenance.end <= maintenance.start:
            return jsonify('End before start not allowed'), 400
        self.scheduler.add(maintenance)
        self.maintenances[maintenance.id] = maintenance
        return jsonify({'mw_id': maintenance.id}), 201

    @rest('/<mw_id>', methods=['PATCH'])
    def update_mw(self, mw_id):
        """Update a maintenance window."""
        data = request.get_json()
        if not data:
            return jsonify("Bad request: The request do not have a json."), 415
        try:
            maintenance = self.maintenances[mw_id]
        except KeyError:
            return jsonify({'response': f'Maintenance with id {mw_id} not '
                                        f'found'}), 404
        try:
            maintenance.update(data)
        except ValueError as error:
            return jsonify(f'{error}'), 400
        self.scheduler.remove(maintenance)
        self.scheduler.add(maintenance)
        return jsonify({'response': f'Maintenance {mw_id} updated'}), 201

    @rest('/<mw_id>', methods=['DELETE'])
    def remove_mw(self, mw_id):
        """Delete a maintenance window."""
        try:
            maintenance = self.maintenances[mw_id]
        except KeyError:
            return jsonify({'response': f'Maintenance with id {mw_id} not '
                                        f'found'}), 404
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
            return jsonify({'response': f'Maintenance with id '
                                        f'{mw_id} not found'}), 404
        now = datetime.datetime.now(pytz.utc)
        if now < maintenance.start:
            return jsonify({'response': f'Maintenance window {mw_id} has not '
                                        f'yet started.'}), 400
        if now > maintenance.end:
            return jsonify({'response': f'Maintenance window {mw_id} has '
                                        f'already finished.'}), 400
        self.scheduler.remove(maintenance)
        maintenance.end_mw()
        return jsonify({'response': f'Maintenance window {mw_id} '
                                    f'finished.'}), 200
