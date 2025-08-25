#########
Changelog
#########
All notable changes to the Maintenance NApp will be documented in this file.

[UNRELEASED] - Under development
********************************

Changed
=======
- Internal refactoring updating UI components to use ``pinia``
- Force option will not ignore time anymore. Instead it will check for time conflicts between assets (switches, interfaces, links).
- MWs can now be created without an ``end``, meaning they will have no end time (actual value is ``9999-12-31T23:59:59.999Z`` which is unreachable). If such MW starts running, it can only be stopped by request and not by updating the MW.
- UI: A modal will appear to confirm if a MW will be created without ``End Time``.
- UI: Added option to enter time period to be added to the current time instead of entering the exact date.

Fixed
=======
- Fixed overridden CSS from the maintenance window list, which affected width

[2025.1.0] - 2025-04-14
***********************

Changed
=======
- UI: The maintenance modal now uses the modal component
- UI: changed variable name which was the reserved keyword interface to k_interface
- UI: Removed the use of this.$set() since it was deprecated

Fixed
=====
- DB controller now retries for ``ExecutionTimeout`` and ``ConnectionFailure`` instead of just ``AutoReconnect``

[2024.1.1] - 2024-09-09
***********************

Fixed
=====
- Fixed maintenance ``edit_windows.kytos`` buttons 

[2024.1.0] - 2024-07-23
***********************

Changed
=======
- Updated python environment installation from 3.9 to 3.11
- Upgraded UI framework to Vue3

[2023.2.0] - 2024-02-16
***********************

Fixed
=====
- Fixed bug that caused links to be filtered incorrectly with interfaces

[2023.1.0] - 2023-06-26
***********************

Added
=====
- Added ``status_func`` and ``status_reason_func`` for maintenance windows.

Fixed
=====
- Prevented potential race conditions when starting/stopping maintenance windows.
- Fixed error 500 when user attempts to add maintenance window with duplicate IDs
- Fixed handling of all device types to properly express all affected devices.

Changed
=======
- Maintenance start and end no longer produce ``kytos/maintenance.*`` events, and instead produce ``topology.interruption.[start|end]`` events to work with blueprint EP0037
- Creating a maintenance window now checks if all devs exist and rejects the window, except when the attribute ``ignore_no_exists`` is set to True

General Information
===================
- ``@rest`` endpoints are now run by ``starlette/uvicorn`` instead of ``flask/werkzeug``.


[2022.3.1] - 2023-02-08
********************************

Fixed
=====
- Fixed maintenance UI using incorrect key for `links` when creating a maintenance window.


[2022.3.0] - 2023-01-23
***********************

Added
=====
- Added persistence to maintenance using mongodb.
- Added tracking of maintenance window creation and updated times.

Changed
=======
- Updated REST API endpoints to include version numbers. Current version is `\v1`.
- Changed API to use descriptive strings for `status` of maintenance windows instead of integers.
- Seperated maintenance window `items` into `switches`, `interfaces`, and `links`. 


[2022.2.1] - 2022-08-15
***********************

Fixed
=====
- Made a shallow copy when iterating on shared data structure to avoid RuntimeError size changed


[2022.2.0] - 2022-08-08
***********************

Added
=====
- UI `k-toolbar` component to list maintenance windows.
- UI `k-toolbar` component to create maintenance windows.  
- UI `k-info-panel` component to list maintenance windows in a sortable and filterable table.
- UI `k-info-panel` component to edit and delete maintenance windows.
- UI `k-info-panel` component to finish maintenance windows.
- UI `k-info-panel` component to extend maintenance windows.


[2022.1.0] - 2022-02-14
***********************

Fixed
=====
- Fixed GET responses in the OpenAPI spec to include ``status``
- Updated requirements to fix conflict error with wrapt and use kytos-ng repository
- Fixed request status code and messages in case of a payload with empty items

Added
=====
- Extend maintenance feature
- Enhanced and standardized setup.py `install_requires` to install pinned dependencies


[1.1.1] - 2021-05-26
********************

Added
=====
- Added verification to not delete/modify maintenances that are running.

Fixed
=====
- Fixed an issue where the scheduler was not updated on maintenance update.

Changed
=======
- Updated class ``Status`` to be JSON Serializable.



[1.1.0] - 2021-03-31
********************

Added
=====
- Added ``description`` and ``status`` attributes to maintenance window.

Changed
=======
- Changed ``setup.py`` to alert when Travis fails.
- Updated dependencies' versions.

Fixed
=====
- Fixed REST API URLs and HTTP status code in the documentation.
- Added missing parameter "Maintenance Window ID" to the REST API documentation.


[1.0.1] - 2020-07-07
********************

Added
=====
- Added ``@tags`` decorator to run tests by type and size.

Fixed
=====
- Fixed README file.


[1.0] - 2020-05-20
******************

Added
=====
- Methods to start and finish a maintenance. These methods generate events
  to make other NApps aware of a maintenance.


[0.2] - 2020-04-17
******************

Added
=====
- Tests to the models module

Fixed
=====
- Fixed datetimes to be timezone aware.


[0.1] - 2020-04-06
******************

Added
=====
- REST API methods to create, delete and update a maintenance.
- Schedule of maintenances.
