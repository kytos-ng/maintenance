"""Main module of kytos/maintenance Kytos Network Application.

This NApp creates maintenance windows, allowing the maintenance of network
devices (switch, link, and interface) without receiving alerts.
"""

from datetime import timedelta

from napps.kytos.maintenance.managers import MaintenanceDeployer as Deployer
from napps.kytos.maintenance.managers import MaintenanceScheduler as Scheduler
from napps.kytos.maintenance.models import MaintenanceID
from napps.kytos.maintenance.models import MaintenanceWindow as MW
from napps.kytos.maintenance.models import OverlapError, Status
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError

from kytos.core import KytosNApp, rest
from kytos.core.rest_api import (
    HTTPException,
    JSONResponse,
    Request,
    Response,
    error_msg,
    get_json_or_400,
)


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
        self.maintenance_deployer = Deployer.new_deployer(self.controller)
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

    @rest("/v1", methods=["GET"])
    def get_all_mw(self, _request: Request) -> Response:
        """Return all maintenance windows."""
        maintenances = self.scheduler.list_maintenances()
        return Response(
            f"{maintenances.json()}\n",
            status_code=200,
            media_type="application/json",
        )

    @rest("/v1/{mw_id}", methods=["GET"])
    def get_mw(self, request: Request) -> Response:
        """Return one maintenance window."""
        mw_id: MaintenanceID = request.path_params["mw_id"]
        window = self.scheduler.get_maintenance(mw_id)
        if window:
            return Response(
                f"{window.json()}\n",
                status_code=200,
                media_type="application/json",
            )
        raise HTTPException(404, f"Maintenance with id {mw_id} not found")

    @rest("/v1", methods=["POST"])
    def create_mw(self, request: Response) -> JSONResponse:
        """Create a new maintenance window."""
        data = get_json_or_400(request, self.controller.loop)
        if not isinstance(data, dict) or not data:
            raise HTTPException(400, detail=f"Invalid json body value: {data}")

        if "status" in data:
            raise HTTPException(
                400, detail="Setting a maintenance status is not allowed"
            )
        # if 'id' in data:
        #     raise HTTPException(
        #         400, detail='Setting a maintenance id is not allowed'
        #     )
        try:
            maintenance = MW.parse_obj(data)
            force = data.get("force", False)
            ignore_no_exists = data.get("ignore_no_exists")
            if not ignore_no_exists:
                self.validate_item_existence(maintenance)
            self.scheduler.add(maintenance, force=force)
        except ValidationError as err:
            msg = error_msg(err.errors())
            raise HTTPException(400, detail=msg) from err
        except DuplicateKeyError as err:
            raise HTTPException(
                409, detail=f"Window with id: {maintenance.id} already exists"
            ) from err
        except OverlapError as err:
            raise HTTPException(400, detail=f"{err}") from err
        except ValueError as err:
            raise HTTPException(400, detail=f"{err}") from err
        return JSONResponse({"mw_id": maintenance.id}, status_code=201)

    @rest("/v1/{mw_id}", methods=["PATCH"])
    def update_mw(self, request: Request) -> JSONResponse:
        """Update a maintenance window."""
        data = get_json_or_400(request, self.controller.loop)
        if not isinstance(data, dict) or not data:
            raise HTTPException(400, detail=f"Invalid json body value: {data}")

        mw_id: MaintenanceID = request.path_params["mw_id"]
        old_maintenance = self.scheduler.get_maintenance(mw_id)
        if old_maintenance is None:
            raise HTTPException(404, detail=f"Maintenance with id {mw_id} not found")
        if old_maintenance.status == Status.RUNNING:
            raise HTTPException(
                400, detail="Updating a running maintenance is not allowed"
            )
        if "status" in data:
            raise HTTPException(
                400, detail="Updating a maintenance status is not allowed"
            )
        try:
            new_maintenance = MW.parse_obj({**old_maintenance.model_dump(), **data})
        except ValidationError as err:
            msg = error_msg(err.errors())
            raise HTTPException(400, detail=msg) from err
        if new_maintenance.id != old_maintenance.id:
            raise HTTPException(400, detail="Updated id must match old id")
        self.scheduler.update(new_maintenance)
        return JSONResponse({"response": f"Maintenance {mw_id} updated"})

    @rest("/v1/{mw_id}", methods=["DELETE"])
    def remove_mw(self, request: Request) -> JSONResponse:
        """Delete a maintenance window."""
        mw_id: MaintenanceID = request.path_params["mw_id"]
        maintenance = self.scheduler.get_maintenance(mw_id)
        if maintenance is None:
            raise HTTPException(404, detail=f"Maintenance with id {mw_id} not found")
        if maintenance.status == Status.RUNNING:
            raise HTTPException(
                400, detail="Deleting a running maintenance is not allowed"
            )
        self.scheduler.remove(mw_id)
        return JSONResponse(
            {"response": f"Maintenance with id {mw_id} successfully removed"}
        )

    @rest("/v1/{mw_id}/end", methods=["PATCH"])
    def end_mw(self, request: Request) -> JSONResponse:
        """Finish a maintenance window right now."""
        mw_id: MaintenanceID = request.path_params["mw_id"]
        maintenance = self.scheduler.get_maintenance(mw_id)
        if maintenance is None:
            raise HTTPException(404, detail=f"Maintenance with id {mw_id} not found")
        if maintenance.status == Status.PENDING:
            raise HTTPException(
                400, detail=f"Maintenance window {mw_id} has not yet started"
            )
        if maintenance.status == Status.FINISHED:
            raise HTTPException(
                400, detail=f"Maintenance window {mw_id} has already finished"
            )
        self.scheduler.end_maintenance_early(mw_id)
        return JSONResponse({"response": f"Maintenance window {mw_id} " f"finished"})

    @rest("/v1/{mw_id}/extend", methods=["PATCH"])
    def extend_mw(self, request: Request) -> JSONResponse:
        """Extend a running maintenance window."""
        mw_id: MaintenanceID = request.path_params["mw_id"]
        data = get_json_or_400(request, self.controller.loop)
        if not isinstance(data, dict):
            raise HTTPException(400, detail=f"Invalid json body value: {data}")

        maintenance = self.scheduler.get_maintenance(mw_id)
        if maintenance is None:
            raise HTTPException(404, detail=f"Maintenance with id {mw_id} not found")
        if "minutes" not in data:
            raise HTTPException(400, detail="Minutes of extension must be sent")
        if maintenance.status == Status.PENDING:
            raise HTTPException(
                400, detail=f"Maintenance window {mw_id} has not yet started"
            )
        if maintenance.status == Status.FINISHED:
            raise HTTPException(
                400, detail=f"Maintenance window {mw_id} has already finished"
            )
        try:
            maintenance_end = maintenance.end + timedelta(minutes=data["minutes"])
            new_maintenance = maintenance.copy(update={"end": maintenance_end})
        except TypeError as exc:
            raise HTTPException(
                400, detail="Minutes of extension must be integer"
            ) from exc

        self.scheduler.update(new_maintenance)
        return JSONResponse({"response": f"Maintenance {mw_id} extended"})

    def validate_item_existence(self, window: MW):
        """Validate that all items in a maintenance window exist."""
        non_existant_switches = list(
            filter(
                lambda switch_id: self.controller.switches.get(switch_id) is None,
                window.switches,
            )
        )
        non_existant_interfaces = list(
            filter(
                lambda interface_id: self.controller.get_interface_by_id(interface_id)
                is None,
                window.interfaces,
            )
        )
        non_existant_links = list(
            filter(
                lambda link_id: self.controller.links.get(
                    link_id
                )
                is None,
                window.links,
            )
        )

        if non_existant_switches or non_existant_interfaces or non_existant_links:
            items = {
                "switches": non_existant_switches,
                "interfaces": non_existant_interfaces,
                "links": non_existant_links,
            }
            raise HTTPException(400, f"Window contains non-existant items: {items}")
