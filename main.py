"""Main module of kytos/maintenance Kytos Network Application.

This NApp creates maintenance windows, allowing the maintenance of network
devices (a switch, a board, a link) without receiving alerts.
"""
import datetime

from flask import jsonify, request
from napps.kytos.maintenance.models import MaintenanceWindow as MW
from napps.kytos.maintenance.models import Scheduler

from kytos.core import KytosNApp, log
from kytos.core.helpers import rest


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
        if mw_id:
            try:
                result = self.maintenances[mw_id].as_dict()
                status = 200
            except KeyError:
                result = {'response': f'Maintenance with id {mw_id} not found'}
                status = 404
        else:
            result = [mw.as_dict() for mw in self.maintenances.values()]
            status = 200

        return jsonify(result), status

    @rest('/', methods=['POST'])
    def create_mw(self):
        """Create a new maintenance window."""
        now = datetime.datetime.utcnow()
        data = request.get_json()
        if not data:
            result = "Bad request: The request do not have a json."
            status = 415
            log.debug('create_mw result %s %s', result, status)
        else:
            mw = MW.from_dict(data, self.controller)
            if mw is None:
                result = 'One or more items are invalid'
                status = 400
            elif mw.start < now:
                result = 'Start in the past not allowed'
                status = 400
            elif mw.end <= mw.start:
                result = 'End before start not allowed'
                status = 400
            else:
                self.scheduler.add(mw)
                self.maintenances[mw.id] = mw
                result = {'mw_id': mw.id}
                status = 201
        return jsonify(result), status

    @rest('/<mw_id>', methods=['PATCH'])
    def update_mw(self, mw_id):
        """Update a maintenance window."""
        data = request.get_json()
        if not data:
            result = "Bad request: The request do not have a json."
            status = 415
            log.debug('update_mw result %s %s', result, status)
        else:
            try:
                mw = self.maintenances[mw_id]
                mw.update(data, self.controller)
                result = {'response': f'Maintenance {mw_id} updated'}
                status = 201
            except KeyError:
                result = {'response': f'Maintenance with id {mw_id} not found'}
                status = 404
        return jsonify(result), status

    @rest('/<mw_id>', methods=['DELETE'])
    def remove_mw(self, mw_id):
        """Delete a maintenance window."""
        try:
            mw = self.maintenances[mw_id]
            self.scheduler.remove(mw)
            del self.maintenances[mw_id]
            result = {'response': f'Maintenance with id {mw_id} successfully '
                                  f'removed'}
            status = 200
        except KeyError:
            result = {'response': f'Maintenance with id {mw_id} not found'}
            status = 404
        return jsonify(result), status

    @rest('/<mw_id>/end', methods=['PATCH'])
    def end_mw(self, mw_id):
        """Finish a maintenance window right now."""
        try:
            mw = self.maintenances[mw_id]
        except KeyError:
            result = {'response': f'Maintenance with id {mw_id} not found'}
            status = 404
        else:
            now = datetime.datetime.utcnow()
            log.info(f'Agora {now}')
            if now < mw.start:
                result = {'response': f'Maintenance window {mw_id} has not '
                                      f'yet started.'}
                status = 400
            elif now > mw.end:
                result = {'response': f'Maintenance window {mw_id} has '
                                      f'already finished.'}
                status = 400
            else:
                self.scheduler.remove(mw)
                mw.end_mw()
                result = {'response': f'Maintenance window {mw_id} finished.'}
                status = 200
        return jsonify(result), status
