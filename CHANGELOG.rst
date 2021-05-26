#########
Changelog
#########
All notable changes to the Maintenance NApp will be documented in this file.

[UNRELEASED] - Under development
********************************
Added
=====

Changed
=======

Deprecated
==========

Removed
=======

Fixed
=====

Security
========

Changed
=======


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
