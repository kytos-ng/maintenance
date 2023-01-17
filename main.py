"""Main module of kytos/maintenance Kytos Network Application.

This NApp creates maintenance windows, allowing the maintenance of network
devices (switch, link, and interface) without receiving alerts.
"""
from datetime import timedelta

from flask import current_app, jsonify, request
from napps.kytos.maintenance.models import MaintenanceDeployer, MaintenanceID
from napps.kytos.maintenance.models import MaintenanceWindow as MW
from napps.kytos.maintenance.models import OverlapError, Scheduler, Status
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest, NotFound, UnsupportedMediaType

from kytos.core import KytosNApp, rest
# pylint: disable=unused-import
from kytos.core.interface import Interface
from kytos.core.link import Link
from kytos.core.switch import Switch

# pylint: enable=unused-import


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
        self.maintenance_deployer = \
            MaintenanceDeployer.new_deployer(self.controller)

        # Switch.register_status_func(
        #     'maintenance_status',
        #     self.maintenance_deployer.dev_in_maintenance
        # )
        # Interface.register_status_func(
        #     'maintenance_status',
        #     self.maintenance_deployer.dev_in_maintenance
        # )
        # Link.register_status_func(
        #     'maintenance_status',
        #     self.maintenance_deployer.dev_in_maintenance
        # )
        self.scheduler = Scheduler.new_scheduler(self.maintenance_deployer)
        self.scheduler.start()

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
        self.scheduler.shutdown()

    @rest('/v1', methods=['GET'])
    def get_all_mw(self):
        """Return all maintenance windows."""
        maintenances = self.scheduler.list_maintenances()
        return current_app.response_class(
            f"{maintenances.json()}\n",
            mimetype=current_app.config["JSONIFY_MIMETYPE"],
        ), 200

    @rest('/v1/<mw_id>', methods=['GET'])
    def get_mw(self, mw_id: MaintenanceID):
        """Return one maintenance window."""
        window = self.scheduler.get_maintenance(mw_id)
        if window:
            return current_app.response_class(
                f"{window.json()}\n",
                mimetype=current_app.config["JSONIFY_MIMETYPE"],
            ), 200
        raise NotFound(f'Maintenance with id {mw_id} not found')

    @rest('/v1', methods=['POST'])
    def create_mw(self):
        """Create a new maintenance window."""
        data: dict = request.get_json()
        if not data:
            raise UnsupportedMediaType('The request does not have a json')
        try:
            if data.get('id') == '':
                del data['id']
            maintenance = MW.parse_obj(data)
            force = data.get('force', False)
        except ValidationError as err:
            raise BadRequest(f'{err.errors()[0]["msg"]}') from err
        try:
            self.scheduler.add(maintenance, force=force)
        except OverlapError as err:
            raise BadRequest(f'{err}') from err
        return jsonify({'mw_id': maintenance.id}), 201

    @rest('/v1/<mw_id>', methods=['PATCH'])
    def update_mw(self, mw_id: MaintenanceID):
        """Update a maintenance window."""
        data = request.get_json()
        if not data:
            raise UnsupportedMediaType('The request does not have a json')
        old_maintenance = self.scheduler.get_maintenance(mw_id)
        if old_maintenance is None:
            raise NotFound(f'Maintenance with id {mw_id} not found')
        if old_maintenance.status == Status.RUNNING:
            raise BadRequest('Updating a running maintenance is not allowed')
        if 'status' in data:
            raise BadRequest('Updating a maintenance status is not allowed')
        try:
            new_maintenance = MW.parse_obj({**old_maintenance.dict(), **data})
        except ValidationError as err:
            raise BadRequest(f'{err.errors()[0]["msg"]}') from err
        if new_maintenance.id != old_maintenance.id:
            raise BadRequest('Updated id must match old id')
        self.scheduler.update(new_maintenance)
        return jsonify({'response': f'Maintenance {mw_id} updated'}), 200

    @rest('/v1/<mw_id>', methods=['DELETE'])
    def remove_mw(self, mw_id: MaintenanceID):
        """Delete a maintenance window."""
        maintenance = self.scheduler.get_maintenance(mw_id)
        if maintenance is None:
            raise NotFound(f'Maintenance with id {mw_id} not found')
        if maintenance.status == Status.RUNNING:
            raise BadRequest('Deleting a running maintenance is not allowed')
        self.scheduler.remove(mw_id)
        return jsonify({'response': f'Maintenance with id {mw_id} '
                                    f'successfully removed'}), 200

    @rest('/v1/<mw_id>/end', methods=['PATCH'])
    def end_mw(self, mw_id: MaintenanceID):
        """Finish a maintenance window right now."""
        maintenance = self.scheduler.get_maintenance(mw_id)
        if maintenance is None:
            raise NotFound(f'Maintenance with id {mw_id} not found')
        if maintenance.status == Status.PENDING:
            raise BadRequest(
                f'Maintenance window {mw_id} has not yet started'
            )
        if maintenance.status == Status.FINISHED:
            raise BadRequest(
                f'Maintenance window {mw_id} has already finished'
            )
        self.scheduler.end_maintenance_early(mw_id)
        return jsonify({'response': f'Maintenance window {mw_id} '
                                    f'finished'}), 200

    @rest('/v1/<mw_id>/extend', methods=['PATCH'])
    def extend_mw(self, mw_id):
        """Extend a running maintenance window."""
        data = request.get_json()
        if not data:
            raise UnsupportedMediaType('The request does not have a json')
        maintenance = self.scheduler.get_maintenance(mw_id)
        if maintenance is None:
            raise NotFound(f'Maintenance with id {mw_id} not found')
        if 'minutes' not in data:
            raise BadRequest('Minutes of extension must be sent')
        if maintenance.status == Status.PENDING:
            raise BadRequest(
                f'Maintenance window {mw_id} has not yet started'
            )
        if maintenance.status == Status.FINISHED:
            raise BadRequest(
                f'Maintenance window {mw_id} has already finished'
            )
        try:
            maintenance_end = maintenance.end + \
                timedelta(minutes=data['minutes'])
            new_maintenance = maintenance.copy(
                update={'end': maintenance_end}
            )
        except TypeError as exc:
            raise BadRequest('Minutes of extension must be integer') from exc

        self.scheduler.update(new_maintenance)
        return jsonify({'response': f'Maintenance {mw_id} extended'}), 200
