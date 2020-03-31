"""Main module of kytos/maintenance Kytos Network Application.

This NApp creates maintenance windows, allowing the maintenance of network
devices (a switch, a board, a link) without receiving alerts.
"""
import datetime
from flask import jsonify, request
from kytos.core import KytosNApp, log
from kytos.core.helpers import listen_to, rest

from napps.kytos.maintenance import settings
from napps.kytos.maintenance.models \
    import MaintenanceWindow as MW, Scheduler


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
        """Return one or all maintenance windows"""
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
        """Create a new maintenance window"""
        now = datetime.datetime.now()
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

