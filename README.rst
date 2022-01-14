Overview
========

This NApp creates maintenance windows, allowing the maintenance of network
devices (a switch, a board, a link) without receiving alerts. The circuits
using those devices will be moved to another path during the maintenance, if
possible. Notifications about those devices will be disabled during the
maintenance.

Requirements
============
This NApp requires the `apscheduler` python package to schedule the
maintenances.
